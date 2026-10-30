from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UTCDateTime, utc_now
from app.models.enums import (
    ACTIVE_TOKEN_STATUSES,
    AT_COUNTER_TOKEN_STATUSES,
    QueueSessionStatus,
    TokenStatus,
    enum_column,
    status_in_clause,
)

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.service import Counter, Service
    from app.models.user import User

_ACTIVE_TOKEN = text(status_in_clause("status", ACTIVE_TOKEN_STATUSES))
_AT_COUNTER = text(status_in_clause("status", AT_COUNTER_TOKEN_STATUSES))


class QueueSession(TimestampMixin, Base):
    """One day's queue for one service.

    business_id duplicates service.business_id on purpose: every queue query is
    scoped by business, and this avoids a join on the hottest code path.
    next_token_number is the allocation counter; it is only ever changed with an
    atomic UPDATE (see queue_service.allocate_token).
    """

    __tablename__ = "queue_sessions"
    __table_args__ = (
        UniqueConstraint("service_id", "session_date"),
        Index("ix_queue_sessions_business_date", "business_id", "session_date"),
        CheckConstraint("max_capacity IS NULL OR max_capacity > 0", name="positive_capacity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    # Local calendar date in the business's timezone.
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[QueueSessionStatus] = mapped_column(
        enum_column(QueueSessionStatus), default=QueueSessionStatus.OPEN, nullable=False
    )
    next_token_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # Maximum number of active (unfinished) tokens; None means unlimited.
    max_capacity: Mapped[int | None] = mapped_column(Integer)
    # Copied from the service when the session opens so old tokens keep their codes.
    token_prefix: Mapped[str] = mapped_column(
        String(3), default="A", server_default="A", nullable=False
    )
    opened_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    paused_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    opened_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    business: Mapped["Business"] = relationship()
    service: Mapped["Service"] = relationship(back_populates="queue_sessions")
    tokens: Mapped[list["QueueToken"]] = relationship(
        back_populates="queue_session", cascade="all, delete-orphan"
    )

    def format_code(self, token_number: int) -> str:
        return f"{self.token_prefix}{token_number:03d}"


class QueueToken(TimestampMixin, Base):
    __tablename__ = "queue_tokens"
    __table_args__ = (
        UniqueConstraint("queue_session_id", "token_number"),
        Index("ix_queue_tokens_session_status", "queue_session_id", "status"),
        # A customer may hold only one unfinished token per session.
        Index(
            "uq_queue_tokens_active_customer",
            "queue_session_id",
            "customer_id",
            unique=True,
            sqlite_where=_ACTIVE_TOKEN,
            postgresql_where=_ACTIVE_TOKEN,
        ),
        # A counter handles at most one token at a time, and a token sits at one counter.
        Index(
            "uq_queue_tokens_counter_in_use",
            "counter_id",
            unique=True,
            sqlite_where=_AT_COUNTER,
            postgresql_where=_AT_COUNTER,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    queue_session_id: Mapped[int] = mapped_column(
        ForeignKey("queue_sessions.id", ondelete="CASCADE"), nullable=False
    )
    token_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Null for walk-in customers registered at the desk.
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    guest_name: Mapped[str | None] = mapped_column(String(120))
    guest_phone: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[TokenStatus] = mapped_column(
        enum_column(TokenStatus), default=TokenStatus.WAITING, nullable=False
    )
    # The counter that last handled the token (kept after completion for history).
    counter_id: Mapped[int | None] = mapped_column(ForeignKey("counters.id", ondelete="SET NULL"))
    served_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    recall_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    joined_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    called_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    service_started_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    skipped_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    no_show_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    # Set once the "your turn is approaching" notification has been sent.
    approaching_notified_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    queue_session: Mapped[QueueSession] = relationship(back_populates="tokens")
    customer: Mapped["User | None"] = relationship(foreign_keys=[customer_id])
    counter: Mapped["Counter | None"] = relationship()

    @property
    def display_code(self) -> str:
        return self.queue_session.format_code(self.token_number)
