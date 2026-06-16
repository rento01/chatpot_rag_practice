# backend (FastAPI) 用イメージ
#
# 教材として軽量に保つ。OCR (poppler-utils 等) は入れていないので、
# PDF テキスト抽出は pypdf のみで完結する。
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

COPY backend ./backend
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
