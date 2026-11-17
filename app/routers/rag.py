from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.llm import LLMError, LLMNotConfigured, generate_question
from app.models import Document, User
from app.retrieval import (
    ensure_document_indexed,
    index_document,
    list_chunks,
    search_chunks,
)
from app.schemas import (
    ChunkSearchResult,
    DocumentIndexOut,
    GeneratedQuestionOut,
    QuestionGenerationRequest,
)
from app.security import get_current_user


router = APIRouter(prefix="/documents", tags=["rag"])


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


@router.post("/{document_id}/reindex", response_model=DocumentIndexOut)
def reindex_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    document = _owned_document(document_id, current_user, session)
    if not document.docments:
        raise HTTPException(
            status_code=409,
            detail="document has no text content to index",
        )
    chunks = index_document(session, document)
    session.commit()
    return DocumentIndexOut(document_id=document.id, chunks=chunks)


@router.get("/{document_id}/search", response_model=list[ChunkSearchResult])
def search_document(
    document_id: int,
    q: str = Query(min_length=1, max_length=500),
    top_k: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    document = _owned_document(document_id, current_user, session)
    ensure_document_indexed(session, document)
    hits = search_chunks(session, document.id, q, top_k)
    return [
        ChunkSearchResult(
            chunk_id=hit.chunk_id,
            chunk_index=hit.chunk_index,
            content=hit.content,
            score=hit.score,
        )
        for hit in hits
    ]


@router.post(
    "/{document_id}/generate-question",
    response_model=GeneratedQuestionOut,
)
def generate_document_question(
    document_id: int,
    payload: QuestionGenerationRequest,
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

    query = payload.focus or document.documents_name
    hits = search_chunks(session, document.id, query, top_k=5)
    if not hits:
        hits = list_chunks(session, document.id, limit=5)

    try:
        draft, model = generate_question(document.documents_name, payload.focus, hits)
    except LLMNotConfigured as exc:
        raise HTTPException(
            status_code=503,
            detail="LLM provider is not configured",
        ) from exc
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    hits_by_id = {hit.chunk_id: hit for hit in hits}
    sources = [
        ChunkSearchResult(
            chunk_id=chunk_id,
            chunk_index=hits_by_id[chunk_id].chunk_index,
            content=hits_by_id[chunk_id].content,
            score=hits_by_id[chunk_id].score,
        )
        for chunk_id in draft.source_chunk_ids
        if chunk_id in hits_by_id
    ]
    return GeneratedQuestionOut(
        **draft.model_dump(),
        model=model,
        sources=sources,
    )
