# WorkLog: Phase 3-2 bolt-0

## サマリー

| 項目 | 内容 |
|---|---|
| 目的 | `ChromaVectorDB.search` をベクトル検索に切り替える |
| 実施内容 | `ChromaVectorDB.search` をベクトル検索に差し替え。BM25 コードはコメントアウトで残存。`SEARCH_TOP_K` を `.env` で設定可能にした |
| 変更ファイル | 3 ファイル（`chroma.py` / `settings.py` / `.env.example`） |
| 動作確認 | PASS |
| AIレビュー | Approve |
| 課題 | RI-05: n_results 上限制御未対応 / RI-06: docstring 未更新 |
| 次の対応 | Phase 3-3: ハイブリッド検索 |

---

## 基本情報

### 実施日

2026-06-27

### 対応 Issue

#4

### bolt

bolt-0

### ブランチ

feature/4-phase3-2-vector-search

---

## 関連資料

**Requirements**
- `docs/design/phase3-2-requirements.md`

**Bolt Design**
- `docs/design/phase3-2-bolt-0.md`

**Code Review**（完了後に記入）
- （未作成）

**Error Investigation**（発生時のみ）
- （なし）

---

## TODO・メモ

- [x] `ChromaVectorDB.search` をベクトル検索に差し替え
- [x] `settings.py` に `search_top_k` を追加
- [x] `.env.example` に `SEARCH_TOP_K=5` を追加
- [ ] Phase 2 以前のコレクションを削除して再取り込み（次元数競合対策）
- [x] 動作確認: ベクトル検索でヒットが返ること
- [x] 動作確認: 言い回しを変えた質問でもヒットが返ること

---

## 1. 作業目的

### 今回の目的

`ChromaVectorDB.search` を BM25 キーワード検索からベクトル検索（コサイン類似度 / k-NN）に切り替え、意味的に近いチャンクを取得できるようにする。

### 完了条件

- ベクトル検索だけでもヒットが返る（AC-01）
- 言い回しを変えた質問でも、意味的に近いチャンクが取れる（AC-02）
- 検索系のパラメータが `.env` から切り替えられる（AC-03）

---

## 2. Requirements 対応

### 対応項目

- R-01: コサイン類似度（または k-NN）でチャンクを検索できること
- R-02: 言い回しを変えた質問でも、意味的に近いチャンクがヒットすること
- R-03: 検索系パラメータ（top_k 等）が `.env` から設定できること
- R-04: embedding が未登録のチャンクが混在していても、エラーにならず空リストを返すこと

### 完了判定

- AC-01: ベクトル検索でヒットが返る → **保留**
- AC-02: 言い回しを変えた質問でもヒットが返る → **保留**
- AC-03: `.env` からパラメータが切り替えられる → **保留**

---

## 3. 実装前調査

### 確認したファイル

```
backend/vector_db/chroma.py
backend/vector_db/vectorDB.py
backend/config/settings.py
backend/rag.py
backend/llm/embedModel.py
backend/llm/ollama.py
.env.example
```

### 調査結果

- `ChromaVectorDB.search` は現状 BM25 キーワード検索のみ実装されている（Phase 2-2 時点）
- `VectorDB.search` のシグネチャ（`collection_id`, `query`, `top_k=5`）は変更しない
- `get_embed_model().embed(texts: list[str])` でクエリの embedding を生成できる
- ChromaDB の `collection.query(query_embeddings=..., n_results=top_k)` でベクトル検索が実行できる
- embedding 次元数は 768（nomic-embed-text）
- Phase 2 以前に取り込んだコレクションは 384 次元のため、再取り込みが必要

### 疑問点

- embedding が `None` のチャンクが混在するコレクションに対してベクトル検索をかけた場合の ChromaDB の挙動 → 実装時に確認する

---

## 4. 実装ログ

### 作業1: `settings.py` に `search_top_k` を追加

**内容**
`Settings` dataclass に `search_top_k: int` フィールドを追加。`load_settings` で `os.getenv("SEARCH_TOP_K", "5")` から読み込む。

**変更ファイル**
`backend/config/settings.py`

**理由**
R-03（検索パラメータの `.env` 設定化）を満たすため。

---

### 作業2: `.env.example` に `SEARCH_TOP_K=5` を追加

**内容**
`SEARCH_TOP_K=5` を検索パラメータセクションとしてコメント付きで追加。

