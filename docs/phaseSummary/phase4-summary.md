# Phase 4 Summary

## Summary

| 項目 | 内容 |
|---|---|
| Phase | Phase 4 |
| Issue | #6 |
| Pull Request | #36 |
| Bolt数 | 1（bolt-0 のみ） |
| 実装結果 | 完了 |
| Review結果 | Request Changes → F-01/F-02 修正済み → Approve |
| Remaining Issues | 3 件 |
| 次Phase | Phase 5（チャンク分割改善） |

---

## Phase概要

Phase 3-3 まででハイブリッド検索が動作するようになったが、処理内部（検索時間・LLM 入出力・各ステップの所要時間）が見えていなかった。Phase 4 では `backend/tracing.py` を Langfuse SDK v4 対応の観測ラッパとして整備し、`chat` と `index-document` のトレースに子 span を追加した。Langfuse ダッシュボードでスパンツリーとして処理を可視化できる状態になった。

実装中に Langfuse SDK v4 の破壊的 API 変更（`.trace()` 廃止）が発覚し、設計時の `trace_ctx` 引き回し方式から OTel コンテキスト伝播方式に変更した。結果として関数シグネチャが変わらずよりシンプルな実装になった。

---

## 完了内容

- `backend/tracing.py`: Langfuse SDK v4（`start_as_current_observation` API）対応。モジュールレベルの `trace()` / `span()` / `generation()` コンテキストマネージャを実装。`NoopSpan` public 化
- `backend/main.py`: `_build_messages` 内に `span("rag-search")` を追加（use_rag=True 時のみ）。`token_stream` に `generation("llm-generation")` を追加。`_build_messages` 呼び出しを trace コンテキスト内に移動
- `backend/rag.py`: `index_document` の各ステップ（extract / split / embed / upsert）を `tracing_span()` で計測
- `.env.example`: `LANGFUSE_BASE_URL` → `LANGFUSE_HOST` に修正。JP リージョン利用時のコメントを追加
- `docs/development_flow.md`: テンプレート対応表（§7）を追加。テンプレート参照の必須ルールを明記
- `CLAUDE.md`: 成果物作成前にテンプレートを読むルールを追加

---

## 主な設計判断

| 項目 | 判断 | 理由 |
|---|---|---|
| `trace_ctx` 引き回し → OTel 方式に変更 | OTel コンテキスト伝播方式を採用 | SDK v4 で `trace_ctx.span()` が廃止。OTel 方式の方が関数シグネチャを変えなくて済みシンプル |
| `Langfuse()` に引数を明示渡し | `public_key` / `secret_key` / `host` を明示 | デフォルト引数で呼ぶと SDK が独自に env を読み直すため `settings.langfuse_host` が反映されない |
| `_build_messages` を trace 内に移動 | trace コンテキスト内で呼ぶ | `rag-search` span を `chat` trace の子にするために必要。`db.add` は db セッションが必要なため trace の外に残す |
| `NoopSpan` public 化 | `_NoopSpan` → `NoopSpan` に rename | `rag.py` から import するために必要。シングルトンより直接 import の方が意図が明確 |
| `LANGFUSE_*` 未設定時は no-op | `_init()` の早期 return で保証 | 学習者が Langfuse 未設定でもアプリが動くことを担保 |

---

## 実装内容

- **`trace("chat")`**: RAG 検索（`rag-search` span）と LLM 生成（`llm-generation` generation）を子として持つスパンツリー
- **`trace("index-document")`**: テキスト抽出（`extract`）/ チャンク分割（`split`）/ embedding 生成（`embed`）/ upsert の 4 span で構成
- **no-op 透過**: `LANGFUSE_*` 未設定時は `NoopSpan` が返り、`.update()` / `.end()` を安全に呼べる
- **OTel コンテキスト伝播**: `with trace(...):` ブロック内で `span()` / `generation()` を呼ぶと自動的に親子関係が構築される

---

## Review結果

| Severity | 件数 |
|---|---|
| High | 1 |
| Medium | 1 |
| Low | 1 |

### 主な指摘

- F-01（High）: `.env.example` に実際の API キーが含まれていた → コミット前に修正済み
- F-02（Medium）: `LANGFUSE_BASE_URL` と `LANGFUSE_HOST` の変数名不一致 → `LANGFUSE_HOST` に統一済み
- F-03（Low）: `rag_ctx` が `with span(...)` ブロック外で参照されている → Remaining Issues に記録

### 対応方針

- F-01・F-02: コミット前に修正済み
- F-03: RI-03 として記録して見送り（機能上問題なし）

---

## Remaining Issues

