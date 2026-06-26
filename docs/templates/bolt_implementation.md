Implementation Template

目的

対象 bolt を実装する。

⸻

対象

Issue #xx

Phase X-X

bolt-x

⸻

実装対象設計書

* docs/design/phaseX-X-requirements.md
* docs/design/phaseX-X-bolt-x.md

⸻

ブランチ作成

Issue内容と命名規則を確認し、

適切なブランチ名を提案してください。

命名規則

* feature/<issue-number>-short-name

* fix/<issue-number>-short-name

* docs/<issue-number>-short-name

* infra/<issue-number>-short-name

出力内容

* 推奨ブランチ名

* 代替案（任意）

* 命名理由

* 作成コマンド

例

ブランチ名

feature/1-phase2-1-pdf-ingestion

代替案（任意）

* feature/1-pdf-ingestion
* feature/phase2-1-pdf-ingestion

理由

* feature = 新機能

* Issue #1 対応

* Phase 2-1 PDF取り込み機能

作成コマンド

git checkout main

git pull origin main

git checkout -b feature/1-phase2-1-pdf-ingestion

⸻

以下を実施してください

1. 実装前確認

まず説明してください。

bolt概要

* この bolt の目的
* 実装対象範囲
* 実装対象外

実装計画

* 変更対象ファイル
* 実装方針
* 確認方法
* 想定影響範囲

リスク確認

* 実装時の懸念事項
* 設計との不整合がないか

実装前確認の結果を提示した後は停止してください。

以下のいずれかの指示を待ってください。

- 「実装してください」
- 「ブランチを切りました」
- 「続けてください」

これらの指示があるまで実装は開始しないでください。

⸻

2. 実装

bolt 設計に従って実装してください。

設計から逸脱する場合は実装前に確認してください。

⸻

3. 実装結果整理

変更内容

* xxx

⸻

変更ファイル一覧

* xxx

⸻

実施した確認

* xxx

⸻

実装判断

設計時に決まっていなかった事項で、
実装中に判断した内容を整理してください。

* xxx
* xxx

⸻

設計との差異

* なし

または

* xxx

理由

* xxx

⸻

残課題

* xxx

⸻

次の bolt への引き継ぎ

* xxx

⸻

taskLog作成用メモ

taskLogに残すべき内容を整理してください。

* 実装内容
* 発生した問題
* 解決方法
* 学んだこと

⸻

制約

* bolt 範囲外の実装をしない
* Requirements の対象外を実装しない
* 過剰な抽象化をしない
* 設計変更が必要なら実装前に確認する
* 変更ファイル数が5を超えそうなら報告する
* 差分が500行を超えそうなら報告する
* 既存機能を壊さない
* 実装完了後に taskLog 用の情報を整理する

⸻

出力形式

Implementation Result

Summary

実装完了

または

一部完了

または

実装保留

⸻

Changed Files

* xxx

⸻

Verification

* xxx

⸻

Implementation Decisions

* xxx

⸻

Design Differences

* xxx

⸻

Remaining Issues

* xxx

⸻

Handover

* xxx

⸻

TaskLog Notes

* xxx

次工程

実装完了後は以下の順序で進める。

1. WorkLog 更新
2. git diff 確認（Claude確認）
3. 動作確認（人間確認）
4. Code Review
5. 必要であれば修正
6. 再度動作確認（人間確認）
7. WorkLog 最終更新
8. TaskLog 作成
9. Commit
10. Push
11. PR 本文を作成する
12. PR 作成
13. Phase Summary 作成（Phase 最終 bolt の場合）

⸻

WorkLog 運用ルール

WorkLog は作業中の記録として扱う。

TaskLog の下書きではなく、以下を記録するために使用する。

* 実装前の調査内容
* 実装中の判断
* 発生した問題
* エラー対応内容
* 作業再開時に必要な情報

作成タイミング

* feature ブランチ作成後
* 実装開始前

更新タイミング

* 実装完了時
* Code Review 完了時
* 作業を中断する場合
* 別日に作業を再開する場合
* Claude Code のセッションが終了する可能性がある場合

実装完了時は、Claude が WorkLog を更新したうえで、
以下を次工程として提案する。

1. git diff 確認
2. 動作確認

例

実装が完了しました。

WorkLog を更新しました。

更新内容

* 実装ログ反映
* エラー対応ログ反映
* 調査結果反映

次工程として以下を推奨します。

1. git diff 確認
2. 動作確認

実施しますか？

例

Code Review が完了しました。

WorkLog を最終更新しました。

更新内容

* Review Findings反映
* 残課題更新
* 次回作業更新

次工程として以下を推奨します。

1. TaskLog 作成

実施しますか？

TaskLog 作成後は、Claude が以下を次工程として提案する。

1. Commit
2. Push
3. PR 本文作成
4. PR 作成

例

「TaskLog が作成されました。

次工程として以下を推奨します。

1. Commit
2. Push
3. PR 本文作成
4. PR 作成

実施しますか？」

PR 作成後は、Claude は
Requirements または Bolt Design を確認し、
現在の bolt が Phase の最終 bolt であるか判断する。

Phase の最終 bolt の場合は、
次工程として Phase Summary の作成を提案する。

判断できない場合は、
ユーザーへ確認する。

例

「PR の作成が完了しました。

現在の bolt は Phase の最終 bolt と判断しました。

次工程として以下を推奨します。

1. Phase Summary 作成

Phase Summary を作成しますか？」

⸻

進行ルール

各工程が完了したら、自動的に次工程へ進まないこと。

必ず以下を実施すること。

1. 完了報告

* 実施内容
* 確認結果
*実施できなかった内容
* 残課題

を整理して報告する。

WorkLog更新

git diff確認

動作確認

については、

Claude が必要と判断した場合は
ユーザー確認なしに実施してよい。

ただし結果は必ず報告する。

2. 次工程提案

次に実施する工程を提案する。

例

* WorkLog を更新する
* git diff 確認を行う（Claude確認）
* 動作確認を行う（人間確認）
* Code Review に進む
* 修正対応を行う
* WorkLog を最終更新する
* TaskLog を作成する
* Commit を実施する
* Push を実施する
* PR 本文を作成する
* PR を作成する
* Phase Summary を作成する

3. ユーザー確認

次工程へ進む前に必ず確認する。

例

「Code Review に進みますか？」

「TaskLog を作成しますか？」

「Commit を実施しますか？」

「PR 本文を作成しますか？」

「PR を作成しますか？」

「Phase Summary を作成しますか？」

4. 禁止事項

ユーザー確認なしに以下を実施しないこと。

* Code Review
* 修正
* TaskLog 作成
* Commit
* Push
* PR 本文作成
* PR 作成
* Merge

不明な点がある場合や、
次工程の判断に必要な情報が不足している場合は、
推測して進めず、ユーザーへ確認すること。

工程がスキップされた場合は、
スキップ理由をユーザーへ確認し、
必要に応じて WorkLog または TaskLog に記録すること。