"""In-memory TTL cache for weather API responses."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional


class SimpleCache:
    """Stores values with a time-to-live; expired entries are dropped on read."""

    def __init__(self, ttl_seconds: int = 600) -> None:
        self._store: dict[str, tuple[Any, datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def get(self, key: str) -> Optional[Any]:
        """Returns the value for key if present and not expired."""
        if key not in self._store:
            return None
        value, ts = self._store[key]
        if datetime.now() - ts < self._ttl:
            return value
        del self._store[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Stores value with the current timestamp."""
        self._store[key] = (value, datetime.now())

    def clear(self) -> None:
        """Removes all entries."""
        self._store.clear()

    def stats(self) -> dict[str, Any]:
        """Summarizes entry counts and TTL configuration."""
        now = datetime.now()
        active = sum(1 for _, (_, ts) in self._store.items() if now - ts < self._ttl)
        return {
            "total_entries": len(self._store),
            "active_entries": active,
            "expired_entries": len(self._store) - active,
            "ttl_seconds": self._ttl.total_seconds(),
        }
