Bolt Design Template

保存先

docs/design/

命名規則

phase<phase番号>-bolt-<bolt番号>.md

例

phase2-1-bolt-0.md

phase2-1-bolt-1.md

phase3-1-bolt-0.md

⸻

Phase X-X bolt-Y 設計

bolt分割判定

分割要否を記載する。

例

* 分割不要。bolt-0 のみで進める
* bolt-0 / bolt-1 に分割する

理由

* xxx
* xxx

⸻

bolt-Y: タイトル

目的

この bolt で達成すること。

⸻

作るもの

実装対象。

* xxx
* xxx

⸻

作らないもの

今回対応しない内容。

* xxx
* xxx

⸻

対象ファイル・ディレクトリ

種別	ファイル
書く	xxx
読む（参照）	xxx

⸻

実装方針

どのような方針で実装するか。

* xxx
* xxx

⸻

完了条件

この bolt が完了したと判断できる条件。

* xxx
* xxx

⸻

懸念事項

設計・実装時に注意すべき事項。

* xxx

⸻

確認事項・決定事項

項目名

確認内容

決定内容

理由

対応方針

⸻

ドキュメント更新

更新対象のドキュメント。

* xxx
* xxx

⸻

次の bolt への引き継ぎ

なし

または

* bolt-1 で対応
* Phase X-X で対応

⸻

作成時のルール

* Requirements を確認してから作成する
* 実装はしない
* コード変更はしない
* bolt を可能な限り小さくする
* 作るものと作らないものを明確にする
* 修正ファイルを明記する
* 完了条件を明記する
* 確認事項・決定事項を残す
* 後から見返して設計意図が分かる内容にする