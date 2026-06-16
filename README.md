# RAG Chat Template

RAG (Retrieval Augmented Generation) の構築を社内で学ぶための、
最小実装のチャットアプリ + 文書取り込みテンプレートです。

> 最初は **動くチャット + 空の RAG ラッパ + 文書アップロード API** だけが
> 揃っています。検索ロジックやベクトル化は、学習者が `reference/ROAD_MAP.md` の
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
- **セットアップも `make` で隠さず、手打ちコマンドで何が起きているかを理解しながら進める**

---

## 2. はじめて触る人がまずやること

教材としては「中身を理解しながら動かす」ことを優先するため、
**Makefile に頼らず Docker コマンドを手打ち** で進める導線を採っています。
細かな手順は [`reference/SETUP_GUIDE.md`](reference/SETUP_GUIDE.md) にまとめてあるので、初回はそちらを開きながら作業してください。

> Ollama 利用方針: このテンプレでは **Ollama はホスト OS で起動する** のが標準です。
> Docker Compose 内で一括起動したい場合は `make up-d` を使います（詳細: `reference/SETUP_GUIDE.md` §6）。

ざっくりの流れは次のとおりです。

1. **前提ソフトのインストール**
   - Docker Desktop と Ollama（ホスト OS 用）をインストールし、両方を起動状態にしておく
   - 詳細: `reference/SETUP_GUIDE.md` §1
2. **`.env` の作成**
   ```bash
   cp .env.example .env
   ```
   `OLLAMA_URL` はデフォルトで `http://host.docker.internal:11434` に設定済み。
3. **ホスト OS で Ollama を起動 + モデル取得**
   ```bash
   ollama serve                          # 別ターミナルで常時起動
   ollama pull llama3.2                  # チャット用
   ollama pull nomic-embed-text          # Phase 3 用
   ```
4. **Docker Compose で残りのサービスを起動**
   ```bash
   docker compose up -d                  # backend / frontend / db / chromadb
   docker compose ps
   ```
