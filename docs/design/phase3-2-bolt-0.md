# Phase 3-2 bolt-0 設計

## Design Summary

| 項目 | 内容 |
|---|---|
| Phase | Phase 3-2 |
| Bolt | bolt-0 |
| Issue | #4 |
| 目的 | `ChromaVectorDB.search` を BM25 キーワード検索からベクトル検索（コサイン類似度 / k-NN）に切り替え、意味的に近いチャンクを取得できるようにする |
| 作るもの | `ChromaVectorDB.search` のベクトル検索実装 / `SEARCH_TOP_K` の設定化 |
| 作らないもの | BM25 とのハイブリッド検索、`VectorDB.search` インターフェース変更、フロント変更 |
| 完了条件 | ベクトル検索でヒットが返り、言い回しを変えた質問でも意味的に近いチャンクが取れること |
| 次Bolt | なし（Issue #4 完了） |

---

## Requirements Summary

### 対応対象

- R-01: コサイン類似度（または k-NN）でチャンクを検索できること
- R-02: 言い回しを変えた質問でも、意味的に近いチャンクがヒットすること
- R-03: 検索系パラメータ（top_k 等）が `.env` から設定できること
- R-04: embedding が未登録のチャンクが混在していても、エラーにならず空リストを返すこと

### 対応対象外

- O-01: BM25 とベクトル検索のハイブリッド化（Phase 3-3 で対応）
- O-02: rerank 実装（Phase 6 で対応）
- O-03: フロントエンド UI の変更
- O-04: `VectorDB.search` のインターフェース変更

---

## bolt分割判定

### 判定

- 分割不要
- bolt-0 のみで対応

### 理由

- 変更対象は `backend/vector_db/chroma.py` の `search` メソッド・`backend/config/settings.py`・`.env.example` の 3 ファイルに絞られる
- 責務は「ベクトル検索への差し替え」1 つのみで、BM25 との共存設計は Phase 3-3 に持ち越す
- 差分は目安 50〜80 行以内であり、分割してもメリットがない

---

## データフロー

```
query（文字列）
↓
get_embed_model().embed([query]) → query_embedding: list[float]
↓
collection.query(query_embeddings=[query_embedding], n_results=top_k)
↓
ChromaDB（コサイン類似度で近傍チャンクを返す）
↓
list[SearchResult]
```

embedding 生成失敗時のフォールバックフロー:

```
get_embed_model().embed([query]) → 例外発生
↓
logger.warning でエラーログ出力
↓
空リスト [] を返す
```

---

## 影響範囲

### 対象

- `backend/vector_db/chroma.py` — `ChromaVectorDB.search` をベクトル検索に差し替え・BM25 関連コードはコメントアウトで残存・`get_embed_model` import 追加
- `backend/config/settings.py` — `search_top_k: int` フィールド追加
- `.env.example` — `SEARCH_TOP_K=5` 追加

### 影響なし

- `backend/rag.py` — `build_context` 側は変更なし（`vdb.search` を呼ぶだけ）
- `backend/vector_db/vectorDB.py` — `VectorDB.search` インターフェース変更なし
- `backend/llm/` — 読み取り専用（embed インターフェース確認のみ）
- `backend/main.py` — 変更なし
- `frontend/` — 変更なし
- DB スキーマ — 変更なし

---

## bolt-0: ベクトル検索への切り替え

### 目的

- `ChromaVectorDB.search` を ChromaDB の `collection.query(query_embeddings=...)` を使ったベクトル検索に差し替える
- クエリの embedding 生成失敗時・コレクション未作成時に安全に空リストを返す

---

### 作るもの

- `backend/vector_db/chroma.py`
  - `ChromaVectorDB.search` のベクトル検索実装（BM25 から差し替え）
  - クエリ embedding 生成・失敗時フォールバック
  - embedding 未登録コレクションへの空リスト返却
- `backend/config/settings.py`
  - `search_top_k: int` フィールドの追加（デフォルト: 5）
- `.env.example`
  - `SEARCH_TOP_K=5` のコメント付き追加

---

### 作らないもの

- BM25 との組み合わせ（Phase 3-3 で対応）
- `VectorDB.search` シグネチャの変更
- フロントエンド UI の変更
- rerank（Phase 6 で対応）

---

### 対象ファイル・修正箇所

| ファイル | 修正対象 | 変更内容 | 理由 |
|---|---|---|---|
| `backend/vector_db/chroma.py` | `ChromaVectorDB.search` | `search` をベクトル検索に差し替え。BM25 検索コードはコメントアウトで残存（Phase 3-3 再利用予定） | R-01〜R-04 を満たすため |
| `backend/vector_db/chroma.py` | import | `from backend.llm import get_embed_model` を追加 | クエリ embedding 生成に必要 |
| `backend/config/settings.py` | `Settings` dataclass / `load_settings` | `search_top_k: int` フィールドと `os.getenv("SEARCH_TOP_K", "5")` を追加 | R-03 を満たすため |
| `.env.example` | 検索設定セクション | `SEARCH_TOP_K=5` をコメント付きで追加 | R-03 を満たすため |

---

### 実装方針

#### 方針

- `search` 冒頭で `get_embed_model().embed([query])` を呼び、クエリの embedding を生成する
- embedding 生成が例外を発生させた場合は `logger.warning` でログを出し、空リストを返す
- コレクションが存在しない場合は既存と同様に空リストを返す（`try/except` でガード）
- `collection.query(query_embeddings=[embedding], n_results=top_k)` でベクトル検索を実行する
- `top_k` は引数のデフォルト値を `settings.search_top_k` に変更する
- BM25 検索コードはコメントアウトで残存する（`_bigram` 関数・`BM25Okapi` import・BM25 検索ロジック）。Phase 3-3 のハイブリッド検索実装時に再利用する

