"""ChromaDB 実装（ローカル前提）。

教材初期段階では HTTP モードの ChromaDB に接続するだけのラッパ。
中身の実装は Phase 2〜3 で埋めていく前提なので、ここでは
- クライアント初期化
- コレクション取得
- delete 系
だけ動く状態にし、検索系は NotImplementedError を投げて
「次にここを実装するんだな」と分かるようにしてある。

依存関係:
  Phase 2-1: upsert を実装すると、初めて Chroma にデータが入る
  Phase 2-2: search を実装すると、RAG モードでヒットが返るようになる
  delete_document/delete_collection は upsert より前に呼ばれることはないが、
    API ハンドラ側からは独立して叩かれるので先に動く形で残してある
"""

from __future__ import annotations

from typing import Iterable

import chromadb

from backend.config import settings
from backend.logging_config import get_logger

from .vectorDB import Chunk, SearchResult, VectorDB

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# クライアント
# ──────────────────────────────────────────────


def _client() -> chromadb.HttpClient:
    """ChromaDB クライアントを取得する。"""
    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)


def _collection_name(collection_id: int) -> str:
    """コレクションIDからChroma上のコレクション名を作る。"""
    return f"col_{collection_id}"


# ──────────────────────────────────────────────
# 実装
# ──────────────────────────────────────────────


class ChromaVectorDB(VectorDB):
    """ChromaDB への薄いラッパ。"""

    def upsert(self, collection_id: int, chunks: Iterable[Chunk]) -> None:
        # Phase 2 (キーワード検索) / Phase 3 (ベクトル検索) で実装する想定。
        # NOTE: 実装時は chroma の collection.add(ids=..., documents=..., embeddings=..., metadatas=...) を使う。
        raise NotImplementedError(
            "ChromaVectorDB.upsert は Phase 2-1 (ファイル取り込み) で実装してください。"
        )

    def search(
        self,
        collection_id: int,
        query: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        # Phase 2-2 (キーワード検索) → Phase 3-2 (ベクトル検索) で実装する想定。
        raise NotImplementedError(
            "ChromaVectorDB.search は Phase 2-2 (キーワード検索) で実装してください。"
        )

    def delete_collection(self, collection_id: int) -> None:
        """コレクションを物理削除する。

        ドキュメント未登録時に呼ばれても、存在しなければ何もしない
        ように try/except でガードする（教材として安全側）。
        """
        try:
            _client().delete_collection(_collection_name(collection_id))
        except Exception:
            logger.warning(
                "コレクション削除に失敗しました: collection_id=%s",
                collection_id,
                exc_info=True,
            )

    def delete_document(self, collection_id: int, document_id: int) -> None:
        # Phase 2-1 で upsert が実装されてから本実装する想定。
        # NOTE: 実装時は collection.delete(where={"document_id": document_id}) を使う。
        try:
            client = _client()
            try:
                col = client.get_collection(_collection_name(collection_id))
            except Exception:
                # コレクション未作成なら何もしない
                return
            col.delete(where={"document_id": document_id})
        except Exception:
            logger.warning(
                "ドキュメント削除に失敗しました: collection_id=%s document_id=%s",
                collection_id,
                document_id,
                exc_info=True,
            )
