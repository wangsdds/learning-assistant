# -*- coding: utf-8 -*-
"""API 输出结构。把下面的 TODO 补完。"""
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