from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UTCDateTime
from app.models.enums import (
    ACTIVE_APPOINTMENT_STATUSES,
    AppointmentStatus,
    enum_column,
    status_in_clause,
)

if TYPE_CHECKING:
    from app.models.queue import QueueToken
    from app.models.service import Service
    from app.models.user import User

_ACTIVE = text(status_in_clause("status", ACTIVE_APPOINTMENT_STATUSES))


class Appointment(TimestampMixin, Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index("ix_appointments_service_start", "service_id", "scheduled_start"),
        CheckConstraint("scheduled_end > scheduled_start", name="end_after_start"),
        # A customer cannot hold two live bookings for the same service slot.
        Index(
            "uq_appointments_active_customer_slot",
            "customer_id",
            "service_id",
            "scheduled_start",
            unique=True,
            sqlite_where=_ACTIVE,
            postgresql_where=_ACTIVE,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="RESTRICT"), nullable=False
    )
    scheduled_start: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    scheduled_end: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        enum_column(AppointmentStatus), default=AppointmentStatus.BOOKED, index=True, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)
    # Optional link if a future workflow converts a check-in into a queue token.
    queue_token_id: Mapped[int | None] = mapped_column(
        ForeignKey("queue_tokens.id", ondelete="SET NULL"), unique=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    checked_in_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    cancellation_reason: Mapped[str | None] = mapped_column(Text)

    customer: Mapped["User"] = relationship(back_populates="appointments")
    service: Mapped["Service"] = relationship(back_populates="appointments")
    queue_token: Mapped["QueueToken | None"] = relationship()
