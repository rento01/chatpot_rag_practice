"""RAG のメイン開発部分（教材本体）。

教材初期段階の方針:
- 検索ロジックはまだ書かない（VectorDB は upsert/search を NotImplementedError）
- ファイルは LargeBinary として DB に入っているだけ
- `build_context()` は「参照できる文書がまだありません」相当を返す
  → 学習者が Phase 2 以降で順に埋めていく

実装する順番（ROAD_MAP.md にも記載）:
  Phase 2-1: extract_text と VectorDB.upsert を埋めて取り込み完成
  Phase 2-2: VectorDB.search のキーワード検索を実装
  Phase 3-1: embedModel.embed を使って embedding を生成
  Phase 3-2: ベクトル検索 + ハイブリッド検索
  Phase 5  : チャンク分割改善
  Phase 6  : rerank 追加
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from pypdf import PdfReader

from backend.logging_config import get_logger
from backend.vector_db import get_vector_db

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# 教材向け定数
# ──────────────────────────────────────────────

NO_DOCUMENTS_MESSAGE = (
    "（参照できる文書がまだありません。Phase 2 以降で `backend/rag.py` と "
    "`backend/vector_db/chroma.py` を実装すると、ここに検索結果が入ります）"
)


# ──────────────────────────────────────────────
# 文書取り込み（薄ラッパ）
# ──────────────────────────────────────────────


def extract_text(file_data: bytes) -> tuple[str, int]:
    """PDF からテキストを抽出して `(本文, ページ数)` を返す。

    教材としてはまず pypdf のみのシンプル実装。
    OCR 等のフォールバックは扱わない（必要になったら学習者が拡張する）。
    """
    reader = PdfReader(io.BytesIO(file_data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages), len(reader.pages)


def split_into_chunks(text: str) -> list[str]:
    """テキストをチャンクに分割する。

    教材初期段階では実装しない。Phase 2-1 で
    `langchain_text_splitters.RecursiveCharacterTextSplitter` などを
    使って実装する想定。
    """
    # NOTE: ここを Phase 2-1 で実装する。
    return []


def index_document(collection_id: int, document_id: int, file_data: bytes) -> int:
    """1 ドキュメントをチャンクに分割して VectorDB に投入する。

    戻り値はページ数。`backend.main._index_document` がそのまま
    `documents.page_count` に書き込むので、ここで 1 回 PDF をパースすれば足りる
    （main 側で重ねて extract_text を呼ばないため）。

    Phase 2-1 で本格実装する想定。教材初期段階では
    extract_text までは動くが、VectorDB.upsert が未実装なので
    呼ぶと NotImplementedError になる。
    """
    # NOTE: Phase 2-1 で以下のような流れを実装する想定:
    #   text, page_count = extract_text(file_data)
    #   chunks = split_into_chunks(text)
    #   vdb = get_vector_db()
    #   vdb.upsert(collection_id, [Chunk(document_id=document_id, text=c) for c in chunks])
    #   return page_count
    raise NotImplementedError(
        "index_document は Phase 2-1 (ファイル取り込み) で実装してください。"
    )


# ──────────────────────────────────────────────
# RAG クエリ（薄ラッパ）
# ──────────────────────────────────────────────


@dataclass
class RagContext:
    """RAG モードで LLM に渡すコンテキスト。

    `context_text` が空（=ヒットなし）の場合、main.py 側で
    「資料に記載がありません」と返す方針にする。
    """

    context_text: str
    has_hits: bool


def build_context(query: str, collection_id: int) -> RagContext:
    """RAG コンテキストを組み立てる薄ラッパ。

    教材初期段階では VectorDB.search が NotImplementedError なので、
    safe に `try` で握りつぶして「文書がまだありません」を返す。
    Phase 2-2 で search を埋めれば自然に検索ヒットが返るようになる。
    """
    try:
        vdb = get_vector_db()
        hits = vdb.search(collection_id, query)
    except NotImplementedError:
        # 教材初期段階の想定どおり: VectorDB 未実装
        return RagContext(context_text=NO_DOCUMENTS_MESSAGE, has_hits=False)
    except Exception:
        logger.exception("RAG 検索に失敗しました: collection_id=%s", collection_id)
        return RagContext(context_text=NO_DOCUMENTS_MESSAGE, has_hits=False)

    if not hits:
        return RagContext(context_text=NO_DOCUMENTS_MESSAGE, has_hits=False)

    # コンテキストの組み立て方は Phase 2-2 以降で見直していく想定。
    blocks = [f"【資料{i + 1}】\n{h.text}" for i, h in enumerate(hits)]
    return RagContext(context_text="\n\n===\n\n".join(blocks), has_hits=True)
