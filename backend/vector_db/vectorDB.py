"""VectorDB 共通インターフェース。

Phase 2〜Phase 6 で段階的に各メソッドを実装していく想定。
初期状態では、まだ何も実装されていないので
`backend.rag` は「文書がまだありません」を返すだけになる。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable

from backend.config import settings

# ──────────────────────────────────────────────
# 共通データクラス
# ──────────────────────────────────────────────


@dataclass(frozen=True)
class Chunk:
    """ベクトルDBに保存する 1 チャンクを表す。

    教材初期段階では `embedding` は未使用（キーワード検索のみ）でもよい。
    Phase 3 でベクトル検索を実装したら埋めていく。
    """

    document_id: int
    text: str
    embedding: list[float] | None = None
    metadata: dict | None = None


@dataclass(frozen=True)
class SearchResult:
    """検索結果の 1 件。"""

    document_id: int
    text: str
    score: float
    metadata: dict | None = None


# ──────────────────────────────────────────────
# 共通インターフェース
# ──────────────────────────────────────────────


class VectorDB(ABC):
    """Vector DB の共通インターフェース。"""

    @abstractmethod
    def upsert(self, collection_id: int, chunks: Iterable[Chunk]) -> None:
        """コレクションにチャンクを追加（or 更新）する。"""
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        collection_id: int,
        query: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """クエリで検索して上位を返す。

        Phase 2 ではキーワード検索、Phase 3 でベクトル検索、
        Phase 6 で rerank と段階的に拡張していく想定。
        """
        raise NotImplementedError

    @abstractmethod
    def delete_collection(self, collection_id: int) -> None:
        """コレクションごと削除する。"""
        raise NotImplementedError

    @abstractmethod
    def delete_document(self, collection_id: int, document_id: int) -> None:
        """指定ドキュメントに紐づくチャンクをすべて削除する。"""
        raise NotImplementedError


# ──────────────────────────────────────────────
# プロバイダ選択
# ──────────────────────────────────────────────


def get_vector_db() -> VectorDB:
    """`.env` の VECTOR_DB_PROVIDER に応じて実装を返す。"""
    provider = settings.vector_db_provider.lower()
    if provider == "chroma":
        from .chroma import ChromaVectorDB

        return ChromaVectorDB()
    if provider == "opensearch":
        from .opensearch import OpenSearchVectorDB

        return OpenSearchVectorDB()
    raise ValueError(
        f"未対応の VECTOR_DB_PROVIDER です: {settings.vector_db_provider}"
    )