5. **ブラウザで動作確認**
   - [http://localhost:3000](http://localhost:3000) を開き、**RAG トグル OFF** でチャットを送信
   - `/ingest` で PDF アップロード → ステータスは `error` で停止する（仕様。Phase 2-1 で実装するパス）
6. **ログを眺める癖をつける**
   ```bash
   docker compose logs -f             # 全サービス
   docker compose logs -f backend     # backend だけ
   ```
7. **次の学習に進む**
   - `reference/ROAD_MAP.md` の Phase 2-1 から実装に取り掛かる
   - 詰まったら `reference/ISSUES.md` の Phase 別 Issue 原稿を参照

### 知っておきたい補足

- **初回の応答は遅くなることがあります。** ローカル LLM はモデルをメモリにロードしてから推論するため、最初の 1 回だけ数十秒〜数分かかることがあります。`docker compose logs -f backend` を眺めながら待ってください（詳細: `reference/SETUP_GUIDE.md` §5）。
- **Ollama を Docker Compose 内で動かす運用も可能です。** その場合は `make up-d` で `--profile bundled-ollama` を付けた compose を起動し、`.env` の `OLLAMA_URL` を `http://ollama:11434` に切り替えます（詳細: `reference/SETUP_GUIDE.md` §6）。
- **Makefile は Compose 内 Ollama 一括起動用の補助** です。ホスト Ollama を使う標準フローでは必須ではありません（詳細: `reference/SETUP_GUIDE.md` §9）。

---

## 3. 学習の進め方

セットアップが完了したら、次は **RAG 学習企画の進め方** を確認してください。
Phase ごとの Issue の進め方、bolt の切り方、taskLog、PR 作成・週次レビュー、
進捗管理の流れは以下にまとめています。

- [reference/LEARN_FLOW.md](reference/LEARN_FLOW.md)

`reference/ROAD_MAP.md` が「何を作っていくか（Phase の地図）」だとすれば、
`LEARN_FLOW.md` は「どう進めていくか（運用ルール）」を扱うドキュメントです。

---

## 4. 関連ドキュメント

- [reference/SETUP_GUIDE.md](reference/SETUP_GUIDE.md) — Docker 手打ちコマンドでのセットアップ手順 / トラブルシュート
- [reference/LEARN_FLOW.md](reference/LEARN_FLOW.md) — RAG 学習企画の進め方（Issue / bolt / taskLog / PR レビュー / 進捗管理）
- [reference/ROAD_MAP.md](reference/ROAD_MAP.md) — Phase 0-1 〜 Phase 8 の学習ロードマップ
- [reference/ISSUES.md](reference/ISSUES.md) — 各 Phase の Issue 原稿
- [terraform/main.tf](terraform/main.tf) — AWS 想定構成（コメント中心）
- [.claude/skills/frontend-design/SKILL.md](.claude/skills/frontend-design/SKILL.md) — frontend design skill
- [.claude/skills/bolt-planning/SKILL.md](.claude/skills/bolt-planning/SKILL.md) — bolt 単位で「何を作るか」を整理する skill

---

## 5. 使用技術スタック


| 区分        | 技術                                            |
| --------- | --------------------------------------------- |
| Backend   | Python 3.11+ / FastAPI / SQLAlchemy / alembic |
| Frontend  | Next.js (App Router) / React 19               |
| DB        | PostgreSQL (ローカルも AWS もコンテナ前提)                |
| Vector DB | ChromaDB (ローカル) / OpenSearch (AWS, 雛形のみ)      |
| LLM       | Ollama (ローカル) / AWS Bedrock (AWS, 雛形のみ)       |
| トレース      | Langfuse (任意, 初期は no-op)                      |
| IaC       | Terraform                                     |
| CI        | GitHub Actions (将来は OIDC で apply/deploy 想定)   |


---

## 6. ディレクトリ構成

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
  bolt-planning/        bolt 単位で作業を整理する skill

docs/                   学習ログや補足資料を置く場所

reference/
  SETUP_GUIDE.md        Docker 手打ちのセットアップ手順
  ROAD_MAP.md           Phase 0-1 〜 Phase 8 の学習ロードマップ
  ISSUES.md             Phase ごとの Issue 原稿
CLAUDE.md               (空) プロジェクト固有の Claude 用メモを書く場所
README.md
```

---

## 7. ローカル起動方法 (リファレンス)

> 手順は §2 のとおり `reference/SETUP_GUIDE.md` を参照してください。
> ここではポート一覧と `.env` の主な変数だけまとめます。

### 7.1 立ち上がるサービス


| URL                                                      | 用途                     |
| -------------------------------------------------------- | ---------------------- |
| [http://localhost:3000](http://localhost:3000)           | フロントエンド (Next.js)      |
| [http://localhost:8000](http://localhost:8000)           | バックエンド (FastAPI)       |
| [http://localhost:8000/docs](http://localhost:8000/docs) | OpenAPI Swagger UI     |
| [http://localhost:8001](http://localhost:8001)           | ChromaDB               |
| [http://localhost:11434](http://localhost:11434)         | Ollama                 |
| postgres://localhost:5432                                | PostgreSQL (chat/chat) |


### 7.2 .env の主な変数


| 変数                            | 既定値                                                  | 説明                                                                                                         |
| ----------------------------- | ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `LLM_PROVIDER`                | `ollama`                                             | `ollama` か `bedrock`                                                                                       |
| `OLLAMA_URL`                  | `http://host.docker.internal:11434` (ホスト Ollama) | Ollama エンドポイント。Compose 内 Ollama (`make up-d`) を使う場合は `http://ollama:11434` |
| `OLLAMA_MODEL`                | `llama3.2`                                           | チャット用モデル                                                                                                   |
| `EMBEDDING_MODEL`             | `nomic-embed-text`                                   | 埋め込み用モデル                                                                                                   |
| `VECTOR_DB_PROVIDER`          | `chroma`                                             | `chroma` か `opensearch`                                                                                    |
| `CHROMA_HOST` / `CHROMA_PORT` | `localhost` / `8001`                                 | ChromaDB 接続先                                                                                               |
| `DATABASE_URL`                | `postgresql+psycopg://chat:chat@localhost:5432/chat` | PostgreSQL 接続先                                                                                             |
| `MAX_UPLOAD_MB`               | `50`                                                 | PDF アップロード上限                                                                                               |
| `LOG_LEVEL`                   | `INFO`                                               | ログレベル                                                                                                      |
| `LANGFUSE_*`                  | (空)                                                  | Langfuse 用 (Phase 4 で設定)                                                                                   |


---

## 8. 現在の接続経路 (ローカル)

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

## 9. 通常チャットの流れ

1. フロントの `ChatComposer` で **RAG トグルを OFF** にする
2. メッセージを送ると `/chat` → `LLM_PROVIDER` の実装 (ollama) →
  ストリーミングでトークンが流れてくる
3. 会話履歴は `conversations` / `messages` テーブルに保存される

## 10. RAG モードの将来想定の流れ

1. `/ingest` ページからコレクションを作り、PDF をアップロード
2. backend が `rag.index_document` で **チャンク分割 + embedding + Vector DB upsert** を行う
  - 教材初期段階ではここが `NotImplementedError`。Phase 2-1 で実装する
3. フロントで RAG トグルを ON にして、対象コレクションを選んで質問
4. backend が `rag.build_context` で **検索 (BM25 / ベクトル / ハイブリッド)** をかけ、
  ヒットしたチャンクを system プロンプトに同梱
5. LLM がコンテキストに基づいて回答

---

## 11. AWS 移行時の想定

詳しくは `terraform/main.tf` 内のコメントを参照。

- backend を **ECS Fargate / EKS** で動かす
- LLM は **Bedrock** に切り替え (PrivateLink VPC Endpoint 経由)
- Vector DB は **OpenSearch Serverless (VECTORSEARCH)** に切り替え
- DB は **RDS for PostgreSQL** に切り替え (当面は backend 同居でも可)
- 文書原本は **S3** に退避し、`documents.file_data` は S3 キーに置換
- `apply` / `deploy` は **GitHub Actions + OIDC** で実施

