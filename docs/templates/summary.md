Phase Summary Template

目的

Phase 全体の成果を要約し、次 Phase へ引き継ぐためのサマリーを作成する。

以下のドキュメントを横断して確認し、重要事項のみを整理する。

* Requirements
* Bolt Design
* WorkLog
* TaskLog
* Pull Request

⸻

保存先

docs/phaseSummary/

⸻

命名規則

phase<phase番号>-summary.md

例

phase2-1-summary.md
phase2-2-summary.md
phase3-1-summary.md

⸻

作成タイミング

TaskLog 完了
↓
Commit
↓
Push
↓
PR 本文作成
↓
PR 作成
↓
Merge
↓
Phase Summary 作成
↓
次 Phase 開始

⸻

作成時のルール

以下の内容を確認する。

* Requirements
* Bolt Design
* WorkLog
* TaskLog
* Pull Request

以下を遵守すること。

* 実装されていない内容を記載しない
* 推測による判断は禁止
* Remaining Issues を整理する
* GitHub Issue を整理する
* Phase 全体の設計判断を整理する
* Phase 全体の学びを整理する
* 次 Phase への引き継ぎ事項を整理する
* Summary だけ読めば Phase 全体が把握できる状態にする

⸻

Phase X-X Summary

Summary

項目	内容
Phase	Phase X-X
Issue	#xx
Pull Request	#xx
Bolt数	x
実装結果	完了
Review結果	Approve
Remaining Issues	x件
次Phase	Phase X-X

⸻

Phase概要

今回の Phase の目的と成果を簡潔にまとめる。

⸻

完了内容

今回完了した内容。

* xxx
* xxx
* xxx

⸻

主な設計判断

Phase 全体で重要だった設計判断を整理する。

項目	判断	理由
xxx	xxx	xxx

⸻

実装内容

実装した機能を整理する。

* xxx
* xxx

⸻

Review結果

Severity	件数
High	0
Medium	0
Low	2

主な指摘

* xxx
* xxx

対応方針

* Phase X-X で対応
* GitHub Issue #xx へ登録

⸻

Remaining Issues

課題	対応方針
xxx	xxx

⸻

GitHub Issues

Issue	内容	状態
#7	ruff導入	Open

⸻

WorkLogからの振り返り

WorkLog を確認し、Phase 全体で重要だった内容のみ整理する。

主な実装判断

* xxx
* xxx

発生した問題

* xxx

解決方法

* xxx

⸻

学んだこと

今回の Phase を通して学んだこと。

* xxx
* xxx
* xxx

⸻

次 Phase への引き継ぎ

次に実施する内容

* xxx
* xxx

注意事項

* xxx

未対応事項

* xxx

⸻

References

* Requirements
* Bolt Design
* WorkLog
* TaskLog
* Pull Request

⸻

完了確認

Phase Summary 作成後は以下を確認する。

* Phase 全体を要約できているか
* Remaining Issues が整理されているか
* 次 Phase の担当者が Summary のみで作業を開始できるか
* TaskLog・WorkLog・PR の内容と整合しているか

確認後、ユーザーへ以下を報告する。

* Phase Summary 作成完了
* Remaining Issues 件数
* 次 Phase の開始可否

ユーザー承認後に Git 反映を提案する。