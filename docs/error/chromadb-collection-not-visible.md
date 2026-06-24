# PDF インデックス後も ChromaDB に Collection が表示されない問題

## 発生日

2026-06-23

---

## Summary

`/ingest` でPDFをアップロードしステータスが `ready` になった後も、ChromaDB Admin UI（http://localhost:8001）に COLLECTIONS が表示されない（0件）。  
調査の結果、`chroma-config.yaml` の `persist_path: "/data"` と `docker-compose.yml` のボリュームマウント先 `/chroma/chroma` が一致していないことが確認できた。この不一致により、ChromaDB がデータを書き込む `/data` はいかなる Docker ボリュームにも保護されていない可能性があり、コンテナ再起動の際にインデックスデータが消失したと推測される。なお、コンテナ再起動が実際にあったかどうか、その正確なタイミングは未確認。

---

## Investigation

### 調査手順

1. ChromaDB Admin UI のスクリーンショットで `COLLECTIONS: 0` を確認
2. `docker ps` でコンテナの稼働時間を確認
3. `docker logs rag-chat-template-backend-1` でバックエンドの起動ログを確認
4. `chroma-config.yaml` と `docker-compose.yml` の設定を照合
5. ChromaDB v2 API（`/api/v2/tenants/default_tenant/databases/default_database/collections`）を curl で直接確認
6. バックエンドコンテナから Python chromadb クライアントで `list_collections()` を実行
7. `docker exec` で ChromaDB コンテナ内のファイルシステムを調査（`/data`、`/chroma/chroma`）
8. PostgreSQL でドキュメントのステータスを確認

---

## Findings

### コンテナ稼働時間

```
rag-chat-template-backend-1    Up 19 minutes
rag-chat-template-chromadb-1   Up 21 hours
```

PDF の indexed_at（PostgreSQL 記録）: `2026-06-21 15:15:38+00`（約2日前）  
ChromaDB 稼働時間は21時間であり、インデックス後に ChromaDB コンテナが再起動された可能性がある。ただし、再起動の有無・タイミングは未確認。

### PostgreSQL の状態（正常）

```sql
 id |   filename   | status | page_count | collection_id |          indexed_at
----+--------------+--------+------------+---------------+-------------------------------
  4 | 就業規則.pdf | ready  |         11 |             4 | 2026-06-21 15:15:38.786809+00
```

PostgreSQL は pgdata ボリュームで保護されており正常。PDF バイナリも `file_data` カラムに残存している。

### ChromaDB 内のファイル配置

| パス | ファイル | 備考 |
|---|---|---|
| `/data/chroma.sqlite3` | あり | ChromaDB が読み書きしている SQLite |
| `/data/5a444e76-.../` | HNSW ファイル群 | 調査中に実施したテスト upsert で生成 |
| `/chroma/chroma/chroma.sqlite3` | あり | Docker ボリュームがマウントされている先。ChromaDB は読んでいないと推測 |

ChromaDB のログ出力から、config の `persist_path: "/data"` は有効に読み込まれていることが確認できた。

### 設定ファイルの不一致

**`chroma-config.yaml`**
```yaml
persist_path: "/data"
cors_allow_origins:
  - "http://localhost:8090"
```

**`docker-compose.yml`（chromadb サービス）**
```yaml
volumes:
  - chromadb_data:/chroma/chroma   ← /data と一致していない
  - ./chroma-config.yaml:/config.yaml
```

`/data` はどの Docker ボリュームにもマウントされていない。コンテナ削除・再作成時にはデータが失われる構造になっている。

### Python クライアント動作確認（調査中に実施したテスト）

バックエンドコンテナから upsert テストを実行した結果：

```
get_or_create_collection 成功: test_col
→ ONNX モデル (all-MiniLM-L6-v2, 79.3MB) のダウンロードが発生
upsert 成功
list_collections: [Collection(name=test_col)]
```

`embeddings=None` の場合、Python chromadb クライアントがローカルで ONNX モデルをダウンロードしてクライアントサイドでベクトル化する挙動を確認。初回インデックス時にもこのダウンロードが発生していたと推測されるが、当時のログは残っていないため確認できていない。

### バージョン情報

| コンポーネント | バージョン |
|---|---|
| ChromaDB サーバー | 1.0.0 |
| Python chromadb クライアント | 1.5.9 |

---

## Root Cause Candidates

### 主要候補（確認済みの事実に基づく）

**`chroma-config.yaml` の `persist_path: "/data"` と `docker-compose.yml` のボリュームマウント先 `/chroma/chroma` が一致していない**

- ChromaDB は `/data` にデータを書くが、`/data` はボリューム外
- `chromadb_data` ボリュームは `/chroma/chroma` をバックアップしている
- コンテナ再起動が発生した場合、`/data` のデータは消える構造になっている

### 副次的懸念点

- 初回 upsert 時に 79.3MB の ONNX モデルダウンロードが発生する
  - バックグラウンドタスクの完了前にコンテナが再起動した場合、インデックスが途中で中断されていた可能性はある
  - ただし PostgreSQL の `status=ready` から見ると、少なくとも upsert は一度完了したと判断できる

---

## Recommended Actions

※ 以下は推奨対応案。実施可否・優先度はチームで判断すること。

### A. ボリュームマウントパスの修正（主要対応）

`docker-compose.yml` のマウント先を `persist_path` と一致させる。

**変更案1: docker-compose.yml を修正**
```yaml
# 変更前
- chromadb_data:/chroma/chroma
# 変更後
- chromadb_data:/data
```

**変更案2: chroma-config.yaml を修正**
```yaml
# 変更前
persist_path: "/data"
# 変更後
persist_path: "/chroma/chroma"
```

どちらを変更するかは、既存ボリュームの扱いと合わせて検討すること。

### B. ドキュメントの再インデックス

PDF データは PostgreSQL に残存しているため、再アップロードで再インデックス可能。

### C. ONNX モデルキャッシュの扱い（将来対応）

Phase 3-1 以降で Ollama/Bedrock の embed モデルを使うよう実装すれば、ONNX ローカルダウンロードの問題は自然解消する考えられる。それまでの期間でキャッシュを永続化したい場合はボリューム追加を検討。

---

## Open Questions

1. ChromaDB コンテナの再起動は実際に発生したか（意図的か、クラッシュか）
2. 変更案1 / 変更案2 のどちらで対応するか（既存ボリューム `chromadb_data` の内容の扱いを含めて判断が必要）
3. `/chroma/chroma/chroma.sqlite3`（ボリューム内）の既存ファイルが今後の動作に影響するか未確認
4. 初回インデックス時の ONNX ダウンロード（79.3MB）がバックグラウンドタスクのタイムアウトに引っかかるリスクがあるか

---

## Conclusion

今回判明した最大の構造的問題は、**ChromaDB の persist_path とボリュームマウント先のパス不一致**であり、コンテナ再起動のたびにインデックスデータが失われうる状態が続いている。PostgreSQL 側のデータ（PDF バイナリ含む）は正常に保護されており、ボリュームのパスを揃えて ChromaDB を再起動・再インデックスすれば復旧可能と考えられる。変更方針（どちらのパスに合わせるか）と既存ボリュームの取り扱いについては Issue で確認・決定することを推奨する。

---

## 関連ファイル

- `docker-compose.yml` — chromadb サービスのボリューム設定
- `chroma-config.yaml` — ChromaDB の persist_path 設定
- `backend/vector_db/chroma.py` — ChromaDB upsert 実装
- `backend/rag.py` — index_document 関数
- `backend/main.py` — _index_document バックグラウンドタスク
