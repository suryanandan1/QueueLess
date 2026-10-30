"""Business logic for services offered by a business (e.g. "Cash Deposit", "Haircut")."""

from datetime import datetime, timezone

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models import (
    Appointment,
    Counter,
    MemberRole,
    QueueSession,
    QueueToken,
    Service,
    TokenStatus,
    User,
)
from app.schemas.common import serialize_hours
from app.schemas.service import ServiceCreate, ServiceStats, ServiceUpdate
from app.services.access_control import has_business_role, require_business_role
from app.services.audit_service import record_audit
from app.services.business_service import (
    UPCOMING_APPOINTMENT_STATUSES,
    get_business_for_viewer,
    local_today,
)
from app.services.db_utils import commit_or_conflict
from app.services.wait_time import recent_service_durations

DUPLICATE_NAME_MESSAGE = "A service with this name already exists in the business."


def _get_service_or_404(db: Session, service_id: int) -> Service:
    service = db.get(Service, service_id)
    if service is None:
        raise NotFoundError("Service not found.")
    return service


def get_managed_service(
    db: Session, actor: User, service_id: int, min_role: MemberRole
) -> Service:
    """Load a service and check the actor's role in the business that owns it."""
    service = _get_service_or_404(db, service_id)
    require_business_role(db, actor, service.business_id, min_role)
    return service


def _name_taken(db: Session, business_id: int, name: str, exclude_id: int | None = None) -> bool:
    query = select(Service.id).where(
        Service.business_id == business_id, func.lower(Service.name) == name.lower()
    )
    if exclude_id is not None:
        query = query.where(Service.id != exclude_id)
    return db.scalar(query) is not None


def list_services(
    db: Session, viewer: User | None, business_id: int, include_inactive: bool
) -> list[Service]:
    get_business_for_viewer(db, viewer, business_id)
    query = select(Service).where(Service.business_id == business_id)
    if include_inactive:
        if not has_business_role(db, viewer, business_id):
            raise PermissionDeniedError("Only business members can view inactive services.")
    else:
        query = query.where(Service.is_active.is_(True))
    return list(db.scalars(query.order_by(Service.name)).all())


def get_service_for_viewer(db: Session, viewer: User | None, service_id: int) -> Service:
    service = _get_service_or_404(db, service_id)
    business = get_business_for_viewer(db, viewer, service.business_id)
    if not service.is_active and not has_business_role(db, viewer, business.id):
        raise NotFoundError("Service not found.")
    return service


def create_service(db: Session, actor: User, business_id: int, data: ServiceCreate) -> Service:
    require_business_role(db, actor, business_id, MemberRole.MANAGER)
    name = data.name.strip()
    if _name_taken(db, business_id, name):
        raise ConflictError(DUPLICATE_NAME_MESSAGE)

    service = Service(
        **data.model_dump(exclude={"name", "operating_hours", "appointment_hours"}),
        name=name,
        business_id=business_id,
        operating_hours=serialize_hours(data.operating_hours),
        appointment_hours=serialize_hours(data.appointment_hours),
    )
    db.add(service)
    db.flush()
    record_audit(db, action="service.created", actor=actor, business_id=business_id,
                 entity_type="service", entity_id=service.id)
    commit_or_conflict(db, DUPLICATE_NAME_MESSAGE)
    return service


def update_service(db: Session, actor: User, service_id: int, data: ServiceUpdate) -> Service:
    service = get_managed_service(db, actor, service_id, MemberRole.MANAGER)
    changes = data.changes()
    if "name" in changes:
        changes["name"] = changes["name"].strip()
        if _name_taken(db, service.business_id, changes["name"], exclude_id=service.id):
            raise ConflictError(DUPLICATE_NAME_MESSAGE)
    for hours_field in ("operating_hours", "appointment_hours"):
        if hours_field in changes:
            changes[hours_field] = serialize_hours(getattr(data, hours_field))

    for field_name, value in changes.items():
        setattr(service, field_name, value)
    if changes:
        record_audit(db, action="service.updated", actor=actor, business_id=service.business_id,
                     entity_type="service", entity_id=service.id,
                     details={"fields": sorted(changes)})
        commit_or_conflict(db, DUPLICATE_NAME_MESSAGE)
    return service


def delete_service(db: Session, actor: User, service_id: int) -> None:
    """Hard-delete a service that has no history; otherwise ask the caller to deactivate it."""
    service = get_managed_service(db, actor, service_id, MemberRole.MANAGER)
    has_history = db.scalar(
        select(
            exists().where(QueueSession.service_id == service.id)
            | exists().where(Appointment.service_id == service.id)
        )
    )
    if has_history:
        raise ConflictError(
            "This service has queue or appointment history and cannot be deleted. "
            "Deactivate it instead."
        )
    record_audit(db, action="service.deleted", actor=actor, business_id=service.business_id,
                 entity_type="service", entity_id=service.id, details={"name": service.name})
    db.delete(service)
    db.commit()


def get_service_stats(db: Session, actor: User, service_id: int) -> ServiceStats:
    service = get_managed_service(db, actor, service_id, MemberRole.STAFF)
    today = local_today(service.business)

    def count(query) -> int:
        return db.scalar(query) or 0

    counter_query = select(func.count(Counter.id)).where(Counter.service_id == service.id)
    token_query = (
        select(func.count(QueueToken.id))
        .join(QueueSession)
        .where(QueueSession.service_id == service.id, QueueSession.session_date == today)
    )

    minutes = recent_service_durations(db, service.id)
    average = round(sum(minutes) / len(minutes), 1) if minutes else None

    return ServiceStats(
        service_id=service.id,
        total_counters=count(counter_query),
        active_counters=count(counter_query.where(Counter.is_active.is_(True))),
        tokens_today=count(token_query),
        tokens_waiting=count(token_query.where(QueueToken.status == TokenStatus.WAITING)),
        tokens_completed_today=count(
            token_query.where(QueueToken.status == TokenStatus.COMPLETED)
        ),
        average_service_minutes=average,
        upcoming_appointments=count(
            select(func.count(Appointment.id)).where(
                Appointment.service_id == service.id,
                Appointment.scheduled_start >= datetime.now(timezone.utc),
                Appointment.status.in_(UPCOMING_APPOINTMENT_STATUSES),
            )
        ),
    )
