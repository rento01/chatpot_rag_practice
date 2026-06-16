import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated

import requests
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import deep_research, models, rag, schemas
from .db import SessionLocal, get_db, run_migrations
from .logging_config import get_logger, setup_logging
from .tracing import trace

load_dotenv()
setup_logging()
logger = get_logger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# 通常チャット（コレクション未選択）用の最小限のシステムプロンプト
SYSTEM_GENERAL = "あなたは親切なアシスタントです。必ず日本語で回答してください。"

# 参照ドキュメントが見つかったときの RAG 用システムプロンプト
SYSTEM_RAG_TEMPLATE = """あなたは社内規程文書を参照して質問に回答するアシスタントです。

## 厳守事項
1. 必ず日本語で回答してください。中国語・英語などの他言語の混入は禁止です。
2. 回答は以下の参照ドキュメントの内容のみを根拠としてください。一般知識や推測で補完してはいけません。
3. 参照ドキュメントに該当する記述が含まれている場合は、必ずその箇所を原文のまま引用してから要約してください。引用は本文の前か後ろに記載してください。
4. 数値（日数・金額・時間など）や固有表現は、参照ドキュメントの表記を改変せず正確に使ってください。
5. 参照ドキュメントを十分に読み込んだ上で、関連する記述が一切見つからない場合に限り「資料に記載がありません」と回答してください。

## 参照ドキュメント
{context}"""

# 検索ヒットなしの場合のシステムプロンプト
SYSTEM_RAG_NO_HIT = (
    "あなたは社内規程文書を参照して質問に回答するアシスタントです。"
    "選択されたコレクションを検索しましたが、質問に関連する記述は見つかりませんでした。"
    "推測で回答せず、必ず日本語で『資料に記載がありません』と回答してください。"
)

CORS_ALLOW_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
ALLOWED_UPLOAD_MIME = {"application/pdf"}


def _sync_vectorstore_on_startup() -> None:
    """ChromaDB とDB の整合性をチェックし、データがなければ再インデックスする。"""
    with SessionLocal() as db:
        collections = list(db.scalars(select(models.Collection)))
        for col in collections:
            try:
                chroma_col = rag.chroma_client.get_collection(f"col_{col.id}")
                count = chroma_col.count()
            except Exception:
                count = 0

            docs = list(db.scalars(
                select(models.Document).where(
                    models.Document.collection_id == col.id,
                    models.Document.status == "ready",
                )
            ))
            if count == 0 and docs:
                import logging
                logging.info("Re-indexing collection %d (%s): %d docs", col.id, col.name, len(docs))
                for doc in docs:
                    doc.status = "pending"
                db.commit()
                for doc in docs:
                    _index_document(doc.id, col.id, doc.file_data)


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    _sync_vectorstore_on_startup()
    yield


