# Development Flow

## 1. 目的

このドキュメントは、本プロジェクトの標準開発フローを定義する。

目的は以下のとおり。

* 開発フローを統一する
* 各工程で使用する Skill・Template を明確にする
* 人と Claude Code が共通で参照できる開発ガイドとする
* 現在の工程と次工程を迷わず進められるようにする

本ドキュメントは開発フローのみを管理する。

各工程の詳細な手順は対応する Skill を参照し、
成果物のフォーマットは Template を参照する。

⸻

## 2. 全体フロー

```
Issue / Phase 選択
        │
        ▼
前 Phase サマリー確認（Phase 着手時のみ）
        │
        ▼
Requirements 作成
        │
        ▼
Bolt Design
        │
        ▼
Feature Branch 作成
        │
        ▼
WorkLog 作成（ブランチ作成後・実装開始前）
        │
        ▼
Implementation（実装中も WorkLog を随時更新）
        │
        ▼
動作確認
        │
        ▼
Code Review
        │
        ▼
WorkLog 最終更新
        │
        ▼
TaskLog 作成
        │
        ▼
Commit Message 作成
        │
        ▼
Commit
        │
        ▼
Push
        │
        ▼
PR 本文作成
        │
        ▼
Pull Request 作成
        │
        ▼
Merge
        │
        ▼
Phase Summary 作成（Phase 最終 bolt のみ）
```

### 条件付きステップ

| 状況 | 追加ステップ | Template |
|---|---|---|
| 実装中にエラーが発生した場合 | Error Investigation | `error-investigation.md` |

⸻

## 3. 各工程

> 実装フロー全体（Step 5〜14）の詳細手順は `docs/templates/bolt_implementation.md` を参照する。

| Step | 工程 | 目的 | 使用 Skill | 使用 Template | 成果物 | 完了条件 |
|---|---|---|---|---|---|---|
| 0 | 前 Phase サマリー確認 | 前 Phase の完了状態・引き継ぎ事項を把握する（Phase 着手時のみ） | - | - | - | `docs/phaseSummary/` の該当ファイルを確認済み |
| 1 | Requirements | 要件整理 | - | `requirements.md` | Requirements | 要件が確定している |
| 2 | Bolt Design | bolt 単位へ分割・設計 | `bolt-planning` | `bolt-design.md` | Bolt Design | ユーザー確認完了 |
| 3 | Feature Branch | 作業ブランチ作成 | `github-workflow` | - | Feature Branch | ブランチ作成完了 |
| 4 | WorkLog 作成 | 作業記録の開始 | - | `worklog.md` | WorkLog | ファイル作成完了 |
| 5 | Implementation | 実装（WorkLog 随時更新） | - | - | 実装 | 実装完了 |
| 6 | 動作確認 | 実装確認 | - | - | 動作確認結果 | 要件を満たす |
| 7 | Code Review | 品質確認 | `code-review` | `code_review.md` | Code Review ファイル（`docs/review/`） | 指摘対応完了 |
| 8 | WorkLog 最終更新 | 作業記録の完結 | - | `worklog.md` | WorkLog（最終版） | 更新完了 |
| 9 | TaskLog | 作業記録（最終版） | - | `tasklog.md` | TaskLog | 作成完了 |
| 10 | Commit Message | Commit 内容整理 | - | `commit_message.md` | Commit Message | 作成完了 |
| 11 | Commit | Git 履歴保存 | `github-workflow` | - | Commit | Commit 完了 |
| 12 | Push | GitHub へ反映 | `github-workflow` | - | Push | Push 完了 |
| 13 | PR 本文作成 | PR 内容の整理・確認 | - | `pr_template.md` | PR 本文 | ユーザー確認完了 |
| 14 | Pull Request 作成 | レビュー依頼 | `github-workflow` | `pr_create.md` | Pull Request | PR 作成完了 |
| 15 | Merge | main へ反映 | - | - | Merge | Merge 完了 |
| 16 | Phase Summary | Phase 振り返り | - | `summary.md` | Phase Summary | Phase 完了 |

⸻

## 4. 成果物一覧

| 成果物 | 保存場所 |
|---|---|
| Requirements | `docs/design/` |
| Bolt Design | `docs/design/` |
| WorkLog | `tmp/worklog/` |
| TaskLog | `docs/taskLog/` |
| Code Review | `docs/review/` |
| Error Investigation | `docs/error/` |
| Commit Message | 一時利用（保存不要） |
| Pull Request | GitHub Pull Request |
| Phase Summary | `docs/phaseSummary/` |

⸻

## 5. 完了条件

### bolt 完了

以下を満たした時点で bolt 完了とする。

* Requirements が整理されている
* Bolt Design が完了している
* 実装が完了している
* 動作確認が完了している
* Code Review が完了している
* WorkLog が最終更新されている
* TaskLog が作成されている
* Commit・Push・Pull Request が完了している

⸻

### Phase 完了

以下を満たした時点で Phase 完了とする。

* Phase 内の全 bolt が完了している
* 最終 Pull Request が Merge されている
* Phase Summary が作成されている

⸻

## 6. 運用ルール

### フロー管理

* 本ドキュメントを開発フローの唯一の正（Single Source of Truth）とする。
* 開発フローを変更する場合は、本ドキュメントを更新する。
* Skill や Template に同じフローを重複して記載しない。

⸻

### Skill の役割

Skill は各工程の実施方法のみを担当する。

例

* `bolt-planning`
* `code-review`
* `github-workflow`

Skill は担当工程を超える処理を行わない。

⸻

### Template の役割

Template は成果物のフォーマットのみを管理する。

例

* `tasklog.md`
* `summary.md`
* `pr_template.md`

Template に開発フローは記載しない。

⸻

### Claude Code 運用

Claude Code は本ドキュメントを開発フローとして参照する。

各工程では対応する Skill を使用する。

各工程終了後は以下をユーザーへ報告する。

* 完了した工程
* 作成した成果物
* 次工程

ユーザーの確認を得てから次工程へ進む。

⸻

## 7. ドキュメントの責務

| ドキュメント | 役割 |
|---|---|
| `development_flow.md` | 開発フロー（唯一の正） |
| `CLAUDE.md` | Claude Code の共通ルール |
| `docs/templates/bolt_implementation.md` | Claude Code 向け実施手順書（詳細ルール） |
| `.claude/skills/*` | 各工程の詳細手順 |
| `docs/templates/*` | 成果物のテンプレート |

⸻

## 8. 更新ルール

以下の場合は本ドキュメントを更新する。

* 開発フローが変更された
* 新しい工程を追加した
* 工程の順番が変更された
* 新しい Skill を追加した
* 新しい Template を追加した

Template の内容変更のみであれば、本ドキュメントは更新しない。
