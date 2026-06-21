# Phase 2-1 Summary

## Summary

| 項目 | 内容 |
|---|---|
| Phase | Phase 2-1 |
| Issue | #1 |
| Bolt数 | 1（bolt-0 のみ） |
| 実装結果 | 完了 |
| Review結果 | Approve |
| Remaining Issues | 3 件 |
| 次Phase | Phase 2-2 |

---

## 完了内容

- `backend/rag.py` の `split_into_chunks` を実装（RecursiveCharacterTextSplitter、chunk_size=500、chunk_overlap=50）
- `backend/rag.py` の `index_document` を完成（extract_text → split_into_chunks → Chunk 化 → vdb.upsert）
- `backend/vector_db/chroma.py` の `ChromaVectorDB.upsert` を実装（get_or_create_collection + collection.upsert）
- PDF をアップロードして `status: ready` になることを動作確認（30 ページ PDF、PASS）
- Chroma コレクションにチャンクが保存されていることを確認（count: 2、ids / metadata 目視確認）
- Phase 2-1 の設計ドキュメント一式を整備（requirements / bolt 設計 / implementation report / taskLog）
- PR #8 を作成・CI グリーン確認・main にマージ

---

## 設計判断

| 項目 | 判断 | 理由 |
|---|---|---|
| Chroma ids 形式 | `doc_{document_id}_chunk_{chunk_index}` | document_id と chunk_index の意味が明確。学習用途として可読性を優先 |
| `collection.add` vs `collection.upsert` | `upsert` を採用 | 同一 ID のチャンクを再アップロード時に上書きできるため。`add` は重複 ID でエラーになる |
| embedding の扱い | Phase 2-1 では `None`、Chroma のデフォルト埋め込みに任せる | Phase 2-1 の目的はキーワード検索の土台作り。実 embedding は Phase 3-1 で追加する設計 |
| `get_or_create_collection` を使用 | `create_collection` ではなく `get_or_create_collection` | 同一コレクションに複数ドキュメントを追加するケースに対応するため |
| 空チャンクガード | `if chunks:` で upsert をスキップ | スキャン PDF 等でテキスト抽出ゼロの場合に対応。page_count のみ返す |
| `main.py` の `except NotImplementedError` 削除 | 今回のスコープ外 | PR を小さく保つ。リファクタ寄りの変更のため taskLog 残課題として記録 |

---

## 実装内容

- **`split_into_chunks`**: `RecursiveCharacterTextSplitter` で 500 文字・overlap 50 のチャンク分割。依存追加不要（`langchain-text-splitters` は既存の依存）
- **`index_document`**: テキスト抽出 → 分割 → Chunk 化 → upsert のパイプラインを結合。空チャンク時は upsert スキップ
- **`ChromaVectorDB.upsert`**: コレクション自動作成・idempotent 保存・metadata 付与

---

## Review結果

| Severity | 件数 |
|---|---|
| High | 0 |
| Medium | 0 |
| Low | 2 |

### 指摘内容

- [L-1] `any(c.embedding for c in chunk_list)` の None チェックが暗黙的。`c.embedding is not None` の方が意図が明確（`backend/vector_db/chroma.py:68`）
- [L-2] `chunk_list` を `any(...)` と list comprehension で 2 回スキャンしている。`has_embeddings` 変数に切り出すと整理される（同箇所）

### 対応方針

- Phase 3-1 で embedding を実装する際に L-1・L-2 を合わせて修正する（動作影響なし）

---

## Remaining Issues

| 課題 | 対応方針 |
|---|---|
| `main.py` の `except NotImplementedError` 節の削除 | taskLog 残課題として記録（GitHub Issue 化なし。数行の削除のみ）|
| L-1・L-2 レビュー指摘対応 | Phase 3-1 での embedding 実装時に整理 |
| ruff 導入 | GitHub Issue #7（`chore: ruff を dev 依存に追加して lint を整備する`）|

---

## GitHub Issues

| Issue | 内容 | 状態 |
|---|---|---|
| #1 | Phase 2-1: ファイル取り込みを動かす | Closed（PR #8 でマージ済み）|
| #7 | chore: ruff を dev 依存に追加して lint を整備する | Open |

---

## 学んだこと

- **RecursiveCharacterTextSplitter の挙動**: 段落・文・単語の順にセパレータを試みるため固定長スプリッタより自然な境界で分割される。`chunk_size` は上限であり、ぴったり切れるわけではない
- **Chroma のデフォルト埋め込み**: `embeddings` 引数なしで `collection.upsert` を呼ぶと ONNX バンドルモデルが起動する。初回は約 10 秒かかるがキャッシュされる。Phase 3-1 で実 embedding に差し替えるときは同じメソッドに `embeddings` を渡すだけで済む設計
- **collection.add vs collection.upsert**: `add` は同一 ID でエラー。再アップロードや再試行を許容するには `upsert` が適切
- **BackgroundTasks の非同期処理**: `main.py` の `_index_document` は既に `BackgroundTasks` で非同期化されており、重い PDF 処理もタイムアウトせず完走できる構造になっていた

---

## 次Phaseへの引き継ぎ

### 次にやること

- Issue #2 Phase 2-2「キーワード検索を実装する」へ進む
- `ChromaVectorDB.search` をキーワード検索（BM25 等）で実装する

### 注意事項

- 今回 upsert 時に付与した `metadata: {"document_id": document_id}` と ids 形式 `doc_{document_id}_chunk_{i}` を前提に search を設計してよい
- Chroma のデフォルト埋め込みで保存されているため、Phase 2-2 のキーワード検索は `where_document={"$contains": query}` 等のテキストフィルタで実装する想定

### 未対応事項

- embedding の生成・付与（Phase 3-1）
- チャンク分割の改善（Phase 5）
- `main.py` の `except NotImplementedError` 節の削除（taskLog 残課題）
- L-1・L-2 レビュー指摘対応（Phase 3-1）
- ruff 導入（Issue #7）

---

## References

- Requirements: [docs/design/phase2-1-requirements.md](../design/phase2-1-requirements.md)
- Bolt Design: [docs/design/phase2-1-bolt-0.md](../design/phase2-1-bolt-0.md)
- Implementation Report: [docs/implementation/phase2-1-bolt-0.md](../implementation/phase2-1-bolt-0.md)
- TaskLog: [docs/taskLog/phase2-1-bolt-0.md](../taskLog/phase2-1-bolt-0.md)
- PR: [#8 feat(phase2-1): implement PDF ingest pipeline](https://github.com/rento01/chatpot_rag_practice/pull/8)
