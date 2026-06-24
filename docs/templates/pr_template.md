Pull Request Template

目的

GitHub Pull Request 本文を作成する。

⸻

対象

* Issue #xx
* Phase X-X
* bolt-x

⸻

Pull Request

PR Summary

項目	内容
Phase	Phase X-X
Bolt	bolt-x
Issue	#xx
変更内容	xxx
動作確認	PASS / FAIL
実装判断	xxx
残課題	xxx
Review対象	xxx

⸻

Scope Check

項目	結果
Requirements Scope Only	Yes
Out Of Scope Included	No

⸻

背景

なぜこの対応が必要だったのか。

Background

* xxx
* xxx

⸻

変更内容

今回の変更内容を整理する。

Changes

* xxx
* xxx
* xxx

⸻

主な変更ファイル

ファイル	内容
xxx.py	xxx
xxx.md	xxx

⸻

確認方法

レビュー担当者が再現確認できるように記載する。

Verification Steps

1. xxx
2. xxx
3. xxx

⸻

動作確認結果

項目	結果
API起動	PASS
テスト	PASS
手動確認	PASS

⸻

Code Review 結果

項目	結果
Requirements整合性	PASS
設計整合性	PASS
可読性	PASS
保守性	PASS
エラーハンドリング	PASS

Review Findings

* xxx
* xxx

⸻

レビュー観点

特に確認してほしいポイント。

Review Points

* xxx
* xxx

⸻

関連Issue

* Issue #xx

⸻

関連TaskLog

* docs/taskLog/phaseX-X-bolt-Y.md

⸻

関連ドキュメント

Requirements

* docs/design/phaseX-X-requirements.md

Bolt Design

* docs/design/phaseX-X-bolt-Y.md

Code Review

* docs/review/phaseX-X-bolt-Y.md

⸻

補足事項

レビュー前に共有しておきたい内容。

* xxx

⸻

作成時のルール

* レビュー担当者が理解できる内容にする
* 変更理由を明記する
* 動作確認方法を記載する
* 関連Issueを明記する
* 関連TaskLogを記載する
* Requirements・Bolt Design・Code Reviewとの整合性を保つ
* 実装内容を簡潔にまとめる
* 推測による判断は禁止
* PR Summaryだけ読めば概要が分かる状態にする
* 実装判断と残課題を明記する