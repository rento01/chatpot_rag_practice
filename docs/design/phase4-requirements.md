# Phase 4 Requirements

## Requirements Summary

| 項目 | 内容 |
|---|---|
| Phase | Phase 4 |
| Issue | #6 |
| タイトル | Langfuse でトレースを取る |
| 目的 | チャットと取り込みの内部処理を可視化し、品質改善のサイクルを回せるようにする |
| 対象範囲 | tracing.py 有効化・chat / index-document トレースへの子 span 追加 |
| 対象外 | Langfuse self-host 設定・評価スコア・カスタムダッシュボード |
| 完了条件数 | 2 |
| 次工程 | Bolt Design |

---

## Phase 情報

| 項目 | 内容 |
|---|---|
| Phase | 4 |
| タイトル | Langfuse でトレースを取る |
| Issue | #6 |

---

## 背景

Phase 3-3 まででハイブリッド検索（BM25 + ベクトル + RRF）が動作するようになったが、処理内部が見えていない。

- どの span で時間がかかっているか
- 検索ヒット数やコンテキストの長さが適切か
- LLM に渡しているプロンプトと返答の内容

これらを観測しないと RAG の品質改善サイクルを回せない。

`backend/tracing.py` には no-op ラッパが実装済みで、`backend/main.py` にはトップレベルの `trace("chat")` と `trace("index-document")` が既に存在する。ただし子 span がないため Langfuse ダッシュボード上でスパンツリーとして表示できない。

---

## 目的

1. Langfuse ダッシュボードで 1 件のチャットをスパンツリーとして確認できる状態を作る
2. `LANGFUSE_*` キーが未設定でもアプリが従来通り動く状態を維持する

---

## 要件

| ID | 要件 |
|---|---|
| R-01 | `chat` トレース内に RAG 検索・LLM 生成の子 span/generation が存在すること |
| R-02 | `index-document` トレース内にテキスト抽出・チャンク分割・embedding 生成・upsert の子 span が存在すること |
| R-03 | `LANGFUSE_SECRET_KEY` / `LANGFUSE_PUBLIC_KEY` が未設定の場合、全 span が no-op として動作しアプリに影響を与えないこと |
| R-04 | 既存の `trace("chat")` / `trace("index-document")` のトップレベル構造を維持すること |

---

## 対象範囲

| ID | 内容 |
|---|---|
| S-01 | `backend/tracing.py` の整備（子 span 作成に必要な公開インタフェースの整理） |
| S-02 | `backend/main.py` の `_build_messages` 関数への `trace_ctx` 引数追加、検索 span の追加 |
| S-03 | `backend/main.py` の `token_stream` 内での LLM 生成 generation span 追加 |
| S-04 | `backend/rag.py` の `index_document` 関数への `trace_ctx` 引数追加、各処理ステップへの span 追加 |

---

## 対象外

| ID | 内容 |
|---|---|
| O-01 | Langfuse self-host（Docker Compose への langfuse サービス追加） |
| O-02 | 評価スコア（Langfuse のスコア機能・LLM-as-judge） |
| O-03 | カスタムダッシュボード・アラート設定 |
| O-04 | `rag.build_context` / `vdb.search` 内への span 追加（Phase 4 では外側でまとめて計測） |
| O-05 | Langfuse Cloud のプロジェクト作成手順（ユーザー自身が実施） |

---

## テスト観点

| ID | 内容 |
|---|---|
| T-01 | `LANGFUSE_*` 未設定でチャットが正常にストリームされること |
| T-02 | `LANGFUSE_*` 未設定でドキュメントアップロード→ステータス `ready` になること |
| T-03 | `LANGFUSE_*` 設定済みで Langfuse ダッシュボードに chat トレースが span ツリーとして表示されること |

---

## 完了条件

### Acceptance Criteria

| ID | 条件 |
|---|---|
| AC-01 | Langfuse ダッシュボードで 1 件のチャットを span ツリー（trace > rag-search span / llm-generation span）として開ける |
| AC-02 | `LANGFUSE_SECRET_KEY` / `LANGFUSE_PUBLIC_KEY` を空にしてもアプリは従来通り動く |

---

## 懸念事項

| ID | 内容 | 対応方針 |
|---|---|---|
| C-01 | `token_stream` はジェネレータ関数。`with trace(...)` 内で `yield` するため span の終了タイミングが遅延する | Langfuse の flush は `trace()` の finally で行われているため、ストリーム完了後に flush される。動作上問題ない |
| C-02 | `trace_ctx` を `_build_messages` / `index_document` に渡すと関数シグネチャが変わる | デフォルト引数 `trace_ctx=None` にして後方互換を維持する |
| C-03 | `rag.py` が現在 `tracing` モジュールを import していない | Phase 4 で import を追加する |

---

## 確認事項・決定事項

| 項目 | 内容 |
|---|---|
| 確認事項 | Langfuse Cloud への接続確認はユーザー自身が実施する（クレデンシャル取得・.env 設定） |
| 決定事項 | Cloud 版を使用する（Issue #6 の方針に従う） |
| 理由 | ローカルの方が扱いやすいが、Issue に「Cloud または self-host」とあり Cloud の方がセットアップコストが低い |
| 対応方針 | `.env` の `LANGFUSE_SECRET_KEY` / `LANGFUSE_PUBLIC_KEY` に Cloud のキーを設定すれば動く。既存 `.env.example` に項目あり |

---

## Bolt 設計への引き継ぎ

- `trace()` が yield するオブジェクトは、Langfuse 有効時は `StatefulTraceClient`、無効時は `_NoopSpan`。どちらも `.span()` / `.generation()` / `.end()` を持つ
- `_NoopSpan` は現在 private。他モジュールから安全に使える形にするか、import せずに使える設計にする
- `rag.py` の `index_document` に `trace_ctx=None` を追加し、main.py から trace オブジェクトを渡す
- `_build_messages` に `trace_ctx=None` を追加し、`token_stream` から呼び出す形にする
- chat の span ツリー構造: `chat（trace）> rag-search（span）/ llm-generation（generation）`
- index-document の span ツリー構造: `index-document（trace）> extract / split / embed / upsert（各 span）`

---

## 関連ドキュメント

### Issue

- GitHub Issue #6

### Related Documents

- `backend/tracing.py`
- `backend/main.py`
- `backend/rag.py`
- `reference/ROAD_MAP.md`（Phase 4）
- `docs/phaseSummary/phase3-3-summary.md`（引き継ぎ事項）

### Reference

- Langfuse Python SDK: https://langfuse.com/docs/sdk/python
- Langfuse Cloud: https://cloud.langfuse.com
