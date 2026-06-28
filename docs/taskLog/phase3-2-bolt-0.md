# Phase 3-2 bolt-0

## サマリー

| 項目 | 内容 |
|---|---|
| 目的 | `ChromaVectorDB.search` をベクトル検索に切り替え、意味的に近いチャンクを取得できるようにする |
| 実施内容 | `search` をベクトル検索に差し替え。BM25 コードはコメントアウトで残存。`SEARCH_TOP_K` を `.env` で設定可能にした |
| 変更ファイル | 3 ファイル（`chroma.py` / `settings.py` / `.env.example`） |
| 動作確認 | PASS |
| Code Review | Approve（Medium: 1 / Low: 1、いずれも Remaining Issues に記録） |
| 課題 | RI-05: n_results 上限制御未対応 / RI-06: docstring 未更新 |
| 次の対応 | Phase 3-3: ハイブリッド検索（BM25 + ベクトル検索 RRF） |

---

## 基本情報

### 実施日

2026-06-27 〜 2026-06-29

### 対応 Issue

#4

### bolt

bolt-0

---

## 目的

`ChromaVectorDB.search` を BM25 キーワード検索からベクトル検索（コサイン類似度 / k-NN）に切り替え、キーワードが一致しなくても意味的に近いチャンクを取得できるようにする。

---

## Requirements 対応

### 対応項目

- R-01: コサイン類似度（または k-NN）でチャンクを検索できること
- R-02: 言い回しを変えた質問でも、意味的に近いチャンクがヒットすること
- R-03: 検索系パラメータ（top_k 等）が `.env` から設定できること
- R-04: embedding が未登録のチャンクが混在していても、エラーにならず空リストを返すこと

### 完了判定

- AC-01: ベクトル検索でヒットが返る → **PASS**
- AC-02: 言い回しを変えた質問でもヒットが返る → **PASS**（就業規則 PDF で確認）
- AC-03: `.env` からパラメータが切り替えられる → **PASS**

---

## 実施内容

- `backend/vector_db/chroma.py` の `search` を `collection.query(query_embeddings=...)` を使ったベクトル検索に差し替え
- BM25 検索コードはコメントアウトで残存（Phase 3-3 再利用予定）
- `from backend.llm import get_embed_model` を追加
- `backend/config/settings.py` に `search_top_k: int` フィールドを追加
- `.env.example` に `SEARCH_TOP_K=5` を追加

---

## 変更ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `backend/vector_db/chroma.py` | 修正 | `search` をベクトル検索に差し替え。`get_embed_model` import 追加。BM25 コードはコメントアウト残存 |
| `backend/config/settings.py` | 修正 | `search_top_k: int` フィールドと `os.getenv("SEARCH_TOP_K", "5")` を追加 |
| `.env.example` | 修正 | `SEARCH_TOP_K=5` をコメント付きで追加 |

---

## 実装概要

`search` メソッド冒頭で `get_embed_model().embed([query])` を呼びクエリの embedding を生成し、`collection.query(query_embeddings=[query_embedding], n_results=top_k)` で ChromaDB のベクトル検索を実行する。スコアは ChromaDB が返す L2 距離を `1.0 - distance / 2.0` で [0, 1] の類似度スコアに変換する。embedding 生成失敗時・コレクション未作成時はいずれも空リストを返す。

---

## 実装判断

### 判断1: BM25 コードをコメントアウトで残存（設計当初は削除予定だったが変更）

**理由**: Phase 3-3 でハイブリッド検索を実装する際に再利用するため、削除より保存が合理的とユーザーが判断。

### 判断2: score = 1.0 - distance / 2.0 で変換

**理由**: nomic-embed-text は単位正規化済みのため、ChromaDB デフォルトの L2 距離とコサイン距離は等価。`1 - distance/2` で [0, 1] に変換できる。

---

## 設計との差異

### 差異内容

- BM25 関連コード（`_bigram`・`BM25Okapi` import・BM25 検索ロジック）を削除する設計だったが、コメントアウトで残存に変更

### 理由

- Phase 3-3 での再利用を見越してユーザー判断で変更

---

## 動作確認

| 確認内容 | 期待結果 | 実結果 | 判定 |
|---|---|---|---|
| ベクトル検索でヒットが返ること | RAG モード ON でチャンクがヒット | ヒットが返った | PASS |
| 言い回しを変えた質問でもヒットが返ること | 「年次有給休暇」→「休みは何日取れますか」でヒット | ヒットが返った | PASS |

---

## Code Review 結果

**Approve**（High: 0 / Medium: 1 / Low: 1）

| ID | 内容 | 対応 |
|---|---|---|
| F-01 | `n_results=top_k` がコレクションのチャンク数を超えた場合のエラーリスク | **Remaining Issues（RI-05）**: 教材規模では発生しにくい。Phase 3-3 着手時に対応検討 |
| F-02 | `chroma.py` 冒頭 docstring に Phase 3-2 の記載がない | **Remaining Issues（RI-06）**: 軽微。Phase 3-3 着手時に合わせて更新 |

---

## 発生した問題と対応

なし

---

## 学んだこと

- ChromaDB の `collection.query(query_embeddings=...)` でベクトル検索が実行できる
- nomic-embed-text は単位正規化済みのため、ChromaDB デフォルトの L2 距離とコサイン距離は等価になる
- `score = 1 - distance/2` で [0, 1] の類似度スコアに変換できる
- キーワード検索（BM25）では「年次有給休暇」に「休みは何日取れますか」がヒットしないが、ベクトル検索では意味的に近いためヒットすることを実際に確認できた

---

## 課題

### Remaining Issues

- RI-05: `n_results=top_k` がチャンク数を超えた場合のエラーリスク（Phase 3-3 または別 Issue）
- RI-06: `chroma.py` 冒頭 docstring に Phase 3-2 の記載なし（Future）
- RI-01: `chroma.py:82` の `any(c.embedding ...)` の書き方（Future）
- RI-02: `main.py` の `except NotImplementedError` 節の削除（別 Issue）

### GitHub Issues

- #4（本 Issue）: 本 bolt で完了

---

## 次の bolt への引き継ぎ

- Issue #5 Phase 3-3「ハイブリッド検索を実装する」へ進む
- BM25 コードは `ChromaVectorDB.search` 内にコメントアウトで残存しており、Phase 3-3 で再利用できる
- RI-05（`n_results` 上限制御）は Phase 3-3 着手時に合わせて対応を検討する

---

## 関連資料

**Requirements**
- `docs/design/phase3-2-requirements.md`

**Bolt Design**
- `docs/design/phase3-2-bolt-0.md`

---

## 関連コミット

（Commit 後に記入）

---

## 関連 PR

（PR 作成後に記入）
