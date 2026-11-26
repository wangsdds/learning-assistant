# -*- coding: utf-8 -*-
"""API 输出结构。把下面的 TODO 补完。"""
import json
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
    question_type: Literal["numeric", "text"] = "numeric"
    que: str = Field(min_length=1, max_length=2000)
    system_answer: int | None = None
    reference_answer: str | None = Field(default=None, max_length=8000)
    rubric: list[str] | None = Field(default=None, max_length=12)
    difficulty: Literal["easy", "medium", "hard"] | None = None
    source_chunk_ids: list[int] | None = Field(default=None, max_length=20)

    @field_validator("que")
    @classmethod
    def que_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("que must not be empty")
        return value

    @field_validator("reference_answer")
    @classmethod
    def strip_reference_answer(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("rubric")
    @classmethod
    def normalize_rubric(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        items = [item.strip()[:500] for item in value if item.strip()]
        if not items:
            raise ValueError("rubric must not be empty")
        return items

    @model_validator(mode="after")
    def validate_question_type(self):
        if self.question_type == "numeric":
            if self.system_answer is None:
                raise ValueError("numeric questions require system_answer")
            if self.reference_answer or self.rubric:
                raise ValueError("numeric questions cannot use reference_answer or rubric")
        elif not self.reference_answer:
            raise ValueError("text questions require reference_answer")
        return self


class QuestionOut(BaseModel):
    id: int
    que: str
    doc_id: int
    question_type: str = "numeric"
    difficulty: str | None = None
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
    feedback: str | None = None
    rubric_hits: list[str] = Field(default_factory=list)
    rubric_misses: list[str] = Field(default_factory=list)
    grade_model: str | None = None
    model_config = ConfigDict(from_attributes=True)

    @field_validator("rubric_hits", "rubric_misses", mode="before")
    @classmethod
    def parse_json_list(cls, value):
        if value is None or value == "":
            return []
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return []
            return parsed if isinstance(parsed, list) else []
        return value


class GradeRequest(BaseModel):
    user_answer: str = Field(min_length=1, max_length=4000)
    costtime: int = Field(ge=0)

    @field_validator("user_answer")
    @classmethod
    def normalize_answer(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("user_answer must not be empty")
        return value


class GradeOut(BaseModel):
    answer_id: int
    score: int
    feedback: str
    rubric_hits: list[str]
    rubric_misses: list[str]
    model: str


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


class StudyAgentRequest(QuestionGenerationRequest):
    pass


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


class StudyAgentOut(GeneratedQuestionOut):
    tool_calls: int = Field(ge=0)
    steps: int = Field(ge=1)


class QuestionDraftCreate(GeneratedQuestionDraft):
    pass


class GradingDraft(BaseModel):
    score: int = Field(ge=0, le=100)
    rubric_hits: list[str] = Field(default_factory=list, max_length=12)
    rubric_misses: list[str] = Field(default_factory=list, max_length=12)
    feedback: str = Field(min_length=1, max_length=1200)
    confidence: Literal["low", "medium", "high"] = "medium"

    @field_validator("rubric_hits", "rubric_misses")
    @classmethod
    def normalize_items(cls, value: list[str]) -> list[str]:
        return [item.strip()[:500] for item in value if item.strip()]

    @field_validator("feedback")
    @classmethod
    def strip_feedback(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("feedback must not be empty")
        return value
