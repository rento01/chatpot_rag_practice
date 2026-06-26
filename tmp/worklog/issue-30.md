# WorkLog — Issue #30

## 基本情報

* 作業日: 2026-06-26〜2026-06-27
* Phase: -
* Bolt: -
* 関連Issue: #30
* 作業ブランチ: fix/30-backend-logging
* 担当者: rento

---

## 1. 作業目的

### 今回の目的

FastAPI 起動後のログが `docker compose logs backend` に出力されない問題を特定・修正する。

---

### 完了条件

* Alembic ログが出力される（AC-01）
* HTTP アクセスログが出力される（AC-02）
* `docker compose logs -f` でリアルタイム確認できる（AC-03）
* `LOG_LEVEL=DEBUG` で DEBUG ログが出力される（AC-04）

---

## 2. 要件・設計確認

### Requirements 要点

* docker compose logs でバックエンドのログが確認できること
* LOG_LEVEL 環境変数でログレベルを切り替えられること

### Bolt 設計要点

通常 Issue 対応のため Bolt 設計なし。

### 今回の実装範囲

* ロギング設定の修正（logging_config.py）
* alembic fileConfig の修正（alembic/env.py）
* lifespan でのログレベル復元（main.py）

### 今回実装しない範囲

* uvicorn ロガーレベルのタイミング問題（実害軽微のため別 Issue 判断）
* ログフォーマットの変更

---

## 3. 実装前調査

### 確認したファイル

* `backend/logging_config.py`
* `alembic/env.py`
* `alembic.ini`
* `backend/main.py`
* `Dockerfile`

### 調査結果

* `PYTHONUNBUFFERED=1` は Dockerfile に設定済み → バッファリングは原因ではない
* `logging_config.py` で `basicConfig(force=True)` を使用 → uvicorn の `dictConfig` と競合
* `alembic/env.py` で `fileConfig(config.config_file_name)` をデフォルト引数で呼び出し → `disable_existing_loggers=True` により uvicorn 等の既存ロガーが全て無効化（根本原因）
* `alembic.ini` の `[logger_root] level = WARN` → migration 後に root ロガーレベルが WARN にリセットされる

### 疑問点

* `PYTHONUNBUFFERED=1` がないのが原因？ → 調査の結果、設定済みで原因ではなかった

---

## 4. 実装ログ

### 作業1: alembic/env.py — disable_existing_loggers=False を追加（根本原因修正）

**内容**

`fileConfig` のデフォルト引数 `disable_existing_loggers=True` が migration 実行後に uvicorn・FastAPI のロガーを全て無効化していた。`False` を明示することで既存ロガーを保護する。

**変更ファイル**

`alembic/env.py`

**理由**

alembic が lifespan 内で migration を実行するタイミングで `fileConfig` が呼ばれ、uvicorn が登録済みのロガーが全て消える。これが「起動後ログが出なくなる」の直接原因。

---

### 作業2: backend/logging_config.py — basicConfig(force=True) を廃止

**内容**

`basicConfig(force=True)` は uvicorn の `dictConfig` 設定を上書きする。`root.handlers` が空のときのみ `StreamHandler(sys.stdout)` を追加する方式に変更。

**変更ファイル**

`backend/logging_config.py`

**理由**

uvicorn はプロセス起動時に `dictConfig` でロガーを設定する。`force=True` はその設定を強制上書きするため、uvicorn との共存ができない。

---

### 作業3: backend/main.py — lifespan で root logger レベルを復元

**内容**

`run_migrations()` 後に `alembic.ini` の `[logger_root] level = WARN` が適用され root ロガーレベルが WARN にリセットされる。migration 完了後に `LOG_LEVEL` 環境変数のレベルへ戻す処理を lifespan に追加。

**変更ファイル**

`backend/main.py`

**理由**

`disable_existing_loggers=False` で既存ロガーは保護できたが、`alembic.ini` の `level = WARN` は root ロガーのレベルを上書きする。放置すると INFO ログが抑制される。

---

## 5. Diff Review

### 実施コマンド

```bash
git status
git diff
git diff --stat
```

---

### 変更ファイル一覧

* `alembic/env.py`
* `backend/logging_config.py`
* `backend/main.py`

---

### ファイル別の変更内容

**alembic/env.py**

* `fileConfig` に `disable_existing_loggers=False` を追加した

理由

* デフォルト `True` のままだと alembic migration 後に uvicorn ロガーが全て無効化されるため

**backend/logging_config.py**

* `import sys` を追加した
* `logging.basicConfig(force=True)` を削除した
* `root.handlers` が空の場合のみ `StreamHandler(sys.stdout)` を追加する形に変更した

理由

* uvicorn の logging 設定と競合しないようにするため
* Docker 環境では標準出力へログを出す構成が実務寄りのため

**backend/main.py**

* `import logging` を追加した
* lifespan に `run_migrations()` 後のログレベル復元処理を追加した

理由

* alembic.ini の `[logger_root] level = WARN` が root ロガーレベルを上書きするため

---

### 変更コード

**alembic/env.py**

変更前

```python
fileConfig(config.config_file_name)
```

変更後

```python
# disable_existing_loggers=False を明示して uvicorn などの既存ロガーを無効化しない。
fileConfig(config.config_file_name, disable_existing_loggers=False)
```

補足

* `fileConfig` のデフォルト引数を変えるだけで根本原因を解消できる
* コメントで理由を残さないと将来削除される可能性があるため必須

**backend/logging_config.py**

変更前

```python
logging.basicConfig(level=level, format=_LOG_FORMAT, force=True)
```

変更後

```python
root = logging.getLogger()
if not root.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(handler)
root.setLevel(level)
```

