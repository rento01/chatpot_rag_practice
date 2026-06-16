"""EmbedModel: 埋め込み生成の共通インターフェース。

教材初期段階では rag.py がまだ embedding を使わないため、
Phase 3 (embedding 生成 / ベクトル検索) で初めて利用する想定。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.config import settings


class EmbedModel(ABC):
    """埋め込みモデルの共通インターフェース。"""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """テキスト列を埋め込みベクトル列に変換する。"""
        raise NotImplementedError


def get_embed_model() -> EmbedModel:
    """`.env` の LLM_PROVIDER に応じて埋め込みモデル実装を返す。

    Chat と Embed を別プロバイダにする要件が出るまでは
    同じ LLM_PROVIDER の値で揃える。
    """
    provider = settings.llm_provider.lower()
    if provider == "ollama":
        from .ollama import OllamaEmbedModel

        return OllamaEmbedModel()
    if provider == "bedrock":
        from .bedrock import BedrockEmbedModel

        return BedrockEmbedModel()
    raise ValueError(f"未対応の LLM_PROVIDER です: {settings.llm_provider}")
