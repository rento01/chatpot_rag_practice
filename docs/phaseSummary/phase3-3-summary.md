# Phase 3-3 Summary

## Summary

| 項目 | 内容 |
|---|---|
| Phase | Phase 3-3 |
| Issue | #5 |
| Pull Request | #35 |
| Bolt数 | 1（bolt-0 のみ） |
| 実装結果 | 完了 |
| Review結果 | Approve |
| Remaining Issues | 4 件 |
| 次Phase | Phase 4（Langfuse） |

---

## Phase概要

Phase 3-2 まではベクトル検索のみで、キーワードが直接一致するチャンクが上位に来ない弱点があった。Phase 3-3 では BM25 キーワード検索とベクトル検索を RRF（Reciprocal Rank Fusion）で統合するハイブリッド検索を `ChromaVectorDB.search` に実装した。Phase 2-2 でコメントアウト保存していた BM25 コードを再利用し、3 ファイルの変更のみで両者の弱点を補い合う検索を実現した。

---

## 完了内容

- Phase 2-2 の BM25 コメントアウトを解除し、ベクトル検索と組み合わせて再利用
- BM25 + ベクトル検索の両方を実行し、RRF でスコアを統合
- RRF スコア = `Σ 1 / (rrf_k + rank)`。両リストにヒットしたチャンクはスコアが加算されて上位になる
- BM25（corpus インデックス）と Chroma（document ID）の異なるキー空間を `bm25_{idx}` で統一
- `n_results=min(top_k, col.count())` で RI-05（チャンク数超過エラー）を解消
- `rrf_k`（デフォルト 60）を `settings.py` / `.env.example` に追加し `.env` から調整可能にした
- embedding 生成失敗時は BM25 のみで継続するフォールバック設計を追加
- Code Review 成果物の保存先（`docs/review/`）と命名規則をテンプレートに追加
- `development_flow.md` の成果物一覧に Code Review ファイルを追記

---

## 主な設計判断

| 項目 | 判断 | 理由 |
|---|---|---|
| BM25・ベクトル検索の候補数を `search_top_k` で共用 | 別パラメータを設けず共用 | 設定項目を増やさず最小変更。学習者が混乱しにくい構成にする |
| embedding 失敗時は BM25 のみで継続 | 空リストを返さず BM25 ヒットを返す | Phase 3-2 と挙動を変えず安全側を維持。BM25 のヒットがある方が学習者に有用 |
| `rrf_k` デフォルト 60 | 標準値を採用 | RRF の標準値として広く使われている値。`.env` から調整可能なため変更コストも低い |
| 共通キー空間 `bm25_{idx}` | corpus インデックスをキー化して統一 | BM25 とベクトル検索の ID 体系の違いを吸収し、RRF スコア集計を単一辞書で管理できる |

---

## 実装内容

- **`ChromaVectorDB.search`**: BM25 → ベクトル検索 → RRF の順に実行し、スコア降順で上位 `top_k` 件の `SearchResult` を返す
- **BM25**: `col.get()` で全チャンクを取得し `BM25Okapi` でスコア計算。スコア > 0 のもののみ候補にする
- **ベクトル検索**: `col.query()` で cosine 距離から上位チャンクを取得。`min(top_k, col.count())` でチャンク数超過を防ぐ
- **RRF 統合**: `bm25_{idx}` をキーにスコアを加算。両リストに登場したチャンクはスコアが2重加算されて上位になる

---

## Review結果

| Severity | 件数 |
|---|---|
| High | 0 |
| Medium | 0 |
| Low | 2 |

### 主な指摘

- F-01 (Low): `int(key.split("_")[1])` がリスト内包表記で 3 回重複
- F-02 (Low): AC-04（`RRF_K` 変更によるスコア変化テスト）が未実施

### 対応方針

- F-01: RI-07 として記録して見送り（動作に影響なし）
- F-02: 任意確認のため見送り

---

## Remaining Issues

| 課題 | 対応方針 |
|---|---|
| RI-07: `int(key.split("_")[1])` のリスト内包表記内で 3 回重複 | Future |
| RI-01: `chroma.py` の `any(c.embedding ...)` の書き方 | Future |
| RI-02: `main.py` の `except NotImplementedError` 節の削除 | 別 Issue |
| RI-03: `OllamaEmbedModel.embed` のバッチ最適化 | Future |

---

## GitHub Issues

| Issue | 内容 | 状態 |
|---|---|---|
| #5 | Phase 3（embedding・ベクトル検索・ハイブリッド検索） | Closed（PR #35 マージ） |
| #7 | chore: ruff を dev 依存に追加して lint を整備する | Open（持ち越し） |
| #34 | Codex 導入の検討・整理 | Open |

---

## WorkLogからの振り返り

### 主な実装判断

- Phase 2-2 時点のコメントアウトが綺麗に再利用できた。「次 Phase で使う」という設計意図が実際に機能した
- BM25 とベクトル検索で ID 体系が異なる問題を、`bm25_{idx}` の共通キーで解決した

### 発生した問題

- 特になし（RI-05 のチャンク数超過は Bolt Design 時点で把握済みで対応済み）

### 解決方法

- `n_results=min(top_k, col.count())` で RI-05 を先回り対応

---

## 学んだこと

- RRF はシンプルな式（`1/(k+rank)` の加算）で 2 つの検索結果を統合できる。重み調整が不要で実装コストが低い
- BM25 とベクトル検索を統合する際、ID 空間の違いを「共通キー」で吸収する設計が有効
- BM25 は `col.get()` で全チャンクを取得してからスコア計算するため、教材規模では問題ないがチャンク数増加時の影響に注意
- 「有休はいつから使えますか」が「記載がありません」になるのは文書にその情報がないためであり、ハイブリッド検索の正常動作

---

## 次Phaseへの引き継ぎ

### 次にやること

- Phase 4（Langfuse）へ進む
- 観測・トレース基盤の構築

### 注意事項

- ChromaDB には Phase 3-3 実装済みのハイブリッド検索（BM25 + ベクトル + RRF）が動いている
- `RRF_K` は `.env` から調整可能（デフォルト 60）
- RI-07 の `int(key.split("_")[1])` 重複は Future 対応

### 未対応事項

- RI-07: `int(key.split("_")[1])` のリスト内包表記内重複
- RI-01: `chroma.py` の `any(c.embedding ...)` 書き方の改善
- RI-02: `main.py` の `except NotImplementedError` 節の削除
- RI-03: `OllamaEmbedModel.embed` のバッチ最適化
- ruff 導入（Issue #7）
- Codex 導入（Issue #34）

---

## References

- Requirements: [docs/design/phase3-3-requirements.md](../design/phase3-3-requirements.md)
- Bolt Design: [docs/design/phase3-3-bolt-0.md](../design/phase3-3-bolt-0.md)
- WorkLog: [tmp/worklog/phase3-3-bolt-0.md](../../tmp/worklog/phase3-3-bolt-0.md)
- TaskLog: [docs/taskLog/phase3-3-bolt-0.md](../taskLog/phase3-3-bolt-0.md)
- Code Review: [docs/review/phase3-3-bolt-0.md](../review/phase3-3-bolt-0.md)
- PR: [#35 feat(phase3-3): implement hybrid search with BM25, vector search, and RRF](https://github.com/rento01/chatpot_rag_practice/pull/35)
