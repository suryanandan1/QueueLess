from tests.conftest import API


def join(client, queue_id, headers):
    return client.post(f"{API}/queues/{queue_id}/join", headers=headers)


def test_open_queue_and_list_active(client, queue_setup):
    queue = queue_setup["queue"]
    assert queue["status"] == "OPEN"
    assert queue["token_prefix"] == "A"
    assert queue["accepting_customers"] is True

    active = client.get(f"{API}/queues", params={"business_id": queue_setup["business"]["id"]}).json()
    assert [q["id"] for q in active] == [queue["id"]]
    # Opening twice on the same day is rejected.
    again = client.post(
        f"{API}/queues", json={"service_id": queue_setup["service"]["id"]}, headers=queue_setup["owner"]
    )
    assert again.status_code == 409


def test_join_returns_token_with_position_and_estimate(client, queue_setup, make_user):
    queue_id = queue_setup["queue"]["id"]
    first = join(client, queue_id, make_user("c1@example.com"))
    second = join(client, queue_id, make_user("c2@example.com"))
    assert first.status_code == 201, first.text

    one, two = first.json(), second.json()
    assert (one["display_code"], two["display_code"]) == ("A001", "A002")
    assert one["status"] == "WAITING"
    assert one["customer_name"] == "Test User"
    assert (one["position"], two["position"]) == (1, 2)
    # One active counter, 20 min configured: nobody ahead -> 0, one ahead -> 20.
    assert one["estimate"]["minutes"] == 0
    assert two["estimate"]["minutes"] == 20
    assert two["estimate"]["basis"] == "configured"


def test_join_creates_notification(client, queue_setup, make_user):
    headers = make_user("c1@example.com")
    join(client, queue_setup["queue"]["id"], headers)
    notes = client.get(f"{API}/notifications", headers=headers).json()
    assert notes["items"][0]["title"] == "Token A001 confirmed"


def test_duplicate_active_token_rejected(client, queue_setup, make_user):
    headers = make_user("c1@example.com")
    queue_id = queue_setup["queue"]["id"]
    assert join(client, queue_id, headers).status_code == 201
    assert join(client, queue_id, headers).status_code == 409


def test_customer_can_rejoin_after_cancelling(client, queue_setup, make_user):
    headers = make_user("c1@example.com")
    queue_id = queue_setup["queue"]["id"]
    token = join(client, queue_id, headers).json()
    assert client.post(f"{API}/tokens/{token['id']}/cancel", headers=headers).status_code == 200
    rejoined = join(client, queue_id, headers)
    assert rejoined.status_code == 201
    assert rejoined.json()["display_code"] == "A002"


def test_join_requires_authentication(client, queue_setup):
    assert client.post(f"{API}/queues/{queue_setup['queue']['id']}/join").status_code == 401


def test_queue_capacity_enforced(client, queue_setup, make_user):
    queue_id = queue_setup["queue"]["id"]
    updated = client.patch(
        f"{API}/queues/{queue_id}", json={"max_capacity": 2}, headers=queue_setup["owner"]
    )
    assert updated.status_code == 200
    assert join(client, queue_id, make_user("c1@example.com")).status_code == 201
    assert join(client, queue_id, make_user("c2@example.com")).status_code == 201
    full = join(client, queue_id, make_user("c3@example.com"))
    assert full.status_code == 400
    assert "full" in full.json()["detail"]
    summary = client.get(f"{API}/queues/{queue_id}").json()
    assert summary["is_full"] is True and summary["accepting_customers"] is False


def test_paused_and_closed_queues_reject_joins(client, queue_setup, make_user):
    queue_id = queue_setup["queue"]["id"]
    owner = queue_setup["owner"]
    customer = make_user("c1@example.com")

    paused = client.post(f"{API}/queues/{queue_id}/pause", headers=owner).json()
    assert paused["status"] == "PAUSED"
    assert paused["estimate_for_new_customer"]["minutes"] is None  # no misleading estimate
    response = join(client, queue_id, customer)
    assert response.status_code == 400 and "paused" in response.json()["detail"]

    assert client.post(f"{API}/queues/{queue_id}/resume", headers=owner).json()["status"] == "OPEN"
    token = join(client, queue_id, customer).json()

    closed = client.post(f"{API}/queues/{queue_id}/close", headers=owner).json()
    assert closed["status"] == "CLOSED"
    assert join(client, queue_id, make_user("c2@example.com")).status_code == 400
    # Waiting tokens are cancelled and the customer is told why.
    assert client.get(f"{API}/tokens/{token['id']}", headers=customer).json()["status"] == "CANCELLED"
    titles = [n["title"] for n in client.get(f"{API}/notifications", headers=customer).json()["items"]]
    assert "Queue closed" in titles


