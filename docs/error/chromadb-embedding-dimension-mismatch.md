# 同一コレクションへの PDF 追加インデックスが error になる問題

## 発生日

2026-06-25

---

## Summary

既存コレクション `company_rules`（`col_5`）に2本目の PDF（通勤手当支給規程.pdf）をアップロードしたところ、status が `error` になった。  
調査の結果、1本目の PDF（就業規則.pdf）インデックス時と2本目インデックス時で、使用された embedding モデルの次元数が異なっていたことが確認できた。ChromaDB はコレクション作成時の次元数を固定するため、次元数が変わると upsert を拒否する。  
なお、エラーの詳細はバックエンドログに出力されているが、後述の理由によりコンテナ現在インスタンスのログには残っていない。

---

## Impact

**ユーザー影響**
- 対象コレクションに追加アップロードした PDF は status=error になり、RAG 検索の対象に含まれない

**システム影響**
- ChromaDB 上のコレクション `col_5` には 384 次元で固定されたインデックスが残存している
- 現在のコード（768 次元）でこのコレクションに upsert すると必ずエラーになる状態

**回避策**
- コレクションを削除して再作成し、現在の embedding モデル（768 次元）で両 PDF を再インデックスする

---

## Investigation

### 調査手順

1. PostgreSQL でドキュメント一覧・ステータスを確認
2. バックエンドログでエラー出力を確認（出力なし → 理由を調査）
3. バックエンドコンテナで `index_document` を直接実行して例外を再現
4. ChromaDB コレクションの一覧・メタデータを確認
5. 現在の embed モデルの出力次元を確認
6. `rag.py`・`main.py` のコードを読んでバックグラウンドタスクの構造を確認

### 調査環境

- OS: Darwin 24.5.0
- Docker: rag-chat-template-backend-1（Up 2026-06-25 08:19:49 〜）
- DB: PostgreSQL 16（rag-chat-template-db-1）
- ChromaDB: 1.0.0（rag-chat-template-chromadb-1）
- Python chromadb クライアント: 1.5.9

---

## Findings

### ドキュメントの状態（PostgreSQL）

```
 id |       filename       | status | page_count | collection_id |          indexed_at
----+----------------------+--------+------------+---------------+-------------------------------
  5 | 就業規則.pdf         | ready  |         11 |             5 | 2026-06-22 17:03:37.609508+00
  8 | 通勤手当支給規程.pdf | error  |            |     94757     |
```

- `通勤手当支給規程.pdf` は `indexed_at` が NULL → `status=ready` に到達する前にエラーが発生している

### ChromaDB コレクション

```
name=col_5, metadata=None
```

- メタデータに embedding 次元の明示的な記録はない
- ChromaDB は初回 upsert 時の次元数をコレクションに紐づけて固定する

### エラー再現

バックエンドコンテナで `index_document` を直接実行した結果：

```
embedding 生成を開始: 12 チャンク
embedding 生成を完了: 12 チャンク
→ HTTP 400 Bad Request
エラー: InvalidArgumentError: Collection expecting embedding with dimension of 384, got 768
```

- `rag.py` の `index_document` → `vdb.upsert` → `chromadb/api/fastapi.py` で HTTP 400 を受信
- エラーは `chromadb.errors.InvalidArgumentError` として raise される

### 現在の embed モデル

```python
<class 'backend.llm.ollama.OllamaEmbedModel'>
embedding dim: 768
```

Ollama `nomic-embed-text` モデルを使用（768 次元）

### バックエンドログにエラーが出ない理由

コードレベルでは `main.py` の `_index_document` の `except Exception` ブロックで `logger.exception(...)` が呼ばれているため、エラーログは**出力されている**。

```python
# main.py:300
except Exception:
    logger.exception("ドキュメント取り込みに失敗: document_id=%s", document_id)
```

しかし現在の `docker logs` に残っていない理由は次のとおり：

- バックエンドコンテナの現在インスタンスは `2026-06-25 08:19:49` に起動した
- `docker logs` はコンテナの**現在インスタンス**のログのみを保持する
- PDF のアップロード（およびエラー発生）はコンテナ起動より前に行われたと考えられる
- コンテナ再作成時に旧インスタンスのログは消失する

つまりログ出力の仕組み自体に問題はなく、**コンテナ再起動によってログが揮発した**ことが原因と考えられる。

---

## Evidence

### コマンド