#### 採用理由

| 判断 | 理由 |
|---|---|
| BM25 を削除してベクトル検索のみにする | Phase 3-3 でハイブリッド化するため、今は差し替えで十分。BM25 を残すと Phase 3-3 の実装範囲が曖昧になる |
| クエリ embedding 生成失敗時に空リストを返す | 検索エラーを呼び出し元（`build_context`）に伝搬させず、「ヒットなし」として安全に処理できる。教材として安全側の設計を優先 |
| `search_top_k` を `settings` 経由で取得する | `.env` から切り替えられる形にすることで R-03 を満たしつつ、引数 `top_k` のシグネチャを維持できる |

---

### テスト観点

| ID | 内容 |
|---|---|
| T-01 | PDF をインデックス後、同じ内容の質問でベクトル検索のヒットが返ること（ログで確認）（AC-01） |
| T-02 | 言い回しを変えた質問（例: "費用" vs "コスト"）でもヒットが返ること（AC-02） |
| T-03 | `.env` の `SEARCH_TOP_K` を変更して backend を再起動後、ヒット件数が変わること（AC-03） |
| T-04 | embedding が存在しないコレクションに対して検索しても空リストが返り、エラーにならないこと（R-04） |

---

### 設計判断

| 項目 | 判断 | 理由 | 代替案 |
|---|---|---|---|
| BM25 の扱い | コメントアウトで残存 | Phase 3-3 のハイブリッド検索で再利用するため削除より保存が合理的 | 削除してベクトル検索のみにする |
| クエリ embedding 生成失敗時の挙動 | 空リストを返す | 検索エラーを上位に伝搬させず「ヒットなし」として安全に処理できる | 例外をそのまま raise して呼び出し元でハンドリングする |
| `rank_bm25` import / `_bigram` 関数 | 残存（コメントアウトなし） | Phase 3-3 での再利用を見越してそのまま残す | 削除する |

---

### 完了条件

#### Functional

- ベクトル検索でヒットが返ること（AC-01）
- 言い回しを変えた質問でもヒットが返ること（AC-02）
- `SEARCH_TOP_K` の変更がヒット件数に反映されること（AC-03）

#### Verification

- PDF をアップロード → ステータスが `ready` になること
- RAG モード ON で質問 → ヒットが返ること
- 言い回しを変えた質問（例: "費用" vs "コスト"）でもヒットが返ること
- `SEARCH_TOP_K=3` に変更して backend 再起動 → ヒット件数が 3 件以下になること
- ERROR ログが出ていないこと

---

### 懸念事項

| 項目 | 内容 | 対応方針 |
|---|---|---|
| Phase 2 以前のコレクションとの次元数競合 | Phase 2 以前に取り込んだコレクションは Chroma のデフォルト embedding（384次元）が保存されており、768次元の `nomic-embed-text` とは共存できない | 動作確認前に既存コレクションを削除して再取り込みする（Phase 3-1 summary より） |
| embedding が `None` のチャンクが混在する場合 | Phase 3-1 のフォールバックにより `embedding=None` のチャンクが存在しうる。このコレクションに対してベクトル検索をかけた場合の ChromaDB の挙動が不明 | コレクション取得後、embedding の有無を確認して空リストを返す設計とする |

---

### Remaining Issues

| ID | 内容 | 対応予定 | 再検討条件 |
|---|---|---|---|
| RI-01 | `chroma.py:81` の `any(c.embedding ...)` の書き方（Phase 2-1 レビュー指摘 L-1/L-2） | Future | 静的解析導入時 |
| RI-02 | `main.py` の `except NotImplementedError` 節の削除（Phase 2-1 からの持ち越し） | 別 Issue | - |
| RI-03 | `OllamaEmbedModel.embed` のバッチ最適化 | Future | チャンク数増加や速度が問題になったとき |
| RI-04 | Phase 2 以前のコレクション次元数競合の注意事項整備 | Future | - |
| RI-05 | `n_results=top_k` がコレクションのチャンク数を超えた場合のエラーリスク（Code Review F-01） | Phase 3-3 または別 Issue | 教材規模では発生しにくいが、`min(top_k, col.count())` で対処可能 |
| RI-06 | `chroma.py` 冒頭 docstring に Phase 3-2 の記載がない（Code Review F-02） | Future | 軽微。Phase 3-3 着手時に合わせて更新 |

---

### 確認事項・決定事項

| 項目 | 内容 |
|---|---|
| 確認事項 | なし |
| 決定事項 | BM25 検索コードはコメントアウトで残存し、`search` メソッドをベクトル検索に差し替える。`SEARCH_TOP_K` を `.env` で設定可能にする |
| 理由 | Phase 3-3 で BM25 を再利用するため削除より保存が合理的。実装中にユーザー判断で変更 |
| 対応方針 | bolt-0 で実装を完了する |

---

### ドキュメント更新

| ドキュメント | 更新内容 |
|---|---|
| `.env.example` | `SEARCH_TOP_K=5` を追加 |
| `docs/taskLog/phase3-2-bolt-0.md` | bolt 完了時に作成 |

---

### 次の bolt への引き継ぎ

なし（Issue #4 完了）

---

## References

### Requirements

- [docs/design/phase3-2-requirements.md](phase3-2-requirements.md)

### Related Issues

- GitHub Issue #4: Phase 3-2: ベクトル検索を実装する
