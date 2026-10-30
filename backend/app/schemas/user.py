from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models import UserRole
from app.schemas.common import ORMModel, PartialUpdateModel, PhoneNumber


class NormalizedEmailModel(BaseModel):
    @field_validator("email", mode="after", check_fields=False)
    @classmethod
    def _lowercase_email(cls, value: str | None) -> str | None:
        return value.lower() if value else value


class UserRead(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    phone: str | None
    role: UserRole
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime


class UserSummary(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    phone: str | None
    role: UserRole


class UserUpdate(PartialUpdateModel):
    non_nullable_fields: ClassVar[frozenset[str]] = frozenset({"full_name"})

    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: PhoneNumber = None


class UserStatusUpdate(BaseModel):
    is_active: bool