app = FastAPI(title="Ollama チャット API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = Annotated[Session, Depends(get_db)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL, "ollama_url": OLLAMA_URL}


@app.post(
    "/conversations",
    response_model=schemas.ConversationOut,
    status_code=201,
)
def create_conversation(
    payload: schemas.ConversationCreate, db: DB
) -> models.Conversation:
    conv = models.Conversation(title=payload.title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@app.get("/conversations", response_model=list[schemas.ConversationOut])
def list_conversations(
    db: DB,
    q: str | None = Query(default=None, description="タイトルで絞り込み"),
) -> list[models.Conversation]:
    stmt = select(models.Conversation).order_by(
        models.Conversation.updated_at.desc()
    )
    if q:
        stmt = stmt.where(models.Conversation.title.ilike(f"%{q}%"))
    return list(db.scalars(stmt))


@app.get(
    "/conversations/{conversation_id}",
    response_model=schemas.ConversationDetail,
)
def get_conversation(conversation_id: int, db: DB) -> models.Conversation:
    conv = db.get(models.Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="会話が見つかりません")
    return conv


@app.patch(
    "/conversations/{conversation_id}",
    response_model=schemas.ConversationOut,
)
def update_conversation(
    conversation_id: int, payload: schemas.ConversationUpdate, db: DB
) -> models.Conversation:
    conv = db.get(models.Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="会話が見つかりません")
    if payload.title is not None:
        conv.title = payload.title
    if payload.pinned is not None:
        conv.pinned = payload.pinned
    if payload.archived is not None:
        conv.archived = payload.archived
    db.commit()
    db.refresh(conv)
    return conv


@app.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int, db: DB) -> None:
    conv = db.get(models.Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="会話が見つかりません")
    db.delete(conv)
    db.commit()


# ──────────────────────────────────────────────
# Collections & Documents
# ──────────────────────────────────────────────

@app.post("/collections", response_model=schemas.CollectionOut, status_code=201)
def create_collection(payload: schemas.CollectionCreate, db: DB) -> models.Collection:
    col = models.Collection(name=payload.name)
    db.add(col)
    db.commit()
    db.refresh(col)
    return col


@app.get("/collections", response_model=list[schemas.CollectionOut])
def list_collections(db: DB) -> list[models.Collection]:
    return list(db.scalars(select(models.Collection).order_by(models.Collection.created_at.desc())))


@app.delete("/collections/{collection_id}", status_code=204)
def delete_collection(collection_id: int, db: DB) -> None:
    col = db.get(models.Collection, collection_id)
    if col is None:
        raise HTTPException(status_code=404, detail="コレクションが見つかりません")
    rag.delete_vectorstore(collection_id)
    db.delete(col)
    db.commit()


def _index_document(doc_id: int, collection_id: int, file_data: bytes) -> None:
    """Background task: extract text, chunk, embed into ChromaDB, update status."""
    with SessionLocal() as db:
        doc = db.get(models.Document, doc_id)
        if doc is None:
            return
        doc.status = "indexing"
        db.commit()

        with trace("index-document", input={"doc_id": doc_id, "collection_id": collection_id, "file_size": len(file_data)}) as t:
            try:
                extract_span = t.span(name="extract-text")
                text, page_count = rag.extract_text(file_data)
                md_text = rag.format_as_markdown(text)
                extract_span.end(output={"page_count": page_count, "text_length": len(md_text)})

                embed_span = t.span(name="embed-and-store")
                rag.add_to_vectorstore(collection_id, doc_id, [md_text])
                embed_span.end()

                doc = db.get(models.Document, doc_id)
                if doc:
                    doc.status = "ready"
                    doc.page_count = page_count
                    doc.indexed_at = datetime.now(timezone.utc)
                    db.commit()
                t.update(output={"status": "ready", "page_count": page_count})
            except Exception as e:
                logger.exception("Failed to index document %s", doc_id)
                doc = db.get(models.Document, doc_id)
                if doc:
                    doc.status = "error"
                    db.commit()
                t.update(output={"status": "error", "error": str(e)})


@app.post("/collections/{collection_id}/documents", response_model=list[schemas.DocumentOut], status_code=201)
async def upload_documents(
    collection_id: int,
    background_tasks: BackgroundTasks,
    db: DB,
    files: list[UploadFile] = File(...),
) -> list[models.Document]:
    col = db.get(models.Collection, collection_id)
    if col is None:
        raise HTTPException(status_code=404, detail="コレクションが見つかりません")

    created: list[models.Document] = []
    for upload in files:
        if not upload.filename or not upload.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=415,
                detail=f"PDF ファイルのみ受け付けます: {upload.filename}",
            )
        if upload.content_type and upload.content_type not in ALLOWED_UPLOAD_MIME:
            raise HTTPException(
                status_code=415,
                detail=f"Content-Type は application/pdf のみ許可: {upload.content_type}",
            )
        file_data = await upload.read()
        if len(file_data) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"ファイルサイズが上限 {MAX_UPLOAD_MB}MB を超えています: {upload.filename}",
            )

        doc = models.Document(
            collection_id=collection_id,
            filename=upload.filename,
            file_data=file_data,
            page_count=None,
            file_size=len(file_data),
            status="pending",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        background_tasks.add_task(_index_document, doc.id, collection_id, file_data)
        created.append(doc)

    return created


@app.post("/collections/{collection_id}/reindex", status_code=200)
def reindex_collection(collection_id: int, background_tasks: BackgroundTasks, db: DB) -> dict:
    """コレクション内の全ドキュメントを再インデックスする。"""
    col = db.get(models.Collection, collection_id)
    if col is None:
        raise HTTPException(status_code=404, detail="コレクションが見つかりません")
    rag.delete_vectorstore(collection_id)
    docs = list(db.scalars(
        select(models.Document).where(models.Document.collection_id == collection_id)
    ))
    for doc in docs:
        doc.status = "pending"
    db.commit()
    for doc in docs:
        background_tasks.add_task(_index_document, doc.id, collection_id, doc.file_data)
    return {"queued": len(docs)}


@app.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int, db: DB) -> None:
    doc = db.get(models.Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="ドキュメントが見つかりません")
    rag.delete_document_from_vectorstore(doc.collection_id, document_id)
    db.delete(doc)
    db.commit()


