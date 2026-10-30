import re
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import NotFoundError
from app.models import (
    Appointment,
    AppointmentStatus,
    Business,
    BusinessCategory,
    BusinessMember,
    Counter,
    MemberRole,
    QueueSession,
    QueueToken,
    Service,
    TokenStatus,
    User,
)
from app.schemas.business import BusinessCreate, BusinessStats, BusinessUpdate
from app.schemas.common import DayHours, serialize_hours
from app.services.access_control import (
    get_business_or_404,
    has_business_role,
    require_business_role,
)
from app.services.audit_service import record_audit
from app.services.db_utils import commit_or_conflict

UPCOMING_APPOINTMENT_STATUSES = (AppointmentStatus.BOOKED, AppointmentStatus.CONFIRMED)


def local_today(business: Business) -> date:
    return datetime.now(ZoneInfo(business.timezone)).date()


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:150] or "business"


def _unique_slug(db: Session, name: str) -> str:
    base = _slugify(name)
    taken = set(
        db.scalars(
            select(Business.slug).where(or_(Business.slug == base, Business.slug.like(f"{base}-%")))
        )
    )
    if base not in taken:
        return base
    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"


def create_business(db: Session, owner: User, data: BusinessCreate) -> Business:
    business = Business(
        **data.model_dump(exclude={"working_hours"}),
        slug=_unique_slug(db, data.name),
        working_hours=serialize_hours(data.working_hours),
    )
    db.add(business)
    db.flush()
    db.add(BusinessMember(business_id=business.id, user_id=owner.id, role=MemberRole.OWNER))
    record_audit(db, action="business.created", actor=owner, business_id=business.id,
                 entity_type="business", entity_id=business.id)
    commit_or_conflict(db, "A business with a similar name was created at the same time; retry.")
    return business


def list_public_businesses(
    db: Session,
    search: str | None,
    category: BusinessCategory | None,
    city: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Business], int]:
    query = select(Business).where(Business.is_active.is_(True))
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(Business.name.ilike(pattern), Business.description.ilike(pattern)))
    if category:
        query = query.where(Business.category == category)
    if city:
        query = query.where(Business.city.ilike(city.strip()))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(Business.name, Business.id).limit(limit).offset(offset)).all()
    return list(items), total


def list_my_businesses(db: Session, user: User) -> list[BusinessMember]:
    return list(
        db.scalars(
            select(BusinessMember)
            .options(joinedload(BusinessMember.business))
            .where(BusinessMember.user_id == user.id, BusinessMember.is_active.is_(True))
            .order_by(BusinessMember.created_at)
        ).all()
    )


def get_business_for_viewer(db: Session, viewer: User | None, business_id: int) -> Business:
    """Active businesses are public; inactive ones are visible only to their members."""
    business = get_business_or_404(db, business_id)
    if not business.is_active and not has_business_role(db, viewer, business_id):
        raise NotFoundError("Business not found.")
    return business


def update_business(db: Session, actor: User, business_id: int, data: BusinessUpdate) -> Business:
    business = require_business_role(db, actor, business_id, MemberRole.MANAGER)
    changes = data.changes()
    for field_name, value in changes.items():
        setattr(business, field_name, value)
    if changes:
        record_audit(db, action="business.updated", actor=actor, business_id=business.id,
                     entity_type="business", entity_id=business.id,
                     details={"fields": sorted(changes)})
        db.commit()
    return business


def update_working_hours(
    db: Session, actor: User, business_id: int, working_hours: list[DayHours]
) -> Business:
    business = require_business_role(db, actor, business_id, MemberRole.MANAGER)
    business.working_hours = serialize_hours(working_hours)
    record_audit(db, action="business.hours_updated", actor=actor, business_id=business.id,
                 entity_type="business", entity_id=business.id)
    db.commit()
    return business


def set_business_status(db: Session, actor: User, business_id: int, is_active: bool) -> Business:
    business = require_business_role(db, actor, business_id, MemberRole.OWNER)
    if business.is_active != is_active:
        business.is_active = is_active
        record_audit(db, action="business.activated" if is_active else "business.deactivated",
                     actor=actor, business_id=business.id, entity_type="business",
                     entity_id=business.id)
        db.commit()
    return business


def get_business_stats(db: Session, actor: User, business_id: int) -> BusinessStats:
    business = require_business_role(db, actor, business_id, MemberRole.STAFF)
    today = local_today(business)

    def count(query) -> int:
        return db.scalar(query) or 0

    service_filter = Service.business_id == business_id
    counter_query = select(func.count(Counter.id)).join(Service).where(service_filter)
    token_query = (
        select(func.count(QueueToken.id))
        .join(QueueSession)
        .where(QueueSession.business_id == business_id, QueueSession.session_date == today)
    )

    return BusinessStats(
        business_id=business_id,
        total_services=count(select(func.count(Service.id)).where(service_filter)),
        active_services=count(
            select(func.count(Service.id)).where(service_filter, Service.is_active.is_(True))
        ),
        total_counters=count(counter_query),
        active_counters=count(counter_query.where(Counter.is_active.is_(True))),
        active_members=count(
            select(func.count(BusinessMember.id)).where(
                BusinessMember.business_id == business_id, BusinessMember.is_active.is_(True)
            )
        ),
        tokens_today=count(token_query),
        tokens_waiting=count(token_query.where(QueueToken.status == TokenStatus.WAITING)),
        tokens_completed_today=count(
            token_query.where(QueueToken.status == TokenStatus.COMPLETED)
        ),
        upcoming_appointments=count(
            select(func.count(Appointment.id))
            .join(Service)
            .where(
                service_filter,
                Appointment.scheduled_start >= datetime.now(timezone.utc),
                Appointment.status.in_(UPCOMING_APPOINTMENT_STATUSES),
            )
        ),
    )
