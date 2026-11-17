from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Document, User
from app.schemas import DocumentCreate, DocumentOut
from app.security import get_current_user


router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)
@router.post("/documents", response_model=DocumentOut, status_code=201)
def create_document(
    payload: DocumentCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    document = Document(
        documents_name=payload.documents_name,
        docments=payload.docments,
        websites=payload.websites,
        user_id=current_user.user_id,
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Document, User
from app.schemas import DocumentCreate, DocumentOut
from app.security import get_current_user


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=201)
def create_document(
    payload: DocumentCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    document = Document(
        documents_name=payload.documents_name,
        docments=payload.docments,
        websites=payload.websites,
        user_id=current_user.user_id,
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return session.scalars(
        select(Document)
        .where(Document.user_id == current_user.user_id)
        .order_by(Document.id)
    ).all()


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
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
    return document
