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
Remaining Issues	xxx
Next Action	Code Review

⸻

実装概要

今回の実装内容を要約する。

例

* PDFファイル取り込み処理を実装
* ChromaDB保存処理を実装
* Phase 2-1 の完了条件を満たした

⸻

Changed Files

ファイル	種別	内容
xxx.py	追加	xxx
xxx.py	修正	xxx
xxx.py	削除	xxx

⸻

Verification

実施した確認内容と結果を記録する。

確認項目	結果
API起動	PASS
curl確認	PASS
テスト実行	PASS

⸻

Implementation Decisions

今回の実装で行った判断を記録する。

判断内容

* add ではなく upsert を採用
* Embedding 実装は Phase 3-1 に分離
* Chunk 化は後続 Bolt で対応

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

今回対応しなかった内容を記録する。

Remaining Issues

* xxx
* xxx

Future Improvements

* xxx
* xxx

⸻

Handover

次の Bolt や Phase への引き継ぎ事項を記録する。

例

* Phase 3-1 で Embedding 実装
* bolt-1 で OCR 対応

または

* なし

⸻

References

Requirements

* docs/design/phaseX-X-requirements.md

Bolt Design

* docs/design/phaseX-X-bolt-Y.md

⸻

作成ルール

* 実装完了後に作成する
* Code Review 前に作成する
* Commit 前に作成する
* TaskLog 作成前に作成する
* 実装結果のみ記録する
* レビュー結果は含めない
* Summary を読めば実装内容が把握できる状態にする
* 設計との差異と判断理由を残す