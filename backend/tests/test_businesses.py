from tests.conftest import API

WEEKDAY_HOURS = [
    {"day_of_week": day, "open_time": "09:00", "close_time": "17:00"} for day in range(5)
] + [{"day_of_week": 5, "is_closed": True}, {"day_of_week": 6, "is_closed": True}]


def test_owner_creates_business_and_becomes_owner_member(client, owner_headers, create_business):
    business = create_business(owner_headers, "City Bank", city="Pune", working_hours=WEEKDAY_HOURS)
    assert business["slug"] == "city-bank"
    assert business["is_active"] is True
    assert len(business["working_hours"]) == 7

    mine = client.get(f"{API}/businesses/mine", headers=owner_headers).json()
    assert [(m["business"]["id"], m["role"]) for m in mine] == [(business["id"], "OWNER")]


def test_duplicate_names_get_unique_slugs(owner_headers, create_business):
    first = create_business(owner_headers, "Glow Salon")
    second = create_business(owner_headers, "Glow Salon")
    assert first["slug"] == "glow-salon"
    assert second["slug"] == "glow-salon-2"


def test_customer_cannot_create_business(client, customer_headers):
    response = client.post(f"{API}/businesses", json={"name": "Nope"}, headers=customer_headers)
    assert response.status_code == 403


def test_unauthenticated_cannot_create_business(client):
    assert client.post(f"{API}/businesses", json={"name": "Nope"}).status_code == 401


def test_business_validation(client, owner_headers):
    bad_hours = client.post(
        f"{API}/businesses",
        json={
            "name": "Bad Hours",
            "working_hours": [{"day_of_week": 0, "open_time": "18:00", "close_time": "09:00"}],
        },
        headers=owner_headers,
    )
    assert bad_hours.status_code == 422
    bad_tz = client.post(
        f"{API}/businesses", json={"name": "Bad TZ", "timezone": "Mars/Base"}, headers=owner_headers
    )
    assert bad_tz.status_code == 422


def test_update_profile_and_working_hours(client, owner_headers, create_business):
    business = create_business(owner_headers)
    updated = client.patch(
        f"{API}/businesses/{business['id']}",
        json={"phone": "+91 98765 43210", "email": "help@citybank.example", "city": "Mumbai"},
        headers=owner_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["city"] == "Mumbai"

    hours = client.put(
        f"{API}/businesses/{business['id']}/working-hours",
        json={"working_hours": WEEKDAY_HOURS},
        headers=owner_headers,
    )
    assert hours.status_code == 200
    assert hours.json()["working_hours"][0]["open_time"] == "09:00:00"

    null_name = client.patch(
        f"{API}/businesses/{business['id']}", json={"name": None}, headers=owner_headers
    )
    assert null_name.status_code == 422


def test_public_listing_hides_inactive_businesses(client, owner_headers, create_business):
    active = create_business(owner_headers, "Open Clinic")
    hidden = create_business(owner_headers, "Closed Clinic")
    status = client.patch(
        f"{API}/businesses/{hidden['id']}/status", json={"is_active": False}, headers=owner_headers
    )
    assert status.status_code == 200 and status.json()["is_active"] is False

    listing = client.get(f"{API}/businesses", params={"search": "clinic"}).json()
    assert [b["id"] for b in listing["items"]] == [active["id"]]
    assert listing["total"] == 1
    # Anonymous visitors get 404 for the inactive business; the owner can still see it.
    assert client.get(f"{API}/businesses/{hidden['id']}").status_code == 404
    assert client.get(f"{API}/businesses/{hidden['id']}", headers=owner_headers).status_code == 200


def test_business_data_isolation(client, make_user, create_business):
    owner_a = make_user("a@example.com", "business-owner")
    owner_b = make_user("b@example.com", "business-owner")
    business_a = create_business(owner_a, "Alpha Bank")
    business_b = create_business(owner_b, "Beta Bank")
    b_id = business_b["id"]

    # Owner A must not read or modify anything private in business B.
    assert client.get(f"{API}/businesses/{b_id}/members", headers=owner_a).status_code == 403
    assert client.get(f"{API}/businesses/{b_id}/stats", headers=owner_a).status_code == 403
    assert client.patch(
        f"{API}/businesses/{b_id}", json={"name": "Hijacked"}, headers=owner_a
    ).status_code == 403
    assert client.patch(
        f"{API}/businesses/{b_id}/status", json={"is_active": False}, headers=owner_a
    ).status_code == 403
    assert client.post(
        f"{API}/businesses/{b_id}/services",
        json={"name": "Fake", "estimated_duration_minutes": 5},
        headers=owner_a,
    ).status_code == 403
    assert client.post(
        f"{API}/businesses/{b_id}/members", json={"email": "a@example.com"}, headers=owner_a
    ).status_code == 403
    assert client.get(
        f"{API}/businesses/{b_id}/services",
        params={"include_inactive": True},
        headers=owner_a,
    ).status_code == 403

    mine = client.get(f"{API}/businesses/mine", headers=owner_a).json()
    assert [m["business"]["id"] for m in mine] == [business_a["id"]]
    assert client.get(f"{API}/businesses/{b_id}").json()["name"] == "Beta Bank"


def test_business_stats_for_members(client, owner_headers, create_business, create_service):
    business = create_business(owner_headers)
    create_service(owner_headers, business["id"], "Deposit")
    create_service(owner_headers, business["id"], "Withdrawal", is_active=False)
    stats = client.get(f"{API}/businesses/{business['id']}/stats", headers=owner_headers).json()
    assert stats["total_services"] == 2
    assert stats["active_services"] == 1
    assert stats["active_members"] == 1
    assert stats["tokens_today"] == 0


def test_super_admin_can_access_any_business(client, owner_headers, admin_headers, create_business):
    business = create_business(owner_headers)
    assert client.get(
        f"{API}/businesses/{business['id']}/stats", headers=admin_headers
    ).status_code == 200
    response = client.patch(
        f"{API}/businesses/{business['id']}/status",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert response.status_code == 200
