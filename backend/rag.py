import base64
import io
import os
import re

import chromadb
import requests
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from .logging_config import get_logger

logger = get_logger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
VISION_MODEL = os.getenv("VISION_MODEL", "llava")
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8001"))

# ── LangChain / Chroma 初期化（モジュールレベル） ─────────────────────────────

embeddings = OllamaEmbeddings(
    model=EMBEDDING_MODEL,
    base_url=OLLAMA_URL,
    keep_alive=-1,  # メモリに常駐させる（アンロードしない）
)

chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "、", " ", ""],
)

# ── OCR ──────────────────────────────────────────────────────────────────────

_OCR_THRESHOLD = 100  # 平均文字数/ページがこれ未満なら LLM OCR に切り替え


def _extract_with_pypdf(file_data: bytes) -> tuple[list[str], int]:
    """pypdf でページごとにテキストを抽出する。"""
    reader = PdfReader(io.BytesIO(file_data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return pages, len(reader.pages)


def _extract_page_with_llm(image_bytes: bytes) -> str:
    """1 ページ分の画像を Ollama ビジョンモデルに渡してテキストを取得する。"""
    b64 = base64.b64encode(image_bytes).decode()
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": VISION_MODEL,
                "prompt": "この画像に含まれるテキストをすべて抽出してください。",
                "images": [b64],
                "stream": False,
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
    except Exception:
        logger.warning("LLM OCR でページ抽出に失敗しました", exc_info=True)
        return ""


def extract_text(file_data: bytes) -> tuple[str, int]:
    """
    ハイブリッド OCR:
    1. pypdf でテキスト抽出を試みる
    2. 平均テキスト量が少ない場合は Ollama ビジョンモデルで OCR にフォールバック
    戻り値: (全文テキスト, ページ数)
    """
    pages, page_count = _extract_with_pypdf(file_data)
    total_chars = sum(len(p) for p in pages)
    avg_chars = total_chars / max(page_count, 1)

    if avg_chars >= _OCR_THRESHOLD:
        return _collapse_char_spaces("\n\n".join(pages)), page_count

    # LLM OCR にフォールバック
    try:
        from pdf2image import convert_from_bytes

        pil_pages = convert_from_bytes(file_data, fmt="png", dpi=150)
        ocr_texts: list[str] = []
        for pil_page in pil_pages:
            buf = io.BytesIO()
            pil_page.save(buf, format="PNG")
            ocr_texts.append(_extract_page_with_llm(buf.getvalue()))
        return "\n\n".join(ocr_texts), page_count
    except Exception:
        logger.warning("pdf2image/LLM OCR が使えないため pypdf 結果にフォールバック", exc_info=True)
        return "\n\n".join(pages), page_count


# ── テキスト → Markdown 整形 ─────────────────────────────────────────────────

def _collapse_char_spaces(text: str) -> str:
    """
    PDF 抽出時に文字間に挿入されるスペースを除去する。
    例: "株 式 会 社" → "株式会社"
    トークンの 50% 超が 1〜2 文字の行は文字間スペースと判定して結合する。
    """
    lines = text.split("\n")
    result: list[str] = []
    for line in lines:
        tokens = line.split()
        if not tokens:
            result.append("")
            continue
        short = sum(1 for t in tokens if len(t) <= 2)
        if len(tokens) >= 4 and short / len(tokens) > 0.5:
            result.append("".join(tokens))
        else:
            result.append(" ".join(tokens))
    return "\n".join(result)


def format_as_markdown(text: str) -> str:
    """
    PDF から抽出した生テキストを読みやすい Markdown に変換する。
    1. 文字間スペースを除去
    2. ページ区切りを水平線に変換
    3. 段落内の改行を結合
    4. 短い行を見出しに変換
    """
    import re

    # 文字間スペースの除去
    text = _collapse_char_spaces(text)

    # ページ区切り文字 → セクション区切り
    text = text.replace("\x0c", "\n\n---\n\n")

    # 段落ごとに分割
    paragraphs = re.split(r"\n{2,}", text)
    result: list[str] = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if para == "---":
            result.append("---")
            continue

        lines = para.splitlines()

        # 単一行かつ短い行 → 見出し候補
        if len(lines) == 1:
            line = lines[0].strip()
            if (
                len(line) <= 50
                and not re.search(r"[。、．，.,:：]$", line)
                and re.search(r"[\w\u3000-\u9fff]", line)
            ):
                result.append(f"## {line}")
                continue

        # 複数行段落: 改行を結合
        joined = "".join(line.strip() for line in lines if line.strip())
        result.append(joined)

    return "\n\n".join(result)


# ── 親子チャンク分割 ─────────────────────────────────────────────────────────

def split_into_parent_chunks(text: str) -> list[dict]:
    """
    Markdown 見出し（#）でテキストを親チャンクに分割する。
    見出しがない場合はテキスト全体を1つの親チャンクとして扱う。
    戻り値: [{"heading": str, "content": str}, ...]
    """
    # 見出し行で分割（見出しレベルは問わない）
    parts = re.split(r"(?m)^(#{1,6}\s+.+)$", text)

    chunks: list[dict] = []
    current_heading = ""
    current_body = ""

    for part in parts:
        part_stripped = part.strip()
        if re.match(r"^#{1,6}\s+", part_stripped):
            # 前のセクションを保存
            if current_heading or current_body.strip():
                chunks.append({
                    "heading": current_heading,
                    "content": (current_heading + "\n" + current_body).strip(),
                })
            current_heading = part_stripped
            current_body = ""
        else:
            current_body += part

    # 最後のセクション
    if current_heading or current_body.strip():
        chunks.append({
            "heading": current_heading,
            "content": (current_heading + "\n" + current_body).strip() if current_heading else current_body.strip(),
        })

    # 見出しが一切なく空の場合はテキスト全体を1チャンクに
    if not chunks and text.strip():
        chunks.append({"heading": "", "content": text.strip()})

    return chunks


def split_parent_into_children(parent_text: str) -> list[str]:
    """親チャンクをさらに子チャンクに分割する。"""
    return text_splitter.split_text(parent_text)


def split_text(text: str) -> list[str]:
    """RecursiveCharacterTextSplitter でテキストを分割する（後方互換）。"""
    return text_splitter.split_text(text)


# ── ベクトルストア操作 ────────────────────────────────────────────────────────

def _get_vectorstore(collection_id: int) -> Chroma:
    return Chroma(
        collection_name=f"col_{collection_id}",
        embedding_function=embeddings,
        client=chroma_client,
    )


def add_to_vectorstore(collection_id: int, document_id: int, chunks: list[str]) -> None:
    """
    親子チャンク構造で Chroma に追加する。
    1. format_as_markdown 済みテキストを見出しで親チャンクに分割
    2. 親チャンクごとに子チャンクを生成
    3. 親・子それぞれを Chroma に保存（type メタデータで区別）
    """
    # chunks 引数は後方互換のため受け取るが、実際は text から再構築する
    # ただし呼び出し元が既にテキスト全体を渡すように変更する
    if not chunks:
        return
    # chunks が1つ = フルテキストとして親子分割する場合
    # chunks が複数 = 旧形式（フルテキストを結合して再分割）
    full_text = "\n\n".join(chunks)
    _add_parent_child_chunks(collection_id, document_id, full_text)


def _add_parent_child_chunks(collection_id: int, document_id: int, text: str) -> None:
    """
    親子チャンクを生成して ChromaDB に保存する。
    - 子チャンクのみ embedding して ChromaDB に保存
    - 親チャンクの内容は子チャンクの metadata (parent_content) に格納
    """
    vs = _get_vectorstore(collection_id)
    parent_chunks = split_into_parent_chunks(text)

    all_texts: list[str] = []
    all_metadatas: list[dict] = []
    all_ids: list[str] = []

    for pi, parent in enumerate(parent_chunks):
        parent_id = f"doc{document_id}_parent{pi}"

        # 子チャンクを生成して保存（embedding は子チャンクのみ）
        children = split_parent_into_children(parent["content"])
        for ci, child in enumerate(children):
            all_texts.append(child)
            all_metadatas.append({
                "document_id": document_id,
                "chunk_type": "child",
                "parent_index": pi,
                "parent_id": parent_id,
                "parent_content": parent["content"],
                "heading": parent["heading"],
                "child_index": ci,
            })
            all_ids.append(f"doc{document_id}_parent{pi}_child{ci}")

    if all_texts:
        vs.add_texts(texts=all_texts, metadatas=all_metadatas, ids=all_ids)


def delete_document_from_vectorstore(collection_id: int, document_id: int) -> None:
    """ドキュメントに属する全チャンクを Chroma から削除する。"""
    try:
        vs = _get_vectorstore(collection_id)
        result = vs._collection.get(where={"document_id": document_id})
        if result["ids"]:
            vs.delete(ids=result["ids"])
    except Exception:
        logger.warning(
            "ベクトルストアからのドキュメント削除に失敗: collection_id=%s document_id=%s",
            collection_id, document_id, exc_info=True,
        )


def delete_vectorstore(collection_id: int) -> None:
    """コレクション全体を Chroma から削除する。"""
    try:
        chroma_client.delete_collection(f"col_{collection_id}")
    except Exception:
        logger.warning(
            "コレクションの削除に失敗: collection_id=%s", collection_id, exc_info=True,
        )


# 句読点・空白・記号で文字列を分割するための正規表現
_PUNCT_RE = re.compile(
    r"[\s、。，．・「」『』【】〈〉《》〔〕"
    r"！？!?,.;:()（）\[\]{}<>＜＞\-_/\\|~〜=+*&%$#@\"'`…―ー]+"
)
# 英数字の連続を 1 語として扱うための正規表現
_WORD_RE = re.compile(r"[a-z0-9]+")


def _bigrams(text: str) -> list[str]:
    """日本語向けの文字 bi-gram を生成する。1 文字以下は単体トークンとして扱う。"""
    if len(text) <= 1:
        return [text] if text else []
    return [text[i : i + 2] for i in range(len(text) - 1)]


def _japanese_bm25_tokens(text: str) -> list[str]:
    """
    日本語対応の BM25 トークナイザ。
    - 英数字の連続語はそのまま 1 トークン
    - 日本語等は文字 bi-gram に分解
    - 句読点・空白は捨てる
    BM25Retriever / rerank の双方で、語境界に依存しない部分一致を可能にするのが目的。
    """
    text = text.lower()
    tokens: list[str] = []
    for segment in _PUNCT_RE.split(text):
        if not segment:
            continue
        last_end = 0
        for m in _WORD_RE.finditer(segment):
            ja = segment[last_end : m.start()]
            tokens.extend(_bigrams(ja))
            tokens.append(m.group(0))
            last_end = m.end()
        tokens.extend(_bigrams(segment[last_end:]))
    return tokens


def _query_match_tokens(query: str) -> list[str]:
    """rerank 用にクエリから一致候補トークンを取り出す（bi-gram + 英数字語）。"""
    return list(dict.fromkeys(_japanese_bm25_tokens(query)))


def rerank(query: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
    """
    クエリと子チャンクの一致度でランク付けして返す。
    - 一致は日本語 bi-gram + 英数字語で評価し、形態素解析なしでも複合語の部分一致を拾う
    - ヒット 0 のチャンクが多くても、上位は RRF 順で必ず埋めて返す
      （以前はヒット 0 を全除外していたため、トークナイズが粗い場合に正解チャンクごと欠落していた）
    """
    if not chunks:
        return []

    tokens = _query_match_tokens(query)
    if not tokens:
        return chunks[:top_n]

    candidates = chunks[:20]

    scored: list[tuple[int, int]] = []
    for i, chunk in enumerate(candidates):
        child = (chunk.get("child_content") or "").lower()
        if not child:
            scored.append((i, 0))
            continue
        hits = sum(1 for tok in tokens if tok in child)
        scored.append((i, hits))

    scored.sort(key=lambda x: (-x[1], x[0]))  # ヒット数降順、同点は RRF 順を維持

    ordered = [candidates[i] for i, _ in scored]
    # ヒット 1 以上を優先しつつ、足りなければ RRF 順で埋める（空返しを避ける）
    matched = [c for c, (_, hits) in zip(ordered, scored) if hits > 0]
    if len(matched) >= top_n:
        return matched[:top_n]
    seen = {id(c) for c in matched}
    for c in ordered:
        if len(matched) >= top_n:
            break
        if id(c) not in seen:
            matched.append(c)
            seen.add(id(c))
    return matched[:top_n]


def _rrf_merge(ranked_lists: list[list[str]], k: int = 60) -> list[str]:
    """
    Reciprocal Rank Fusion で複数のランキングリストを統合する。
    score(d) = Σ 1 / (k + rank(d))
    """
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, doc in enumerate(ranked, start=1):
            scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda d: scores[d], reverse=True)


def retrieve_chunks(query: str, collection_id: int, top_k: int = 40) -> list[dict]:
    """
    親子チャンク対応ハイブリッド検索:
    1. 子チャンクのみを対象に BM25 + ベクトル検索を実行
    2. ヒットした子チャンクの親チャンクを取得
    3. 重複排除して親チャンクを返す（LLM にはより広い文脈を渡す）

    戻り値: [{
        "content": str (親チャンク),
        "child_content": str (マッチした子チャンク),
        "heading": str,
        "document_id": int | None,
    }, ...]
    """
    try:
        from langchain_community.retrievers import BM25Retriever
        from langchain_core.documents import Document as LCDocument

        vs = _get_vectorstore(collection_id)

        # コレクション内の全チャンクを取得
        all_data = vs._collection.get()
        if not all_data["documents"]:
            return []

        metadatas = all_data["metadatas"] or []

        # 子チャンクだけを抽出（親チャンクの内容は metadata に格納済み）
        child_texts: list[str] = []
        child_metas: list[dict] = []
        child_ids: list[str] = []

        for text, meta, cid in zip(all_data["documents"], metadatas, all_data["ids"]):
            if not meta:
                continue
            chunk_type = meta.get("chunk_type", "")
            if chunk_type == "child":
                child_texts.append(text)
                child_metas.append(meta)
                child_ids.append(cid)
            elif chunk_type == "" and "parent_content" not in (meta or {}):
                # 旧形式データ
                child_texts.append(text)
                child_metas.append(meta)
                child_ids.append(cid)

        # 子チャンクがない場合はフォールバック
        if not child_texts:
            return _retrieve_chunks_legacy(query, collection_id, top_k)

        # chunk_type が設定されていない場合は旧形式
        has_parent_child = any(m.get("chunk_type") == "child" for m in child_metas)
        if not has_parent_child:
            return _retrieve_chunks_legacy(query, collection_id, top_k)

        # 子チャンクでのみ検索
        child_docs = [LCDocument(page_content=t, metadata=m) for t, m in zip(child_texts, child_metas)]

        # ── BM25（キーワード）検索 ──
        # 日本語向け bi-gram トークナイザを渡さないと、デフォルトの空白トークナイザでは
        # 文単位でしか分割されず BM25 がほぼ機能しない。
        bm25_retriever = BM25Retriever.from_documents(
            child_docs, preprocess_func=_japanese_bm25_tokens,
        )
        bm25_retriever.k = top_k
        bm25_results = bm25_retriever.invoke(query)

        # ── ベクトル類似度検索（子チャンクのみフィルタ） ──
        vector_results_raw = vs.similarity_search(
            query, k=top_k, filter={"chunk_type": "child"},
        )

        # RRF 用に子チャンクIDでランキング
        def _child_id(doc: LCDocument) -> str:
            pi = doc.metadata.get("parent_index", 0)
            ci = doc.metadata.get("child_index", 0)
            did = doc.metadata.get("document_id", 0)
            return f"doc{did}_parent{pi}_child{ci}"

        bm25_ranked = [_child_id(d) for d in bm25_results]
        vector_ranked = [_child_id(d) for d in vector_results_raw]
        merged_ids = _rrf_merge([bm25_ranked, vector_ranked])

        # 子チャンクID → メタデータ・テキストのマップ
        child_id_map: dict[str, tuple[str, dict]] = {
            cid: (text, meta) for cid, text, meta in zip(child_ids, child_texts, child_metas)
        }

        # チャンク単位で返す（重複排除、順序保持）
        seen_cids: set[str] = set()
        results: list[dict] = []
        for cid in merged_ids:
            if cid not in child_id_map or cid in seen_cids:
                continue
            seen_cids.add(cid)
            child_text, child_meta = child_id_map[cid]
            parent_content = child_meta.get("parent_content", child_text)
            results.append({
                "content": parent_content,
                "child_content": child_text,
                "heading": child_meta.get("heading", ""),
                "document_id": child_meta.get("document_id"),
            })

            if len(results) >= top_k:
                break

        return results

    except Exception:
        logger.exception("retrieve_chunks に失敗: collection_id=%s", collection_id)
        return []


def _retrieve_chunks_legacy(query: str, collection_id: int, top_k: int = 40) -> list[dict]:
    """旧形式（親子なし）のチャンクに対するフォールバック検索。"""
    from langchain_community.retrievers import BM25Retriever
    from langchain_core.documents import Document as LCDocument

    vs = _get_vectorstore(collection_id)
    all_data = vs._collection.get()
    if not all_data["documents"]:
        return []

    content_to_doc_id: dict[str, int | None] = {
        text: (meta.get("document_id") if meta else None)
        for text, meta in zip(all_data["documents"], all_data["metadatas"] or [])
    }
    all_docs = [LCDocument(page_content=t) for t in all_data["documents"]]

    bm25_retriever = BM25Retriever.from_documents(
        all_docs, preprocess_func=_japanese_bm25_tokens,
    )
    bm25_retriever.k = top_k
    bm25_results = [d.page_content for d in bm25_retriever.invoke(query)]
    vector_results = [d.page_content for d in vs.similarity_search(query, k=top_k)]

    merged = _rrf_merge([bm25_results, vector_results])[:top_k]
    return [
        {"content": c, "child_content": c, "heading": "", "document_id": content_to_doc_id.get(c)}
        for c in merged
    ]
