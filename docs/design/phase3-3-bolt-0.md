# Phase 3-3 bolt-0 設計

## Design Summary

| 項目 | 内容 |
|---|---|
| Phase | Phase 3-3 |
| Bolt | bolt-0 |
| Issue | #5 |
| 目的 | `ChromaVectorDB.search` に BM25 + ベクトル検索 + RRF 統合を実装し、両者の弱点を補完するハイブリッド検索を実現する |
| 作るもの | `ChromaVectorDB.search` の RRF 統合実装 / `rrf_k` の設定化 / RI-05 の `n_results` 上限制御 |
| 作らないもの | rerank / 親子チャンク / フロント UI 変更 / BM25・ベクトルの重み係数調整 |
| 完了条件 | BM25 + ベクトル検索が両方実行され RRF で統合された結果が返ること |
| 次Bolt | なし（Issue #5 完了） |

---

## Requirements Summary

### 対応対象

- R-01: BM25 検索とベクトル検索の両方を実行し、それぞれの結果リストを取得できること
- R-02: RRF でスコアを統合し、1つの `list[SearchResult]` として返せること
- R-03: BM25 のみヒット・ベクトルのみヒット・両方ヒット・どちらもヒットなし の全ケースで正しく動くこと
- R-04: パラメータ（`rrf_k`）が `.env` から設定できること
- R-05: `n_results` がコレクションのチャンク数を超えないように制御すること（RI-05 対応）

### 対応対象外

- O-01: rerank（Phase 6 で対応）
- O-02: フロントエンド UI の変更
- O-03: `VectorDB.search` のインターフェース変更
- O-04: 親子チャンク（Phase 5 で対応）
- O-05: BM25・ベクトルの重み係数調整（RRF に統一）

---

## bolt分割判定

### 判定

分割不要。bolt-0 のみで対応。

### 理由

- 変更対象は `chroma.py` / `settings.py` / `.env.example` の 3 ファイル
- 責務は「BM25 + ベクトル検索 + RRF 統合」1つのみ
- 差分は目安 50〜80 行以内で収まる見込み

---

## データフロー

```
query（文字列）
    │
    ├─── BM25 検索 ────────────────────────────────────────────
    │    col.get() → 全チャンク取得
    │    BM25Okapi(tokenized_corpus).get_scores(_bigram(query))
    │    スコア > 0 の上位 top_k 件 → bm25_hits: list[(chunk_index, score)]
    │
    └─── ベクトル検索 ──────────────────────────────────────────
         get_embed_model().embed([query]) → query_embedding
         col.query(query_embeddings=[query_embedding],
                   n_results=min(top_k, col.count()))
         → vector_hits: list[(chunk_id, score)]

    ↓
RRF 統合
    各チャンクの RRF スコア = Σ ( 1 / (rrf_k + rank_i) )
    ※ 両リストに登場するチャンクはスコアが加算される
    ↓
RRF スコアで降順ソート → 上位 top_k 件
    ↓
list[SearchResult]（score = RRF スコア）
```

---

## 影響範囲

### 対象

- `backend/vector_db/chroma.py` — `ChromaVectorDB.search` を BM25 + ベクトル検索 + RRF に拡張。BM25 コメントアウトを解除
- `backend/config/settings.py` — `rrf_k: int` フィールド追加
- `.env.example` — `RRF_K=60` 追加

### 影響なし

- `backend/rag.py` — `vdb.search` を呼ぶだけ。変更なし
- `backend/vector_db/vectorDB.py` — `VectorDB.search` インターフェース変更なし
- `backend/llm/` — 読み取り専用
- `backend/main.py` — 変更なし
- `frontend/` — 変更なし
- DB スキーマ — 変更なし

---

## bolt-0: ハイブリッド検索（BM25 + ベクトル + RRF）

### 目的

