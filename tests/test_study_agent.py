from pydantic_ai import models
from pydantic_ai.messages import ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel


models.ALLOW_MODEL_REQUESTS = False


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


def latest_search_result(messages) -> list[dict] | None:
    for message in reversed(messages):
        for part in message.parts:
            if (
                isinstance(part, ToolReturnPart)
                and part.tool_name == "search_documents"
            ):
                return part.content
    return None


def draft_args(chunk_id: int) -> dict:
    return {
        "question": "为什么二级索引查询可能需要回表？",
        "expected_answer": "二级索引叶子节点只保存索引列和主键，查询其他列时要用主键回聚簇索引再查一次。",
        "rubric": ["指出二级索引保存主键", "说明需要回聚簇索引取整行"],
        "difficulty": "medium",
        "source_chunk_ids": [chunk_id],
    }


def configure_test_model(monkeypatch, function):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "http://test.local/v1")
    monkeypatch.setenv("LLM_MODEL", "test-study-model")
    monkeypatch.setenv("LLM_TRUST_ENV", "false")
    monkeypatch.setattr(
        "app.study_agent.create_study_model",
        lambda config, http_client: FunctionModel(
            function,
            model_name="function-study-agent",
        ),
    )


def test_study_agent_searches_then_returns_grounded_draft(client, monkeypatch):
    headers = auth_headers(client, "study-agent@example.com")
    chunk_text = (
        "聚簇索引叶子节点保存完整行数据。二级索引叶子节点只保存索引列和主键，"
        "查询不在二级索引中的列时，需要拿主键回到聚簇索引再次查找，这叫回表。"
    )
    document_id = create_document(client, headers, chunk_text)
    model_calls = []

    def model_function(messages, info: AgentInfo):
        model_calls.append(messages)
        search_result = latest_search_result(messages)
        if search_result is None:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="search_documents",
                        args={"query": "回表 二级索引"},
                    )
                ]
            )
        assert search_result
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name=info.output_tools[0].name,
                    args=draft_args(search_result[0]["chunk_id"]),
                )
            ]
        )

    configure_test_model(monkeypatch, model_function)
    response = client.post(
        f"/documents/{document_id}/study-agent",
        json={"focus": "回表和二级索引"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(model_calls) == 2
    assert body["question"].startswith("为什么二级索引")
    assert body["model"] == "test-study-model"
    assert body["tool_calls"] == 1
    assert body["steps"] == 2
    assert body["sources"][0]["chunk_id"] == body["source_chunk_ids"][0]
    assert "回表" in body["sources"][0]["content"]


def test_study_agent_rejects_other_users_document(client):
    alice = auth_headers(client, "alice-study@example.com", "alice")
    bob = auth_headers(client, "bob-study@example.com", "bob")
    document_id = create_document(client, alice, "只有 Alice 能看的资料。")

    response = client.post(
        f"/documents/{document_id}/study-agent",
        json={},
        headers=bob,
    )

    assert response.status_code == 404


def test_study_agent_retries_when_source_is_not_retrieved(client, monkeypatch):
    headers = auth_headers(client, "study-agent-retry@example.com")
    document_id = create_document(
        client,
        headers,
        "B+ 树非叶子节点只保存键和子节点指针，因此单页能容纳更多键。",
    )
    model_calls = []

    def model_function(messages, info: AgentInfo):
        model_calls.append(messages)
        search_result = latest_search_result(messages)
        if search_result is None:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="search_documents",
                        args={"query": "B+ 树 非叶子节点"},
                    )
                ]
            )

        chunk_id = search_result[0]["chunk_id"]
        args = draft_args(chunk_id)
        if len(model_calls) == 2:
            args["source_chunk_ids"] = [999999]
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name=info.output_tools[0].name,
                    args=args,
                )
            ]
        )

    configure_test_model(monkeypatch, model_function)
    response = client.post(
        f"/documents/{document_id}/study-agent",
        json={},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert len(model_calls) == 3
    assert response.json()["source_chunk_ids"] != [999999]
    assert response.json()["steps"] == 3


def test_study_agent_returns_502_after_invalid_sources_exhaust_retries(
    client,
    monkeypatch,
):
    headers = auth_headers(client, "study-agent-invalid@example.com")
    document_id = create_document(client, headers, "哈希索引适合等值查询。")

    def model_function(messages, info: AgentInfo):
        search_result = latest_search_result(messages)
        if search_result is None:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="search_documents",
                        args={"query": "哈希索引"},
                    )
                ]
            )
        args = draft_args(999999)
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name=info.output_tools[0].name,
                    args=args,
                )
            ]
        )

    configure_test_model(monkeypatch, model_function)
    response = client.post(
        f"/documents/{document_id}/study-agent",
        json={},
        headers=headers,
    )

    assert response.status_code == 502


def test_study_agent_requires_llm_configuration(client, monkeypatch):
    headers = auth_headers(client, "study-agent-config@example.com")
    document_id = create_document(client, headers, "事务的 ACID 特性。")
    for name in ("LLM_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    response = client.post(
        f"/documents/{document_id}/study-agent",
        json={},
        headers=headers,
    )

    assert response.status_code == 503


def test_study_agent_rejects_document_without_text(client, monkeypatch):
    headers = auth_headers(client, "study-agent-url@example.com")
    created = client.post(
        "/documents",
        json={"documents_name": "网页资料", "websites": "https://example.com"},
        headers=headers,
    )
    assert created.status_code == 201, created.text

    response = client.post(
        f"/documents/{created.json()['id']}/study-agent",
        json={},
        headers=headers,
    )

    assert response.status_code == 409
