from fastapi import APIRouter, Depends, HTTPException
from pydantic_ai import AgentRunError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.llm import LLMNotConfigured
from app.models import Document, User
from app.retrieval import ensure_document_indexed
from app.schemas import (
    ChunkSearchResult,
    StudyAgentOut,
    StudyAgentRequest,
)
from app.security import get_current_user
from app.study_agent import StudyDeps, run_study_agent


router = APIRouter(prefix="/documents", tags=["study-agent"])


def _owned_document(
    document_id: int,
    current_user: User,
    session: Session,
) -> Document:
    document = session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.user_id,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    return document


@router.post(
    "/{document_id}/study-agent",
    response_model=StudyAgentOut,
)
async def generate_study_agent_draft(
    document_id: int,
    payload: StudyAgentRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    document = _owned_document(document_id, current_user, session)
    chunk_count = ensure_document_indexed(session, document)
    if chunk_count == 0:
        raise HTTPException(
            status_code=409,
            detail="document has no text content to generate from",
        )

    deps = StudyDeps(
        session=session,
        user_id=current_user.user_id,
        document_id=document.id,
    )
    try:
        run = await run_study_agent(
            deps,
            document_name=document.documents_name,
            focus=payload.focus,
        )
    except LLMNotConfigured as exc:
        raise HTTPException(
            status_code=503,
            detail="LLM provider is not configured",
        ) from exc
    except AgentRunError as exc:
        raise HTTPException(
            status_code=502,
            detail="study agent could not produce a grounded draft",
        ) from exc

    missing_ids = set(run.draft.source_chunk_ids) - set(deps.retrieved_hits)
    if missing_ids:
        raise HTTPException(
            status_code=502,
            detail="study agent returned invalid source chunks",
        )

    sources = [
        ChunkSearchResult(
            chunk_id=chunk_id,
            chunk_index=deps.retrieved_hits[chunk_id].chunk_index,
            content=deps.retrieved_hits[chunk_id].content,
            score=deps.retrieved_hits[chunk_id].score,
        )
        for chunk_id in run.draft.source_chunk_ids
    ]
    return StudyAgentOut(
        **run.draft.model_dump(),
        model=run.model,
        sources=sources,
        tool_calls=run.tool_calls,
        steps=run.steps,
    )
