from app.schemas import GradingDraft


def auth_headers(client, email, nickname="alice"):
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


def create_document(client, headers, content="B+ 树的非叶子节点只保存键和子节点指针。"):
    response = client.post(
        "/documents",
        json={"documents_name": "索引笔记", "docments": content},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_text_question(client, headers, document_id):
    response = client.post(
        f"/documents/{document_id}/questions",
        json={
            "question_type": "text",
            "que": "为什么 B+ 树的非叶子节点能容纳更多键？",
            "reference_answer": "因为非叶子节点只保存键和子节点指针，不保存整行数据。",
            "rubric": ["指出非叶子节点不保存整行数据", "说明单页能容纳更多键"],
            "difficulty": "medium",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_owner_can_create_text_question_without_leaking_answer(client):
    headers = auth_headers(client, "text-create@example.com")
    document_id = create_document(client, headers)

    body = create_text_question(client, headers, document_id)

    assert body["question_type"] == "text"
    assert body["difficulty"] == "medium"
    assert "reference_answer" not in body
    assert "rubric" not in body


def test_generated_draft_can_be_saved_as_formal_question(client):
    headers = auth_headers(client, "draft-save@example.com")
    document_id = create_document(client, headers)
    search = client.get(
        f"/documents/{document_id}/search",
        params={"q": "B+ 树"},
        headers=headers,
    )
    assert search.status_code == 200, search.text
    chunk_id = search.json()[0]["chunk_id"]

    response = client.post(
        f"/documents/{document_id}/questions/from-draft",
        json={
            "question": "B+ 树非叶子节点为什么不保存整行数据？",
            "expected_answer": "这样单页能保存更多键，使树更矮。",
            "rubric": ["指出不保存整行数据", "说明树更矮或 I/O 更少"],
            "difficulty": "medium",
            "source_chunk_ids": [chunk_id],
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["question_type"] == "text"
    assert body["difficulty"] == "medium"
    assert "reference_answer" not in body


def test_draft_rejects_source_chunk_from_another_document(client):
    headers = auth_headers(client, "draft-source@example.com")
    first_document = create_document(client, headers, "第一份资料")
    second_document = create_document(client, headers, "第二份资料")
    search = client.get(
        f"/documents/{first_document}/search",
        params={"q": "第一份资料"},
        headers=headers,
    )
    chunk_id = search.json()[0]["chunk_id"]

    response = client.post(
        f"/documents/{second_document}/questions/from-draft",
        json={
            "question": "测试题",
            "expected_answer": "测试答案",
            "rubric": ["测试要点"],
            "difficulty": "easy",
            "source_chunk_ids": [chunk_id],
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_text_answer_is_graded_and_history_contains_feedback(client, monkeypatch):
    headers = auth_headers(client, "grade@example.com")
    document_id = create_document(client, headers)
    question = create_text_question(client, headers, document_id)

    def fake_grade_answer(question, reference_answer, rubric, user_answer):
        assert "B+ 树" in question
        assert reference_answer
        assert rubric == ["指出非叶子节点不保存整行数据", "说明单页能容纳更多键"]
        assert user_answer == "因为非叶子节点不保存整行数据。"
        return (
            GradingDraft(
                score=60,
                rubric_hits=["指出非叶子节点不保存整行数据"],
                rubric_misses=["说明单页能容纳更多键"],
                feedback="方向正确，再补上单页容量和树高的关系。",
                confidence="high",
            ),
            "fake-grader",
        )

    monkeypatch.setattr("app.routers.answers.grade_answer", fake_grade_answer)
    response = client.post(
        f"/questions/{question['id']}/answers/grade",
        json={
            "user_answer": "因为非叶子节点不保存整行数据。",
            "costtime": 12,
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["score"] == 60
    assert body["rubric_hits"] == ["指出非叶子节点不保存整行数据"]
    assert body["rubric_misses"] == ["说明单页能容纳更多键"]
    assert body["model"] == "fake-grader"

    history = client.get(
        f"/questions/{question['id']}/answers",
        headers=headers,
    )
    assert history.status_code == 200, history.text
    saved = history.json()[0]
    assert saved["scores"] == "60"
    assert saved["feedback"] == body["feedback"]
    assert saved["rubric_hits"] == body["rubric_hits"]
    assert saved["rubric_misses"] == body["rubric_misses"]
    assert saved["grade_model"] == "fake-grader"


def test_text_question_rejects_numeric_answer_endpoint(client):
    headers = auth_headers(client, "text-numeric@example.com")
    document_id = create_document(client, headers)
    question = create_text_question(client, headers, document_id)

    response = client.post(
        f"/questions/{question['id']}/answers",
        json={"user_answer": "42", "costtime": 1},
        headers=headers,
    )

    assert response.status_code == 409


def test_code_question_rejects_model_grading(client):
    headers = auth_headers(client, "numeric-grade@example.com")
    document_id = create_document(client, headers)
    created = client.post(
        f"/documents/{document_id}/questions",
        json={"que": "1 + 1 = ?", "system_answer": 2},
        headers=headers,
    )
    question_id = created.json()["id"]

    response = client.post(
        f"/questions/{question_id}/answers/grade",
        json={"user_answer": "2", "costtime": 1},
        headers=headers,
    )

    assert response.status_code == 409


def test_user_cannot_grade_other_users_question(client):
    alice = auth_headers(client, "alice-grade@example.com", "alice")
    bob = auth_headers(client, "bob-grade@example.com", "bob")
    document_id = create_document(client, alice)
    question = create_text_question(client, alice, document_id)

    response = client.post(
        f"/questions/{question['id']}/answers/grade",
        json={"user_answer": "试图批改别人的题", "costtime": 1},
        headers=bob,
    )

    assert response.status_code == 404
