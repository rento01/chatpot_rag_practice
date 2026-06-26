# Phase 3-1 bolt-0

## サマリー

| 項目 | 内容 |
|---|---|
| 目的 | `rag.index_document` に embedding 生成を組み込み、取り込み時にチャンクごとの embedding を Chroma に保存する |
| 実施内容 | `index_document` への `get_embed_model().embed()` 呼び出し追加、進捗ログ・失敗フォールバック追加 |
| 変更ファイル | 1 ファイル（`backend/rag.py` 修正） |
| 動作確認 | PASS（AC-01 確認済み、AC-02 は Issue #30 対応後に確認予定） |
| AIレビュー | Approve（Blocker: 0 / Important: 0 / Suggestions: 2、S-01 対応済み） |
| 課題 | 次元数競合時の既存コレクション対応（RI-04）、進捗ログ確認（Issue #30）、`chroma.py` L-1/L-2（RI-01） |
| 次の対応 | Commit → Push → PR 作成 → Phase 3-2（ベクトル検索）へ進む |

---

## 基本情報

### 実施日

2026-06-25

### 対応 Issue

#3

### bolt

bolt-0

### ブランチ

feature/3-phase3-1-embedding

---

## 関連資料

**Requirements**
- `docs/design/phase3-1-requirements.md`

**Bolt Design**
- `docs/design/phase3-1-bolt-0.md`

**Code Review**（完了後に記入）

**Error Investigation**
- なし

---

## TODO・メモ

- [x] embedding 生成を `index_document` に組み込む
- [x] 進捗ログ（開始・完了）を追加する
- [x] 失敗時フォールバック（embedding=None）を実装する
- [x] Chroma に embedding が保存されることを確認する（次元数: 768）
- [ ] AC-02 進捗ログの確認（Issue #30 対応後）
- [x] Code Review（S-01 対応済み・Approve）
- [x] WorkLog 最終更新
- [x] TaskLog 作成
- [ ] Commit / Push / PR 作成

---

## 1. 作業目的

### 今回の目的

Phase 2-1 で構築した取り込みパイプライン（extract_text → split_into_chunks → upsert）に
embedding 生成ステップを追加し、各チャンクに `Chunk.embedding` を付与して Chroma に保存する。

### 完了条件

- 取り込み完了後、Chroma 側でチャンクごとに embedding が保存されている
- 取り込み中の進捗が backend ログで追える

---

## 2. Requirements 対応

### 対応項目

- R-01: `rag.index_document` が各チャンクの embedding を生成し `Chunk.embedding` に付与して `vdb.upsert` を呼ぶ
- R-02: 取り込み完了後、Chroma のコレクション内でチャンクごとに embedding が保存されている
- R-03: 取り込み中の進捗（チャンク数・処理状況）がバックエンドログで確認できる
- R-04: embedding 生成に失敗した場合に、失敗内容がバックエンドログで確認できる

### 完了判定

- AC-01: 取り込み後に Chroma の各チャンクに embedding が保存されていること → **PASS**（次元数: 768 を確認）
- AC-02: 取り込み中の進捗が backend ログで追えること → **保留**（Issue #30 のログ基盤対応後に確認）

---

## 3. 実装前調査

### 確認したファイル

```
backend/rag.py
backend/llm/embedModel.py
backend/llm/ollama.py
backend/vector_db/chroma.py
backend/config/settings.py
```

### 調査結果

- `EmbedModel.embed(texts: list[str]) -> list[list[float]]` のインターフェースはすでに定義済み
- `OllamaEmbedModel.embed` は 1 件ずつ HTTP リクエストを送る実装（学習規模では問題なし）
- `ChromaVectorDB.upsert` の `embeddings` 渡し部分はすでに実装済みのため、`rag.py` の変更のみで完結する
- `get_embed_model()` のインポートが `rag.py` に未追加のため、import 追加が必要
- `EMBEDDING_MODEL=nomic-embed-text` が `.env` の既定値

### 疑問点

- なし（調査で解消済み）

---

## 4. 実装ログ

### 作業1: インポート追加

**内容**

`from backend.llm import get_embed_model` を `rag.py` に追加

**変更ファイル**

`backend/rag.py`

**理由**

`get_embed_model()` を `index_document` から呼び出すために必要。既存 import が `get_chat_model` のみで `get_embed_model` は含まれていなかった。

---

### 作業2: embedding 生成の組み込み

**内容**

`index_document` の `if chunks:` ブロック内に以下を追加：
- `logger.info("embedding 生成を開始: %d チャンク", len(chunks))`
- `get_embed_model().embed(chunks)` の呼び出し
- 例外時の `logger.warning` + `embeddings = [None] * len(chunks)` フォールバック
- `logger.info("embedding 生成を完了: %d チャンク", len(chunks))`
- `Chunk` 生成時に `embedding=e` を付与（`zip(chunks, embeddings)` で対応）

**変更ファイル**

