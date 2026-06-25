# バックエンドの起動後ログが docker compose logs に出力されない問題

## 発生日

2026-06-25

---

## Summary

`docker compose logs backend | grep "embedding 生成"` でログを確認しようとしたところ、該当ログが出力されなかった。  
調査の結果、コンテナ起動後（uvicorn が HTTP リクエストの受付を開始した以降）のログが、HTTP アクセスログ・バックグラウンドタスクのアプリケーションログを問わず、`docker compose logs` に一切出力されていないことが確認できた。  
起動時（alembic マイグレーションログ等）は正常に出力されており、コンテナの stdout/stderr 自体は Docker によってキャプチャされていることを直接書き込みテストで確認済み。  
根本原因については後述する2点が有力候補だが、現時点で確定していない。

---

## Impact

**ユーザー影響**
- バックグラウンドタスク（PDF インデックス処理）のログが確認できない
- エラー発生時も `docker compose logs` からは原因を追えない
- AC（受け入れ基準）のログ確認が `docker compose logs` では実施不可能な状態

**システム影響**
- 実際の処理（embedding 生成・ChromaDB upsert）は正常に動作している（PostgreSQL の `status=ready` / `page_count` で確認済み）
- ログが欠落しているだけで、アプリケーション本体には影響なし

**回避策**
- PostgreSQL で `status`・`page_count`・`indexed_at` を確認することで処理完了を代替確認できる
- `docker exec` でスクリプトを直接実行した場合はターミナルにログが出力される（ただし `docker logs` には入らない）

---

## Investigation

### 調査手順

1. `docker compose logs backend | grep "embedding 生成"` で対象ログを検索 → 出力なし
2. `docker logs rag-chat-template-backend-1` で全ログ確認 → 起動ログ 10 行のみ
3. `curl /health`、`curl /collections` を送信後に `docker logs --follow` でリアルタイム確認 → アクセスログも出ず
4. PID 1（uvicorn）の fd/1（stdout）・fd/2（stderr）に直接書き込みテスト
5. `docker logs` でテスト文字列が出力されることを確認 → Docker のキャプチャ自体は正常
6. `/proc/1/fd/` の一覧を確認し、stdin/stdout/stderr のマッピングを確認
7. `docker exec` で `uvicorn.config.LOGGING_CONFIG` を確認し、ログハンドラの設定を読み解く
8. `docker exec` で root logger・`uvicorn.access` ロガーの状態を確認
9. コンテナ内の全 PID を確認（PID 1 のみ稼働、PID 729 は一時的なプロセス）
10. `backend/logging_config.py` のコードを読み、`setup_logging()` の挙動を確認

### 調査環境

- OS: Darwin 24.5.0
- Docker: rag-chat-template-backend-1（Up 2026-06-25 08:47:46 〜）
- uvicorn: 0.49.0
- Python: 3.12

---

## Findings

### docker logs に出力されているもの・いないもの

| ログ種別 | 出力 | 備考 |
|---|---|---|
| uvicorn 起動メッセージ | ✓ | "Started server process [1]" |
| alembic マイグレーションログ | ✓ | lifespan 内の同期処理 |
| uvicorn HTTP アクセスログ | ✗ | /health・/collections に curl 後も出ず |
| FastAPI バックグラウンドタスクのアプリログ | ✗ | embedding 生成ログ等 |

### Docker のキャプチャ確認（正常）

PID 1 の fd/1（stdout）・fd/2（stderr）に直接書き込んだところ、docker logs に即時出力されることを確認。Docker 側のキャプチャ自体に問題はない。

```bash
# fd/2（stderr）に書き込み → docker logs に出力された
docker exec ... python -c "
with open('/proc/1/fd/2', 'wb') as f:
    f.write(b'TEST_STDERR_WRITE\n')
"

# fd/1（stdout）に書き込み → docker logs に出力された
docker exec ... python -c "
with open('/proc/1/fd/1', 'wb') as f:
    f.write(b'TEST_STDOUT_WRITE\n')
"
```

### PID 1 のファイルディスクリプタ

```
0 -> /dev/null        （stdin）
1 -> pipe:[20358110]  （stdout） ← Docker がキャプチャ
2 -> pipe:[20358111]  （stderr） ← Docker がキャプチャ
```

### uvicorn 0.49.0 のデフォルトログ設定

```python
{
  'version': 1,
  'disable_existing_loggers': False,
  'handlers': {
    'default': {'class': 'logging.StreamHandler', 'stream': 'ext://sys.stderr'},
    'access':  {'class': 'logging.StreamHandler', 'stream': 'ext://sys.stdout'}
  },
  'loggers': {
    'uvicorn':        {'handlers': ['default'], 'level': 'INFO', 'propagate': False},
    'uvicorn.error':  {'level': 'INFO'},
    'uvicorn.access': {'handlers': ['access'],  'level': 'INFO', 'propagate': False}
  }
}
```

