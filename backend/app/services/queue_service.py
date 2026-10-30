"""Queue sessions and token allocation (the queue engine).

Token allocation is the critical section. It works like this:

1. Cheap pre-checks (queue open, service available, no duplicate token) give
   friendly errors without taking any lock.
2. A single atomic ``UPDATE queue_sessions SET next_token_number = next_token_number + 1
   WHERE id = :id AND status = 'OPEN' RETURNING next_token_number`` both reserves
   the token number and takes the session's write lock (row lock on PostgreSQL,
   database write lock on SQLite). Concurrent joins for the same queue therefore
   run one at a time from this point on.
3. Capacity and duplicate checks are repeated under that lock, the token row is
   inserted and the transaction commits. Any failure rolls back, which also
   releases the reserved number.

Database constraints back this up: (queue_session_id, token_number) is unique and
a partial unique index allows one active token per customer per session.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import (
    ACTIVE_TOKEN_STATUSES,
    AT_COUNTER_TOKEN_STATUSES,
    Business,
    MemberRole,
    NotificationType,
    QueueSession,
    QueueSessionStatus,
    QueueToken,
    Service,
    TokenStatus,
    User,
)
from app.schemas.queue import (
    NowServing,
    QueueSessionRead,
    QueueSummary,
    StaffTokenRead,
    TokenDetail,
    WalkInCreate,
)
from app.services.access_control import has_business_role, require_business_role
from app.services.audit_service import record_audit
from app.services.business_service import local_today
from app.services.notification_service import create_notification
from app.services.queue_views import TOKEN_LOAD_OPTIONS, session_read, staff_token_read, token_read
from app.services.service_service import get_managed_service
from app.services.transitions import compare_and_set
from app.services.wait_time import estimate_for_session

DUPLICATE_TOKEN_MESSAGE = "You already have an active token in this queue."
CANCELLABLE_ON_CLOSE = (TokenStatus.WAITING, TokenStatus.SKIPPED)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_session_or_404(db: Session, session_id: int) -> QueueSession:
    queue = db.get(QueueSession, session_id)
    if queue is None:
        raise NotFoundError("Queue not found.")
    return queue


def get_todays_session(db: Session, service: Service) -> QueueSession | None:
    return db.scalar(
        select(QueueSession).where(
            QueueSession.service_id == service.id,
            QueueSession.session_date == local_today(service.business),
        )
    )


def _count_tokens(db: Session, session_id: int, statuses) -> int:
    return db.scalar(
        select(func.count(QueueToken.id)).where(
            QueueToken.queue_session_id == session_id, QueueToken.status.in_(statuses)
        )
    ) or 0


def _active_token_for(db: Session, session_id: int, customer_id: int) -> QueueToken | None:
    return db.scalar(
        select(QueueToken).where(
            QueueToken.queue_session_id == session_id,
            QueueToken.customer_id == customer_id,
            QueueToken.status.in_(ACTIVE_TOKEN_STATUSES),
        )
    )


def joining_blocker(db: Session, queue: QueueSession) -> str | None:
    """Why customers cannot join this queue right now, or None if they can."""
    if not queue.business.is_active:
        return "This business is not accepting customers."
    if not queue.service.is_active or not queue.service.is_available:
        return "This service is not available right now."
    if queue.status == QueueSessionStatus.CLOSED:
        return "This queue is closed."
    if queue.status == QueueSessionStatus.PAUSED:
        return "This queue is paused. Please try again shortly."
    if queue.session_date != local_today(queue.business):
        return "This queue has ended for the day."
    if queue.max_capacity is not None:
        if _count_tokens(db, queue.id, ACTIVE_TOKEN_STATUSES) >= queue.max_capacity:
            return "This queue is full. Please try again later."
    return None


# --------------------------------------------------------------------- sessions


def _close_and_cancel(db: Session, actor: User | None, queue: QueueSession) -> None:
    """Mark a session closed and cancel tokens that were still waiting (caller commits)."""
    now = _now()
    queue.status = QueueSessionStatus.CLOSED
    queue.closed_at = now
    queue.paused_at = None
    waiting = db.scalars(
        select(QueueToken).where(
            QueueToken.queue_session_id == queue.id, QueueToken.status.in_(CANCELLABLE_ON_CLOSE)
        )
    ).all()
    for token in waiting:
        token.status = TokenStatus.CANCELLED
        token.cancelled_at = now
        token.notes = "Cancelled because the queue closed."
        if token.customer_id:
            create_notification(
                db,
                user_id=token.customer_id,
                business_id=queue.business_id,
                notification_type=NotificationType.QUEUE_UPDATE,
                title="Queue closed",
                message=f"The {queue.service.name} queue at {queue.business.name} has closed, "
                f"so token {token.display_code} was cancelled.",
            )
    record_audit(db, action="queue.closed", actor=actor, business_id=queue.business_id,
                 entity_type="queue_session", entity_id=queue.id,
                 details={"cancelled_tokens": len(waiting)})


def open_queue(db: Session, actor: User, service_id: int, max_capacity: int | None) -> QueueSession:
    service = get_managed_service(db, actor, service_id, MemberRole.MANAGER)
    if not service.business.is_active:
        raise BadRequestError("Activate the business before opening a queue.")
    if not service.is_active:
        raise BadRequestError("Activate the service before opening a queue.")
    today = local_today(service.business)

    # Sessions from previous days that were never closed are closed now.
    stale = db.scalars(
        select(QueueSession).where(
            QueueSession.service_id == service.id,
            QueueSession.session_date < today,
            QueueSession.status != QueueSessionStatus.CLOSED,
        )
    ).all()
    for old_session in stale:
        _close_and_cancel(db, actor, old_session)

    capacity = max_capacity if max_capacity is not None else service.max_queue_capacity
    queue = get_todays_session(db, service)
    if queue is None:
        queue = QueueSession(
            business_id=service.business_id,
            service_id=service.id,
            session_date=today,
            status=QueueSessionStatus.OPEN,
            max_capacity=capacity,
            token_prefix=service.token_prefix,
            opened_by_id=actor.id,
        )
        db.add(queue)
        action = "queue.opened"
    elif queue.status == QueueSessionStatus.CLOSED:
        # Reopening keeps today's numbering so token codes stay unique for the day.
        queue.status = QueueSessionStatus.OPEN
        queue.closed_at = None
        queue.max_capacity = capacity
        action = "queue.reopened"
    else:
        raise ConflictError("Today's queue for this service is already open.")

    db.flush()
    record_audit(db, action=action, actor=actor, business_id=service.business_id,
                 entity_type="queue_session", entity_id=queue.id)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Today's queue for this service was just opened by someone else.") from exc
    return queue


def _manage_session(db: Session, actor: User, session_id: int) -> QueueSession:
    queue = get_session_or_404(db, session_id)
    require_business_role(db, actor, queue.business_id, MemberRole.MANAGER)
    return queue


def _change_status(
    db: Session,
    actor: User,
    queue: QueueSession,
    expected: tuple[QueueSessionStatus, ...],
    values: dict,
    action: str,
) -> QueueSession:
    if queue.status not in expected:
        raise ConflictError(f"The queue is {queue.status.value.lower()}; it cannot be {action}.")
    if not compare_and_set(db, QueueSession, queue.id, expected, values):
        db.rollback()
        raise ConflictError("The queue was changed by someone else. Refresh and try again.")
    record_audit(db, action=f"queue.{action}", actor=actor, business_id=queue.business_id,
                 entity_type="queue_session", entity_id=queue.id)
    db.commit()
    db.refresh(queue)
    return queue


def pause_queue(db: Session, actor: User, session_id: int) -> QueueSession:
    queue = _manage_session(db, actor, session_id)
    return _change_status(
        db, actor, queue, (QueueSessionStatus.OPEN,),
        {"status": QueueSessionStatus.PAUSED, "paused_at": _now()}, "paused",
    )


def resume_queue(db: Session, actor: User, session_id: int) -> QueueSession:
    queue = _manage_session(db, actor, session_id)
    if queue.session_date != local_today(queue.business):
        raise BadRequestError("This queue is from a previous day. Open today's queue instead.")
    return _change_status(
        db, actor, queue, (QueueSessionStatus.PAUSED,),
        {"status": QueueSessionStatus.OPEN, "paused_at": None}, "resumed",
    )


def close_queue(db: Session, actor: User, session_id: int) -> QueueSession:
    queue = _manage_session(db, actor, session_id)
    if queue.status == QueueSessionStatus.CLOSED:
        raise ConflictError("The queue is already closed.")
    _close_and_cancel(db, actor, queue)
    db.commit()
    return queue


def update_queue(db: Session, actor: User, session_id: int, max_capacity: int | None) -> QueueSession:
    queue = _manage_session(db, actor, session_id)
    if queue.status == QueueSessionStatus.CLOSED:
        raise ConflictError("A closed queue cannot be changed.")
    queue.max_capacity = max_capacity
    record_audit(db, action="queue.capacity_changed", actor=actor, business_id=queue.business_id,
                 entity_type="queue_session", entity_id=queue.id,
                 details={"max_capacity": max_capacity})
    db.commit()
    return queue


# ------------------------------------------------------------------- read models


def build_summary(db: Session, queue: QueueSession) -> QueueSummary:
    waiting = _count_tokens(db, queue.id, (TokenStatus.WAITING,))
    active = _count_tokens(db, queue.id, ACTIVE_TOKEN_STATUSES)
    at_counters = db.scalars(
        select(QueueToken)
        .options(selectinload(QueueToken.counter))
        .where(
            QueueToken.queue_session_id == queue.id,
            QueueToken.status.in_(AT_COUNTER_TOKEN_STATUSES),
        )
        .order_by(QueueToken.called_at.desc())
    ).all()
    blocker = joining_blocker(db, queue)
    is_full = queue.max_capacity is not None and active >= queue.max_capacity
    estimate = (
        estimate_for_session(db, queue, people_ahead=waiting)
        if queue.status != QueueSessionStatus.CLOSED
        else None
    )
    return QueueSummary(
        **session_read(queue).model_dump(),
        waiting_count=waiting,
        active_count=active,
        is_full=is_full,
        accepting_customers=blocker is None,
        not_accepting_reason=blocker,
        now_serving=[
            NowServing(
                display_code=token.display_code,
                counter_name=token.counter.name if token.counter else None,
                status=token.status,
            )
            for token in at_counters
        ],
        estimate_for_new_customer=estimate,
    )


def get_queue_summary(db: Session, viewer: User | None, session_id: int) -> QueueSummary:
    queue = get_session_or_404(db, session_id)
    if not queue.business.is_active and not has_business_role(db, viewer, queue.business_id):
        raise NotFoundError("Queue not found.")
    return build_summary(db, queue)


def list_active_queues(
    db: Session, business_id: int | None, service_id: int | None
) -> list[QueueSummary]:
    """Today's open or paused queues of active businesses and services (public)."""
    query = (
        select(QueueSession)
        .join(Business, Business.id == QueueSession.business_id)
        .join(Service, Service.id == QueueSession.service_id)
        .where(
            QueueSession.status != QueueSessionStatus.CLOSED,
            Business.is_active.is_(True),
            Service.is_active.is_(True),
        )
        .order_by(Service.name)
    )
    if business_id is not None:
        query = query.where(QueueSession.business_id == business_id)
    if service_id is not None:
        query = query.where(QueueSession.service_id == service_id)
    sessions = db.scalars(query).all()
    # "Today" depends on each business's timezone, so stale sessions are filtered here.
    return [
        build_summary(db, queue)
        for queue in sessions
        if queue.session_date == local_today(queue.business)
    ]


