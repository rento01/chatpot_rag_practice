"""Langfuse 連携の薄いラッパ。

教材としてのねらい:
- Phase 4 (Langfuse 導入) でここを埋めることで「観測」を体験する
- 初期状態では完全に no-op なので、`LANGFUSE_*` 未設定でもアプリは動く

Langfuse SDK v4 対応:
- v3 以前の .trace() / .span() / .generation() メソッドは廃止
- v4 は OTel ベースの start_as_current_observation() API を使う
- 親子関係は OTel コンテキストで自動管理されるため trace_ctx の引き回し不要
"""

from __future__ import annotations

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

    # settings 経由で読むことで LANGFUSE_HOST の値が確実に反映される。
    # Langfuse() をデフォルト引数で呼ぶと SDK が独自に env を読み直すため、
    # settings.py との変数名の差異でエンドポイントが意図しない値になる。
    from backend.config import settings

    if not settings.langfuse_secret_key or not settings.langfuse_public_key:
        # 未設定: Langfuse を使わない（教材初期段階の想定）
        return

    try:
        from langfuse import Langfuse

        _langfuse = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception:
        # SDK が無い・初期化失敗時は黙って no-op
        _langfuse = None


# ──────────────────────────────────────────────
# 公開 API
# ──────────────────────────────────────────────


@contextmanager
def trace(name: str, input: Any = None) -> Generator[None, None, None]:
    """トップレベルのトレースを開始するコンテキストマネージャ。

    Langfuse 無効時は no-op として透過的に動作する。
    内部で span() / generation() を使うと OTel コンテキスト経由で自動的に子になる。
    """
    _init()
    if _langfuse is None:
        yield
        return

    try:
        with _langfuse.start_as_current_observation(name=name, as_type="span", input=input):
            yield
    finally:
        _langfuse.flush()


@contextmanager
def span(name: str, input: Any = None) -> Generator[Any, None, None]:
    """子 span を作成するコンテキストマネージャ。trace() 内で使う。

    OTel コンテキストで親 trace に自動的に紐づく。
    Langfuse 無効時は NoopSpan を返す。
    """
    _init()
    if _langfuse is None:
        yield NoopSpan()
        return

    with _langfuse.start_as_current_observation(name=name, as_type="span", input=input) as s:
        yield s


@contextmanager
def generation(name: str, model: str = "", input: Any = None) -> Generator[Any, None, None]:
    """LLM 生成 span を作成するコンテキストマネージャ。trace() 内で使う。

    OTel コンテキストで親 trace に自動的に紐づく。
    Langfuse 無効時は NoopSpan を返す。
    """
    _init()
    if _langfuse is None:
        yield NoopSpan()
        return

    with _langfuse.start_as_current_observation(name=name, as_type="generation", model=model, input=input) as g:
        yield g


class NoopSpan:
    """Langfuse 無効時のダミー。span() / generation() が yield するデフォルト値。

    .update() / .end() を安全に呼べる。
    """

    def update(self, **kwargs: Any) -> None:
        pass

    def end(self, **kwargs: Any) -> None:
        pass
