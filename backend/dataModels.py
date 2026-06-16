"""SQLAlchemy データモデル定義。

教材としての最小スキーマ:
- conversations / messages : 会話履歴
- collections / documents : RAG 用の文書管理

ファイル名は Issue 指定に従って `dataModels.py`（キャメルケース）にしている。
"""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from backend.db import Base

# ──────────────────────────────────────────────
# 会話履歴
# ──────────────────────────────────────────────


class Conversation(Base):
    """会話 1 セッションを表す。"""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )


class Message(Base):
    """会話に紐づく 1 メッセージ。"""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


# 会話一覧で「何メッセージあるか」だけ知りたいケース用。
# correlated subquery にして N+1 を避ける。
Conversation.message_count = column_property(  # type: ignore[attr-defined]
    select(func.count(Message.id))
    .where(Message.conversation_id == Conversation.id)
    .correlate_except(Message)
    .scalar_subquery()
)


# ──────────────────────────────────────────────
# RAG 用の文書管理
# ──────────────────────────────────────────────


class Collection(Base):
    """文書コレクション（テーマ単位のフォルダのようなもの）。"""

    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="Document.id",
    )


class Document(Base):
    """コレクションに登録された 1 ドキュメント。

    教材初期段階では PDF のみ受け付ける想定。
    file_data はバイト列のまま DB に保管しておく。
      （S3 への退避は Phase 7 (AWS 移行) で検討する）
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    # status: pending / indexing / ready / error
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    collection: Mapped[Collection] = relationship(back_populates="documents")
