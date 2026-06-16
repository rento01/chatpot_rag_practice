.PHONY: up up-d down build logs restart pull migrate revision downgrade

MODEL ?= llama3.2
MSG ?= update

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

pull:
	docker compose exec ollama ollama pull $(MODEL)

pull-embed:
	docker compose exec ollama ollama pull nomic-embed-text

pull-vision:
	docker compose exec ollama ollama pull llava

migrate:
	docker compose exec backend alembic upgrade head

revision:
	docker compose exec backend alembic revision --autogenerate -m "$(MSG)"

downgrade:
	docker compose exec backend alembic downgrade -1
