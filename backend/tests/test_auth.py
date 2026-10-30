from tests.conftest import API, DEFAULT_PASSWORD, auth_header


def test_register_customer_returns_user_without_password(client):
    response = client.post(
        f"{API}/auth/register/customer",
        json={"email": "Alice@Example.com", "password": DEFAULT_PASSWORD, "full_name": "Alice"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["role"] == "CUSTOMER"
    assert body["is_active"] is True
    assert "password" not in body and "hashed_password" not in body


def test_register_business_owner_sets_role(register):
    assert register("owner@example.com", "business-owner")["role"] == "BUSINESS_OWNER"


def test_register_duplicate_email_conflicts(client, register):
    register("dup@example.com")
    response = client.post(
        f"{API}/auth/register/customer",
        json={"email": "DUP@example.com", "password": DEFAULT_PASSWORD, "full_name": "Dup"},
    )
    assert response.status_code == 409


def test_register_rejects_weak_password_and_bad_email(client):
    weak = client.post(
        f"{API}/auth/register/customer",
        json={"email": "weak@example.com", "password": "short", "full_name": "Weak"},
    )
    assert weak.status_code == 422
    bad_email = client.post(
        f"{API}/auth/register/customer",
        json={"email": "not-an-email", "password": DEFAULT_PASSWORD, "full_name": "Bad"},
    )
    assert bad_email.status_code == 422


def test_login_returns_token_pair(register, login):
    register("bob@example.com")
    tokens = login("BOB@example.com")
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"] and tokens["refresh_token"]
    assert tokens["user"]["email"] == "bob@example.com"


def test_login_invalid_credentials(client, register):
    register("carol@example.com")
    wrong_password = client.post(
        f"{API}/auth/login", json={"email": "carol@example.com", "password": "Wrong1234"}
    )
    unknown_user = client.post(
        f"{API}/auth/login", json={"email": "nobody@example.com", "password": DEFAULT_PASSWORD}
    )
    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    # Same message for both so attackers cannot discover registered emails.
    assert wrong_password.json()["detail"] == unknown_user.json()["detail"]


def test_me_requires_valid_token(client, customer_headers):
    assert client.get(f"{API}/auth/me").status_code == 401
    assert client.get(f"{API}/auth/me", headers=auth_header("garbage")).status_code == 401
    response = client.get(f"{API}/auth/me", headers=customer_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "customer@example.com"


def test_refresh_rotates_tokens_and_detects_reuse(client, register, login):
    register("dave@example.com")
    tokens = login("dave@example.com")

    refreshed = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    assert client.get(f"{API}/auth/me", headers=auth_header(new_tokens["access_token"])).is_success

    # Replaying the old refresh token is rejected and kills the new session too.
    replay = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401
    me = client.get(f"{API}/auth/me", headers=auth_header(new_tokens["access_token"]))
    assert me.status_code == 401


def test_access_token_cannot_be_used_as_refresh_token(client, register, login):
    register("erin@example.com")
    tokens = login("erin@example.com")
    response = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert response.status_code == 401


def test_logout_revokes_session(client, register, login):
    register("frank@example.com")
    tokens = login("frank@example.com")
    headers = auth_header(tokens["access_token"])

    assert client.post(
        f"{API}/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    ).status_code == 204
    assert client.get(f"{API}/auth/me", headers=headers).status_code == 401
    assert client.post(
        f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    ).status_code == 401


def test_deactivated_user_cannot_log_in(client, register, login, admin_headers):
    user = register("gina@example.com")
    response = client.patch(
        f"{API}/admin/users/{user['id']}/status", json={"is_active": False}, headers=admin_headers
    )
    assert response.status_code == 200
    login_response = client.post(
        f"{API}/auth/login", json={"email": "gina@example.com", "password": DEFAULT_PASSWORD}
    )
    assert login_response.status_code == 403


def test_password_reset_flow(client, register, caplog):
    register("hank@example.com")
    with caplog.at_level("WARNING"):
        response = client.post(f"{API}/auth/forgot-password", json={"email": "hank@example.com"})
    assert response.status_code == 202
    token = caplog.text.split("reset-password?token=")[1].split()[0]

    reset = client.post(
        f"{API}/auth/reset-password", json={"token": token, "new_password": "NewPassw0rd"}
    )
    assert reset.status_code == 200
    # The link is single-use.
    again = client.post(
        f"{API}/auth/reset-password", json={"token": token, "new_password": "Another1pass"}
    )
    assert again.status_code == 401
    login_response = client.post(
        f"{API}/auth/login", json={"email": "hank@example.com", "password": "NewPassw0rd"}
    )
    assert login_response.status_code == 200


def test_forgot_password_does_not_reveal_unknown_email(client):
    response = client.post(f"{API}/auth/forgot-password", json={"email": "ghost@example.com"})
    assert response.status_code == 202


def test_change_password_and_profile_update(client, register, login):
    register("ivy@example.com")
    headers = auth_header(login("ivy@example.com")["access_token"])

    wrong = client.post(
        f"{API}/users/me/change-password",
        json={"current_password": "Nope12345", "new_password": "Fresh1pass"},
        headers=headers,
    )
    assert wrong.status_code == 401
    changed = client.post(
        f"{API}/users/me/change-password",
        json={"current_password": DEFAULT_PASSWORD, "new_password": "Fresh1pass"},
        headers=headers,
    )
    assert changed.status_code == 204
    # The session that changed the password stays valid.
    profile = client.patch(f"{API}/users/me", json={"full_name": "Ivy Q"}, headers=headers)
    assert profile.status_code == 200 and profile.json()["full_name"] == "Ivy Q"
    assert client.patch(f"{API}/users/me", json={"full_name": None}, headers=headers).status_code == 422


def test_validation_errors_do_not_echo_password(client):
    response = client.post(
        f"{API}/auth/register/customer",
        json={"email": "echo@example.com", "password": "short-secret", "full_name": "Echo"},
    )
    assert response.status_code == 422
    assert "short-secret" not in response.text
