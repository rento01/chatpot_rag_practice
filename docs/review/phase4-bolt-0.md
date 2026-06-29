# Code Review

## 対象

| 項目 | 内容 |
|---|---|
| Issue | #6 |
| Phase | Phase 4 |
| Bolt | bolt-0 |
| レビュー日 | 2026-06-29 |

---

## Review Summary

| 項目 | 結果 |
|---|---|
| Phase | Phase 4 |
| Bolt | bolt-0 |
| Review Result | Request Changes |
| High | 1 |
| Medium | 1 |
| Low | 1 |
| Overall Risk | High |
| Next Action | F-01 修正後に再レビュー |

---

## 1. Requirements・Bolt 設計との整合性

### 確認観点

- Requirements を満たしているか
- bolt 設計の目的を満たしているか
- 作るもの / 作らないものを守っているか
- スコープ超過がないか

### レビュー結果

- R-01（`chat` トレースに `rag-search` / `llm-generation` span）: 満たしている
- R-02（`index-document` トレースに `extract` / `split` / `embed` / `upsert` span）: 満たしている
- R-03（`LANGFUSE_*` 未設定時は no-op）: 満たしている
- R-04（既存トップレベルトレース構造を維持）: 満たしている
- AC-01（Langfuse ダッシュボードで span ツリー確認）: ユーザーが確認済み
- AC-02（`LANGFUSE_*` 空でアプリが動く）: `_init()` の早期 return で保証されている

スコープ超過なし。

---

## 2. コード品質

### 確認観点

- 命名は分かりやすいか
- 関数やクラスの責務は明確か
- 不要な import や未使用コードはないか

### レビュー結果

- `tracing.py`: `trace()` / `span()` / `generation()` の責務分離が明確。OTel 方式への移行コメントも適切
- `main.py`: `_build_messages` の docstring が実装と整合している（`span("rag-search") は OTel コンテキスト経由`）
- `rag.py`: `tracing_span` という alias は `span` との名前衝突を避けるための意図が明確
- `_init()` の遅延初期化パターンは教材として読みやすい

---

## 3. バグリスク

### 確認観点

- 例外処理は適切か
- 想定外ケースで落ちないか

### レビュー結果

- `trace()` の `finally: _langfuse.flush()` は正常系・例外系どちらでも flush される
- `span()` / `generation()` の Langfuse 無効時は `NoopSpan()` を yield し、`.update()` / `.end()` が安全に呼べる
- `_build_messages` で `rag_ctx` は `with span(...) as s:` ブロック内で定義されるが、ブロック外（`if rag_ctx.has_hits:`）で参照している。`with` ブロック内で例外が発生しなければ問題ないが、可読性の観点で注意点として挙げておく（Low）

---

## 4. 保守性

### 確認観点

- 将来修正しやすいか
- ハードコードが増えていないか

### レビュー結果

- span 名（`"rag-search"` / `"llm-generation"` / `"extract"` / `"split"` / `"embed"` / `"upsert"`）は文字列リテラルだが、Langfuse のダッシュボードで表示される名前であり定数化の必要性は低い
- `Langfuse()` の初期化引数（`public_key` / `secret_key` / `host`）が `settings` 経由で渡されており、ハードコードなし

---

## 5. セキュリティ観点

### 確認観点

- 秘密情報を出力していないか
- APIキー・トークンがコードに含まれていないか

### レビュー結果

- **[BLOCKER] `.env.example` に実際の API キーが含まれている**（F-01 参照）
- `tracing.py` / `main.py` / `rag.py` には秘密情報なし
- ログ出力に API キーは含まれていない

---

## 6. 動作確認・テスト観点

### 確認観点

- bolt 完了条件を満たしているか

### レビュー結果