**変更ファイル**
`.env.example`

**理由**
学習者が `.env` で調整できることを示すため。

---

### 作業3: `ChromaVectorDB.search` をベクトル検索に差し替え

**内容**
- `from backend.llm import get_embed_model` を追加
- `search` メソッドを `collection.query(query_embeddings=..., n_results=top_k)` を使ったベクトル検索に差し替え
- BM25 検索コードはコメントアウトで残存（Phase 3-3 再利用予定）
- クエリ embedding 生成失敗時は `logger.warning` + 空リスト返却
- score は `1.0 - distance / 2.0` で [0, 1] に変換（nomic-embed-text は単位正規化済みのため L2 ≒ cosine）

**変更ファイル**
`backend/vector_db/chroma.py`

**理由**
R-01（ベクトル検索）・R-04（失敗時フォールバック）を満たすため。BM25 はコメントアウトで残し Phase 3-3 に備える。

---

## 5. Diff Review

（実装後に記入）

---

## 6. エラー対応ログ

（発生時に記入）

---

## 7. Claude Code 活用ログ

### 判断1: BM25 の扱い（削除 or 残す）

**質問内容**

Phase 3-2 で BM25 を削除してベクトル検索のみにするか、残してフォールバックにするか

**回答要約**

Phase 3-3 でハイブリッド化するため、今は切り替えで十分。BM25 を残すと Phase 3-3 の実装範囲が曖昧になる

**採用判断**

変更（BM25 コードはコメントアウトで残存・ベクトル検索のみ有効）

**判断理由**

Phase 3-3 で BM25 を再利用するため削除より保存が合理的とユーザーが判断

---

## 8. 動作確認

### 確認1: ベクトル検索でヒットが返ること

| 項目 | 内容 |
|---|---|
| 実施内容 | 就業規則 PDF を取り込み後、RAG モード ON でチャット |
| 期待結果 | ベクトル検索でチャンクがヒットして回答が返ること |
| 実結果 | ヒットが返った |
| 判定 | OK |

---

### 確認2: 言い回しを変えた質問でもヒットが返ること

| 項目 | 内容 |
|---|---|
| 実施内容 | 就業規則の表現と異なる言い回し（例: 「年次有給休暇」→「休みは何日取れますか」）で質問 |
| 期待結果 | キーワードが一致しなくても意味的に近いチャンクがヒットすること |
| 実結果 | ヒットが返った |
| 判定 | OK |

---

## 9. 作業振り返り

### 完了したこと

- `ChromaVectorDB.search` をベクトル検索（`collection.query(query_embeddings=...)`）に差し替え
- BM25 コードをコメントアウトで残存（Phase 3-3 再利用予定）
- `SEARCH_TOP_K` を `.env` から設定可能にした
- 就業規則 PDF で動作確認 PASS（ヒット確認・言い回し変更でもヒット確認）

### 学んだこと

- ChromaDB の `collection.query(query_embeddings=...)` でベクトル検索が実行できる
- nomic-embed-text は単位正規化済みのため、ChromaDB デフォルトの L2 距離とコサイン距離は等価
- `score = 1 - distance/2` で [0, 1] の類似度スコアに変換できる
- キーワード検索（BM25）では「年次有給休暇」に「休みは何日取れますか」がヒットしないが、ベクトル検索ではヒットすることを確認

### 判断理由として残したいこと

- BM25 コードは削除せずコメントアウトで残存。Phase 3-3 のハイブリッド検索で再利用するため（実装中にユーザー判断で変更）

### 残課題

| ID | 内容 | 対応予定 |
|---|---|---|
| RI-05 | `n_results=top_k` がチャンク数を超えた場合のエラーリスク | Phase 3-3 または別 Issue |
| RI-06 | `chroma.py` 冒頭 docstring に Phase 3-2 の記載なし | Future |
| RI-01 | `chroma.py:82` の `any(c.embedding ...)` の書き方 | Future |
| RI-02 | `main.py` の `except NotImplementedError` 節の削除 | 別 Issue |

### 次回作業

Phase 3-3: ハイブリッド検索（BM25 + ベクトル検索 RRF）の実装

---

## 関連ドキュメント

- Requirements: `docs/design/phase3-2-requirements.md`
- Bolt Design: `docs/design/phase3-2-bolt-0.md`
- TaskLog（完了後）: `docs/taskLog/phase3-2-bolt-0.md`
