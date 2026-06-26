# Phase 3-1 Requirements

## Requirements Summary

| 項目 | 内容 |
|---|---|
| Phase | Phase 3-1 |
| Issue | #3 |
| タイトル | embedding を生成する |
| 目的 | 取り込み時にチャンクごとの embedding を生成し Chroma に保存することで、後段のベクトル検索（Phase 3-2）が動く前提を整える |
| 対象範囲 | `rag.index_document` への embedding 生成の組み込み、取り込み進捗ログの追加 |
| 対象外 | ベクトル検索の実装、ハイブリッド検索、既存チャンクへの embedding 一括付与 |
| 完了条件数 | 2 |
| 次工程 | Bolt Design |

---

## Phase情報

| 項目 | 内容 |
|---|---|
| Phase | 3-1 |
| タイトル | embedding を生成する |
| Issue | #3 |

---

## 背景

Phase 2-1 で PDF 取り込みパイプライン（テキスト抽出 → チャンク分割 → Chroma への保存）が完成した。
ただし現状では `Chunk.embedding = None` のまま upsert しており、Chroma にはテキストのみが保存されている。

Phase 3-2 でベクトル検索（cosine similarity / k-NN）を実装するためには、
取り込み時点でチャンクごとに embedding が生成・保存されている必要がある。

`backend/llm/` には `EmbedModel` インターフェースと `OllamaEmbedModel` の実装がすでに用意されており、
`ChromaVectorDB.upsert` も embedding を受け取る実装になっている。
Phase 3-1 では、これらを `rag.index_document` に繋ぎ込むことが主な作業となる。

---

## 目的

- `rag.index_document` で各チャンクの embedding を生成し、`Chunk.embedding` に付与して Chroma に保存する
- 取り込み中の進捗をバックエンドログで追えるようにする（入力数・処理済み数など）

---

## 要件

| ID | 要件 |
|---|---|
| R-01 | `rag.index_document` が各チャンクの embedding を生成し、`Chunk.embedding` に付与してから `vdb.upsert` を呼ぶこと |
| R-02 | 取り込み完了後、Chroma のコレクション内でチャンクごとに embedding が保存されていること |
| R-03 | 取り込み中の進捗（チャンク数・処理状況）がバックエンドログで確認できること |
| R-04 | embedding 生成に失敗したチャンクが発生した場合に、失敗内容がバックエンドログで確認できること |

---

## 対象範囲

| ID | 内容 |
|---|---|
| S-01 | `backend/rag.py` の `index_document` に `get_embed_model()` を使った embedding 生成を追加する |
| S-02 | 取り込み中の進捗が分かるログ出力を追加する |

---

## 対象外

| ID | 内容 |
|---|---|
| O-01 | ベクトル検索（cosine similarity / k-NN）の実装は Phase 3-2 で扱う |
| O-02 | ハイブリッド検索（BM25 + ベクトルの融合）は Phase 3-3 で扱う |
| O-03 | 既存の取り込み済みチャンク（embedding なし）への一括 embedding 付与は今回スコープ外 |
| O-04 | `OllamaEmbedModel.embed` 自体の変更（バッチ API への切り替え等）は今回スコープ外 |
| O-05 | Bedrock など Ollama 以外のプロバイダの動作確認は今回スコープ外 |

---

## テスト観点

| ID | 内容 |
|---|---|
| T-01 | PDF をアップロードして取り込みが完走し、Chroma のチャンクに embedding が保存されていること |
| T-02 | 取り込み中にバックエンドログで進捗が確認できること |

---

## 完了条件

Issue #3 の完了条件を具体化したものを以下に記載する。

### Acceptance Criteria

| ID | 条件 |
|---|---|
| AC-01 | 取り込み完了後、Chroma 側でチャンクごとに embedding が保存されていること |
| AC-02 | 取り込み中の進捗が backend ログで追えること |

---

## 懸念事項

| ID | 内容 | 対応方針 |
|---|---|---|
| C-01 | `OllamaEmbedModel.embed` は現在 1 件ずつ HTTP リクエストを送る実装であり、チャンク数が多い場合に取り込みが遅くなる | 学習規模では許容範囲として今回はそのまま使う。バッチ最適化は O-04 として対象外 |
| C-02 | embedding モデル（nomic-embed-text 等）には入力長上限があり、長いチャンクでエラーになる可能性がある | 発生した場合の挙動（スキップ / エラー停止）をBolt設計で決定する |
| C-03 | Phase 2-1 レビュー指摘 L-1・L-2（`chroma.py:81` の `any(c.embedding ...)` の書き方）が Phase 3-1 スコープに含まれると Phase 2-2 summary で言及されているが、Issue #3 本文には記載がない | Issue 範囲外のため今回は対象外とし、残課題として記録する（確認事項・決定事項参照） |
| C-04 | Phase 3-1 完了後も既存の取り込み済みチャンクには embedding がないため、Phase 3-2 でベクトル検索を試すには再取り込みが必要になる | ドキュメントを削除して再アップロードすれば embedding が付与される。注意事項として引き継ぐ |

---

## 確認事項・決定事項

| 項目 | 内容 |
|---|---|
| 確認事項 | Phase 2-2 summary では「Phase 2-1 のレビュー指摘 L-1・L-2 は Phase 3-1 の実装時に合わせて修正する」と記載されているが、Issue #3 には明示なし |
| 決定事項 | Issue #3 の範囲外として今回は対象外とする |
| 理由 | Requirements は Issue 記載内容に基づいて作成する方針（`docs/templates/requirements.md`）のため、Issue に記載のない内容を推測で追加しない |
| 対応方針 | 残課題として記録し、後続フェーズまたは個別 Issue で対応する |

---

## Bolt設計への引き継ぎ

- `EmbedModel.embed(texts: list[str]) -> list[list[float]]` がすでに定義済み（`backend/llm/embedModel.py`）
- `OllamaEmbedModel.embed` は 1 件ずつ HTTP リクエストを送る実装（`backend/llm/ollama.py:88-98`）
- `ChromaVectorDB.upsert` は `any(c.embedding ...)` が True の場合のみ `embeddings` を Chroma に渡す実装になっている（`backend/vector_db/chroma.py:81`）
- 変更の主体は `backend/rag.py:70-88` の `index_document` 関数
- C-02（入力長上限超過時の挙動）の決定が Bolt 設計の最初の判断事項
- 進捗ログの粒度（例: N チャンクごと / 開始・完了のみ）も Bolt 設計で決定する

---

## 関連ドキュメント

### Issue

- GitHub Issue #3: Phase 3-1: embedding を生成する

### Related Documents

- Phase 2-2 Requirements: [docs/design/phase2-2-requirements.md](phase2-2-requirements.md)
- Phase 2-2 Summary: [docs/phaseSummary/phase2-2-summary.md](../phaseSummary/phase2-2-summary.md)

### Reference

- ROAD_MAP: [reference/ROAD_MAP.md](../../reference/ROAD_MAP.md)
