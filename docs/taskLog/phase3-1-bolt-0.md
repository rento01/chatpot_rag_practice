# Phase 3-1 bolt-0

## サマリー

| 項目 | 内容 |
|---|---|
| 目的 | `rag.index_document` に embedding 生成を組み込み、取り込み時にチャンクごとの embedding を Chroma に保存する |
| 実施内容 | `get_embed_model().embed()` 呼び出し追加、進捗ログ・失敗フォールバック追加 |
| 変更ファイル | 1 ファイル（`backend/rag.py`） |
| 動作確認 | PASS（AC-01 確認済み、AC-02 は Issue #30 対応後に確認予定） |
| Code Review | Approve（Suggestions 2 件、S-01 対応済み） |
| 課題 | 既存コレクションとの次元数競合（RI-04）、進捗ログ確認（Issue #30）、`chroma.py` L-1/L-2（RI-01） |
| 次の対応 | Phase 3-2（ベクトル検索）へ進む |

---

## 基本情報

### 実施日

2026-06-25

### 対応 Issue

#3

### bolt

bolt-0

---

## 目的

Phase 2-1 で構築した取り込みパイプライン（extract_text → split_into_chunks → upsert）に
embedding 生成ステップを追加し、各チャンクに `Chunk.embedding` を付与して Chroma に保存する。
これにより Phase 3-2 のベクトル検索が動く前提を整える。

---

## Requirements 対応

### 対応項目

- R-01: `rag.index_document` が各チャンクの embedding を生成し `Chunk.embedding` に付与して `vdb.upsert` を呼ぶ
- R-02: 取り込み完了後、Chroma のコレクション内でチャンクごとに embedding が保存されている
- R-03: 取り込み中の進捗（チャンク数・処理状況）がバックエンドログで確認できる
- R-04: embedding 生成に失敗した場合に、失敗内容がバックエンドログで確認できる

### 完了判定

- AC-01: Chroma の各チャンクに embedding が保存されていること → **PASS**（次元数: 768 確認）
- AC-02: 取り込み中の進捗が backend ログで追えること → **保留**（Issue #30 対応後に確認）

---

## 実施内容

- `from backend.llm import get_embed_model` を `rag.py` に追加
- `index_document` の `if chunks:` ブロック内に embedding 生成を追加
  - `get_embed_model().embed(chunks)` で全チャンクを一括 embed
  - 成功時: `logger.info("embedding 生成を完了: %d チャンク")`
  - 失敗時: `logger.warning` + `embeddings = [None] * len(chunks)` でフォールバック
- `Chunk` 生成時に `embedding=e` を付与（`zip(chunks, embeddings)` で対応）
- Code Review S-01 対応: 完了ログを `try` ブロック内に移動し、成功時のみ出力されるよう修正

---

## 変更ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `backend/rag.py` | 修正 | `index_document` に embedding 生成・進捗ログ・フォールバック追加 |

---

## 実装概要

`EmbedModel`・`OllamaEmbedModel.embed`・`ChromaVectorDB.upsert` はいずれも実装済みであったため、
`rag.py` の `index_document` に繋ぎ込む数行の追加で完結した。

```python
logger.info("embedding 生成を開始: %d チャンク", len(chunks))
try:
    embeddings: list[list[float] | None] = get_embed_model().embed(chunks)
    logger.info("embedding 生成を完了: %d チャンク", len(chunks))
except Exception:
    logger.warning(
        "embedding 生成に失敗しました。embedding なしで upsert を継続します",
        exc_info=True,
    )
    embeddings = [None] * len(chunks)

vdb.upsert(
    collection_id,
    [Chunk(document_id=document_id, text=c, embedding=e) for c, e in zip(chunks, embeddings)],
)
```

---

## 実装判断

### 判断1: 失敗時フォールバック（embedding=None で継続）を採用

embed() が例外を発生させた場合、取り込み全体をエラーにせず `embedding=None` のまま upsert を継続する。

**理由**: BM25 キーワード検索は embedding なしでも動作するため、Ollama 未起動・ネットワーク障害等でも文書取り込み自体を完走できる。教材として「失敗しても部分的に動く」安全側の設計を優先した。

### 判断2: 全チャンクを一括で `embed(chunks)` する

ループで 1 件ずつ呼ぶのではなく、`embed(texts: list[str])` インターフェースに沿って一括呼び出しする。

**理由**: インターフェース設計の意図に従うことで、将来バッチ API に切り替える場合も `OllamaEmbedModel.embed` 側だけ変更すれば呼び出し側は変わらない。

