# Phase 3-2 Requirements

## Requirements Summary

| 項目 | 内容 |
|---|---|
| Phase | Phase 3-2 |
| Issue | #4 |
| タイトル | Phase 3-2: ベクトル検索を実装する |
| 目的 | キーワード一致では拾えない、意味的に近い質問にもヒットを返せるようにする |
| 対象範囲 | `ChromaVectorDB.search` のベクトル検索対応 / 検索パラメータの `.env` 設定化 |
| 対象外 | BM25 との組み合わせ（Phase 3-3）/ rerank（Phase 6）/ フロント UI の変更 |
| 完了条件数 | 3 |
| 次工程 | Bolt Design |

---

## Phase 情報

| 項目 | 内容 |
|---|---|
| Phase | 3-2 |
| タイトル | ベクトル検索を実装する |
| Issue | #4 |

---

## 背景

Phase 3-1 で各チャンクに embedding（768次元 / nomic-embed-text）が付与され、ChromaDB に保存されるようになった。

現状の `ChromaVectorDB.search` は BM25 キーワード検索のみを実装しており、同じ意味の言い回しを変えた質問（例: "費用はいくら" vs "コストはどのくらい"）にヒットしない。embedding を活用したベクトル検索（コサイン類似度 / k-NN）に切り替えることで、意味的に近いチャンクを取得できるようにする。

---

## 目的

- ベクトル検索を使って意味的に近いチャンクを取得できるようにする
- キーワード検索との違いを観察できる状態を作る（学習ポイント）
- 検索パラメータを `.env` で調整可能にして、実験しやすい環境を整える

---

## 要件

| ID | 要件 |
|---|---|
| R-01 | コサイン類似度（または k-NN）でチャンクを検索できること |
| R-02 | 言い回しを変えた質問でも、意味的に近いチャンクがヒットすること |
| R-03 | 検索系パラメータ（top_k 等）が `.env` から設定できること |
| R-04 | embedding が未登録のチャンクが混在していても、エラーにならず空リストを返すこと |

---

## 対象範囲

| ID | 内容 |
|---|---|
| S-01 | `backend/vector_db/chroma.py` の `ChromaVectorDB.search` をベクトル検索に切り替える |
| S-02 | 検索パラメータ（top_k など）を `backend/config/settings.py` と `.env` に追加する |

---

## 対象外

| ID | 内容 |
|---|---|
| O-01 | BM25 とベクトル検索のハイブリッド化（Phase 3-3 で対応） |
| O-02 | rerank 実装（Phase 6 で対応） |
| O-03 | フロントエンド UI の変更 |
| O-04 | `VectorDB.search` のインターフェース変更 |

---

## テスト観点

| ID | 内容 |
|---|---|
| T-01 | PDF をインデックス後、同じ内容の質問でベクトル検索のヒットが返ること（ログで確認） |
| T-02 | 言い回しを変えた質問（例: "費用" vs "コスト"）でもヒットが返ること |
| T-03 | embedding が存在しないコレクションに対して検索しても空リストが返ること |
| T-04 | `.env` の `SEARCH_TOP_K` を変更してヒット件数が変わること |

---

## 完了条件

### Acceptance Criteria

| ID | 条件 |
|---|---|
| AC-01 | ベクトル検索だけでもヒットが返る |
| AC-02 | 言い回しを変えた質問でも、キーワード検索ではヒットしなかったチャンクが取れる |
| AC-03 | 検索系のパラメータが `.env` から切り替えられる |

---

## 懸念事項

| ID | 内容 | 対応方針 |
|---|---|---|
| C-01 | embedding が `None` のチャンクが混在する可能性（Phase 3-1 フォールバックにより存在しうる） | embedding が存在しないコレクションは空リストを返す設計とする |
| C-02 | Phase 2 以前に取り込んだコレクションは 384次元のため、768次元の embedding と次元数が競合する | 実験前に既存コレクションを削除して再取り込みする（Phase 3-1 summary RI-04 より） |
| C-03 | クエリの embedding 生成が失敗した場合の挙動 | 例外をキャッチして空リストを返す設計とする |

---

## 確認事項・決定事項

| 項目 | 内容 |
|---|---|
| 確認事項 | BM25 検索は Phase 3-2 で削除するか、残すか |
| 決定事項 | `search` メソッドをベクトル検索に差し替える。BM25 コードはコメントアウトで残存し Phase 3-3 で再利用する |
| 理由 | Phase 3-3 でハイブリッド化する際に BM25 コードを再利用するため、削除より保存が合理的（実装中にユーザー判断で変更） |
| 対応方針 | `ChromaVectorDB.search` の実装をベクトル検索に差し替え、BM25 コードはコメントアウトで残す |

---

## Bolt 設計への引き継ぎ

- 変更対象は `backend/vector_db/chroma.py` の `search` メソッド・`backend/config/settings.py`・`.env.example` の 3 ファイル
- ChromaDB の `collection.query(query_embeddings=..., n_results=top_k)` を使う設計になる見込み
- クエリの embedding は `get_embed_model().embed([query])` で生成する
- top_k を `.env` から設定できるようにする（例: `SEARCH_TOP_K`、デフォルト: 5）
- `VectorDB.search` のシグネチャ（`collection_id`, `query`, `top_k=5`）は変更しない（Phase 3-1 summary より）
- embedding なし（`None`）のコレクションへの安全なフォールバックを設計に含める

---

## 関連ドキュメント

- GitHub Issue #4
- `docs/design/phase3-1-requirements.md`
- `docs/phaseSummary/phase3-1-summary.md`
- `reference/ROAD_MAP.md`
