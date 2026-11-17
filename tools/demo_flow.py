"""Run the complete MVP flow against an isolated in-memory database."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import app


def build_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app), engine


def expect(response, status_code, label):
    if response.status_code != status_code:
        raise RuntimeError(
            f"{label} failed: HTTP {response.status_code}\n{response.text}"
        )
    return response.json()


def main():
    client, engine = build_client()
    try:
        with client:
            print("1. 注册用户")
            user = expect(
                client.post(
                    "/users",
                    json={
                        "email": "demo@example.com",
                        "nickname": "demo",
                        "password": "12345678",
                    },
                ),
                201,
                "register",
            )
            print(f"   user_id={user['user_id']} email={user['email']}")

            print("2. 登录并获取 JWT")
            login = expect(
                client.post(
                    "/login",
                    json={
                        "email": "demo@example.com",
                        "password": "12345678",
                    },
                ),
                200,
                "login",
            )
            token = login["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print(f"   token={token[:24]}...")

            print("3. 建立今日学习计划")
            plan = expect(
                client.post(
                    "/plan_days",
                    json={"calender": "2026-11-16", "add_date": "2026-11-16"},
                    headers=headers,
                ),
                201,
                "create plan",
            )
            print(f"   plan_id={plan['plan_id']}")

            print("4. 添加学习资料")
            document = expect(
                client.post(
                    "/documents",
                    json={
                        "documents_name": "Python 基础",
                        "docments": "python-basics.pdf",
                    },
                    headers=headers,
                ),
                201,
                "create document",
            )
            document_id = document["id"]
            print(f"   document_id={document_id}")

            print("5. 从资料创建题目")
            question = expect(
                client.post(
                    f"/documents/{document_id}/questions",
                    json={"que": "1 + 1 = ?", "system_answer": 2},
                    headers=headers,
                ),
                201,
                "create question",
            )
            question_id = question["id"]
            print(f"   question_id={question_id} que={question['que']}")

            print("6. 提交答案并让服务端评分")
            answer = expect(
                client.post(
                    f"/questions/{question_id}/answers",
                    json={"user_answer": "2", "costtime": 3},
                    headers=headers,
                ),
                201,
                "submit answer",
            )
            print(
                f"   answer_id={answer['id']} scores={answer['scores']} "
                f"costtime={answer['costtime']}"
            )

            print("7. 回看答题记录")
            history = expect(
                client.get(
                    f"/questions/{question_id}/answers",
                    headers=headers,
                ),
                200,
                "list answers",
            )
            print(f"   history_count={len(history)}")

            print("\nMVP flow summary")
            print(json.dumps(
                {
                    "user_id": user["user_id"],
                    "plan_id": plan["plan_id"],
                    "document_id": document_id,
                    "question_id": question_id,
                    "answer_score": answer["scores"],
                    "history_count": len(history),
                },
                ensure_ascii=False,
                indent=2,
            ))
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


if __name__ == "__main__":
    main()
