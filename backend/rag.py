"""RAG のメイン開発部分（教材本体）。

教材初期段階の方針:
- 検索ロジックはまだ書かない（VectorDB は upsert/search を NotImplementedError）
- ファイルは LargeBinary として DB に入っているだけ
- `build_context()` は「参照できる文書がまだありません」相当を返す
  → 学習者が Phase 2 以降で順に埋めていく

実装する順番（reference/ROAD_MAP.md にも記載）:
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

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from backend.llm import get_embed_model
from backend.logging_config import get_logger
from backend.tracing import span as tracing_span
from backend.vector_db import get_vector_db
from backend.vector_db.vectorDB import Chunk

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

    Phase 2 では固定長で OK なので、RecursiveCharacterTextSplitter を
    シンプルな設定で使う。chunk_overlap=50 は前後の文脈が切れにくくするため。
    Phase 5 でチャンク分割を改善する想定。
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    return splitter.split_text(text)


def index_document(collection_id: int, document_id: int, file_data: bytes) -> int:
    """1 ドキュメントをチャンクに分割して VectorDB に投入する。

    戻り値はページ数。`backend.main._index_document` がそのまま
    `documents.page_count` に書き込むので、ここで 1 回 PDF をパースすれば足りる
    （main 側で重ねて extract_text を呼ばないため）。

    各処理ステップは tracing_span() で記録される。
    呼び出し元の trace("index-document") が OTel コンテキストを保持しているため、
    ここで作る span は自動的に index-document の子になる。
    """
    # テキスト抽出
    with tracing_span(name="extract", input={"file_size": len(file_data)}) as s_extract:
        text, page_count = extract_text(file_data)
        s_extract.update(output={"page_count": page_count})

    # チャンク分割
    with tracing_span(name="split", input={"text_length": len(text)}) as s_split:
        chunks = split_into_chunks(text)
        s_split.update(output={"chunk_count": len(chunks)})

    # スキャン PDF など、テキストが抽出できなかった場合は upsert をスキップする。
    if chunks:
        # embedding 生成。失敗時は warning ログを出して embedding=None のままフォールバックし、
        # upsert 自体は継続する（BM25 キーワード検索は embedding なしでも動作するため）。
        logger.info("embedding 生成を開始: %d チャンク", len(chunks))
        with tracing_span(name="embed", input={"chunk_count": len(chunks)}) as s_embed:
            try:
                embeddings: list[list[float] | None] = get_embed_model().embed(chunks)
                logger.info("embedding 生成を完了: %d チャンク", len(chunks))
                s_embed.update(output={"status": "ok"})
            except Exception:
                logger.warning(
                    "embedding 生成に失敗しました。embedding なしで upsert を継続します",
                    exc_info=True,
                )
                s_embed.update(output={"status": "failed"})
                embeddings = [None] * len(chunks)

        with tracing_span(name="upsert", input={"chunk_count": len(chunks)}) as s_upsert:
            vdb = get_vector_db()
            vdb.upsert(
                collection_id,
                [Chunk(document_id=document_id, text=c, embedding=e) for c, e in zip(chunks, embeddings)],
            )
            s_upsert.update(output={"chunk_count": len(chunks)})

    return page_count


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
