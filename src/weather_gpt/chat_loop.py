"""Dedicated event loop for async chat (Flask sync + Gemini / async HTTP).

Each ``asyncio.run()`` creates a new loop and closes it when the coroutine returns.
LangChain's Google GenAI stack keeps an async HTTP client bound to the loop where it
first ran; a second ``asyncio.run()`` often triggers ``RuntimeError: Event loop is
closed`` during TLS/connection teardown (especially on Windows).

Chat runs on one long-lived loop in a background thread instead.
"""

from __future__ import annotations

import asyncio
import atexit
import threading
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")


class DedicatedChatLoop:
    """Owns a single ``asyncio`` loop running in a daemon thread."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._ready = threading.Event()

    def _thread_target(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._ready.set()
        try:
            loop.run_forever()
        finally:
            try:
                if loop.is_running():
                    loop.stop()
            except Exception:
                pass
            try:
                loop.close()
            except Exception:
                pass

    def ensure_started(self) -> None:
        with self._lock:
            if self._thread is not None:
                return
            self._ready.clear()
            self._thread = threading.Thread(
                target=self._thread_target,
                name="weather-gpt-chat-loop",
                daemon=True,
            )
            self._thread.start()
            if not self._ready.wait(timeout=60.0):
                raise RuntimeError("chat event loop did not start")
            if self._loop is None:
                raise RuntimeError("chat event loop is missing")

    def run(self, coro: Coroutine[Any, Any, T], *, timeout: float | None = 300) -> T:
        self.ensure_started()
        assert self._loop is not None
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=timeout)

    def stop(self) -> None:
        loop = self._loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(loop.stop)
        t = self._thread
        if t is not None and t.is_alive():
            t.join(timeout=10.0)


_dedicated = DedicatedChatLoop()


def run_chat_coroutine(coro: Coroutine[Any, Any, T], *, timeout: float | None = 300) -> T:
    """Runs ``coro`` on the shared chat loop (thread-safe from Flask request threads)."""
    return _dedicated.run(coro, timeout=timeout)


def stop_chat_loop() -> None:
    _dedicated.stop()


atexit.register(stop_chat_loop)
