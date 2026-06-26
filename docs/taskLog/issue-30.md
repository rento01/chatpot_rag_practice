# Issue #30 — バックエンドの起動後ログが docker compose logs に出力されない

## サマリー

| 項目 | 内容 |
|---|---|
| 目的 | FastAPI 起動後のログが `docker compose logs` に出力されない問題を修正する |
| 実施内容 | alembic fileConfig 修正・logging_config.py 修正・main.py lifespan でレベル復元 |
| 変更ファイル | 3 ファイル（`alembic/env.py`・`backend/logging_config.py`・`backend/main.py`） |
| 動作確認 | PASS（AC-01〜04 全件確認済み） |
| AIレビュー | Approve（Blocker: 0 / Important: 1 / Suggestions: 1） |
| 課題 | uvicorn ロガーへのレベル設定タイミング（実害軽微） |
| 次の対応 | Commit → Push → PR 作成 |

---

## 基本情報

### 実施日

2026-06-26〜2026-06-27

### 対応 Issue

#30

### bolt

なし（通常 Issue 対応）

---

## 目的

FastAPI（uvicorn）起動後に `docker compose logs backend` でログが出力されない問題を修正する。

Issue #30 の完了条件：
- `docker compose logs` で Alembic ログ・HTTP アクセスログ・アプリログが確認できる
- `LOG_LEVEL` 環境変数でログレベルを切り替えられる

---

## Requirements 対応

### 対応項目

* R-01: docker compose logs でバックエンドのログが確認できること
* R-02: LOG_LEVEL 環境変数でログレベルを切り替えられること

### 完了判定

* AC-01: Alembic ログが出力される → PASS
* AC-02: HTTP アクセスログが出力される → PASS
* AC-03: `docker compose logs -f` でリアルタイム確認できる → PASS
* AC-04: `LOG_LEVEL=DEBUG` で DEBUG ログが出力される → PASS

---

## 実施内容

* `alembic/env.py` に `disable_existing_loggers=False` を追加（根本原因修正）
* `backend/logging_config.py` の `basicConfig(force=True)` を廃止し、条件付き `StreamHandler(sys.stdout)` 方式へ変更
* `backend/main.py` の lifespan に `run_migrations()` 後の root logger レベル復元処理を追加

---

## 変更ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `alembic/env.py` | 修正 | `fileConfig` に `disable_existing_loggers=False` を追加 |
| `backend/logging_config.py` | 修正 | `basicConfig(force=True)` を廃止、条件付き `StreamHandler(sys.stdout)` 追加 |
| `backend/main.py` | 修正 | `import logging` 追加・lifespan に root logger レベル復元処理を追加 |

---

## 実装概要

### 根本原因

alembic の `env.py` で `fileConfig(config.config_file_name)` を呼び出す際、デフォルト引数 `disable_existing_loggers=True` が有効になっていた。FastAPI の lifespan 内で `run_migrations()` が実行されると、その時点で uvicorn・FastAPI が登録した全ロガーが無効化される。これにより起動後のあらゆるログが docker logs に出なくなっていた。

### 修正の構成

1. **alembic/env.py**: `disable_existing_loggers=False` を明示（根本原因修正）
2. **backend/logging_config.py**: `basicConfig(force=True)` → 条件付き `StreamHandler` に変更（uvicorn との共存）
3. **backend/main.py**: `run_migrations()` 後に root logger レベルを `LOG_LEVEL` 環境変数の値へ復元（alembic.ini の `level = WARN` 対策）

---

## 実装判断

### 判断内容

* alembic.ini の `[logger_root] level = WARN` は変更しない
* root logger レベルの復元は lifespan 内（migration 後）で行う

### 判断理由

| 判断 | 理由 |
|---|---|
| alembic.ini を変更しない | alembic CLI を単独実行するときの出力抑制として合理的。アプリ側で復元する方針の方が責務が明確 |
| basicConfig(force=True) を廃止 | uvicorn の dictConfig 設定を破壊するため使えない。条件付き追加の方が共存しやすい |

---

## 動作確認

### 実施内容

* `docker compose up --build -d backend` で再ビルド
* `docker compose logs backend` でログ出力確認
* `/health` エンドポイントへのリクエストでアクセスログ確認
* コンテナ内で Python 実行し root logger レベルと DEBUG ログ出力を確認

### 結果

| 確認内容 | 結果 |
|---|---|
| AC-01: Alembic ログ | PASS |
| AC-02: HTTP アクセスログ | PASS |
| AC-03: リアルタイム確認 | PASS |
| AC-04: LOG_LEVEL=DEBUG | PASS |

---

## AIレビュー結果

### Summary

Approve

### Blocker

なし

### Important

* uvicorn ロガーへのレベル設定（`setup_logging()` 内の `for name in ("uvicorn", ...)` ）は uvicorn の `dictConfig` が後から上書きする可能性がある。`LOG_LEVEL=DEBUG` 時に uvicorn アクセスログが DEBUG にならない場合があるが、実害は限定的。

### Suggestions

* alembic.ini の `level = WARN` を変更していない理由をコメントで補足してもよい。

---

## Review Findings の対応

| 指摘 | 判断 | 理由 |
|---|---|---|
| uvicorn ロガーレベルのタイミング問題（Important） | 残課題 | 実害限定的のため、現時点では対応しない。必要になれば別 Issue で判断 |
| alembic.ini コメント補足（Suggestions） | 保留 | コードコメントに理由を記載済みのため十分と判断 |

---

## 発生した問題と対応

| 問題 | 原因 | 対応 |
|---|---|---|
| `basicConfig(force=True)` 除去後もログが出ない | `alembic/env.py` の `fileConfig` が `disable_existing_loggers=True` で uvicorn ロガーを無効化 | `disable_existing_loggers=False` を追加 |
| INFO ログが出ない（ERROR・WARNING のみ） | `alembic.ini` の `[logger_root] level = WARN` が root ロガーレベルを上書き | lifespan の migration 後にレベルを復元 |

---

## 学んだこと

* Python `logging.config.fileConfig` はデフォルトで既存ロガーを全て無効化する（`disable_existing_loggers=True`）。alembic を使うアプリでは必ず `False` を明示する。
* uvicorn は `dictConfig` でロガーを設定するため、後から `fileConfig` を呼ぶと上書きされる。`basicConfig(force=True)` も同じ理由で uvicorn と共存できない。
* alembic を FastAPI の lifespan 内で実行する場合、alembic.ini のロガー設定がアプリ全体に影響する。migration 後のログレベル復元が必要になる。

---

## 課題

### Remaining Issues

* RI-01: uvicorn ロガーへのレベル設定タイミング問題（`LOG_LEVEL=DEBUG` 時の uvicorn アクセスログ）。実害は限定的のため、必要になれば別 Issue で対応。

### GitHub Issues

なし

---

## 次の bolt への引き継ぎ

なし（Issue #30 完了）

**次の対応**: Commit → Push → PR 作成 → PR #31（Phase 3-1）マージ後に Phase 3-2 へ進む

---

## 関連資料

### Error Investigation

* `docs/error/backend-logging-not-visible-in-docker-logs.md`

### WorkLog

* `tmp/worklog/issue-30.md`

---

## 関連コミット

（コミット後に記録）

---

## 関連 PR

https://github.com/rento01/chatpot_rag_practice/pull/32
