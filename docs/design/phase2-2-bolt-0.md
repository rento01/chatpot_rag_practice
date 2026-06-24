# Phase 2-2 bolt-0 設計

## Design Summary

| 項目 | 内容 |
|---|---|
| Phase | Phase 2-2 |
| Bolt | bolt-0 |
| Issue | #2 |
| 目的 | `ChromaVectorDB.search` をキーワード検索（BM25 + 文字 n-gram）で実装する |
| 作るもの | `ChromaVectorDB.search` の実装、`rank_bm25` 依存追加 |
| 作らないもの | ベクトル検索、形態素解析（janome 等）、`build_context` の変更 |
| 完了条件 | RAG モード ON でヒット・ヒットなし両方が機能すること |
| 次Bolt | なし（Issue #2 完了） |

---

## Requirements Summary

### 対応対象

- R-01: `ChromaVectorDB.search` がキーワード一致で上位チャンクを返す
- R-02: 検索結果を `SearchResult` 型（`document_id`, `text`, `score`, `metadata`）で返す
- R-03: 日本語クエリに対してトークナイズを考慮した検索（文字 n-gram）
- R-04: ヒットゼロ時に `build_context` が `has_hits=False` を返す
- R-05: RAG モード ON で質問したとき、ヒットしたチャンクが LLM に渡る

### 対応対象外

- O-01〜O-06: ベクトル検索・embedding 生成・ハイブリッド検索・rerank・`build_context` フォーマット改善・L-1/L-2 レビュー指摘対応

---

## bolt分割判定

### 判定

- 分割不要
- bolt-0 のみで対応

### 理由

- 変更対象は `ChromaVectorDB.search` の 1 メソッドのみ
- `pyproject.toml` への依存追加を含めても差分は小規模（目安 50 行以内）
- 責務が単一（キーワード検索の実装）
- `build_context` 側はすでに完成しており、`search` を実装するだけで RAG が動く構造になっている

---

## データフロー

```
query（ユーザー入力）
↓
collection.get() で全チャンク取得
↓
文字 n-gram でトークナイズ（query + documents）
↓
BM25Okapi でスコアリング
↓
score > 0 の上位 top_k を SearchResult で返す
↓
build_context がコンテキストに組み立て LLM へ渡す
```

ヒットゼロの場合:

```
search が空リストを返す
↓
build_context が has_hits=False を返す
↓
「資料に記載がありません」が返る（rag.py 既実装）
```

---

## 影響範囲

### 対象

- `backend/vector_db/chroma.py` — `ChromaVectorDB.search` を実装
- `pyproject.toml` — `rank_bm25` を依存に追加

### 影響なし

- `backend/rag.py` — `build_context` は変更なし。`search` が値を返せば自然に動く
- `backend/main.py` — 変更なし
- `frontend/` — 変更なし
- DB スキーマ — 変更なし

---

## bolt-0: キーワード検索実装

### 目的

- `ChromaVectorDB.search` を BM25 + 文字 n-gram で実装し、RAG モードで検索ヒットが返るようにする

---

### 作るもの

- `ChromaVectorDB.search` の実装（`backend/vector_db/chroma.py`）
- `rank_bm25` の依存追加（`pyproject.toml`）

---

### 作らないもの

- ベクトル検索（Phase 3-2 で対応）
- 形態素解析による単語分割（janome 等）— Remaining Issues に記録
- `build_context` の変更
- `main.py` の `except NotImplementedError` 節の削除（Phase 2-1 からの残課題、今回スコープ外）

---

### 対象ファイル・修正箇所

| ファイル | 修正対象 | 変更内容 |
|---|---|---|
| `backend/vector_db/chroma.py` | `ChromaVectorDB.search` | BM25 + 文字 n-gram でキーワード検索を実装（NotImplementedError を置き換え） |
| `pyproject.toml` | `dependencies` | `rank_bm25` を追加 |

### 修正理由

| ファイル | 修正対象 | 変更内容 | 理由 |
|---|---|---|---|
| `backend/vector_db/chroma.py` | `ChromaVectorDB.search` | BM25 キーワード検索を実装 | NotImplementedError を解消し、RAG モードで検索ヒットを返せるようにするため |
| `pyproject.toml` | `dependencies` | `rank_bm25` を追加 | BM25 スコアリングに使用するため |

---

### 実装方針

#### 方針