- `ChromaVectorDB.search` で BM25 とベクトル検索を両方実行し、RRF でスコアを統合する
- Phase 3-2 でコメントアウトした BM25 コードを解除して再利用する
- RI-05（`n_results` 上限制御）を `min(top_k, col.count())` で対応する

---

### 作るもの

- `backend/vector_db/chroma.py`
  - `ChromaVectorDB.search` に BM25 + ベクトル検索 + RRF 統合ロジックを実装
  - Phase 3-2 の BM25 コメントアウトを解除・再利用
  - `n_results=min(top_k, col.count())` で RI-05 対応
- `backend/config/settings.py`
  - `rrf_k: int` フィールド追加（デフォルト: 60）
- `.env.example`
  - `RRF_K=60` 追加

---

### 作らないもの

- BM25・ベクトル検索の重み係数による調整（シンプルな RRF に統一）
- `bm25_top_k` / `vector_top_k` の個別設定（`search_top_k` を共用する）
- rerank（Phase 6 で対応）
- `VectorDB.search` シグネチャの変更
- フロントエンド UI の変更

---

### 対象ファイル・修正箇所

| ファイル | 修正対象 | 変更内容 | 理由 |
|---|---|---|---|
| `backend/vector_db/chroma.py` | `ChromaVectorDB.search` | BM25 コメントアウトを解除し、ベクトル検索と RRF 統合を追加。`n_results=min(top_k, col.count())` で上限制御 | R-01〜R-05 を満たすため |
| `backend/config/settings.py` | `Settings` dataclass / `load_settings` | `rrf_k: int` フィールドと `os.getenv("RRF_K", "60")` を追加 | R-04 を満たすため |
| `.env.example` | 検索パラメータセクション | `RRF_K=60` をコメント付きで追加 | R-04 を満たすため |

---

### 実装方針

#### 方針

1. `col.get()` で全チャンクを取得し、BM25 スコアを計算する（既存の `_bigram` 関数を再利用）
2. スコア > 0 の上位 `top_k` 件を BM25 ヒットとする
3. クエリ embedding を生成し、`col.query(n_results=min(top_k, col.count()))` でベクトル検索を実行する
4. 両リストを RRF でスコア統合する: `score = Σ 1 / (rrf_k + rank_i)`（rank は 1 始まり）
5. RRF スコアで降順ソートして上位 `top_k` 件の `SearchResult` を返す
6. BM25 のみヒット・ベクトルのみヒットは `score = 1 / (rrf_k + rank)` になる
7. embedding 生成失敗時はベクトル検索をスキップし、BM25 のみの結果を RRF スコアに変換して返す

#### 採用理由

| 判断 | 理由 |
|---|---|
| `bm25_top_k` / `vector_top_k` を `search_top_k` で共用 | 設定項目を増やさず最小変更。効果の差は `rrf_k` と `top_k` で観察できる |
| embedding 生成失敗時は BM25 のみ返す | ベクトル検索が使えない状況でも検索が機能する。教材として安全側の設計を優先 |
| `rrf_k` のデフォルト 60 | RRF の標準値。調整は `.env` から行える |
| RRF スコアを `SearchResult.score` に格納 | インターフェース変更なしで統合スコアを返せる |

---

### 既存コードの扱い

| ファイル | 対象 | 扱い | 理由 |
|---|---|---|---|
| `backend/vector_db/chroma.py` | Phase 2-2 BM25 コメントアウト（`# ── Phase 2-2: BM25 〜 ──` ブロック） | **コメントアウトを解除して有効化** | Phase 3-3 での再利用を前提に Phase 3-2 でコメントアウト保存していた |
| `backend/vector_db/chroma.py` | Phase 3-2 ベクトル検索コード | **残存・RRF 統合に組み込む** | ベクトル検索は引き続き使用する |
| `backend/vector_db/chroma.py` | `# ── Phase 2-2 BM25 ──` のセクションコメント | **削除**（コード解除に伴い不要になる） | コメントアウトの目印として付けたものであり、解除後は不要 |

