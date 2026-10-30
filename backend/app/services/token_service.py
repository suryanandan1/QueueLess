"""Token lifecycle: controlled status transitions performed by staff and customers.

    WAITING  -> CALLED (call / call-next), CANCELLED
    CALLED   -> SERVING (start), SKIPPED (skip), NO_SHOW, CALLED (recall)
    SKIPPED  -> CALLED (recall), NO_SHOW, CANCELLED
    SERVING  -> COMPLETED
    COMPLETED, CANCELLED, NO_SHOW are final.

Every transition is a compare-and-set UPDATE (see transitions.compare_and_set):
if two staff members act on the same token at the same moment, only one update
matches the expected status and the other gets a 409. A partial unique index
additionally guarantees a counter handles at most one CALLED/SERVING token.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models import (
    ACTIVE_TOKEN_STATUSES,
    AT_COUNTER_TOKEN_STATUSES,
    Counter,
    MemberRole,
    NotificationType,
    QueueSession,
    QueueSessionStatus,
    QueueToken,
    TokenStatus,
    User,
)
from app.schemas.queue import StaffTokenRead, TokenDetail, TokenRead
from app.services.access_control import get_active_membership, has_business_role
from app.services.audit_service import record_audit
from app.services.notification_service import create_notification
from app.services.queue_service import get_todays_session, token_detail
from app.services.queue_views import TOKEN_LOAD_OPTIONS, staff_token_read, token_read
from app.services.transitions import compare_and_set

ALLOWED_FROM: dict[str, tuple[TokenStatus, ...]] = {
    "call": (TokenStatus.WAITING,),
    "recall": (TokenStatus.CALLED, TokenStatus.SKIPPED),
    "start": (TokenStatus.CALLED,),
    "complete": (TokenStatus.SERVING,),
    "skip": (TokenStatus.CALLED,),
    "no_show": (TokenStatus.CALLED, TokenStatus.SKIPPED),
    "cancel": (TokenStatus.WAITING, TokenStatus.SKIPPED),
}
ACTION_LABELS = {
    "call": "call",
    "recall": "recall",
    "start": "start serving",
    "complete": "complete",
    "skip": "skip",
    "no_show": "mark as no-show",
    "cancel": "cancel",
}
# Waiting customers within this many places get an "approaching" notification.
APPROACHING_POSITIONS = 2
CALL_NEXT_ATTEMPTS = 3


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_token_or_404(db: Session, token_id: int) -> QueueToken:
    token = db.scalar(select(QueueToken).options(*TOKEN_LOAD_OPTIONS).where(QueueToken.id == token_id))
    if token is None:
        raise NotFoundError("Token not found.")
    return token


# --------------------------------------------------------------- authorization


def get_operable_counter(
    db: Session, actor: User, counter_id: int, service_id: int | None = None
) -> Counter:
    """A counter the actor may operate: managers/owners any counter of their business,
    staff only counters assigned to them."""
    counter = db.get(Counter, counter_id)
    if counter is None:
        raise NotFoundError("Counter not found.")
    business_id = counter.service.business_id
    if not has_business_role(db, actor, business_id, MemberRole.MANAGER):
        membership = get_active_membership(db, business_id, actor.id)
        if membership is None or counter.assigned_member_id != membership.id:
            raise PermissionDeniedError("You can only operate counters assigned to you.")
    if service_id is not None and counter.service_id != service_id:
        raise BadRequestError(f"{counter.name} does not serve this queue's service.")
    if not counter.is_active:
        raise BadRequestError(f"{counter.name} is offline. Activate it first.")
    return counter


def _require_service_operator(db: Session, actor: User, queue: QueueSession) -> None:
    """For actions not tied to a counter (e.g. on a skipped token): managers, or staff
    with an active counter assigned to them for this service."""
    if has_business_role(db, actor, queue.business_id, MemberRole.MANAGER):
        return
    membership = get_active_membership(db, queue.business_id, actor.id)
    has_counter = membership is not None and db.scalar(
        select(Counter.id).where(
            Counter.service_id == queue.service_id,
            Counter.assigned_member_id == membership.id,
            Counter.is_active.is_(True),
        )
    )
    if not has_counter:
        raise PermissionDeniedError("You are not assigned to a counter for this service.")


def _current_token_at(db: Session, counter_id: int) -> QueueToken | None:
    return db.scalar(
        select(QueueToken).where(
            QueueToken.counter_id == counter_id,
            QueueToken.status.in_(AT_COUNTER_TOKEN_STATUSES),
        )
    )


def _ensure_counter_free(db: Session, counter: Counter) -> None:
    current = _current_token_at(db, counter.id)
    if current is not None:
        raise ConflictError(
            f"{counter.name} is already handling token {current.display_code}. "
            "Complete, skip or mark it as no-show first."
        )


def _ensure_queue_open(queue: QueueSession) -> None:
    if queue.status != QueueSessionStatus.OPEN:
        raise BadRequestError(
            f"The queue is {queue.status.value.lower()}. Resume it before calling customers."
        )


# ----------------------------------------------------------------- transitions


def _apply(
    db: Session,
    token: QueueToken,
    action: str,
    values: dict[str, Any],
    expected: tuple[TokenStatus, ...] | None = None,
) -> TokenStatus:
    """Validate and atomically apply a transition. Returns the previous status."""
    expected = expected or ALLOWED_FROM[action]
    previous = token.status
    if previous not in expected:
        allowed = ", ".join(status.value for status in ALLOWED_FROM[action])
        raise ConflictError(
            f"Cannot {ACTION_LABELS[action]} token {token.display_code}: it is {previous.value}. "
            f"This is only possible from {allowed}."
        )
    try:
        updated = compare_and_set(db, QueueToken, token.id, expected, values)
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("That counter is already handling another token.") from exc
    if not updated:
        db.rollback()
        db.refresh(token)
        raise ConflictError(
            f"Token {token.display_code} was just updated by someone else "
            f"(now {token.status.value}). Refresh and try again."
        )
    db.refresh(token)
    return previous


def _audit_transition(
    db: Session, actor: User, token: QueueToken, action: str, previous: TokenStatus
) -> None:
    record_audit(
        db,
        action=f"token.{action}",
        actor=actor,
        business_id=token.queue_session.business_id,
        entity_type="queue_token",
        entity_id=token.id,
        details={"from": previous.value, "to": token.status.value, "counter_id": token.counter_id},
    )


def _notify(db: Session, token: QueueToken, title: str, message: str) -> None:
    if token.customer_id:
        create_notification(
            db,
            user_id=token.customer_id,
            business_id=token.queue_session.business_id,
            notification_type=NotificationType.QUEUE_UPDATE,
            title=title,
            message=message,
        )


def _notify_approaching(db: Session, queue: QueueSession) -> None:
    """Tell the next few waiting customers their turn is close (once per token)."""
    upcoming = db.scalars(
        select(QueueToken)
        .where(QueueToken.queue_session_id == queue.id, QueueToken.status == TokenStatus.WAITING)
        .order_by(QueueToken.token_number)
        .limit(APPROACHING_POSITIONS)
    ).all()
    for position, token in enumerate(upcoming, start=1):
        if token.approaching_notified_at is None and token.customer_id:
            token.approaching_notified_at = _now()
            _notify(
                db,
                token,
                "Your turn is approaching",
                f"Token {token.display_code}: you are number {position} in line for "
                f"{queue.service.name}. Please be ready.",
            )


def _after_called(db: Session, actor: User, token: QueueToken, action: str, previous: TokenStatus) -> None:
    counter_name = token.counter.name if token.counter else "the counter"
    _notify(
        db,
        token,
        f"Token {token.display_code} is being called",
        f"It's your turn! Please go to {counter_name} at {token.queue_session.business.name}.",
    )
    _notify_approaching(db, token.queue_session)
    _audit_transition(db, actor, token, action, previous)


def _staff_result(db: Session, token: QueueToken) -> StaffTokenRead:
    db.commit()
    return staff_token_read(get_token_or_404(db, token.id))


def call_token(db: Session, actor: User, token_id: int, counter_id: int) -> StaffTokenRead:
    token = get_token_or_404(db, token_id)
    queue = token.queue_session
    counter = get_operable_counter(db, actor, counter_id, queue.service_id)
    _ensure_queue_open(queue)
    _ensure_counter_free(db, counter)
    previous = _apply(
        db, token, "call",
        {"status": TokenStatus.CALLED, "counter_id": counter.id, "called_at": _now(),
         "served_by_id": actor.id},
    )
    _after_called(db, actor, token, "called", previous)
    return _staff_result(db, token)


def call_next(db: Session, actor: User, counter_id: int) -> StaffTokenRead:
    counter = get_operable_counter(db, actor, counter_id)
    queue = get_todays_session(db, counter.service)
    if queue is None:
        raise BadRequestError("There is no queue open today for this service.")
    _ensure_queue_open(queue)
    _ensure_counter_free(db, counter)

    for _attempt in range(CALL_NEXT_ATTEMPTS):
        candidate_ids = db.scalars(
            select(QueueToken.id)
            .where(QueueToken.queue_session_id == queue.id, QueueToken.status == TokenStatus.WAITING)
            .order_by(QueueToken.token_number)
            .limit(5)
        ).all()
        if not candidate_ids:
            raise NotFoundError("No customers are waiting.")
        for candidate_id in candidate_ids:
            values = {"status": TokenStatus.CALLED, "counter_id": counter.id,
                      "called_at": _now(), "served_by_id": actor.id}
            try:
                won = compare_and_set(db, QueueToken, candidate_id, (TokenStatus.WAITING,), values)
            except IntegrityError as exc:
                db.rollback()
                raise ConflictError(f"{counter.name} is already handling another token.") from exc
            # Another counter may have taken this token a moment ago; try the next one.
            if won:
                token = get_token_or_404(db, candidate_id)
                db.refresh(token)
                _after_called(db, actor, token, "called", TokenStatus.WAITING)
                return _staff_result(db, token)
    raise ConflictError("The queue is very busy right now. Please try again.")


def recall_token(db: Session, actor: User, token_id: int, counter_id: int | None) -> StaffTokenRead:
    token = get_token_or_404(db, token_id)
    queue = token.queue_session
    if token.status == TokenStatus.CALLED:
        get_operable_counter(db, actor, token.counter_id, queue.service_id)
        previous = _apply(
            db, token, "recall",
            {"called_at": _now(), "recall_count": QueueToken.recall_count + 1},
            expected=(TokenStatus.CALLED,),
        )
    elif token.status == TokenStatus.SKIPPED:
        target_counter_id = counter_id or token.counter_id
        if target_counter_id is None:
            raise BadRequestError("Choose a counter to recall this token to.")
        counter = get_operable_counter(db, actor, target_counter_id, queue.service_id)
        _ensure_queue_open(queue)
        _ensure_counter_free(db, counter)
        previous = _apply(
            db, token, "recall",
            {"status": TokenStatus.CALLED, "counter_id": counter.id, "called_at": _now(),
             "served_by_id": actor.id, "recall_count": QueueToken.recall_count + 1},
            expected=(TokenStatus.SKIPPED,),
        )
    else:
        previous = _apply(db, token, "recall", {})  # raises a clear transition error
    _after_called(db, actor, token, "recalled", previous)
    return _staff_result(db, token)


def _at_counter_action(
    db: Session, actor: User, token_id: int, action: str, values: dict[str, Any]
) -> tuple[QueueToken, TokenStatus]:
    token = get_token_or_404(db, token_id)
    if token.status in AT_COUNTER_TOKEN_STATUSES and token.counter_id is not None:
        get_operable_counter(db, actor, token.counter_id)
    else:
        _require_service_operator(db, actor, token.queue_session)
    previous = _apply(db, token, action, values)
    return token, previous


def start_service(db: Session, actor: User, token_id: int) -> StaffTokenRead:
    token, previous = _at_counter_action(
        db, actor, token_id, "start",
        {"status": TokenStatus.SERVING, "service_started_at": _now(), "served_by_id": actor.id},
    )
    _audit_transition(db, actor, token, "started", previous)
    return _staff_result(db, token)


def complete_service(db: Session, actor: User, token_id: int) -> StaffTokenRead:
    token, previous = _at_counter_action(
        db, actor, token_id, "complete",
        {"status": TokenStatus.COMPLETED, "completed_at": _now()},
    )
    _audit_transition(db, actor, token, "completed", previous)
    return _staff_result(db, token)


def skip_token(db: Session, actor: User, token_id: int) -> StaffTokenRead:
    token, previous = _at_counter_action(
        db, actor, token_id, "skip", {"status": TokenStatus.SKIPPED, "skipped_at": _now()}
    )
    _notify(
        db, token, f"Token {token.display_code} was skipped",
        "You were not at the counter when called. Please speak to the staff to be recalled.",
    )
    _audit_transition(db, actor, token, "skipped", previous)
    return _staff_result(db, token)


def mark_no_show(db: Session, actor: User, token_id: int) -> StaffTokenRead:
    token, previous = _at_counter_action(
        db, actor, token_id, "no_show", {"status": TokenStatus.NO_SHOW, "no_show_at": _now()}
    )
    _audit_transition(db, actor, token, "no_show", previous)
    return _staff_result(db, token)


def cancel_token(db: Session, actor: User, token_id: int, reason: str | None) -> TokenRead:
    token = get_token_or_404(db, token_id)
    by_customer = token.customer_id == actor.id
    if not by_customer:
        if not has_business_role(db, actor, token.queue_session.business_id, MemberRole.STAFF):
            raise NotFoundError("Token not found.")
        _require_service_operator(db, actor, token.queue_session)
    previous = _apply(
        db, token, "cancel",
        {"status": TokenStatus.CANCELLED, "cancelled_at": _now(), "notes": reason},
    )
    if not by_customer:
        _notify(
            db, token, f"Token {token.display_code} was cancelled",
            f"Your token for {token.queue_session.service.name} was cancelled by the business."
            + (f" Reason: {reason}" if reason else ""),
        )
    _audit_transition(db, actor, token, "cancelled", previous)
    db.commit()
    return token_read(get_token_or_404(db, token.id))


# ----------------------------------------------------------------------- reads


def get_token_for_viewer(db: Session, viewer: User, token_id: int) -> TokenDetail:
    """Customers see their own tokens; business staff see tokens of their business."""
    token = get_token_or_404(db, token_id)
    if token.customer_id != viewer.id and not has_business_role(
        db, viewer, token.queue_session.business_id, MemberRole.STAFF
    ):
        raise NotFoundError("Token not found.")
    return token_detail(db, token)


def list_my_tokens(
    db: Session, user: User, active_only: bool, limit: int, offset: int
) -> tuple[list[TokenDetail], int]:
    query = select(QueueToken).where(QueueToken.customer_id == user.id)
    if active_only:
        query = query.where(QueueToken.status.in_(ACTIVE_TOKEN_STATUSES))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    tokens = db.scalars(
        query.options(*TOKEN_LOAD_OPTIONS)
        .order_by(QueueToken.joined_at.desc(), QueueToken.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [token_detail(db, token) for token in tokens], total
