TaskLog Template

目的

今回の bolt の最終成果を記録する。

実装内容だけでなく、

* 実装判断
* レビュー結果
* 発生した問題
* 学習内容
* 次 bolt への引き継ぎ

を残し、後から振り返り可能な状態にする。

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
Code Review	Approve / Request Changes
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

設計との差異

設計時との変更点を記録する。

差異内容

* xxx
* xxx

理由

* xxx
* xxx

差異がない場合

なし

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

Code Review 結果

**Approve / Request Changes**（High: 0 / Medium: 0 / Low: 0）

| ID | 内容 | 対応 |
|---|---|---|
| F-01 | xxx | **対応済み / Remaining Issues（RI-xx）/ 見送り**: 理由 |
| F-02 | xxx | **対応済み / Remaining Issues（RI-xx）/ 見送り**: 理由 |

⸻

発生した問題と対応

実装中に発生した問題と解決内容を記録する。

問題	原因	対応
xxx	xxx	xxx

問題がない場合

なし

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

* docs/report/phaseX-X-bolt-Y.md

Code Review

* docs/review/phaseX-X-bolt-Y.md

Error Investigation（発生時のみ）

* docs/error/YYYYMMDD-error-title.md

Phase Summary（Phase完了時のみ）

* docs/summary/phaseX-summary.md

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
* 設計との差異を残す
* Review Findings の判断を残す
* 発生した問題と対応を記録する
* GitHub Issue の有無を記録する
* 次の bolt が迷わないように引き継ぎを書く
* 後から見返して理解できる内容にする
* Claude Code が生成しても人間が読める形にする
* サマリーだけ読めば作業内容が把握できる状態にする