---

### テスト観点

| ID | 内容 |
|---|---|
| T-01 | PDF をインデックス後、キーワードを含む質問で BM25 + ベクトル両方がヒットして上位に来ること |
| T-02 | 言い回しを変えた質問でベクトル検索がヒットすること（Phase 3-2 同様の確認） |
| T-03 | RRF スコアが `SearchResult.score` に格納されていること（ログで確認） |
| T-04 | `.env` の `RRF_K` を変更して検索結果のスコアが変わること |
| T-05 | チャンク数が `top_k` より少ないコレクションでエラーにならないこと（RI-05） |

---

### 設計判断

| 項目 | 判断 | 理由 | 代替案 |
|---|---|---|---|
| BM25 候補数と ベクトル検索候補数 | `search_top_k` で共用 | 設定項目を増やさず最小変更。学習者が混乱しにくい | `bm25_top_k` / `vector_top_k` を個別設定する |
| embedding 生成失敗時の挙動 | BM25 のみの結果を返す | 完全に空リストよりも BM25 のヒットがある方が学習者にとって有用 | 空リストを返す（Phase 3-2 と同じ） |
| `SearchResult.score` の値 | RRF スコア | インターフェース変更なし。値の意味はコメントで補足 | BM25・ベクトルの正規化スコアを別フィールドで返す |

---

### 完了条件

#### Functional

- BM25 とベクトル検索が両方実行され RRF で統合された結果が返ること（AC-01）
- 言い回しを変えた質問でもヒットが返ること（AC-02）
- 両方でヒットしたチャンクが上位に来ること（AC-03、ログ確認）
- `RRF_K` の変更がスコアに反映されること（AC-04）

#### Verification

- PDF をアップロード → ステータスが `ready` になること
- RAG モード ON でキーワードを含む質問 → ヒットが返ること
- 言い回しを変えた質問 → ヒットが返ること
- チャンク数 < `top_k` のコレクションで検索 → エラーにならないこと
- ERROR ログが出ていないこと

---

### 懸念事項

| 項目 | 内容 | 対応方針 |
|---|---|---|
| BM25 の速度 | `col.get()` で全チャンク取得するため、チャンク数が増えると遅くなる | 教材規模では問題なし。Phase 6 以降で改善を検討 |
| embedding が `None` のチャンクが混在する場合 | ベクトル検索が空リストを返す可能性がある | BM25 のみの結果を RRF スコアに変換して返す |

---

### Remaining Issues

| ID | 内容 | 対応予定 | 再検討条件 |
|---|---|---|---|
| RI-01 | `chroma.py:82` の `any(c.embedding ...)` の書き方 | Future（静的解析導入時） | - |
| RI-02 | `main.py` の `except NotImplementedError` 節の削除 | 別 Issue | - |
| RI-03 | `OllamaEmbedModel.embed` のバッチ最適化 | Future | チャンク数増加や速度が問題になったとき |

---

### 確認事項・決定事項

| 項目 | 内容 |
|---|---|
| 確認事項 | なし |
| 決定事項 | BM25 + ベクトル検索 + RRF で統合する。`bm25_top_k` / `vector_top_k` は `search_top_k` で共用。`rrf_k` のみ新規追加 |
| 理由 | 設定項目を最小にして学習者が混乱しにくい構成にする |
| 対応方針 | bolt-0 で実装を完了する |

---

### ドキュメント更新

| ドキュメント | 更新内容 |
|---|---|
| `.env.example` | `RRF_K=60` を追加 |
| `docs/taskLog/phase3-3-bolt-0.md` | bolt 完了時に作成 |

---

### 次の bolt への引き継ぎ

なし（Issue #5 完了）

---

## References

### Requirements

- [docs/design/phase3-3-requirements.md](phase3-3-requirements.md)

### Related Issues

- GitHub Issue #5: Phase 3-3: ハイブリッド検索を実装する
