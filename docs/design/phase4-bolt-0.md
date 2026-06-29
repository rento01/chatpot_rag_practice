# Phase 4 bolt-0 設計

## Design Summary

| 項目 | 内容 |
|---|---|
| Phase | Phase 4 |
| Bolt | bolt-0 |
| Issue | #6 |
| 目的 | chat / index-document トレースに子 span を追加し、Langfuse でスパンツリーを確認できるようにする |
| 作るもの | `tracing.py` 整備・`main.py` span 追加・`rag.py` span 追加 |
| 作らないもの | Langfuse self-host / 評価スコア / `vdb.search` 内部の span |
| 完了条件 | AC-01・AC-02 を満たす |
| 次 Bolt | なし（Phase 4 完了） |

---

## Requirements Summary

### 対応対象

- R-01: `chat` トレース内に `rag-search` span / `llm-generation` generation を追加
- R-02: `index-document` トレース内に `extract` / `split` / `embed` / `upsert` span を追加
- R-03: `LANGFUSE_*` 未設定時は全 span が no-op として動作
- R-04: 既存トップレベルトレース構造を維持

### 対応対象外

- O-01〜O-05: Langfuse self-host / 評価スコア / カスタムダッシュボード / `vdb.search` 内部 / Cloud プロジェクト作成

---

## bolt 分割判定

**判定**: 分割不要（bolt-0 のみで対応）

**理由**:
- 変更ファイルは 3 ファイル（`tracing.py` / `main.py` / `rag.py`）
- 変更量は約 50〜70 行程度（span の追加のみ）
- すべての変更は「子 span を追加する」という単一目的に収束する

---

## データフロー

### chat トレース（実装後）

```
POST /chat
  └─ token_stream()
       └─ trace("chat") as t
            ├─ _build_messages(req, t)
            │    └─ t.span("rag-search")     [use_rag=True 時のみ]
            │         input : query, collection_id
            │         output: has_hits
            └─ t.generation("llm-generation")
                 model  : ollama_chat_model
                 output : "".join(collected)
```

### index-document トレース（実装後）

```
_index_document(document_id, collection_id, file_data)
  └─ trace("index-document") as t
       └─ rag.index_document(..., t)
            ├─ t.span("extract")
            │    output: page_count
            ├─ t.span("split")
            │    output: chunk_count
            ├─ t.span("embed")   [chunks が存在する場合のみ]
            │    output: status("ok" or "failed")
            └─ t.span("upsert")  [chunks が存在する場合のみ]
                 output: chunk_count
```

---

## 影響範囲

### 対象

| ファイル | 変更内容 |
|---|---|
| `backend/tracing.py` | `_NoopSpan` を `NoopSpan`（public）に rename して他モジュールから import 可能にする |
| `backend/main.py` | `_build_messages` に `trace_ctx` 引数追加・`token_stream` 内で `_build_messages` を trace 内に移動・`llm-generation` generation 追加・`_index_document` から `rag.index_document` に `t` を渡す |
| `backend/rag.py` | `index_document` に `trace_ctx` 引数追加・各処理ステップに span を追加 |

### 影響なし

- `backend/vector_db/chroma.py`（変更なし）
- `backend/llm/ollama.py`（変更なし）
- `backend/schemas.py` / `backend/dataModels.py`（変更なし）
- フロントエンド（変更なし）

---

## bolt-0: Langfuse span 追加

### 目的

既存の `trace("chat")` / `trace("index-document")` トップレベルトレースに子 span を追加し、Langfuse ダッシュボードでスパンツリーとして観測できる状態にする。

---

### 作るもの

