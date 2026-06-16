# ISSUES

このリポジトリの **学習 Phase ごとの Issue 原稿** をここに集約します。
GitHub Issue を新規に切るときは、対応する見出しの本文をそのままコピペして
使ってください。

目次:

- [Issue: Phase 2-1 — ファイル取り込みを動かす](#issue-phase-2-1--ファイル取り込みを動かす)
- [Issue: Phase 2-2 — キーワード検索を実装する](#issue-phase-2-2--キーワード検索を実装する)
- [Issue: Phase 3-1 — embedding を生成する](#issue-phase-3-1--embedding-を生成する)
- [Issue: Phase 3-2 — ベクトル検索とハイブリッド検索を実装する](#issue-phase-3-2--ベクトル検索とハイブリッド検索を実装する)
- [Issue: Phase 4 — Langfuse でトレースを取る](#issue-phase-4--langfuse-でトレースを取る)
- [Issue: Phase 5 — 親子チャンクで分割を改善する](#issue-phase-5--親子チャンクで分割を改善する)
- [Issue: Phase 6 — rerank を実装する](#issue-phase-6--rerank-を実装する)
- [Issue: Phase 7 — AWS 移行 (Terraform + GitHub OIDC)](#issue-phase-7--aws-移行-terraform--github-oidc)
- [Issue: Phase 8 — RAGAS で品質評価を回す](#issue-phase-8--ragas-で品質評価を回す)

---

## Issue: Phase 2-1 — ファイル取り込みを動かす

### 目的
PDF をアップロードしたら、テキスト抽出 → チャンク分割 → ChromaDB 保存まで
通る状態にする。

### 背景
教材初期段階では `backend/rag.py` の `index_document` と
`backend/vector_db/chroma.py` の `upsert` が `NotImplementedError` を投げる。
そのため `/ingest` ページからアップロードしても、status が `error` で止まる。
これを `ready` まで通すのが本 Issue。

### 作業内容
- `backend/rag.py`
  - `split_into_chunks(text)` を実装
    - `langchain_text_splitters.RecursiveCharacterTextSplitter` を使うのが手軽
    - 区切り文字に日本語句読点を入れる
  - `index_document(collection_id, document_id, file_data)` を実装
    - `extract_text` でテキストとページ数を取得
    - `split_into_chunks` で `list[str]` に分割
    - 各チャンクを `vector_db.Chunk` に変換して `get_vector_db().upsert(...)` に渡す
- `backend/vector_db/chroma.py`
  - `ChromaVectorDB.upsert` を実装
    - `_client().get_or_create_collection(_collection_name(collection_id))` でコレクション取得
    - `collection.add(ids=..., documents=..., metadatas=...)` で投入
    - `embedding` は Phase 3-1 まで未使用でも OK

### 完了条件
- `/ingest` ページから PDF をアップロードして status が `ready` になる
- ChromaDB の `col_<id>` コレクションにチャンクが入っている
- 数十ページ規模の PDF でも `BackgroundTasks` で詰まらず非同期に処理できる

### 学習ポイント
- `BackgroundTasks` は同一プロセス内で動くため、長時間処理時の注意点
- ChromaDB の metadata 設計（後段で document_id でフィルタするため）

### 関連ファイル
- `backend/rag.py`
- `backend/vector_db/chroma.py`
- `backend/main.py` の `_index_document`

---

## Issue: Phase 2-2 — キーワード検索を実装する

### 目的
RAG モード ON でチャットすると、ChromaDB から **キーワード一致** で
ヒットしたチャンクが LLM に渡るようにする。

### 作業内容
- `backend/vector_db/chroma.py` の `ChromaVectorDB.search` を実装
  - 全チャンクを `collection.get()` で取り出して BM25 で検索
  - `langchain_community.retrievers.BM25Retriever` を使うのが手軽
  - 日本語向けに preprocess_func を渡す（空白 split だと文単位になってしまう）

### 完了条件
- 取り込み済みコレクションを選んで RAG モードで質問すると、
  ヒットしたチャンクが回答の根拠として返ってくる
- ヒット無し時は「資料に記載がありません」と返る

### 学習ポイント
- BM25 の挙動と、日本語 bi-gram トークナイザの必要性
- 「全部メモリに乗せる」前提の限界

### 関連ファイル
- `backend/vector_db/chroma.py`
- `backend/rag.py` (`build_context`)

---

## Issue: Phase 3-1 — embedding を生成する

### 目的
Phase 2-1 の `upsert` で **チャンクに embedding ベクトルを付与** する。

### 作業内容
- `backend/llm/embedModel.py` の `get_embed_model()` から `OllamaEmbedModel` を取り、
  `embed(texts)` で埋め込みを生成
- `backend/vector_db/chroma.py` の `upsert` で `embedding=...` を渡す
- バッチサイズと進捗ログを工夫

### 完了条件
- 取り込み完了後、`vs._collection.get(include=["embeddings"])` で
  各チャンクに embedding が入っている

### 学習ポイント
- 埋め込みモデルのトークン上限と、過剰に長いチャンクの扱い
- chunk のテキスト長と embedding 品質のトレードオフ

### 関連ファイル
- `backend/llm/ollama.py`
- `backend/vector_db/chroma.py`

---

## Issue: Phase 3-2 — ベクトル検索とハイブリッド検索を実装する

### 目的
キーワード検索 (BM25) と ベクトル検索 (k-NN) を組み合わせた
ハイブリッド検索を `ChromaVectorDB.search` に実装する。

### 作業内容
- ベクトル検索: `collection.query(query_texts=..., n_results=...)`
- BM25 と vector の結果を RRF (Reciprocal Rank Fusion) でマージ
- top_k を `.env` で調整できるようにする

### 完了条件
- キーワードだけでは拾えなかったセマンティックなクエリにも答えられる
- BM25 のみと比べて回答品質が改善している（主観で OK、Phase 8 で定量化）

### 学習ポイント
- RRF の k パラメータの効きどころ
- BM25 / ベクトルそれぞれの強み・弱み

### 関連ファイル
- `backend/vector_db/chroma.py`

---

## Issue: Phase 4 — Langfuse でトレースを取る

### 目的
チャットリクエストごとに **検索 / 生成 / 保存** の各 span を Langfuse に
記録し、品質改善のサイクルを回せるようにする。

### 作業内容
- Langfuse プロジェクトを作り `.env` に key を設定
- `backend/tracing.py` は既に no-op 切替の雛形が入っているので、
  そのまま有効化
- `backend/main.py` の `chat` 関数で `trace(...)` の `span` / `generation` を活用
- 取り込み (`_index_document`) にも span を追加

### 完了条件
- Langfuse のダッシュボードで 1 件のチャットが span ツリーとして見える
- `LANGFUSE_*` を空にした状態でも従来通りローカル動作する（no-op）

### 学習ポイント
- 観測ポイント（retrieval, rerank, generation, save）の粒度設計

### 関連ファイル
- `backend/tracing.py`
- `backend/main.py`
- `backend/rag.py`

---

## Issue: Phase 5 — 親子チャンクで分割を改善する

### 目的
Markdown 見出し基準で **親チャンク → 子チャンク** の階層分割を実装し、
検索粒度（子）と LLM コンテキスト粒度（親）を分離する。

### 作業内容
- `backend/rag.py` に `split_into_parent_chunks` / `split_parent_into_children`
  を追加
- `vector_db/chroma.py` の `upsert` で **子チャンクのみ embedding を保存**、
  親チャンクの内容は metadata (`parent_content`) に格納
- `search` 時は子チャンクで一致を取り、親チャンクを context として返す

### 完了条件
- 同じ質問でも、より広い文脈を LLM に渡せるようになっている
- 同じ親チャンクの子が複数ヒットしても、結果は親単位で重複排除されている

### 学習ポイント
- 検索粒度と回答粒度の分離
- metadata 設計の妙

### 関連ファイル
- `backend/rag.py`
- `backend/vector_db/chroma.py`

---

## Issue: Phase 6 — rerank を実装する

### 目的
ハイブリッド検索 + 親子チャンクの結果に対し、**rerank を追加** して
top_n を絞る。

### 作業内容
- `backend/rag.py` に `rerank(query, chunks, top_n)` を追加
- 教材としては、まずクエリ語の一致数で並べ替える heuristic 実装で OK
- 必要であれば cross-encoder (e.g. `bge-reranker-base`) を導入

### 完了条件
- 検索後 K 件 → rerank で top_n 件、というフローが入っている
- top_n を `.env` で調整できる

### 学習ポイント
- rerank のコストと効果のバランス
- BM25 だけで足りるケース vs 足りないケース

### 関連ファイル
- `backend/rag.py`
- `backend/main.py` (chat の流れに `rerank` を組み込む)

---

## Issue: Phase 7 — AWS 移行 (Terraform + GitHub OIDC)

### 目的
ローカル前提のテンプレを、**AWS 上で動かす** ところまで持っていく。

### 作業内容
- `terraform/main.tf`
  - VPC のサブネット / IGW / NAT / Route Table / SG を有効化
  - Bedrock 用 VPC Endpoint を作成
  - RDS for PostgreSQL を立てる (当面はコンテナ同居でも OK)
  - OpenSearch Serverless (VECTORSEARCH) を作成
  - ECR + ECS Fargate + ALB を作成
- `backend/llm/bedrock.py` の `BedrockChatModel.stream` / `BedrockEmbedModel.embed`
  を実装
- `backend/vector_db/opensearch.py` の各メソッドを実装
- `.github/workflows/` に OIDC で `terraform apply` するワークフローを追加
- `.github/workflows/` に ECR push + ECS deploy ワークフローを追加

### 完了条件
- AWS 上で `https://<alb>/` がチャットを返す
- `LLM_PROVIDER=bedrock` / `VECTOR_DB_PROVIDER=opensearch` に切り替え可能
- GitHub Actions から OIDC で apply / deploy できる

### 学習ポイント
- PrivateLink 経由で Bedrock を呼ぶ構成
- OpenSearch Serverless の AccessPolicy / NetworkPolicy

### 関連ファイル
- `terraform/main.tf`
- `backend/llm/bedrock.py`
- `backend/vector_db/opensearch.py`
- `.github/workflows/`

---

## Issue: Phase 8 — RAGAS で品質評価を回す

### 目的
RAG の **検索 / 生成品質をオフラインで定量評価** できるようにし、
改善サイクルを回す。

### 作業内容
- `eval/` ディレクトリを新設
- 評価用データセット (質問 + 期待回答 + 期待ソース) を JSON で用意
- `ragas` で `faithfulness` / `answer_relevancy` / `context_precision` を測る
- 結果を `docs/eval/` に Markdown で残す

### 完了条件
- `make eval` で 1 コマンドで評価が回る
- Langfuse の trace と RAGAS のスコアが突き合わせられる

### 学習ポイント
- 評価セットの作り方（典型・例外・ハマりどころ）
- 「主観品質」と「RAGAS 値」の解釈の差

### 関連ファイル
- `eval/`
- `docs/eval/`
