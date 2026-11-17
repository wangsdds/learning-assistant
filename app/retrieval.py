"""Document indexing and lexical retrieval backed by SQLite FTS5."""
from dataclasses import dataclass
import re

from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.chunking import chunk_text
from app.models import Document, DocumentChunk


_CJK_RUN = re.compile(r"^[\u4e00-\u9fff]+$")


@dataclass(frozen=True)
class SearchHit:
    chunk_id: int
    chunk_index: int
    content: str
    score: float


def _create_fts_table(connection) -> None:
    try:
        connection.exec_driver_sql(
            "CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts "
            "USING fts5(content, content='document_chunks', content_rowid='id', tokenize='trigram')"
        )
    except OperationalError:
        connection.exec_driver_sql(
            "CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts "
            "USING fts5(content, content='document_chunks', content_rowid='id', tokenize='unicode61')"
        )


def ensure_fts_schema(session: Session) -> None:
    """Create the FTS5 index and synchronization triggers when needed."""
    connection = session.connection()
    if connection.dialect.name != "sqlite":
        return

    _create_fts_table(connection)
    connection.exec_driver_sql(
        """
        CREATE TRIGGER IF NOT EXISTS document_chunks_ai
        AFTER INSERT ON document_chunks BEGIN
            INSERT INTO document_chunks_fts(rowid, content)
            VALUES (new.id, new.content);
        END
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TRIGGER IF NOT EXISTS document_chunks_ad
        AFTER DELETE ON document_chunks BEGIN
            INSERT INTO document_chunks_fts(document_chunks_fts, rowid, content)
            VALUES ('delete', old.id, old.content);
        END
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TRIGGER IF NOT EXISTS document_chunks_au
        AFTER UPDATE ON document_chunks BEGIN
            INSERT INTO document_chunks_fts(document_chunks_fts, rowid, content)
            VALUES ('delete', old.id, old.content);
            INSERT INTO document_chunks_fts(rowid, content)
            VALUES (new.id, new.content);
        END
        """
    )


def index_document(session: Session, document: Document) -> int:
    """Replace all chunks for a document and return the new chunk count."""
    ensure_fts_schema(session)
    session.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
    )
    session.flush()

    pieces = chunk_text(document.docments or "")
    for index, content in enumerate(pieces):
        session.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=content,
                char_count=len(content),
            )
        )
    session.flush()
    return len(pieces)


def ensure_document_indexed(session: Session, document: Document) -> int:
    count = session.scalar(
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.document_id == document.id)
    )
    count = count or 0
    if count == 0 and document.docments:
        count = index_document(session, document)
        session.commit()
    return count


def list_chunks(session: Session, document_id: int, limit: int = 5) -> list[SearchHit]:
    chunks = session.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .limit(max(1, min(limit, 20)))
    ).all()
    return [
        SearchHit(
            chunk_id=chunk.id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            score=0.0,
        )
        for chunk in chunks
    ]


def extract_terms(query: str) -> list[str]:
    """Extract useful Latin tokens and CJK trigrams without a word segmenter."""
    normalized = (query or "").lower().strip()
    terms: list[str] = []
    for segment in re.findall(r"[a-z0-9_+]+|[\u4e00-\u9fff]+", normalized):
        if _CJK_RUN.fullmatch(segment):
            if len(segment) <= 3:
                terms.append(segment)
            else:
                terms.extend(segment[index:index + 3] for index in range(len(segment) - 2))
        elif len(segment) >= 2:
            terms.append(segment)

    if not terms and normalized:
        terms.append(normalized[:64])

    unique: list[str] = []
    for term in terms:
        if term and term not in unique:
            unique.append(term)
    return unique[:16]


def _fallback_search(
    session: Session,
    document_id: int,
    terms: list[str],
    top_k: int,
) -> list[SearchHit]:
    if not terms:
        return []
    conditions = [DocumentChunk.content.contains(term) for term in terms]
    chunks = session.scalars(
        select(DocumentChunk).where(
            DocumentChunk.document_id == document_id,
            or_(*conditions),
        )
    ).all()
    ranked: list[SearchHit] = []
    for chunk in chunks:
        lowered = chunk.content.lower()
        score = sum(lowered.count(term) * len(term) for term in terms)
        if score > 0:
            ranked.append(
                SearchHit(
                    chunk_id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    score=round(float(score), 4),
                )
            )
    ranked.sort(key=lambda hit: (-hit.score, hit.chunk_index))
    return ranked[:top_k]


def search_chunks(
    session: Session,
    document_id: int,
    query: str,
    top_k: int = 5,
) -> list[SearchHit]:
    """Search one user-owned document with FTS5, then fall back to LIKE scoring."""
    if not query or not query.strip():
        return []
    top_k = max(1, min(top_k, 20))
    is_sqlite = session.connection().dialect.name == "sqlite"
    if is_sqlite:
        ensure_fts_schema(session)
    terms = extract_terms(query)
    fts_terms = [term for term in terms if len(term) >= 3]

    if is_sqlite and fts_terms:
        fts_query = " OR ".join(
            f'"{term.replace(chr(34), chr(34) * 2)}"' for term in fts_terms
        )
        rows = session.execute(
            text(
                """
                SELECT c.id, c.chunk_index, c.content, bm25(document_chunks_fts) AS rank
                FROM document_chunks_fts
                JOIN document_chunks c ON c.id = document_chunks_fts.rowid
                WHERE document_chunks_fts MATCH :fts_query
                  AND c.document_id = :document_id
                ORDER BY rank
                LIMIT :limit
                """
            ),
            {
                "fts_query": fts_query,
                "document_id": document_id,
                "limit": top_k,
            },
        ).all()
        if rows:
            return [
                SearchHit(
                    chunk_id=row.id,
                    chunk_index=row.chunk_index,
                    content=row.content,
                    score=round(-float(row.rank), 4),
                )
                for row in rows
            ]

    return _fallback_search(session, document_id, terms, top_k)
