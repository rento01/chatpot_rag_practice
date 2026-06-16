# RAG 学習ロードマップ

このリポジトリは、初期状態では「チャットは動くが、RAG 検索は中身が空」の
状態になっています。各 Phase で 1〜2 ファイルずつ書き足していくことで、
最終的に AWS 上のフル RAG にたどり着く想定です。

各 Phase は `ISSUES.md` に対応する Issue 原稿があります。
進めるときはまず Issue 原稿を読んでください。

---

## 作業の進め方 (bolt 単位)

このプロジェクトでは、各 Phase / Issue を **bolt** と呼ぶ小さな実装単位に
分けてから着手します。

- bolt 名は必ず **`bolt-0`, `bolt-1`, `bolt-2` …** の形式で表記する
  （別表記 `bolt-zero` / `bolt_0` などは使わない）
- 各 bolt で「何を作るか」「何を作らないか」「完了条件」「次の bolt への引き継ぎ」を
  **実装前に整理** してから着手する
- bolt 設計の手順・出力フォーマット・判断基準は
  [`.claude/skills/bolt-planning/SKILL.md`](.claude/skills/bolt-planning/SKILL.md)
  を参照すること
- 1 bolt = 1 PR を原則とし、PR 本文の冒頭に bolt 設計（目的 / 作るもの /
  作らないもの / 完了条件 / 引き継ぎ）を貼る
- Phase の中で複数 bolt に分割される場合は、`bolt-0`, `bolt-1`, … と通し番号で扱う

> ROAD_MAP.md には「Phase の地図」だけを書きます。bolt の詳細は PR 本文
> （必要に応じて `docs/taskLog/`）に残し、ROAD_MAP は薄く保ちます。

---

## Phase 0-1: 環境構築

- Docker / Docker Compose のインストール
- Ollama のセットアップ（モデル: `llama3.2`, `nomic-embed-text`）
- `make up-d && make pull && make pull-embed` でローカル一式が起動することを確認

**ゴール**: `http://localhost:3000` でチャットが返ってくる。

## Phase 0-2: 構成理解（rag-with-claude repo も併読）

- 既存実装を読む順番（おすすめ）:
  1. `backend/main.py`（ルーティング全体）
  2. `backend/dataModels.py` / `backend/schemas.py`（データ）
  3. `backend/rag.py`（薄ラッパ — まだ何もしていない）
  4. `backend/llm/` / `backend/vector_db/`（プロバイダ切り替え）
  5. `frontend/src/app/page.tsx`（チャットの UI と API 呼び出し）
- 並行して **rag-with-claude** リポジトリの実装も読む
  - 本テンプレでは省いた parent-child chunk / BM25+RRF / リランクの実装が
    参考になる

**ゴール**: 「ここの `NotImplementedError` を埋めればこう動く」が頭に入る。

---

## Phase 1: ローカル起動

- `.env` を編集して別モデル (`gemma3`, `qwen2.5` 等) で動かしてみる
- `/ingest` ページから PDF をアップロードし、status が `error` になることを確認
  （初期状態では `rag.index_document` が `NotImplementedError` のため）

**ゴール**: 自分の環境で確実に動く前提が整う。

---

## Phase 2-1: ファイル取り込み（Chroma に投入）

- `backend/rag.py` の `split_into_chunks` を実装
- `backend/vector_db/chroma.py` の `ChromaVectorDB.upsert` を実装
- `backend/rag.py` の `index_document` を完成させる
  - `extract_text` → `split_into_chunks` → `Chunk` 化 → `vdb.upsert`
- アップロードしてステータスが `ready` になることを確認

**学習ポイント**:
- ChromaDB の collection 作成 / metadata 設計
- 大きな PDF を 1 リクエストで処理するときの注意点（BackgroundTasks）

## Phase 2-2: キーワード検索実装

- `backend/vector_db/chroma.py` の `ChromaVectorDB.search` を
  **キーワード一致 (BM25 など)** で実装
- フロントの **RAG トグル ON** + コレクション選択でヒットすることを確認

**学習ポイント**:
- BM25 のトークナイザ（日本語は素朴な split では不十分）
- ヒットなし時の「資料に記載がありません」分岐

---

## Phase 3-1: embedding 生成

- `backend/llm/ollama.py` の `OllamaEmbedModel.embed` を活用
- Phase 2-1 の `upsert` で、各チャンクに `embedding` を付与

**学習ポイント**:
- 埋め込みモデルのバッチサイズ / トークン上限
- DB / Chroma に保存するときの正規化

## Phase 3-2: ベクトル検索実装

- `ChromaVectorDB.search` を **コサイン類似 / k-NN** に拡張
- BM25 と ベクトル検索の **ハイブリッド (RRF)** を実装する

**学習ポイント**:
- BM25 と ベクトルの弱点の補完
- RRF (Reciprocal Rank Fusion) の効きどころ

---

## Phase 4: Langfuse 導入

- Langfuse Cloud（または self-host）にプロジェクトを作り、
  `.env` に `LANGFUSE_SECRET_KEY` / `LANGFUSE_PUBLIC_KEY` を設定
- `backend/tracing.py` を有効化（既に環境変数が揃えば動く）
- `backend/main.py` / `rag.py` に span / generation を追加

**学習ポイント**:
- トレースの粒度（リクエスト/検索/生成/保存）
- どこを観測すれば RAG の品質が見えるか

---

## Phase 5: チャンク分割改善（階層化）

- Markdown 見出しベースで **親チャンク → 子チャンク** に分割
- Chroma の metadata に `parent_id` / `parent_content` を保持
- `search` 時は子チャンクで検索 → 親チャンクをコンテキストにする

**学習ポイント**:
- 「検索粒度」と「LLM に渡す粒度」のずれ
- metadata 設計が後段の rerank に効く理由

---

## Phase 6: rerank 実装

- ハイブリッド検索後にトップ K を rerank
- 教材としては「軽量な heuristic (BM25 二段目 / クエリ語の一致数)」から始め、
  必要なら cross-encoder を導入

**学習ポイント**:
- top_n を絞る効果（プロンプト長 / コスト）
- rerank の評価方法

---

## Phase 7: AWS 移行 (Terraform + GitHub OIDC)

- `terraform/main.tf` の VPC を実 apply
- `aws_s3_bucket.documents` を有効化し、PDF の保存先を S3 に切り替え
- `backend/llm/bedrock.py` を実装し `LLM_PROVIDER=bedrock` で動くようにする
- `backend/vector_db/opensearch.py` を実装し
  `VECTOR_DB_PROVIDER=opensearch` で動くようにする
- GitHub Actions OIDC を組み、`apply` / `deploy` を CI から実行できるようにする

**学習ポイント**:
- PrivateLink で Bedrock を呼ぶ構成
- OpenSearch Serverless (VECTORSEARCH) の特性

---

## Phase 8: RAGAS 導入

- 検索/生成のオフライン評価ハーネスを `eval/` に追加
- RAGAS の主要メトリクス (faithfulness / answer_relevancy / context_precision) を取得
- Langfuse のトレースと突き合わせて品質指標を可視化

**学習ポイント**:
- 評価データセットの作り方
- 「再現可能な改善」をどう定量化するか

---

## おまけ: 学習中のメモ

- 試行錯誤や気づきは `docs/` 下に Markdown でログとして残す
- 大きな設計変更は PR タイトルに Phase 番号を入れる
  例: `feat(phase-2-1): implement chroma upsert`
