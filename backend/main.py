"""FastAPI 本体。

教材向けに以下のミニマム API を提供する:
- ヘルスチェック
- 会話 (Conversation) の CRUD と詳細取得
- コレクション (Collection) の CRUD
- ドキュメント (Document) のアップロード / 取得 / 削除
- チャット (RAG 利用有無トグル付き)

router は分割しない。1ファイルでルーティングを追える方が
初学者にとっては読みやすい、という Issue の方針に従う。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated

from dotenv import load_dotenv
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import dataModels as dm
from backend import rag, schemas
from backend.config import settings
from backend.db import SessionLocal, get_db, run_migrations
from backend.llm import get_chat_model
from backend.logging_config import get_logger, setup_logging
from backend.tracing import trace

# ──────────────────────────────────────────────
# 初期化
# ──────────────────────────────────────────────

load_dotenv()
setup_logging()
logger = get_logger(__name__)

MAX_UPLOAD_BYTES = settings.max_upload_mb * 1024 * 1024
ALLOWED_UPLOAD_MIME = {"application/pdf"}


# システムプロンプト（教材として小さく保つ）
SYSTEM_GENERAL = "あなたは親切なアシスタントです。必ず日本語で回答してください。"

SYSTEM_RAG_TEMPLATE = """あなたは社内文書を参照して質問に回答するアシスタントです。

## 厳守事項
1. 必ず日本語で回答してください。
2. 以下の参照ドキュメントの内容のみを根拠としてください。
3. 該当する記述がない場合は「資料に記載がありません」と回答してください。

