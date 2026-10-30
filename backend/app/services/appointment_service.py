"""Advance appointment booking.

Slots are generated from the service's booking hours (appointment_hours, else
operating_hours, else the business working hours) in the business's timezone.

Double booking is prevented in two layers:

* Every booking first runs ``UPDATE services SET booking_version = booking_version + 1``.
  That takes the service's write lock, so bookings for one service are serialized
  and the slot/daily capacity counts that follow cannot race.
* A partial unique index stops one customer holding two live bookings for the
  same service slot, and an overlap check stops overlapping bookings elsewhere.
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models import (
    ACTIVE_APPOINTMENT_STATUSES,
    Appointment,
    AppointmentStatus,
    MemberRole,
    NotificationType,
    Service,
    User,
)
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentSlot,
    AppointmentSlotDay,
)
from app.services.access_control import has_business_role, require_business_role
from app.services.audit_service import record_audit
from app.services.business_service import local_today
from app.services.notification_service import create_notification
from app.services.transitions import compare_and_set

MAX_ADVANCE_DAYS = 60
APPOINTMENT_LOAD_OPTIONS = (
    selectinload(Appointment.service).selectinload(Service.business),
    selectinload(Appointment.customer),
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def appointment_read(appointment: Appointment) -> AppointmentRead:
    service = appointment.service
    return AppointmentRead(
        id=appointment.id,
        service_id=service.id,
        service_name=service.name,
        business_id=service.business_id,
        business_name=service.business.name,
        business_timezone=service.business.timezone,
        customer_id=appointment.customer_id,
        customer_name=appointment.customer.full_name,
        customer_email=appointment.customer.email,
        customer_phone=appointment.customer.phone,
        scheduled_start=appointment.scheduled_start,
        scheduled_end=appointment.scheduled_end,
        status=appointment.status,
        notes=appointment.notes,
        cancellation_reason=appointment.cancellation_reason,
        created_at=appointment.created_at,
        confirmed_at=appointment.confirmed_at,
        checked_in_at=appointment.checked_in_at,
        completed_at=appointment.completed_at,
        cancelled_at=appointment.cancelled_at,
    )


def _get_appointment(db: Session, appointment_id: int) -> Appointment:
    appointment = db.scalar(
        select(Appointment).options(*APPOINTMENT_LOAD_OPTIONS).where(Appointment.id == appointment_id)
    )
    if appointment is None:
        raise NotFoundError("Appointment not found.")
    return appointment


# ----------------------------------------------------------------------- slots


def duration_minutes(service: Service) -> int:
    return service.appointment_duration_minutes or service.estimated_duration_minutes


def _booking_hours(service: Service) -> list[dict]:
    return service.appointment_hours or service.operating_hours or service.business.working_hours or []


def generate_slots(service: Service, day: date) -> list[tuple[datetime, datetime]]:
    """All slot (start, end) pairs in UTC for a local calendar day."""
    entry = next((d for d in _booking_hours(service) if d["day_of_week"] == day.weekday()), None)
    if entry is None or entry["is_closed"]:
        return []
    zone = ZoneInfo(service.business.timezone)
    opens = datetime.combine(day, time.fromisoformat(entry["open_time"]), zone)
    closes = datetime.combine(day, time.fromisoformat(entry["close_time"]), zone)
    step = timedelta(minutes=duration_minutes(service))
    slots = []
    start = opens
    while start + step <= closes:
        slots.append((start.astimezone(timezone.utc), (start + step).astimezone(timezone.utc)))
        start += step
    return slots


def _bookable_service(db: Session, service_id: int) -> Service:
    service = db.get(Service, service_id)
    if (
        service is None
        or not service.is_active
        or not service.business.is_active
    ):
        raise NotFoundError("Service not found.")
    if not service.appointments_enabled:
        raise BadRequestError("This service does not take appointments.")
    return service


def _check_date_window(service: Service, day: date) -> None:
    today = local_today(service.business)
    if day < today:
        raise BadRequestError("That date is in the past.")
    if day > today + timedelta(days=MAX_ADVANCE_DAYS):
        raise BadRequestError(f"Appointments can be booked at most {MAX_ADVANCE_DAYS} days ahead.")


def _day_bounds_utc(service: Service, day: date) -> tuple[datetime, datetime]:
    zone = ZoneInfo(service.business.timezone)
    start = datetime.combine(day, time.min, zone)
    return start.astimezone(timezone.utc), (start + timedelta(days=1)).astimezone(timezone.utc)


def _active_bookings(db: Session, service_id: int, start: datetime, end: datetime):
    return select(Appointment).where(
        Appointment.service_id == service_id,
        Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
        Appointment.scheduled_start >= start,
        Appointment.scheduled_start < end,
    )


def list_slots(db: Session, service_id: int, day: date) -> AppointmentSlotDay:
    service = _bookable_service(db, service_id)
    _check_date_window(service, day)
    day_start, day_end = _day_bounds_utc(service, day)
    booked = db.scalars(_active_bookings(db, service.id, day_start, day_end)).all()
    per_slot: dict[datetime, int] = {}
    for appointment in booked:
        per_slot[appointment.scheduled_start] = per_slot.get(appointment.scheduled_start, 0) + 1

    daily_remaining = (
        max(service.appointment_daily_capacity - len(booked), 0)
        if service.appointment_daily_capacity is not None
        else None
    )
    now = _now()
    slots = []
    for start, end in generate_slots(service, day):
        remaining = max(service.appointment_slot_capacity - per_slot.get(start, 0), 0)
        if daily_remaining is not None:
            remaining = min(remaining, daily_remaining)
        slots.append(
            AppointmentSlot(start=start, end=end, remaining=remaining,
                            is_available=remaining > 0 and start > now)
        )
    return AppointmentSlotDay(
        service_id=service.id,
        date=day,
        timezone=service.business.timezone,
        duration_minutes=duration_minutes(service),
        daily_capacity=service.appointment_daily_capacity,
        daily_remaining=daily_remaining,
        slots=slots,
    )


# --------------------------------------------------------------------- booking


def book_appointment(db: Session, customer: User, data: AppointmentCreate) -> AppointmentRead:
    service = _bookable_service(db, data.service_id)
    start = data.scheduled_start.astimezone(timezone.utc)
    local_day = start.astimezone(ZoneInfo(service.business.timezone)).date()
    _check_date_window(service, local_day)
    if start <= _now():
        raise BadRequestError("That time has already passed.")
    slot = next((s for s in generate_slots(service, local_day) if s[0] == start), None)
    if slot is None:
        raise BadRequestError("That time is not an available appointment slot.")
    end = slot[1]

    # Serialize bookings for this service (see module docstring).
    db.execute(
        update(Service)
        .where(Service.id == service.id)
        .values(booking_version=Service.booking_version + 1)
        .execution_options(synchronize_session=False)
    )
    try:
        overlapping = db.scalar(
            select(Appointment.id).where(
                Appointment.customer_id == customer.id,
                Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
                Appointment.scheduled_start < end,
                Appointment.scheduled_end > start,
            )
        )
        if overlapping:
            raise ConflictError("You already have an appointment that overlaps this time.")

        slot_count = db.scalar(
            select(func.count(Appointment.id)).where(
                Appointment.service_id == service.id,
                Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
                Appointment.scheduled_start == start,
            )
        ) or 0
        if slot_count >= service.appointment_slot_capacity:
            raise ConflictError("This slot has just been fully booked. Please choose another time.")

        if service.appointment_daily_capacity is not None:
            day_start, day_end = _day_bounds_utc(service, local_day)
            day_count = db.scalar(
                select(func.count()).select_from(
                    _active_bookings(db, service.id, day_start, day_end).subquery()
                )
            ) or 0
            if day_count >= service.appointment_daily_capacity:
                raise ConflictError("All appointments for this day are booked.")

        appointment = Appointment(
            customer_id=customer.id,
            service_id=service.id,
            scheduled_start=start,
            scheduled_end=end,
            status=AppointmentStatus.BOOKED,
            notes=data.notes,
        )
        db.add(appointment)
        db.flush()
    except ConflictError:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("You already booked this slot.") from exc

    when = _format_local(start, service)
    create_notification(
        db, user_id=customer.id, business_id=service.business_id,
        notification_type=NotificationType.APPOINTMENT,
        title="Appointment booked",
        message=f"{service.name} at {service.business.name} on {when}. "
        "The business will confirm your booking.",
    )
    record_audit(db, action="appointment.booked", actor=customer, business_id=service.business_id,
                 entity_type="appointment", entity_id=appointment.id,
                 details={"service_id": service.id, "start": start.isoformat()})
    db.commit()
    return appointment_read(_get_appointment(db, appointment.id))


def _format_local(moment: datetime, service: Service) -> str:
    local = moment.astimezone(ZoneInfo(service.business.timezone))
    return local.strftime("%a %d %b %Y, %H:%M") + f" ({service.business.timezone})"


# ----------------------------------------------------------------------- reads


def list_my_appointments(
    db: Session, customer: User, upcoming_only: bool, limit: int, offset: int
) -> tuple[list[AppointmentRead], int]:
    query = select(Appointment).where(Appointment.customer_id == customer.id)
    if upcoming_only:
        query = query.where(
            Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
            Appointment.scheduled_end >= _now(),
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    order = Appointment.scheduled_start.asc() if upcoming_only else Appointment.scheduled_start.desc()
    items = db.scalars(
        query.options(*APPOINTMENT_LOAD_OPTIONS).order_by(order).limit(limit).offset(offset)
    ).all()
    return [appointment_read(a) for a in items], total


def get_appointment_for_viewer(db: Session, viewer: User, appointment_id: int) -> AppointmentRead:
    appointment = _get_appointment(db, appointment_id)
    if appointment.customer_id != viewer.id and not has_business_role(
        db, viewer, appointment.service.business_id, MemberRole.STAFF
    ):
        raise NotFoundError("Appointment not found.")
    return appointment_read(appointment)


def list_business_appointments(
    db: Session,
    actor: User,
    business_id: int,
    day: date | None,
    service_id: int | None,
    status: AppointmentStatus | None,
    limit: int,
    offset: int,
) -> tuple[list[AppointmentRead], int]:
    business = require_business_role(db, actor, business_id, MemberRole.STAFF)
    query = select(Appointment).join(Service).where(Service.business_id == business_id)
    if day is not None:
        zone = ZoneInfo(business.timezone)
        start = datetime.combine(day, time.min, zone).astimezone(timezone.utc)
        query = query.where(
            Appointment.scheduled_start >= start,
            Appointment.scheduled_start < start + timedelta(days=1),
        )
    if service_id is not None:
        query = query.where(Appointment.service_id == service_id)
    if status is not None:
        query = query.where(Appointment.status == status)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.options(*APPOINTMENT_LOAD_OPTIONS)
        .order_by(Appointment.scheduled_start, Appointment.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return [appointment_read(a) for a in items], total


# ----------------------------------------------------------------- transitions


def _transition(
    db: Session,
    actor: User,
    appointment: Appointment,
    expected: tuple[AppointmentStatus, ...],
    values: dict,
    action: str,
) -> None:
    if appointment.status not in expected:
        allowed = ", ".join(s.value for s in expected)
        raise ConflictError(
            f"Cannot {action.replace('_', ' ')} this appointment: it is {appointment.status.value}. "
            f"This is only possible from {allowed}."
        )
    if not compare_and_set(db, Appointment, appointment.id, expected, values):
        db.rollback()
        raise ConflictError("The appointment was just changed by someone else. Refresh and try again.")
    record_audit(db, action=f"appointment.{action}", actor=actor,
                 business_id=appointment.service.business_id, entity_type="appointment",
                 entity_id=appointment.id,
                 details={"from": appointment.status.value, "to": values["status"].value})


def _notify_customer(db: Session, appointment: Appointment, title: str, message: str) -> None:
    create_notification(
        db, user_id=appointment.customer_id, business_id=appointment.service.business_id,
        notification_type=NotificationType.APPOINTMENT, title=title, message=message,
    )


def _finish(db: Session, appointment_id: int) -> AppointmentRead:
    db.commit()
    db.expire_all()
    return appointment_read(_get_appointment(db, appointment_id))


def cancel_appointment(db: Session, actor: User, appointment_id: int, reason: str | None) -> AppointmentRead:
    appointment = _get_appointment(db, appointment_id)
    service = appointment.service
    by_customer = appointment.customer_id == actor.id
    if by_customer:
        if appointment.scheduled_start <= _now():
            raise BadRequestError("Appointments can only be cancelled before they start.")
    elif not has_business_role(db, actor, service.business_id, MemberRole.MANAGER):
        if has_business_role(db, actor, service.business_id, MemberRole.STAFF):
            raise PermissionDeniedError("Only owners and managers can cancel bookings.")
        raise NotFoundError("Appointment not found.")

    _transition(
        db, actor, appointment, (AppointmentStatus.BOOKED, AppointmentStatus.CONFIRMED),
        {"status": AppointmentStatus.CANCELLED, "cancelled_at": _now(),
         "cancellation_reason": reason},
        "cancelled",
    )
    when = _format_local(appointment.scheduled_start, service)
    _notify_customer(
        db, appointment, "Appointment cancelled",
        f"Your {service.name} appointment on {when} was cancelled"
        + (" at your request." if by_customer else f" by {service.business.name}.")
        + (f" Reason: {reason}" if reason and not by_customer else ""),
    )
    return _finish(db, appointment.id)


def confirm_appointment(db: Session, actor: User, appointment_id: int) -> AppointmentRead:
    appointment = _get_appointment(db, appointment_id)
    require_business_role(db, actor, appointment.service.business_id, MemberRole.MANAGER)
    _transition(
        db, actor, appointment, (AppointmentStatus.BOOKED,),
        {"status": AppointmentStatus.CONFIRMED, "confirmed_at": _now()}, "confirmed",
    )
    _notify_customer(
        db, appointment, "Appointment confirmed",
        f"{appointment.service.business.name} confirmed your {appointment.service.name} "
        f"appointment on {_format_local(appointment.scheduled_start, appointment.service)}.",
    )
    return _finish(db, appointment.id)


def check_in_appointment(db: Session, actor: User, appointment_id: int) -> AppointmentRead:
    appointment = _get_appointment(db, appointment_id)
    service = appointment.service
    require_business_role(db, actor, service.business_id, MemberRole.STAFF)
    local_day = appointment.scheduled_start.astimezone(ZoneInfo(service.business.timezone)).date()
    if local_day != local_today(service.business):
        raise BadRequestError("Customers can only check in on the day of their appointment.")
    _transition(
        db, actor, appointment, (AppointmentStatus.BOOKED, AppointmentStatus.CONFIRMED),
        {"status": AppointmentStatus.CHECKED_IN, "checked_in_at": _now()}, "checked_in",
    )
    return _finish(db, appointment.id)


def complete_appointment(db: Session, actor: User, appointment_id: int) -> AppointmentRead:
    appointment = _get_appointment(db, appointment_id)
    require_business_role(db, actor, appointment.service.business_id, MemberRole.STAFF)
    _transition(
        db, actor, appointment, (AppointmentStatus.CHECKED_IN,),
        {"status": AppointmentStatus.COMPLETED, "completed_at": _now()}, "completed",
    )
    return _finish(db, appointment.id)


def mark_appointment_no_show(db: Session, actor: User, appointment_id: int) -> AppointmentRead:
    appointment = _get_appointment(db, appointment_id)
    require_business_role(db, actor, appointment.service.business_id, MemberRole.STAFF)
    if appointment.scheduled_start > _now():
        raise BadRequestError("An appointment can only be marked as no-show after it starts.")
    _transition(
        db, actor, appointment, (AppointmentStatus.BOOKED, AppointmentStatus.CONFIRMED),
        {"status": AppointmentStatus.NO_SHOW}, "no_show",
    )
    return _finish(db, appointment.id)
