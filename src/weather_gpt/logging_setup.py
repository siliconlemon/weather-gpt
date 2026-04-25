"""File logging: one log file per calendar day (weather-gpt-YYYY-MM-DD.log), pruned by age."""

from __future__ import annotations

import logging
import os
import re
from datetime import date, timedelta
from pathlib import Path

# Werkzeug (and others) embed terminal color CSI sequences in log messages.
_ANSI_SGR_RE = re.compile(r"\x1b\[[0-9;]*m")

_LOG_FILE_PREFIX = "weather-gpt"


class _StripAnsiFormatter(logging.Formatter):
    """File-friendly formatter: removes ANSI SGR codes from the final line."""

    def format(self, record: logging.LogRecord) -> str:
        return _ANSI_SGR_RE.sub("", super().format(record))


class _DayStampedFileHandler(logging.FileHandler):
    """Appends to ``{prefix}-YYYY-MM-DD.log`` and opens the next day's file after local midnight."""

    def __init__(self, log_dir: Path, *, prefix: str, encoding: str = "utf-8") -> None:
        self._log_dir = Path(log_dir)
        self._prefix = prefix
        self._current_date = date.today()
        self._log_dir.mkdir(parents=True, exist_ok=True)
        path = self._log_dir / f"{prefix}-{self._current_date.isoformat()}.log"
        super().__init__(str(path), mode="a", encoding=encoding, delay=False)

    def emit(self, record: logging.LogRecord) -> None:
        today = date.today()
        if self._current_date != today:
            self._rollover_to(today)
        logging.FileHandler.emit(self, record)

    def _rollover_to(self, today: date) -> None:
        if self.stream:
            try:
                self.stream.flush()
            except OSError:
                pass
            try:
                self.stream.close()
            except OSError:
                pass
            self.stream = None
        self.baseFilename = os.path.abspath(
            str(self._log_dir / f"{self._prefix}-{today.isoformat()}.log")
        )
        self._current_date = today
        if not self.delay:
            self.stream = self._open()


_MARKER = "_weather_gpt_log_handler"


def flush_logging_handlers() -> None:
    """Flushes root logging handlers (e.g. file) so lines appear promptly under the dev reloader."""
    for h in logging.getLogger().handlers:
        try:
            h.flush()
        except (AttributeError, OSError, RuntimeError):
            pass


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _resolve_log_dir(raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    return _repo_root() / p


def _enabled() -> bool:
    """File logging is opt-in (default off) so production can rely on stdout / platform logging."""
    flag = (os.getenv("LOG_TO_FILE", "false") or "false").lower()
    if flag not in ("1", "true", "yes", "on"):
        return False
    log_dir = (os.getenv("LOG_DIR", "logs") or "").strip()
    return bool(log_dir)


def _remove_marked_handlers(root: logging.Logger) -> None:
    for h in list(root.handlers):
        if getattr(h, _MARKER, False):
            root.removeHandler(h)
            h.close()


def _prune_old_log_files(log_dir: Path, *, prefix: str, retention_days: int) -> None:
    """Removes ``{prefix}-YYYY-MM-DD.log`` and legacy ``{prefix}.log.YYYY-MM-DD`` older than retention."""
    if retention_days <= 0:
        return
    cutoff = date.today() - timedelta(days=retention_days)
    stamped = re.compile(rf"^{re.escape(prefix)}-(\d{{4}}-\d{{2}}-\d{{2}})\.log$")
    legacy = re.compile(rf"^{re.escape(prefix)}\.log\.(\d{{4}}-\d{{2}}-\d{{2}})$")
    for path in log_dir.iterdir():
        if not path.is_file():
            continue
        m = stamped.match(path.name) or legacy.match(path.name)
        if not m:
            continue
        try:
            file_date = date.fromisoformat(m.group(1))
        except ValueError:
            continue
        if file_date < cutoff:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


def configure_file_logging() -> None:
    """Attaches a day-stamped file handler to the root logger; idempotent per process."""
    root = logging.getLogger()
    _remove_marked_handlers(root)

    if not _enabled():
        return

    log_dir = _resolve_log_dir(os.getenv("LOG_DIR", "logs") or "logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    retention_raw = os.getenv("LOG_RETENTION_DAYS", "7") or "7"
    try:
        retention_days = max(1, int(retention_raw))
    except ValueError:
        retention_days = 7

    level_name = (os.getenv("LOG_LEVEL", "INFO") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    _prune_old_log_files(log_dir, prefix=_LOG_FILE_PREFIX, retention_days=retention_days)

    handler = _DayStampedFileHandler(log_dir, prefix=_LOG_FILE_PREFIX, encoding="utf-8")
    handler.setFormatter(
        _StripAnsiFormatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    setattr(handler, _MARKER, True)
    root.addHandler(handler)

    root.setLevel(level)
