"""Estimated waiting time.

The estimate models the service as `active_counters` parallel desks, each taking
`average_minutes` per customer:

* If a counter is free for this customer right now, the wait is 0.
* Otherwise they wait for the first desk to free up (half a service on average
  when desks are busy, a full service when the free desks were just taken by
  the people ahead), plus one full service per extra "round" of people ahead.

The average comes from real completed services when there is enough history,
otherwise from the service's configured duration.
"""

import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AT_COUNTER_TOKEN_STATUSES,
    Counter,
    QueueSession,
    QueueSessionStatus,
    QueueToken,
    Service,
    TokenStatus,
)
from app.schemas.queue import WaitEstimate

HISTORY_WINDOW_DAYS = 30
MIN_HISTORY_SAMPLES = 5


def recent_service_durations(db: Session, service_id: int, days: int = HISTORY_WINDOW_DAYS) -> list[float]:
    """Minutes spent serving each token completed for this service in the last `days`."""
    window_start = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(QueueToken.service_started_at, QueueToken.completed_at)
        .join(QueueSession)
        .where(
            QueueSession.service_id == service_id,
            QueueToken.status == TokenStatus.COMPLETED,
            QueueToken.service_started_at.is_not(None),
            QueueToken.completed_at >= window_start,
        )
    ).all()
    # Computed in Python to stay portable across SQLite and PostgreSQL date arithmetic.
    return [(done - started).total_seconds() / 60 for started, done in rows]


def average_service_minutes(db: Session, service: Service) -> tuple[float, str]:
    """Return (minutes, basis) where basis is 'history' or 'configured'."""
    durations = recent_service_durations(db, service.id)
    if len(durations) >= MIN_HISTORY_SAMPLES:
        return round(sum(durations) / len(durations), 1), "history"
    return float(service.estimated_duration_minutes), "configured"


def estimate_wait_minutes(
    people_ahead: int, average_minutes: float, active_counters: int, busy_counters: int
) -> int | None:
    if active_counters <= 0:
        return None
    busy_counters = min(busy_counters, active_counters)
    free_counters = active_counters - busy_counters
    if people_ahead < free_counters:
        return 0
    still_ahead = people_ahead - free_counters
    first_desk_frees_after = average_minutes / 2 if busy_counters else average_minutes
    rounds = still_ahead // active_counters
    return math.ceil(first_desk_frees_after + rounds * average_minutes)


def estimate_for_session(db: Session, queue: QueueSession, people_ahead: int) -> WaitEstimate:
    average, basis = average_service_minutes(db, queue.service)
    active_counters = db.scalar(
        select(func.count(Counter.id)).where(
            Counter.service_id == queue.service_id, Counter.is_active.is_(True)
        )
    ) or 0
    busy_counters = db.scalar(
        select(func.count(QueueToken.id)).where(
            QueueToken.queue_session_id == queue.id,
            QueueToken.status.in_(AT_COUNTER_TOKEN_STATUSES),
        )
    ) or 0

    estimate = WaitEstimate(
        minutes=None,
        people_ahead=people_ahead,
        average_service_minutes=average,
        active_counters=active_counters,
        basis=basis,
    )
    if queue.status == QueueSessionStatus.PAUSED:
        estimate.note = "The queue is paused. Waiting time will be estimated once serving resumes."
    elif queue.status == QueueSessionStatus.CLOSED:
        estimate.note = "The queue is closed."
    elif active_counters == 0:
        estimate.note = "No counters are open for this service right now, so no estimate is available."
    else:
        estimate.minutes = estimate_wait_minutes(people_ahead, average, active_counters, busy_counters)
        estimate.note = "This is an estimate, not a guarantee."
    return estimate