@app.get("/documents/{document_id}/text")
def get_document_text(document_id: int, db: DB) -> dict:
    doc = db.get(models.Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="ドキュメントが見つかりません")
    try:
        text, _ = rag.extract_text(doc.file_data)
        text = rag.format_as_markdown(text)
    except Exception:
        logger.exception("テキスト抽出に失敗しました: document_id=%s", document_id)
        text = ""
    return {"text": text, "filename": doc.filename}


@app.get("/documents/{document_id}/file")
def get_document_file(document_id: int, db: DB) -> Response:
    doc = db.get(models.Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="ドキュメントが見つかりません")
    return Response(
        content=doc.file_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{doc.filename}"'},
    )


# ──────────────────────────────────────────────
# Deep Research
# ──────────────────────────────────────────────

@app.post("/deep-research", status_code=202)
def start_deep_research(req: schemas.DeepResearchRequest, db: DB) -> dict:
    """DeepResearch ジョブを開始する。"""
    col = db.get(models.Collection, req.collection_id)
    if col is None:
        raise HTTPException(status_code=404, detail="コレクションが見つかりません")
    if req.conversation_id is not None:
        conv = db.get(models.Conversation, req.conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="会話が見つかりません")
        db.add(models.Message(
            conversation_id=req.conversation_id, role="user", content=req.query,
        ))
        db.commit()
    job_id = deep_research.start_research(
        query=req.query,
        collection_id=req.collection_id,
        conversation_id=req.conversation_id,
    )
    return {"job_id": job_id}


@app.get("/deep-research/{job_id}/progress")
def get_deep_research_progress(job_id: str) -> dict:
    """DeepResearch ジョブの進捗を返す。"""
    job = deep_research.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    return deep_research.job_to_dict(job)


@app.post("/deep-research/{job_id}/save")
def save_deep_research_result(job_id: str, db: DB) -> dict:
    """完了した DeepResearch の結果を会話メッセージとして保存する。"""
    job = deep_research.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    if job.final_answer is None:
        raise HTTPException(status_code=400, detail="リサーチ未完了")
    if job.conversation_id is None:
        raise HTTPException(status_code=400, detail="conversation_id が未設定")
    msg = models.Message(
        conversation_id=job.conversation_id, role="assistant", content=job.final_answer,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"assistant_message_id": msg.id}


# ──────────────────────────────────────────────
# Chat
# ──────────────────────────────────────────────

