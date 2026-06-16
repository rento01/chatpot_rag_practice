"""Vector DB の薄いラッパ群。

教材としてのねらい:
- `VectorDB` 共通インターフェースを通して読み・書きを行えば、
  ローカル (Chroma) と AWS (OpenSearch) を `.env` で切り替えられる
- Phase 2 (キーワード検索) → Phase 3 (ベクトル検索) と段階的に
  実装を埋めていけるよう、メソッド単位で空実装を残してある
"""

from .vectorDB import VectorDB, get_vector_db

__all__ = ["VectorDB", "get_vector_db"]
