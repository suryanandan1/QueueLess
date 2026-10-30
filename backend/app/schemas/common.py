import re
from datetime import time
from typing import Annotated, Any, ClassVar, Generic, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T")

PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9\s\-()]{6,19}$")


def _validate_phone(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if not PHONE_PATTERN.match(value):
        raise ValueError("Enter a valid phone number (digits, spaces, dashes, optional leading +).")
    return value


def _strip(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


PhoneNumber = Annotated[str | None, AfterValidator(_validate_phone)]
OptionalText = Annotated[str | None, AfterValidator(_strip)]


def _validate_password(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 bytes long.")
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must contain at least one letter and one number.")
    return value


Password = Annotated[str, AfterValidator(_validate_password)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PartialUpdateModel(BaseModel):
    """Base for PATCH payloads: unset fields are ignored, explicit nulls are rejected
    for fields listed in `non_nullable_fields`."""

    non_nullable_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _reject_explicit_nulls(self):
        for field_name in self.non_nullable_fields & self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"'{field_name}' cannot be null.")
        return self

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class DayHours(BaseModel):
    """Opening hours for one weekday. day_of_week: 0 = Monday ... 6 = Sunday."""

    day_of_week: int = Field(ge=0, le=6)
    is_closed: bool = False
    open_time: time | None = None
    close_time: time | None = None

    @model_validator(mode="after")
    def _check_times(self):
        if self.is_closed:
            self.open_time = None
            self.close_time = None
            return self
        if self.open_time is None or self.close_time is None:
            raise ValueError("open_time and close_time are required unless the day is closed.")
        if self.open_time >= self.close_time:
            raise ValueError("open_time must be earlier than close_time.")
        return self


def _validate_week(days: list[DayHours] | None) -> list[DayHours] | None:
    if days is None:
        return None
    seen = [day.day_of_week for day in days]
    if len(seen) != len(set(seen)):
        raise ValueError("Each day_of_week may appear only once.")
    return sorted(days, key=lambda day: day.day_of_week)


WeeklyHours = Annotated[list[DayHours], AfterValidator(_validate_week)]


def serialize_hours(days: list[DayHours] | None) -> list[dict[str, Any]] | None:
    if days is None:
        return None
    return [day.model_dump(mode="json") for day in days]


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class Message(BaseModel):
    message: str