@app.post("/chat")
async def chat(req: schemas.ChatRequest, db: DB) -> StreamingResponse:
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    # カスタムインストラクション機能は廃止。常に固定のシステムプロンプトを使う。
    system = SYSTEM_GENERAL
    user_query = req.messages[-1].content

    # Langfuse トレース開始
    trace_ctx = trace(
        "chat",
        input={"query": user_query, "collection_id": req.collection_id},
        metadata={"model": MODEL, "conversation_id": req.conversation_id},
    )
    trace_obj = trace_ctx.__enter__()

    # RAG: inject relevant chunks when a collection is selected
    sources: list[dict] = []
    top_chunks: list[dict] = []
    if req.collection_id is not None:
        query = user_query
        loop = asyncio.get_event_loop()

        retrieval_span = trace_obj.span(name="retrieval", input={"query": query, "collection_id": req.collection_id})
        try:
            chunks = await asyncio.wait_for(
                loop.run_in_executor(
                    ThreadPoolExecutor(max_workers=1),
                    rag.retrieve_chunks, query, req.collection_id,
                ),
                timeout=60.0,
            )
            retrieval_span.end(output={"chunk_count": len(chunks)})
        except (asyncio.TimeoutError, Exception):
            chunks = []
            retrieval_span.end(output={"chunk_count": 0, "error": "timeout"})
        if chunks:
            # リランクし、関連性の高いチャンクだけに絞る
            rerank_span = trace_obj.span(name="rerank", input={"chunk_count": len(chunks)})
            try:
                top_chunks = await asyncio.wait_for(
                    loop.run_in_executor(
                        ThreadPoolExecutor(max_workers=1),
                        rag.rerank, query, chunks,
                    ),
                    timeout=30.0,
                )
                rerank_span.end(output={"kept": len(top_chunks)})
            except (asyncio.TimeoutError, Exception):
                top_chunks = []
                rerank_span.end(output={"kept": 0, "error": "fallback"})
        if top_chunks:
            # heading と filename を context に同梱し、LLM が条文を選びやすくする
            context_parts: list[str] = []
            for ci, c in enumerate(top_chunks, start=1):
                heading = (c.get("heading") or "").lstrip("# ").strip()
                body = (c.get("child_content") or c.get("content") or "").strip()
                doc_id = c.get("document_id")
                filename = ""
                if doc_id is not None:
                    doc = db.get(models.Document, doc_id)
                    if doc:
                        filename = doc.filename
                        sources.append({
                            "id": doc.id,
                            "filename": doc.filename,
                            "heading": c.get("heading", ""),
                            "content": body,
                            "chunk_index": ci,
                        })
                header_bits = [f"資料{ci}"]
                if filename:
                    header_bits.append(filename)
                if heading:
                    header_bits.append(heading)
                context_parts.append(f"【{' / '.join(header_bits)}】\n{body}")
            context = "\n\n===\n\n".join(context_parts)
            system = SYSTEM_RAG_TEMPLATE.format(context=context)
        else:
            # コレクションは選ばれているが検索ヒットなし → 推測させない
            system = SYSTEM_RAG_NO_HIT

    messages = [{"role": "system", "content": system}]
    messages.extend({"role": m.role, "content": m.content} for m in req.messages)

    conversation_id = req.conversation_id
    if conversation_id is not None:
        conv = db.get(models.Conversation, conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="会話が見つかりません")
        last = req.messages[-1]
        if last.role == "user":
            db.add(
                models.Message(
                    conversation_id=conversation_id,
                    role=last.role,
                    content=last.content,
                )
            )
            db.commit()

    # Langfuse generation スパン
    generation = trace_obj.generation(
        name="ollama-chat",
        model=MODEL,
        input=messages,
    )

    def token_stream():
        collected: list[str] = []
        try:
            with requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": MODEL, "messages": messages, "stream": True},
                stream=True,
                timeout=None,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines(chunk_size=1, decode_unicode=True):
                    if not line:
                        continue
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content")
                    if chunk:
                        collected.append(chunk)
                        yield chunk
                    if data.get("done"):
                        break
        except requests.RequestException as exc:
            yield f"\n[エラー] {exc}"

        # Langfuse generation 終了
        generation.end(output={"content": "".join(collected)})

        if conversation_id is not None and collected:
            with SessionLocal() as db2:
                db2.add(
                    models.Message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content="".join(collected),
                        sources_json=json.dumps(sources, ensure_ascii=False) if sources else None,
                    )
                )
                db2.commit()

        if sources:
            yield f"\n\n__SOURCES__\n{json.dumps(sources, ensure_ascii=False)}"

        # トレース終了
        trace_obj.update(output={"answer_length": sum(len(c) for c in collected), "source_count": len(sources)})
        trace_ctx.__exit__(None, None, None)

    return StreamingResponse(
        token_stream(), media_type="text/plain; charset=utf-8"
    )
