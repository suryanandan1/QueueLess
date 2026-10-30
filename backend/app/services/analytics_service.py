from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    ACTIVE_APPOINTMENT_STATUSES,
    Appointment,
    AppointmentStatus,
    MemberRole,
    QueueSession,
    QueueToken,
    Service,
    TokenStatus,
    User,
)
from app.schemas.analytics import (
    AppointmentMetrics,
    BusinessAnalytics,
    DailyQueueMetrics,
    ServiceMetrics,
)
from app.services.access_control import require_business_role
from app.services.business_service import local_today


def _mean_minutes(pairs: list[tuple[datetime | None, datetime | None]]) -> float | None:
    values = [(end - start).total_seconds() / 60 for start, end in pairs if start and end]
    return round(sum(values) / len(values), 1) if values else None


def _rate(part: int, whole: int) -> float | None:
    return round(part / whole, 3) if whole else None


def get_business_analytics(db: Session, actor: User, business_id: int, days: int) -> BusinessAnalytics:
    """Queue and appointment metrics for the last `days` local days (today included).

    Aggregation happens in Python: per-business volumes are small and this keeps
    the date arithmetic portable between SQLite and PostgreSQL.
    """
    business = require_business_role(db, actor, business_id, MemberRole.MANAGER)
    end_date = local_today(business)
    start_date = end_date - timedelta(days=days - 1)

    tokens = db.scalars(
        select(QueueToken)
        .join(QueueSession)
        .options(selectinload(QueueToken.queue_session))
        .where(
            QueueSession.business_id == business_id,
            QueueSession.session_date >= start_date,
            QueueSession.session_date <= end_date,
        )
    ).all()

    daily = []
    for offset in range(days):
        day = start_date + timedelta(days=offset)
        day_tokens = [t for t in tokens if t.queue_session.session_date == day]
        daily.append(
            DailyQueueMetrics(
                date=day,
                tokens_issued=len(day_tokens),
                completed=sum(t.status == TokenStatus.COMPLETED for t in day_tokens),
                cancelled=sum(t.status == TokenStatus.CANCELLED for t in day_tokens),
                no_show=sum(t.status == TokenStatus.NO_SHOW for t in day_tokens),
                average_wait_minutes=_mean_minutes([(t.joined_at, t.called_at) for t in day_tokens]),
                average_service_minutes=_mean_minutes(
                    [(t.service_started_at, t.completed_at) for t in day_tokens]
                ),
            )
        )

    services = db.scalars(
        select(Service).where(Service.business_id == business_id).order_by(Service.name)
    ).all()
    per_service = []
    for service in services:
        service_tokens = [t for t in tokens if t.queue_session.service_id == service.id]
        per_service.append(
            ServiceMetrics(
                service_id=service.id,
                service_name=service.name,
                tokens_issued=len(service_tokens),
                completed=sum(t.status == TokenStatus.COMPLETED for t in service_tokens),
                average_wait_minutes=_mean_minutes(
                    [(t.joined_at, t.called_at) for t in service_tokens]
                ),
                average_service_minutes=_mean_minutes(
                    [(t.service_started_at, t.completed_at) for t in service_tokens]
                ),
            )
        )

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=days)
    appointments = db.scalars(
        select(Appointment)
        .join(Service)
        .where(Service.business_id == business_id, Appointment.scheduled_start >= window_start)
    ).all()
    appointment_metrics = AppointmentMetrics(
        total=sum(a.scheduled_start <= now for a in appointments),
        completed=sum(a.status == AppointmentStatus.COMPLETED for a in appointments),
        cancelled=sum(a.status == AppointmentStatus.CANCELLED for a in appointments),
        no_show=sum(a.status == AppointmentStatus.NO_SHOW for a in appointments),
        upcoming=sum(
            a.scheduled_start > now and a.status in ACTIVE_APPOINTMENT_STATUSES for a in appointments
        ),
    )

    finished = [
        t for t in tokens
        if t.status in (TokenStatus.COMPLETED, TokenStatus.NO_SHOW, TokenStatus.CANCELLED)
    ]
    return BusinessAnalytics(
        business_id=business_id,
        start_date=start_date,
        end_date=end_date,
        days=daily,
        services=per_service,
        appointments=appointment_metrics,
        total_tokens=len(tokens),
        completion_rate=_rate(sum(t.status == TokenStatus.COMPLETED for t in finished), len(finished)),
        no_show_rate=_rate(sum(t.status == TokenStatus.NO_SHOW for t in finished), len(finished)),
    )
