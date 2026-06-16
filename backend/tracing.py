"""Langfuse tracing utilities.

Langfuse の環境変数 (LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY) が未設定の場合は
全てのトレーシングが no-op になるため、Langfuse なしでも動作する。
"""

import os
from contextlib import contextmanager
from typing import Any, Generator

_langfuse = None
_enabled = False


def _init() -> None:
    global _langfuse, _enabled
    secret = os.getenv("LANGFUSE_SECRET_KEY", "")
    public = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    if not secret or not public:
        _enabled = False
        return
    try:
        from langfuse import Langfuse
        _langfuse = Langfuse()
        _enabled = True
    except Exception:
        _enabled = False


def get_langfuse():
    """Langfuse クライアントを返す。未初期化なら初期化する。"""
    global _langfuse, _enabled
    if _langfuse is None and not _enabled:
        _init()
    return _langfuse if _enabled else None


def flush() -> None:
    """保留中のイベントを送信する。"""
    lf = get_langfuse()
    if lf:
        lf.flush()


@contextmanager
def trace(name: str, **kwargs: Any) -> Generator:
    """Langfuse トレースを作成する context manager。無効時は no-op。"""
    lf = get_langfuse()
    if lf is None:
        yield _NoopSpan()
        return
    t = lf.trace(name=name, **kwargs)
    try:
        yield t
    finally:
        lf.flush()


class _NoopSpan:
    """Langfuse 無効時のダミースパン。"""

    def span(self, **kwargs: Any) -> "_NoopSpan":
        return self

    def generation(self, **kwargs: Any) -> "_NoopSpan":
        return self

    def end(self, **kwargs: Any) -> None:
        pass

    def update(self, **kwargs: Any) -> None:
        pass
