.PHONY: up up-d down build logs restart pull pull-embed migrate revision downgrade

# Ollama のチャット用モデル（必要に応じて変更）
MODEL ?= llama3.2
# Ollama の埋め込み用モデル
EMBED_MODEL ?= nomic-embed-text
# alembic revision のメッセージ
MSG ?= update

# ──────────────────────────────────────────────
# Compose 操作
#   Issue #29: デフォルトはホスト OS で `ollama serve` を起動する想定。
#   ここの up / up-d は compose 内 Ollama も含めて一括起動するための補助コマンド
#   (`--profile bundled-ollama` で ollama サービスを起動対象に含める)。
# ──────────────────────────────────────────────
up:
	docker compose --profile bundled-ollama up

up-d:
	docker compose --profile bundled-ollama up -d

down:
	docker compose --profile bundled-ollama down

build:
	docker compose --profile bundled-ollama build

logs:
	docker compose logs -f

restart:
	docker compose --profile bundled-ollama restart

# ──────────────────────────────────────────────
# Ollama モデル取得
# ──────────────────────────────────────────────
pull:
	docker compose exec ollama ollama pull $(MODEL)

pull-embed:
	docker compose exec ollama ollama pull $(EMBED_MODEL)

# ──────────────────────────────────────────────
# Alembic
# ──────────────────────────────────────────────
migrate:
	docker compose exec backend alembic upgrade head

revision:
	docker compose exec backend alembic revision --autogenerate -m "$(MSG)"

downgrade:
	docker compose exec backend alembic downgrade -1
