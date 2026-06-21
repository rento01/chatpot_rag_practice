Commit Message Template

目的

今回の変更内容に適した Commit Message を作成する。

⸻

対象

* Issue #xx
* Phase X-X
* bolt-x

⸻

Commit Summary

項目	内容
Phase	Phase X-X
Bolt	bolt-x
Issue	#xx
変更種別	feat / fix / docs / refactor / test / chore
対象	xxx
概要	xxx

⸻

Conventional Commits

以下から適切な Prefix を選択する。

Prefix	用途
feat	新機能追加
fix	バグ修正
docs	ドキュメント修正
refactor	リファクタリング
test	テスト追加・修正
chore	雑務・設定変更

⸻

差分確認

以下を確認して Commit Message を決定する。

変更内容

* xxx
* xxx

主な変更ファイル

* xxx.py
* xxx.md

⸻

出力

推奨 Commit Message

<type>(<scope>): <summary>

例

feat(phase2-1): implement document chunk indexing
docs(tasklog): add phase2-1 bolt-0 task log
chore(ruff): add lint configuration

⸻

理由

なぜその Commit Message が適切か説明する。

* xxx
* xxx

⸻

作成時のルール

* Conventional Commits を使用する
* 1行目は簡潔に記載する
* Commit Message は 50文字程度を目安とする
* 実装内容が分かる表現を使用する
* docs や chore を適切に使い分ける
* Issue番号がある場合は追記を検討する
* 推測による判断は禁止