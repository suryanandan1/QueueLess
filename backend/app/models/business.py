from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin
from app.models.enums import BusinessCategory, MemberRole, enum_column

if TYPE_CHECKING:
    from app.models.service import Service
    from app.models.user import User


class Business(TimestampMixin, Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(170), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[BusinessCategory] = mapped_column(
        enum_column(BusinessCategory), default=BusinessCategory.OTHER, index=True, nullable=False
    )

    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    address_line: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100), index=True)
    state: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    country: Mapped[str | None] = mapped_column(String(100))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)

    # Weekly schedule: list of {day_of_week, is_closed, open_time, close_time}.
    # Validated by app.schemas.common.DayHours before it is stored.
    working_hours: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), index=True, nullable=False
    )

    members: Mapped[list["BusinessMember"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    services: Mapped[list["Service"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )


class BusinessMember(TimestampMixin, Base):
    """Links a user to a business with a business-scoped role."""

    __tablename__ = "business_members"
    __table_args__ = (UniqueConstraint("business_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[MemberRole] = mapped_column(
        enum_column(MemberRole), default=MemberRole.STAFF, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )

    business: Mapped[Business] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")
