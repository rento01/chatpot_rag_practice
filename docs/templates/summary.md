Phase Summary Template

目的

Phase完了後の内容を要約し、次Phaseへ引き継ぐためのサマリーを作成する。

以下のドキュメントを横断して確認し、重要事項のみを整理する。

* Requirements
* Bolt Design
* Implementation Report
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

PR Approve
↓
Merge
↓
Phase Summary 作成
↓
次Phase開始

⸻

作成時のルール

* Requirements を確認する
* Bolt Design を確認する
* Implementation Report を確認する
* TaskLog を確認する
* PR を確認する
* 実装されていない内容を記載しない
* Remaining Issues を記録する
* 次Phaseへの引き継ぎ事項を記録する
* 推測による判断は禁止
* Summaryだけ読めばPhase全体が把握できる状態にする

⸻

Phase X-X Summary

Summary

項目	内容
Phase	Phase X-X
Issue	#xx
Bolt数	x
実装結果	完了
Review結果	Approve
Remaining Issues	x件
次Phase	Phase X-X

⸻

完了内容

今回完了した内容。

* xxx
* xxx
* xxx

⸻

設計判断

重要な設計判断。

項目	判断	理由
xxx	xxx	xxx

⸻

実装内容

実装した機能。

* xxx
* xxx

⸻

Review結果

Severity	件数
High	0
Medium	0
Low	2

指摘内容

* xxx
* xxx

対応方針

* Phase X-X で対応

⸻

Remaining Issues

課題	対応方針
xxx	xxx

⸻

GitHub Issues

Issue	内容	状態
#7	ruff導入	Open

⸻

学んだこと

今回のPhaseで学んだこと。

* xxx
* xxx
* xxx

⸻

次Phaseへの引き継ぎ

次にやること

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
* Implementation Report
* TaskLog
* PR

Summary作成後は、
次Phaseへの引き継ぎ資料として十分かをユーザーへ確認すること。

ユーザー承認後にGit反映を提案すること。