> **注意**: 設計時の実装方針（`trace_ctx` 引き回し方式）から、実装中に発覚した Langfuse SDK v4 の破壊的 API 変更により OTel コンテキスト伝播方式へ変更した。詳細は「[設計変更履歴](#設計変更履歴)」を参照。

1. **`backend/tracing.py`**: `_NoopSpan` → `NoopSpan` に rename（public）し、v4 API（`start_as_current_observation`）ベースの `trace()` / `span()` / `generation()` を実装
2. **`backend/main.py`**:
   - `from backend.tracing import generation, span, trace` に import を変更
   - `_build_messages` 内でモジュールレベルの `span("rag-search")` を呼ぶ（OTel コンテキスト経由で自動的に親 trace の子になる）
   - `token_stream` 内: `with trace("chat", ...)` の中で `_build_messages(req)` を呼び、`with generation("llm-generation") as gen:` で LLM ストリームを計測
   - `_index_document` 内: `with trace("index-document", ...):` の中で `rag.index_document(...)` を呼ぶ（`trace_ctx` 引数は不要）
3. **`backend/rag.py`**:
   - `from backend.tracing import span as tracing_span` を追加
   - `index_document` の引数は変更しない（`trace_ctx` 引き回し不要）
   - 各処理ステップを `with tracing_span(name="...", input=...) as s:` / `s.update(output=...)` で計測

---

### 作らないもの

- Langfuse self-host（`docker-compose.yml` への langfuse サービス追加）→ ユーザーが Cloud で設定
- 評価スコア（`langfuse.score()`）→ Phase 8（RAGAS）で検討
- `vdb.search` / `rag.build_context` 内部への span → `_build_messages` の `rag-search` span でまとめて計測
- `LANGFUSE_HOST` の自動判定ロジック変更
- generation の `usage`（input_tokens / output_tokens）→ Ollama の場合トークン数取得が困難なため見送り

---

### 対象ファイル・修正箇所

> 「設計時」は設計書作成時の計画、「実装時」は SDK v4 対応後の実際の実装を示す。

| ファイル | 修正対象 | 設計時 | 実装時 | 変更理由 |
|---|---|---|---|---|
| `backend/tracing.py` | `_NoopSpan` クラス名 | `NoopSpan` に rename | 同左（変更なし） | `rag.py` から import するために public 化 |
| `backend/tracing.py` | `trace()` 実装 | v3 API（`.trace()` 呼び出し） | v4 API（`start_as_current_observation(as_type="span")`） | SDK v4 で `.trace()` 廃止 |
| `backend/tracing.py` | `span()` / `generation()` | `trace_ctx` に委譲（`ctx.span()`） | モジュールレベルのコンテキストマネージャ | OTel コンテキスト伝播方式に変更 |
| `backend/tracing.py` | `NoopSpan` のメソッド | `.span()` / `.generation()` / `.end()` | `.update()` / `.end()` のみ | v4 の observation オブジェクトに合わせた |
| `backend/main.py` | `_build_messages` シグネチャ | `trace_ctx=None` 引数追加 | 引数変更なし（OTel で自動伝播） | `trace_ctx` 引き回し不要 |
| `backend/main.py` | `_build_messages` 内 | `trace_ctx.span("rag-search")` | モジュールレベル `span("rag-search")` | OTel コンテキスト伝播方式に変更 |
| `backend/main.py` | `token_stream` 内 | `trace(...) as t` → `t.generation(...)` | `trace(...)` + `generation(...)` を別々に呼ぶ | OTel コンテキスト伝播方式に変更 |
| `backend/main.py` | `_index_document` 内 | `rag.index_document(..., t)` で `t` を渡す | `rag.index_document(...)` のみ（引数なし） | `trace_ctx` 引き回し不要 |
| `backend/rag.py` | import 文 | `from backend.tracing import NoopSpan` | `from backend.tracing import span as tracing_span` | モジュールレベル関数を使う方式に変更 |
| `backend/rag.py` | `index_document` シグネチャ | `trace_ctx=None` 引数追加 | 引数変更なし | `trace_ctx` 引き回し不要 |
| `backend/rag.py` | `index_document` 本体 | `ctx.span(...)` / `.end(...)` | `with tracing_span(...) as s:` / `s.update(...)` | コンテキストマネージャ方式に統一 |

---

### 実装方針

> 「設計時の方針」と「実際の実装方針」を併記する。変更理由は「[設計変更履歴](#設計変更履歴)」に詳細がある。

#### 設計時の方針（`trace_ctx` 引き回し方式）

`trace()` が yield するオブジェクト（`StatefulTraceClient` または `NoopSpan`）に `.span()` / `.generation()` / `.end()` を持たせ、呼び出し元から trace context を引き回す。

```python
# 設計時の呼び出しイメージ
with trace("chat", ...) as t:
    s = t.span(name="rag-search", input={"query": q})
    result = do_search(q)
    s.end(output={"has_hits": result.has_hits})
    gen = t.generation(name="llm-generation", ...)
```

#### 実際の実装方針（OTel コンテキスト伝播方式）

Langfuse SDK v4 が OTel ベースに変わったため、親子関係の管理をモジュールレベルのコンテキストマネージャに委ねる。`trace_ctx` を引き回さなくてよいため、関数シグネチャが変わらずシンプルになった。

```python
# 実際の実装（main.py）
with trace("chat", ...):
    messages = _build_messages(req)   # 内部で span("rag-search") を呼ぶ
    with generation(name="llm-generation", ...) as gen:
        async for chunk in chat_model.stream(messages):
            yield chunk
        gen.update(output="".join(collected))

# 実際の実装（_build_messages 内）
with span(name="rag-search", input={...}) as s:
    rag_ctx = rag.build_context(last_user, req.collection_id)
    s.update(output={"has_hits": rag_ctx.has_hits})

# 実際の実装（rag.py）
with tracing_span(name="extract", input={...}) as s_extract:
    text, page_count = extract_text(file_data)
    s_extract.update(output={"page_count": page_count})
```

**`token_stream` の `_build_messages` 移動**（設計時・実装時共通）

`_build_messages` を `trace("chat")` コンテキスト内で呼ぶ。ユーザーメッセージの保存（`db.add(dm.Message(...))`）は `db` セッションが必要なため、trace の外（`chat` 関数のアウタースコープ）に残す。

---

### テスト観点

| ID | 内容 |
|---|---|
| T-01 | `LANGFUSE_*` 未設定でチャットが正常にストリームされること |
| T-02 | `LANGFUSE_*` 未設定でドキュメントアップロード → ステータス `ready` になること |
| T-03 | `LANGFUSE_*` 設定済みで Langfuse ダッシュボードに `chat` トレースが span ツリーとして表示されること（rag-search / llm-generation が子 span として見えること） |
| T-04 | `use_rag=False` の場合、`rag-search` span が存在しないこと |

---

### 設計判断

| 項目 | 判断 | 理由 | 代替案 |
|---|---|---|---|
| `_NoopSpan` を public rename | `NoopSpan` に rename | `rag.py` からも使えるようにするために必要。教材としても明快 | module-level singleton `noop_span = _NoopSpan()` を export するだけで rename しない案もある |
| `_build_messages` を trace 内に移動 | 移動する | `rag-search` span を `chat` trace の子にするために必要。構造的にも自然 | 移動せず `rag.build_context` 内で独立した trace を作る案もあるが、span ツリーにならない |
| generation の `usage` を記録しない | 見送り | Ollama はストリーム時にトークン数を返さない。Langfuse の `usage` フィールドへの記録が困難 | Bedrock 移行（Phase 7）後に追加する |
| 1 bolt で全ファイル対応 | 1 bolt | 変更量が小さく（~60 行）、3 ファイルの変更が相互依存しているため分割すると片方が動作しない | bolt-0（main.py）/ bolt-1（rag.py）に分割する案もあるが、PR が 2 つになると確認コストが増える |
| `trace_ctx` 引き回し → OTel 方式へ変更（実装中判断） | OTel 方式を採用 | Langfuse SDK v4 で `trace_ctx.span()` が廃止。OTel 方式の方が関数シグネチャを変えなくて済むためよりシンプル | v3 互換 SDK を固定バージョンでインストールする案もあるが、教材として新 API に対応する方が長期的に有益 |

---

### 設計変更履歴

#### 変更概要

設計時は「`trace_ctx` を `main.py` → `rag.py` へ引数で引き回す」方式で実装を計画していた。しかし実装中に以下の問題が発覚し、OTel コンテキスト伝播方式に変更した。

#### 変更理由

`pyproject.toml` の `langfuse>=2.0.0` という上限なし指定により、Langfuse SDK v4.10.0 がインストールされていた。v4 では以下の API が廃止されており、設計書どおりに実装するとランタイムエラーになった。

| 廃止 API（v3 以前） | 代替（v4） |
|---|---|
| `Langfuse().trace()` | `Langfuse().start_as_current_observation(as_type="span")` |
| `trace_obj.span()` | OTel コンテキスト管理（モジュールレベル関数） |
| `trace_obj.generation()` | `start_as_current_observation(as_type="generation")` |

エラー詳細: `docs/error/20260629-langfuse-trace-not-delivered.md`

#### 設計変更の影響

| 設計要素 | 変更前（設計時） | 変更後（実装時） |
|---|---|---|
| 親子 span の管理 | `trace_ctx` を引数で引き回す | OTel コンテキストが自動管理 |
| `_build_messages` シグネチャ | `trace_ctx=None` 引数追加 | 変更なし |
| `index_document` シグネチャ | `trace_ctx=None` 引数追加 | 変更なし |
| `rag.py` の import | `from backend.tracing import NoopSpan` | `from backend.tracing import span as tracing_span` |
| span の開始/終了 | `s = ctx.span(...)` / `s.end(...)` | `with tracing_span(...) as s:` / `s.update(...)` |
| `NoopSpan` のメソッド | `.span()` / `.generation()` / `.end()` | `.update()` / `.end()` のみ |

#### 結果として得られたメリット

- `trace_ctx` を引数で引き回す必要がなくなり、関数シグネチャが変わらずシンプルになった
- 呼び出し元から Langfuse の有無を意識しなくてよい（`tracing.py` の `_init()` で透過的に処理）
- OTel は Langfuse 以外のオブザーバビリティツールとも互換性があり、将来の拡張性が高い

---

### 完了条件

**Functional**

- `chat` トレース内に `rag-search` span（use_rag=True 時）と `llm-generation` generation が存在する
- `index-document` トレース内に `extract` / `split` / `embed` / `upsert` span が存在する
- `LANGFUSE_*` 未設定時に全 span が no-op として動作する

**Verification**

- `LANGFUSE_*` を空にした状態でチャット・ドキュメントアップロードが正常動作すること（T-01 / T-02）
- `LANGFUSE_*` 設定済みで Langfuse ダッシュボードに span ツリーが表示されること（T-03）
- `use_rag=False` 時に `rag-search` span が不要（T-04）

---

### 懸念事項

| 項目 | 内容 | 対応方針 |
|---|---|---|
| `token_stream` はジェネレータ | `with trace(...)` 内で `yield` するため span の終了タイミングが遅延する | `gen.end(output=...)` をストリーム完了直後（`yield` の後）に書けば正確なタイミングで記録できる |
| `_build_messages` の移動 | `messages = _build_messages(req)` が `chat` アウタースコープからなくなる | ユーザーメッセージ保存・会話バリデーションは引き続き `chat` 内（`db` のスコープ内）で行うため、移動は `_build_messages` 呼び出しのみ |

---

### Remaining Issues

| ID | 内容 | 対応予定 | 再検討条件 |
|---|---|---|---|
| RI-01 | generation の `usage`（input_tokens / output_tokens）が記録できない | Phase 7（Bedrock 移行）後 | Bedrock では usage が取れるため、そのタイミングで追加する |
| RI-02 | `rag.build_context` / `vdb.search` 内の span が存在しない | Future | 検索品質の詳細デバッグが必要になったタイミングで追加する |

---

### 確認事項・決定事項

| 項目 | 内容 |
|---|---|
| 確認事項 | Langfuse Cloud のプロジェクト作成・API キー取得はユーザー自身が行う前提でよいか |
| 決定事項 | よい（Issue #6 の方針に従う） |
| 理由 | クレデンシャルはコードに含めず `.env` で管理。セットアップ手順は教材の学習ポイントの一部 |
| 対応方針 | `.env.example` の `LANGFUSE_SECRET_KEY` / `LANGFUSE_PUBLIC_KEY` を設定するだけで動く |

---

### ドキュメント更新

| ドキュメント | 更新内容 |
|---|---|
| なし | API 仕様・設定値に変更なし。span 追加のみのため既存ドキュメントへの影響なし |

---

### 次の bolt への引き継ぎ

なし（bolt-0 で Phase 4 完了）

---

## References

### Requirements

- `docs/design/phase4-requirements.md`

### Error Investigation

- `docs/error/20260629-langfuse-trace-not-delivered.md` — SDK v4 破壊的変更・401 Unauthorized・コンテナ未反映の調査記録

### Related Issues

- GitHub Issue #6: Phase 4: Langfuse でトレースを取る
