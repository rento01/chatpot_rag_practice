# WorkLog: Phase 4 bolt-0

## サマリー

| 項目 | 内容 |
|---|---|
| 目的 | chat / index-document トレースに子 span を追加し、Langfuse でスパンツリーを確認できるようにする |
| 実施内容 | tracing.py: NoopSpan public 化・v4 API 対応 / main.py: rag-search span・llm-generation span 追加 / rag.py: extract・split・embed・upsert span 追加 / .env.example: 変数名修正・シークレット削除 |
| 変更ファイル | 4 ファイル（backend/tracing.py / backend/main.py / backend/rag.py / .env.example） |
| 動作確認 | 完了（Langfuse JP エンドポイントで span ツリー表示を確認）|
| AIレビュー | 完了（Request Changes → F-01/F-02 修正済み） |
| 課題 | RI-01: usage 記録（Phase 7 対応予定） / RI-02: search 内部 span（必要時追加） |
| 次の対応 | コミット・PR 作成 |

---

## 基本情報

### 実施日

2026-06-29

### 対応 Issue

#6

### bolt

bolt-0

### ブランチ

feature/6-phase4-bolt-0-langfuse-tracing

---

## 関連資料

**Requirements**
- `docs/design/phase4-requirements.md`

**Bolt Design**
- `docs/design/phase4-bolt-0.md`

**Code Review**（完了後に記入）
- `docs/review/phase4-bolt-0.md`

**Error Investigation**
- `docs/error/20260629-langfuse-trace-not-delivered.md`

---

## TODO・メモ

- [x] tracing.py: `_NoopSpan` → `NoopSpan` に rename
- [x] main.py: `_build_messages` に `trace_ctx` 追加・`rag-search` span 追加
- [x] main.py: `token_stream` 内で `_build_messages` を trace 内に移動・`llm-generation` generation 追加
- [x] main.py: `_index_document` で `rag.index_document` に `t` を渡す
- [x] rag.py: `index_document` に `trace_ctx` 追加・各ステップ span 追加
- [x] 動作確認: `LANGFUSE_*` 未設定でチャット・アップロードが正常動作すること
- [x] 動作確認: `LANGFUSE_*` 設定済みで span ツリーが表示されること（Langfuse JP エンドポイントで確認済み）
- [x] コードレビュー実施・F-01（シークレット漏洩）/ F-02（変数名不一致）修正済み

---

## 1. 作業目的

### 今回の目的

`backend/tracing.py` に既存の no-op ラッパを整備し、`backend/main.py` と `backend/rag.py` に Langfuse の子 span を追加する。これにより Langfuse ダッシュボードで `chat` と `index-document` のスパンツリーを確認できる状態にする。

### 完了条件

- Langfuse ダッシュボードで 1 件のチャットを span ツリーとして開ける（AC-01）
- `LANGFUSE_*` を空にしてもアプリは従来通り動く（AC-02）

---

## 2. Requirements 対応

### 対応項目

- R-01: `chat` トレース内に `rag-search` span と `llm-generation` generation を追加
- R-02: `index-document` トレース内に `extract` / `split` / `embed` / `upsert` span を追加
- R-03: `LANGFUSE_*` 未設定時は no-op として動作
- R-04: 既存トップレベルトレース構造を維持

### 完了判定

- AC-01: Langfuse ダッシュボードで span ツリーを確認できること → **達成**（JP エンドポイントで確認済み）
- AC-02: `LANGFUSE_*` 空でアプリが動くこと → **達成**（動作確認済み）

---

## 3. 実装前調査

### 確認したファイル

```
backend/tracing.py
backend/main.py
backend/rag.py
backend/config/settings.py
.env.example
pyproject.toml
docs/phaseSummary/phase3-3-summary.md
```

### 調査結果

- `tracing.py`: `trace()` Context Manager が実装済み。`_NoopSpan` が private のため他モジュールからは import できない
- `main.py`: `trace("chat")` と `trace("index-document")` のトップレベルトレースは既に存在。`_build_messages` は現在 trace の外で呼ばれている
- `rag.py`: `index_document` に trace_ctx 引数が存在しない。`tracing` モジュールを import していない
- `pyproject.toml`: `langfuse>=2.0.0` が依存に含まれており、インストール済み
- `settings.py`: `langfuse_secret_key` / `langfuse_public_key` / `langfuse_host` が既に定義済み

