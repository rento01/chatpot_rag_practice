"""API リクエスト/レスポンス用の Pydantic スキーマ。

教材としての最小構成。RAG 機能の拡張で必要になったら、
このファイルに追加していく。
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ──────────────────────────────────────────────
# 会話 / メッセージ
# ──────────────────────────────────────────────


class Message(BaseModel):
    """チャット送信時の 1 メッセージ。"""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """`POST /chat` のリクエストボディ。

    - `use_rag` が True かつ `collection_id` 指定で RAG モード
    - どちらかが欠ければ通常チャットとして扱う
    """

    messages: list[Message] = Field(..., min_length=1)
    conversation_id: int | None = None
    collection_id: int | None = None
    use_rag: bool = False


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationUpdate(BaseModel):
    title: str | None = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


# ──────────────────────────────────────────────
# コレクション / ドキュメント
# ──────────────────────────────────────────────


class CollectionCreate(BaseModel):
    name: str


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    filename: str
    page_count: int | None
    file_size: int
    status: str
    indexed_at: datetime | None
    created_at: datetime


class CollectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    documents: list[DocumentOut] = []
