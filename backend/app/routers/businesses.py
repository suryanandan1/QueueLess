from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentUser, DbSession, OptionalUser, PaginationParams, require_roles
from app.models import BusinessCategory, User, UserRole
from app.schemas.business import (
    BusinessCreate,
    BusinessRead,
    BusinessStats,
    BusinessStatusUpdate,
    BusinessUpdate,
    MyBusinessRead,
    WorkingHoursUpdate,
)
from app.schemas.analytics import BusinessAnalytics
from app.schemas.common import Page
from app.services import analytics_service, business_service

router = APIRouter(prefix="/businesses", tags=["Businesses"])

BusinessCreator = Annotated[
    User, Depends(require_roles(UserRole.BUSINESS_OWNER, UserRole.SUPER_ADMIN))
]


@router.post("", response_model=BusinessRead, status_code=status.HTTP_201_CREATED)
def create_business(payload: BusinessCreate, db: DbSession, current_user: BusinessCreator):
    return business_service.create_business(db, current_user, payload)


@router.get("", response_model=Page[BusinessRead], summary="Browse active businesses")
def list_businesses(
    db: DbSession,
    pagination: PaginationParams,
    search: Annotated[str | None, Query(max_length=100)] = None,
    category: BusinessCategory | None = None,
    city: Annotated[str | None, Query(max_length=100)] = None,
):
    items, total = business_service.list_public_businesses(
        db, search, category, city, pagination.limit, pagination.offset
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/mine", response_model=list[MyBusinessRead], summary="Businesses I belong to")
def list_my_businesses(db: DbSession, current_user: CurrentUser):
    return [
        MyBusinessRead(membership_id=member.id, role=member.role, business=member.business)
        for member in business_service.list_my_businesses(db, current_user)
    ]


@router.get("/{business_id}", response_model=BusinessRead)
def get_business(business_id: int, db: DbSession, viewer: OptionalUser):
    return business_service.get_business_for_viewer(db, viewer, business_id)


@router.patch("/{business_id}", response_model=BusinessRead)
def update_business(
    business_id: int, payload: BusinessUpdate, db: DbSession, current_user: CurrentUser
):
    return business_service.update_business(db, current_user, business_id, payload)


@router.put("/{business_id}/working-hours", response_model=BusinessRead)
def update_working_hours(
    business_id: int, payload: WorkingHoursUpdate, db: DbSession, current_user: CurrentUser
):
    return business_service.update_working_hours(
        db, current_user, business_id, payload.working_hours
    )


@router.patch("/{business_id}/status", response_model=BusinessRead)
def set_business_status(
    business_id: int, payload: BusinessStatusUpdate, db: DbSession, current_user: CurrentUser
):
    return business_service.set_business_status(db, current_user, business_id, payload.is_active)


@router.get("/{business_id}/stats", response_model=BusinessStats)
def get_business_stats(business_id: int, db: DbSession, current_user: CurrentUser):
    return business_service.get_business_stats(db, current_user, business_id)


@router.get("/{business_id}/analytics", response_model=BusinessAnalytics)
def get_business_analytics(
    business_id: int,
    db: DbSession,
    current_user: CurrentUser,
    days: Annotated[int, Query(ge=1, le=90)] = 7,
):
    return analytics_service.get_business_analytics(db, current_user, business_id, days)
