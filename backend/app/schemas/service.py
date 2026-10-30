from datetime import datetime
from typing import Annotated, ClassVar

from pydantic import AfterValidator, BaseModel, Field

from app.models import CounterStatus, TokenStatus
from app.schemas.common import DayHours, ORMModel, OptionalText, PartialUpdateModel, WeeklyHours


def _normalize_prefix(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().upper()
    if not value.isalpha() or not 1 <= len(value) <= 3:
        raise ValueError("Token prefix must be 1-3 letters, e.g. 'A'.")
    return value


TokenPrefix = Annotated[str, AfterValidator(_normalize_prefix)]


class ServiceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: OptionalText = Field(default=None, max_length=2000)
    estimated_duration_minutes: int = Field(ge=1, le=480)
    max_queue_capacity: int | None = Field(default=None, ge=1, le=10000)
    is_active: bool = True
    is_available: bool = True
    operating_hours: WeeklyHours | None = None
    token_prefix: TokenPrefix = "A"
    appointments_enabled: bool = False
    appointment_duration_minutes: int | None = Field(default=None, ge=5, le=480)
    appointment_slot_capacity: int = Field(default=1, ge=1, le=50)
    appointment_daily_capacity: int | None = Field(default=None, ge=1, le=1000)
    appointment_hours: WeeklyHours | None = None


class ServiceUpdate(PartialUpdateModel):
    non_nullable_fields: ClassVar[frozenset[str]] = frozenset(
        {
            "name",
            "estimated_duration_minutes",
            "is_active",
            "is_available",
            "token_prefix",
            "appointments_enabled",
            "appointment_slot_capacity",
        }
    )

    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: OptionalText = Field(default=None, max_length=2000)
    estimated_duration_minutes: int | None = Field(default=None, ge=1, le=480)
    max_queue_capacity: int | None = Field(default=None, ge=1, le=10000)
    is_active: bool | None = None
    is_available: bool | None = None
    operating_hours: WeeklyHours | None = None
    token_prefix: Annotated[str | None, AfterValidator(_normalize_prefix)] = None
    appointments_enabled: bool | None = None
    appointment_duration_minutes: int | None = Field(default=None, ge=5, le=480)
    appointment_slot_capacity: int | None = Field(default=None, ge=1, le=50)
    appointment_daily_capacity: int | None = Field(default=None, ge=1, le=1000)
    appointment_hours: WeeklyHours | None = None


class ServiceRead(ORMModel):
    id: int
    business_id: int
    name: str
    description: str | None
    estimated_duration_minutes: int
    max_queue_capacity: int | None
    is_active: bool
    is_available: bool
    operating_hours: list[DayHours] | None
    token_prefix: str
    appointments_enabled: bool
    appointment_duration_minutes: int | None
    appointment_slot_capacity: int
    appointment_daily_capacity: int | None
    appointment_hours: list[DayHours] | None
    created_at: datetime
    updated_at: datetime


class ServiceStats(BaseModel):
    service_id: int
    total_counters: int
    active_counters: int
    tokens_today: int
    tokens_waiting: int
    tokens_completed_today: int
    average_service_minutes: float | None = Field(
        description="Mean serving time of tokens completed in the last 30 days"
    )
    upcoming_appointments: int


class CounterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    is_active: bool = True
    assigned_member_id: int | None = None


class CounterUpdate(PartialUpdateModel):
    non_nullable_fields: ClassVar[frozenset[str]] = frozenset({"name", "is_active", "service_id"})

    name: str | None = Field(default=None, min_length=1, max_length=60)
    is_active: bool | None = None
    assigned_member_id: int | None = None
    # Move the counter to another service of the same business.
    service_id: int | None = None


class CounterTokenBrief(BaseModel):
    id: int
    display_code: str
    status: TokenStatus


class CounterRead(BaseModel):
    id: int
    service_id: int
    service_name: str
    business_id: int
    name: str
    is_active: bool
    status: CounterStatus
    assigned_member_id: int | None
    assigned_member_name: str | None
    current_token: CounterTokenBrief | None
    created_at: datetime
    updated_at: datetime
