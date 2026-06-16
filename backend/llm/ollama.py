"""Ollama 実装。

ローカル開発の前提実装。`OLLAMA_URL` の HTTP API を直接叩く。

教材としてのねらい:
- LangChain などのラッパ経由ではなく、生 HTTP を見せる
- 何が起きているか（system プロンプトの組み立て・ストリーミング処理）を
  そのままコードから追える
"""

from __future__ import annotations

import json
from typing import AsyncIterator, Iterable

import requests

from backend.config import settings
from backend.logging_config import get_logger

from .chatModel import ChatMessage, ChatModel
from .embedModel import EmbedModel

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Chat
# ──────────────────────────────────────────────


class OllamaChatModel(ChatModel):
    """Ollama /api/chat への薄いラッパ。"""

    def __init__(self) -> None:
        self.base_url = settings.ollama_url
        self.model = settings.ollama_chat_model

    async def stream(self, messages: Iterable[ChatMessage]) -> AsyncIterator[str]:
        """Ollama にストリーミングリクエストを送り、トークンを逐次 yield する。

        Ollama の `stream=True` は NDJSON 形式のレスポンスを返すため、
        1 行ずつパースして `message.content` を取り出す。

        エラー時はログに残すだけで yield しない方針にしている。
        ストリームに混ぜると、その文字列がそのまま会話履歴に保存されてしまうため。
        """
        payload = {
            "model": self.model,
            "messages": list(messages),
            "stream": True,
        }
        try:
            with requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=None,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content")
                    if chunk:
                        yield chunk
                    if data.get("done"):
                        break
        except requests.RequestException:
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
