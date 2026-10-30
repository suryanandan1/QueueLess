from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import (
    AT_COUNTER_TOKEN_STATUSES,
    Business,
    BusinessMember,
    Counter,
    MemberRole,
    QueueToken,
    Service,
    TokenStatus,
    User,
)
from app.schemas.queue import CounterConsole
from app.schemas.service import CounterCreate, CounterRead, CounterUpdate
from app.services.access_control import require_business_role
from app.services.audit_service import record_audit
from app.services.db_utils import commit_or_conflict
from app.services.queue_service import build_summary, get_todays_session
from app.services.queue_views import TOKEN_LOAD_OPTIONS, counter_read, staff_token_read
from app.services.service_service import get_managed_service

DUPLICATE_COUNTER_MESSAGE = "A counter with this name already exists for the service."
RECENTLY_COMPLETED_LIMIT = 10

COUNTER_LOAD_OPTIONS = (
    selectinload(Counter.service),
    selectinload(Counter.assigned_member).selectinload(BusinessMember.user),
)


def _get_counter(db: Session, actor: User, counter_id: int, min_role: MemberRole) -> Counter:
    counter = db.get(Counter, counter_id)
    if counter is None:
        raise NotFoundError("Counter not found.")
    require_business_role(db, actor, counter.service.business_id, min_role)
    return counter


def _active_tokens_by_counter(db: Session, counter_ids: list[int]) -> dict[int, QueueToken]:
    if not counter_ids:
        return {}
    tokens = db.scalars(
        select(QueueToken)
        .options(*TOKEN_LOAD_OPTIONS)
        .where(
            QueueToken.counter_id.in_(counter_ids),
            QueueToken.status.in_(AT_COUNTER_TOKEN_STATUSES),
        )
    ).all()
    return {token.counter_id: token for token in tokens}


def counters_to_read(db: Session, counters: list[Counter]) -> list[CounterRead]:
    current = _active_tokens_by_counter(db, [counter.id for counter in counters])
    return [counter_read(counter, current.get(counter.id)) for counter in counters]


def describe_counter(db: Session, counter: Counter) -> CounterRead:
    return counters_to_read(db, [counter])[0]


def _validate_assignee(db: Session, business_id: int, member_id: int | None) -> None:
    if member_id is None:
        return
    member = db.get(BusinessMember, member_id)
    if member is None or member.business_id != business_id or not member.is_active:
        raise BadRequestError("Assigned member must be an active member of this business.")


def _name_taken(db: Session, service_id: int, name: str, exclude_id: int | None = None) -> bool:
    query = select(Counter.id).where(
        Counter.service_id == service_id, func.lower(Counter.name) == name.lower()
    )
    if exclude_id is not None:
        query = query.where(Counter.id != exclude_id)
    return db.scalar(query) is not None


def _ensure_idle(db: Session, counter: Counter, action: str) -> None:
    current = _active_tokens_by_counter(db, [counter.id]).get(counter.id)
    if current is not None:
        raise ConflictError(
            f"{counter.name} is handling token {current.display_code}; finish it before you {action}."
        )


def list_counters(db: Session, actor: User, service_id: int) -> list[CounterRead]:
    service = get_managed_service(db, actor, service_id, MemberRole.STAFF)
    counters = db.scalars(
        select(Counter).options(*COUNTER_LOAD_OPTIONS)
        .where(Counter.service_id == service.id).order_by(Counter.name)
    ).all()
    return counters_to_read(db, list(counters))


def list_business_counters(db: Session, actor: User, business_id: int) -> list[CounterRead]:
    require_business_role(db, actor, business_id, MemberRole.STAFF)
    counters = db.scalars(
        select(Counter)
        .options(*COUNTER_LOAD_OPTIONS)
        .join(Service)
        .where(Service.business_id == business_id)
        .order_by(Service.name, Counter.name)
    ).all()
    return counters_to_read(db, list(counters))


def list_assigned_counters(db: Session, user: User) -> list[CounterRead]:
    """Counters assigned to the user through an active membership of an active business."""
    counters = db.scalars(
        select(Counter)
        .options(*COUNTER_LOAD_OPTIONS)
        .join(BusinessMember, BusinessMember.id == Counter.assigned_member_id)
        .join(Business, Business.id == BusinessMember.business_id)
        .where(
            BusinessMember.user_id == user.id,
            BusinessMember.is_active.is_(True),
            Business.is_active.is_(True),
        )
        .order_by(Counter.name)
    ).all()
    return counters_to_read(db, list(counters))


