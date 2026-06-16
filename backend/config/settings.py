"""環境変数からアプリ設定を読み込む。

教材としてのねらい:
- 1ファイルにまとめておくと、ローカルと AWS の差分が
  どこから来るのか初学者でも把握しやすい
- `.env` を変えるだけで Ollama→Bedrock / Chroma→OpenSearch に
  切り替えできるよう、プロバイダ選択もここに集約する
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# settings は import 時に os.getenv を評価して固定するため、
# どの import 経路から呼ばれても先に .env を読み込んでおく必要がある。
# `load_dotenv()` は冪等（既存環境変数は上書きしない）なので、テスト等で
# 環境変数を明示注入したケースも壊さない。
load_dotenv()

# ──────────────────────────────────────────────
# 設定オブジェクト
# ──────────────────────────────────────────────


@dataclass(frozen=True)
class Settings:
    # DB
    database_url: str

    # CORS
    cors_allow_origins: list[str]

    # LLM プロバイダ選択（"ollama" or "bedrock"）
    llm_provider: str

    # Ollama
    ollama_url: str
    ollama_chat_model: str
    ollama_embed_model: str

    # Bedrock（雛形。AWS 移行時に利用）
    bedrock_region: str
    bedrock_chat_model_id: str
    bedrock_embed_model_id: str

    # Vector DB プロバイダ選択（"chroma" or "opensearch"）
    vector_db_provider: str

    # Chroma
    chroma_host: str
    chroma_port: int

    # OpenSearch（雛形。AWS 移行時に利用）
    opensearch_endpoint: str
    opensearch_index_prefix: str

    # アップロード制限
    max_upload_mb: int

    # ログ
    log_level: str

    # Langfuse（任意）
    langfuse_secret_key: str
    langfuse_public_key: str
    langfuse_host: str


def _split_csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def load_settings() -> Settings:
    """環境変数から Settings を構築する。"""
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL", "postgresql+psycopg://chat:chat@localhost:5432/chat"
        ),
        cors_allow_origins=_split_csv(
            os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000")
        ),
        llm_provider=os.getenv("LLM_PROVIDER", "ollama"),
        ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
        ollama_chat_model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        ollama_embed_model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
        bedrock_region=os.getenv("BEDROCK_REGION", "us-east-1"),
        bedrock_chat_model_id=os.getenv(
            "BEDROCK_CHAT_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"
        ),
        bedrock_embed_model_id=os.getenv(
            "BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0"
        ),
        vector_db_provider=os.getenv("VECTOR_DB_PROVIDER", "chroma"),
        chroma_host=os.getenv("CHROMA_HOST", "localhost"),
        chroma_port=int(os.getenv("CHROMA_PORT", "8001")),
        opensearch_endpoint=os.getenv("OPENSEARCH_ENDPOINT", ""),
        opensearch_index_prefix=os.getenv("OPENSEARCH_INDEX_PREFIX", "rag-chat"),
        max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "50")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
        langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
        langfuse_host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    )


# モジュールロード時に1回だけ評価する
settings = load_settings()
