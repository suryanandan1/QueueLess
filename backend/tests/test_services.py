from datetime import date

from app.models import QueueSession
from tests.conftest import API


def test_create_and_list_services(client, owner_headers, create_business, create_service):
    business = create_business(owner_headers)
    service = create_service(
        owner_headers,
        business["id"],
        "Account Opening",
        estimated_duration_minutes=25,
        max_queue_capacity=40,
        operating_hours=[{"day_of_week": 0, "open_time": "10:00", "close_time": "14:00"}],
    )
    assert service["business_id"] == business["id"]
    assert service["max_queue_capacity"] == 40
    assert service["operating_hours"][0]["open_time"] == "10:00:00"

    public = client.get(f"{API}/businesses/{business['id']}/services").json()
    assert [s["name"] for s in public] == ["Account Opening"]


def test_service_validation_and_duplicate_names(client, owner_headers, create_business, create_service):
    business = create_business(owner_headers)
    url = f"{API}/businesses/{business['id']}/services"
    assert client.post(
        url, json={"name": "Zero", "estimated_duration_minutes": 0}, headers=owner_headers
    ).status_code == 422

    create_service(owner_headers, business["id"], "Haircut")
    duplicate = client.post(
        url, json={"name": "haircut", "estimated_duration_minutes": 30}, headers=owner_headers
    )
    assert duplicate.status_code == 409


def test_update_and_deactivate_service(client, owner_headers, create_business, create_service):
    business = create_business(owner_headers)
    service = create_service(owner_headers, business["id"])
    url = f"{API}/services/{service['id']}"

    updated = client.patch(
        url,
        json={"estimated_duration_minutes": 15, "is_available": False, "max_queue_capacity": None},
        headers=owner_headers,
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["estimated_duration_minutes"] == 15
    assert body["is_available"] is False
    assert body["max_queue_capacity"] is None

    client.patch(url, json={"is_active": False}, headers=owner_headers)
    # Deactivated services disappear from the public catalog but stay visible to members.
    assert client.get(f"{API}/businesses/{business['id']}/services").json() == []
    assert client.get(url).status_code == 404
    member_view = client.get(
        f"{API}/businesses/{business['id']}/services",
        params={"include_inactive": True},
        headers=owner_headers,
    ).json()
    assert len(member_view) == 1


def test_update_rejects_name_collision(client, owner_headers, create_business, create_service):
    business = create_business(owner_headers)
    create_service(owner_headers, business["id"], "Deposit")
    other = create_service(owner_headers, business["id"], "Withdrawal")
    response = client.patch(
        f"{API}/services/{other['id']}", json={"name": "Deposit"}, headers=owner_headers
    )
    assert response.status_code == 409


def test_other_business_cannot_update_service(client, make_user, create_business, create_service):
    owner_a = make_user("a@example.com", "business-owner")
    owner_b = make_user("b@example.com", "business-owner")
    create_business(owner_a, "Alpha")
    business_b = create_business(owner_b, "Beta")
    service_b = create_service(owner_b, business_b["id"])

    url = f"{API}/services/{service_b['id']}"
    assert client.patch(url, json={"name": "Stolen"}, headers=owner_a).status_code == 403
    assert client.delete(url, headers=owner_a).status_code == 403
    assert client.get(f"{url}/stats", headers=owner_a).status_code == 403
    assert client.get(f"{url}/counters", headers=owner_a).status_code == 403


def test_delete_service_without_history(client, owner_headers, create_business, create_service):
    business = create_business(owner_headers)
    service = create_service(owner_headers, business["id"])
    assert client.delete(f"{API}/services/{service['id']}", headers=owner_headers).status_code == 204
    assert client.get(f"{API}/services/{service['id']}").status_code == 404


def test_delete_service_with_history_is_blocked(
    client, db, owner_headers, create_business, create_service
):
    business = create_business(owner_headers)
    service = create_service(owner_headers, business["id"])
    db.add(QueueSession(business_id=business["id"], service_id=service["id"], session_date=date.today()))
    db.commit()

    response = client.delete(f"{API}/services/{service['id']}", headers=owner_headers)
    assert response.status_code == 409


def test_service_stats_and_counters(client, owner_headers, create_business, create_service):
    business = create_business(owner_headers)
    service = create_service(owner_headers, business["id"])
    counters_url = f"{API}/services/{service['id']}/counters"

    counter = client.post(counters_url, json={"name": "Counter 1"}, headers=owner_headers)
    assert counter.status_code == 201
    assert client.post(
        counters_url, json={"name": "counter 1"}, headers=owner_headers
    ).status_code == 409
    client.post(counters_url, json={"name": "Counter 2", "is_active": False}, headers=owner_headers)

    stats = client.get(f"{API}/services/{service['id']}/stats", headers=owner_headers).json()
    assert stats["total_counters"] == 2
    assert stats["active_counters"] == 1
    assert stats["average_service_minutes"] is None

    counter_id = counter.json()["id"]
    renamed = client.patch(
        f"{API}/counters/{counter_id}", json={"name": "Desk A"}, headers=owner_headers
    )
    assert renamed.json()["name"] == "Desk A"
    assert client.delete(f"{API}/counters/{counter_id}", headers=owner_headers).status_code == 204


def test_counter_assignee_must_belong_to_business(
    client, make_user, register, create_business, create_service
):
    owner_a = make_user("a@example.com", "business-owner")
    owner_b = make_user("b@example.com", "business-owner")
    business_a = create_business(owner_a, "Alpha")
    business_b = create_business(owner_b, "Beta")
    service_a = create_service(owner_a, business_a["id"])
    register("worker@example.com")
    member_b = client.post(
        f"{API}/businesses/{business_b['id']}/members",
        json={"email": "worker@example.com"},
        headers=owner_b,
    ).json()

    response = client.post(
        f"{API}/services/{service_a['id']}/counters",
        json={"name": "Desk", "assigned_member_id": member_b["id"]},
        headers=owner_a,
    )
    assert response.status_code == 400
