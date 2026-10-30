from datetime import date, datetime, timedelta, timezone

import pytest

from tests.conftest import API

BOOKING_HOURS = [
    {"day_of_week": day, "open_time": "09:00", "close_time": "12:00"} for day in range(7)
]


@pytest.fixture
def bookable(client, owner_headers, create_business, create_service):
    business = create_business(owner_headers, "Care Clinic", timezone="UTC")
    service = create_service(
        owner_headers,
        business["id"],
        "Consultation",
        appointments_enabled=True,
        appointment_duration_minutes=30,
        appointment_slot_capacity=1,
        appointment_hours=BOOKING_HOURS,
    )
    return {"business": business, "service": service, "owner": owner_headers}


def tomorrow() -> date:
    return datetime.now(timezone.utc).date() + timedelta(days=1)


def slot_start(hour: int, minute: int = 0) -> str:
    moment = datetime.combine(tomorrow(), datetime.min.time(), timezone.utc)
    return (moment + timedelta(hours=hour, minutes=minute)).isoformat()


def book(client, service_id, start, headers):
    return client.post(
        f"{API}/appointments", json={"service_id": service_id, "scheduled_start": start}, headers=headers
    )


def test_slots_are_generated_from_hours(client, bookable):
    day = client.get(
        f"{API}/services/{bookable['service']['id']}/appointment-slots",
        params={"date": tomorrow().isoformat()},
    ).json()
    assert day["duration_minutes"] == 30
    assert len(day["slots"]) == 6  # 09:00-12:00 in 30-minute slots
    assert all(slot["is_available"] for slot in day["slots"])


def test_book_and_list_my_appointments(client, bookable, customer_headers):
    response = book(client, bookable["service"]["id"], slot_start(9, 30), customer_headers)
    assert response.status_code == 201, response.text
    appointment = response.json()
    assert appointment["status"] == "BOOKED"
    assert appointment["scheduled_end"].startswith(f"{tomorrow().isoformat()}T10:00")

    mine = client.get(f"{API}/appointments", headers=customer_headers).json()
    assert mine["total"] == 1
    day = client.get(
        f"{API}/services/{bookable['service']['id']}/appointment-slots",
        params={"date": tomorrow().isoformat()},
    ).json()
    taken = next(s for s in day["slots"] if s["start"].endswith("09:30:00Z"))
    assert taken["remaining"] == 0 and taken["is_available"] is False
    titles = [n["title"] for n in client.get(f"{API}/notifications", headers=customer_headers).json()["items"]]
    assert "Appointment booked" in titles


def test_double_booking_prevented(client, bookable, make_user):
    first = make_user("a@example.com")
    second = make_user("b@example.com")
    service_id = bookable["service"]["id"]
    assert book(client, service_id, slot_start(10), first).status_code == 201
    assert book(client, service_id, slot_start(10), second).status_code == 409  # slot full
    assert book(client, service_id, slot_start(10), first).status_code == 409  # same customer


def test_customer_cannot_overlap_appointments(client, bookable, owner_headers, create_service, customer_headers):
    other = create_service(
        owner_headers, bookable["business"]["id"], "Lab Test",
        appointments_enabled=True, appointment_duration_minutes=60, appointment_hours=BOOKING_HOURS,
    )
    assert book(client, bookable["service"]["id"], slot_start(10), customer_headers).status_code == 201
    assert book(client, other["id"], slot_start(10), customer_headers).status_code == 409


