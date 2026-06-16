"""ロギング初期化ユーティリティ。

`LOG_LEVEL` 環境変数（デフォルト INFO）でレベルを切り替え、
uvicorn のロガーとフォーマットを揃える。
"""

import logging
import os

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_initialized = False


def setup_logging() -> None:
    """アプリ起動時に一度だけ呼び出してルートロガーを初期化する。"""
    global _initialized
    if _initialized:
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(level=level, format=_LOG_FORMAT, force=True)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).setLevel(level)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """モジュール用のロガーを返す。初期化されていなければ初期化する。"""
    if not _initialized:
        setup_logging()
    return logging.getLogger(name)
