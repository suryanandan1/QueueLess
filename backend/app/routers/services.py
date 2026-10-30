from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession, OptionalUser
from app.schemas.service import (
    ServiceCreate,
    ServiceRead,
    ServiceStats,
    ServiceUpdate,
)
from app.services import service_service

router = APIRouter(tags=["Services"])


@router.get("/businesses/{business_id}/services", response_model=list[ServiceRead])
def list_services(
    business_id: int, db: DbSession, viewer: OptionalUser, include_inactive: bool = False
):
    """Active services are public. `include_inactive=true` requires business membership."""
    return service_service.list_services(db, viewer, business_id, include_inactive)


@router.post(
    "/businesses/{business_id}/services",
    response_model=ServiceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_service(
    business_id: int, payload: ServiceCreate, db: DbSession, current_user: CurrentUser
):
    return service_service.create_service(db, current_user, business_id, payload)


@router.get("/services/{service_id}", response_model=ServiceRead)
def get_service(service_id: int, db: DbSession, viewer: OptionalUser):
    return service_service.get_service_for_viewer(db, viewer, service_id)


@router.patch("/services/{service_id}", response_model=ServiceRead)
def update_service(
    service_id: int, payload: ServiceUpdate, db: DbSession, current_user: CurrentUser
):
    return service_service.update_service(db, current_user, service_id, payload)


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(service_id: int, db: DbSession, current_user: CurrentUser) -> None:
    service_service.delete_service(db, current_user, service_id)


@router.get("/services/{service_id}/stats", response_model=ServiceStats)
def get_service_stats(service_id: int, db: DbSession, current_user: CurrentUser):
    return service_service.get_service_stats(db, current_user, service_id)
