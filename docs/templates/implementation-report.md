Implementation Report Template

保存先

docs/implementation/

⸻

命名規則

phase<phase番号>-bolt-<bolt番号>.md

例

* phase2-1-bolt-0.md
* phase2-2-bolt-0.md
* phase3-1-bolt-0.md

⸻

Implementation Report

対象

* Issue #xx
* Phase X-X
* bolt-x

⸻

Summary

項目	内容
Phase	Phase X-X
Bolt	bolt-x
Issue	#xx
実装内容	xxx
変更ファイル数	xx
Verification	PASS / FAIL
Review Result	Approve / Request Changes
Remaining Issues	xxx
Next Action	TaskLog 作成

⸻

実装概要

今回の実装内容を要約する。

例

* PDFファイル取り込みパイプラインを実装
* ChromaDBへのチャンク保存を実装
* Phase 2-1 の完了条件を満たした

⸻

Changed Files

ファイル	種別	内容
xxx.py	追加	xxx
xxx.py	修正	xxx
xxx.py	削除	xxx

⸻

Verification

実施した確認内容と結果を記載する。

確認項目	結果
API起動	PASS
curl確認	PASS
テスト実行	PASS

⸻

Implementation Decisions

今回の実装で行った設計判断を記載する。

判断内容

* add ではなく upsert を採用
* Embedding は Phase 3-1 で実装予定
* Review 指摘は今回は対応しない

判断理由

* xxx
* xxx

⸻

Design Differences

設計との差異を記録する。

差異

* なし

または

* xxx

理由

* xxx

⸻

Remaining Issues

今回対応しなかった内容や今後の課題を記録する。

Remaining Issues

* xxx
* xxx

Future Improvements

* xxx
* xxx

⸻

Review Findings

Code Review で検出された指摘事項を整理する。

ID	Severity	内容	推奨対応
F-01	High	xxx	修正必須
F-02	Medium	xxx	修正推奨
F-03	Low	xxx	任意対応

⸻

Findings Handling Decision

Review Findings の最終判断を記録する。

Finding	修正要否	記録先	理由
F-01	対応済み	TaskLog	実装修正済み
F-02	未対応	GitHub Issue	独立対応が適切
F-03	未対応	Remaining Issues	優先度低

記録先

* TaskLog
* Remaining Issues
* GitHub Issue

⸻

Implementation Owner Opinion

必須ルール

Review Findings が存在する場合、

Implementation Owner Opinion を記載する前に
実装者確認を行うこと。

推測で記載しないこと。

⸻

実装者確認

* 指摘内容に同意するか
* 今回修正するか
* Remaining Issues に記録するか
* GitHub Issue 化するか
* TaskLog のみで管理するか

⸻

Agree

レビュー内容に同意する点

* xxx

⸻

Disagree

異なる見解がある場合

* xxx

⸻

Trade-offs

対応する場合・しない場合の影響

* xxx

⸻

Handover

次の bolt や Phase への引き継ぎ事項を記載する。

引き継ぎ事項

* Phase 3-1 で Embedding 実装
* bolt-1 で対応

または

* なし

⸻

Review Summary

項目	結果
Review Result	Approve / Request Changes
High	0
Medium	0
Low	0
Re-review Required	Yes / No

⸻

Review Notes

High

* xxx

Medium

* xxx

Low

* xxx

⸻

Review Fixes

レビュー指摘への対応内容を記録する。

対応内容

* Medium 指摘の変数名を修正
* Low 指摘は Phase 3 で対応予定

または

* 指摘なし

⸻

Issue Candidate Review

GitHub Issue 化候補を整理する。

課題	推奨対応	理由
xxx	Issue化	xxx
xxx	Remaining Issues	xxx

⸻

ユーザー確認

Issue 化候補がある場合は以下を確認する。

* GitHub Issue を作成する
* Remaining Issues のみで管理する
* TaskLog のみで管理する

ユーザー確認前に Issue を作成しないこと。

⸻

最終判断

課題	決定	理由
xxx	GitHub Issue	xxx
xxx	Remaining Issues	xxx
xxx	TaskLog	xxx

⸻

References

関連資料を記載する。

Requirements

* docs/design/phaseX-X-requirements.md

Bolt Design

* docs/design/phaseX-X-bolt-Y.md

Code Review

* docs/review/phaseX-X-bolt-Y.md

TaskLog

* docs/taskLog/phaseX-X-bolt-Y.md

PR

* PR URL

⸻

作成時のルール

* 実装完了後に作成する
* Code Review 完了後に更新する
* 実装結果とレビュー結果の両方を残す
* Review Findings の扱いを明記する
* 実装者確認後に Implementation Owner Opinion を記載する
* GitHub Issue 化はユーザー確認後に決定する
* TaskLog 作成前に作成する
* Commit 前に作成する
* 後から見返して実装経緯が分かる内容にする
* PR の参考資料として利用できる粒度で記載する
* 面接や振り返りでも利用できるレベルの判断理由を残す
* Summary だけ読めば実装内容が把握できる状態にする