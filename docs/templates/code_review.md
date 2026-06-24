Code Review Template

目的

実装済みの差分をレビューし、

* 設計とのズレ
* バグリスク
* 保守性
* セキュリティ
* テスト漏れ

を確認する。

⸻

対象

* Issue #xx
* Phase X-X
* bolt-x
* 今回の変更差分

⸻

Code Review Result

Review Summary

項目	結果
Phase	Phase X-X
Bolt	bolt-x
Review Result	Approve / Request Changes
High	0
Medium	0
Low	0
Overall Risk	Low / Medium / High
Next Action	Implementation Report 作成

⸻

実施内容

今回の差分をレビューしてください。

⸻

1. Requirements・Bolt設計との整合性

確認観点

* Requirementsを満たしているか
* bolt設計の目的を満たしているか
* 作るもの / 作らないものを守っているか
* スコープ超過がないか
* 過剰実装していないか

レビュー結果

* xxx

⸻

2. コード品質

確認観点

* 命名は分かりやすいか
* 関数やクラスの責務は明確か
* 可読性は問題ないか
* 重複コードはないか
* 不要な import や未使用コードはないか

レビュー結果

* xxx

⸻

3. バグリスク

確認観点

* 例外処理は適切か
* None / 空文字 / 空配列への考慮はあるか
* 入力値バリデーションは適切か
* 想定外ケースで落ちないか
* エッジケースの考慮はあるか

レビュー結果

* xxx

⸻

4. 保守性

確認観点

* 将来修正しやすいか
* 依存関係が複雑になっていないか
* ハードコードが増えていないか
* 過剰な抽象化をしていないか

レビュー結果

* xxx

⸻

5. セキュリティ観点

確認観点

* 秘密情報を出力していないか
* 個人情報やトークンをログ出力していないか
* 危険な入力をそのまま利用していないか

レビュー結果

* xxx

⸻

6. 動作確認・テスト観点

確認観点

* bolt完了条件を満たしているか
* 確認手順は妥当か
* テスト漏れはないか

レビュー結果

* xxx

⸻

7. 学習観点

この実装から学ぶべきポイントを整理してください。

学習ポイント

* xxx

⸻

Good Points

* xxx
* xxx

⸻

Findings

ID	Severity	内容	推奨対応
F-01	High	xxx	修正必須
F-02	Medium	xxx	修正推奨
F-03	Low	xxx	任意対応

⸻

## Remaining Issues

今回対応しない課題

ID | 内容 | 理由 | 対応予定
---|---|---|---
RI-01 | xxx | xxx | Phase3

⸻

Recommendations

* xxx
* xxx

⸻

Learning Points

* xxx
* xxx

⸻

Final Judgment

項目	判定
Result	Approve / Request Changes
Ready for Implementation Report	Yes / No
Re-review Required	Yes / No

⸻

Review Policy

High

* 修正必須
* Request Changes
* 修正後に再レビュー実施

Medium

* 原則修正推奨
* 修正後に再レビュー推奨
* 見送る場合は理由を記録
* 必要に応じて GitHub Issue 化

Low

* 修正任意
* Issue 化可能
* Remaining Issues に記録

⸻

Next Action

以下のいずれかを提案してください。

修正不要

* Implementation Report 作成へ進む

軽微修正

* 修正後に再レビュー

要修正

* 修正対応を実施
* 再レビューを実施

⸻

Review Findings for Implementation Report

Implementation Report に転記するための内容を整理してください。

Review Result

* Approve
* Request Changes

Key Findings

* F-01 xxx
* F-02 xxx

Follow-up

* Remaining Issuesへ記録
* GitHub Issue化
* 対応不要

Related Issues

* GitHub Issue #xx
* GitHub Issue Draft
* 該当なし