補足

* `if not root.handlers` で冪等性を確保している
* `force=True` は uvicorn の dictConfig 設定を破壊するため使えない

---

### 意図した変更

* alembic migration 後に uvicorn ロガーが無効化されないようにした
* `force=True` による root logger の強制再設定をやめた
* ログ出力先を標準出力に統一した
* migration 後に root ロガーレベルが WARN にリセットされる問題を修正した

---

### 意図していない変更がないか

以下を確認する。

* 関係ないファイルが変更されていないか
* フォーマットだけの変更が大量に入っていないか
* 不要なコメントやデバッグコードが残っていないか
* `.env` や秘密情報が含まれていないか
* 一時ファイルやキャッシュが含まれていないか

確認結果

* なし

---

### 削除した処理

* `logging.basicConfig(force=True)` を削除

理由

* 既存 handler を強制的に削除し、uvicorn のログ設定と競合するため

---

### 差分メモ

* `disable_existing_loggers=False` 1行の追加が根本原因の修正
* `logging_config.py` は uvicorn との共存を意識した最小変更
* 関係ないファイルへの変更なし

---

### 想定外変更

なし

---

### リスク・未確認事項

* uvicorn ロガーへのレベル設定（`setup_logging()` 内の `for name in ("uvicorn", ...)` ）は uvicorn の `dictConfig` が後から上書きする可能性がある。実害は限定的。

---

### 次回確認事項

* `LOG_LEVEL=DEBUG` 時に uvicorn アクセスログのレベルが期待通り動作するか

---

## 6. エラー対応ログ

### 問題1: basicConfig(force=True) 除去後もログが出ない

**原因調査**

`logging_config.py` 修正後も `Application startup complete.` が出ない。uvicorn の dictConfig と alembic の fileConfig の実行順序を確認。

**原因**

`alembic/env.py` の `fileConfig` がデフォルト `disable_existing_loggers=True` で uvicorn ロガーを無効化していた。

**対応内容**

`fileConfig(config.config_file_name, disable_existing_loggers=False)` に変更。

**再発防止**

`fileConfig` 呼び出しには必ず `disable_existing_loggers=False` を明示する。

---

### 問題2: INFO ログが出ない（ERROR・WARNING のみ）

**原因調査**

ロガー無効化は解消されたが、INFO ログが抑制される。`alembic.ini` の `[logger_root] level = WARN` を確認。

**原因**

`alembic.ini` の `[logger_root] level = WARN` が root ロガーのレベルを上書きしていた。

**対応内容**

`main.py` の lifespan で `run_migrations()` 後に root ロガーレベルを `LOG_LEVEL` 環境変数の値へ復元。

**再発防止**

alembic を lifespan 内で実行する場合、alembic.ini のロガー設定がアプリ全体に影響することを意識する。

---

## 7. Claude Code 活用ログ

| 質問 | 回答要約 | 採用判断 | 判断理由 |
|---|---|---|---|
| `basicConfig(force=True)` 除去後もログが出ない原因 | alembic fileConfig の `disable_existing_loggers=True` が根本原因 | 採用 | 調査と実験で確認済み |
| `LOG_LEVEL=DEBUG` でログが出ない原因 | アプリが DEBUG レベルのメッセージを生成していないため（設定は正常） | 採用 | コンテナ内で Python 実行して root レベルが DEBUG であることを確認 |

---

## 8. 動作確認

### 確認1: Alembic ログ（AC-01）

**実施内容**: `docker compose logs backend` で alembic 出力を確認

**期待結果**: alembic の migration ログが出力される

**実結果**: 出力確認

**判定**: OK

---

### 確認2: HTTP アクセスログ（AC-02）

**実施内容**: `GET /health` リクエスト後に `docker compose logs` を確認

**期待結果**: `GET /health 200 OK` が出力される

**実結果**: 出力確認

**判定**: OK

---

### 確認3: リアルタイム確認（AC-03）

**実施内容**: `docker compose logs -f backend` で起動ログを確認

**期待結果**: `Application startup complete.` が出力される

**実結果**: 出力確認

**判定**: OK

---

### 確認4: LOG_LEVEL=DEBUG（AC-04）

**実施内容**: コンテナ内で Python 実行し root ロガーレベルと DEBUG ログ出力を確認

**期待結果**: root レベルが DEBUG、DEBUG ログが出力される

**実結果**: `root level after setup_logging: DEBUG`、`TEST DEBUG MESSAGE` 出力確認

**判定**: OK

---

## 9. 作業振り返り

### 完了したこと

* Issue #30 の根本原因（alembic fileConfig の `disable_existing_loggers=True`）を特定し修正
* `basicConfig(force=True)` 問題を同時に解消
* `LOG_LEVEL` 環境変数によるレベル制御が正常に動作することを確認

---

### 学んだこと

* Python `logging.config.fileConfig` はデフォルトで既存ロガーを全て無効化する（`disable_existing_loggers=True`）
* uvicorn は `dictConfig` でロガーを設定するため、後から `fileConfig` を呼ぶと上書きされる
* alembic を FastAPI の lifespan 内で実行する場合、alembic.ini のロガー設定がアプリ全体に影響する

---

### 判断理由として残したいこと

* alembic.ini の `[logger_root] level = WARN` は変更しない。alembic CLI を単独実行するときの出力抑制として合理的なため、アプリ側（main.py lifespan）で復元する方針を採用した。

---

### 残課題

* uvicorn ロガーへのレベル設定タイミング問題（`LOG_LEVEL=DEBUG` 時の uvicorn アクセスログ）

---

### 次回作業

Commit → Push → PR 作成