`backend/rag.py`

**理由**

- 全チャンクを一括 `embed(chunks)` するのは `EmbedModel` のインターフェース設計意図に沿う
- 例外時フォールバック（embedding=None）を選択したのは、取り込み全体を失敗にするよりテキストのみで保存した方が教材として安全なため。BM25 キーワード検索は embedding なしでも引き続き動作する

---

## 5. Diff Review

### 変更ファイル

- `backend/rag.py`（+14 行 / -2 行）

### 意図した変更

- `get_embed_model` のインポート追加
- embedding 生成呼び出し（進捗ログ・フォールバックを含む）
- `Chunk` 生成時の `embedding=e` 付与

### 削除した処理

- `[Chunk(document_id=document_id, text=c) for c in chunks]` を `zip` を使う形に置き換え（embedding=None の場合も同じ構造で扱える）

### 想定外変更

なし

### リスク・未確認事項

- AC-02（進捗ログ）は Issue #30 のログ基盤問題のため確認不可
- Phase 2 以前の既存コレクションとの次元数競合が発生した（エラー対応ログ参照）

### 次回確認事項

- Issue #30 対応後に AC-02 のログ出力を再確認する
- Code Review で `chroma.py:81` の L-1/L-2 指摘への対応方針を確認する

---

## 6. エラー対応ログ

### エラー1: 既存コレクションとの次元数競合

**発生した問題**

Phase 2-1/2-2 で取り込んだ既存コレクションに対して Phase 3-1 の実装で再取り込みしたところ、ドキュメントのステータスが `error` になった

**原因**

Phase 2-1/2-2 では `embedding=None` のまま upsert していたため、Chroma がデフォルトの埋め込み関数（sentence-transformers `all-MiniLM-L6-v2`、384次元）で自動生成した embedding を保存していた。Phase 3-1 で `nomic-embed-text`（768次元）による embedding を同一コレクションに upsert しようとしたため、次元数の競合が発生した。

**対応内容**

コレクションを削除して再取り込みすることで、768次元の embedding で統一した新しいコレクションとして再構築した

**再発防止**

Phase 3-1 以降は embedding を付与して取り込むため、Phase 2 以前に作成した既存コレクションはそのまま使えない。既存コレクションを使い続ける場合はコレクションを削除して再取り込みが必要

---

### エラー2: 動作確認コマンドの TTY エラー

**発生した問題**

heredoc 形式の `docker compose exec` コマンドで `the input device is not a TTY` エラーが発生した

**原因**

`docker compose exec` はデフォルトで TTY を要求するが、パイプや非インタラクティブな実行環境では TTY が割り当てられない

**対応内容**

`-T` フラグを付けることで回避。または複数行 Python コードを `-c` の文字列として渡す形式に変更することで解決

**再発防止**

非インタラクティブな確認コマンドには `-T` フラグを使う

---

### エラー3: numpy 配列の真偽値判定エラー

**発生した問題**

embedding 次元数確認コマンドで `ValueError: The truth value of an array with more than one element is ambiguous` が発生した

**原因**

Chroma の `embeddings` は numpy 配列として返ってくるため、`if e` による真偽値判定が機能しない

**対応内容**

`if e is not None` に変更することで回避

**再発防止**

embedding のような数値配列の存在チェックは `if e is not None` を使う

---

## 7. Claude Code 活用ログ

### 判断1: 入力長超過時の挙動

**質問内容**

embedding 生成が失敗した場合（入力長超過など）、取り込み全体をエラーにするか、フォールバックするか

**回答要約**

フォールバック（embedding=None で upsert 継続）を推奨。BM25 キーワード検索は embedding なしでも動作するため、学習者がネットワーク障害等で Ollama につながらなくても取り込み自体を完走できる安全な設計

**採用判断**

採用

**判断理由**

教材として「失敗しても部分的に動く」安全側の設計が適切。フォールバック時は warning ログで失敗を記録するため、問題を見落とす心配もない

---

### 判断2: `embed()` の呼び出し粒度

**質問内容**

全チャンクを一括で `embed(chunks)` するか、ループで 1 件ずつ `embed([chunk])` を呼ぶか

**回答要約**

一括呼び出し（`embed(chunks)`）を推奨。`EmbedModel` のインターフェース設計意図に沿い、実装の詳細（1 件ずつ HTTP リクエスト）は隠蔽される。呼び出し側が実装詳細を気にしなくてよい構造になる

**採用判断**

採用

**判断理由**

インターフェース設計に従うことでコードの意図が明確になる。将来バッチ API に切り替える場合も `OllamaEmbedModel.embed` 側だけ変更すれば呼び出し側は変わらない

---

### 判断3: 進捗ログの粒度

**質問内容**

進捗ログを「開始・完了の 2 点のみ」にするか、N チャンクごとに出すか

**回答要約**

「開始: N チャンク / 完了: N チャンク」の 2 点のみで十分。教材規模（チャンク数は多くても数百件）では N 件ごとのログは過剰になる

