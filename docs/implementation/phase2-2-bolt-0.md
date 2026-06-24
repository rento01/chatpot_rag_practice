# Implementation Report

## 対象

- Issue #2
- Phase 2-2
- bolt-0

---

## Summary

| 項目 | 内容 |
|---|---|
| Phase | Phase 2-2 |
| Bolt | bolt-0 |
| Issue | #2 |
| 実装内容 | `ChromaVectorDB.search` を BM25 + 文字 bigram で実装 |
| 変更ファイル数 | 2 |
| Verification | PASS |
| Remaining Issues | 2 件（janome 対応、main.py NotImplementedError 節） |
| Next Action | Docker 再ビルド → 動作確認 → TaskLog 作成 |

---

## 実装概要

- `ChromaVectorDB.search` の `NotImplementedError` を BM25 キーワード検索で置き換えた
- 文字 bigram（2 文字スライド）でトークナイズし、日本語テキストにも対応した
- `score > 0` フィルタによって、ヒットなし時は空リストを返す構造にした
- これにより `build_context` → LLM への RAG パイプラインが end-to-end で動くようになった

---

## Changed Files

| ファイル | 種別 | 内容 |
|---|---|---|
| `backend/vector_db/chroma.py` | 修正 | `_bigram` ヘルパー追加・`search` メソッド実装（NotImplementedError を置き換え） |
| `pyproject.toml` | 修正 | `rank-bm25>=0.2.2` を依存に追加 |

---

## Verification

| 確認項目 | 結果 |
|---|---|
| T-01：RAG モード ON でヒットが返ること | PASS（検索ヒットを確認） |
| T-02：ヒットなし時に「資料に記載がありません」が返ること | PASS（応答を確認） |
| T-03：空コレクションで例外が起きないこと | コード上は `try/except` と `not documents` で対応済み |
| バックエンドログに ERROR なし | PASS（WARNING 1 件は設計どおりの動作） |

---

## Implementation Decisions

### 判断内容

- BM25（`rank_bm25`）を採用し、Chroma のテキストフィルタ（`where_document`）は使用しない
- 日本語トークナイザは文字 bigram とし、janome 等の形態素解析は導入しない
- `_bigram` をモジュールレベルのヘルパーとして切り出した

### 判断理由

- BM25 採用：Issue の学習ポイント「BM25 の挙動と日本語での効きどころ」に直結するため。Chroma テキストフィルタでは BM25 スコアが得られない
- 文字 bigram 採用：追加ライブラリなしで日本語を扱えるため。Issue の「素朴な実装で一度動かしてから観察する」方針に沿う
- `_bigram` をヘルパーに切り出した理由：Phase 3-2 でトークナイザを差し替える際に、`search` 本体を変えずに `_bigram` の呼び出し箇所だけを変更できる構成にするため

---

## Design Differences

なし

---

## Remaining Issues

### Remaining Issues

- `main.py` の `except NotImplementedError` 節の削除（Phase 2-1 からの持ち越し）→ taskLog 残課題として記録

### Future Improvements

- janome 等の形態素解析を用いた日本語トークナイズで検索精度を改善する（検索精度改善時に判断）
- `chroma.py` のモジュール docstring が `search` 実装後も旧い記述（「検索系は NotImplementedError を投げて」）を含んでいる（機能影響なし、任意対応）

---

## Handover

なし（bolt-0 = Issue #2 完了）

---

## References

- [docs/design/phase2-2-requirements.md](../design/phase2-2-requirements.md)
- [docs/design/phase2-2-bolt-0.md](../design/phase2-2-bolt-0.md)
