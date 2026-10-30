from datetime import date

from fastapi import APIRouter, BackgroundTasks, status

from app.core.dependencies import CurrentUser, DbSession, PaginationParams
from app.models import AppointmentStatus
from app.schemas.appointment import (
    AppointmentCancel,
    AppointmentCreate,
    AppointmentRead,
    AppointmentSlotDay,
)
from app.schemas.common import Page
from app.services import appointment_service
from app.websocket.events import appointments_changed

router = APIRouter(tags=["Appointments"])


def _published(tasks: BackgroundTasks, appointment: AppointmentRead) -> AppointmentRead:
    appointments_changed(tasks, appointment.business_id)
    return appointment


@router.get("/services/{service_id}/appointment-slots", response_model=AppointmentSlotDay,
            summary="Bookable slots for a day (public)")
def list_slots(service_id: int, db: DbSession, date: date):
    return appointment_service.list_slots(db, service_id, date)


@router.post("/appointments", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def book_appointment(payload: AppointmentCreate, db: DbSession, current_user: CurrentUser,
                     tasks: BackgroundTasks):
    return _published(tasks, appointment_service.book_appointment(db, current_user, payload))


@router.get("/appointments", response_model=Page[AppointmentRead], summary="My appointments")
def list_my_appointments(db: DbSession, current_user: CurrentUser, pagination: PaginationParams,
                         upcoming_only: bool = False):
    items, total = appointment_service.list_my_appointments(
        db, current_user, upcoming_only, pagination.limit, pagination.offset
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/appointments/{appointment_id}", response_model=AppointmentRead)
def get_appointment(appointment_id: int, db: DbSession, current_user: CurrentUser):
    return appointment_service.get_appointment_for_viewer(db, current_user, appointment_id)


@router.post("/appointments/{appointment_id}/cancel", response_model=AppointmentRead)
def cancel_appointment(appointment_id: int, db: DbSession, current_user: CurrentUser,
                       tasks: BackgroundTasks, payload: AppointmentCancel | None = None):
    reason = payload.reason if payload else None
    return _published(
        tasks, appointment_service.cancel_appointment(db, current_user, appointment_id, reason)
    )


@router.post("/appointments/{appointment_id}/confirm", response_model=AppointmentRead)
def confirm_appointment(appointment_id: int, db: DbSession, current_user: CurrentUser,
                        tasks: BackgroundTasks):
    return _published(tasks, appointment_service.confirm_appointment(db, current_user, appointment_id))


@router.post("/appointments/{appointment_id}/check-in", response_model=AppointmentRead)
def check_in_appointment(appointment_id: int, db: DbSession, current_user: CurrentUser,
                         tasks: BackgroundTasks):
    return _published(tasks, appointment_service.check_in_appointment(db, current_user, appointment_id))


@router.post("/appointments/{appointment_id}/complete", response_model=AppointmentRead)
def complete_appointment(appointment_id: int, db: DbSession, current_user: CurrentUser,
                         tasks: BackgroundTasks):
    return _published(tasks, appointment_service.complete_appointment(db, current_user, appointment_id))


@router.post("/appointments/{appointment_id}/no-show", response_model=AppointmentRead)
def mark_appointment_no_show(appointment_id: int, db: DbSession, current_user: CurrentUser,
                             tasks: BackgroundTasks):
    return _published(
        tasks, appointment_service.mark_appointment_no_show(db, current_user, appointment_id)
    )


@router.get("/businesses/{business_id}/appointments", response_model=Page[AppointmentRead])
def list_business_appointments(
    business_id: int,
    db: DbSession,
    current_user: CurrentUser,
    pagination: PaginationParams,
    date: date | None = None,
    service_id: int | None = None,
    status: AppointmentStatus | None = None,
):
    items, total = appointment_service.list_business_appointments(
        db, current_user, business_id, date, service_id, status, pagination.limit, pagination.offset
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)
