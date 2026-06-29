# Phase 4 bolt-0

## サマリー

| 項目 | 内容 |
|---|---|
| 目的 | `chat` / `index-document` トレースに子 span を追加し、Langfuse ダッシュボードでスパンツリーとして観測できる状態にする |
| 実施内容 | tracing.py: v4 API 対応・NoopSpan public 化 / main.py: rag-search span・llm-generation span 追加 / rag.py: extract・split・embed・upsert span 追加 / .env.example: 変数名修正 |
| 変更ファイル | 4 ファイル（`backend/tracing.py` / `backend/main.py` / `backend/rag.py` / `.env.example`） |
| 動作確認 | PASS |
| Code Review | Request Changes → F-01/F-02 修正済み → Approve |
| 課題 | RI-01: usage 記録（Phase 7 対応予定）/ RI-02: search 内部 span（必要時追加） |
| 次の対応 | Phase 4 完了 → Phase 5（チャンク分割改善） |

---

## 基本情報

### 実施日

2026-06-29

### 対応 Issue

#6

### bolt

bolt-0

---

## 目的

`backend/tracing.py` に Langfuse SDK v4 対応の観測ラッパを整備し、`backend/main.py` と `backend/rag.py` に子 span を追加する。これにより Langfuse ダッシュボードで `chat` と `index-document` のスパンツリーを確認できる状態にする。

---

## Requirements 対応

### 対応項目

- R-01: `chat` トレース内に `rag-search` span（use_rag=True 時）と `llm-generation` generation を追加
- R-02: `index-document` トレース内に `extract` / `split` / `embed` / `upsert` span を追加
- R-03: `LANGFUSE_*` 未設定時は全 span が no-op として動作
- R-04: 既存トップレベルトレース構造（`trace("chat")` / `trace("index-document")`）を維持

### 完了判定

- AC-01: Langfuse ダッシュボードで span ツリーを確認できること → **PASS**（JP エンドポイントで `chat` → `rag-search` / `llm-generation` を確認）
- AC-02: `LANGFUSE_*` 空でアプリが動くこと → **PASS**

---

## 実施内容

### tracing.py

Langfuse SDK v4 の OTel ベース API（`start_as_current_observation()`）に対応。モジュールレベルの `trace()` / `span()` / `generation()` コンテキストマネージャを実装した。`_NoopSpan` → `NoopSpan` に rename（public 化）。`Langfuse()` に `host=settings.langfuse_host` を明示渡しすることで、`settings.py` の `LANGFUSE_HOST` が確実に反映される。

### main.py

- `_build_messages` 内で `with span(name="rag-search", ...)` を追加（use_rag=True 時のみ）
- `token_stream` 内: `_build_messages(req)` を `with trace("chat", ...):` ブロック内に移動
- `with generation(name="llm-generation", ...) as gen:` で LLM ストリームを計測
- `_index_document` 内: `rag.index_document(...)` を `with trace("index-document", ...):` ブロック内で呼ぶ

### rag.py

`index_document` の各処理ステップを `with tracing_span(name="...", input=...) as s:` / `s.update(output=...)` で計測。引数変更なし（OTel コンテキストで自動的に親 span の子になる）。

### .env.example

`LANGFUSE_BASE_URL` → `LANGFUSE_HOST` に統一（`settings.py` / `docker-compose.yml` との整合）。JP リージョン利用時のコメントを追加。

---

## 変更ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `backend/tracing.py` | 修正 | v4 API 対応。`trace()` / `span()` / `generation()` を `start_as_current_observation()` ベースに書き換え。`NoopSpan` public 化。`Langfuse()` に明示引数を渡す |
| `backend/main.py` | 修正 | `_build_messages` 内に `span("rag-search")` 追加。`token_stream` に `generation("llm-generation")` 追加。メッセージ構築を trace 内に移動 |
| `backend/rag.py` | 修正 | `index_document` の各処理ステップに `tracing_span()` を追加（extract / split / embed / upsert） |
| `.env.example` | 修正 | `LANGFUSE_BASE_URL` → `LANGFUSE_HOST` に修正。JP コメント追加。シークレットをプレースホルダーに差し戻し |

---

## 実装判断

### 判断1: `trace_ctx` 引き回し → OTel コンテキスト伝播方式に変更

**設計時の方針**: `trace()` が yield するオブジェクト（`StatefulTraceClient`）を関数引数として `_build_messages` / `index_document` に引き回す。

**変更後の方針**: OTel コンテキストが自動で親子関係を管理するため、`trace_ctx` 引数が不要。モジュールレベルの `span()` / `generation()` を直接呼ぶ。

**変更理由**: `pyproject.toml` の `langfuse>=2.0.0` という上限なし指定により SDK v4.10.0 がインストールされており、v3 の `.trace()` / `.span()` API が廃止されていた。v4 の OTel 方式に対応した結果、関数シグネチャが変わらずよりシンプルな実装になった。

### 判断2: `Langfuse()` に引数を明示渡し

**理由**: `Langfuse()` をデフォルト引数で呼ぶと SDK が独自に環境変数を読み直すため、`settings.py` の `LANGFUSE_HOST` 変数が反映されない。明示渡しで `settings.langfuse_host` の値を確実に使う。

### 判断3: `_build_messages` を trace 内に移動

