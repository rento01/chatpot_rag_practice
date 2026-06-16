"""LLM 呼び出しの薄いラッパ群。

教材としてのねらい:
- 共通インターフェース (`ChatModel` / `EmbedModel`) を分離しておくと、
  ローカル (Ollama) と AWS (Bedrock) の切り替え観点が見通しやすい
- 実装の差し替えは `get_chat_model()` / `get_embed_model()` を経由する
"""

from .chatModel import ChatModel, get_chat_model
from .embedModel import EmbedModel, get_embed_model

__all__ = [
    "ChatModel",
    "EmbedModel",
    "get_chat_model",
    "get_embed_model",
]
