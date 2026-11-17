import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Document, DocumentChunk, Question, User
from app.schemas import QuestionCreate, QuestionDraftCreate, QuestionOut, QuestionUpdate
from app.security import get_current_user


router = APIRouter(tags=["questions"])


def _validate_chunk_ids(
    session: Session,
    document_id: int,
    chunk_ids: list[int] | None,
) -> list[int]:
    if not chunk_ids:
        return []
    unique_ids = sorted(set(chunk_ids))
    found_ids = set(
        session.scalars(
            select(DocumentChunk.id).where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.id.in_(unique_ids),
            )
        ).all()
    )
    if found_ids != set(unique_ids):
        raise HTTPException(
            status_code=422,
            detail="source_chunk_ids must belong to this document",
        )
    return unique_ids


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
        question_type=payload.question_type,
        que=payload.que,
        system_answer=payload.system_answer,
        reference_answer=payload.reference_answer,
        rubric=json.dumps(payload.rubric, ensure_ascii=False) if payload.rubric else None,
        difficulty=payload.difficulty,
        source_chunk_ids=json.dumps(
            _validate_chunk_ids(session, document_id, payload.source_chunk_ids)
        ),
        doc_id=document_id,
    )
    session.add(question)
    session.commit()
    session.refresh(question)
    return question


@router.post(
    "/documents/{document_id}/questions/from-draft",
    response_model=QuestionOut,
    status_code=201,
)
def create_question_from_draft(
    document_id: int,
    payload: QuestionDraftCreate,
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

    source_chunk_ids = _validate_chunk_ids(
        session,
        document_id,
        payload.source_chunk_ids,
    )
    question = Question(
        question_type="text",
        que=payload.question,
        system_answer=None,
        reference_answer=payload.expected_answer,
        rubric=json.dumps(payload.rubric, ensure_ascii=False),
        difficulty=payload.difficulty,
        source_chunk_ids=json.dumps(source_chunk_ids),
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
