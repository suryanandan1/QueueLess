from datetime import datetime
from typing import Annotated, ClassVar

from pydantic import AfterValidator, EmailStr, Field

from app.models import MemberRole
from app.schemas.common import ORMModel, PartialUpdateModel, Password, PhoneNumber
from app.schemas.user import NormalizedEmailModel, UserSummary


def _reject_owner_role(value: MemberRole | None) -> MemberRole | None:
    if value == MemberRole.OWNER:
        raise ValueError("The OWNER role cannot be assigned; only MANAGER or STAFF.")
    return value


AssignableRole = Annotated[MemberRole, AfterValidator(_reject_owner_role)]


class MemberCreate(NormalizedEmailModel):
    """Add an existing account by email, or create a staff account when
    full_name and password are supplied for an email that is not registered."""

    email: EmailStr
    role: AssignableRole = MemberRole.STAFF
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    password: Password | None = None
    phone: PhoneNumber = None


class MemberUpdate(PartialUpdateModel):
    non_nullable_fields: ClassVar[frozenset[str]] = frozenset({"role", "is_active"})

    role: AssignableRole | None = None
    is_active: bool | None = None


class MemberRead(ORMModel):
    id: int
    business_id: int
    role: MemberRole
    is_active: bool
    created_at: datetime
    user: UserSummary
