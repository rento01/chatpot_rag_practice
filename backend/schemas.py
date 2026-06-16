from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[Message] = Field(..., min_length=1)
    conversation_id: int | None = None
    collection_id: int | None = None


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationUpdate(BaseModel):
    title: str | None = None
    pinned: bool | None = None
    archived: bool | None = None


class SourceOut(BaseModel):
    id: int
    filename: str
    heading: str | None = None
    content: str | None = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    sources_json: str | None = None
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None
    pinned: bool
    archived: bool
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


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


# [P3 DeepResearch]
class DeepResearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    collection_id: int
    conversation_id: int | None = None
