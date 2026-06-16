# [P3 DeepResearch] クエリ分解 → サブクエリ検索・リランク → 統合要約のパイプライン
# ジョブの進捗はインメモリ dict で管理し、ポーリング API で返す。
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from enum import Enum
from threading import Thread
from typing import Any

import requests

from . import rag

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


# ---------------------------------------------------------------------------
# データモデル
# ---------------------------------------------------------------------------

class JobStatus(str, Enum):
    DECOMPOSING = "decomposing"
    SEARCHING = "searching"
    SYNTHESIZING = "synthesizing"
    DONE = "done"
    ERROR = "error"


class SubQueryStatus(str, Enum):
    PENDING = "pending"
    SEARCHING = "searching"
    DONE = "done"


@dataclass
class SourceChunk:
    source_file: str
    heading: str
    content: str
    document_id: int | None = None


@dataclass
class SubQueryResult:
    sub_query: str
    status: SubQueryStatus = SubQueryStatus.PENDING
    sources: list[SourceChunk] = field(default_factory=list)


@dataclass
class ResearchJob:
    id: str
    query: str
    collection_id: int
    conversation_id: int | None = None
    status: JobStatus = JobStatus.DECOMPOSING
    sub_queries: list[SubQueryResult] = field(default_factory=list)
    final_answer: str | None = None
    error: str | None = None


# インメモリのジョブストア
_jobs: dict[str, ResearchJob] = {}


def get_job(job_id: str) -> ResearchJob | None:
    return _jobs.get(job_id)


def job_to_dict(job: ResearchJob) -> dict[str, Any]:
    return {
        "job_id": job.id,
        "status": job.status.value,
        "query": job.query,
        "sub_queries": [
            {
                "sub_query": sq.sub_query,
                "status": sq.status.value,
                "sources": [
                    {
                        "source_file": s.source_file,
                        "heading": s.heading,
                        "content": s.content,
                        "document_id": s.document_id,
                    }
                    for s in sq.sources
                ],
            }
            for sq in job.sub_queries
        ],
        "final_answer": job.final_answer,
        "error": job.error,
    }


# ---------------------------------------------------------------------------
# Ollama API ヘルパー（main.py と同じパターン）
# ---------------------------------------------------------------------------

def _ollama_generate(prompt: str) -> str:
    """Ollama /api/generate を同期で呼び出し、レスポンステキストを返す。"""
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


# ---------------------------------------------------------------------------
# Step 1: クエリ分解 — LLM でサブクエリを生成
# ---------------------------------------------------------------------------

_DECOMPOSE_PROMPT = """\
あなたはリサーチアシスタントです。
ユーザーの質問をより深く調査するために、異なる角度から検索すべきサブクエリを3〜5個生成してください。

ルール:
- 各サブクエリは1行に1つ
- 番号やリスト記号は付けないでください
- サブクエリのみを出力し、他の説明は不要です

ユーザーの質問:
{query}
"""


def _decompose_query(query: str) -> list[str]:
    """LLM を使ってユーザークエリをサブクエリに分解する。"""
    raw = _ollama_generate(_DECOMPOSE_PROMPT.format(query=query))
    lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
    return lines


# ---------------------------------------------------------------------------
# Step 2: サブクエリごとの検索 + リランク（rag.py の既存機能を利用）
# ---------------------------------------------------------------------------

def _search_and_rerank(sub_query: str, collection_id: int) -> list[SourceChunk]:
    """1 つのサブクエリに対して rag.retrieve_chunks → rag.rerank を実行。"""
    chunks = rag.retrieve_chunks(sub_query, collection_id)
    if not chunks:
        return []
    top_chunks = rag.rerank(sub_query, chunks, top_n=5)
    return [
        SourceChunk(
            source_file=f"doc_{c.get('document_id', '?')}",
            heading=c.get("heading", ""),
            content=c.get("content", c.get("child_content", "")),
            document_id=c.get("document_id"),
        )
        for c in top_chunks
    ]


# ---------------------------------------------------------------------------
# Step 3: 統合・要約生成
# ---------------------------------------------------------------------------

_SYNTHESIZE_PROMPT = """\
あなたは優秀なリサーチアシスタントです。
ユーザーの質問に対して、複数の角度から収集した情報を統合し、包括的で正確な回答を生成してください。

## ユーザーの質問
{query}

## 調査したサブクエリと取得した情報
{sub_query_results}

## 指示
- 各サブクエリの調査結果を統合し、元の質問に対する包括的な回答を作成してください
- 情報源が明確な場合は引用してください
- 矛盾する情報がある場合は、その旨を記載してください
- 調査で見つからなかった点があれば正直に述べてください
"""


def _synthesize(query: str, sub_query_results: list[SubQueryResult]) -> str:
    """全サブクエリの結果を統合して最終回答を生成する。"""
    parts = []
    for sq in sub_query_results:
        section = f"### サブクエリ: {sq.sub_query}\n"
        if sq.sources:
            for src in sq.sources:
                section += f"- [{src.heading or src.source_file}] {src.content[:200]}\n"
        else:
            section += "- (関連情報なし)\n"
        parts.append(section)
    sub_query_text = "\n".join(parts)
    return _ollama_generate(
        _SYNTHESIZE_PROMPT.format(query=query, sub_query_results=sub_query_text)
    )


# ---------------------------------------------------------------------------
# ジョブ実行（バックグラウンドスレッド）
# ---------------------------------------------------------------------------

def start_research(query: str, collection_id: int, conversation_id: int | None = None) -> str:
    """DeepResearch ジョブを開始し、job_id を返す。"""
    job_id = str(uuid.uuid4())
    job = ResearchJob(
        id=job_id, query=query,
        collection_id=collection_id, conversation_id=conversation_id,
    )
    _jobs[job_id] = job
    thread = Thread(target=_run_research, args=(job,), daemon=True)
    thread.start()
    return job_id


def _run_research(job: ResearchJob) -> None:
    """バックグラウンドスレッドで DeepResearch パイプラインを実行する。"""
    try:
        # Step 1: クエリ分解
        job.status = JobStatus.DECOMPOSING
        sub_queries = _decompose_query(job.query)
        job.sub_queries = [SubQueryResult(sub_query=sq) for sq in sub_queries]

        # Step 2: サブクエリごとの検索・リランク
        job.status = JobStatus.SEARCHING
        for sq_result in job.sub_queries:
            sq_result.status = SubQueryStatus.SEARCHING
            sources = _search_and_rerank(sq_result.sub_query, job.collection_id)
            sq_result.sources = sources
            sq_result.status = SubQueryStatus.DONE

        # Step 3: 統合・要約生成
        job.status = JobStatus.SYNTHESIZING
        final_answer = _synthesize(job.query, job.sub_queries)
        job.final_answer = final_answer
        job.status = JobStatus.DONE

    except Exception as e:
        job.status = JobStatus.ERROR
        job.error = str(e)
