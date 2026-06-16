# RAG Chat Template

RAG (Retrieval Augmented Generation) の構築を社内で学ぶための、
最小実装のチャットアプリ + 文書取り込みテンプレートです。

> 最初は **動くチャット + 空の RAG ラッパ + 文書アップロード API** だけが
> 揃っています。検索ロジックやベクトル化は、学習者が `ROAD_MAP.md` の
> Phase に沿って段階的に実装していきます。

---

## 1. このリポジトリの目的

- 初めて RAG に触れる社員が、**ローカル環境ですぐに開発学習を始められる**
- 学習が進むほど、`backend/rag.py` と `backend/vector_db/chroma.py` を
  読み・書きしていくことになる
- 将来 **AWS** に持って行く動線（Bedrock / OpenSearch / PrivateLink / OIDC）も
  ディレクトリ・コメントとして用意してある

教材としての方針:

- 抽象化は最小限。1 ファイルで処理が追える方を優先
- 「初期状態では何ができないか」をコード中の `NotImplementedError` で明示
- AWS 構成は Terraform にコメントとして残し、実装は Phase 7 で

---

## 2. 使用技術スタック

| 区分 | 技術 |
| --- | --- |
| Backend | Python 3.11+ / FastAPI / SQLAlchemy / alembic |
| Frontend | Next.js (App Router) / React 19 |
| DB | PostgreSQL (ローカルも AWS もコンテナ前提) |
| Vector DB | ChromaDB (ローカル) / OpenSearch (AWS, 雛形のみ) |
| LLM | Ollama (ローカル) / AWS Bedrock (AWS, 雛形のみ) |
| トレース | Langfuse (任意, 初期は no-op) |
| IaC | Terraform |
| CI | GitHub Actions (将来は OIDC で apply/deploy 想定) |

---

## 3. ディレクトリ構成

```
backend/
  main.py              FastAPI 本体 (router も兼ねる)
  db.py                DB 接続・Base・alembic 起動
  dataModels.py        SQLAlchemy モデル (Conversation/Message/Collection/Document)
  schemas.py           Pydantic スキーマ
  rag.py               RAG メイン開発部分 (今は薄ラッパ)
  tracing.py           Langfuse 連携 (今は no-op)
  logging_config.py
  config/
    settings.py        .env を一手に読む
  llm/
    chatModel.py       共通インターフェース
    embedModel.py      共通インターフェース
    ollama.py          ローカル前提の Ollama 実装
    bedrock.py         AWS Bedrock 実装の雛形
  vector_db/
    vectorDB.py        共通インターフェース
    chroma.py          ChromaDB 実装 (検索本体は学習者が実装)
    opensearch.py      AWS OpenSearch 実装の雛形

frontend/
  src/
    app/
      page.tsx         チャット画面
      ingest/page.tsx  ファイル取り込み画面
      layout.tsx
      globals.css      デザイントークン + スタイル
    components/
      ConversationSidebar.tsx
      MessageList.tsx
      ChatComposer.tsx
    lib/
      api.ts           API クライアント
      types.ts

alembic/                DB マイグレーション (0001_initial.py)

terraform/
  main.tf               最小構成: VPC + 文書用 S3
                        他の AWS 構成はコメントで補足

.claude/skills/
  frontend-design/      公式 frontend-design skill

docs/                   学習ログや補足資料を置く場所

ROAD_MAP.md             Phase 0-1 〜 Phase 8 の学習ロードマップ
ISSUES.md               Phase ごとの Issue 原稿
CLAUDE.md               (空) プロジェクト固有の Claude 用メモを書く場所
README.md
```

---

## 4. ローカル起動方法

### 4.1 前提

- Docker / Docker Compose
- Ollama 用にローカル GPU を使う場合のみ NVIDIA Container Toolkit
- （GPU が無くてもモデルを軽くすれば動きます）

### 4.2 セットアップ

```bash
# 1. .env を作成
cp .env.example .env

# 2. コンテナを起動
make up-d

# 3. Ollama にチャット用と埋め込み用のモデルを取り込む
make pull               # 既定: llama3.2
make pull-embed         # 既定: nomic-embed-text
```

これで以下が立ち上がります。

| URL | 用途 |
| --- | --- |
| http://localhost:3000 | フロントエンド (Next.js) |
| http://localhost:8000 | バックエンド (FastAPI) |
| http://localhost:8000/docs | OpenAPI Swagger UI |
| http://localhost:8001 | ChromaDB |
| http://localhost:11434 | Ollama |
| postgres://localhost:5432 | PostgreSQL (chat/chat) |