- T-01（`LANGFUSE_*` 未設定でチャットが正常ストリーム）: ユーザーが動作確認済み
- T-02（`LANGFUSE_*` 未設定でドキュメントアップロード → `ready`）: ユーザーが動作確認済み
- T-03（`LANGFUSE_*` 設定済みで span ツリー表示）: ユーザーが確認済み（JP エンドポイントで受信を確認）
- T-04（`use_rag=False` 時に `rag-search` span が存在しない）: コードレベルでは `_build_messages` の `if req.use_rag` 分岐で保証されている

---

## 7. 学習観点

### 学習ポイント

- Langfuse SDK のメジャーバージョン間の破壊的変更（v3 → v4）と、上限なし依存指定のリスク（`>=2.0.0` で v4 がインストールされた）
- OTel コンテキスト伝播による親子 span の自動管理：`trace_ctx` を引き回すより、コンテキストマネージャが自動で親子関係を構築する方がシンプル
- `contextmanager` デコレータを使った no-op / 実装の透過的な切り替えパターン
- Docker イメージ焼き込み構成でのコード反映手順（`--build` + stop → up）

---

## Good Points

- `_init()` の遅延初期化 + `_initialized` フラグで、未設定時の副作用ゼロを保証している
- `NoopSpan` の設計がシンプルで、呼び出し元が Langfuse の有無を意識しなくてよい
- `settings` 経由で `LANGFUSE_HOST` を渡すことで、変数名の不一致問題を根本から解消している
- `rag.py` の span が `with tracing_span(...) as s:` のコンテキストマネージャ形式で書かれており、例外時でも span が閉じられる

---

## Findings

| ID | Severity | 内容 | 推奨対応 |
|---|---|---|---|
| F-01 | High | `.env.example` に実際の Langfuse API キー（`sk-lf-...` / `pk-lf-...`）が含まれている。コミットするとシークレットが公開リポジトリに漏洩する | コミット前に必ずプレースホルダーに差し戻す |
| F-02 | Medium | `.env.example` の変数名が `LANGFUSE_BASE_URL` であり、`settings.py` / `docker-compose.yml` の `LANGFUSE_HOST` と不一致。学習者が `.env.example` を見て `.env` を設定する際に混乱する | `LANGFUSE_HOST` に統一し、JP リージョン利用時のコメントを追加 |
| F-03 | Low | `_build_messages` で `rag_ctx` が `with span(...) as s:` ブロック内で定義され、ブロック外で参照されている。Python のスコープ上は問題ないが、ブロック外で参照するのは可読性が低い | 任意対応（変数をブロック外で宣言するか、ブロック内で返すように整理） |

---

## Remaining Issues

| ID | 内容 | 理由 | 対応予定 |
|---|---|---|---|
| RI-01 | generation の `usage`（input_tokens / output_tokens）が記録できない | Ollama はストリーム時にトークン数を返さない | Phase 7（Bedrock 移行）後 |
| RI-02 | `rag.build_context` / `vdb.search` 内の span が存在しない | Phase 4 では外側の `rag-search` span でまとめて計測で十分 | 必要になったタイミングで追加 |

---

## Final Judgment

| 項目 | 判定 |
|---|---|
| Result | Request Changes |
| Ready for Next Step | No（F-01 修正後に Yes） |
| Re-review Required | No（F-01 修正の目視確認のみで可） |

---

## Next Action

**F-01（High）を修正してからコミットすること。**

F-01 修正内容:
- `.env.example` の `LANGFUSE_SECRET_KEY` / `LANGFUSE_PUBLIC_KEY` をプレースホルダー（空文字）に差し戻す
- `LANGFUSE_BASE_URL` → `LANGFUSE_HOST` に変数名を修正（F-02 も同時対応）
- JP リージョン利用時のコメントを追加

F-02 は F-01 と同時対応を推奨。F-03 は Remaining Issues に記録して対応任意。

---

## Related Issues

- GitHub Issue #6: Phase 4: Langfuse でトレースを取る
- Error Investigation: `docs/error/20260629-langfuse-trace-not-delivered.md`
