from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Answer, Document, Question, User
from app.schemas import AnswerCreate, AnswerOut
from app.security import get_current_user


router = APIRouter(prefix="/questions/{question_id}/answers", tags=["answers"])


@router.post("", response_model=AnswerOut, status_code=201)
def create_answer(
    question_id: int,
    payload: AnswerCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    question = session.scalar(
        select(Question)
        .join(Document, Question.doc_id == Document.id)
        .where(
            Question.id == question_id,
            Document.user_id == current_user.user_id,
        )
    )
    if question is None:
        raise HTTPException(status_code=404, detail="question not found")

    scores = "1" if payload.user_answer == str(question.system_answer) else "0"
    answer = Answer(
        user_answer=payload.user_answer,
        scores=scores,
        costtime=payload.costtime,
        answer_time=datetime.now(timezone.utc).isoformat(),
        que_id=question_id,
        owner_id=current_user.user_id,
    )
    session.add(answer)
    session.commit()
    session.refresh(answer)
    return answer


@router.get("", response_model=list[AnswerOut])
def list_answers(
    question_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    question = session.scalar(
        select(Question)
        .join(Document, Question.doc_id == Document.id)
        .where(
            Question.id == question_id,
            Document.user_id == current_user.user_id,
        )
    )
    if question is None:
        raise HTTPException(status_code=404, detail="question not found")

    return session.scalars(
        select(Answer)
        .where(
            Answer.que_id == question_id,
            Answer.owner_id == current_user.user_id,
        )
        .order_by(Answer.id.desc())
    ).all()