### 4.3 .env の主な変数

| 変数 | 既定値 | 説明 |
| --- | --- | --- |
| `LLM_PROVIDER` | `ollama` | `ollama` か `bedrock` |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama エンドポイント |
| `OLLAMA_MODEL` | `llama3.2` | チャット用モデル |
| `EMBEDDING_MODEL` | `nomic-embed-text` | 埋め込み用モデル |
| `VECTOR_DB_PROVIDER` | `chroma` | `chroma` か `opensearch` |
| `CHROMA_HOST` / `CHROMA_PORT` | `localhost` / `8001` | ChromaDB 接続先 |
| `DATABASE_URL` | `postgresql+psycopg://chat:chat@localhost:5432/chat` | PostgreSQL 接続先 |
| `MAX_UPLOAD_MB` | `50` | PDF アップロード上限 |
| `LOG_LEVEL` | `INFO` | ログレベル |
| `LANGFUSE_*` | (空) | Langfuse 用 (Phase 4 で設定) |

---

## 5. 現在の接続経路 (ローカル)

```
+---------------+     /api/*     +--------------+    HTTP    +-----------+
| Next.js (3000)|--------------> | FastAPI (8000)|--------->| Ollama    |
|  page.tsx     |  rewrite proxy |   main.py     |          | (11434)   |
|  ingest/page  |                |   rag.py      |          +-----------+
+---------------+                |   vector_db/  |          +-----------+
                                 |               |---HTTP-->| ChromaDB  |
                                 |               |          | (8001)    |
                                 |               |          +-----------+
                                 |   db.py       |---SQL--->| Postgres  |
                                 +---------------+          | (5432)    |
                                                            +-----------+
```

教材初期段階では、`use_rag=true` + コレクション選択時でも `vector_db/chroma.py`
の `search` が `NotImplementedError` を投げるので、**「資料に記載がありません」**
と返ります。Phase 2 から学習者がここを埋めていきます。

---

## 6. 通常チャットの流れ

1. フロントの `ChatComposer` で **RAG トグルを OFF** にする
2. メッセージを送ると `/chat` → `LLM_PROVIDER` の実装 (ollama) →
   ストリーミングでトークンが流れてくる
3. 会話履歴は `conversations` / `messages` テーブルに保存される

## 7. RAG モードの将来想定の流れ

1. `/ingest` ページからコレクションを作り、PDF をアップロード
2. backend が `rag.index_document` で **チャンク分割 + embedding + Vector DB upsert** を行う
   - 教材初期段階ではここが `NotImplementedError`。Phase 2-1 で実装する
3. フロントで RAG トグルを ON にして、対象コレクションを選んで質問
4. backend が `rag.build_context` で **検索 (BM25 / ベクトル / ハイブリッド)** をかけ、
   ヒットしたチャンクを system プロンプトに同梱
5. LLM がコンテキストに基づいて回答

---

## 8. AWS 移行時の想定

詳しくは `terraform/main.tf` 内のコメントを参照。

- backend を **ECS Fargate / EKS** で動かす
- LLM は **Bedrock** に切り替え (PrivateLink VPC Endpoint 経由)
- Vector DB は **OpenSearch Serverless (VECTORSEARCH)** に切り替え
- DB は **RDS for PostgreSQL** に切り替え (当面は backend 同居でも可)
- 文書原本は **S3** に退避し、`documents.file_data` は S3 キーに置換
- `apply` / `deploy` は **GitHub Actions + OIDC** で実施

---

## 9. 初めて触る人がまずやること

1. `make up-d && make pull && make pull-embed`
2. http://localhost:3000 を開いて **RAG トグル OFF** でチャットを動かす
3. `/ingest` でコレクションを作って PDF をアップロード
   （ステータスは `error` になる。それで OK ）
4. `ROAD_MAP.md` を読み、Phase 2-1 から実装に取りかかる
5. 詰まったら `ISSUES.md` の各 Issue 原稿を参照する

---

## 10. 関連ドキュメント

- [ROAD_MAP.md](ROAD_MAP.md) — Phase 0-1 〜 Phase 8 の学習ロードマップ
- [ISSUES.md](ISSUES.md) — 各 Phase の Issue 原稿
- [terraform/main.tf](terraform/main.tf) — AWS 想定構成（コメント中心）
- [.claude/skills/frontend-design/SKILL.md](.claude/skills/frontend-design/SKILL.md) — frontend design skill
