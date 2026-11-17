def auth_headers(client, email, nickname):
    created = client.post(
        "/users",
        json={"email": email, "nickname": nickname, "password": "12345678"},
    )
    assert created.status_code == 201, created.text

    login = client.post(
        "/login",
        json={"email": email, "password": "12345678"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_plan_days_requires_auth(client):
    response = client.get("/plan_days")
    assert response.status_code == 401


def test_create_and_list_own_plan(client):
    headers = auth_headers(client, "alice@example.com", "alice")
    payload = {"calender": "2026-10-26", "add_date": "2026-10-26"}

    created = client.post("/plan_days", json=payload, headers=headers)
    assert created.status_code == 201, created.text
    assert created.json()["calender"] == payload["calender"]
    assert created.json()["add_date"] == payload["add_date"]

    listed = client.get("/plan_days", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["plan_id"] == created.json()["plan_id"]


def test_user_cannot_read_other_users_plan(client):
    alice = auth_headers(client, "alice@example.com", "alice")
    bob = auth_headers(client, "bob@example.com", "bob")

    created = client.post(
        "/plan_days",
        json={"calender": "2026-10-26", "add_date": "2026-10-26"},
        headers=alice,
    )
    assert created.status_code == 201
    plan_id = created.json()["plan_id"]

    bob_list = client.get("/plan_days", headers=bob)
    assert bob_list.status_code == 200
    assert bob_list.json() == []

    bob_read = client.get(f"/plan_days/{plan_id}", headers=bob)
    assert bob_read.status_code == 404


def test_invalid_plan_payload_is_rejected(client):
    headers = auth_headers(client, "alice@example.com", "alice")
    response = client.post(
        "/plan_days",
        json={"calender": "", "add_date": "2026-10-26"},
        headers=headers,
    )
    assert response.status_code == 422
