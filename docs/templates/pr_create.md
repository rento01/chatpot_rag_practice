# Pull Request Create Template

## 目的

作成した Pull Request の内容を確認し、
GitHub に Pull Request を作成する。

---

# 対象

- Issue #xx
- Phase X-X
- bolt-x
- feature ブランチ

---

# PR作成前チェック

以下を確認する。

## Git

- [ ] git status が clean
- [ ] Commit 済み
- [ ] Push 済み
- [ ] feature ブランチ上である

---

## 実装

- [ ] Requirements を満たしている
- [ ] 動作確認済み
- [ ] TaskLog 作成済み
- [ ] Commit Message 作成済み
- [ ] PR本文 作成済み

---

## Review

- [ ] AI Review 完了
- [ ] Review Findings を確認
- [ ] 必要な修正を反映済み

---

# Pull Request 情報

## Base Branch

```
main
```

## Head Branch

```
feature/xxx
```

---

## PR Title

```
feat(phaseX-X): xxxxx
```

---

## PR Body

作成済みの PR本文を使用する。

---

# gh コマンド

実行例

```bash
gh pr create \
  --title "<PR Title>" \
  --body "<PR Body>" \
  --base main \
  --head feature/xxx
```

または

```bash
gh pr create
```

対話形式で作成してもよい。

---

# 作成後の確認

以下を確認する。

- [ ] PR が作成された
- [ ] Title が正しい
- [ ] PR本文 が反映されている
- [ ] Files changed を確認
- [ ] 差分が想定通り
- [ ] CI が開始された

---

# 完了後

次の作業を提案する。

- CI 完了待ち
- CI 結果確認
- Self Review
- Merge
- 次の bolt に着手

現在の bolt が Phase の最終 bolt の場合は、
Phase Summary の作成を提案する。