def test_reopen_continues_numbering(client, queue_setup, make_user):
    queue_id = queue_setup["queue"]["id"]
    owner = queue_setup["owner"]
    join(client, queue_id, make_user("c1@example.com"))
    client.post(f"{API}/queues/{queue_id}/close", headers=owner)
    reopened = client.post(
        f"{API}/queues", json={"service_id": queue_setup["service"]["id"]}, headers=owner
    )
    assert reopened.status_code == 201 and reopened.json()["id"] == queue_id
    token = join(client, queue_id, make_user("c2@example.com")).json()
    assert token["display_code"] == "A002"


def test_unavailable_service_rejects_joins(client, queue_setup, make_user):
    client.patch(
        f"{API}/services/{queue_setup['service']['id']}",
        json={"is_available": False},
        headers=queue_setup["owner"],
    )
    response = join(client, queue_setup["queue"]["id"], make_user("c1@example.com"))
    assert response.status_code == 400


def test_custom_token_prefix(client, owner_headers, create_business, create_service, make_user):
    business = create_business(owner_headers, "City Bank", timezone="UTC")
    service = create_service(owner_headers, business["id"], "Loans", token_prefix="ln")
    assert service["token_prefix"] == "LN"
    queue = client.post(f"{API}/queues", json={"service_id": service["id"]}, headers=owner_headers).json()
    token = join(client, queue["id"], make_user("c1@example.com")).json()
    assert token["display_code"] == "LN001"


def test_queue_management_permissions(client, queue_setup, make_user, create_business):
    queue_id = queue_setup["queue"]["id"]
    # Business staff cannot pause/close; outsiders cannot even list tokens.
    assert client.post(f"{API}/queues/{queue_id}/pause", headers=queue_setup["staff"]).status_code == 403
    other_owner = make_user("other@example.com", "business-owner")
    create_business(other_owner, "Other Shop")
    assert client.post(f"{API}/queues/{queue_id}/close", headers=other_owner).status_code == 403
    assert client.get(f"{API}/queues/{queue_id}/tokens", headers=other_owner).status_code == 403
    assert client.post(
        f"{API}/queues", json={"service_id": queue_setup["service"]["id"]}, headers=other_owner
    ).status_code == 403
    assert client.post(
        f"{API}/queues/{queue_id}/walk-ins", json={"guest_name": "X"}, headers=other_owner
    ).status_code == 403


def test_public_summary_hides_customer_details(client, queue_setup, make_user):
    queue_id = queue_setup["queue"]["id"]
    join(client, queue_id, make_user("secret.person@example.com"))
    body = client.get(f"{API}/queues/{queue_id}").text
    assert "secret.person" not in body and "Test User" not in body


def test_walk_in_and_session_history(client, queue_setup):
    queue_id = queue_setup["queue"]["id"]
    walk_in = client.post(
        f"{API}/queues/{queue_id}/walk-ins",
        json={"guest_name": "Walk-in Wendy", "guest_phone": "+91 98765 43210"},
        headers=queue_setup["staff"],
    )
    assert walk_in.status_code == 201
    assert walk_in.json()["is_walk_in"] is True

    tokens = client.get(f"{API}/queues/{queue_id}/tokens", headers=queue_setup["staff"]).json()
    assert tokens[0]["customer_name"] == "Walk-in Wendy"
    assert tokens[0]["customer_phone"] == "+91 98765 43210"

    history = client.get(
        f"{API}/businesses/{queue_setup['business']['id']}/queues", headers=queue_setup["owner"]
    ).json()
    assert history["total"] == 1 and history["items"][0]["tokens_issued"] == 1


def test_queue_websocket_announces_changes_without_customer_data(client, queue_setup, make_user):
    queue_id = queue_setup["queue"]["id"]
    customer = make_user("private.person@example.com")
    with client.websocket_connect(f"{API}/ws/queues/{queue_id}") as websocket:
        join(client, queue_id, customer)
        message = websocket.receive_json()
    assert message == {"event": "queue_updated", "data": {"queue_id": queue_id}}
