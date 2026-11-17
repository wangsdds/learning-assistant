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


def create_document(client, headers, name="notes"):
    response = client.post(
        "/documents",
        json={"documents_name": name, "docments": f"{name}.pdf"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_create_question_requires_auth(client):
    response = client.post(
        "/documents/1/questions",
        json={"que": "1 + 1 = ?", "system_answer": 2},
    )
    assert response.status_code == 401


def test_owner_can_create_question(client):
    headers = auth_headers(client, "alice@example.com", "alice")
    document_id = create_document(client, headers)

    response = client.post(
        f"/documents/{document_id}/questions",
        json={"que": " 1 + 1 = ? ", "system_answer": 2},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["que"] == "1 + 1 = ?"
    assert body["doc_id"] == document_id
    assert "system_answer" not in body


def test_user_cannot_add_question_to_other_users_document(client):
    alice = auth_headers(client, "alice@example.com", "alice")
    bob = auth_headers(client, "bob@example.com", "bob")
    document_id = create_document(client, alice)

    response = client.post(
        f"/documents/{document_id}/questions",
        json={"que": "1 + 1 = ?", "system_answer": 2},
        headers=bob,
    )
    assert response.status_code == 404


def test_blank_question_is_rejected(client):
    headers = auth_headers(client, "alice@example.com", "alice")
    document_id = create_document(client, headers)

    response = client.post(
        f"/documents/{document_id}/questions",
        json={"que": "   ", "system_answer": 2},
        headers=headers,
    )
    assert response.status_code == 422

def test_owner_can_list_questions_without_answers(client):
    headers = auth_headers(client, "alice@example.com", "alice")
    document_id = create_document(client, headers)

    for prompt, answer in [("1 + 1 = ?", 2), ("2 + 2 = ?", 4)]:
        created = client.post(
            f"/documents/{document_id}/questions",
            json={"que": prompt, "system_answer": answer},
            headers=headers,
        )
        assert created.status_code == 201, created.text

    response = client.get(
        f"/documents/{document_id}/questions",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert all("system_answer" not in item for item in body)


def test_user_cannot_list_other_users_questions(client):
    alice = auth_headers(client, "alice@example.com", "alice")
    bob = auth_headers(client, "bob@example.com", "bob")
    document_id = create_document(client, alice)

    response = client.get(
        f"/documents/{document_id}/questions",
        headers=bob,
    )
    assert response.status_code == 404
def create_question(client, headers, document_id, prompt="1 + 1 = ?", system_answer=2):
    response = client.post(
        f"/documents/{document_id}/questions",
        json={"que": prompt, "system_answer": system_answer},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_create_answer_requires_auth(client):
    response = client.post(
        "/questions/1/answers",
        json={"user_answer": "2", "costtime": 0},
    )
    assert response.status_code == 401


def test_correct_answer_scores_one(client):
    headers = auth_headers(client, "alice@example.com", "alice")
    document_id = create_document(client, headers)
    question_id = create_question(client, headers, document_id)

    response = client.post(
        f"/questions/{question_id}/answers",
        json={"user_answer": " 2 ", "costtime": 0},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["que_id"] == question_id
    assert body["user_answer"] == "2"
    assert body["scores"] == "1"
    assert body["costtime"] == 0
    assert body["answer_time"]


def test_wrong_answer_scores_zero(client):
    headers = auth_headers(client, "alice@example.com", "alice")
    document_id = create_document(client, headers)
    question_id = create_question(client, headers, document_id)

    response = client.post(
        f"/questions/{question_id}/answers",
        json={"user_answer": "3", "costtime": 12},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["scores"] == "0"


def test_user_cannot_answer_other_users_question(client):
    alice = auth_headers(client, "alice@example.com", "alice")
    bob = auth_headers(client, "bob@example.com", "bob")
    document_id = create_document(client, alice)
    question_id = create_question(client, alice, document_id)

    response = client.post(
        f"/questions/{question_id}/answers",
        json={"user_answer": "2", "costtime": 0},
        headers=bob,
    )
    assert response.status_code == 404


def test_blank_answer_is_rejected(client):
    headers = auth_headers(client, "alice@example.com", "alice")
    document_id = create_document(client, headers)
    question_id = create_question(client, headers, document_id)

    response = client.post(
        f"/questions/{question_id}/answers",
        json={"user_answer": "   ", "costtime": 0},
        headers=headers,
    )
    assert response.status_code == 422


def test_negative_costtime_is_rejected(client):
    headers = auth_headers(client, "alice@example.com", "alice")
    document_id = create_document(client, headers)
    question_id = create_question(client, headers, document_id)

    response = client.post(
        f"/questions/{question_id}/answers",
        json={"user_answer": "2", "costtime": -1},
        headers=headers,
    )
    assert response.status_code == 422


def test_owner_can_list_answers_newest_first(client):
    headers = auth_headers(client, "alice@example.com", "alice")
    document_id = create_document(client, headers)
    question_id = create_question(client, headers, document_id)

    for value, costtime in [("2", 3), ("3", 4)]:
        created = client.post(
            f"/questions/{question_id}/answers",
            json={"user_answer": value, "costtime": costtime},
            headers=headers,
        )
        assert created.status_code == 201, created.text

    response = client.get(
        f"/questions/{question_id}/answers",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 2
    assert body[0]["id"] > body[1]["id"]
    assert body[0]["scores"] == "0"
    assert body[1]["scores"] == "1"


def test_list_answers_requires_auth(client):
    response = client.get("/questions/1/answers")
    assert response.status_code == 401


def test_user_cannot_list_other_users_answers(client):
    alice = auth_headers(client, "alice@example.com", "alice")
    bob = auth_headers(client, "bob@example.com", "bob")
    document_id = create_document(client, alice)
    question_id = create_question(client, alice, document_id)

    response = client.get(
        f"/questions/{question_id}/answers",
        headers=bob,
    )
    assert response.status_code == 404


def test_update_question_requires_auth(client):
    response = client.patch(
        "/questions/1",
        json={"que": "新题干"},
    )
    assert response.status_code == 401


def test_owner_can_update_question_text_only(client):
    headers = auth_headers(client, "alice@example.com", "alice")
    document_id = create_document(client, headers)
    question_id = create_question(
        client,
        headers,
        document_id,
        prompt="1 + 1 = ?",
        system_answer=2,
    )

    response = client.patch(
        f"/questions/{question_id}",
        json={"que": " 2 + 2 = ? "},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == question_id
    assert body["que"] == "2 + 2 = ?"
    assert body["doc_id"] == document_id

    answer = client.post(
        f"/questions/{question_id}/answers",
        json={"user_answer": "2", "costtime": 0},
        headers=headers,
    )
    assert answer.status_code == 201, answer.text
    assert answer.json()["scores"] == "1"


def test_owner_can_update_system_answer_only(client):
    headers = auth_headers(client, "alice@example.com", "alice")
    document_id = create_document(client, headers)
    question_id = create_question(client, headers, document_id)

    response = client.patch(
        f"/questions/{question_id}",
        json={"system_answer": 3},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == question_id
    assert body["doc_id"] == document_id
    assert "system_answer" not in body

    answer = client.post(
        f"/questions/{question_id}/answers",
        json={"user_answer": "3", "costtime": 0},
        headers=headers,
    )
    assert answer.status_code == 201, answer.text
    assert answer.json()["scores"] == "1"


def test_empty_question_update_is_rejected(client):
    headers = auth_headers(client, "alice@example.com", "alice")
    document_id = create_document(client, headers)
    question_id = create_question(client, headers, document_id)

    response = client.patch(
        f"/questions/{question_id}",
        json={},
        headers=headers,
    )
    assert response.status_code == 422


def test_blank_question_update_is_rejected(client):
    headers = auth_headers(client, "alice@example.com", "alice")
    document_id = create_document(client, headers)
    question_id = create_question(client, headers, document_id)

    response = client.patch(
        f"/questions/{question_id}",
        json={"que": "   "},
        headers=headers,
    )
    assert response.status_code == 422


def test_user_cannot_update_other_users_question(client):
    alice = auth_headers(client, "alice@example.com", "alice")
    bob = auth_headers(client, "bob@example.com", "bob")
    document_id = create_document(client, alice)
    question_id = create_question(client, alice, document_id)

    response = client.patch(
        f"/questions/{question_id}",
        json={"que": "偷改题目"},
        headers=bob,
    )
    assert response.status_code == 404
