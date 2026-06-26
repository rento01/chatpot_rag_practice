# Phase 3-1 bolt-0 設計

## Design Summary

| 項目 | 内容 |
|---|---|
| Phase | Phase 3-1 |
| Bolt | bolt-0 |
| Issue | #3 |
| 目的 | `rag.index_document` に embedding 生成を組み込み、取り込み時にチャンクごとの embedding を Chroma に保存する |
| 作るもの | `index_document` への embedding 生成・進捗ログの追加 |
| 作らないもの | ベクトル検索、EmbedModel 実装の変更、`chroma.py` の変更 |
| 完了条件 | 取り込み後に Chroma の各チャンクに embedding が保存されており、進捗がログで確認できること |
| 次Bolt | なし（Issue #3 完了） |

---

## Requirements Summary

### 対応対象

- R-01: `rag.index_document` が各チャンクの embedding を生成し `Chunk.embedding` に付与して `vdb.upsert` を呼ぶ
- R-02: 取り込み完了後、Chroma のコレクション内でチャンクごとに embedding が保存されている
- R-03: 取り込み中の進捗（チャンク数・処理状況）がバックエンドログで確認できる
- R-04: embedding 生成に失敗した場合、失敗内容がバックエンドログで確認できる

### 対応対象外

- O-01: ベクトル検索（Phase 3-2）
- O-02〜O-03: ハイブリッド検索、既存チャンクへの一括付与
- O-04: `OllamaEmbedModel.embed` 自体の変更（バッチ API 切り替え等）
- O-05: Bedrock 等 Ollama 以外のプロバイダの動作確認

---

## bolt分割判定

### 判定

- 分割不要
- bolt-0 のみで対応

### 理由

- 変更対象は `backend/rag.py` の `index_document` 関数のみ
- `EmbedModel.embed`・`OllamaEmbedModel.embed`・`ChromaVectorDB.upsert`（embedding 受け取り部）はすでに実装済みのため、繋ぎ込む数行の追加で完結する
- 差分は目安 30〜50 行以内、責務は単一（embedding 生成の組み込み）
- 教材として「動く最小構成を一度見せる」ことが目的であり、分割してもメリットがない

---

## データフロー

```
file_data（PDF バイト列）
↓
extract_text → (text, page_count)
↓
split_into_chunks → chunks: list[str]
↓
get_embed_model().embed(chunks) → embeddings: list[list[float]]  ← 今回追加
↓
[Chunk(document_id=document_id, text=c, embedding=e) for c, e in zip(chunks, embeddings)]
↓
vdb.upsert(collection_id, chunk_list)
↓
ChromaDB（テキスト + embedding が保存される）
```

embedding 生成失敗時のフォールバックフロー:

```
get_embed_model().embed(chunks) → 例外発生
↓
logger.warning でエラーログ出力
↓
embedding=None のまま Chunk 化（既存の upsert 動作に戻る）
↓
vdb.upsert（テキストのみ保存）
```

---

## 影響範囲

### 対象

- `backend/rag.py` — `index_document` に embedding 生成とログを追加

### 影響なし

- `backend/llm/embedModel.py` — インターフェース変更なし
- `backend/llm/ollama.py` — `OllamaEmbedModel.embed` 変更なし
- `backend/vector_db/chroma.py` — `upsert` は embedding 受け取り済みのため変更なし
- `backend/main.py` — 変更なし
- `frontend/` — 変更なし
- DB スキーマ — 変更なし

---

## bolt-0: embedding 生成の組み込み

### 目的

- `rag.index_document` に `get_embed_model()` を使った embedding 生成を追加し、各チャンクに `Chunk.embedding` を付与してから Chroma に upsert する
- 取り込み開始・完了の進捗をバックエンドログに出力する

---

### 作るもの

- `backend/rag.py` の `index_document` への embedding 生成呼び出しの追加
- 取り込み進捗ログ（開始時チャンク数・完了）
- embedding 生成失敗時の warning ログとフォールバック（embedding=None で継続）

---

### 作らないもの

- `EmbedModel` インターフェースの変更
- `OllamaEmbedModel.embed` の変更（バッチ API 切り替え等）
- `ChromaVectorDB.upsert` の変更（`chroma.py:81` の L-1/L-2 修正）— Remaining Issues に記録
- ベクトル検索（Phase 3-2 で対応）
- 既存チャンクへの一括 embedding 付与

---

### 対象ファイル・修正箇所

| ファイル | 修正対象 | 変更内容 | 理由 |
|---|---|---|---|
| `backend/rag.py` | `index_document`（L70〜88） | `get_embed_model().embed(chunks)` を呼び出し、各 Chunk に embedding を付与する。進捗ログ・エラーログを追加 | R-01〜R-04 を満たすため。他ファイルは変更不要 |

---

### 実装方針

#### 方針

- `split_into_chunks` でチャンク分割した後、`get_embed_model().embed(chunks)` を一括呼び出しする
- 戻り値の embeddings と chunks を `zip` して `Chunk(document_id, text, embedding)` のリストを組み立てる
- embedding 生成全体が例外を発生させた場合は `logger.warning` でログを出し、`embedding=None` の Chunk リストにフォールバックして upsert を継続する（ドキュメント取り込み全体は止めない）
- 進捗ログは「embedding 生成開始: N チャンク」「embedding 生成完了: N チャンク」の 2 点とする（シンプルで AC-02 を満たせる最小構成）

#### 採用理由

