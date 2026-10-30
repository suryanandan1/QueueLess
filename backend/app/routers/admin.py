from typing import Annotated

from fastapi import APIRouter, Query

from app.core.dependencies import DbSession, PaginationParams, SuperAdmin
from app.models import UserRole
from app.schemas.admin import AuditLogRead, PlatformStats
from app.schemas.business import BusinessRead
from app.schemas.common import Page
from app.schemas.user import UserRead, UserStatusUpdate
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["Super admin"])

SearchQuery = Annotated[str | None, Query(max_length=100)]


@router.get("/stats", response_model=PlatformStats)
def get_platform_stats(db: DbSession, _admin: SuperAdmin):
    return admin_service.get_platform_stats(db)


@router.get("/users", response_model=Page[UserRead])
def list_users(
    db: DbSession,
    _admin: SuperAdmin,
    pagination: PaginationParams,
    search: SearchQuery = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
):
    items, total = admin_service.list_users(
        db, search, role, is_active, pagination.limit, pagination.offset
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.patch("/users/{user_id}/status", response_model=UserRead)
def set_user_status(user_id: int, payload: UserStatusUpdate, db: DbSession, admin: SuperAdmin):
    return admin_service.set_user_status(db, admin, user_id, payload.is_active)


@router.get("/businesses", response_model=Page[BusinessRead])
def list_all_businesses(
    db: DbSession,
    _admin: SuperAdmin,
    pagination: PaginationParams,
    search: SearchQuery = None,
    is_active: bool | None = None,
):
    items, total = admin_service.list_businesses(
        db, search, is_active, pagination.limit, pagination.offset
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/audit-logs", response_model=Page[AuditLogRead])
def list_audit_logs(
    db: DbSession,
    _admin: SuperAdmin,
    pagination: PaginationParams,
    business_id: int | None = None,
    action: Annotated[str | None, Query(max_length=64)] = None,
):
    items, total = admin_service.list_audit_logs(
        db, business_id, action, pagination.limit, pagination.offset
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)
