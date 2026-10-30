from enum import Enum

from sqlalchemy import Enum as SAEnum


class UserRole(str, Enum):
    """Platform-wide role; decides which dashboard a user gets."""

    SUPER_ADMIN = "SUPER_ADMIN"
    BUSINESS_OWNER = "BUSINESS_OWNER"
    STAFF = "STAFF"
    CUSTOMER = "CUSTOMER"


class MemberRole(str, Enum):
    """Role a user holds inside one specific business."""

    OWNER = "OWNER"
    MANAGER = "MANAGER"
    STAFF = "STAFF"


class BusinessCategory(str, Enum):
    BANK = "BANK"
    SALON = "SALON"
    GOVERNMENT = "GOVERNMENT"
    REPAIR_CENTER = "REPAIR_CENTER"
    SERVICE_CENTER = "SERVICE_CENTER"
    CLINIC = "CLINIC"
    CUSTOMER_SERVICE = "CUSTOMER_SERVICE"
    OTHER = "OTHER"


class QueueSessionStatus(str, Enum):
    OPEN = "OPEN"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


class TokenStatus(str, Enum):
    WAITING = "WAITING"
    CALLED = "CALLED"
    SERVING = "SERVING"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


class AppointmentStatus(str, Enum):
    BOOKED = "BOOKED"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


class NotificationType(str, Enum):
    GENERAL = "GENERAL"
    MEMBERSHIP = "MEMBERSHIP"
    QUEUE_UPDATE = "QUEUE_UPDATE"
    APPOINTMENT = "APPOINTMENT"


def enum_column(enum_class: type[Enum]) -> SAEnum:
    """Portable enum column: stored as VARCHAR + CHECK, works on SQLite and PostgreSQL."""
    return SAEnum(
        enum_class,
        native_enum=False,
        validate_strings=True,
        length=32,
        name=enum_class.__name__.lower(),
    )


class CounterStatus(str, Enum):
    """Derived from counter activity, never stored (so it cannot drift out of sync)."""

    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"


# Tokens that still occupy a place in the queue.
ACTIVE_TOKEN_STATUSES = (
    TokenStatus.WAITING,
    TokenStatus.CALLED,
    TokenStatus.SERVING,
    TokenStatus.SKIPPED,
)
# Tokens currently being handled at a counter.
AT_COUNTER_TOKEN_STATUSES = (TokenStatus.CALLED, TokenStatus.SERVING)
# Appointments that still hold their slot.
ACTIVE_APPOINTMENT_STATUSES = (
    AppointmentStatus.BOOKED,
    AppointmentStatus.CONFIRMED,
    AppointmentStatus.CHECKED_IN,
)


def status_in_clause(column: str, statuses: tuple[Enum, ...]) -> str:
    """SQL predicate for partial indexes, e.g. "status IN ('WAITING', 'CALLED')"."""
    values = ", ".join(f"'{status.value}'" for status in statuses)
    return f"{column} IN ({values})"
