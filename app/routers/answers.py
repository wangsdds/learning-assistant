import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.llm import LLMError, LLMNotConfigured, grade_answer
from app.models import Answer, Document, Question, User
from app.schemas import AnswerCreate, AnswerOut, GradeOut, GradeRequest
from app.security import get_current_user


router = APIRouter(prefix="/questions/{question_id}/answers", tags=["answers"])


def _owned_question(
    question_id: int,
    current_user: User,
    session: Session,
) -> Question:
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
    return question


@router.post("", response_model=AnswerOut, status_code=201)
def create_answer(
    question_id: int,
    payload: AnswerCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    question = _owned_question(question_id, current_user, session)
    if question.question_type != "numeric":
        raise HTTPException(
            status_code=409,
            detail="text questions must be submitted to the grade endpoint",
        )
    if question.system_answer is None:
        raise HTTPException(
            status_code=409,
            detail="question has no numeric answer",
        )

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


@router.post("/grade", response_model=GradeOut, status_code=201)
def grade_text_answer(
    question_id: int,
    payload: GradeRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    question = _owned_question(question_id, current_user, session)
    if question.question_type != "text":
        raise HTTPException(
            status_code=409,
            detail="only text questions can be graded by the model",
        )
    if not question.reference_answer:
        raise HTTPException(
            status_code=409,
            detail="question has no reference answer",
        )

    try:
        rubric = json.loads(question.rubric or "[]")
    except json.JSONDecodeError:
        rubric = []
    if not isinstance(rubric, list):
        rubric = []

    try:
        draft, model = grade_answer(
            question=question.que,
            reference_answer=question.reference_answer,
            rubric=[str(item) for item in rubric],
            user_answer=payload.user_answer,
        )
    except LLMNotConfigured as exc:
        raise HTTPException(
            status_code=503,
            detail="LLM provider is not configured",
        ) from exc
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    answer = Answer(
        user_answer=payload.user_answer,
        scores=str(draft.score),
        costtime=payload.costtime,
        answer_time=datetime.now(timezone.utc).isoformat(),
        feedback=draft.feedback,
        rubric_hits=json.dumps(draft.rubric_hits, ensure_ascii=False),
        rubric_misses=json.dumps(draft.rubric_misses, ensure_ascii=False),
        grade_model=model,
        que_id=question_id,
        owner_id=current_user.user_id,
    )
    session.add(answer)
    session.commit()
    session.refresh(answer)
    return GradeOut(
        answer_id=answer.id,
        score=draft.score,
        feedback=draft.feedback,
        rubric_hits=draft.rubric_hits,
        rubric_misses=draft.rubric_misses,
        model=model,
    )


@router.get("", response_model=list[AnswerOut])
def list_answers(
    question_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _owned_question(question_id, current_user, session)

    return session.scalars(
        select(Answer)
        .where(
            Answer.que_id == question_id,
            Answer.owner_id == current_user.user_id,
        )
        .order_by(Answer.id.desc())
    ).all()
