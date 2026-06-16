"""AWS OpenSearch Vector DB 実装の雛形。

Phase 7 (AWS 移行) で実装する想定の placeholder。

想定構成:
- backend (ECS/Fargate) から OpenSearch Serverless (VECTORSEARCH 用途) を呼ぶ
- 認証は SigV4 (IAM)
- インデックス名は OPENSEARCH_INDEX_PREFIX + "_col_<collection_id>"
- ハイブリッド検索 (BM25 + k-NN) は OpenSearch の neural search プラグイン or アプリ側 RRF で実現
"""

from __future__ import annotations

from typing import Iterable

from backend.config import settings

from .vectorDB import Chunk, SearchResult, VectorDB


class OpenSearchVectorDB(VectorDB):
    """OpenSearch ベクトル検索の薄いラッパ（雛形）。"""

    def __init__(self) -> None:
        self.endpoint = settings.opensearch_endpoint
        self.index_prefix = settings.opensearch_index_prefix
        # NOTE: 本実装時に opensearch-py クライアントを初期化する。
        # self._client = OpenSearch(hosts=[self.endpoint], http_auth=AWSV4SignerAuth(...))

    def _index_name(self, collection_id: int) -> str:
        return f"{self.index_prefix}_col_{collection_id}"

    def upsert(self, collection_id: int, chunks: Iterable[Chunk]) -> None:
        raise NotImplementedError(
            "OpenSearchVectorDB.upsert は Phase 7 (AWS 移行) で実装してください。"
        )

    def search(
        self,
        collection_id: int,
        query: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        raise NotImplementedError(
            "OpenSearchVectorDB.search は Phase 7 (AWS 移行) で実装してください。"
        )

    def delete_collection(self, collection_id: int) -> None:
        raise NotImplementedError(
            "OpenSearchVectorDB.delete_collection は Phase 7 (AWS 移行) で実装してください。"
        )

    def delete_document(self, collection_id: int, document_id: int) -> None:
        raise NotImplementedError(
            "OpenSearchVectorDB.delete_document は Phase 7 (AWS 移行) で実装してください。"
        )
