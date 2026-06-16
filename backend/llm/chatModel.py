"""ChatModel: チャット用 LLM 呼び出しの共通インターフェース。

`stream()` でトークンを逐次返す async generator を返す方針。
ストリーミング前提にしておけば、フロントエンドの体験を変えずに
プロバイダだけ差し替えできる。

引数の型は LangChain の `BaseMessage` 列に揃えている。
呼び出し側（`backend/main.py`）で `ChatPromptTemplate.format_messages()` を
通すことで、SystemMessage / HumanMessage / AIMessage が宣言的に組まれる前提。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Sequence

from langchain_core.messages import BaseMessage

from backend.config import settings


class ChatModel(ABC):
    """チャット LLM の共通インターフェース。"""

    @abstractmethod
    def stream(self, messages: Sequence[BaseMessage]) -> AsyncIterator[str]:
        """LangChain の BaseMessage 列を渡し、トークンを逐次返す。"""
        raise NotImplementedError


# ──────────────────────────────────────────────
# プロバイダ選択
# ──────────────────────────────────────────────


def get_chat_model() -> ChatModel:
    """`.env` の LLM_PROVIDER に応じて実装を返す。

    教材としては「最初は ollama 一択 → Phase 7 で bedrock を有効化」を想定。
    """
    provider = settings.llm_provider.lower()
    if provider == "ollama":
        from .ollama import OllamaChatModel

        return OllamaChatModel()
    if provider == "bedrock":
        from .bedrock import BedrockChatModel

        return BedrockChatModel()
    raise ValueError(f"未対応の LLM_PROVIDER です: {settings.llm_provider}")
