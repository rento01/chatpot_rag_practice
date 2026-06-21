# Implementation Report

## 対象

- Issue #1
- Phase 2-1
- bolt-0

---

## Summary

- PDF ファイル取り込みパイプライン（テキスト抽出 → チャンク分割 → ChromaDB 保存）を実装
- `/ingest` から PDF をアップロードして `status: ready` になることを確認
- Phase 2-1 の完了条件をすべて満たした

---

## Changed Files

| ファイル | 変更内容 |
|---|---|
| `backend/rag.py` | `split_into_chunks` 実装、`index_document` 完成、`import` 2 件追加 |
| `backend/vector_db/chroma.py` | `ChromaVectorDB.upsert` 実装 |

---

## Verification

| 確認項目 | 結果 |
|---|---|
| バックエンド起動 `/health` | OK |
| 既存コレクション API（既存データへの影響なし） | OK |
| PDF アップロード → `status: ready` | OK（page_count: 30 も正常）|
| Chroma コレクションにチャンクが保存されている | OK（count: 2, ids: `doc_3_chunk_0` / `doc_3_chunk_1`）|
| metadata に `document_id` が付与されている | OK（`{'document_id': 3}`）|
| バックエンドログに ERROR / Exception なし | OK |
| lint（ruff） | 未実行（ruff が環境未導入のため省略）|

---

## Implementation Decisions

- **`collection.upsert` を採用**: `add` は同一 ID が存在するとエラーになるため、再アップロード時の安全性を優先して `upsert` を使用
- **embedding は Chroma のデフォルト埋め込みに任せる**: Phase 2-1 時点では `Chunk.embedding` は常に `None`。`embeddings` 引数を渡さなければ Chroma の ONNX バンドルが自動生成する。Phase 3-1 で実 embedding を渡すよう `upsert` を拡張する設計
- **`get_or_create_collection` を使用**: 同一コレクションに複数ドキュメントを追加するケースに対応するため `create_collection` ではなく `get_or_create_collection` を使用

---

## Design Differences

なし

---

## Remaining Issues

### Future Improvements

- `main.py` の `except NotImplementedError` 節の削除 → **taskLog 残課題として記録**（GitHub Issue 化なし。数行の削除のみで独立 Issue を立てる規模ではないため）
- チャンク分割の改善（親子チャンク / Markdown 見出しベース）は Phase 5 で対応

### Review Findings

対応見送りとした指摘（Low のみ、動作影響なし）

- Low
    - [L-1] `any(c.embedding for c in chunk_list)` の None チェックが暗黙的。`c.embedding is not None` の方が意図が明確
    - [L-2] `chunk_list` を `any(...)` と list comprehension で 2 回スキャンしている。変数に切り出すと整理される

### Related Issues

| 課題 | 対応方針 | 判断理由 |
|---|---|---|
| ruff 導入 | GitHub Issue #7 として作成 | 開発環境整備として独立した作業。後から着手しやすくするため Issue 化 |
| `main.py` NotImplementedError 削除 | taskLog 残課題として記録 | 数行の削除のみ。独立した Issue を立てる規模ではない |
| L-1 / L-2 レビュー指摘 | Phase 3-1 対応時に整理 | 動作影響なし。embedding 実装時に同箇所を自然に修正できる |

---

## Handover

なし（bolt-0 = Issue #1 完了）

Phase 2-2（Issue #2）へ進む：`ChromaVectorDB.search` のキーワード検索実装。

---

## Review Summary

### Review Result

**Approve**

### Review Notes

**High:** なし

**Medium:** なし

**Low:**
- [L-1] `c.embedding` の None チェックが暗黙的（`c.embedding is not None` が明示的）
- [L-2] `chunk_list` を 2 回スキャン

### Review Fixes

- [L-1] **対応見送り（Phase 3-1 で整理予定）**
  実装者として指摘に同意する。`c.embedding is not None` の方が意図が明確で望ましい。
  ただし、現状の `None` falsy 判定も Phase 2-1 の動作に影響しないため、
  Phase 3-1 で embedding を実装する際に同箇所を修正する。

- [L-2] **対応見送り（Phase 3-1 で L-1 と合わせて整理予定）**
  実装者として指摘に同意する。`has_embeddings` 変数に切り出すことで可読性が上がる。
  L-1 と同じタイミング（Phase 3-1）で一括して対応する。

---

## References

- [docs/design/phase2-1-requirements.md](../design/phase2-1-requirements.md)
- [docs/design/phase2-1-bolt-0.md](../design/phase2-1-bolt-0.md)
- docs/taskLog/phase2-1-bolt-0.md（作成予定）
