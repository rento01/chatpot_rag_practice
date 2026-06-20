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

3. 実装後報告

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