### 疑問点

- `token_stream` はジェネレータ関数のため `with trace(...)` 内で `yield` するが、Langfuse の flush タイミングに影響がないか → finally で flush されるため問題なし

---

## 4. 実装ログ

### 作業1: tracing.py — `_NoopSpan` を `NoopSpan` に public rename

**内容**

`_NoopSpan` を `NoopSpan` に rename し、他モジュール（`rag.py`）から import 可能にした。

**変更ファイル**

`backend/tracing.py`

**理由**

`rag.py` の `index_document` でデフォルト引数として `NoopSpan()` を使うために public 化が必要。

---

### 作業2: main.py — `_build_messages` に `trace_ctx` 追加・`rag-search` span 追加

**内容**

`_build_messages(req, trace_ctx=None)` の引数に `trace_ctx` を追加した。`use_rag=True` かつ `collection_id` が存在する場合に `trace_ctx.span("rag-search")` で RAG 検索を計測するようにした。

**変更ファイル**

`backend/main.py`

**理由**

RAG 検索の所要時間・ヒット有無を Langfuse で観測するため。

---

### 作業3: main.py — `token_stream` 内で `_build_messages` を trace 内に移動・`llm-generation` generation 追加

**内容**

`_build_messages(req)` の呼び出しを `chat` 関数アウタースコープから `token_stream` 内の `with trace("chat", ...) as t:` ブロック内に移動した。`_build_messages(req, t)` として trace context を渡す形に変更した。また、LLM ストリーム前後に `t.generation("llm-generation")` を追加した。

**変更ファイル**

`backend/main.py`

**理由**

`rag-search` span を `chat` trace の子として紐づけるために、メッセージ構築を trace コンテキスト内に移動する必要があった。

---

### 作業4: main.py — `_index_document` で trace context を `rag.index_document` に渡す

**内容**

`with trace("index-document", ...) as t:` で得られる `t` を `rag.index_document(collection_id, document_id, file_data, t)` に渡すよう変更した。

**変更ファイル**

`backend/main.py`

**理由**

`rag.py` 内の span を `index-document` trace の子として紐づけるため。

---

### 作業5: rag.py — `index_document` に `trace_ctx` 追加・各ステップに span 追加

**内容**

`index_document(collection_id, document_id, file_data, trace_ctx=None)` に引数を追加した。関数先頭で `ctx = trace_ctx if trace_ctx is not None else NoopSpan()` として no-op フォールバックを確保した。各処理ステップ（extract / split / embed / upsert）に span を追加した。

**変更ファイル**

`backend/rag.py`

**理由**

インデックス取り込みの各ステップ（テキスト抽出・チャンク分割・embedding 生成・upsert）を個別に可視化するため。

---

## 5. Diff Review

### 実施コマンド

```bash
git diff --stat
git diff
```

### 変更ファイル一覧

- `backend/tracing.py`（+10 行 / -7 行）
- `backend/main.py`（+34 行 / -14 行）
- `backend/rag.py`（+24 行 / -1 行）

### ファイル別の変更内容

`backend/tracing.py`

- `_NoopSpan` を `NoopSpan` に rename（public 化）
- `span()` / `generation()` の戻り値を `return self` から `return NoopSpan()` に変更（新しいインスタンスを返す。本物の Langfuse の動作に合わせるため）
- `trace()` 内の `yield _NoopSpan()` を `yield NoopSpan()` に変更

`backend/main.py`

- `from backend.tracing import NoopSpan, trace` に変更
- `_index_document`: `with trace(...) as t:` で trace context を取得し、`rag.index_document(..., t)` に渡す
- `_build_messages`: `trace_ctx=None` 引数を追加。`use_rag=True` 時に `ctx_span.span("rag-search")` で検索を記録
- `chat` / `token_stream`: `messages = _build_messages(req)` を trace の外から削除し、`token_stream` の `with trace(...) as t:` 内で `_build_messages(req, t)` を呼ぶ形に変更。ストリーム前後に `t.generation("llm-generation")` / `gen.end()` を追加

`backend/rag.py`

