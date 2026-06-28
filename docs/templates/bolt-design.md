Bolt Design Template

保存先

docs/design/

⸻

命名規則

phase<phase番号>-bolt-<bolt番号>.md

例

* phase2-1-bolt-0.md
* phase2-1-bolt-1.md
* phase3-1-bolt-0.md

⸻

Phase X-X bolt-Y 設計

Design Summary

項目	内容
Phase	Phase X-X
Bolt	bolt-Y
Issue	#xx
目的	xxx
作るもの	xxx
作らないもの	xxx
完了条件	xxx
次Bolt	bolt-x / なし

⸻

Requirements Summary

今回対応する Requirements の要点を整理する。

対応対象

* xxx
* xxx

対応対象外

* xxx
* xxx

⸻

bolt分割判定

判定

* 分割不要
* bolt-0 のみで対応

または

* bolt-0
* bolt-1

へ分割

理由

* xxx
* xxx

⸻

データフロー

今回の処理の流れを整理する。

Flow

xxx
↓
xxx
↓
xxx

例

PDF
↓
extract_text
↓
Chunk
↓
upsert
↓
ChromaDB

⸻

影響範囲

今回の変更が影響する範囲を整理する。

対象

* xxx
* xxx

影響なし

* xxx
* xxx

⸻

bolt-Y: タイトル

目的

この bolt で達成すること。

* xxx
* xxx

⸻

作るもの

今回実装する対象。

* xxx
* xxx

⸻

作らないもの

今回実装しない対象。

* xxx
* xxx

⸻

対象ファイル・修正箇所

ファイル | 修正対象 | 変更内容 | 理由

⸻

実装方針

どのような方針で実装するか。

方針

* xxx
* xxx

採用理由

* xxx
* xxx

既存コードの扱い

置き換え・削除・変更対象のコードについて、設計時点で扱いを決定する。

ファイル	対象	扱い（削除 / コメントアウト / 移動 / 残存）	理由
xxx	xxx	xxx	xxx

⸻

テスト観点

実装後に確認すべき観点を整理する。

ID | 内容
---|---
T-01 | xxx
T-02 | xxx
T-03 | xxx

⸻

設計判断

設計時点で採用した判断と見送った代替案を記録する。

項目	判断	理由	代替案
xxx	xxx	xxx	xxx
xxx	xxx	xxx	xxx

⸻

完了条件

この bolt が完了したと判断できる条件。

Functional

* xxx
* xxx

Verification

* API確認
* 動作確認
* エラー確認

⸻

懸念事項

設計・実装時に注意すべき事項。

項目	内容	対応方針
xxx	xxx	xxx

⸻

Remaining Issues

今回の bolt では対応しない課題を記録する。

ID | 内容 | 対応予定 | 再検討条件
---|---|---|---
RI-01 | xxx | Phase X-X | xxx
RI-02 | xxx | Future | xxx

⸻

確認事項・決定事項

実装前に確認が必要な内容を整理する。

項目	内容
確認事項	xxx
決定事項	xxx
理由	xxx
対応方針	xxx

⸻

ドキュメント更新

更新対象ドキュメント。

ドキュメント	更新内容
xxx	xxx
xxx	xxx

⸻

次の bolt への引き継ぎ

Handover

* bolt-1 で対応
* Phase X-X で対応

または

* なし

⸻

References

Requirements

* docs/design/phaseX-X-requirements.md

Related Issues

* GitHub Issue #xx

⸻

作成時のルール

* Requirements を確認してから作成する
* 実装はしない
* コード変更はしない
* bolt を可能な限り小さくする
* 作るものと作らないものを明確にする
* 修正ファイルを明記する
* 修正対象の関数・クラスを明記する
* 修正理由を記載する
* 完了条件を明記する
* 確認事項・決定事項を残す
* 設計判断を記録する
* Requirements にない内容を勝手に追加しない
* 不明点は確認事項へ記録する
* 推測による判断は禁止
* 後から見返して設計意図が分かる内容にする
* Summary だけ読めば設計内容が把握できる状態にする