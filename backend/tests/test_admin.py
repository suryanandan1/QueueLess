import pytest
from starlette.websockets import WebSocketDisconnect

from tests.conftest import API


def test_admin_endpoints_require_super_admin(client, customer_headers, owner_headers):
    for headers in (customer_headers, owner_headers):
        assert client.get(f"{API}/admin/stats", headers=headers).status_code == 403
        assert client.get(f"{API}/admin/users", headers=headers).status_code == 403
    assert client.get(f"{API}/admin/stats").status_code == 401


def test_admin_stats_and_user_listing(client, admin_headers, register, owner_headers, create_business):
    register("c1@example.com")
    create_business(owner_headers)

    stats = client.get(f"{API}/admin/stats", headers=admin_headers).json()
    assert stats["total_users"] == 3
    assert stats["users_by_role"]["CUSTOMER"] == 1
    assert stats["total_businesses"] == 1

    owners = client.get(
        f"{API}/admin/users", params={"role": "BUSINESS_OWNER"}, headers=admin_headers
    ).json()
    assert owners["total"] == 1 and owners["items"][0]["email"] == "owner@example.com"


def test_admin_cannot_deactivate_self(client, admin_headers):
    me = client.get(f"{API}/auth/me", headers=admin_headers).json()
    response = client.patch(
        f"{API}/admin/users/{me['id']}/status", json={"is_active": False}, headers=admin_headers
    )
    assert response.status_code == 400


def test_deactivating_user_ends_their_sessions(client, admin_headers, customer_headers):
    me = client.get(f"{API}/auth/me", headers=customer_headers).json()
    client.patch(
        f"{API}/admin/users/{me['id']}/status", json={"is_active": False}, headers=admin_headers
    )
    assert client.get(f"{API}/auth/me", headers=customer_headers).status_code in (401, 403)


def test_audit_log_records_actions(client, admin_headers, owner_headers, create_business):
    business = create_business(owner_headers)
    logs = client.get(
        f"{API}/admin/audit-logs", params={"business_id": business["id"]}, headers=admin_headers
    ).json()
    assert "business.created" in [entry["action"] for entry in logs["items"]]


def test_websocket_requires_membership(client, login, owner_headers, make_user, create_business):
    business = create_business(owner_headers)
    owner_token = owner_headers["Authorization"].split()[1]
    outsider_token = make_user("out@example.com")["Authorization"].split()[1]
    url = f"{API}/ws/businesses/{business['id']}"

    with client.websocket_connect(f"{url}?token={owner_token}") as websocket:
        websocket.send_text("ping")
        assert websocket.receive_text() == "pong"

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"{url}?token={outsider_token}") as websocket:
            websocket.receive_text()
