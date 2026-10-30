from tests.conftest import API


def join(client, queue_id, headers):
    response = client.post(f"{API}/queues/{queue_id}/join", headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def act(client, token_id, action, headers, **body):
    return client.post(f"{API}/tokens/{token_id}/{action}", json=body or None, headers=headers)


def test_full_lifecycle_and_counter_status(client, queue_setup, make_user):
    staff, counter = queue_setup["staff"], queue_setup["counter"]
    customer = make_user("c1@example.com")
    token = join(client, queue_setup["queue"]["id"], customer)

    called = client.post(f"{API}/counters/{counter['id']}/call-next", headers=staff)
    assert called.status_code == 200, called.text
    assert called.json()["status"] == "CALLED" and called.json()["counter_name"] == "Chair 1"
    assert client.get(f"{API}/counters/{counter['id']}", headers=staff).json()["status"] == "BUSY"

    assert act(client, token["id"], "start", staff).json()["status"] == "SERVING"
    done = act(client, token["id"], "complete", staff).json()
    assert done["status"] == "COMPLETED"
    assert done["called_at"] and done["service_started_at"] and done["completed_at"]
    assert client.get(f"{API}/counters/{counter['id']}", headers=staff).json()["status"] == "AVAILABLE"

    # Completing twice is an invalid transition with a clear message.
    again = act(client, token["id"], "complete", staff)
    assert again.status_code == 409
    assert "COMPLETED" in again.json()["detail"]

    titles = [n["title"] for n in client.get(f"{API}/notifications", headers=customer).json()["items"]]
    assert "Token A001 is being called" in titles


def test_invalid_transitions_rejected(client, queue_setup, make_user):
    staff = queue_setup["staff"]
    token = join(client, queue_setup["queue"]["id"], make_user("c1@example.com"))
    assert act(client, token["id"], "start", staff).status_code == 409  # WAITING -> SERVING
    assert act(client, token["id"], "complete", staff).status_code == 409  # WAITING -> COMPLETED
    assert act(client, token["id"], "skip", staff).status_code == 409  # WAITING -> SKIPPED


def test_skip_recall_and_no_show(client, queue_setup, make_user):
    staff, counter = queue_setup["staff"], queue_setup["counter"]
    token = join(client, queue_setup["queue"]["id"], make_user("c1@example.com"))
    act(client, token["id"], "call", staff, counter_id=counter["id"])

    assert act(client, token["id"], "recall", staff).json()["recall_count"] == 1  # re-announce
    skipped = act(client, token["id"], "skip", staff).json()
    assert skipped["status"] == "SKIPPED" and skipped["skipped_at"]
    assert client.get(f"{API}/counters/{counter['id']}", headers=staff).json()["status"] == "AVAILABLE"

    recalled = act(client, token["id"], "recall", staff, counter_id=counter["id"]).json()
    assert recalled["status"] == "CALLED" and recalled["recall_count"] == 2
    no_show = act(client, token["id"], "no-show", staff).json()
    assert no_show["status"] == "NO_SHOW"
    assert act(client, token["id"], "recall", staff).status_code == 409  # final state


def test_counter_handles_one_token_at_a_time(client, queue_setup, make_user):
    staff, counter = queue_setup["staff"], queue_setup["counter"]
    queue_id = queue_setup["queue"]["id"]
    first = join(client, queue_id, make_user("c1@example.com"))
    second = join(client, queue_id, make_user("c2@example.com"))
    act(client, first["id"], "call", staff, counter_id=counter["id"])

    busy = act(client, second["id"], "call", staff, counter_id=counter["id"])
    assert busy.status_code == 409 and "A001" in busy.json()["detail"]
    assert client.post(f"{API}/counters/{counter['id']}/call-next", headers=staff).status_code == 409


def test_call_next_order_and_positions_update(client, queue_setup, make_user):
    staff, counter = queue_setup["staff"], queue_setup["counter"]
    queue_id = queue_setup["queue"]["id"]
    customers = [make_user(f"c{i}@example.com") for i in range(3)]
    tokens = [join(client, queue_id, headers) for headers in customers]

    called = client.post(f"{API}/counters/{counter['id']}/call-next", headers=staff).json()
    assert called["display_code"] == "A001"
    # The others moved up one place; their estimates take the busy counter into account.
    second = client.get(f"{API}/tokens/{tokens[1]['id']}", headers=customers[1]).json()
    assert second["position"] == 1
    assert second["estimate"]["minutes"] == 10  # half an average service while the desk is busy
    # A cancelled token frees its place.
    act(client, tokens[1]["id"], "cancel", customers[1])
    third = client.get(f"{API}/tokens/{tokens[2]['id']}", headers=customers[2]).json()
    assert third["position"] == 1


def test_approaching_turn_notification(client, queue_setup, make_user):
    staff, counter = queue_setup["staff"], queue_setup["counter"]
    queue_id = queue_setup["queue"]["id"]
    customers = [make_user(f"c{i}@example.com") for i in range(3)]
    for headers in customers:
        join(client, queue_id, headers)
    client.post(f"{API}/counters/{counter['id']}/call-next", headers=staff)
    titles = [n["title"] for n in client.get(f"{API}/notifications", headers=customers[1]).json()["items"]]
    assert "Your turn is approaching" in titles


def test_staff_can_only_operate_assigned_counters(client, queue_setup, make_user):
    owner, service = queue_setup["owner"], queue_setup["service"]
    business_id = queue_setup["business"]["id"]
    other_staff = make_user("other.staff@example.com")
    client.post(f"{API}/businesses/{business_id}/members",
                json={"email": "other.staff@example.com"}, headers=owner)
    token = join(client, queue_setup["queue"]["id"], make_user("c1@example.com"))

    # Member of the business, but Chair 1 is not assigned to them.
    denied = act(client, token["id"], "call", other_staff, counter_id=queue_setup["counter"]["id"])
    assert denied.status_code == 403
    # Owners/managers can operate any counter of their business.
    counter2 = client.post(f"{API}/services/{service['id']}/counters", json={"name": "Chair 2"},
                           headers=owner).json()
    assert act(client, token["id"], "call", owner, counter_id=counter2["id"]).status_code == 200


def test_other_business_cannot_touch_tokens(client, queue_setup, make_user, create_business):
    token = join(client, queue_setup["queue"]["id"], make_user("c1@example.com"))
    outsider = make_user("outsider@example.com", "business-owner")
    create_business(outsider, "Rival Salon")
    assert act(client, token["id"], "call", outsider, counter_id=queue_setup["counter"]["id"]).status_code == 403
    assert client.get(f"{API}/tokens/{token['id']}", headers=outsider).status_code == 404
    assert act(client, token["id"], "cancel", outsider).status_code == 404
    assert client.get(f"{API}/counters/{queue_setup['counter']['id']}/console",
                      headers=outsider).status_code == 403


def test_customer_cannot_see_or_cancel_others_tokens(client, queue_setup, make_user):
    token = join(client, queue_setup["queue"]["id"], make_user("c1@example.com"))
    other = make_user("c2@example.com")
    assert client.get(f"{API}/tokens/{token['id']}", headers=other).status_code == 404
    assert act(client, token["id"], "cancel", other).status_code == 404


def test_customer_cannot_cancel_after_being_called(client, queue_setup, make_user):
    customer = make_user("c1@example.com")
    token = join(client, queue_setup["queue"]["id"], customer)
    act(client, token["id"], "call", queue_setup["staff"], counter_id=queue_setup["counter"]["id"])
    assert act(client, token["id"], "cancel", customer).status_code == 409


def test_paused_queue_blocks_calling(client, queue_setup, make_user):
    join(client, queue_setup["queue"]["id"], make_user("c1@example.com"))
    client.post(f"{API}/queues/{queue_setup['queue']['id']}/pause", headers=queue_setup["owner"])
    response = client.post(f"{API}/counters/{queue_setup['counter']['id']}/call-next",
                           headers=queue_setup["staff"])
    assert response.status_code == 400


def test_counter_console_and_history(client, queue_setup, make_user):
    staff, counter = queue_setup["staff"], queue_setup["counter"]
    customer = make_user("c1@example.com")
    queue_id = queue_setup["queue"]["id"]
    first = join(client, queue_id, customer)
    join(client, queue_id, make_user("c2@example.com"))
    client.post(f"{API}/counters/{counter['id']}/call-next", headers=staff)
    act(client, first["id"], "start", staff)

    console = client.get(f"{API}/counters/{counter['id']}/console", headers=staff).json()
    assert console["current_token"]["display_code"] == "A001"
    assert [t["display_code"] for t in console["waiting"]] == ["A002"]
    assert console["queue"]["now_serving"][0]["display_code"] == "A001"

    assigned = client.get(f"{API}/counters/assigned", headers=staff).json()
    assert [c["id"] for c in assigned] == [counter["id"]]

    act(client, first["id"], "complete", staff)
    history = client.get(f"{API}/tokens", headers=customer).json()
    assert history["total"] == 1 and history["items"][0]["status"] == "COMPLETED"


def test_counter_cannot_go_offline_while_busy(client, queue_setup, make_user):
    token = join(client, queue_setup["queue"]["id"], make_user("c1@example.com"))
    act(client, token["id"], "call", queue_setup["staff"], counter_id=queue_setup["counter"]["id"])
    response = client.patch(f"{API}/counters/{queue_setup['counter']['id']}",
                            json={"is_active": False}, headers=queue_setup["owner"])
    assert response.status_code == 409


def test_audit_log_records_transitions(client, queue_setup, make_user, admin_headers):
    token = join(client, queue_setup["queue"]["id"], make_user("c1@example.com"))
    act(client, token["id"], "call", queue_setup["staff"], counter_id=queue_setup["counter"]["id"])
    logs = client.get(f"{API}/admin/audit-logs",
                      params={"business_id": queue_setup["business"]["id"]},
                      headers=admin_headers).json()
    actions = {entry["action"] for entry in logs["items"]}
    assert {"queue.opened", "token.created", "token.called"} <= actions
