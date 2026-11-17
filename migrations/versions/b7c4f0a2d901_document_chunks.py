"""document chunks and full-text index

Revision ID: b7c4f0a2d901
Revises: f683734084d5
Create Date: 2026-11-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError


revision: str = "b7c4f0a2d901"
down_revision: Union[str, Sequence[str], None] = "f683734084d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_fts(connection) -> None:
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


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_index",
        ),
    )
    op.create_index(
        "ix_document_chunks_document_id",
        "document_chunks",
        ["document_id"],
        unique=False,
    )

    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        _create_fts(connection)
        connection.exec_driver_sql(
            "INSERT INTO document_chunks_fts(document_chunks_fts) VALUES('rebuild')"
        )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        connection.exec_driver_sql("DROP TRIGGER IF EXISTS document_chunks_au")
        connection.exec_driver_sql("DROP TRIGGER IF EXISTS document_chunks_ad")
        connection.exec_driver_sql("DROP TRIGGER IF EXISTS document_chunks_ai")
        connection.exec_driver_sql("DROP TABLE IF EXISTS document_chunks_fts")

    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
