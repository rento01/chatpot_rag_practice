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
from rank_bm25 import BM25Okapi

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


def _bigram(text: str) -> list[str]:
    """文字 bigram でトークナイズする。

    日本語は空白分割では単語が切れないため、2 文字ずつスライドさせて
    トークン列を作る。1 文字の場合はその 1 文字をそのまま返す。
    """
    text = text.lower()
    if len(text) < 2:
        return [text] if text else []
    return [text[i : i + 2] for i in range(len(text) - 1)]


# ──────────────────────────────────────────────
# 実装
# ──────────────────────────────────────────────


class ChromaVectorDB(VectorDB):
    """ChromaDB への薄いラッパ。"""

    def upsert(self, collection_id: int, chunks: Iterable[Chunk]) -> None:
        chunk_list = list(chunks)
        if not chunk_list:
            return

        col = _client().get_or_create_collection(_collection_name(collection_id))

        ids = [f"doc_{c.document_id}_chunk_{i}" for i, c in enumerate(chunk_list)]
        documents = [c.text for c in chunk_list]
        metadatas = [{"document_id": c.document_id} for c in chunk_list]

        # embedding が渡されている場合（Phase 3-1 以降）のみ embeddings を明示する。
        # None のままの場合は Chroma のデフォルト埋め込み関数に任せる。
        embeddings = [c.embedding for c in chunk_list] if any(c.embedding for c in chunk_list) else None

        col.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)

    def search(
        self,
        collection_id: int,
        query: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        # コレクションが存在しない場合（ドキュメント未登録など）は空リストを返す。
        try:
            col = _client().get_collection(_collection_name(collection_id))
        except Exception:
            return []

        result = col.get()
        documents: list[str] = result.get("documents") or []
        metadatas: list[dict] = result.get("metadatas") or []

        if not documents:
            return []

        # 文字 bigram でトークナイズし BM25 スコアを算出する。
        # 日本語は空白で単語が切れないため、文字単位のスライドウィンドウで対応する。
        # Phase 2-2 では「まず動かして観察する」方針のため形態素解析は導入しない。
        tokenized_corpus = [_bigram(doc) for doc in documents]
        scores = BM25Okapi(tokenized_corpus).get_scores(_bigram(query))

        # score > 0 のものだけを有効ヒットとして上位 top_k 件返す。
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        hits = [(i, s) for i, s in ranked if s > 0][:top_k]

        return [
            SearchResult(
                document_id=metadatas[i].get("document_id", 0),
                text=documents[i],
                score=float(score),
                metadata=metadatas[i],
            )
            for i, score in hits
        ]

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
