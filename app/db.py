# -*- coding: utf-8 -*-
"""数据库连接：engine / Base / 会话工厂。

这一层只做三件事，别把业务逻辑塞进来。
"""
import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "app.db"

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///" + str(DEFAULT_DB).replace("\\", "/"))

engine = create_engine(
    DATABASE_URL,
    echo=bool(os.environ.get("SQL_ECHO")),
    future=True,
)

class Base(DeclarativeBase):
    """所有模型都继承它；Alembic 靠 Base.metadata 自动生成迁移。"""

@event.listens_for(engine, "connect")
def _sqlite_enable_foreign_keys(dbapi_connection, _record):
    """SQLite 默认不检查外键：每个新连接都要开一次，ON DELETE CASCADE 才真的生效。"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session():
    """FastAPI 依赖注入用；现在先手动 with 也行。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()