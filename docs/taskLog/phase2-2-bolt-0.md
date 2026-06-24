# Phase 2-2 bolt-0

## サマリー

| 項目 | 内容 |
|---|---|
| 目的 | `ChromaVectorDB.search` を BM25 + 文字 bigram で実装し、RAG 検索を end-to-end で動かす |
| 実施内容 | `ChromaVectorDB.search` 実装、`rank-bm25` 依存追加 |
| 変更ファイル | 2 ファイル（`chroma.py` 修正・`pyproject.toml` 修正） |
| 動作確認 | PASS（T-01・T-02 確認済み、ERROR ログなし） |
| AIレビュー | Approve（High: 0 / Medium: 0 / Low: 1） |
| 課題 | janome 対応（RI-01）、`main.py` NotImplementedError 節（RI-02） |
| 次の対応 | Phase 3-1（embedding 実装）へ進む |

---

## 基本情報

### 実施日

2026-06-24

### 対応Issue

#2

### bolt

bolt-0

---

## 目的

`ChromaVectorDB.search` の `NotImplementedError` を BM25 キーワード検索で置き換え、
RAG モード ON のチャットで取り込み済みドキュメントからヒットが返るようにする。

Issue #2 の完了条件：
- 取り込み済みコレクションを選んで RAG モード ON で質問するとヒットしたチャンクが回答の根拠として返る
- ヒットがない場合は「資料に記載がありません」と返る

---

## Requirements 対応

### 対応項目

- R-01: `ChromaVectorDB.search` がキーワード一致で上位チャンクを返す
- R-02: `SearchResult` 型（`document_id`, `text`, `score`, `metadata`）で返す
- R-03: 日本語クエリに対してトークナイズを考慮した検索（文字 bigram）
- R-04: ヒットゼロ時に `build_context` が `has_hits=False` を返す
- R-05: RAG モード ON で質問したとき、ヒットしたチャンクが LLM に渡る

### 完了判定

- AC-01: RAG モード ON でクエリを送ると `has_hits=True` が返り LLM にコンテキストが渡ること → 動作確認待ち
- AC-02: ヒットなし時に「資料に記載がありません」が返ること → 動作確認待ち

---

## 実施内容

- `backend/vector_db/chroma.py` に `_bigram` ヘルパーを追加（文字 bigram トークナイザ）
- `ChromaVectorDB.search` の `NotImplementedError` を BM25 キーワード検索で置き換え
- `pyproject.toml` に `rank-bm25>=0.2.2` を追加

---

## 変更ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `backend/vector_db/chroma.py` | 修正 | `_bigram` 追加・`search` 実装（NotImplementedError を置き換え） |
| `pyproject.toml` | 修正 | `rank-bm25>=0.2.2` を依存に追加 |

---

## 実装概要

### _bigram

テキストを 2 文字ずつスライドさせてトークン列を生成するヘルパー。
日本語は空白で単語が切れないため、文字単位のスライドウィンドウで対応する。
1 文字以下の入力も安全に処理できるよう境界ケースを考慮した。

### ChromaVectorDB.search

1. `collection.get()` でコレクションの全チャンクを取得
2. `_bigram` でクエリとドキュメントをトークナイズ
3. `BM25Okapi` にコーパスを渡してスコアを算出
4. `score > 0` の上位 `top_k` 件を `SearchResult` のリストで返す
5. コレクション未存在・チャンクゼロの場合は空リストを返す（`build_context` の no-hit パスが自然に機能する）

---

## 実装判断

### 判断内容

- BM25（`rank_bm25`）を採用し、Chroma テキストフィルタ（`where_document`）は使用しない
- 日本語トークナイザは文字 bigram とし、janome 等の形態素解析は導入しない
- `_bigram` をモジュールレベルのヘルパーとして切り出す

### 判断理由

| 判断 | 理由 |
|---|---|
| BM25 採用 | Issue の学習ポイント「BM25 の挙動と日本語での効きどころ」に直結。Chroma テキストフィルタでは BM25 スコアが得られない |
| 文字 bigram 採用 | 追加依存なしで日本語を扱える。Issue の「素朴な実装で一度動かしてから観察する」方針に沿う |
| janome 見送り | 依存を増やさず最小実装を優先。検索精度改善は RI-01 として後続フェーズで判断 |
| `_bigram` をヘルパーに切り出し | Phase 3-2 でトークナイザを差し替える際、`search` 本体を変えずに呼び出し箇所だけ変更できる構成にするため |

