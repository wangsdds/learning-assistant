# -*- coding: utf-8 -*-
"""ORM 模型：把 docs/schema.sql 的 6 张表翻译成 SQLAlchemy 2.0 的写法。

写法参考（一张跟你项目无关的示例表，照这个风格写你自己的）：

    from datetime import datetime
    from sqlalchemy import String, DateTime, ForeignKey, CheckConstraint
    from sqlalchemy.orm import Mapped, mapped_column, relationship
    from app.db import Base

    class Tag(Base):
        __tablename__ = "tags"

        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str] = mapped_column(String(50), unique=True)
        created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

要写的 6 张表（列名/类型/约束以 docs/schema.sql 为准，不要自己发明）：
    users / plan_days / newplan / documents / question / answer

三条硬要求：
1. 外键必须带 ondelete="CASCADE"（数据库层才有级联，光写 relationship 不管用）；
2. 至少一个表用 __table_args__ 写 CHECK 约束（documents：文件或网址至少填一个）；
3. 每张表都写 __tablename__，不要依赖类名自动转换。
"""

from app.db import Base  # noqa: F401  ← 现在只有 import，写完模型后 Alembic 才看得见表
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, CheckConstraint, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
class User(Base):
    __tablename__="users"
    user_id: Mapped[int]=mapped_column(primary_key=True)
    email:Mapped[str]=mapped_column(String(255),unique=True)
    nickname:Mapped[str]=mapped_column(Text)
    password:Mapped[str]=mapped_column(Text)
class PlanDay(Base):
    __tablename__="plan_days"
    plan_id:Mapped[int]=mapped_column(primary_key=True)
    calender:Mapped[str]=mapped_column(Text)
    add_date:Mapped[str]=mapped_column(Text)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.user_id",ondelete="CASCADE"),index=True)
class NewPlan(Base):
    __tablename__="newplan"
    plan_id:Mapped[int]=mapped_column(ForeignKey("plan_days.plan_id",ondelete="CASCADE"),index=True)
    plan:Mapped[str]=mapped_column(Text)
    id:Mapped[int]=mapped_column(primary_key=True)
class Document(Base):
    __tablename__="documents"
    __table_args__ = (
    CheckConstraint("docments IS NOT NULL OR websites IS NOT NULL", name="chk_contact_at_least_one"),
)
    id:Mapped[int]=mapped_column(primary_key=True)
    documents_name:Mapped[str]=mapped_column(Text)
    docments:Mapped[str|None]=mapped_column(Text)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.user_id",ondelete="CASCADE"),index=True)
    websites:Mapped[str|None]=mapped_column(Text)
class DocumentChunk(Base):
    __tablename__="document_chunks"
    __table_args__=(
        UniqueConstraint("document_id","chunk_index",name="uq_document_chunks_document_index"),
    )
    id:Mapped[int]=mapped_column(primary_key=True)
    document_id:Mapped[int]=mapped_column(ForeignKey("documents.id",ondelete="CASCADE"),index=True)
    chunk_index:Mapped[int]=mapped_column()
    content:Mapped[str]=mapped_column(Text)
    char_count:Mapped[int]=mapped_column()
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Question(Base):
    __tablename__="question"
    id:Mapped[int]=mapped_column(primary_key=True)
    system_answer:Mapped[int]=mapped_column()
    que:Mapped[str]=mapped_column(Text)
    doc_id:Mapped[int]=mapped_column(ForeignKey("documents.id",ondelete="CASCADE"),index=True)
class Answer(Base):
    __tablename__="answer"
    id:Mapped[int]=mapped_column(primary_key=True)
    costtime:Mapped[int]=mapped_column()
    answer_time:Mapped[str]=mapped_column(Text)
    user_answer:Mapped[str]=mapped_column(Text)
    scores:Mapped[str]=mapped_column(Text)
    que_id:Mapped[int]=mapped_column(ForeignKey("question.id",ondelete="CASCADE"),index=True)
    owner_id:Mapped[int]=mapped_column(ForeignKey("users.user_id",ondelete="CASCADE"),index=True)


    