- `from backend.tracing import NoopSpan` を追加
- `index_document`: `trace_ctx: object | None = None` 引数を追加
- 関数先頭で `ctx = trace_ctx if trace_ctx is not None else NoopSpan()` としてフォールバック
- `extract_text` 前後に `ctx.span("extract")` / `.end({"page_count": ...})`
- `split_into_chunks` 前後に `ctx.span("split")` / `.end({"chunk_count": ...})`
- `embed` 前後に `ctx.span("embed")` / `.end({"status": "ok"|"failed"})`
- `vdb.upsert` 前後に `ctx.span("upsert")` / `.end({"chunk_count": ...})`

### 変更コード（抜粋）

**tracing.py: NoopSpan の public 化**

変更前:
```python
class _NoopSpan:
    def span(self, **kwargs: Any) -> "_NoopSpan":
        return self
    def generation(self, **kwargs: Any) -> "_NoopSpan":
        return self
```

変更後:
```python
class NoopSpan:
    def span(self, **kwargs: Any) -> "NoopSpan":
        return NoopSpan()
    def generation(self, **kwargs: Any) -> "NoopSpan":
        return NoopSpan()
```

**rag.py: index_document に span を追加**

変更前:
```python
def index_document(collection_id: int, document_id: int, file_data: bytes) -> int:
    text, page_count = extract_text(file_data)
    chunks = split_into_chunks(text)
    if chunks:
        try:
            embeddings = get_embed_model().embed(chunks)
        except Exception:
            embeddings = [None] * len(chunks)
        vdb.upsert(...)
    return page_count
```

変更後:
```python
def index_document(collection_id, document_id, file_data, trace_ctx=None) -> int:
    ctx = trace_ctx if trace_ctx is not None else NoopSpan()
    s_extract = ctx.span(name="extract", input={"file_size": len(file_data)})
    text, page_count = extract_text(file_data)
    s_extract.end(output={"page_count": page_count})
    s_split = ctx.span(name="split", input={"text_length": len(text)})
    chunks = split_into_chunks(text)
    s_split.end(output={"chunk_count": len(chunks)})
    if chunks:
        s_embed = ctx.span(name="embed", input={"chunk_count": len(chunks)})
        try:
            embeddings = get_embed_model().embed(chunks)
            s_embed.end(output={"status": "ok"})
        except Exception:
            s_embed.end(output={"status": "failed"})
            embeddings = [None] * len(chunks)
        s_upsert = ctx.span(name="upsert", input={"chunk_count": len(chunks)})
        vdb.upsert(...)
        s_upsert.end(output={"chunk_count": len(chunks)})
    return page_count
```

**main.py: token_stream の restructure**

変更前:
```python
messages = _build_messages(req)  # trace の外

async def token_stream():
    with trace("chat", ...) :
        async for chunk in chat_model.stream(messages):
            yield chunk
```

変更後:
```python
async def token_stream():
    with trace("chat", ...) as t:
        messages = _build_messages(req, t)  # trace の中に移動
        gen = t.generation(name="llm-generation", model=...)
        async for chunk in chat_model.stream(messages):
            yield chunk
        gen.end(output="".join(collected))
```

### 意図した変更

- `NoopSpan` public 化（`rag.py` から import するため）
- `rag-search` span 追加
- `llm-generation` generation 追加
- `extract` / `split` / `embed` / `upsert` span 追加

### 意図していない変更がないか

- `.env` や秘密情報: なし
- 不要なコメント・デバッグコード: なし
- 関係ないファイルの変更: なし

### 削除した処理

- `messages = _build_messages(req)` を `chat` アウタースコープから削除（`token_stream` 内に移動）

### 差分メモ

- `NoopSpan.span()` を `return self` から `return NoopSpan()` に変更した。本物の Langfuse では `span()` が異なるオブジェクトを返すため、noop も同じ構造にした
- `_build_messages` 内のローカル変数名 `ctx` が `rag.build_context()` の戻り値（`RagContext`）と名前が衝突するため、`rag_ctx` に変更した

### リスク・未確認事項

- `LANGFUSE_*` 設定済みの場合のスパンツリー確認はユーザーが実施する（クレデンシャルがないため Claude では確認不可）
- `token_stream` は async generator のため、例外発生時に `gen.end()` が呼ばれない可能性がある。ただし Langfuse 側でタイムアウト扱いになるだけで、アプリへの影響はない

---

## 6. エラー対応ログ

詳細は `docs/error/20260629-langfuse-trace-not-delivered.md` を参照。