## 参照ドキュメント
{context}"""

SYSTEM_RAG_NO_HIT = (
    "あなたは社内文書を参照して質問に回答するアシスタントです。"
    "選択されたコレクションに参照できる文書がまだないため、"
    "推測で答えず必ず日本語で『資料に記載がありません』と回答してください。"
)


# ──────────────────────────────────────────────
# アプリケーション
# ──────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """起動時に alembic upgrade head でスキーマを作る。"""
    run_migrations()
    yield


app = FastAPI(title="RAG Chat Template", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = Annotated[Session, Depends(get_db)]


# ──────────────────────────────────────────────
# Health
# ──────────────────────────────────────────────


@app.get("/health")
def health() -> dict[str, str]:
    """ヘルスチェック。LLM/VectorDB の状態には踏み込まない最小実装。"""
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "vector_db_provider": settings.vector_db_provider,
    }


# ──────────────────────────────────────────────
# Conversations
# ──────────────────────────────────────────────


@app.post(
    "/conversations",
    response_model=schemas.ConversationOut,
    status_code=201,
)
def create_conversation(
    payload: schemas.ConversationCreate, db: DB
) -> dm.Conversation:
    conv = dm.Conversation(title=payload.title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@app.get("/conversations", response_model=list[schemas.ConversationOut])
def list_conversations(
    db: DB,
    q: str | None = Query(default=None, description="タイトル部分一致で絞り込み"),
) -> list[dm.Conversation]:
    stmt = select(dm.Conversation).order_by(dm.Conversation.updated_at.desc())
    if q:
        stmt = stmt.where(dm.Conversation.title.ilike(f"%{q}%"))
    return list(db.scalars(stmt))


@app.get(
    "/conversations/{conversation_id}",
    response_model=schemas.ConversationDetail,
)
def get_conversation(conversation_id: int, db: DB) -> dm.Conversation:
    conv = db.get(dm.Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="会話が見つかりません")
    return conv


@app.patch(
    "/conversations/{conversation_id}",
    response_model=schemas.ConversationOut,
)
def update_conversation(
    conversation_id: int, payload: schemas.ConversationUpdate, db: DB
) -> dm.Conversation:
    conv = db.get(dm.Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="会話が見つかりません")
    if payload.title is not None:
        conv.title = payload.title
    db.commit()
    db.refresh(conv)
    return conv


@app.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int, db: DB) -> None:
    conv = db.get(dm.Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="会話が見つかりません")
    db.delete(conv)
    db.commit()


# ──────────────────────────────────────────────
# Collections
# ──────────────────────────────────────────────


@app.post("/collections", response_model=schemas.CollectionOut, status_code=201)
def create_collection(
    payload: schemas.CollectionCreate, db: DB
) -> dm.Collection:
    col = dm.Collection(name=payload.name)
    db.add(col)
    db.commit()
    db.refresh(col)
    return col


@app.get("/collections", response_model=list[schemas.CollectionOut])
def list_collections(db: DB) -> list[dm.Collection]:
    return list(
        db.scalars(select(dm.Collection).order_by(dm.Collection.created_at.desc()))
    )


@app.delete("/collections/{collection_id}", status_code=204)
def delete_collection(collection_id: int, db: DB) -> None:
    col = db.get(dm.Collection, collection_id)
    if col is None:
        raise HTTPException(status_code=404, detail="コレクションが見つかりません")
    # Vector DB 側のコレクションも一緒に消す（ない場合は内部で握りつぶす）
    try:
        from backend.vector_db import get_vector_db

        get_vector_db().delete_collection(collection_id)
    except Exception:
        logger.warning(
            "VectorDB のコレクション削除に失敗（無視して RDB は削除を続行）",
            exc_info=True,
        )
    db.delete(col)
    db.commit()


# ──────────────────────────────────────────────
# Documents
# ──────────────────────────────────────────────


def _index_document(document_id: int, collection_id: int, file_data: bytes) -> None:
    """バックグラウンドで文書を取り込む。

    教材初期段階では `rag.index_document` が NotImplementedError なので、
    status を 'error' に倒して詳細をログに残すだけにしている。
    Phase 2-1 以降で `rag.index_document` を埋めれば、ここで取り込みが
    完走するようになる。
    """
    with SessionLocal() as db:
        doc = db.get(dm.Document, document_id)
        if doc is None:
            return
        doc.status = "indexing"
        db.commit()

        try:
            with trace(
                "index-document",
                input={"document_id": document_id, "collection_id": collection_id},
            ):
                # Phase 2-1 以降ではここで extract_text → split → upsert される。
                rag.index_document(collection_id, document_id, file_data)
                # 教材初期段階では reach できないが、本実装後に到達する想定。
                _, page_count = rag.extract_text(file_data)

                doc = db.get(dm.Document, document_id)
                if doc:
                    doc.status = "ready"
                    doc.page_count = page_count
                    doc.indexed_at = datetime.now(timezone.utc)
                    db.commit()
        except NotImplementedError:
            # 教材初期段階の想定パス: rag.index_document が未実装
            logger.info(
                "rag.index_document が未実装のため status=error にします "
                "（Phase 2-1 で実装すれば取り込みが完走します）"
            )
            doc = db.get(dm.Document, document_id)
            if doc:
                doc.status = "error"
                db.commit()
        except Exception:
            logger.exception("ドキュメント取り込みに失敗: document_id=%s", document_id)
            doc = db.get(dm.Document, document_id)
            if doc:
                doc.status = "error"
                db.commit()


@app.post(
    "/collections/{collection_id}/documents",
    response_model=list[schemas.DocumentOut],
    status_code=201,
)
async def upload_documents(
    collection_id: int,
    background_tasks: BackgroundTasks,
    db: DB,
    files: list[UploadFile] = File(...),
) -> list[dm.Document]:
    col = db.get(dm.Collection, collection_id)
    if col is None:
        raise HTTPException(status_code=404, detail="コレクションが見つかりません")

    created: list[dm.Document] = []
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
                detail=(
                    f"ファイルサイズが上限 {settings.max_upload_mb}MB を"
                    f"超えています: {upload.filename}"
                ),
            )

        doc = dm.Document(
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


@app.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int, db: DB) -> None:
    doc = db.get(dm.Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="ドキュメントが見つかりません")
    try:
        from backend.vector_db import get_vector_db

        get_vector_db().delete_document(doc.collection_id, document_id)
    except Exception:
        logger.warning(
            "VectorDB からの削除に失敗（無視して RDB の削除を続行）", exc_info=True
        )
    db.delete(doc)
    db.commit()


@app.get("/documents/{document_id}/file")
def get_document_file(document_id: int, db: DB) -> Response:
    doc = db.get(dm.Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="ドキュメントが見つかりません")
    return Response(
        content=doc.file_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{doc.filename}"'},
    )


# ──────────────────────────────────────────────
# Chat
# ──────────────────────────────────────────────


def _build_messages(
    req: schemas.ChatRequest,
    db: Session,
) -> list[dict[str, str]]:
    """LLM に渡すメッセージ列を組み立てる。

    use_rag=True かつ collection_id 指定時のみ RAG コンテキストを差し込む。
    教材初期段階では検索は未実装なので、NO_DOCUMENTS_MESSAGE が入る。
    """
    system_content = SYSTEM_GENERAL

    if req.use_rag and req.collection_id is not None:
        # 直近の user 発話をクエリとして RAG にかける
        last_user = next(
            (m.content for m in reversed(req.messages) if m.role == "user"),
            "",
        )
        ctx = rag.build_context(last_user, req.collection_id)
        if ctx.has_hits:
            system_content = SYSTEM_RAG_TEMPLATE.format(context=ctx.context_text)
        else:
            system_content = SYSTEM_RAG_NO_HIT

    messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]
    messages.extend({"role": m.role, "content": m.content} for m in req.messages)
    return messages


@app.post("/chat")
async def chat(req: schemas.ChatRequest, db: DB) -> StreamingResponse:
    """チャットエンドポイント。

    フローは
      1. system プロンプトを組み立て (RAG 有無で分岐)
      2. user メッセージを DB に保存
      3. LLM ストリームを yield しつつ、終わったら assistant メッセージを保存
    """
    messages = _build_messages(req, db)

    # user メッセージを履歴に追加
    if req.conversation_id is not None:
        conv = db.get(dm.Conversation, req.conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="会話が見つかりません")
        last = req.messages[-1]
        if last.role == "user":
            db.add(
                dm.Message(
                    conversation_id=req.conversation_id,
                    role=last.role,
                    content=last.content,
                )
            )
            db.commit()

    chat_model = get_chat_model()

    async def token_stream():
        collected: list[str] = []
        with trace(
            "chat",
            input={
                "use_rag": req.use_rag,
                "collection_id": req.collection_id,
                "conversation_id": req.conversation_id,
            },
        ):
            async for chunk in chat_model.stream(messages):
                collected.append(chunk)
                yield chunk

        # assistant メッセージを履歴に保存
        if req.conversation_id is not None and collected:
            with SessionLocal() as db2:
                db2.add(
                    dm.Message(
                        conversation_id=req.conversation_id,
                        role="assistant",
                        content="".join(collected),
                    )
                )
                db2.commit()

    return StreamingResponse(
        token_stream(), media_type="text/plain; charset=utf-8"
    )
