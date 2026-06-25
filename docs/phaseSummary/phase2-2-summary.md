# Phase 2-2 Summary

## Summary

| 項目 | 内容 |
|---|---|
| Phase | Phase 2-2 |
| Issue | #2 |
| Pull Request | #11 |
| Bolt数 | 1（bolt-0 のみ） |
| 実装結果 | 完了 |
| Review結果 | Approve |
| Remaining Issues | 3 件 |
| 次Phase | Phase 3-1 |

---

## Phase概要

Phase 2-1 で PDF 取り込みパイプラインが完成したが、`ChromaVectorDB.search` が `NotImplementedError` のままであったため、RAG モード ON で質問しても固定文言しか返らない状態だった。Phase 2-2 では `search` を BM25 + 文字 bigram で実装し、取り込み済みドキュメントから関連チャンクを取得して LLM に渡す RAG パイプラインを end-to-end で動くようにした。

---

## 完了内容

- `backend/vector_db/chroma.py` に `_bigram`（文字 bigram トークナイザ）ヘルパーを追加
- `ChromaVectorDB.search` の `NotImplementedError` を BM25 キーワード検索で置き換え
- `pyproject.toml` に `rank-bm25>=0.2.2` を依存追加
- Docker 再ビルド・動作確認（T-01・T-02 PASS、ERROR ログなし）
- Phase 2-2 の設計ドキュメント一式を整備（requirements / bolt 設計 / implementation report / taskLog）
- PR #11 を作成・main にマージ

---

## 主な設計判断

| 項目 | 判断 | 理由 |
|---|---|---|
| 検索方式 | BM25（rank_bm25） | Issue の学習ポイント「BM25 の挙動と日本語での効きどころ」に直結。Chroma テキストフィルタでは BM25 スコアが得られない |
| 日本語トークナイザ | 文字 bigram（2 文字スライド） | 追加依存なしで日本語を扱える。「素朴な実装で一度動かしてから観察する」という Issue の方針に沿う |
| janome 不採用 | 今回は見送り | 最小実装を優先し依存を増やさない。検索精度改善は RI-01 として後続フェーズで判断 |
| score > 0 フィルタ | 有効ヒットのみ返す | BM25 スコアが 0 のものはクエリと無関係なチャンク。ヒットなしパスを正しく機能させるため |
| `_bigram` をヘルパーに切り出し | モジュールレベルのヘルパー | Phase 3-2 でトークナイザを差し替える際に `search` 本体を変えずに差し替えられる構成にするため |

---

## 実装内容

- **`_bigram`**: テキストを 2 文字ずつスライドさせてトークン列を生成するヘルパー関数。1 文字以下の入力も安全に処理できるよう境界ケースを考慮した
- **`ChromaVectorDB.search`**: `collection.get()` で全チャンク取得 → `_bigram` でトークナイズ → `BM25Okapi` でスコアリング → `score > 0` の上位 `top_k` 件を `SearchResult` のリストで返す。コレクション未存在・空コレクション時は例外なく空リストを返す

---

## Review結果

| Severity | 件数 |
|---|---|
| High | 0 |
| Medium | 0 |
| Low | 1 |

### 主な指摘

- [F-01] `chroma.py` のモジュール docstring に「検索系は NotImplementedError を投げて」という記述が残っており、`search` 実装後は内容が古くなっている（機能影響なし）

### 対応方針

- F-01（Low）: Remaining Issues として記録し後続フェーズで修正を検討

---

## Remaining Issues

| 課題 | 対応方針 |
|---|---|
| RI-01: janome 等の形態素解析で日本語検索精度を改善する | Future（検索精度改善時に判断） |
| RI-02: `main.py` の `except NotImplementedError` 節の削除（Phase 2-1 からの持ち越し） | taskLog 残課題のまま継続 |
| F-01: `chroma.py` のモジュール docstring が stale（機能影響なし） | 後続フェーズで修正を検討 |

