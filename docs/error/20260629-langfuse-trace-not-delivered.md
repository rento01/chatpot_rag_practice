# Langfuse トレースが届かない・チャットがクラッシュする

## 発生日

2026-06-29

---

## Summary

Phase 4（Langfuse 導入）の実装・動作確認中に、以下の 3 つの問題が連続して発生した。

1. チャット送信時に `AttributeError: 'Langfuse' object has no attribute 'trace'` でクラッシュ
2. エラー解消後もトレースが Langfuse ダッシュボードに届かない（`401 Unauthorized`）
3. コードを修正しても変更がコンテナに反映されない

いずれも解消し、最終的に Langfuse JP エンドポイントへのトレース送信を確認した。

---

## Impact

**ユーザー影響**

- 問題 1: チャット送信が全件 500 エラーになりレスポンスが返らない
- 問題 2・3: アプリは動作するがトレースが届かない

**システム影響**

- 問題 1: `token_stream` ジェネレータ内で未捕捉例外が発生し、ストリームが中断される

**回避策**

- 問題 1: `LANGFUSE_SECRET_KEY` / `LANGFUSE_PUBLIC_KEY` を空にすれば no-op で動作する
- 問題 2・3: なし（設定・ビルド手順が前提）

---

## Investigation

### 調査手順

1. `docker compose logs backend 2>&1 | tail -50` でエラーの種類を特定
2. `docker compose exec backend python -c "import langfuse; print(langfuse.__version__)"` で SDK バージョンを確認
3. `docker compose exec backend python -c "from langfuse import Langfuse; print(dir(Langfuse()))"` で利用可能メソッドを確認
4. `docker compose exec backend env | grep LANGFUSE` でコンテナ内の環境変数を確認
5. `docker compose logs --since 60s backend 2>&1 | grep -v 'GET /health'` でチャット後のログを確認

### 調査環境

- OS: macOS Darwin 24.5.0
- Docker: Docker Desktop（Mac）
- Backend: Python 3.12 / FastAPI / uvicorn
- Langfuse SDK: 4.10.0（インストール済み）

---

## Findings

### 問題 1: AttributeError — SDK v4 の破壊的 API 変更

`pyproject.toml` の依存は `langfuse>=2.0.0` と緩く指定されており、v4.10.0 がインストールされていた。

v4 で以下のメソッドが廃止された:

| 廃止 API（v3 以前） | 代替（v4） |
|---|---|
| `Langfuse().trace()` | `Langfuse().start_as_current_observation(as_type="span")` |
| `trace.span()` | OTel コンテキストで自動管理（モジュールレベル関数） |
| `trace.generation()` | `start_as_current_observation(as_type="generation")` |

`tracing.py` が v3 API を前提に書かれており、v4 環境で動作しなかった。

### 問題 2: 401 Unauthorized — エンドポイント不一致

- ユーザーの Langfuse プロジェクトは JP サーバー（`https://jp.cloud.langfuse.com`）に作成されていた
- `.env` の `LANGFUSE_HOST` は US エンドポイント（`https://cloud.langfuse.com`）がデフォルト
- `docker-compose.yml` の定義: `LANGFUSE_HOST: ${LANGFUSE_HOST:-https://cloud.langfuse.com}`
- US エンドポイントに JP のキーを送信したため 401 が返った

また、`.env.example` の `LANGFUSE_BASE_URL`（Langfuse SDK が認識しない変数名）と `settings.py` の `LANGFUSE_HOST` で変数名が不一致だった。さらに `tracing.py` が `Langfuse()` を引数なしで呼んでいたため、`settings.langfuse_host` の値がトレースに使われていなかった。

### 問題 3: コード変更がコンテナに反映されない

- backend はコードをイメージに焼き込む構成（`build: .`、volume mount なし）
- `docker compose up -d --force-recreate backend` はイメージを再ビルドしない
- `--build` フラグでビルドしても、Docker がコンテナを差し替えないケースがあった
- `stop` → `up -d` の 2 ステップで確実に反映された

---

## Evidence

### コマンド

```bash
# エラーログ確認
docker compose logs backend 2>&1 | tail -50

# SDK バージョン確認
docker compose exec backend python -c "import langfuse; print(langfuse.__version__)"

# 利用可能 API 確認
docker compose exec backend python -c "from langfuse import Langfuse; print(dir(Langfuse()))"

# 環境変数確認
docker compose exec backend env | grep LANGFUSE

# チャット後のログ確認
docker compose logs --since 60s backend 2>&1 | grep -v "GET /health"

# コード反映の確認
docker compose exec backend grep -n "start_as_current_observation" /app/backend/tracing.py
```

