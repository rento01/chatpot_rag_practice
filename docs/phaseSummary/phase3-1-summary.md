# Phase 3-1 Summary

## Summary

| 項目 | 内容 |
|---|---|
| Phase | Phase 3-1 |
| Issue | #3 |
| Pull Request | #31 |
| Bolt数 | 1（bolt-0 のみ） |
| 実装結果 | 完了 |
| Review結果 | Approve |
| Remaining Issues | 5 件 |
| 次Phase | Phase 3-2 |

---

## Phase概要

Phase 2 で構築した取り込みパイプライン（extract_text → split_into_chunks → upsert）は、各チャンクを `embedding=None` のまま ChromaDB に保存していた。Phase 3-1 では `get_embed_model().embed()` を呼び出して取り込み時に embedding を生成し、チャンクごとに付与して保存するように変更した。これにより Phase 3-2 のベクトル検索が動く前提が整った。

---

## 完了内容

- `backend/rag.py` の `index_document` に `get_embed_model().embed(chunks)` の呼び出しを追加
- 各チャンクに `embedding` を付与して `vdb.upsert` を呼ぶように変更
- embedding 生成失敗時のフォールバック実装（`embedding=None` のまま継続・BM25 検索は維持）
- 進捗ログ（開始・完了チャンク数）を追加
- Code Review S-01 対応（完了ログを `try` ブロック内に移動）
- PR #31 を作成

---

## 主な設計判断

| 項目 | 判断 | 理由 |
|---|---|---|
| 失敗時フォールバック採用 | `embedding=None` のまま upsert を継続 | BM25 キーワード検索は embedding なしでも動作するため、Ollama 未起動・ネットワーク障害等でも取り込みを完走させる。教材として安全側の設計を優先 |
| 全チャンク一括 embed | `embed(chunks)` に全チャンクを渡す | インターフェース設計の意図に従い、将来バッチ API に切り替える際も呼び出し側を変えずに済む構成 |
| 進捗ログを開始・完了の 2 点のみ | N チャンクごとのログは採用しない | 教材規模（チャンク数は多くても数百件）では過剰。最小実装で AC-02 を満たせる |

---

## 実装内容

- **`get_embed_model().embed(chunks)`**: `OllamaEmbedModel.embed` が既に実装済みであったため、`rag.py` から繋ぎ込む数行の追加で完結した
- **フォールバック**: `except Exception` で全例外をキャッチし `embeddings = [None] * len(chunks)` を設定。`logger.warning` に `exc_info=True` で原因を記録する
- **embedding 付与**: `zip(chunks, embeddings)` で `Chunk(embedding=e)` を生成。`ChromaVectorDB.upsert` は既存の `any(c.embedding ...)` 条件付きで embedding を保存する実装になっていた

---

## Review結果

| Severity | 件数 |
|---|---|
| High | 0 |
| Medium | 0 |
| Suggestions | 2 |

### 主な指摘

- S-01: フォールバック後も「embedding 生成を完了」ログが出力され、成功・失敗の区別がつかない
- S-02: 型アノテーション `list[list[float] | None]` が `embed()` の戻り値型と厳密には異なる

### 対応方針

- S-01: **対応済み**（`logger.info("完了")` を `try` ブロック内に移動し、成功時のみ出力）
- S-02: **見送り**（動作上の問題なし。静的解析導入時に改めて検討）

---

## Remaining Issues

| 課題 | 対応方針 |
|---|---|
| RI-01: `chroma.py:81` の `any(c.embedding ...)` の書き方（Phase 2-1 レビュー指摘 L-1/L-2） | Future |
| RI-02: `main.py` の `except NotImplementedError` 節の削除（Phase 2-2 からの持ち越し） | 別 Issue |
| RI-03: `OllamaEmbedModel.embed` のバッチ最適化 | Future |
| RI-04: Phase 2 以前の既存コレクションとの次元数競合（384次元 vs 768次元）の注意事項整備 | Future |
| AC-02: 取り込み進捗ログの確認（Issue #30 対応後） | Issue #30 完了後 |

---

## GitHub Issues

| Issue | 内容 | 状態 |
|---|---|---|
| #3 | Phase 3-1: embedding を実装する | Open（PR #31 マージ待ち） |
| #7 | chore: ruff を dev 依存に追加して lint を整備する | Open（持ち越し） |
| #30 | バックエンドログが docker compose logs で確認できない問題 | Open |

---

## WorkLogからの振り返り

### 主な実装判断

- `EmbedModel`・`OllamaEmbedModel.embed`・`ChromaVectorDB.upsert` はいずれも実装済みであったため、`rag.py` の変更のみで完結した
- フォールバック設計を採用したことで、Ollama 停止時でも文書取り込み自体は完走できる

### 発生した問題

- 既存コレクション（Phase 2 以前）に Chroma のデフォルト埋め込み（384次元）が保存されており、768次元 embedding との次元数競合が発生した
- `docker compose exec` の heredoc で TTY エラーが発生した
- Chroma が返す `embeddings` が numpy 配列のため `if e` が真偽値判定エラーになった

### 解決方法

- 既存コレクションを削除して再取り込みし、768次元に統一した
- `docker compose exec` に `-T` フラグを付けるか、単一行コマンド形式で回避した
- `if e is not None` に変更した

---

## 学んだこと

- `nomic-embed-text` の出力次元は **768 次元**。Phase 3-2 でベクトル検索を実装するときはこの次元数を前提にする
- Phase 2 以前に取り込んだコレクションには Chroma のデフォルト埋め込み（384次元）が付いている。768次元 embedding とは同一コレクションに共存できないため再取り込みが必要
- Chroma が返す `embeddings` は numpy 配列のため、存在チェックは `if e is not None` を使う
- `docker compose exec` は非インタラクティブ環境では `-T` フラグが必要

---

## 次Phaseへの引き継ぎ

### 次にやること

- Issue #4（または対応する Issue） Phase 3-2「ベクトル検索を実装する」へ進む
- `ChromaVectorDB.search` にベクトル検索（cosine similarity / k-NN）を実装する

### 注意事項

- Chroma に保存された embedding の次元数は **768**（nomic-embed-text）
- Phase 3-2 でベクトル検索を試す際は、Phase 2 以前に取り込んだコレクションを一度削除して再取り込みする必要がある（次元数競合のため）
- `ChromaVectorDB.search` のシグネチャ（`collection_id`, `query`, `top_k=5`）は現状のまま。Phase 3-2 側で内部実装を差し替える

### 未対応事項

- RI-01: `chroma.py` の `any(c.embedding ...)` 書き方の改善
- RI-03: `OllamaEmbedModel.embed` のバッチ最適化
- RI-04: 既存コレクション次元数競合の注意事項整備
- AC-02: 進捗ログ確認（Issue #30 対応後）
- BM25 + ベクトルのハイブリッド検索（Phase 3-2 以降）
- ruff 導入（Issue #7）

---

## References

- Requirements: [docs/design/phase3-1-requirements.md](../design/phase3-1-requirements.md)
- Bolt Design: [docs/design/phase3-1-bolt-0.md](../design/phase3-1-bolt-0.md)
- WorkLog: [tmp/worklog/phase3-1-bolt-0.md](../../tmp/worklog/phase3-1-bolt-0.md)
- TaskLog: [docs/taskLog/phase3-1-bolt-0.md](../taskLog/phase3-1-bolt-0.md)
- PR: [#31 feat(phase3-1): generate embeddings during document indexing](https://github.com/rento01/chatpot_rag_practice/pull/31)