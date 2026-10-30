import pytest

from app.services.wait_time import estimate_wait_minutes


@pytest.mark.parametrize(
    ("ahead", "average", "counters", "busy", "expected"),
    [
        (0, 10, 1, 0, 0),      # free desk: served immediately
        (0, 10, 1, 1, 5),      # next in line, desk busy: ~half a service
        (3, 10, 1, 1, 35),     # 5 for the current customer + 3 full services
        (4, 10, 2, 0, 20),     # two desks, four ahead: two rounds
        (1, 10, 2, 0, 0),      # second desk is free
        (2, 10, 2, 2, 15),     # both busy, two ahead on two desks
        (5, 12.5, 3, 1, 19),   # fractional averages round up
    ],
)
def test_estimate_formula(ahead, average, counters, busy, expected):
    assert estimate_wait_minutes(ahead, average, counters, busy) == expected


def test_no_counters_means_no_estimate():
    assert estimate_wait_minutes(3, 10, 0, 0) is None


def test_history_replaces_configured_duration(client, db, queue_setup, make_user):
    """With enough completed services, the real average is used instead of the configured one."""
    from datetime import datetime, timedelta, timezone

    from app.models import QueueToken, TokenStatus
    from tests.conftest import API

    now = datetime.now(timezone.utc)
    queue_id = queue_setup["queue"]["id"]
    for number in range(1, 6):
        db.add(QueueToken(
            queue_session_id=queue_id, token_number=900 + number, status=TokenStatus.COMPLETED,
            service_started_at=now - timedelta(minutes=8), completed_at=now,
        ))
    db.commit()

    summary = client.get(f"{API}/queues/{queue_id}").json()
    estimate = summary["estimate_for_new_customer"]
    assert estimate["basis"] == "history"
    assert estimate["average_service_minutes"] == 8.0
