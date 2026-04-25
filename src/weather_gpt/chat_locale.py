"""Per-invocation chat locale for stub LLM placeholder strings."""

from __future__ import annotations

from contextvars import ContextVar, Token

_ctx: ContextVar[str | None] = ContextVar("_chat_locale", default=None)


def set_chat_locale(locale: str) -> Token[str | None]:
    """Sets the active locale for the current async/sync context; returns a reset token."""
    loc = locale.lower().strip() if locale else "cs"
    if loc not in ("cs", "en"):
        loc = "cs"
    return _ctx.set(loc)


def reset_chat_locale(token: Token[str | None]) -> None:
    """Restores the previous locale after a chat turn."""
    _ctx.reset(token)


def get_chat_locale() -> str:
    """Returns the active chat locale, defaulting to Czech when unset."""
    v = _ctx.get()
    return v if v in ("cs", "en") else "cs"