def list_business_sessions(
    db: Session, actor: User, business_id: int, include_closed: bool, limit: int, offset: int
) -> tuple[list[QueueSessionRead], int]:
    require_business_role(db, actor, business_id, MemberRole.STAFF)
    query = select(QueueSession).where(QueueSession.business_id == business_id)
    if not include_closed:
        query = query.where(QueueSession.status != QueueSessionStatus.CLOSED)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    sessions = db.scalars(
        query.order_by(QueueSession.session_date.desc(), QueueSession.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [session_read(queue) for queue in sessions], total


def list_session_tokens(db: Session, actor: User, session_id: int) -> list[StaffTokenRead]:
    queue = get_session_or_404(db, session_id)
    require_business_role(db, actor, queue.business_id, MemberRole.STAFF)
    tokens = db.scalars(
        select(QueueToken)
        .options(*TOKEN_LOAD_OPTIONS)
        .where(QueueToken.queue_session_id == queue.id)
        .order_by(QueueToken.token_number)
    ).all()
    return [staff_token_read(token) for token in tokens]


def token_position(db: Session, token: QueueToken) -> int | None:
    """1-based place in the waiting line; None if the token is no longer waiting."""
    if token.status != TokenStatus.WAITING:
        return None
    ahead = db.scalar(
        select(func.count(QueueToken.id)).where(
            QueueToken.queue_session_id == token.queue_session_id,
            QueueToken.status == TokenStatus.WAITING,
            QueueToken.token_number < token.token_number,
        )
    ) or 0
    return ahead + 1


def token_detail(db: Session, token: QueueToken) -> TokenDetail:
    position = token_position(db, token)
    estimate = (
        estimate_for_session(db, token.queue_session, people_ahead=position - 1)
        if position is not None
        else None
    )
    return TokenDetail(**token_read(token).model_dump(), position=position, estimate=estimate)


# ------------------------------------------------------------------ allocation


def allocate_token(
    db: Session,
    queue: QueueSession,
    *,
    customer: User | None = None,
    guest_name: str | None = None,
    guest_phone: str | None = None,
) -> QueueToken:
    """Reserve the next number and insert the token. The caller commits."""
    blocker = joining_blocker(db, queue)
    if blocker:
        raise BadRequestError(blocker)
    if customer is not None and _active_token_for(db, queue.id, customer.id):
        raise ConflictError(DUPLICATE_TOKEN_MESSAGE)

    allocated = db.execute(
        update(QueueSession)
        .where(QueueSession.id == queue.id, QueueSession.status == QueueSessionStatus.OPEN)
        .values(next_token_number=QueueSession.next_token_number + 1)
        .returning(QueueSession.next_token_number)
        .execution_options(synchronize_session=False)
    ).scalar_one_or_none()
    if allocated is None:
        db.rollback()
        raise BadRequestError("This queue is not accepting customers right now.")

    # This transaction now holds the session's write lock: the checks below cannot
    # interleave with another join for the same queue.
    try:
        if queue.max_capacity is not None:
            if _count_tokens(db, queue.id, ACTIVE_TOKEN_STATUSES) >= queue.max_capacity:
                raise ConflictError("This queue is full. Please try again later.")
        if customer is not None and _active_token_for(db, queue.id, customer.id):
            raise ConflictError(DUPLICATE_TOKEN_MESSAGE)
        token = QueueToken(
            queue_session_id=queue.id,
            token_number=allocated - 1,
            customer_id=customer.id if customer else None,
            guest_name=guest_name,
            guest_phone=guest_phone,
            status=TokenStatus.WAITING,
        )
        db.add(token)
        db.flush()
    except ConflictError:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(DUPLICATE_TOKEN_MESSAGE) from exc

    db.refresh(queue)
    return token


def _describe_estimate(detail: TokenDetail) -> str:
    if detail.estimate is None or detail.estimate.minutes is None:
        return ""
    return f" Estimated wait: about {detail.estimate.minutes} min (estimate, not a guarantee)."


def join_queue(db: Session, customer: User, session_id: int) -> TokenDetail:
    queue = get_session_or_404(db, session_id)
    token = allocate_token(db, queue, customer=customer)
    detail = token_detail(db, token)
    create_notification(
        db,
        user_id=customer.id,
        business_id=queue.business_id,
        notification_type=NotificationType.QUEUE_UPDATE,
        title=f"Token {token.display_code} confirmed",
        message=f"You joined the {queue.service.name} queue at {queue.business.name}. "
        f"You are number {detail.position} in line.{_describe_estimate(detail)}",
    )
    record_audit(db, action="token.created", actor=customer, business_id=queue.business_id,
                 entity_type="queue_token", entity_id=token.id,
                 details={"queue_session_id": queue.id, "token_number": token.token_number})
    db.commit()
    return detail


def add_walk_in(db: Session, actor: User, session_id: int, data: WalkInCreate) -> TokenDetail:
    queue = get_session_or_404(db, session_id)
    require_business_role(db, actor, queue.business_id, MemberRole.STAFF)
    token = allocate_token(
        db, queue, guest_name=data.guest_name.strip(), guest_phone=data.guest_phone
    )
    detail = token_detail(db, token)
    record_audit(db, action="token.walk_in_created", actor=actor, business_id=queue.business_id,
                 entity_type="queue_token", entity_id=token.id,
                 details={"queue_session_id": queue.id, "token_number": token.token_number})
    db.commit()
    return detail
