from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.business import Business, BusinessMember
    from app.models.queue import QueueSession


class Service(TimestampMixin, Base):
    __tablename__ = "services"
    __table_args__ = (
        UniqueConstraint("business_id", "name"),
        CheckConstraint("estimated_duration_minutes > 0", name="positive_duration"),
        CheckConstraint(
            "max_queue_capacity IS NULL OR max_queue_capacity > 0", name="positive_capacity"
        ),
        CheckConstraint("appointment_slot_capacity > 0", name="positive_slot_capacity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    # Default capacity for new queue sessions; None means no limit.
    max_queue_capacity: Mapped[int | None] = mapped_column(Integer)
    # is_active=False archives the service (hidden from customers).
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), index=True, nullable=False
    )
    # is_available=False keeps the service listed but stops new customers joining.
    is_available: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
    # Same shape as Business.working_hours; None means "follow business hours".
    operating_hours: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    # Letter(s) shown before token numbers, e.g. "A" -> A001.
    token_prefix: Mapped[str] = mapped_column(
        String(3), default="A", server_default="A", nullable=False
    )

    appointments_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    # None means "use estimated_duration_minutes".
    appointment_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    # How many customers can book the same time slot.
    appointment_slot_capacity: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )
    # Maximum bookings per day; None means only slot capacity applies.
    appointment_daily_capacity: Mapped[int | None] = mapped_column(Integer)
    # Booking window; None falls back to operating_hours, then business hours.
    appointment_hours: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    # Incremented by every booking so concurrent bookings for this service are serialized.
    booking_version: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )

    business: Mapped["Business"] = relationship(back_populates="services")
    counters: Mapped[list["Counter"]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )
    queue_sessions: Mapped[list["QueueSession"]] = relationship(back_populates="service")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="service")


class Counter(TimestampMixin, Base):
    """A physical or virtual desk where customers of a service are served.

    Its AVAILABLE/BUSY/OFFLINE status is derived from is_active and the token it is
    currently handling (see counter_service), so it can never drift out of sync.
    """

    __tablename__ = "counters"
    __table_args__ = (UniqueConstraint("service_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
    assigned_member_id: Mapped[int | None] = mapped_column(
        ForeignKey("business_members.id", ondelete="SET NULL"), index=True
    )

    service: Mapped[Service] = relationship(back_populates="counters")
    assigned_member: Mapped["BusinessMember | None"] = relationship()