- `collection.get()` でコレクション内の全チャンクを取得し、メモリ上で BM25 スコアリングを行う
- トークナイザは文字 n-gram（bigram、2 文字ずつスライド）を使う
- `rank_bm25` の `BM25Okapi` にトークナイズ済みコーパスを渡してスコアを算出する
- `score > 0` のものだけを有効ヒットとして扱い、上位 `top_k` 件を `SearchResult` で返す
- コレクションが空、またはチャンクが 0 件の場合は空リストを返す

#### 採用理由

| 判断 | 理由 |
|---|---|
| BM25（rank_bm25）を採用 | Issue の学習ポイント「BM25 の挙動と日本語での効きどころ」に直結するため |
| 文字 n-gram を採用 | 追加ライブラリなしで日本語を扱えるため。Issue の「素朴な実装で一度動かしてから観察する」方針に沿う |
| メモリ上でスコアリング | Chroma の検索 API は BM25 スコアを直接返さないため。学習規模（チャンク数）なら全件取得でも問題ない |

---

### テスト観点

| ID | 内容 |
|---|---|
| T-01 | 取り込み済みコレクションを選択し RAG モード ON で質問したとき、チャンクがヒットして回答の根拠として返ること |
| T-02 | コレクションに存在しないキーワードで質問したとき、「資料に記載がありません」が返ること |
| T-03 | コレクション未作成または空のときに検索しても例外が起きないこと |

---

### 設計判断

| 項目 | 判断 | 理由 |
|---|---|---|
| 検索方式 | BM25（rank_bm25） | Issue の学習ポイント「BM25 の挙動と日本語での効きどころ」に直結。Chroma テキストフィルタでは BM25 スコアが得られない |
| 日本語トークナイザ | 文字 n-gram（bigram） | 追加依存なしで日本語を扱えるため。「素朴な実装で一度動かしてから観察する」という Issue の方針に沿う |
| janome 不採用 | 今回は見送り | 依存を増やさず最小実装を優先する。検索精度改善は Remaining Issues に記録し後続フェーズで判断する |
| score > 0 フィルタ | 有効ヒットのみ返す | BM25 スコアが 0 のものはクエリと無関係なチャンク。ヒットなしパスを正しく機能させるため |

---

### 完了条件

#### Functional

- `ChromaVectorDB.search` が `SearchResult` のリストを返すこと（`NotImplementedError` が解消されていること）
- 取り込み済みコレクションへのクエリでヒットが返ること（AC-01）
- ヒットゼロ時に「資料に記載がありません」が返ること（AC-02）

#### Verification

- RAG モード ON で質問 → ヒットしたチャンクが回答の根拠として表示されることを画面で確認
- コレクションにないキーワードで質問 → 「資料に記載がありません」が返ることを確認
- `docker compose logs -f backend` でエラーが出ていないことを確認

---

### 懸念事項

| 項目 | 内容 | 対応方針 |
|---|---|---|
| 文字 n-gram の精度限界 | bigram は形態素解析より精度が低く、ヒットしないクエリが発生しやすい | 想定内。「観察する」フェーズとして扱い、改善は Remaining Issues に記録 |
| コレクションが大きい場合の全件取得 | `collection.get()` は全チャンクをメモリに展開する | 学習規模（数千チャンク）では問題なし。本番スケールへの対応は対象外 |

---

### Remaining Issues

| ID | 内容 | 対応予定 |
|---|---|---|
| RI-01 | janome 等の形態素解析を用いた日本語トークナイズで検索精度を改善する | Future（検索精度改善時に判断） |
| RI-02 | `main.py` の `except NotImplementedError` 節の削除（Phase 2-1 からの持ち越し） | taskLog 残課題のまま継続 |

---

### 確認事項・決定事項

| 項目 | 内容 |
|---|---|
| 確認事項 | なし（設計判断はすべて決定済み） |
| 決定事項 | BM25（rank_bm25）+ 文字 n-gram（bigram）で実装する |
| 理由 | Issue の学習ポイントに沿いつつ、追加依存を最小化し「まず動かす」方針を優先 |
| 対応方針 | bolt-0 で実装、janome 等の改善は RI-01 として Remaining Issues に記録 |

---

### ドキュメント更新

| ドキュメント | 更新内容 |
|---|---|
| `docs/taskLog/phase2-2-bolt-0.md` | bolt 完了時に作成 |

---

### 次の bolt への引き継ぎ

なし（Issue #2 完了）

---

## References

### Requirements

- [docs/design/phase2-2-requirements.md](phase2-2-requirements.md)

### Related Issues

- GitHub Issue #2: Phase 2-2: キーワード検索を実装する