```bash
# ドキュメント状態確認
docker exec rag-chat-template-db-1 psql -U chat -d chat \
  -c "SELECT id, filename, status, page_count, collection_id, indexed_at FROM documents ORDER BY id;"

# エラー再現
docker exec rag-chat-template-backend-1 python -c "
from backend.db import SessionLocal
from backend import dataModels as dm
from backend.rag import index_document
import traceback
with SessionLocal() as db:
    doc = db.get(dm.Document, 8)
    try:
        page_count = index_document(doc.collection_id, doc.id, doc.file_data)
    except Exception as e:
        traceback.print_exc()
"

# embed モデルの次元確認
docker exec rag-chat-template-backend-1 python -c "
from backend.llm import get_embed_model
model = get_embed_model()
print(type(model))
print(len(model.embed(['テスト'])[0]))
"

# ChromaDB コレクション確認
docker exec rag-chat-template-backend-1 python -c "
import chromadb
c = chromadb.HttpClient(host='chromadb', port=8000)
for col in c.list_collections():
    print(col.name, c.get_collection(col.name).metadata)
"
```

### エラートレースバック

```
chromadb.errors.InvalidArgumentError: Collection expecting embedding with dimension of 384, got 768
  File "backend/rag.py", line 97, in index_document
    vdb.upsert(...)
  File "backend/vector_db/chroma.py", line 83, in upsert
    col.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
  File "chromadb/api/fastapi.py", line 723, in _upsert
    ...
  File "chromadb/api/base_http_client.py", line 129, in _raise_chroma_error
    raise chroma_error
```

---

## Root Cause Candidates

### 主要候補（高確度）

**コレクション作成時と upsert 時で embedding 次元数が異なる**

- `就業規則.pdf`（2026-06-22）インデックス時点のコードでは `embeddings=None` で upsert していたと考えられる。この場合 ChromaDB の Python クライアントが ONNX デフォルトモデル（all-MiniLM-L6-v2）でローカル埋め込みを生成し、384 次元でコレクションが固定された可能性がある
- その後のコード更新で `rag.py` に Ollama 埋め込み生成（768 次元）が追加された
- `通勤手当支給規程.pdf` のインデックス時に 768 次元の embedding を渡したが、ChromaDB 側で 384 次元を期待しているため拒否された

### 副次的懸念点

- コンテナ再起動でバックエンドログが揮発するため、エラー発生時の詳細追跡が困難になっている
- `_index_document` のエラー内容は DB の `status=error` のみに記録されており、エラー種別・スタックトレースの永続化手段がない

---

## Recommended Actions

※ 以下は推奨対応案。実施可否・優先度は Issue 作成時に判断すること。

### A. コレクションを削除して再作成（即時対応）

**内容**
UI またはバックエンド API でコレクション `company_rules` を削除 → 再作成 → 両 PDF を再アップロード

**メリット**
- 追加実装不要、すぐ解消できる

**デメリット**
- 手動オペレーションが必要
- 今後も embedding モデルを変更するたびに同じ問題が起きる

**影響範囲**
- コレクション `company_rules` 配下のドキュメント（ChromaDB データは削除、PostgreSQL の file_data は保持）

---

### B. embedding モデル変更時のコレクション再作成を自動化（中期対応）

**内容**
embedding 次元をコレクションメタデータに記録し、次元不一致を検出したら自動的にコレクションを再作成してすべてのドキュメントを再インデックスするロジックを実装する

**メリット**
- モデル変更時の手動対応が不要になる

**デメリット**
- 実装コストが高い
- 再インデックスが大量の場合は時間がかかる

**影響範囲**
- `backend/vector_db/chroma.py`、`backend/rag.py` の修正が必要

---

### C. エラー永続化の改善（中期対応）

**内容**
`documents` テーブルに `error_message` カラムを追加し、`_index_document` のエラー内容をDBに書き込む

**メリット**
- コンテナ再起動後もエラー詳細を追跡できる

**デメリット**
- スキーマ変更・マイグレーションが必要

**影響範囲**
- `alembic/versions/`（マイグレーション追加）、`backend/dataModels.py`、`backend/main.py`

---

## Open Questions

1. `就業規則.pdf` のインデックス時のコードを git log で確認し、当時 `embeddings=None` だったかを確認する（未実施）
2. 対応 A を実施した後、`col_5` 内に他のドキュメントが残っていた場合の扱いをどうするか
3. 将来的に embedding モデルを変更する予定があるか（ある場合は対応 B の優先度が上がる）

---

## Conclusion

エラーの直接原因は ChromaDB コレクションの **embedding 次元の不一致**（384 vs 768）であることが再現実験により確認できた。コレクションを削除・再作成して両 PDF を再インデックスすることで復旧可能と考えられる。また、コンテナ再起動によってバックエンドログが揮発する点は独立した観察可能性の課題として別途検討することを推奨する。

---

## Related Files

- `backend/rag.py` — embedding 生成・upsert 処理
- `backend/vector_db/chroma.py` — ChromaDB upsert 実装
- `backend/llm/embedModel.py` — embed モデル切り替えロジック
- `backend/main.py` — `_index_document` バックグラウンドタスク（エラーログ出力箇所）

---

## Related Issues

- Issue #10（chromadb-collection-not-visible — persist_path とボリュームの不一致）