- `uvicorn.access` は stdout への `StreamHandler` を持ち、`propagate: False`
- `uvicorn`（error 系）は stderr への `StreamHandler` を持ち、`propagate: False`
- 'root' キーがないため、`dictConfig` による root logger の変更は行われない設計

### `setup_logging()` の処理

```python
# backend/logging_config.py
logging.basicConfig(level=level, format=_LOG_FORMAT, force=True)
for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    logging.getLogger(name).setLevel(level)
```

- `force=True` により、root logger の既存ハンドラを全削除し `StreamHandler(sys.stderr)` を追加
- uvicorn の named logger ハンドラには影響しない（`force=True` は root のみに作用）

### `setup_logging()` と uvicorn `dictConfig` の実行順序（推測）

| 順序 | 処理 | 結果 |
|---|---|---|
| 1 | uvicorn が `dictConfig(LOGGING_CONFIG)` を呼び出す | uvicorn loggers に handler が設定される |
| 2 | uvicorn が `backend.main` を import | `setup_logging()` が実行され root logger に `StreamHandler(stderr)` が追加 |
| 3 | lifespan 開始 → `run_migrations()` | alembic → root logger → `StreamHandler(stderr)` → **docker logs に出力される** |
| 4 | HTTP リクエスト受付開始 | uvicorn の named logger ハンドラ経由でログ出力されるはずだが… |
| 5 | バックグラウンドタスク実行 | `backend.rag` → root logger → `StreamHandler(stderr)` → **出力されない** |

手順 3 ではログが出るが手順 5 では出ない。root logger の `StreamHandler` は変わっていないはずであり、その理由が現時点で確定していない。

### `docker exec` セッションでのロガー状態

```
root logger: handlers=[], level=30 (WARNING)
uvicorn.access: handlers=[], propagate=True
```

`docker exec` は uvicorn プロセスとは別の Python プロセスを起動するため、この結果は uvicorn プロセス自体の状態とは異なる点に注意。

---

## Evidence

### コマンド

```bash
# ログ確認
docker compose logs backend | grep "embedding 生成"
docker logs rag-chat-template-backend-1 --follow &
curl -s http://localhost:8000/health > /dev/null

# Docker キャプチャ確認
docker exec rag-chat-template-backend-1 python -c "
with open('/proc/1/fd/2', 'wb') as f: f.write(b'TEST_STDERR_WRITE\n')
"
docker exec rag-chat-template-backend-1 python -c "
with open('/proc/1/fd/1', 'wb') as f: f.write(b'TEST_STDOUT_WRITE\n')
"
docker logs rag-chat-template-backend-1 | grep "TEST"

# uvicorn 設定確認
docker exec rag-chat-template-backend-1 python -c "
import uvicorn.config as cfg; print(cfg.LOGGING_CONFIG)"

# PID / fd 確認
docker exec rag-chat-template-backend-1 ls /proc/ | grep -E '^[0-9]+$'
docker exec rag-chat-template-backend-1 ls -la /proc/1/fd/
```

### docker logs（全ログ）

```
backend-1  | INFO:     Started server process [1]
backend-1  | INFO:     Waiting for application startup.
backend-1  | 2026-06-25 08:47:46,197 [INFO] alembic.runtime.plugins: setup plugin ...
backend-1  | ...（alembic 6行）...
backend-1  | INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
backend-1  | INFO  [alembic.runtime.migration] Will assume transactional DDL.
backend-1  | TEST_STDERR_WRITE   ← 直接書き込みテスト
backend-1  | TEST_STDOUT_WRITE   ← 直接書き込みテスト
```

HTTP リクエスト後のアクセスログや、"Application startup complete." も出力されていない。

---

## Root Cause Candidates

### 主要候補1: `setup_logging()` と uvicorn `dictConfig` の干渉

`setup_logging()` の `basicConfig(force=True)` が uvicorn 0.49.0 の `dictConfig(LOGGING_CONFIG)` と組み合わさり、起動後のログ出力経路を壊している可能性がある。具体的には：

- `force=True` は root logger のハンドラのみを変更するが、uvicorn 0.49.0 が `dictConfig` を `import` 後に再度呼び出す場合、root logger のハンドラが再度除去される可能性がある
- `uvicorn.access` の `propagate: False` により、アクセスログが root logger へ伝播せず stdout へ直接書かれるが、その stdout ハンドラが機能していない可能性がある

