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
from backend.llm import get_embed_model
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
        top_k: int = settings.search_top_k,
    ) -> list[SearchResult]:
        # コレクションが存在しない場合（ドキュメント未登録など）は空リストを返す。
        try:
            col = _client().get_collection(_collection_name(collection_id))
        except Exception:
            return []

        # Phase 3-3: ハイブリッド検索（BM25 + ベクトル検索 + RRF）
        #
        # BM25 と ベクトル検索の結果を RRF（Reciprocal Rank Fusion）で統合する。
        # RRF スコア = Σ 1 / (rrf_k + rank)  ※ rank は 1 始まり
        # 両リストに登場するチャンクはスコアが加算されるため上位になる。

        # ── BM25 キーワード検索 ──
        all_data = col.get()
        all_documents: list[str] = all_data.get("documents") or []
        all_metadatas: list[dict] = all_data.get("metadatas") or []

        bm25_hits: list[tuple[int, float]] = []
        if all_documents:
            tokenized_corpus = [_bigram(doc) for doc in all_documents]
            scores = BM25Okapi(tokenized_corpus).get_scores(_bigram(query))
            ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
            bm25_hits = [(i, s) for i, s in ranked if s > 0][:top_k]

        # ── ベクトル検索 ──
        # n_results がチャンク数を超えるとエラーになるため上限を設ける（RI-05 対応）。
        vector_hits: list[tuple[str, float]] = []
        try:
            query_embedding = get_embed_model().embed([query])[0]
            n_results = min(top_k, col.count())
            if n_results > 0:
                v_result = col.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                )
                v_ids: list[str] = v_result.get("ids", [[]])[0]
                v_distances: list[float] = v_result.get("distances", [[]])[0]
                vector_hits = list(zip(v_ids, v_distances))
        except Exception:
            logger.warning("ベクトル検索に失敗しました。BM25 のみで返します", exc_info=True)

        if not bm25_hits and not vector_hits:
            return []

        # ── RRF 統合 ──
        # chunk_id をキーに RRF スコアを集計する。
        # BM25 は corpus インデックス、ベクトル検索は Chroma の document ID を使うため
        # BM25 側は "bm25_{index}" 形式で仮 ID を発行して統一する。
        rrf_k = settings.rrf_k
        rrf_scores: dict[str, float] = {}

        for rank, (idx, _) in enumerate(bm25_hits, start=1):
            key = f"bm25_{idx}"
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (rrf_k + rank)

        # ベクトル検索の Chroma document ID を BM25 corpus インデックスに逆引きする。
        all_ids: list[str] = all_data.get("ids") or []
        id_to_index: dict[str, int] = {doc_id: i for i, doc_id in enumerate(all_ids)}

        for rank, (chroma_id, _) in enumerate(vector_hits, start=1):
            idx = id_to_index.get(chroma_id)
            if idx is None:
                continue
            key = f"bm25_{idx}"
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (rrf_k + rank)

        # RRF スコアで降順ソートして上位 top_k 件を SearchResult に変換する。
        sorted_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)[:top_k]

        return [
            SearchResult(
                document_id=all_metadatas[int(key.split("_")[1])].get("document_id", 0),
                text=all_documents[int(key.split("_")[1])],
                score=rrf_scores[key],
                metadata=all_metadatas[int(key.split("_")[1])],
            )
            for key in sorted_keys
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
