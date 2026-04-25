"""Tests for file logging configuration."""

import logging
from datetime import date, timedelta
from pathlib import Path

import pytest

from weather_gpt.logging_setup import configure_file_logging


def _today_log(tmp_path: Path) -> Path:
    return tmp_path / f"weather-gpt-{date.today().isoformat()}.log"


def test_configure_creates_rotating_file(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """A day-stamped file handler is attached and receives log records."""
    monkeypatch.setenv("LOG_TO_FILE", "true")
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_RETENTION_DAYS", "3")
    monkeypatch.setenv("LOG_LEVEL", "INFO")

    configure_file_logging()
    logging.getLogger("weather_gpt.test").info("hello from test logger")

    log_file = _today_log(tmp_path)
    assert log_file.is_file()
    text = log_file.read_text(encoding="utf-8")
    assert "hello from test logger" in text
    assert "INFO" in text

    marked = [
        h
        for h in logging.getLogger().handlers
        if getattr(h, "_weather_gpt_log_handler", False)
    ]
    assert len(marked) == 1


def test_file_log_strips_ansi_sgr(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Werkzeug-style color codes in the message must not appear in the log file."""
    monkeypatch.setenv("LOG_TO_FILE", "true")
    monkeypatch.setenv("LOG_DIR", str(tmp_path))

    configure_file_logging()
    colored = "\033[36mGET / HTTP/1.1\033[0m"
    logging.getLogger("werkzeug").info("%s", colored)
    for h in logging.getLogger().handlers:
        try:
            h.flush()
        except (AttributeError, OSError, RuntimeError):
            pass

    text = _today_log(tmp_path).read_text(encoding="utf-8")
    assert "\x1b" not in text
    assert "GET / HTTP/1.1" in text


def test_configure_twice_single_handler(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Repeated configure replaces the previous app file handler."""
    monkeypatch.setenv("LOG_TO_FILE", "true")
    monkeypatch.setenv("LOG_DIR", str(tmp_path))

    configure_file_logging()
    configure_file_logging()

    marked = [
        h
        for h in logging.getLogger().handlers
        if getattr(h, "_weather_gpt_log_handler", False)
    ]
    assert len(marked) == 1


def test_configure_disabled_removes_handler(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Turning file logging off drops the marked handler."""
    monkeypatch.setenv("LOG_TO_FILE", "true")
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    configure_file_logging()
    monkeypatch.setenv("LOG_TO_FILE", "false")
    configure_file_logging()

    marked = [
        h
        for h in logging.getLogger().handlers
        if getattr(h, "_weather_gpt_log_handler", False)
    ]
    assert marked == []


def test_prune_removes_dated_logs_older_than_retention(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Day-stamped and legacy rotated names past LOG_RETENTION_DAYS are deleted."""
    stale_day = date.today() - timedelta(days=30)
    stale_stamped = tmp_path / f"weather-gpt-{stale_day.isoformat()}.log"
    stale_stamped.write_text("gone", encoding="utf-8")
    stale_legacy = tmp_path / f"weather-gpt.log.{stale_day.isoformat()}"
    stale_legacy.write_text("gone", encoding="utf-8")

    keep_day = date.today() - timedelta(days=1)
    keep_file = tmp_path / f"weather-gpt-{keep_day.isoformat()}.log"
    keep_file.write_text("keep", encoding="utf-8")

    monkeypatch.setenv("LOG_TO_FILE", "true")
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_RETENTION_DAYS", "7")

    configure_file_logging()

    assert not stale_stamped.is_file()
    assert not stale_legacy.is_file()
    assert keep_file.is_file()