**理由**: `rag-search` span を `chat` trace の子にするには、`_build_messages` の呼び出しが trace コンテキスト内にある必要がある。ユーザーメッセージ保存（`db.add`）は `db` セッションが必要なため trace の外に残す。

---

## 設計との差異

設計書（`docs/design/phase4-bolt-0.md`）の「設計変更履歴」に詳細を記載。主な差異は以下。

| 設計要素 | 設計時 | 実装時 |
|---|---|---|
| 親子 span の管理 | `trace_ctx` を引数で引き回す | OTel コンテキストが自動管理 |
| `_build_messages` シグネチャ | `trace_ctx=None` 引数追加 | 変更なし |
| `index_document` シグネチャ | `trace_ctx=None` 引数追加 | 変更なし |
| span の開始/終了 | `s = ctx.span(...)` / `s.end(...)` | `with tracing_span(...) as s:` / `s.update(...)` |

---

## 動作確認

| 確認内容 | 期待結果 | 実結果 | 判定 |
|---|---|---|---|
| `LANGFUSE_*` 未設定でチャットが正常ストリームされること | no-op で透過的に動作 | 正常にストリームが返った | PASS |
| `LANGFUSE_*` 未設定でドキュメントアップロード → `ready` になること | no-op で取り込みが完走 | `ready` になった | PASS |
| `LANGFUSE_*` 設定済みで span ツリーが Langfuse ダッシュボードに表示されること | `chat` → `rag-search` / `llm-generation` のツリーが見える | JP エンドポイントで span ツリーを確認 | PASS |

---

## Code Review 結果

**Request Changes → 修正後 Approve**（High: 1 / Medium: 1 / Low: 1 → 全件対応済み）

| ID | Severity | 内容 | 対応 |
|---|---|---|---|
| F-01 | High | `.env.example` に実際の API キーが含まれていた | **修正済み**（プレースホルダーに差し戻し） |
| F-02 | Medium | `.env.example` の `LANGFUSE_BASE_URL` が `LANGFUSE_HOST` と不一致 | **修正済み**（`LANGFUSE_HOST` に統一・JP コメント追加） |
| F-03 | Low | `rag_ctx` が `with span(...)` ブロック外で参照されている | **Remaining Issues 記録**（機能上問題なし） |

---

## 発生した問題と対応

詳細は `docs/error/20260629-langfuse-trace-not-delivered.md` を参照。

| # | 現象 | 原因 | 対応 |
|---|---|---|---|
| 1 | チャット送信で `AttributeError: 'Langfuse' object has no attribute 'trace'` | SDK v4 で `.trace()` API が廃止 | `tracing.py` を `start_as_current_observation()` ベースに全面書き換え |
| 2 | `401 Unauthorized`（OTel exporter） | JP プロジェクトに US エンドポイントのキーを送信していた + `Langfuse()` が `settings.langfuse_host` を参照していなかった | `Langfuse(host=settings.langfuse_host)` に変更・`.env` の `LANGFUSE_HOST` を JP に設定 |
| 3 | コード修正がコンテナに反映されない | イメージ焼き込み構成で `--build` 後にコンテナが差し替わらないケースがあった | `docker compose stop backend && docker compose up -d backend` の 2 ステップで解消 |

---

## 学んだこと

- **Langfuse SDK v4 の破壊的変更**: `trace()` / `span()` / `generation()` がインスタンスメソッドから廃止され、OTel コンテキスト伝播ベースの API に移行した。上限なし依存指定（`>=2.0.0`）でメジャーバージョンアップを吸収してしまうリスクがある
- **OTel コンテキスト伝播**: `with start_as_current_observation():` 内で別の `start_as_current_observation()` を呼ぶと自動的に親子関係が構築される。`trace_ctx` を引き回す必要がなくなりコードがシンプルになる
- **`contextmanager` デコレータ**: `yield` の前後に処理を書くことで、`with` 構文で使えるファクトリを作れる。`finally` で flush を確保する設計が有効
- **Docker イメージ焼き込み構成**: コードを volume mount せずイメージに焼き込む構成では、`docker compose stop` → `docker compose up -d` が確実なコンテナ差し替え手順

---

## 課題

### Remaining Issues

| ID | 内容 | 理由 | 対応予定 |
|---|---|---|---|
| RI-01 | generation の `usage`（input_tokens / output_tokens）が記録できない | Ollama はストリーム時にトークン数を返さない | Phase 7（Bedrock 移行）後 |
| RI-02 | `rag.build_context` / `vdb.search` 内の span が存在しない | Phase 4 では外側の `rag-search` span でまとめて計測で十分 | 必要になったタイミングで追加 |
| RI-03 | `pyproject.toml` の `langfuse>=2.0.0` に上限バージョンを付けていない | 今回は v4 に対応済みだが、v5 での再発リスクがある | 別 Issue |

---

## 次の bolt への引き継ぎ

なし（bolt-0 で Phase 4 完了）

---

## 関連資料

**Requirements**
- `docs/design/phase4-requirements.md`

**Bolt Design**
- `docs/design/phase4-bolt-0.md`

**Code Review**
- `docs/review/phase4-bolt-0.md`

**Error Investigation**
- `docs/error/20260629-langfuse-trace-not-delivered.md`

---

## 関連コミット

（Commit 後に記入）

---

## 関連 PR

（PR 作成後に記入）