| 判断 | 理由 |
|---|---|
| 一括 `embed(chunks)` を採用 | `OllamaEmbedModel.embed` が `list[str]` を受け取るインターフェースになっており、1 回呼べば全チャンクの embedding が揃う。ループで個別呼び出しするより意図が明確 |
| 例外時フォールバック（embedding=None）を採用 | ドキュメント全体の取り込みをエラーにするより、テキストのみで保存できる方が教材として安全。失敗はログで確認できる（R-04） |
| 進捗ログを「開始・完了」の 2 点に絞る | 学習規模のチャンク数（数十〜数百件）では N 件ごとのログは不要。シンプルな実装で R-03 を満たせる |
| `chroma.py` を変更しない | `upsert` の `any(c.embedding ...)` 条件は「全チャンクが embedding を持つ」か「全チャンクが embedding=None」のいずれかになるよう実装を設計するため、既存 `upsert` を触らなくてよい |

---

### テスト観点

| ID | 内容 |
|---|---|
| T-01 | PDF をアップロードし取り込みが完走した後、Chroma のコレクションに embedding が保存されていること（AC-01） |
| T-02 | 取り込み中のバックエンドログに「embedding 生成開始」「embedding 生成完了」が出力されること（AC-02） |
| T-03 | T-01 完了後に RAG モード ON で質問したとき、チャンクがヒットして回答の根拠として返ること（Phase 2-2 の動作が壊れていないこと） |

---

### 設計判断

| 項目 | 判断 | 理由 | 代替案 |
|---|---|---|---|
| embedding 生成失敗時の挙動 | フォールバック（embedding=None で upsert を継続） | ドキュメント取り込み全体を止めると学習者の手戻りが大きい。テキストのみで保存しておけば BM25 検索は引き続き動く | 失敗時にドキュメント全体を error にする（Phase 2-1 と同様の挙動） |
| `embed` の呼び出し粒度 | チャンク全件を一括で `embed(chunks)` | インターフェース（`embed(texts: list[str])`）の設計意図に沿う。実装（1 件ずつ HTTP リクエスト）は隠蔽されており、呼び出し側が気にしなくてよい | ループで 1 件ずつ `embed([chunk])` を呼ぶ |
| 進捗ログの粒度 | 開始・完了の 2 点のみ | 教材規模（チャンク数は多くても数百件）では N 件ごとのログは過剰。シンプルな実装で要件を満たせる | N チャンクごとにログを出す |
| `chroma.py` の L-1/L-2 修正 | 今回は対象外 | Issue #3 スコープ外（Requirements C-03 で記録済み）。今回の実装で全チャンクが embedding を持つ想定のため、`any()` の問題は実質的に表面化しない | このフェーズで合わせて修正する |

---

### 完了条件

#### Functional

- `rag.index_document` で embedding が生成され、各 Chunk に付与されてから `vdb.upsert` が呼ばれること（AC-01）
- 取り込み後に Chroma コレクションの各チャンクに embedding が保存されていること（AC-01）
- 取り込み中のバックエンドログで進捗が確認できること（AC-02）

#### Verification

- PDF をアップロード → ステータスが `ready` になる
- `docker compose logs -f backend` で「embedding 生成開始」「embedding 生成完了」のログを確認
- Chroma コレクションの get 結果に `embeddings` が含まれていることを確認
- RAG モード ON で質問 → Phase 2-2 時点と同様にヒットが返ること（既存動作の非破壊確認）
- ERROR ログが出ていないこと

---

### 懸念事項

| 項目 | 内容 | 対応方針 |
|---|---|---|
| OllamaEmbedModel の速度 | 1 件ずつ HTTP リクエストを送る実装のため、チャンク数が多い場合に取り込みが遅い | 学習規模では許容。バッチ API 切り替えは O-04 として対象外 |
| 入力長超過 | `nomic-embed-text` の上限（8192 tokens）に対し、chunk_size=500 文字は通常超えないが理論上は発生しうる | 例外発生時は warning ログ + フォールバック（embedding=None）で対応する（設計判断に記録済み） |
| 既存チャンクの扱い | Phase 2-2 以前に取り込み済みのチャンクには embedding がない。Phase 3-2 でベクトル検索を試すには再取り込みが必要 | 注意事項として引き継ぎに記録する |

---

### Remaining Issues

| ID | 内容 | 対応予定 | 再検討条件 |
|---|---|---|---|
| RI-01 | `chroma.py:81` の `any(c.embedding ...)` の書き方（Phase 2-1 レビュー指摘 L-1/L-2） | Future（別 Issue または後続フェーズ） | embedding 生成エラーで混在状態が実際に問題になったとき |
| RI-02 | `main.py` の `except NotImplementedError` 節の削除（Phase 2-1 からの持ち越し） | 別 Issue | Phase 2-2 からの継続残課題 |
| RI-03 | `OllamaEmbedModel.embed` のバッチ最適化（複数チャンクを 1 リクエストで処理） | Future | チャンク数増加や速度が問題になったとき |

---

### 確認事項・決定事項

| 項目 | 内容 |
|---|---|
| 確認事項 | なし（設計判断はすべて決定済み） |
| 決定事項 | `rag.index_document` に `get_embed_model().embed(chunks)` を追加。失敗時はフォールバック（embedding=None）で継続 |
| 理由 | 変更ファイルが 1 つで差分が小さく、既存インターフェースを活かせる最小実装。教材として安全側の設計（フォールバック）を優先 |
| 対応方針 | bolt-0 で実装を完了する。`chroma.py` の L-1/L-2 は RI-01 として Remaining Issues に記録 |

---

### ドキュメント更新

| ドキュメント | 更新内容 |
|---|---|
| `docs/taskLog/phase3-1-bolt-0.md` | bolt 完了時に作成 |

---

### 次の bolt への引き継ぎ

なし（Issue #3 完了）

---

## References

### Requirements

- [docs/design/phase3-1-requirements.md](phase3-1-requirements.md)

### Related Issues

- GitHub Issue #3: Phase 3-1: embedding を生成する
