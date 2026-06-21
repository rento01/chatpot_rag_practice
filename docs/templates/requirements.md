Requirements Template

保存先

docs/design/

⸻

命名規則

phase<phase番号>-requirements.md

例

* phase2-1-requirements.md
* phase2-2-requirements.md
* phase3-1-requirements.md

⸻

Phase X-X Requirements

Requirements Summary

項目	内容
Phase	Phase X-X
Issue	#xx
タイトル	xxx
目的	xxx
対象範囲	xxx
対象外	xxx
完了条件数	xx
次工程	Bolt Design

⸻

Phase情報

項目	内容
Phase	X-X
タイトル	xxx
Issue	#xx

⸻

背景

なぜこの対応が必要なのか。

Background

* xxx
* xxx

⸻

目的

この Phase で達成したいこと。

Objective

* xxx
* xxx

⸻

要件

この Phase で満たすべき要件を整理する。

ID	要件
R-01	xxx
R-02	xxx
R-03	xxx

⸻

対象範囲

今回対応する内容。

ID	内容
S-01	xxx
S-02	xxx

⸻

対象外

今回対応しない内容。

ID	内容
O-01	xxx
O-02	xxx

⸻

完了条件

この Phase が完了したと判断する条件。

Acceptance Criteria

ID	条件
AC-01	xxx
AC-02	xxx
AC-03	xxx

⸻

懸念事項

設計・実装時に注意すべき事項。

ID	内容	対応方針
C-01	xxx	xxx
C-02	xxx	xxx

⸻

確認事項・決定事項

Requirements 作成時に発生した確認事項と決定事項を記録する。

Record

項目	内容
確認事項	xxx
決定事項	xxx
理由	xxx
対応方針	xxx

⸻

Bolt設計への引き継ぎ

Bolt 設計時に考慮すべき内容を記録する。

Handover

* xxx
* xxx

⸻

関連ドキュメント

Issue

* GitHub Issue #xx

Related Documents

* xxx
* xxx

Reference

* xxx
* xxx

⸻

作成時のルール

* Issue を確認して要件を整理する
* 実装方法は書かない
* 実装ファイルは書かない
* 実装方針は書かない
* Bolt Design で設計を行う
* 不明点は確認事項・決定事項へ記録する
* 対象範囲と対象外を明確に分ける
* 要件は ID 管理する（R-01形式）
* 完了条件は ID 管理する（AC-01形式）
* 後続工程で追跡可能な粒度で記載する
* Requirements にない内容を勝手に追加しない
* Issue に記載のない内容を推測で追加しない
* 不明点は確認事項へ記録する
* 推測による判断は禁止
* なぜその判断になったのか理由を残す
* 後から見返して意思決定の経緯が分かる内容にする
* Summary だけ読めば要件概要が把握できる状態にする