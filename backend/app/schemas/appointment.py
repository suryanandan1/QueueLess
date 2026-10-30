from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.models import AppointmentStatus
from app.schemas.common import OptionalText


class AppointmentSlot(BaseModel):
    start: datetime
    end: datetime
    remaining: int
    is_available: bool


class AppointmentSlotDay(BaseModel):
    service_id: int
    date: date
    timezone: str
    duration_minutes: int
    daily_capacity: int | None
    daily_remaining: int | None
    slots: list[AppointmentSlot]


class AppointmentCreate(BaseModel):
    service_id: int
    scheduled_start: datetime
    notes: OptionalText = Field(default=None, max_length=1000)

    @field_validator("scheduled_start")
    @classmethod
    def _require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("scheduled_start must include a timezone offset (e.g. Z or +05:30).")
        return value


class AppointmentCancel(BaseModel):
    reason: OptionalText = Field(default=None, max_length=500)


class AppointmentRead(BaseModel):
    id: int
    service_id: int
    service_name: str
    business_id: int
    business_name: str
    business_timezone: str
    customer_id: int
    customer_name: str
    customer_email: str
    customer_phone: str | None
    scheduled_start: datetime
    scheduled_end: datetime
    status: AppointmentStatus
    notes: str | None
    cancellation_reason: str | None
    created_at: datetime
    confirmed_at: datetime | None
    checked_in_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