---

## GitHub Issues

| Issue | 内容 | 状態 |
|---|---|---|
| #2 | Phase 2-2: キーワード検索を実装する | Closed（PR #11 でマージ済み）|
| #7 | chore: ruff を dev 依存に追加して lint を整備する | Open（Phase 2-1 からの持ち越し）|

---

## WorkLogからの振り返り

### 主な実装判断

- メモリ上での BM25 スコアリングを選択した。Chroma の検索 API は BM25 スコアを直接返さないため、`collection.get()` で全チャンクを取得しメモリ上でスコアを計算する構成にした
- `_bigram` をヘルパーに分離した。Phase 3-2 でトークナイザを差し替える際に `search` 本体を変えずに対応できる構成を意識した

### 発生した問題

- Docker イメージを再ビルドしないと `rank-bm25` が認識されない。`pyproject.toml` への依存追加だけでは足りず `docker compose up --build -d backend` が必要だった

### 解決方法

- `docker compose up --build -d backend` で再ビルドを実施し `rank-bm25` をインストールした

---

## 学んだこと

- **BM25 のスコアリング**: コーパス全体の単語頻度（IDF）とドキュメント内の頻度（TF）を組み合わせて関連度を算出する。クエリ語がコーパスに一切現れない場合はスコア 0 になるため、`score > 0` フィルタがヒットなし判定の自然な実装になる
- **文字 bigram の特性**: 「日本語」というクエリは「日本」「本語」のトークンに分解される。ドキュメント中に同じ 2 文字の並びが含まれていればヒットするが、単語境界を意識しないため、クエリの粒度によってヒットしやすさが大きく変わる
- **ヒットなしパスの設計**: `search` が空リストを返すと `build_context`（`rag.py:125`）が `has_hits=False` を返す。この分岐はすでに既実装であり、`search` を実装するだけで no-hit 時の「資料に記載がありません」が自動的に機能した
- **`collection.get()` の挙動**: 引数なしで全チャンクを返す。学習規模では問題ないが、本番スケールでは全件取得がボトルネックになりうる点を意識しておく

---

## 次Phaseへの引き継ぎ

### 次にやること

- Issue #3 Phase 3-1「embedding を実装する」へ進む
- `ChromaVectorDB.upsert` 時に実 embedding を生成・付与する実装を行う

### 注意事項

- `_bigram` はモジュールレベルのヘルパーとして切り出されており、Phase 3-2 でトークナイザを差し替える際はここを変更すればよい
- Phase 2-1 のレビュー指摘 L-1・L-2（`chroma.py:68` 付近の `any(c.embedding ...)` の書き方）は Phase 3-1 での embedding 実装時に合わせて修正する
- `search` が `SearchResult` のリストを返す構造は確定しており、Phase 3-2 でベクトル検索に差し替えても同じ型を維持する設計になっている

### 未対応事項

- RI-01: janome 等の形態素解析による日本語検索精度の改善（Future）
- RI-02: `main.py` の `except NotImplementedError` 節の削除（taskLog 残課題）
- F-01: `chroma.py` のモジュール docstring の更新（任意対応）
- embedding の生成・付与（Phase 3-1）
- ベクトル検索・ハイブリッド検索（Phase 3-2）
- ruff 導入（Issue #7）

---

## References

- Requirements: [docs/design/phase2-2-requirements.md](../design/phase2-2-requirements.md)
- Bolt Design: [docs/design/phase2-2-bolt-0.md](../design/phase2-2-bolt-0.md)
- Implementation Report: [docs/implementation/phase2-2-bolt-0.md](../implementation/phase2-2-bolt-0.md)
- TaskLog: [docs/taskLog/phase2-2-bolt-0.md](../taskLog/phase2-2-bolt-0.md)
- PR: [#11 feat(phase2-2): implement BM25 keyword search](https://github.com/rento01/chatpot_rag_practice/pull/11)
