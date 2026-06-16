"""AWS Bedrock 実装の雛形。

Phase 7 (AWS 移行) で実装する想定の placeholder。
ここでは「将来こう繋ぐ」という設計意図をコメントで残しておく。

想定構成:
- backend (ECS/Fargate or EKS) から Bedrock を PrivateLink (VPC エンドポイント) 経由で呼び出す
- 認証は ECS タスクロール / EC2 インスタンスロール経由の IAM
- リージョンは BEDROCK_REGION で切り替え
- モデル ID は BEDROCK_CHAT_MODEL_ID / BEDROCK_EMBED_MODEL_ID

学習者向け補足:
- ローカルで動かすつもりは無いので import boto3 はあえて遅延 import にしてある
- 本実装する際は `backend.llm.chatModel.get_chat_model()` の分岐に
  `LLM_PROVIDER=bedrock` を渡せばここに切り替わる
"""

from __future__ import annotations

from typing import AsyncIterator, Iterable

from backend.config import settings

from .chatModel import ChatMessage, ChatModel
from .embedModel import EmbedModel


class BedrockChatModel(ChatModel):
    """Bedrock Converse / InvokeModel への薄いラッパ（雛形）。"""

    def __init__(self) -> None:
        self.region = settings.bedrock_region
        self.model_id = settings.bedrock_chat_model_id
        # NOTE: 本実装時に boto3 セッションをここで作る。
        # self._client = boto3.client("bedrock-runtime", region_name=self.region)

    async def stream(self, messages: Iterable[ChatMessage]) -> AsyncIterator[str]:
        # NOTE: 本実装時には bedrock-runtime の converse_stream を使う想定。
        #   for event in self._client.converse_stream(...)["stream"]:
        #       delta = event.get("contentBlockDelta", {}).get("delta", {}).get("text")
        #       if delta:
        #           yield delta
        raise NotImplementedError(
            "BedrockChatModel は雛形です。Phase 7 (AWS 移行) で実装してください。"
        )
        # 型チェックを満たすためのダミー
        if False:  # pragma: no cover
            yield ""


class BedrockEmbedModel(EmbedModel):
    """Bedrock Titan Embed への薄いラッパ（雛形）。"""

    def __init__(self) -> None:
        self.region = settings.bedrock_region
        self.model_id = settings.bedrock_embed_model_id

    def embed(self, texts: list[str]) -> list[list[float]]:
        # NOTE: 本実装時には bedrock-runtime の invoke_model を使う想定。
        raise NotImplementedError(
            "BedrockEmbedModel は雛形です。Phase 7 (AWS 移行) で実装してください。"
        )