**採用判断**

採用

**判断理由**

最小実装で AC-02 を満たせる。ログが多すぎると逆に読みにくくなる

---

## 8. 動作確認

### 確認1: ドキュメント取り込み完了

| 項目 | 内容 |
|---|---|
| 実施内容 | PDF（就業規則.pdf）をアップロードし、ステータスが ready になることを確認 |
| 期待結果 | `status=ready`、`page_count` に値が入る |
| 実結果 | `status=ready`、`page_count=11`、`indexed_at` 記録あり |
| 判定 | OK |

### 確認2: Chroma への embedding 保存（AC-01）

| 項目 | 内容 |
|---|---|
| 実施内容 | backend コンテナ内から `chromadb.HttpClient` 経由でコレクションの embedding を取得 |
| 期待結果 | embedding 次元数が `None` でなく数値で返ること |
| 実結果 | 次元数: 768（nomic-embed-text の出力次元） |
| 判定 | OK |

### 確認3: 取り込み進捗ログ（AC-02）

| 項目 | 内容 |
|---|---|
| 実施内容 | `docker compose logs backend` でログを確認 |
| 期待結果 | 「embedding 生成を開始」「embedding 生成を完了」が出力されること |
| 実結果 | Issue #30（ログ基盤問題）のため確認不可 |
| 判定 | 保留（Issue #30 対応後に再確認） |

---

## 9. 作業振り返り

### 完了したこと

- `rag.index_document` への embedding 生成組み込み（AC-01 PASS）
- 取り込み時の進捗ログ・失敗フォールバックの実装
- Chroma に 768 次元の embedding が保存されることを確認

### 学んだこと

- `OllamaEmbedModel.embed` はすでに実装済みであり、`rag.py` の変更のみで embedding 生成が動いた。事前に用意されたインターフェース設計の恩恵を体験した
- Phase 2 以前に `embedding=None` で取り込んだコレクションには Chroma のデフォルト埋め込み（384次元）が付いている。Phase 3-1 以降の 768次元 embedding とは同一コレクションに共存できないため、再取り込みが必要
- Chroma が返す `embeddings` は numpy 配列であるため、`if e is not None` で存在チェックする必要がある
- `nomic-embed-text` の出力次元は 768 次元。Phase 3-2 でベクトル検索を実装するときはこの次元数を前提にする

### 判断理由として残したいこと

- **フォールバック採用の理由**: embedding 生成が失敗した場合に取り込み全体を error にせず、embedding=None のまま upsert を継続する設計にした。BM25 キーワード検索は embedding なしで動作するため、学習者がネットワーク障害等で Ollama につながらなくても文書取り込み自体は完走できる

### 残課題

| ID | 内容 | 対応予定 |
|---|---|---|
| RI-01 | `chroma.py:81` の `any(c.embedding ...)` 書き方（Phase 2-1 レビュー指摘 L-1/L-2） | Future |
| RI-02 | `main.py` の `except NotImplementedError` 節の削除 | 別 Issue |
| RI-03 | `OllamaEmbedModel.embed` のバッチ最適化 | Future |
| RI-04 | Phase 2 以前に作成した既存コレクションと embedding 次元数が競合する問題（利用者への注意事項の整備） | Future |
| AC-02 | 進捗ログの確認（Issue #30 対応後） | Issue #30 完了後 |

### 次回作業

- Commit / Push / PR 作成
- Phase 3-2（ベクトル検索）へ進む

---

## 10. Code Review

### 結果

Approve（Blocker: 0 / Important: 0 / Suggestions: 2）

### 指摘一覧

| ID | 重要度 | 内容 | 対応 |
|---|---|---|---|
| S-01 | Suggestion | フォールバック後も「embedding 生成を完了」ログが出力され、成功・失敗の区別がつかない | 対応済み：`logger.info("完了")` を `try` ブロック内に移動 |
| S-02 | Suggestion（軽微） | 型アノテーション `list[list[float] \| None]` が `embed()` の戻り値型と厳密には異なる | 見送り：動作上の問題なし。静的解析導入時に改めて検討 |

### S-01 修正内容

```python
# 修正前: 失敗パスでも「完了」が出力される
try:
    embeddings = get_embed_model().embed(chunks)
except Exception:
    ...
logger.info("embedding 生成を完了: %d チャンク", len(chunks))  # ← try の外

# 修正後: 成功時のみ「完了」が出力される
try:
    embeddings = get_embed_model().embed(chunks)
    logger.info("embedding 生成を完了: %d チャンク", len(chunks))  # ← try の中
except Exception:
    ...
```

---

## 関連ドキュメント

- Requirements: `docs/design/phase3-1-requirements.md`
- Bolt Design: `docs/design/phase3-1-bolt-0.md`
- TaskLog（完了後）: `docs/taskLog/phase3-1-bolt-0.md`
