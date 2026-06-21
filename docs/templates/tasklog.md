TaskLog Template

目的

今回の作業内容を学習ログとして記録する。

⸻

対象

* Issue #xx
* Phase X-X
* bolt-x

⸻

出力先

docs/taskLog/
phaseX-X-bolt-Y.md

⸻

Phase X-X bolt-Y

サマリー

項目	内容
目的	xxx
実施内容	xxx
変更ファイル	xxx
動作確認	PASS / FAIL
AIレビュー	Approve / Request Changes
課題	xxx
次の対応	xxx

⸻

基本情報

実施日

YYYY-MM-DD

対応Issue

#xx

bolt

bolt-x

⸻

目的

今回の bolt で達成したかったこと。

⸻

Requirements 対応

今回対応した Requirements を整理する。

対応項目

* xxx
* xxx

完了判定

* xxx
* xxx
* xxx

⸻

実施内容

* xxx
* xxx
* xxx

⸻

変更ファイル

ファイル	種別	内容
xxx.py	追加	xxx
xxx.py	修正	xxx
xxx.py	削除	xxx

⸻

実装概要

今回どのような実装を行ったかを説明する。

概要

xxx

⸻

実装判断

なぜその実装方針にしたか。

判断内容

* add ではなく upsert を採用
* Embedding は Phase 3-1 で実装予定のため対象外
* Review 指摘は今回は見送り

判断理由

xxx

⸻

動作確認

実施内容

* API起動確認
* curl確認
* UI確認
* テスト実行

結果

確認内容	結果
API起動	PASS
curl確認	PASS
UI確認	PASS
テスト実行	PASS

⸻

AIレビュー結果

Summary

* Approve
* Request Changes

High

なし

Medium

なし

Low

なし

⸻

Review Findings の対応

レビュー指摘に対する最終判断。

指摘	判断	理由
xxx	Remaining Issues	xxx
xxx	GitHub Issue	#xx

⸻

学んだこと

今回理解できたこと・気付きを記録する。

* xxx
* xxx
* xxx

⸻

課題

残っている課題。

Remaining Issues

* xxx
* xxx

GitHub Issues

* #xx
* #yy

⸻

次の bolt への引き継ぎ

次の bolt で対応すべき内容。

* xxx
* xxx

⸻

関連資料

Requirements

* docs/design/phaseX-X-requirements.md

Bolt Design

* docs/design/phaseX-X-bolt-Y.md

Implementation Report

* docs/implementation/phaseX-X-bolt-Y.md

Code Review

* docs/review/phaseX-X-bolt-Y.md

⸻

関連コミット

commit hash

⸻

関連PR

PR URL

⸻

作成時のルール

* 学習した内容を必ず残す
* なぜその実装にしたかを書く
* Review Findings の判断を残す
* GitHub Issue の有無を記録する
* 次の bolt が迷わないように引き継ぎを書く
* 後から見返して理解できる内容にする
* Claude Code が生成しても人間が読める形にする
* Implementation Report と矛盾しない内容にする
* サマリーだけ読めば作業内容が把握できる状態にする