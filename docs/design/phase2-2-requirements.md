# Phase 2-2 Requirements

## Requirements Summary

| 項目 | 内容 |
|---|---|
| Phase | Phase 2-2 |
| Issue | #2 |
| タイトル | キーワード検索を実装する |
| 目的 | RAG モード ON のチャットで、コレクション内の文書から関連箇所を取得して回答の根拠として返す最初の検索を動かす |
| 対象範囲 | `ChromaVectorDB.search` のキーワード検索実装、日本語トークナイズへの対応 |
| 対象外 | ベクトル検索、embedding 生成、rerank |
| 完了条件数 | 2 |
| 次工程 | Bolt Design |

---

## Phase情報

| 項目 | 内容 |
|---|---|
| Phase | 2-2 |
| タイトル | キーワード検索を実装する |
| Issue | #2 |

---

## 背景

Phase 2-1 で PDF の取り込みパイプライン（テキスト抽出 → チャンク分割 → Chroma への保存）が完成した。
現状では `ChromaVectorDB.search` が `NotImplementedError` を投げるため、
RAG モード ON で質問しても「参照できる文書がまだありません」という固定文言しか返らない。

Phase 2-2 では `search` を実装してキーワード検索を動かし、
取り込み済みの文書から関連チャンクを取得して LLM に渡せる状態にする。

---

## 目的

- `ChromaVectorDB.search` を実装し、RAG モードで検索ヒットが返るようにする
- 日本語クエリを考慮したキーワード検索で、ヒットする状態を確認できるようにする
- ヒットがない場合に「資料に記載がありません」と返る分岐が機能することを確認する

---

## 要件

| ID | 要件 |
|---|---|
| R-01 | `ChromaVectorDB.search` がキーワード一致で上位チャンクを返すこと |
| R-02 | 検索結果は `SearchResult` 型（`document_id`, `text`, `score`, `metadata`）のリストで返すこと |
| R-03 | 日本語クエリに対してトークナイズを考慮した検索ができること |
| R-04 | 検索ヒットがゼロの場合、`build_context` が `has_hits=False` を返すこと |
| R-05 | RAG モード ON で質問したとき、ヒットしたチャンクが回答の根拠として LLM に渡ること |

---

## 対象範囲

| ID | 内容 |
|---|---|
| S-01 | `backend/vector_db/chroma.py` の `ChromaVectorDB.search` を実装する |
| S-02 | 日本語トークナイズを考慮したキーワード検索を実装する |

---

## 対象外

| ID | 内容 |
|---|---|
| O-01 | ベクトル検索（cosine similarity）は Phase 3-2 で扱う |
| O-02 | embedding の生成・付与は Phase 3-1 で扱う |
| O-03 | ハイブリッド検索（キーワード + ベクトルの融合）は Phase 3-2 で扱う |
| O-04 | rerank の実装は Phase 6 で扱う |
| O-05 | `build_context` の返却フォーマット改善は今回スコープ外（現状フォーマットを維持） |
| O-06 | Phase 2-1 のレビュー指摘 L-1・L-2 対応は Phase 3-1 で実施 |

---

## テスト観点

| ID | 内容 |
|---|---|
| T-01 | 取り込み済みコレクションを選択し RAG モード ON で質問したとき、チャンクがヒットして回答の根拠として返ること |
| T-02 | コレクションに存在しないキーワードで質問したとき、「資料に記載がありません」が返ること |

---

## 完了条件

Issue #2 の完了判断をそのまま採用する。

### Acceptance Criteria

| ID | 条件 |
|---|---|
| AC-01 | 取り込み済みコレクションを選んで RAG モード ON で質問すると、ヒットしたチャンクが回答の根拠として返ること |
| AC-02 | ヒットがない場合は「資料に記載がありません」と返ること |

---

## 懸念事項

| ID | 内容 | 対応方針 |
|---|---|---|
| C-01 | 日本語は空白で単語が切れないため、素朴な split ではキーワード検索の精度が低くなりやすい | トークナイズの方式選択は Bolt Design で判断する。まず動かしてヒットしないクエリで挙動を観察することを想定 |
| C-02 | `SearchResult.score` の意味がキーワード検索とベクトル検索で異なる | Phase 2-2 ではキーワード一致スコアとして定義する。Phase 3-2 で再設計が必要になる可能性がある |

---

## 確認事項・決定事項

| 項目 | 内容 |
|---|---|
| 確認事項 | キーワード検索の具体的な方式（Chroma のテキストフィルタ vs 外部ライブラリ BM25 等）をどちらにするか |
| 決定事項 | Bolt Design で確認・決定する |
| 理由 | 要件レベルでは「キーワード一致ベースの検索」と定義し、実装方式は Bolt Design に委ねる |
| 対応方針 | 確認事項として Bolt Design に引き継ぐ |

---

## Bolt設計への引き継ぎ

- `ChromaVectorDB.search` のシグネチャはすでに `vectorDB.py` に定義済み（引数: `collection_id`, `query`, `top_k=5`）
- Phase 2-1 で保存した `metadata: {"document_id": document_id}` と ids 形式 `doc_{document_id}_chunk_{i}` を前提に設計してよい
- `rag.build_context` はすでに `vdb.search()` の結果をコンテキストに組み立てる実装が完成しており、`search` を実装するだけで RAG が動く構造になっている
- `search` が空リストを返した場合のヒットゼロパスは `rag.py` 側にすでに実装済み（AC-02 は自然に満たされる）
- C-01（日本語トークナイズ）の方式選択が Bolt 設計の最初の判断事項

---

## 関連ドキュメント

### Issue

- GitHub Issue #2: Phase 2-2: キーワード検索を実装する

### Related Documents

- Phase 2-1 Requirements: [docs/design/phase2-1-requirements.md](phase2-1-requirements.md)
- Phase 2-1 Summary: [docs/phaseSummary/phase2-1-summary.md](../phaseSummary/phase2-1-summary.md)

### Reference

- ROAD_MAP: [reference/ROAD_MAP.md](../../reference/ROAD_MAP.md)
