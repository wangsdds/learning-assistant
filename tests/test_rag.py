from app.schemas import GeneratedQuestionDraft


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


def create_document(client, headers, content):
    response = client.post(
        "/documents",
        json={"documents_name": "MySQL 索引", "docments": content},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_document_is_indexed_and_searchable(client):
    headers = auth_headers(client, "rag@example.com")
    content = (
        "聚簇索引的叶子节点保存完整行数据，因此按主键查询通常只需一次树查找。\n\n"
        "二级索引的叶子节点保存索引列和主键值。查询列不在二级索引中时，"
        "需要拿主键回到聚簇索引再次查找，这个过程叫回表。\n\n"
        "哈希索引适合等值查询，但不能高效支持范围查询。"
    )
    document_id = create_document(client, headers, content)

    response = client.get(
        f"/documents/{document_id}/search",
        params={"q": "回表", "top_k": 2},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    results = response.json()
    assert results
    assert "回表" in results[0]["content"]
    assert results[0]["chunk_id"] > 0


def test_search_is_isolated_between_users(client):
    alice = auth_headers(client, "alice-rag@example.com", "alice")
    bob = auth_headers(client, "bob-rag@example.com", "bob")
    document_id = create_document(client, alice, "这是一份只有 Alice 能看的资料。")

    response = client.get(
        f"/documents/{document_id}/search",
        params={"q": "Alice"},
        headers=bob,
    )

    assert response.status_code == 404


def test_url_only_document_has_no_indexable_chunks(client):
    headers = auth_headers(client, "url-rag@example.com")
    created = client.post(
        "/documents",
        json={"documents_name": "网页资料", "websites": "https://example.com"},
        headers=headers,
    )
    document_id = created.json()["id"]

    search = client.get(
        f"/documents/{document_id}/search",
        params={"q": "索引"},
        headers=headers,
    )
    generated = client.post(
        f"/documents/{document_id}/generate-question",
        json={},
        headers=headers,
    )

    assert search.status_code == 200
    assert search.json() == []
    assert generated.status_code == 409


def test_generate_question_returns_grounded_structured_draft(client, monkeypatch):
    headers = auth_headers(client, "generate@example.com")
    document_id = create_document(
        client,
        headers,
        "B+ 树的非叶子节点只保存键和子节点指针，不保存整行数据，因此单页能容纳更多键。",
    )

    def fake_generate(document_name, focus, hits):
        assert document_name == "MySQL 索引"
        assert focus == "为什么 B+ 树更矮"
        assert hits
        return (
            GeneratedQuestionDraft(
                question="B+ 树的非叶子节点为什么能容纳更多键？",
                expected_answer="因为非叶子节点只保存键和子节点指针，不保存整行数据。",
                rubric=["指出非叶子节点不保存整行数据", "说明单页能保存更多键"],
                difficulty="medium",
                source_chunk_ids=[hits[0].chunk_id],
            ),
            "fake-model",
        )

    monkeypatch.setattr("app.routers.rag.generate_question", fake_generate)
    response = client.post(
        f"/documents/{document_id}/generate-question",
        json={"focus": "为什么 B+ 树更矮"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["question"].startswith("B+ 树")
    assert body["difficulty"] == "medium"
    assert body["model"] == "fake-model"
    assert body["sources"]
    assert body["sources"][0]["chunk_id"] == body["source_chunk_ids"][0]
