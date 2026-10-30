"""Builders that turn ORM objects into API schemas for queue-related resources."""

from sqlalchemy.orm import selectinload

from app.models import Counter, CounterStatus, QueueSession, QueueToken
from app.schemas.queue import QueueSessionRead, StaffTokenRead, TokenRead
from app.schemas.service import CounterRead, CounterTokenBrief

# Eager-load everything token_read() touches, to avoid N+1 queries in lists.
TOKEN_LOAD_OPTIONS = (
    selectinload(QueueToken.queue_session).selectinload(QueueSession.service),
    selectinload(QueueToken.queue_session).selectinload(QueueSession.business),
    selectinload(QueueToken.counter),
    selectinload(QueueToken.customer),
)


def session_read(queue: QueueSession) -> QueueSessionRead:
    return QueueSessionRead(
        id=queue.id,
        business_id=queue.business_id,
        business_name=queue.business.name,
        service_id=queue.service_id,
        service_name=queue.service.name,
        session_date=queue.session_date,
        status=queue.status,
        max_capacity=queue.max_capacity,
        token_prefix=queue.token_prefix,
        tokens_issued=queue.next_token_number - 1,
        opened_at=queue.opened_at,
        paused_at=queue.paused_at,
        closed_at=queue.closed_at,
        created_at=queue.created_at,
    )


def _token_fields(token: QueueToken) -> dict:
    queue = token.queue_session
    return {
        "id": token.id,
        "display_code": token.display_code,
        "token_number": token.token_number,
        "status": token.status,
        "queue_session_id": queue.id,
        "queue_status": queue.status,
        "session_date": queue.session_date,
        "service_id": queue.service_id,
        "service_name": queue.service.name,
        "business_id": queue.business_id,
        "business_name": queue.business.name,
        "customer_id": token.customer_id,
        "customer_name": token.customer.full_name if token.customer else token.guest_name,
        "is_walk_in": token.customer_id is None,
        "counter_id": token.counter_id,
        "counter_name": token.counter.name if token.counter else None,
        "recall_count": token.recall_count,
        "joined_at": token.joined_at,
        "called_at": token.called_at,
        "service_started_at": token.service_started_at,
        "completed_at": token.completed_at,
        "skipped_at": token.skipped_at,
        "no_show_at": token.no_show_at,
        "cancelled_at": token.cancelled_at,
    }


def token_read(token: QueueToken) -> TokenRead:
    return TokenRead(**_token_fields(token))


def staff_token_read(token: QueueToken) -> StaffTokenRead:
    return StaffTokenRead(
        **_token_fields(token),
        customer_phone=token.customer.phone if token.customer else token.guest_phone,
        customer_email=token.customer.email if token.customer else None,
    )


def counter_read(counter: Counter, current_token: QueueToken | None) -> CounterRead:
    if not counter.is_active:
        status = CounterStatus.OFFLINE
    elif current_token is not None:
        status = CounterStatus.BUSY
    else:
        status = CounterStatus.AVAILABLE
    member = counter.assigned_member
    return CounterRead(
        id=counter.id,
        service_id=counter.service_id,
        service_name=counter.service.name,
        business_id=counter.service.business_id,
        name=counter.name,
        is_active=counter.is_active,
        status=status,
        assigned_member_id=counter.assigned_member_id,
        assigned_member_name=member.user.full_name if member else None,
        current_token=(
            CounterTokenBrief(
                id=current_token.id,
                display_code=current_token.display_code,
                status=current_token.status,
            )
            if current_token
            else None
        ),
        created_at=counter.created_at,
        updated_at=counter.updated_at,
    )
