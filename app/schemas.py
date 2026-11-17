# -*- coding: utf-8 -*-
"""API 输出结构。把下面的 TODO 补完。"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field,field_validator, model_validator

class UserOut(BaseModel):
    # 定义三个对外字段：user_id / e
    user_id: int
    email: str
    nickname: str

    model_config = ConfigDict(from_attributes=True)
class UserCreate(BaseModel):
    email:EmailStr
    nickname:str
    password: str=Field(min_length=8,max_length=72)
class LoginIn(BaseModel):
    email: EmailStr
    password: str

class PlanDayCreate(BaseModel):
    calender: str = Field(min_length=1, max_length=32)
    add_date: str = Field(min_length=1, max_length=32)


class PlanDayOut(BaseModel):
    plan_id: int
    calender: str
    add_date: str
    user_id: int

    model_config = ConfigDict(from_attributes=True)

class DocumentCreate(BaseModel):
    documents_name: str = Field(min_length=1, max_length=255)
    docments: str | None = Field(default=None, min_length=1, max_length=2000)
    websites: str | None = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode="after")
    def require_file_or_website(self):
        if not self.docments and not self.websites:
            raise ValueError("docments or websites is required")
        return self


class DocumentOut(BaseModel):
    id: int
    documents_name: str
    docments: str | None
    websites: str | None
    user_id: int

    model_config = ConfigDict(from_attributes=True)
class QuestionCreate(BaseModel):
    que:str= Field(min_length=1, max_length=2000)
    system_answer:int
    @field_validator("que")
    @classmethod
    def que_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("que must not be empty")
        return value
class QuestionOut(BaseModel):
    id:int
    que:str
    doc_id:int
    model_config = ConfigDict(from_attributes=True)


class QuestionUpdate(BaseModel):
    que: str | None = Field(default=None, max_length=2000)
    system_answer: int | None = None

    @field_validator("que")
    @classmethod
    def que_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("que must not be empty")
        return value

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("at least one field is required")
        if "que" in self.model_fields_set and self.que is None:
            raise ValueError("que must not be null")
        if (
            "system_answer" in self.model_fields_set
            and self.system_answer is None
        ):
            raise ValueError("system_answer must not be null")
        return self
class AnswerCreate(BaseModel):
    user_answer:str= Field(min_length=1, max_length=2000)
    costtime:int= Field(ge=0)
    @field_validator("user_answer")
    @classmethod
    def user_answer_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("user_answer must not be empty")
        return value
class AnswerOut(BaseModel):
    id: int
    que_id: int
    user_answer: str
    scores: str
    costtime: int
    answer_time: str
    model_config = ConfigDict(from_attributes=True)


class ChunkSearchResult(BaseModel):
    chunk_id: int
    chunk_index: int
    content: str
    score: float


class DocumentIndexOut(BaseModel):
    document_id: int
    chunks: int


class QuestionGenerationRequest(BaseModel):
    focus: str | None = Field(default=None, max_length=500)

    @field_validator("focus")
    @classmethod
    def normalize_focus(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class GeneratedQuestionDraft(BaseModel):
    question: str = Field(min_length=1, max_length=1200)
    expected_answer: str = Field(min_length=1, max_length=4000)
    rubric: list[str] = Field(min_length=1, max_length=8)
    difficulty: Literal["easy", "medium", "hard"]
    source_chunk_ids: list[int] = Field(min_length=1, max_length=8)

    @field_validator("question", "expected_answer")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("rubric")
    @classmethod
    def strip_rubric(cls, value: list[str]) -> list[str]:
        items = [item.strip()[:500] for item in value if item.strip()]
        if not items:
            raise ValueError("rubric must not be empty")
        return items


class GeneratedQuestionOut(GeneratedQuestionDraft):
    model: str
    sources: list[ChunkSearchResult]
