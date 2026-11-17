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


def test_documents_requires_auth(client):
    response = client.get("/documents")
    assert response.status_code == 401


def test_create_file_document_and_url_document(client):
    headers = auth_headers(client, "alice@example.com", "alice")

    file_document = client.post(
        "/documents",
        json={"documents_name": "notes.pdf", "docments": "uploads/notes.pdf"},
        headers=headers,
    )
    assert file_document.status_code == 201, file_document.text
    assert file_document.json()["docments"] == "uploads/notes.pdf"
    assert file_document.json()["websites"] is None

    url_document = client.post(
        "/documents",
        json={"documents_name": "article", "websites": "https://example.com/article"},
        headers=headers,
    )
    assert url_document.status_code == 201, url_document.text
    assert url_document.json()["docments"] is None

    listed = client.get("/documents", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 2


def test_document_requires_file_or_website(client):
    headers = auth_headers(client, "alice@example.com", "alice")
    response = client.post(
        "/documents",
        json={"documents_name": "empty"},
        headers=headers,
    )
    assert response.status_code == 422


def test_user_cannot_read_other_users_document(client):
    alice = auth_headers(client, "alice@example.com", "alice")
    bob = auth_headers(client, "bob@example.com", "bob")

    created = client.post(
        "/documents",
        json={"documents_name": "private.pdf", "docments": "private.pdf"},
        headers=alice,
    )
    assert created.status_code == 201
    document_id = created.json()["id"]

    bob_list = client.get("/documents", headers=bob)
    assert bob_list.status_code == 200
    assert bob_list.json() == []

    bob_read = client.get(f"/documents/{document_id}", headers=bob)
    assert bob_read.status_code == 404
