from datetime import datetime
from typing import Annotated, ClassVar
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel, EmailStr, Field

from app.models import BusinessCategory, MemberRole
from app.schemas.common import (
    DayHours,
    ORMModel,
    OptionalText,
    PartialUpdateModel,
    PhoneNumber,
    WeeklyHours,
)


def _validate_timezone(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Unknown timezone '{value}'. Use an IANA name like 'Asia/Kolkata'.") from exc
    return value


TimezoneName = Annotated[str, AfterValidator(_validate_timezone)]


class BusinessFields(BaseModel):
    description: OptionalText = Field(default=None, max_length=2000)
    email: EmailStr | None = None
    phone: PhoneNumber = None
    address_line: OptionalText = Field(default=None, max_length=255)
    city: OptionalText = Field(default=None, max_length=100)
    state: OptionalText = Field(default=None, max_length=100)
    postal_code: OptionalText = Field(default=None, max_length=20)
    country: OptionalText = Field(default=None, max_length=100)


class BusinessCreate(BusinessFields):
    name: str = Field(min_length=2, max_length=150)
    category: BusinessCategory = BusinessCategory.OTHER
    timezone: TimezoneName = "UTC"
    working_hours: WeeklyHours = Field(default_factory=list)


class BusinessUpdate(BusinessFields, PartialUpdateModel):
    non_nullable_fields: ClassVar[frozenset[str]] = frozenset({"name", "category", "timezone"})

    name: str | None = Field(default=None, min_length=2, max_length=150)
    category: BusinessCategory | None = None
    timezone: Annotated[str | None, AfterValidator(_validate_timezone)] = None


class WorkingHoursUpdate(BaseModel):
    working_hours: WeeklyHours


class BusinessStatusUpdate(BaseModel):
    is_active: bool


class BusinessRead(ORMModel):
    id: int
    name: str
    slug: str
    description: str | None
    category: BusinessCategory
    email: str | None
    phone: str | None
    address_line: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    country: str | None
    timezone: str
    working_hours: list[DayHours]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MyBusinessRead(BaseModel):
    membership_id: int
    role: MemberRole
    business: BusinessRead


class BusinessStats(BaseModel):
    business_id: int
    total_services: int
    active_services: int
    total_counters: int
    active_counters: int
    active_members: int
    tokens_today: int
    tokens_waiting: int
    tokens_completed_today: int
    upcoming_appointments: int
