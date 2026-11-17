from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Document, Question, User
from app.schemas import QuestionCreate, QuestionOut, QuestionUpdate
from app.security import get_current_user


router = APIRouter(tags=["questions"])


@router.post(
    "/documents/{document_id}/questions",
    response_model=QuestionOut,
    status_code=201,
)
def create_question(
    document_id: int,
    payload: QuestionCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    document = session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.user_id,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")

    question = Question(
        que=payload.que,
        system_answer=payload.system_answer,
        doc_id=document_id,
    )
    session.add(question)
    session.commit()
    session.refresh(question)
    return question


@router.get(
    "/documents/{document_id}/questions",
    response_model=list[QuestionOut],
)
def list_questions(
    document_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    document = session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.user_id,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")

    return session.scalars(
        select(Question)
        .where(Question.doc_id == document_id)
        .order_by(Question.id)
    ).all()


@router.patch(
    "/questions/{question_id}",
    response_model=QuestionOut,
)
def update_question(
    question_id: int,
    payload: QuestionUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    question = session.scalar(
        select(Question).where(Question.id == question_id)
    )
    if question is None:
        raise HTTPException(status_code=404, detail="question not found")

    document = session.scalar(
        select(Document).where(
            Document.id == question.doc_id,
            Document.user_id == current_user.user_id,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="question not found")

    updates = payload.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(question, field, value)

    session.commit()
    session.refresh(question)

    return question