| 課題 | 対応方針 |
|---|---|
| RI-01: generation の `usage`（input_tokens / output_tokens）が記録できない | Phase 7（Bedrock 移行）後に追加 |
| RI-02: `rag.build_context` / `vdb.search` 内の span が存在しない | 必要になったタイミングで追加 |
| RI-03: `pyproject.toml` の `langfuse>=2.0.0` に上限バージョンがない | 別 Issue 化を推奨 |

---

## GitHub Issues

| Issue | 内容 | 状態 |
|---|---|---|
| #6 | Phase 4: Langfuse でトレースを取る | Closed（PR #36 マージ） |
| #7 | chore: ruff を dev 依存に追加して lint を整備する | Open（持ち越し） |
| #34 | Codex 導入の検討・整理 | Open |

---

## WorkLogからの振り返り

### 主な実装判断

- 設計時は `trace_ctx` を引数で引き回す方式を想定していたが、SDK v4 の破壊的変更により OTel 方式に切り替えた。`_build_messages` と `index_document` の引数が変わらずに済み、設計変更が結果的にシンプルな実装につながった（WorkLog §9 作業振り返り）
- `NoopSpan.span()` を `return self` から `return NoopSpan()` に変更した。本物の Langfuse では `span()` が異なるオブジェクトを返すため、noop も同じ構造にした（WorkLog §5 差分メモ）
- `_build_messages` 内のローカル変数名 `ctx` が `rag.build_context()` の戻り値（`RagContext`）と衝突するため `rag_ctx` に変更した（WorkLog §5 差分メモ）

### 発生した問題

1. `AttributeError: 'Langfuse' object has no attribute 'trace'`（SDK v4 破壊的 API 変更）
2. `401 Unauthorized`（JP プロジェクトに US エンドポイントのキーを送信 + `Langfuse()` が `settings.langfuse_host` を参照していなかった）
3. コード変更がコンテナに反映されない（`docker compose up -d --build` がコンテナを差し替えないケース）

### 解決方法

1. `tracing.py` を `start_as_current_observation()` ベースに全面書き換え。`main.py` / `rag.py` も OTel コンテキスト方式に変更
2. `Langfuse(host=settings.langfuse_host)` に明示渡し。`.env` の `LANGFUSE_HOST` を `https://jp.cloud.langfuse.com` に設定
3. `docker compose stop backend && docker compose up -d backend` の 2 ステップを確立

---

## 学んだこと

- Langfuse SDK v4 は OTel ベースに移行しており、v3 以前の `trace_ctx` 引き回し方式は廃止された。上限なし依存指定（`>=2.0.0`）でメジャーバージョンアップを自動吸収するリスクがある
- OTel コンテキスト伝播：`with start_as_current_observation():` 内で別の observation を開くと自動的に親子関係が構築される。`trace_ctx` を引き回す設計より責務が明確になる
- Docker イメージ焼き込み構成では `docker compose stop` → `docker compose up -d` の 2 ステップが確実なコンテナ差し替え手順
- `.env.example` はプレースホルダー値で管理する。実際のキーを書いてコミットするとシークレットが漏洩する
- 開発フローの各工程でテンプレートを参照する前に出力を始めてはならない（`CLAUDE.md` と `development_flow.md` にルールとして追記）

---

## 次Phaseへの引き継ぎ

### 次にやること

- Phase 5（チャンク分割改善）へ進む
- 現在の固定長チャンク（chunk_size=500 / chunk_overlap=50）を改善する

### 注意事項

- Langfuse JP リージョンを使う場合は `.env` に `LANGFUSE_HOST=https://jp.cloud.langfuse.com` を設定する
- `LANGFUSE_*` を空にすれば no-op で動作するため、未設定でも従来通り動く
- `tracing.py` の `trace()` / `span()` / `generation()` はコンテキストマネージャとして使う（`with` 構文必須）

### 未対応事項

- RI-01: usage 記録（Phase 7 後）
- RI-02: `vdb.search` 内部 span（必要時）
- RI-03: `langfuse>=2.0.0` に上限バージョンを付ける（別 Issue 推奨）
- ruff 導入（Issue #7）
- Codex 導入（Issue #34）

---

## References

- Requirements: [docs/design/phase4-requirements.md](../design/phase4-requirements.md)
- Bolt Design: [docs/design/phase4-bolt-0.md](../design/phase4-bolt-0.md)
- WorkLog: [tmp/worklog/phase4-bolt-0.md](../../tmp/worklog/phase4-bolt-0.md)
- TaskLog: [docs/taskLog/phase4-bolt-0.md](../taskLog/phase4-bolt-0.md)
- Code Review: [docs/review/phase4-bolt-0.md](../review/phase4-bolt-0.md)
- Error Investigation: [docs/error/20260629-langfuse-trace-not-delivered.md](../error/20260629-langfuse-trace-not-delivered.md)
- PR: [#36 feat(phase4): add Langfuse tracing spans for chat and index-document](https://github.com/rento01/chatpot_rag_practice/pull/36)
