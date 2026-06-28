# Phase 3-2 Summary

## Summary

| 項目 | 内容 |
|---|---|
| Phase | Phase 3-2 |
| Issue | #4 |
| Pull Request | #33 |
| Bolt数 | 1（bolt-0 のみ） |
| 実装結果 | 完了 |
| Review結果 | Approve |
| Remaining Issues | 4 件 |
| 次Phase | Phase 3-3 |

---

## Phase概要

Phase 3-1 で embedding 生成が取り込み時に組み込まれたことで、ChromaDB 内の各チャンクに 768 次元の embedding が付与された。Phase 3-2 では `ChromaVectorDB.search` を BM25 キーワード検索からベクトル検索（コサイン類似度 / k-NN）に差し替え、キーワードが一致しなくても意味的に近いチャンクを取得できるようにした。これにより Phase 3 のコア機能（取り込み時 embedding 生成 + 検索時ベクトル検索）が揃い、Phase 3-3 のハイブリッド検索の前提が整った。

---

## 完了内容

- `ChromaVectorDB.search` を `collection.query(query_embeddings=...)` を使ったベクトル検索に差し替え
- BM25 検索コードをコメントアウトで残存（Phase 3-3 ハイブリッド検索で再利用予定）
- クエリ embedding 生成失敗時・コレクション未作成時に空リストを返す安全設計を実装
- score を `1.0 - distance / 2.0` で [0, 1] に変換（nomic-embed-text は単位正規化済みのため L2 ≒ cosine）
- `SEARCH_TOP_K` を `.env` から設定可能にした（`settings.py` / `.env.example` 追加）
- `docs/development_flow.md` に「前 Phase サマリー確認」ステップを追加
- `bolt-planning` / `code-review` スキルにプロジェクトテンプレート参照を追加

---

## 主な設計判断

| 項目 | 判断 | 理由 |
|---|---|---|
| BM25 コードの扱い | コメントアウトで残存 | Phase 3-3 のハイブリッド検索で再利用するため削除より保存が合理的。ユーザー判断で実装中に変更 |
| score 変換式 | `1.0 - distance / 2.0` | nomic-embed-text は単位正規化済みのため ChromaDB デフォルトの L2 距離とコサイン距離は等価。`1 - distance/2` で [0, 1] に変換できる |
| embedding 生成失敗時の挙動 | 空リストを返す | 検索エラーを上位（`build_context`）に伝搬させず「ヒットなし」として安全に処理できる。教材として安全側の設計を優先 |
| `rank_bm25` import / `_bigram` 関数 | 残存（コメントアウトなし） | Phase 3-3 での再利用を見越してそのまま残す |

---

## 実装内容

- **ベクトル検索**: `search` 冒頭で `get_embed_model().embed([query])` を呼びクエリ embedding を生成し、`collection.query(query_embeddings=[query_embedding], n_results=top_k)` で ChromaDB のベクトル検索を実行
- **フォールバック**: embedding 生成失敗時は `logger.warning` + 空リスト返却。コレクション未作成時は既存と同様に空リスト返却
- **設定化**: `settings.search_top_k`（デフォルト 5）で `top_k` のデフォルト値を `.env` から制御可能にした

---

## Review結果

| Severity | 件数 |
|---|---|
| High | 0 |
| Medium | 1 |
| Low | 1 |

### 主な指摘

- F-01（Medium）: `n_results=top_k` がコレクションのチャンク数を超えた場合のエラーリスク
- F-02（Low）: `chroma.py` 冒頭 docstring に Phase 3-2 の記載がない

### 対応方針

- F-01: Remaining Issues（RI-05）に記録。教材規模では発生しにくい。Phase 3-3 着手時に `min(top_k, col.count())` で対応検討
- F-02: Remaining Issues（RI-06）に記録。軽微。Phase 3-3 着手時に合わせて更新

---

## Remaining Issues

| 課題 | 対応方針 |
|---|---|
| RI-01: `chroma.py:82` の `any(c.embedding ...)` の書き方（Phase 2-1 レビュー指摘） | Future（静的解析導入時） |
| RI-02: `main.py` の `except NotImplementedError` 節の削除（Phase 2-1 からの持ち越し） | 別 Issue |
| RI-05: `n_results=top_k` がチャンク数を超えた場合のエラーリスク（Phase 3-2 Code Review F-01） | Phase 3-3 または別 Issue |
| RI-06: `chroma.py` 冒頭 docstring に Phase 3-2 の記載がない（Phase 3-2 Code Review F-02） | Future（Phase 3-3 着手時） |

---

## GitHub Issues

| Issue | 内容 | 状態 |
|---|---|---|
| #4 | Phase 3-2: ベクトル検索を実装する | Closed（PR #33 マージ済み） |
| #7 | chore: ruff を dev 依存に追加して lint を整備する | Open（持ち越し） |

---

## WorkLogからの振り返り

### 主な実装判断

- BM25 コードは削除せずコメントアウトで残存。Phase 3-3 のハイブリッド検索で再利用するため、実装中にユーザー判断で設計を変更した
- score 変換式は nomic-embed-text の単位正規化特性に基づいて採用した

### 発生した問題

- なし

### 解決方法

- なし

---

## 学んだこと

- ChromaDB の `collection.query(query_embeddings=...)` でベクトル検索が実行できる
- nomic-embed-text は単位正規化済みのため、ChromaDB デフォルトの L2 距離とコサイン距離は等価になる。`score = 1 - distance/2` で [0, 1] の類似度スコアに変換できる
- キーワード検索（BM25）では「年次有給休暇」に「休みは何日取れますか」がヒットしないが、ベクトル検索では意味的に近いためヒットすることを実際に確認できた
- `SEARCH_TOP_K` を `.env` から制御する設計で、引数シグネチャを変えずに設定可能にできる

---

## 次Phaseへの引き継ぎ

### 次にやること

- Issue #5（または対応する Issue） Phase 3-3「ハイブリッド検索を実装する」へ進む
- BM25 + ベクトル検索を RRF（Reciprocal Rank Fusion）で統合するハイブリッド検索を実装する

### 注意事項

- BM25 コードは `ChromaVectorDB.search` 内にコメントアウトで残存している。Phase 3-3 で再利用できる
- `rank_bm25` import と `_bigram` 関数は削除せずに残存している
- RI-05（`n_results=top_k` 上限制御）は Phase 3-3 着手時に `min(top_k, col.count())` で対応検討する

### 未対応事項

- RI-01: `chroma.py` の `any(c.embedding ...)` 書き方の改善
- RI-02: `main.py` の `except NotImplementedError` 節の削除
- RI-05: `n_results=top_k` がチャンク数を超えた場合のエラーリスク
- RI-06: `chroma.py` 冒頭 docstring の更新
- ruff 導入（Issue #7）

---

## References

- Requirements: [docs/design/phase3-2-requirements.md](../design/phase3-2-requirements.md)
- Bolt Design: [docs/design/phase3-2-bolt-0.md](../design/phase3-2-bolt-0.md)
- WorkLog: [tmp/worklog/phase3-2-bolt-0.md](../../tmp/worklog/phase3-2-bolt-0.md)
- TaskLog: [docs/taskLog/phase3-2-bolt-0.md](../taskLog/phase3-2-bolt-0.md)
- PR: [#33 feat(phase3-2): implement vector search in ChromaVectorDB](https://github.com/rento01/chatpot_rag_practice/pull/33)
