"""initial: conversations / messages / collections / documents

Revision ID: 0001
Revises:
Create Date: 2026-06-16

教材テンプレートとして、最初の 1 本で最終スキーマを作る。
学習者がスキーマ拡張する際は、ここに頼らず 0002, 0003... を追加していく想定。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── conversations ────────────────────────────────────────────
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ── messages ─────────────────────────────────────────────────
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_messages_conversation_id",
        "messages",
        ["conversation_id"],
    )

    # ── collections ──────────────────────────────────────────────
    op.create_table(
        "collections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ── documents ────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_data", sa.LargeBinary(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collections.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_documents_collection_id",
        "documents",
        ["collection_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_documents_collection_id", table_name="documents")
    op.drop_table("documents")
    op.drop_table("collections")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    op.drop_table("conversations")
