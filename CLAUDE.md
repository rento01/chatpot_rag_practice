# CLAUDE.md

## 1. プロジェクト概要

本プロジェクトは RAG 構築を段階的に学習するための教材です。

実装は Phase ごとに進め、各 Phase の目的・完了条件を満たしながら開発を進めます。

---

## 2. Claude の役割

Claude は本プロジェクトの開発支援エージェントとして振る舞います。

以下を基本方針とします。

- プロジェクトの設計方針・ロードマップを尊重する
- 既存構成・既存命名規則を維持する
- 必要最小限の変更で実装する
- 可読性・保守性を優先する
- 不明点は推測せず、提案または確認を行う

以下は、ユーザーから明示的な指示がある場合のみ実施します。

- 大規模なリファクタリング
- ディレクトリ構成の変更
- API 仕様の変更
- 新規ライブラリ・フレームワークの追加
- アーキテクチャの変更
- Road Map・Phase 構成の変更

---

## 3. 開発フロー

開発フローおよび成果物の作成手順は以下を参照します。

- `docs/development_flow.md`

---

## 4. 技術スタック

| 項目 | 内容 |
|---|---|
| Backend | Python 3.11 / FastAPI |
| Frontend | Next.js（App Router） |
| Vector DB | ChromaDB（ポート 8001） |
| RDB | PostgreSQL 16（ポート 5432） |
| LLM | Ollama（デフォルト: ホストOS側で `ollama serve`） |
| Embedding | nomic-embed-text（768次元） |
| Package Manager | uv |
| 起動方法 | `docker compose up -d`（Ollama はホスト起動） / `make up-d`（Docker 内 Ollama を含む） |

---

## 5. 主要ディレクトリ

```
backend/
├── main.py               # API エントリポイント
├── rag.py                # RAG ロジック（教材本体）
├── db.py                 # DB アクセス
├── dataModels.py         # ドメインモデル
├── schemas.py            # API スキーマ
├── llm/                  # LLM・Embedding 実装
├── vector_db/            # VectorDB 実装
└── config/               # 設定

reference/
└── ROAD_MAP.md           # 実装ロードマップ

docs/
├── development_flow.md   # 開発フロー
└── templates/            # 成果物テンプレート

.claude/
└── skills/               # Claude Skills
```

---

## 6. プロジェクト固有ルール

### 学習教材としての方針

- 学習者が実装する箇所は `NotImplementedError` などで示されています
- 対象箇所を中心に実装し、不要な設計変更は行いません
- 実装の進め方は `reference/ROAD_MAP.md` および `docs/development_flow.md` を参照します

### 開発原則

実装時は以下を優先します。

- KISS（Keep It Simple）
- YAGNI（You Aren't Gonna Need It）
- 必要最小限の変更
- 既存コードとの整合性

---

## 7. 参照優先順位

判断に迷った場合は、以下の順で参照します。

1. 本ファイル（プロジェクト固有ルール）
2. `docs/development_flow.md`（開発フロー）
3. `.claude/skills/`（各工程の詳細手順）
4. `docs/templates/`（成果物フォーマット）

グローバル `~/.claude/CLAUDE.md` のルールはプロジェクト固有ルールで上書きされます。