def get_counter(db: Session, actor: User, counter_id: int) -> CounterRead:
    return describe_counter(db, _get_counter(db, actor, counter_id, MemberRole.STAFF))


def create_counter(db: Session, actor: User, service_id: int, data: CounterCreate) -> CounterRead:
    service = get_managed_service(db, actor, service_id, MemberRole.MANAGER)
    name = data.name.strip()
    if _name_taken(db, service.id, name):
        raise ConflictError(DUPLICATE_COUNTER_MESSAGE)
    _validate_assignee(db, service.business_id, data.assigned_member_id)

    counter = Counter(
        service_id=service.id,
        name=name,
        is_active=data.is_active,
        assigned_member_id=data.assigned_member_id,
    )
    db.add(counter)
    db.flush()
    record_audit(db, action="counter.created", actor=actor, business_id=service.business_id,
                 entity_type="counter", entity_id=counter.id)
    commit_or_conflict(db, DUPLICATE_COUNTER_MESSAGE)
    return describe_counter(db, counter)


def update_counter(db: Session, actor: User, counter_id: int, data: CounterUpdate) -> CounterRead:
    counter = _get_counter(db, actor, counter_id, MemberRole.MANAGER)
    business_id = counter.service.business_id
    changes = data.changes()

    if "service_id" in changes and changes["service_id"] != counter.service_id:
        target = db.get(Service, changes["service_id"])
        if target is None or target.business_id != business_id:
            raise BadRequestError("The counter can only be moved to a service of the same business.")
        _ensure_idle(db, counter, "move it to another service")
    if changes.get("is_active") is False and counter.is_active:
        _ensure_idle(db, counter, "take it offline")

    target_service_id = changes.get("service_id", counter.service_id)
    name = changes.get("name", counter.name).strip()
    if "name" in changes or target_service_id != counter.service_id:
        if _name_taken(db, target_service_id, name, exclude_id=counter.id):
            raise ConflictError(DUPLICATE_COUNTER_MESSAGE)
        changes["name"] = name
    if "assigned_member_id" in changes:
        _validate_assignee(db, business_id, changes["assigned_member_id"])

    for field_name, value in changes.items():
        setattr(counter, field_name, value)
    if changes:
        record_audit(db, action="counter.updated", actor=actor, business_id=business_id,
                     entity_type="counter", entity_id=counter.id,
                     details={"fields": sorted(changes)})
        commit_or_conflict(db, DUPLICATE_COUNTER_MESSAGE)
        db.refresh(counter)
    return describe_counter(db, counter)


def delete_counter(db: Session, actor: User, counter_id: int) -> None:
    counter = _get_counter(db, actor, counter_id, MemberRole.MANAGER)
    _ensure_idle(db, counter, "delete it")
    record_audit(db, action="counter.deleted", actor=actor,
                 business_id=counter.service.business_id, entity_type="counter",
                 entity_id=counter.id, details={"name": counter.name})
    db.delete(counter)
    db.commit()


def get_counter_console(db: Session, actor: User, counter_id: int) -> CounterConsole:
    """Everything a staff member needs at their desk, in one response."""
    counter = _get_counter(db, actor, counter_id, MemberRole.STAFF)
    counter_view = describe_counter(db, counter)
    queue = get_todays_session(db, counter.service)
    if queue is None:
        return CounterConsole(
            counter=counter_view, queue=None, current_token=None,
            waiting=[], skipped=[], recently_completed=[],
        )

    tokens = db.scalars(
        select(QueueToken)
        .options(*TOKEN_LOAD_OPTIONS)
        .where(QueueToken.queue_session_id == queue.id)
        .order_by(QueueToken.token_number)
    ).all()
    current = next(
        (t for t in tokens if t.counter_id == counter.id and t.status in AT_COUNTER_TOKEN_STATUSES),
        None,
    )
    completed = sorted(
        (t for t in tokens if t.status == TokenStatus.COMPLETED),
        key=lambda t: t.completed_at,
        reverse=True,
    )[:RECENTLY_COMPLETED_LIMIT]
    return CounterConsole(
        counter=counter_view,
        queue=build_summary(db, queue),
        current_token=staff_token_read(current) if current else None,
        waiting=[staff_token_read(t) for t in tokens if t.status == TokenStatus.WAITING],
        skipped=[staff_token_read(t) for t in tokens if t.status == TokenStatus.SKIPPED],
        recently_completed=[staff_token_read(t) for t in completed],
    )
