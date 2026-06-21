# ChromaDB v1.x CORS 設定が機能しない問題

## 発生日

2026-06-22

## 関連ファイル

- `docker-compose.yml`
- `chroma-config.yaml`（本対応で新規追加）

---

## 症状

ChromaDB UI（`BlackyDrum/chromadb-ui`、`http://localhost:8090` で動作）から
ChromaDB（`http://localhost:8001`）に接続しようとすると、ブラウザで CORS エラーが発生して接続できない。

---

## 原因

### ChromaDB v1.x は Rust 実装に移行している

`chromadb/chroma:latest` イメージがバージョン 1.4.4 になり、サーバーが Python から Rust 実装に切り替わった。

| 比較項目 | v0.x（旧） | v1.x（新） |
|----------|------------|------------|
| 実装言語 | Python (FastAPI) | Rust |
| コンテナ内 Python | あり | なし |
| CORS 設定方法 | 環境変数 | `config.yaml` |

### 環境変数 `CHROMA_SERVER_CORS_ALLOW_ORIGINS` が機能しない

v0.x 時代の設定をそのまま残していたが、Rust 実装では無視されていた。

```yaml
# 旧: docker-compose.yml に書いていたが効果なし
environment:
  CHROMA_SERVER_CORS_ALLOW_ORIGINS: '["http://localhost:8090"]'
```

実際のレスポンスには CORS ヘッダーが一切含まれていなかった。

```
# curl で確認した結果（修正前）
< HTTP/1.1 200 OK
< content-type: application/json
< content-length: 44
< date: ...
# ← Access-Control-Allow-Origin ヘッダーなし
```

また、プリフライト（OPTIONS）リクエストも `405 Method Not Allowed` で拒否されていた。

---

## 調査手順

### 1. CORSヘッダーの有無を確認

```bash
curl -sv \
  -H "Origin: http://localhost:8090" \
  -X GET \
  http://localhost:8001/api/v2 2>&1 | grep -E "(< HTTP|access-control|Access-Control)"
```

→ `Access-Control-Allow-Origin` ヘッダーが返ってこないことを確認。

### 2. プリフライトの確認

```bash
curl -sv \
  -H "Origin: http://localhost:8090" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: content-type" \
  -X OPTIONS \
  http://localhost:8001/api/v2 2>&1 | grep -E "(< HTTP|access-control|Access-Control)"
```

→ `405 Method Not Allowed` で拒否されていることを確認。

### 3. ChromaDB のバージョン確認

```bash
docker exec rag-chat-template-chromadb-1 chroma --version
# chroma 1.4.4
```

→ Rust 実装（コンテナ内に `chroma` バイナリのみ、Python なし）を確認。

### 4. コンテナ内の config.yaml 確認

```bash
docker exec rag-chat-template-chromadb-1 cat /config.yaml
# persist_path: "/data"  ← cors_allow_origins の記述がない
```

→ CORS 設定が `config.yaml` に反映されていないことを確認。

---

## 解決策

### `chroma-config.yaml` を作成してボリュームマウント

**chroma-config.yaml（プロジェクトルートに新規作成）:**

```yaml
persist_path: "/data"
cors_allow_origins:
  - "http://localhost:8090"
```

**docker-compose.yml の変更点:**

```yaml
chromadb:
  image: chromadb/chroma:latest
  ports:
    - "8001:8000"
  volumes:
    - chromadb_data:/chroma/chroma
    - ./chroma-config.yaml:/config.yaml   # ← 追加
  environment:
    IS_PERSISTENT: "TRUE"
    ANONYMIZED_TELEMETRY: "FALSE"
    # CHROMA_SERVER_CORS_ALLOW_ORIGINS は削除（v1.x では無効）
```

### 適用コマンド

```bash
# restart では volume の変更が反映されないため --force-recreate が必要
docker compose up -d --force-recreate chromadb
```

> **注意:** `docker compose restart` では新しいボリュームマウントが反映されない。
> `--force-recreate` でコンテナを作り直す必要がある。

---

## 動作確認

### GET リクエスト

```bash
curl -sv \
  -H "Origin: http://localhost:8090" \
  -X GET \
  http://localhost:8001/api/v2 2>&1 | grep -E "(< HTTP|access-control|Access-Control)"
```

**期待する結果:**

```
< HTTP/1.1 200 OK
< vary: origin, access-control-request-method, access-control-request-headers
< access-control-allow-origin: http://localhost:8090
```

### OPTIONS プリフライト

```bash
curl -sv \
  -H "Origin: http://localhost:8090" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: content-type" \
  -X OPTIONS \
  http://localhost:8001/api/v2 2>&1 | grep -E "(< HTTP|access-control|Access-Control)"
```

**期待する結果:**

```
< HTTP/1.1 200 OK
< access-control-allow-methods: *
< access-control-allow-headers: *
< access-control-allow-origin: http://localhost:8090
```

---

## ChromaDB UI の設定

`BlackyDrum/chromadb-ui` を使う場合の接続設定:

| 項目 | 値 |
|------|----|
| UI URL | `http://localhost:8090` |
| ChromaDB 接続 URL | `http://localhost:8001` |
| CORS 許可オリジン | `http://localhost:8090` |

UI はバックエンドを持たず、ブラウザから直接 ChromaDB API に接続する構成のため、
ChromaDB 側の CORS 設定が必須。

---

## 残課題・注意点

- ChromaDB UI をブラウザの異なるオリジン（例: 別ポート、別ホスト）から開く場合は
  `chroma-config.yaml` の `cors_allow_origins` にそのオリジンを追加する。
- `chroma-config.yaml` を変更した場合は `docker compose up -d --force-recreate chromadb` が必要。
- ChromaDB のバージョンアップ時は CORS 設定の仕様変更がないか確認すること。