### 主要候補2: `PYTHONUNBUFFERED` 未設定による stdout のバッファリング

docker-compose.yml の backend サービスに `PYTHONUNBUFFERED: "1"` が設定されていない。Python プロセスが pipe に接続された場合、stdout はブロックバッファリングモードで動作する。`logging.StreamHandler.emit()` は `flush()` を呼び出すが、何らかの理由でバッファが適切にフラッシュされていない可能性がある。

- stderr はほぼ常にアンバッファリングのため起動ログ（alembic）は出る
- stdout ベースのアクセスログはバッファに溜まったまま出ない、という挙動と一致する

### 副次的事項: コンテナ再起動によるログ消失

これは本 Issue の直接の原因ではないが、今後も発生し得る問題として記録しておく。`docker logs` は現在のコンテナインスタンスのログのみを保持するため、コンテナ再起動・再作成でログが失われる。

---

## Recommended Actions

※ 以下は推奨対応案。実施可否・優先度は Issue 作成時に判断すること。

### A. `PYTHONUNBUFFERED: "1"` の追加（主要対応・低リスク）

**内容**
`docker-compose.yml` の backend サービスの environment に `PYTHONUNBUFFERED: "1"` を追加する。

```yaml
environment:
  PYTHONUNBUFFERED: "1"   # 追加
  LLM_PROVIDER: ...
```

**メリット**
- Python の stdout/stderr バッファリング問題を根本から解消できる可能性が高い
- 変更が1行で済み、リスクが低い
- コンテナ化された Python アプリケーションのベストプラクティスに沿った対応

**デメリット**
- バッファリングを無効化するため、ログ出力が多い場合にわずかなパフォーマンス影響がある可能性があるが、通常は無視できるレベル

**影響範囲**
- `docker-compose.yml`（1行追加）
- コンテナ再起動が必要

---

### B. `setup_logging()` の修正（干渉解消）

**内容**
`basicConfig(force=True)` を使わず、既存ハンドラと共存できる形でロガーを設定し直す。または uvicorn 0.49.0 の logging API に合わせて設定方法を変更する。

**メリット**
- 干渉の根本原因を解消できる

**デメリット**
- uvicorn のバージョンアップ追従が必要になる可能性がある
- 変更による副作用のテストが必要

**影響範囲**
- `backend/logging_config.py`

---

### C. ログの永続化（中期対応）

**内容**
コンテナ再起動によるログ消失を防ぐために、ログをファイルに書き出す設定を追加するか、外部ログ収集基盤（例: CloudWatch Logs）に転送する構成を検討する。

**メリット**
- コンテナ再起動後もログが参照できるようになる

**デメリット**
- インフラ追加が必要（特にファイル出力では別途ボリュームマウントが必要）

**影響範囲**
- `docker-compose.yml`、または外部ログ基盤設定

---

## Open Questions

1. 対応 A（`PYTHONUNBUFFERED`）で起動後のログ出力が解消されるかは適用後の確認が必要
2. `setup_logging()` → `basicConfig(force=True)` → uvicorn `dictConfig` の実際の呼び出し順序を uvicorn 0.49.0 のソースコードで確認する（現時点では推測）
3. "Application startup complete." のログが出ていない理由が `PYTHONUNBUFFERED` で説明できるか（stderr はアンバッファリングのはずなので、別の原因がある可能性）

---

## Conclusion

`docker compose logs backend` には起動後のログが一切出力されていないことが確認できた。Docker のキャプチャ自体は正常（直接書き込みテストで確認済み）であり、問題は Python 側のログ出力経路にある。有力候補は `PYTHONUNBUFFERED` 未設定によるバッファリングと、`setup_logging()` と uvicorn 0.49.0 の `dictConfig` の干渉だが、どちらが主因かは現時点で確定していない。  
対応 A（`PYTHONUNBUFFERED: "1"` の追加）が低リスク・高確度の改善策として推奨される。埋め込み生成の動作確認については、現時点では PostgreSQL の `status=ready` / `page_count` で代替確認することを推奨する。

---

## Related Files

- `docker-compose.yml` — backend サービスの environment 設定（`PYTHONUNBUFFERED` 追加候補）
- `backend/logging_config.py` — `setup_logging()` の実装
- `backend/main.py` — `setup_logging()` 呼び出し元・`_index_document` バックグラウンドタスク
- `backend/rag.py` — `logger.info("embedding 生成を開始/完了")` の出力箇所

---

## Related Issues

- Issue #10（ChromaDB persist_path とボリュームの不一致）
- Issue #29（embedding 次元不一致による PDF インデックスエラー）
