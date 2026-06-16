.PHONY: up up-d down build logs restart pull pull-embed migrate revision downgrade

# Ollama のチャット用モデル（必要に応じて変更）
MODEL ?= llama3.2
# Ollama の埋め込み用モデル
EMBED_MODEL ?= nomic-embed-text
# alembic revision のメッセージ
MSG ?= update

# ──────────────────────────────────────────────
# Compose 操作
# ──────────────────────────────────────────────
up:
	docker compose up

up-d:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

restart:
	docker compose restart

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