def test_invalid_slot_times_rejected(client, bookable, customer_headers):
    service_id = bookable["service"]["id"]
    assert book(client, service_id, slot_start(9, 10), customer_headers).status_code == 400  # misaligned
    assert book(client, service_id, slot_start(13), customer_headers).status_code == 400  # after hours
    past = (datetime.now(timezone.utc) - timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    assert book(client, service_id, past.isoformat(), customer_headers).status_code == 400
    naive = client.post(
        f"{API}/appointments",
        json={"service_id": service_id, "scheduled_start": slot_start(9)[:19]},
        headers=customer_headers,
    )
    assert naive.status_code == 422


def test_service_without_appointments_rejects_booking(client, owner_headers, create_business, create_service, customer_headers):
    business = create_business(owner_headers, "Walk-in Only", timezone="UTC")
    service = create_service(owner_headers, business["id"], "Quick Fix")
    assert book(client, service["id"], slot_start(9), customer_headers).status_code == 400


def test_daily_capacity(client, bookable, make_user):
    client.patch(f"{API}/services/{bookable['service']['id']}",
                 json={"appointment_daily_capacity": 1}, headers=bookable["owner"])
    service_id = bookable["service"]["id"]
    assert book(client, service_id, slot_start(9), make_user("a@example.com")).status_code == 201
    response = book(client, service_id, slot_start(11), make_user("b@example.com"))
    assert response.status_code == 409 and "day" in response.json()["detail"]


def test_cancel_frees_the_slot(client, bookable, make_user):
    service_id = bookable["service"]["id"]
    first = make_user("a@example.com")
    appointment = book(client, service_id, slot_start(9), first).json()
    cancelled = client.post(f"{API}/appointments/{appointment['id']}/cancel", headers=first)
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "CANCELLED"
    assert client.post(f"{API}/appointments/{appointment['id']}/cancel", headers=first).status_code == 409
    assert book(client, service_id, slot_start(9), make_user("b@example.com")).status_code == 201


def test_business_confirms_and_cancels(client, bookable, customer_headers):
    owner = bookable["owner"]
    appointment = book(client, bookable["service"]["id"], slot_start(9), customer_headers).json()
    listed = client.get(f"{API}/businesses/{bookable['business']['id']}/appointments",
                        params={"date": tomorrow().isoformat()}, headers=owner).json()
    assert listed["total"] == 1 and listed["items"][0]["customer_email"] == "customer@example.com"

    confirmed = client.post(f"{API}/appointments/{appointment['id']}/confirm", headers=owner).json()
    assert confirmed["status"] == "CONFIRMED"
    cancelled = client.post(f"{API}/appointments/{appointment['id']}/cancel",
                            json={"reason": "Doctor unavailable"}, headers=owner).json()
    assert cancelled["status"] == "CANCELLED"
    messages = [n["message"] for n in client.get(f"{API}/notifications", headers=customer_headers).json()["items"]]
    assert any("Doctor unavailable" in m for m in messages)
    assert any("confirmed" in m for m in messages)


def test_check_in_only_on_the_day(client, bookable, customer_headers):
    appointment = book(client, bookable["service"]["id"], slot_start(9), customer_headers).json()
    response = client.post(f"{API}/appointments/{appointment['id']}/check-in", headers=bookable["owner"])
    assert response.status_code == 400
    no_show = client.post(f"{API}/appointments/{appointment['id']}/no-show", headers=bookable["owner"])
    assert no_show.status_code == 400  # not started yet


def test_appointment_isolation(client, bookable, customer_headers, make_user, create_business):
    appointment = book(client, bookable["service"]["id"], slot_start(9), customer_headers).json()
    other_customer = make_user("other@example.com")
    rival = make_user("rival@example.com", "business-owner")
    rival_business = create_business(rival, "Rival Clinic")
    for headers in (other_customer, rival):
        assert client.get(f"{API}/appointments/{appointment['id']}", headers=headers).status_code == 404
        assert client.post(f"{API}/appointments/{appointment['id']}/cancel", headers=headers).status_code == 404
    assert client.post(f"{API}/appointments/{appointment['id']}/confirm", headers=rival).status_code == 403
    assert client.get(f"{API}/businesses/{bookable['business']['id']}/appointments",
                      headers=rival).status_code == 403
    assert client.get(f"{API}/businesses/{rival_business['id']}/appointments",
                      headers=rival).json()["total"] == 0


def test_check_in_and_complete_today(client, db, bookable, customer_headers):
    """Seed an appointment that started earlier today and walk it through the day-of flow."""
    from app.models import Appointment, User

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    customer = db.query(User).filter_by(email="customer@example.com").one()
    start = max(now - timedelta(minutes=5), datetime.combine(now.date(), datetime.min.time(), timezone.utc))
    appointment = Appointment(customer_id=customer.id, service_id=bookable["service"]["id"],
                              scheduled_start=start, scheduled_end=start + timedelta(minutes=30))
    db.add(appointment)
    db.commit()

    owner = bookable["owner"]
    assert client.post(f"{API}/appointments/{appointment.id}/check-in", headers=owner).json()["status"] == "CHECKED_IN"
    assert client.post(f"{API}/appointments/{appointment.id}/complete", headers=owner).json()["status"] == "COMPLETED"


def test_analytics(client, queue_setup, make_user):
    customer = make_user("c1@example.com")
    token = client.post(f"{API}/queues/{queue_setup['queue']['id']}/join", headers=customer).json()
    staff = queue_setup["staff"]
    client.post(f"{API}/counters/{queue_setup['counter']['id']}/call-next", headers=staff)
    client.post(f"{API}/tokens/{token['id']}/start", headers=staff)
    client.post(f"{API}/tokens/{token['id']}/complete", headers=staff)

    analytics = client.get(f"{API}/businesses/{queue_setup['business']['id']}/analytics",
                           params={"days": 7}, headers=queue_setup["owner"]).json()
    assert len(analytics["days"]) == 7
    assert analytics["days"][-1]["tokens_issued"] == 1
    assert analytics["days"][-1]["completed"] == 1
    assert analytics["completion_rate"] == 1.0
    assert client.get(f"{API}/businesses/{queue_setup['business']['id']}/analytics",
                      headers=staff).status_code == 403  # managers and owners only
