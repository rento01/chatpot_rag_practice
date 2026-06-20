# Phase 2-1 bolt-0 設計

## bolt分割判定

分割不要。bolt-0 のみで進める。

理由：
- 実装対象は 3 関数・2 ファイルのみ
- 3 関数は密結合（`split_into_chunks` → `index_document` → `upsert` の一本道）
- 推定差分は 60〜80 行程度
- 責務は「取り込みパイプラインを完走させる」1 つに絞れる

---

## bolt-0: ファイル取り込みパイプライン実装

### 目的

`split_into_chunks` / `index_document` / `ChromaVectorDB.upsert` の 3 関数を実装し、
PDF をアップロードしたとき status が `ready` になるまでパイプラインを完走させる。

### 作るもの

- **`backend/rag.py` — `split_into_chunks`**
  - `RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)` で実装
  - `langchain_text_splitters` は `pyproject.toml` に既に含まれているため、依存追加不要

- **`backend/rag.py` — `index_document`**
  - `extract_text` → `split_into_chunks` → `Chunk` 化 → `vdb.upsert` を繋ぐ
  - チャンクが空（テキスト抽出ゼロ）の場合は upsert をスキップして `page_count` だけ返す
  - 戻り値: `page_count: int`（`main.py` 側がそのまま `documents.page_count` に書き込む仕様）

- **`backend/vector_db/chroma.py` — `ChromaVectorDB.upsert`**
  - `client.get_or_create_collection` でコレクションを取得・作成
  - ids 形式: `doc_{document_id}_chunk_{chunk_index}`
  - `metadata` に `document_id`（int）を保存する（`delete_document` の `where` フィルタで使用）
  - `collection.upsert` を使う（再アップロード時に同一 ID を上書きできるよう、`add` より idempotent）
  - `Chunk.embedding` が `None` の場合は `embeddings` を渡さない（Chroma の default 埋め込みに任せる）

### 作らないもの

- `ChromaVectorDB.search` — Phase 2-2 で実装
- `Chunk.embedding` の生成 — Phase 3-1 で実装（今回は常に `None`）
- `main.py` の `except NotImplementedError` 節の削除 — Phase 2-1 完了後のリファクタ（bolt 完了後の taskLog に残課題として記録）
- `delete_document` の本実装 — 既存のまま（upsert と整合を取るのは後フェーズ）

### 対象ファイル・ディレクトリ

| 種別 | ファイル |
|---|---|
| 書く | `backend/rag.py` |
| 書く | `backend/vector_db/chroma.py` |
| 読む（参照） | `backend/vector_db/vectorDB.py`（`Chunk` / `VectorDB` の型定義） |
| 読む（参照） | `backend/main.py`（`_index_document` の呼び出し契約確認） |

### 実装方針

- **チャンク分割**: `RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)` を使う。
  Issue に「Phase 2 では固定長 (500 文字など) で OK」とあるため、シンプルな設定にとどめる。
  `chunk_overlap=50` は前後の文脈が切れにくくするための最小値。

- **Chroma への保存**: `collection.upsert` を使う。
  同一 `document_id` のチャンクが再度送られても上書きできるよう、`add` ではなく idempotent な `upsert` にする。

- **embedding の扱い**: Phase 2-1 時点では `Chunk.embedding` は常に `None`。
  `embeddings` を渡さなければ Chroma がデフォルト埋め込み（ONNX バンドル）を自動生成する。
  Phase 3-1 で実 embedding を渡すように `upsert` を拡張する想定。

- **空チャンク対応**: `split_into_chunks` が空リストを返した場合（スキャン PDF 等）、`upsert` 呼び出しをスキップして `page_count` のみ返す。

### ドキュメント更新

- `docs/design/phase2-1-requirements.md` の確認事項は既に更新済み
- 実装完了後に `docs/taskLog/phase2-1-bolt-0.md` を作成する（taskLog は bolt 完了後に書く）

### 完了条件

- `/ingest` ページから PDF をアップロードして status が `ready` になる
- Chroma のコレクションにチャンクが入っていることを確認できる（`collection.get()` 等で確認）
- 数十ページ規模の PDF でタイムアウトしない（BackgroundTasks で非同期実行されている既存の構造をそのまま使う）

### 確認事項

なし（要件定義フェーズで決定済み）

### 次の bolt への引き継ぎ

なし（bolt-0 = Issue #1 完了）

完了後の残課題として taskLog に記録する：
- `main.py` の `except NotImplementedError` 節の削除（Issue #1 完了後のリファクタ）
