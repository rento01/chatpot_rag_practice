"""DB 接続まわりの初期化。

ローカルでも AWS でも同じ PostgreSQL を前提にする。
接続先は `DATABASE_URL` で `.env` から切り替える。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings

# ──────────────────────────────────────────────
# Engine / Session
# ──────────────────────────────────────────────

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """SQLAlchemy DeclarativeBase。dataModels はこれを継承する。"""

    pass


def get_db():
    """FastAPI Depends 用の DB セッション生成器。"""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ──────────────────────────────────────────────
# 起動時マイグレーション
# ──────────────────────────────────────────────


def run_migrations() -> None:
    """alembic upgrade head を実行する。

    教材ではコンテナ起動と同時にスキーマを作りたいので、
    FastAPI の lifespan からも呼び出す。
    """
    from alembic.config import Config

    from alembic import command

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")
