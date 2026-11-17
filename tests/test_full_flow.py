def test_complete_learning_flow(client):
    registered = client.post(
        "/users",
        json={
            "email": "demo@example.com",
            "nickname": "demo",
            "password": "12345678",
        },
    )
    assert registered.status_code == 201, registered.text

    login = client.post(
        "/login",
        json={"email": "demo@example.com", "password": "12345678"},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    plan = client.post(
        "/plan_days",
        json={"calender": "2026-11-16", "add_date": "2026-11-16"},
        headers=headers,
    )
    assert plan.status_code == 201, plan.text
    plan_id = plan.json()["plan_id"]

    plans = client.get("/plan_days", headers=headers)
    assert plans.status_code == 200
    assert [item["plan_id"] for item in plans.json()] == [plan_id]

    document = client.post(
        "/documents",
        json={"documents_name": "Python 基础", "docments": "python.pdf"},
        headers=headers,
    )
    assert document.status_code == 201, document.text
    document_id = document.json()["id"]

    question = client.post(
        f"/documents/{document_id}/questions",
        json={"que": "1 + 1 = ?", "system_answer": 2},
        headers=headers,
    )
    assert question.status_code == 201, question.text
    question_id = question.json()["id"]
    assert question.json()["doc_id"] == document_id
    assert "system_answer" not in question.json()

    answer = client.post(
        f"/questions/{question_id}/answers",
        json={"user_answer": "2", "costtime": 3},
        headers=headers,
    )
    assert answer.status_code == 201, answer.text
    answer_body = answer.json()
    assert answer_body["scores"] == "1"
    assert answer_body["que_id"] == question_id
    assert answer_body["user_answer"] == "2"
    assert answer_body["costtime"] == 3
    assert answer_body["answer_time"]

    history = client.get(
        f"/questions/{question_id}/answers",
        headers=headers,
    )
    assert history.status_code == 200, history.text
    assert len(history.json()) == 1
    assert history.json()[0]["id"] == answer_body["id"]
    assert history.json()[0]["scores"] == "1"

    client.post(
        "/users",
        json={
            "email": "bob@example.com",
            "nickname": "bob",
            "password": "12345678",
        },
    )
    bob_login = client.post(
        "/login",
        json={"email": "bob@example.com", "password": "12345678"},
    )
    bob_headers = {"Authorization": f"Bearer {bob_login.json()['access_token']}"}

    forbidden_history = client.get(
        f"/questions/{question_id}/answers",
        headers=bob_headers,
    )
    assert forbidden_history.status_code == 404
