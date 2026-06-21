# Phase 2-1 bolt-0

## 実施日

2026-06-21

## 対応Issue

#1

## bolt

bolt-0

## 目的

PDF をアップロードしたとき `status: ready` になるまでパイプラインを完走させる。
`split_into_chunks` / `index_document` / `ChromaVectorDB.upsert` の 3 関数を実装し、
Phase 2-2（キーワード検索）に進める土台を作る。

---

## 実施内容

- `backend/rag.py` の `split_into_chunks` を実装（RecursiveCharacterTextSplitter、chunk_size=500、chunk_overlap=50）
- `backend/rag.py` の `index_document` を完成（extract_text → split_into_chunks → Chunk 化 → vdb.upsert の流れを結合）
- `backend/vector_db/chroma.py` の `ChromaVectorDB.upsert` を実装（get_or_create_collection + collection.upsert）
- Phase 2-1 の設計ドキュメントを整備（requirements / bolt 設計 / implementation report）

---

## 変更ファイル

### 追加

- `docs/design/phase2-1-requirements.md`
- `docs/design/phase2-1-bolt-0.md`
- `docs/implementation/phase2-1-bolt-0.md`
- `docs/taskLog/phase2-1-bolt-0.md`（本ファイル）

### 修正

- `backend/rag.py`
- `backend/vector_db/chroma.py`

### 削除

なし

---

## 実装概要

### split_into_chunks

`langchain_text_splitters.RecursiveCharacterTextSplitter` を使い、テキストを最大 500 文字のチャンクに分割する。
`chunk_overlap=50` を設定することで前後の文脈の断絶を緩和している。
`langchain-text-splitters` は `pyproject.toml` に既存の依存として含まれていたため、新たな依存追加は不要だった。

### index_document

`extract_text` → `split_into_chunks` → `Chunk` オブジェクト化 → `vdb.upsert` の流れを繋いだ。
テキストが抽出できなかった場合（スキャン PDF 等）のために `if chunks:` のガードを入れ、
空の場合は upsert をスキップして `page_count` のみ返す。

### ChromaVectorDB.upsert

- `get_or_create_collection` を使い、コレクションが存在しない場合は自動作成する（複数ドキュメントの追加に対応）
- `ids` は `doc_{document_id}_chunk_{i}` 形式で設定（可読性・追跡性を優先）
- `metadata` に `document_id` を付与（`delete_document` の `where` フィルタと整合）
- `collection.upsert` を採用（`add` と異なり同一 ID を上書きできるため、再アップロード時の安全性を確保）
- `Chunk.embedding` が `None` の場合は `embeddings` 引数を渡さず、Chroma のデフォルト埋め込み（ONNX バンドル）に任せる設計。Phase 3-1 で実 embedding を渡すよう拡張する

---

## 学んだこと

- **RecursiveCharacterTextSplitter の挙動**: 段落・文・単語の順にセパレータを試みるため、固定長スプリッタより自然な境界で分割される。`chunk_size` はあくまで上限であり、ぴったり切れるわけではない。
- **Chroma のデフォルト埋め込み**: `embeddings` 引数なしで `collection.upsert` を呼ぶと ONNX バンドルモデルが起動する。初回は約 10 秒かかるがキャッシュされる。Phase 3-1 で実 embedding に差し替えるときは同じ `upsert` メソッドに `embeddings` を渡すだけで済む設計になっている。
- **collection.add vs collection.upsert**: `add` は同一 ID で呼ぶとエラー。再アップロードや再試行を許容するには `upsert` が適切。
- **BackgroundTasks の非同期処理**: `main.py` の `_index_document` はすでに `BackgroundTasks` で非同期化されており、重い PDF 処理もタイムアウトせず完走できる構造になっていた。今回はその構造をそのまま活かした。

---

## 動作確認

### 実施した確認内容

- バックエンド起動確認（`/health` エンドポイント）
- 既存コレクション API が壊れていないことを確認
- PDF（30 ページ）をアップロードし `status: ready` になることを確認
- `collection.get()` で Chroma にチャンクが保存されていることを確認（count: 2、ids・metadata を目視）
- バックエンドログに ERROR / Exception がないことを確認

### 結果

- PASS（完了条件をすべて満たした）

---

## AIレビュー結果

### High

なし

### Medium

なし

### Low

- [L-1] `any(c.embedding for c in chunk_list)` の None チェックが暗黙的。`c.embedding is not None` の方が意図が明確（`backend/vector_db/chroma.py:68`）
- [L-2] `chunk_list` を `any(...)` と list comprehension で 2 回スキャンしている。`has_embeddings` 変数に切り出すと整理される（同箇所）

**対応方針**: 動作影響なしのため今回は対応見送り。Phase 3-1 で embedding を実装する際に L-1・L-2 を合わせて修正する。

---

## 課題

- `main.py` の `except NotImplementedError` 節の削除（Phase 2-1 完了後のリファクタ。数行の削除のみ。GitHub Issue 化なし）
- L-1・L-2 のレビュー指摘対応（Phase 3-1 での embedding 実装時に整理）
- ruff 導入 → **GitHub Issue #7**（`chore: ruff を dev 依存に追加して lint を整備する`）

---

## 次のboltへの引き継ぎ

なし（bolt-0 = Issue #1 完了）

**次の Phase**: Issue #2 Phase 2-2「キーワード検索を実装する」
- `ChromaVectorDB.search` を実装する
- 今回 upsert 時に付与した `document_id` metadata と `doc_{document_id}_chunk_{i}` の ids 形式を前提に設計してよい

---

## 関連コミット

```text
（作成予定）
```

---

## 関連PR

```
（作成予定）
```
