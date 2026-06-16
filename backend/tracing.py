"""Langfuse 連携の薄いラッパ。

教材としてのねらい:
- Phase 4 (Langfuse 導入) でここを埋めることで「観測」を体験する
- 初期状態では完全に no-op なので、`LANGFUSE_*` 未設定でもアプリは動く
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Generator

# ──────────────────────────────────────────────
# 内部状態
# ──────────────────────────────────────────────

_langfuse: Any = None
_initialized = False


def _init() -> None:
    """環境変数が揃っていれば Langfuse クライアントを初期化する。"""
    global _langfuse, _initialized
    if _initialized:
        return
    _initialized = True

    secret = os.getenv("LANGFUSE_SECRET_KEY", "")
    public = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    if not secret or not public:
        # 未設定: Langfuse を使わない（教材初期段階の想定）
        return

    try:
        from langfuse import Langfuse

        _langfuse = Langfuse()
    except Exception:
        # SDK が無い・初期化失敗時は黙って no-op
        _langfuse = None


# ──────────────────────────────────────────────
# 公開 API
# ──────────────────────────────────────────────


@contextmanager
def trace(name: str, **kwargs: Any) -> Generator[Any, None, None]:
    """トレース context manager。Langfuse 無効時は no-op を返す。

    Phase 4 で span/generation を追加するときは、ここで返すオブジェクトを
    実トレース or _NoopSpan で透過的に切り替える想定。
    """
    _init()
    if _langfuse is None:
        yield _NoopSpan()
        return

    t = _langfuse.trace(name=name, **kwargs)
    try:
        yield t
    finally:
        _langfuse.flush()


class _NoopSpan:
    """Langfuse 無効時のダミー。`span(...).end(...)` などを安全に呼べる。"""

    def span(self, **kwargs: Any) -> "_NoopSpan":
        return self

    def generation(self, **kwargs: Any) -> "_NoopSpan":
        return self

    def end(self, **kwargs: Any) -> None:
        pass

    def update(self, **kwargs: Any) -> None:
        pass
