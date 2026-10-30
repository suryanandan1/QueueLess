from tests.conftest import API, DEFAULT_PASSWORD


def test_owner_adds_existing_customer_as_staff(
    client, owner_headers, register, login, create_business
):
    business = create_business(owner_headers)
    register("teller@example.com")

    response = client.post(
        f"{API}/businesses/{business['id']}/members",
        json={"email": "teller@example.com", "role": "STAFF"},
        headers=owner_headers,
    )
    assert response.status_code == 201
    member = response.json()
    assert member["role"] == "STAFF"
    assert member["user"]["email"] == "teller@example.com"
    # Customers are promoted so they can reach the staff dashboard.
    assert member["user"]["role"] == "STAFF"

    tokens = login("teller@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    notifications = client.get(f"{API}/notifications", headers=headers).json()
    assert notifications["total"] == 1
    assert "City Bank" in notifications["items"][0]["message"]


def test_owner_creates_new_staff_account(client, owner_headers, create_business, login):
    business = create_business(owner_headers)
    missing = client.post(
        f"{API}/businesses/{business['id']}/members",
        json={"email": "new@example.com"},
        headers=owner_headers,
    )
    assert missing.status_code == 404

    created = client.post(
        f"{API}/businesses/{business['id']}/members",
        json={
            "email": "new@example.com",
            "role": "MANAGER",
            "full_name": "New Manager",
            "password": DEFAULT_PASSWORD,
        },
        headers=owner_headers,
    )
    assert created.status_code == 201
    assert login("new@example.com")["user"]["role"] == "STAFF"


def test_member_role_rules(client, owner_headers, register, create_business):
    business = create_business(owner_headers)
    register("staff@example.com")
    url = f"{API}/businesses/{business['id']}/members"

    assert client.post(
        url, json={"email": "staff@example.com", "role": "OWNER"}, headers=owner_headers
    ).status_code == 422
    member = client.post(url, json={"email": "staff@example.com"}, headers=owner_headers).json()
    assert client.post(
        url, json={"email": "staff@example.com"}, headers=owner_headers
    ).status_code == 409

    promoted = client.patch(f"{url}/{member['id']}", json={"role": "MANAGER"}, headers=owner_headers)
    assert promoted.status_code == 200 and promoted.json()["role"] == "MANAGER"

    owner_member = next(
        m for m in client.get(url, headers=owner_headers).json() if m["role"] == "OWNER"
    )
    assert client.delete(f"{url}/{owner_member['id']}", headers=owner_headers).status_code == 400
    assert client.delete(f"{url}/{member['id']}", headers=owner_headers).status_code == 204
    assert len(client.get(url, headers=owner_headers).json()) == 1


def test_staff_permissions_are_limited(client, owner_headers, make_user, create_business):
    business = create_business(owner_headers)
    staff_headers = make_user("staff@example.com")
    client.post(
        f"{API}/businesses/{business['id']}/members",
        json={"email": "staff@example.com", "role": "STAFF"},
        headers=owner_headers,
    )
    base = f"{API}/businesses/{business['id']}"

    assert client.get(f"{base}/members", headers=staff_headers).status_code == 200
    assert client.get(f"{base}/stats", headers=staff_headers).status_code == 200
    assert client.patch(base, json={"name": "Renamed"}, headers=staff_headers).status_code == 403
    assert client.post(
        f"{base}/services",
        json={"name": "Loans", "estimated_duration_minutes": 20},
        headers=staff_headers,
    ).status_code == 403
    assert client.post(
        f"{base}/members", json={"email": "x@example.com"}, headers=staff_headers
    ).status_code == 403


def test_deactivated_membership_loses_access(client, owner_headers, make_user, create_business):
    business = create_business(owner_headers)
    staff_headers = make_user("staff@example.com")
    url = f"{API}/businesses/{business['id']}/members"
    member = client.post(url, json={"email": "staff@example.com"}, headers=owner_headers).json()

    client.patch(f"{url}/{member['id']}", json={"is_active": False}, headers=owner_headers)
    assert client.get(url, headers=staff_headers).status_code == 403


def test_member_ids_from_other_business_are_rejected(
    client, make_user, register, create_business
):
    owner_a = make_user("a@example.com", "business-owner")
    owner_b = make_user("b@example.com", "business-owner")
    business_a = create_business(owner_a, "Alpha")
    business_b = create_business(owner_b, "Beta")
    register("worker@example.com")
    member_b = client.post(
        f"{API}/businesses/{business_b['id']}/members",
        json={"email": "worker@example.com"},
        headers=owner_b,
    ).json()

    # Owner A uses their own business id in the URL with a member id from business B.
    response = client.delete(
        f"{API}/businesses/{business_a['id']}/members/{member_b['id']}", headers=owner_a
    )
    assert response.status_code == 404