### ログ

```
# 問題 1
AttributeError: 'Langfuse' object has no attribute 'trace'
  File "/app/backend/tracing.py", line 61, in trace
    t = _langfuse.trace(name=name, **kwargs)

# 問題 2
ERROR [opentelemetry.exporter.otlp.proto.http.trace_exporter]
Failed to export span batch code: 401, reason: Unauthorized
```

### SDK v4 の利用可能メソッド（抜粋）

```
['auth_check', 'create_dataset', 'create_prompt', 'create_score',
 'flush', 'get_current_observation_id', 'get_current_trace_id',
 'start_as_current_observation', 'start_observation',
 'score_current_span', 'score_current_trace',
 'update_current_generation', 'update_current_span', ...]
```

`.trace()` / `.span()` / `.generation()` は存在しない。

---

## Root Cause Candidates

### 主要候補

- **問題 1**: `pyproject.toml` の `langfuse>=2.0.0` という緩い上限なし指定により、v3 前提のコードが v4 環境で動作しなくなったと考えられる
- **問題 2**: `docker-compose.yml` の `LANGFUSE_HOST` デフォルトが US エンドポイントであり、JP プロジェクトのユーザーが明示設定しない限り 401 になる可能性がある
- **問題 3**: `docker compose up -d --build` が常にコンテナを差し替えるとは限らない仕様と考えられる

### 副次的懸念点

- `.env.example` の `LANGFUSE_BASE_URL` という変数名が `settings.py` の `LANGFUSE_HOST` と一致しておらず混乱を招く
- `tracing.py` が `Langfuse()` を引数なしで初期化しており、`settings.langfuse_host` が使われない状態だった（v3 時点での設計上の問題）

---

## Recommended Actions

### A. `pyproject.toml` に Langfuse SDK の上限バージョンを指定する

**内容**

`langfuse>=2.0.0,<5.0.0` のように上限を設ける

**メリット**

メジャーバージョンアップによる破壊的変更を自動的に吸収してしまうリスクを下げられる

**デメリット**

手動でのバージョン追従が必要になる

**影響範囲**

`pyproject.toml` / `uv.lock`

---

### B. `.env.example` の `LANGFUSE_BASE_URL` を `LANGFUSE_HOST` に統一する

**内容**

`.env.example` 内の変数名を `settings.py` と `docker-compose.yml` に合わせて `LANGFUSE_HOST` に変更する

**メリット**

学習者が `.env.example` を見て `.env` を設定する際に変数名の不一致で混乱しない

**デメリット**

なし

**影響範囲**

`.env.example` のみ

---

### C. `docker-compose.yml` の `LANGFUSE_HOST` デフォルトにコメントを追加する

**内容**

JP リージョンを使う場合の設定例をコメントで記載する

```yaml
# JP リージョンの場合: https://jp.cloud.langfuse.com
LANGFUSE_HOST: ${LANGFUSE_HOST:-https://cloud.langfuse.com}
```

**メリット**

JP ユーザーが 401 で詰まるリスクを下げられる

**デメリット**

なし

**影響範囲**

`docker-compose.yml` のみ

---

## Open Questions

1. Langfuse SDK v4 への完全対応（`start_as_current_observation` ベース）で教材として意図したトレース粒度が実現できているか、ダッシュボードで継続確認が必要

---

## Conclusion

3 つの問題はそれぞれ独立した原因を持つが、連鎖的に発生した。

- 問題 1（クラッシュ）: Langfuse SDK v4 の破壊的 API 変更。`tracing.py` を v4 の `start_as_current_observation` ベースに書き換えて解消
- 問題 2（401）: JP プロジェクトに US エンドポイントのキーを送っていた。`.env` の `LANGFUSE_HOST` を `https://jp.cloud.langfuse.com` に変更して解消
- 問題 3（反映されない）: イメージ焼き込み構成での再起動手順の誤解。`--build` 後に `stop` → `up -d` で解消

最終的に Langfuse JP エンドポイントへのトレース送信（span ツリー表示）を確認済み。

---

## Related Files

- `backend/tracing.py` — v4 API 対応済み
- `backend/main.py` — `span()` / `generation()` モジュールレベル関数を使う形に変更
- `backend/rag.py` — 同上
- `docker-compose.yml` — `LANGFUSE_HOST` のデフォルト定義

---

## Related Issues

- Issue #6: Phase 4: Langfuse でトレースを取る