### エラー1: AttributeError — Langfuse SDK v4 の破壊的 API 変更

**現象**: チャット送信時に `AttributeError: 'Langfuse' object has no attribute 'trace'` でクラッシュ

**原因**: `pyproject.toml` の `langfuse>=2.0.0` という上限なし指定により SDK v4.10.0 がインストールされていた。v4 では `.trace()` / `.span()` / `.generation()` が廃止され、`start_as_current_observation()` ベースの OTel API に移行している。

**対応**: `tracing.py` を v4 の `start_as_current_observation()` API に全面書き換え。`main.py` / `rag.py` も `trace_ctx` 引き回しから OTel コンテキスト自動管理方式に変更。

---

### エラー2: 401 Unauthorized — JP/US エンドポイント不一致

**現象**: `ERROR [opentelemetry.exporter.otlp.proto.http.trace_exporter] Failed to export span batch code: 401, reason: Unauthorized`

**原因**: ユーザーの Langfuse プロジェクトは JP サーバーにあるが、`.env` の `LANGFUSE_HOST` が US（`https://cloud.langfuse.com`）のデフォルト値のまま。また `tracing.py` が当初 `Langfuse()` を引数なしで呼んでいたため `settings.langfuse_host` が使われていなかった。

**対応**: `Langfuse()` に `host=settings.langfuse_host` を明示渡しするよう修正。`.env` の `LANGFUSE_HOST` を `https://jp.cloud.langfuse.com` に設定。

---

### エラー3: コード変更がコンテナに反映されない

**現象**: `--force-recreate` / `--build` 後も古いコードで動作していた

**原因**: backend はコードをイメージに焼き込む構成。`docker compose up -d --build` がコンテナを差し替えないケースがあった。

**対応**: `docker compose stop backend && docker compose up -d backend` の 2 ステップで確実に反映。

---

## 7. Claude Code 活用ログ

### 判断1: `_NoopSpan` の public 化方針

**質問内容**

`_NoopSpan` を他モジュールから使えるようにするため、rename / module-level singleton / export 関数のどれが適切か

**回答要約**

`NoopSpan` に rename して public 化する方法が最もシンプルで教材としての可読性が高い

**採用判断**

採用

**判断理由**

`noop_span = _NoopSpan()` のようなシングルトンよりも、クラスを直接 import する方がコードの意図が明確

---

### 判断2: `_build_messages` の trace 内への移動

**質問内容**

`rag-search` span を `chat` trace の子にするために、`_build_messages` を `token_stream` の trace コンテキスト内に移動することの是非

**回答要約**

移動すべき。ユーザーメッセージ保存（`db.add`）は `db` セッションが必要なため `chat` アウタースコープに残す。`_build_messages` 呼び出しのみを移動すれば済む

**採用判断**

採用

**判断理由**

`_build_messages` の呼び出しを trace 内に移動するだけで span ツリーが正しく形成できる。`db` セッションは外側に残るため影響なし

---

## 8. 動作確認

| ID | 確認内容 | 結果 |
|---|---|---|
| T-01 | `LANGFUSE_*` 未設定でチャットが正常ストリームされること | OK |
| T-02 | `LANGFUSE_*` 未設定でドキュメントアップロード → `ready` になること | OK |
| T-03 | `LANGFUSE_*` 設定済みで Langfuse ダッシュボードに span ツリーが表示されること | OK（JP エンドポイントで `chat` → `rag-search` / `llm-generation` を確認） |

---

## 9. 作業振り返り

### 設計と実装の乖離

設計時は Langfuse v3 の `trace_ctx` 引き回し方式を想定していたが、SDK v4 の破壊的変更により OTel コンテキスト伝播方式に変更した。結果として、`trace_ctx` 引数が不要になり関数シグネチャがよりシンプルになった。

### 今後への教訓

- 依存ライブラリにメジャーバージョン上限を付ける（`langfuse>=2.0.0,<5.0.0`）ことで破壊的変更を防げる
- `.env.example` は必ずプレースホルダー値で管理する
- Docker イメージ焼き込み構成では `stop` → `up -d` の 2 ステップを確認手順に明記する

---

## 関連ドキュメント

- Requirements: `docs/design/phase4-requirements.md`
- Bolt Design: `docs/design/phase4-bolt-0.md`
- TaskLog（完了後）: `docs/taskLog/phase4-bolt-0.md`
