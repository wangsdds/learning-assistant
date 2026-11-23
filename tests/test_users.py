def register_and_login(client, email, nickname):
    created = client.post(
        "/users",
        json={"email": email, "nickname": nickname, "password": "12345678"},
    )
    assert created.status_code == 201, created.text
    body = created.json()

    login = client.post(
        "/login",
        json={"email": email, "password": "12345678"},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    return body, headers


def test_user_queries_require_auth(client):
    by_id = client.get("/users/1")
    by_email = client.get("/users/by-email/alice@example.com")

    assert by_id.status_code == 401
    assert by_email.status_code == 401


def test_user_can_query_self(client):
    user, headers = register_and_login(
        client,
        "alice@example.com",
        "alice",
    )

    by_id = client.get(f"/users/{user['user_id']}", headers=headers)
    by_email = client.get(
        "/users/by-email/alice@example.com",
        headers=headers,
    )

    assert by_id.status_code == 200, by_id.text
    assert by_id.json()["user_id"] == user["user_id"]
    assert by_email.status_code == 200, by_email.text
    assert by_email.json()["email"] == "alice@example.com"


def test_user_cannot_query_another_user_by_id(client):
    alice, alice_headers = register_and_login(
        client,
        "alice@example.com",
        "alice",
    )
    bob, _ = register_and_login(
        client,
        "bob@example.com",
        "bob",
    )

    response = client.get(
        f"/users/{bob['user_id']}",
        headers=alice_headers,
    )

    assert alice["user_id"] != bob["user_id"]
    assert response.status_code == 404


def test_user_cannot_query_another_user_by_email(client):
    _, alice_headers = register_and_login(
        client,
        "alice@example.com",
        "alice",
    )
    bob, _ = register_and_login(
        client,
        "bob@example.com",
        "bob",
    )

    response = client.get(
        f"/users/by-email/{bob['email']}",
        headers=alice_headers,
    )

    assert response.status_code == 404
