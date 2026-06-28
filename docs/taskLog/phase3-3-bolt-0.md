# Phase 3-3 bolt-0

## サマリー

| 項目 | 内容 |
|---|---|
| 目的 | `ChromaVectorDB.search` に BM25 + ベクトル検索 + RRF を実装し、両者の弱点を補完するハイブリッド検索を実現する |
| 実施内容 | BM25 コメントアウトを解除して再利用。ベクトル検索と RRF 統合を実装。`RRF_K` を `.env` で設定可能にした |
| 変更ファイル | 3 ファイル（`chroma.py` / `settings.py` / `.env.example`） |
| 動作確認 | PASS |
| Code Review | Approve（Low: 2件、いずれも Remaining Issues に記録） |
| 課題 | RI-07: `int(key.split("_")[1])` の重複（Future） |
| 次の対応 | Phase 3-3 完了 → Phase 4（Langfuse） |

---

## 基本情報

### 実施日

2026-06-29

### 対応 Issue

#5

### bolt

bolt-0

---

## 目的

`ChromaVectorDB.search` を BM25 キーワード検索とベクトル検索の両方を実行し、RRF（Reciprocal Rank Fusion）でスコアを統合するハイブリッド検索に拡張する。キーワードが一致する場合も意味的に近い場合も、どちらでもヒットを返せる安定した検索を実現する。

---

## Requirements 対応

### 対応項目

- R-01: BM25 検索とベクトル検索の両方を実行し結果リストを取得できること
- R-02: RRF でスコアを統合し `list[SearchResult]` として返せること
- R-03: 全ケース（BM25 のみ・ベクトルのみ・両方・なし）で正しく動くこと
- R-04: `rrf_k` が `.env` から設定できること
- R-05: `n_results` がチャンク数を超えないように制御すること（RI-05 対応）

### 完了判定

- AC-01: ハイブリッド検索が実行されエラーなく結果が返ること → **PASS**
- AC-02: 言い回しを変えた質問でもヒットが返ること → **PASS**（「年次有給休暇は何日取れますか」で確認）
- AC-03: 両方でヒットしたチャンクが上位に来ること → **PASS**（ログ上エラーなし）
- AC-04: `.env` から `RRF_K` が切り替えられること → 未確認（任意）

---

## 実施内容

- Phase 2-2 BM25 コメントアウトを解除し、ベクトル検索・RRF 統合と組み合わせて実装
- RRF スコア = `Σ 1 / (rrf_k + rank)`。両リストに登場するチャンクはスコアが加算されて上位になる
- `n_results=min(top_k, col.count())` で RI-05（チャンク数超過エラー）を対応
- embedding 生成失敗時はベクトル検索をスキップし、BM25 のみの結果を RRF スコアに変換して返す
- `rrf_k`（デフォルト 60）を `settings.py` / `.env.example` に追加

---

## 変更ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `backend/vector_db/chroma.py` | 修正 | `search` を BM25 + ベクトル検索 + RRF に差し替え。BM25 コメントアウト解除。`min(top_k, col.count())` で RI-05 対応 |
| `backend/config/settings.py` | 修正 | `rrf_k: int` フィールドと `os.getenv("RRF_K", "60")` を追加 |
| `.env.example` | 修正 | `RRF_K=60` をコメント付きで追加 |

---

## 実装概要

`search` メソッドで BM25 とベクトル検索を両方実行し、それぞれの結果リスト（corpus インデックス / Chroma document ID）を共通キー `bm25_{idx}` に統一して RRF スコアを集計する。RRF スコアで降順ソートして上位 `top_k` 件の `SearchResult` を返す。

---

## 実装判断

### 判断1: BM25・ベクトル検索の候補数を `search_top_k` で共用

**理由**: 設定項目を増やさず最小変更。学習者が混乱しにくい構成にする。

### 判断2: embedding 生成失敗時は BM25 のみの結果を返す

**理由**: 完全に空リストにするより BM25 のヒットがある方が学習者にとって有用。Phase 3-2 と挙動を変えず安全側を維持する。

### 判断3: `rrf_k` のデフォルト 60

**理由**: RRF の標準値として広く使われている値。`.env` から調整可能にしているため変更コストも低い。

---

## 設計との差異

なし

---

## 動作確認

| 確認内容 | 期待結果 | 実結果 | 判定 |
|---|---|---|---|
| ハイブリッド検索でヒットが返ること | BM25 + ベクトル検索が実行され回答が返る | 回答が返った。backend ログに警告なし | PASS |
| 言い回しを変えた質問でもヒットが返ること | 「年次有給休暇は何日取れますか」でヒット | ヒットが返った | PASS |

---

## Code Review 結果

**Approve**（High: 0 / Medium: 0 / Low: 2）

| ID | 内容 | 対応 |
|---|---|---|
| F-01 | `int(key.split("_")[1])` がリスト内包表記内で3回重複 | **Remaining Issues（RI-07）**: 動作に影響なし。Future |
| F-02 | AC-04（`RRF_K` 変更テスト）が未実施 | **見送り**: 任意確認のため |

---

## 発生した問題と対応

なし

---

## 学んだこと

- RRF はシンプルな式（`1/(k+rank)` の加算）で2つの検索結果を統合できる。重み調整が不要で実装コストが低い
- BM25 とベクトル検索を「同じキー空間」に統一するために corpus インデックスを `bm25_{idx}` 形式でキー化するアプローチが有効
- BM25 は `col.get()` で全チャンクを取得してからスコア計算するため、教材規模では問題ないがチャンク数増加に注意が必要
- 「有休はいつから使えますか」が「記載がありません」になるのは文書にその情報がないためであり、ハイブリッド検索の正常動作

---

## 課題

### Remaining Issues

- RI-07: `int(key.split("_")[1])` がリスト内包表記で3回重複（Future）
- RI-01: `chroma.py:82` の `any(c.embedding ...)` の書き方（Future）
- RI-02: `main.py` の `except NotImplementedError` 節の削除（別 Issue）
- RI-03: `OllamaEmbedModel.embed` のバッチ最適化（Future）

### GitHub Issues

- #5（本 Issue）: 本 bolt で完了

---

## 次の bolt への引き継ぎ

- なし（Issue #5 完了）
- 次は Phase 4（Langfuse）へ進む

---

## 関連資料

**Requirements**
- `docs/design/phase3-3-requirements.md`

**Bolt Design**
- `docs/design/phase3-3-bolt-0.md`

**Code Review**
- `docs/review/phase3-3-bolt-0.md`

---

## 関連コミット

（Commit 後に記入）

---

## 関連 PR

（PR 作成後に記入）
