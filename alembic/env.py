import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# backend パッケージを import 可能にする
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# モデルを Base.metadata に登録するため、import 自体に副作用がある
from backend import dataModels  # noqa: F401
from backend.db import Base

config = context.config

if (db_url := os.getenv("DATABASE_URL")):
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    # disable_existing_loggers=False を明示して uvicorn などの既存ロガーを無効化しない。
    # デフォルト(True)のままだと FastAPI 起動中に alembic が migrate するとき
    # uvicorn のロガーが無効化され、起動後のすべてのログが docker logs に出なくなる。
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
