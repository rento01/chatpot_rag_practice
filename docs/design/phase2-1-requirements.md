# Phase 2-1 Requirements

## Phase情報

Phase: 2-1

タイトル: ファイル取り込みを動かす

---

## 対応Issue

#1

---

## 背景

このプロジェクトは RAG システムを段階的に学習するための教材テンプレートです。
初期状態では `rag.index_document()` が `NotImplementedError` を投げるため、
`/ingest` ページから PDF をアップロードしても status が `error` になって止まります。
Phase 2-1 では「テキスト抽出 → チャンク分割 → VectorDB への保存」のパイプラインを実装し、
後段の検索・RAG が動く土台を整えます。

---

## 目的

PDF をアップロードしたとき status が `ready` になるまで完走させ、
Phase 2-2 以降の検索実装に進める状態にする。

---

## 要件

- PDF からテキストを抽出し、固定長チャンクに分割できること
- 分割したチャンクを Chroma のコレクションに保存できること
- 取り込みはバックグラウンドタスクで動作し、数十ページの PDF でもタイムアウトしないこと
- 取り込み完了後、ドキュメントの status が `ready`、page_count が正しく記録されること

---

## 対象範囲

- `backend/rag.py` の `split_into_chunks` を実装する（固定長、目安 500 文字程度）
- `backend/rag.py` の `index_document` を完成させる
  - `extract_text` → `split_into_chunks` → `Chunk` 化 → `vdb.upsert` の流れを繋ぐ
- `backend/vector_db/chroma.py` の `ChromaVectorDB.upsert` を実装する
  - chromadb の `collection.add` を使ってチャンクを保存する

---

## 対象外

- 検索（`ChromaVectorDB.search`）は Phase 2-2 で実装する
- embedding の生成・付与は Phase 3-1 で実装する（今回の `Chunk.embedding` は `None` のまま）
- チャンク分割の改善（階層チャンクなど）は Phase 5 で扱う
- OCR フォールバックは今回のスコープ外
- `delete_document` の本実装は今回対象外（既に動く状態で残す）

---

## 完了条件

- `/ingest` ページから PDF をアップロードして status が `ready` になる
- アップロード後、Chroma 側のコレクションにチャンクが入っていることを確認できる
- 数十ページ規模の PDF でも取り込み API がタイムアウトせず非同期に処理が完了する

---

## 懸念事項

- 同一コレクションに複数ドキュメントを追加するケースがあるため、
  `create_collection` ではなく `get_or_create_collection` を使う必要がある

---

## 確認事項（決定済み）

- **Chroma の `ids` 形式**: `doc_{document_id}_chunk_{chunk_index}` を使う
  - 理由: document_id と chunk_index の意味が明確で、学習用途として可読性を優先
- **`main.py` の `except NotImplementedError` 節の削除**: 今回のスコープ外
  - 理由: PR のスコープを小さく保つ。リファクタ寄りの変更であるため
  - 対応: Phase 2-1 完了後の taskLog に残課題として記録する

---

## 関連ドキュメント

- Issue: #1 Phase 2-1: ファイル取り込みを動かす
- 実装対象: `backend/rag.py`, `backend/vector_db/chroma.py`
- 参考: `reference/ROAD_MAP.md` Phase 2-1 セクション
