## **目的**

今回の作業内容を学習ログとして記録する。

---

対象

Issue #xx

bolt-x

---

以下の形式で taskLog を作成してください。

出力先

```
docs/taskLog/
phaseX-boltY.md
```

---

出力フォーマット

```markdown
# Phase X-X bolt-Y

## 実施日

YYYY-MM-DD

## 対応Issue

#xx

## bolt

bolt-x

## 目的

今回のboltで達成したかったこと

---

## 実施内容

- xxx
- xxx
- xxx

---

## 変更ファイル

### 追加

- xxx

### 修正

- xxx

### 削除

- xxx

---

## 実装概要

今回どのような実装を行ったかを説明する。

---

## 学んだこと

- xxx
- xxx
- xxx

---

## 動作確認

実施した確認内容

例

- API起動確認
- curl確認
- UI確認
- テスト実行

結果

- PASS
- FAIL

---

## AIレビュー結果

レビューで指摘された内容

### High

なし

### Medium

なし

### Low

なし

---

## 課題

残っている課題

- xxx

---

## 次のboltへの引き継ぎ

次のboltで対応すべき内容

- xxx

---

## 関連コミット

```text
commit hash
```

---

## **関連PR**

```
PR URL
```

```
---

作成時のルール

- 学習した内容を必ず残す
- なぜその実装にしたかを書く
- 次のboltが迷わないように引き継ぎを書く
- 後から見返して理解できる内容にする
- Claude Codeが生成しても人間が読める形にする
```