### 判断3: 進捗ログを開始・完了の 2 点のみにする

N チャンクごとのログは採用しない。

**理由**: 教材規模（チャンク数は多くても数百件）では過剰。最小実装で AC-02 を満たせる。

---

## 設計との差異

なし

---

## 動作確認

| 確認内容 | 期待結果 | 実結果 | 判定 |
|---|---|---|---|
| PDF 取り込み後 status=ready | `status=ready`、`page_count` に値 | `status=ready`、`page_count=11` | PASS |
| Chroma の embedding 保存（AC-01） | 次元数が `None` でなく数値 | 次元数: 768（nomic-embed-text） | PASS |
| 取り込み進捗ログ（AC-02） | 「開始」「完了」ログが出る | Issue #30 のため確認不可 | 保留 |

---

## Code Review 結果

**Approve**（Blocker: 0 / Important: 0 / Suggestions: 2）

| ID | 内容 | 対応 |
|---|---|---|
| S-01 | フォールバック後も「完了」ログが出力され成功・失敗の区別がつかない | **対応済み**: `logger.info("完了")` を `try` ブロック内に移動 |
| S-02 | 型アノテーション `list[list[float] \| None]` が `embed()` の戻り値型と厳密には異なる | **見送り**: 動作上の問題なし。静的解析導入時に改めて検討 |

---

## 発生した問題と対応

| 問題 | 原因 | 対応 |
|---|---|---|
| 既存コレクションへの再取り込みで `status=error` | Phase 2 で Chroma のデフォルト埋め込み（384次元）が保存済みのため、768次元 embedding との次元数競合が発生 | コレクションを削除して再取り込みし、768次元で統一 |
| `docker compose exec` の heredoc で TTY エラー | デフォルトで TTY を要求するが非インタラクティブ環境では割り当てられない | `-T` フラグを付けるか、`-c` に単一行コマンドを渡す形式で回避 |
| numpy 配列の真偽値判定エラー | Chroma が返す embeddings は numpy 配列のため `if e` が ambiguous | `if e is not None` に変更 |

---

## 学んだこと

- `OllamaEmbedModel.embed` はすでに実装済みであり、`rag.py` の変更のみで embedding 生成が動いた。事前に用意されたインターフェース設計の恩恵を体験した
- Phase 2 以前に `embedding=None` で取り込んだコレクションには Chroma のデフォルト埋め込み（384次元）が付いている。`nomic-embed-text`（768次元）とは同一コレクションに共存できないため、再取り込みが必要
- Chroma が返す `embeddings` は numpy 配列であるため、存在チェックは `if e is not None` を使う
- `nomic-embed-text` の出力次元は 768 次元。Phase 3-2 でベクトル検索を実装するときはこの次元数を前提にする

---

## 課題

### Remaining Issues

| ID | 内容 | 対応予定 |
|---|---|---|
| RI-01 | `chroma.py:81` の `any(c.embedding ...)` 書き方（Phase 2-1 レビュー指摘 L-1/L-2） | Future |
| RI-02 | `main.py` の `except NotImplementedError` 節の削除 | 別 Issue |
| RI-03 | `OllamaEmbedModel.embed` のバッチ最適化 | Future |
| RI-04 | Phase 2 以前の既存コレクションとの次元数競合（利用者への注意事項整備） | Future |
| AC-02 | 進捗ログの確認（Issue #30 対応後） | Issue #30 完了後 |

### GitHub Issues

- #7: ruff を dev 依存に追加して lint を整備する（継続中）
- #30: バックエンドログが docker compose logs で確認できない問題（継続中）

---

## 次の bolt への引き継ぎ

- Phase 3-2 ではベクトル検索（cosine similarity / k-NN）を実装する
- Chroma に保存された embedding の次元数は **768**（nomic-embed-text）
- Phase 3-2 でベクトル検索を試す際は、Phase 2 以前に取り込んだコレクションを一度削除して再取り込みする必要がある（次元数競合のため）
- `ChromaVectorDB.search` のシグネチャは現状のまま（`collection_id`, `query`, `top_k=5`）で Phase 3-2 側から変更する

---

## 関連資料

- Requirements: [docs/design/phase3-1-requirements.md](../design/phase3-1-requirements.md)
- Bolt Design: [docs/design/phase3-1-bolt-0.md](../design/phase3-1-bolt-0.md)
- WorkLog: [tmp/worklog/phase3-1-bolt-0.md](../../tmp/worklog/phase3-1-bolt-0.md)

### 関連コミット

（PR マージ後に記入）

### 関連 PR

（作成後に記入）
