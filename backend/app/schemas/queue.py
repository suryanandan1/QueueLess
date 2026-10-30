from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models import QueueSessionStatus, TokenStatus
from app.schemas.common import PartialUpdateModel, PhoneNumber
from app.schemas.service import CounterRead


class WaitEstimate(BaseModel):
    """An estimate, not a guarantee. `minutes` is None when no honest estimate exists."""

    minutes: int | None
    people_ahead: int
    average_service_minutes: float
    active_counters: int
    basis: Literal["history", "configured"] = Field(
        description="'history' = average of recent completed services; "
        "'configured' = the service's configured duration"
    )
    note: str | None = None


class QueueOpenRequest(BaseModel):
    service_id: int
    # Defaults to the service's max_queue_capacity when omitted.
    max_capacity: int | None = Field(default=None, ge=1, le=10000)


class QueueUpdate(PartialUpdateModel):
    max_capacity: int | None = Field(default=None, ge=1, le=10000)


class QueueSessionRead(BaseModel):
    id: int
    business_id: int
    business_name: str
    service_id: int
    service_name: str
    session_date: date
    status: QueueSessionStatus
    max_capacity: int | None
    token_prefix: str
    tokens_issued: int
    opened_at: datetime
    paused_at: datetime | None
    closed_at: datetime | None
    created_at: datetime


class NowServing(BaseModel):
    display_code: str
    counter_name: str | None
    status: TokenStatus


class QueueSummary(QueueSessionRead):
    """Public view of a queue: counts and codes only, never customer details."""

    waiting_count: int
    active_count: int
    is_full: bool
    accepting_customers: bool
    not_accepting_reason: str | None
    now_serving: list[NowServing]
    estimate_for_new_customer: WaitEstimate | None


class WalkInCreate(BaseModel):
    guest_name: str = Field(min_length=1, max_length=120)
    guest_phone: PhoneNumber = None


class CallTokenRequest(BaseModel):
    counter_id: int


class RecallTokenRequest(BaseModel):
    # Needed when recalling a SKIPPED token to a different counter than before.
    counter_id: int | None = None


class TokenCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class TokenRead(BaseModel):
    id: int
    display_code: str
    token_number: int
    status: TokenStatus
    queue_session_id: int
    queue_status: QueueSessionStatus
    session_date: date
    service_id: int
    service_name: str
    business_id: int
    business_name: str
    customer_id: int | None
    customer_name: str | None
    is_walk_in: bool
    counter_id: int | None
    counter_name: str | None
    recall_count: int
    joined_at: datetime
    called_at: datetime | None
    service_started_at: datetime | None
    completed_at: datetime | None
    skipped_at: datetime | None
    no_show_at: datetime | None
    cancelled_at: datetime | None


class TokenDetail(TokenRead):
    # 1 = next in line. None once the token has left the waiting line.
    position: int | None
    estimate: WaitEstimate | None


class StaffTokenRead(TokenRead):
    """Token view for business staff; includes contact details."""

    customer_phone: str | None
    customer_email: str | None


class CounterConsole(BaseModel):
    counter: CounterRead
    queue: QueueSummary | None
    current_token: StaffTokenRead | None
    waiting: list[StaffTokenRead]
    skipped: list[StaffTokenRead]
    recently_completed: list[StaffTokenRead]