---

## 動作確認

### 実施内容

- `docker compose up --build -d backend` で Docker イメージを再ビルド（`rank-bm25` の追加のため必要）
- T-01：RAG モード ON でコレクションを選択し質問 → ヒットしたチャンクが回答根拠として返ること
- T-02：コレクションに存在しないキーワードで質問 → 「資料に記載がありません」が返ること
- `docker compose logs -f backend` でエラーなし確認

### 結果

| 確認内容 | 結果 |
|---|---|
| T-01：ヒットが返ること | PASS（RAG モード ON で検索ヒットを確認） |
| T-02：ヒットなし時の応答 | PASS（「資料に記載がありません」が返ることを確認） |
| バックエンドログに ERROR なし | PASS（WARNING 1 件あるが設計どおりの動作、詳細は下記） |

### ログ確認補足

`WARNI コレクション削除に失敗しました: collection_id=4`
→ 存在しないコレクションへの削除要求を `delete_collection` の `try/except` が正常にキャッチしたもの。設計どおりの動作のため問題なし。

---

## AIレビュー結果

### Summary

Approve

### High

なし

### Medium

なし

### Low

- [F-01] `chroma.py` のモジュール docstring に「検索系は NotImplementedError を投げて」という記述が残っており、`search` 実装後は内容が古くなっている（機能影響なし）

---

## Review Findings の対応

| 指摘 | 判断 | 理由 |
|---|---|---|
| F-01（Low）: モジュール docstring が stale | Remaining Issues | 機能影響なし。任意対応として記録し後続フェーズで修正を検討 |

---

## 学んだこと

- **BM25 のスコアリング**: コーパス全体の単語頻度（IDF）とドキュメント内の頻度（TF）を組み合わせて関連度を算出する。クエリ語がコーパスに一切現れない場合はスコア 0 になるため、`score > 0` フィルタがヒットなし判定の自然な実装になる
- **文字 bigram の特性**: 「日本語」というクエリは「日本」「本語」のトークンに分解される。ドキュメント中に「日本語」という連続した 2 文字が含まれていればヒットするが、「日本」と「語」が離れていてもヒットしない。形態素解析と異なり単語境界を意識しない分、クエリの粒度によってヒットしやすさが大きく変わる点を観察できる
- **ヒットなしパスの設計**: `search` が空リストを返すと `build_context`（`rag.py:125`）が `has_hits=False` を返す。この分岐はすでに既実装であり、`search` を実装するだけで no-hit 時の「資料に記載がありません」が自動的に機能した
- **`collection.get()` の挙動**: Chroma の `get()` は引数なしで全チャンクを返す。学習規模（数千チャンク）ではメモリ上での BM25 スコアリングが成立するが、本番スケールでは全件取得がボトルネックになりうることを意識しておく

---

## 課題

### Remaining Issues

- RI-01: janome 等の形態素解析で日本語検索精度を改善する（検索精度改善時に判断）
- RI-02: `main.py` の `except NotImplementedError` 節の削除（Phase 2-1 からの持ち越し）
- F-01: `chroma.py` のモジュール docstring が stale（機能影響なし、任意対応）

### GitHub Issues

- #7: `chore: ruff を dev 依存に追加して lint を整備する`（Phase 2-1 からの持ち越し、Open）

---

## 次の bolt への引き継ぎ

なし（bolt-0 = Issue #2 完了）

**次の Phase**: Phase 3-1（embedding 実装）へ進む

---

## 関連資料

### Requirements

- [docs/design/phase2-2-requirements.md](../design/phase2-2-requirements.md)

### Bolt Design

- [docs/design/phase2-2-bolt-0.md](../design/phase2-2-bolt-0.md)

### Implementation Report

- [docs/implementation/phase2-2-bolt-0.md](../implementation/phase2-2-bolt-0.md)

---

## 関連コミット

（コミット後に記録）

---

## 関連PR

（PR 作成後に記録）
