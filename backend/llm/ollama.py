"""Ollama 実装。

ローカル開発の前提実装。
チャット呼び出しは LangChain (`langchain-ollama` の `ChatOllama`) 経由で
行い、トークンストリーミングは `astream()` で受け取る。

教材としてのねらい:
- LangChain の ChatModel と BaseMessage / astream に慣れる
- 生 HTTP / NDJSON パースは LangChain 側に隠蔽してもらう代わりに、
  呼び出し側（`backend/main.py`）で ChatPromptTemplate を組み立てる流れに触れる

埋め込み (OllamaEmbedModel) は Phase 3 用の雛形なのでここでは触らない。
"""

from __future__ import annotations

from typing import AsyncIterator, Sequence

import httpx
import requests
from langchain_core.messages import BaseMessage
from langchain_ollama import ChatOllama

from backend.config import settings
from backend.logging_config import get_logger

from .chatModel import ChatModel
from .embedModel import EmbedModel

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Chat
# ──────────────────────────────────────────────


class OllamaChatModel(ChatModel):
    """LangChain `ChatOllama` への薄いラッパ。"""

    def __init__(self) -> None:
        # NOTE: LangChain のクライアントを保持する。base_url / model は
        # 既存どおり .env の設定値をそのまま使う。
        self._llm = ChatOllama(
            base_url=settings.ollama_url,
            model=settings.ollama_chat_model,
        )

    async def stream(self, messages: Sequence[BaseMessage]) -> AsyncIterator[str]:
        """LangChain の astream() でトークンを逐次 yield する。

        実装メモ:
        - エラー時はログに残すだけで yield しない（ストリームに混ぜると
          そのまま会話履歴に保存されてしまうため）
        - chunk は AIMessageChunk。`content` の型は LangChain 上
          `str | list[str | dict]`（マルチモーダル対応）。Ollama 経由では実質
          str しか来ないが、念のため isinstance ガードで弾く
        - 例外は接続系（httpx.HTTPError）とそれ以外でログメッセージを分ける。
          バグ要因の例外も log には残るので、ローカルで気づきやすくしてある
        """
        try:
            async for chunk in self._llm.astream(list(messages)):
                content = getattr(chunk, "content", "")
                if isinstance(content, str) and content:
                    yield content
        except httpx.HTTPError:
            logger.exception("Ollama 接続エラー")
        except Exception:
            logger.exception("Ollama チャット呼び出しに失敗しました")
            # ストリームには何も流さない（呼び出し元では空応答 = 履歴に保存しない）


# ──────────────────────────────────────────────
# Embedding
# ──────────────────────────────────────────────


class OllamaEmbedModel(EmbedModel):
    """Ollama /api/embeddings への薄いラッパ。

    Phase 3 (embedding 生成) で初めて利用する想定。
    """

    def __init__(self) -> None:
        self.base_url = settings.ollama_url
        self.model = settings.ollama_embed_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for text in texts:
            resp = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=60,
            )
            resp.raise_for_status()
            results.append(resp.json().get("embedding", []))
        return results
