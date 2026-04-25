"""Tests for SimpleCache."""

import time

from weather_gpt.weather.cache import SimpleCache


def test_get_set_roundtrip() -> None:
    """Stored values are returned before TTL expires."""
    c = SimpleCache(ttl_seconds=60)
    c.set("a", {"x": 1})
    assert c.get("a") == {"x": 1}


def test_expiry() -> None:
    """Expired entries are treated as missing."""
    c = SimpleCache(ttl_seconds=0.05)
    c.set("k", 1)
    time.sleep(0.08)
    assert c.get("k") is None


def test_clear() -> None:
    """Clear removes all keys."""
    c = SimpleCache(60)
    c.set("a", 1)
    c.clear()
    assert c.get("a") is None


def test_stats() -> None:
    """Stats reflect entry counts."""
    c = SimpleCache(600)
    c.set("a", 1)
    st = c.stats()
    assert st["total_entries"] == 1
    assert st["active_entries"] == 1
