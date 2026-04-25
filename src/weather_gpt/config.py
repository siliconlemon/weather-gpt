"""Environment-backed settings for the app, LLM, and OpenWeatherMap."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None or v == "":
        return default
    return v


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = _env(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Application configuration loaded once at startup."""

    api_key: str | None
    base_url: str
    geo_url: str
    default_units: str
    default_lang: str
    cache_ttl: int
    max_daily_calls: int
    llm_provider: str
    llm_model: str | None
    openai_api_key: str | None
    openai_base_url: str | None
    anthropic_api_key: str | None
    opencode_zen_api_key: str | None
    opencode_zen_model: str
    opencode_zen_base_url: str
    gemini_api_key: str | None
    flask_secret_key: str
    llm_timeout_seconds: float
    llm_max_retries: int
    chat_agent_timeout_seconds: float

    @staticmethod
    def from_env() -> Settings:
        """Builds settings from environment variables."""
        return Settings(
            api_key=_env("API_KEY"),
            base_url=_env("BASE_URL", "https://api.openweathermap.org/data/2.5") or "",
            geo_url=_env("GEO_URL", "https://api.openweathermap.org/geo/1.0") or "",
            default_units=_env("DEFAULT_UNITS", "metric") or "metric",
            default_lang=_env("DEFAULT_LANG", "en") or "en",
            cache_ttl=_env_int("CACHE_TTL", 600),
            max_daily_calls=_env_int("MAX_DAILY_CALLS", 1000),
            llm_provider=(_env("LLM_PROVIDER", "stub") or "stub").lower(),
            llm_model=_env("LLM_MODEL"),
            openai_api_key=_env("OPENAI_API_KEY"),
            openai_base_url=_env("OPENAI_BASE_URL"),
            anthropic_api_key=_env("ANTHROPIC_API_KEY"),
            opencode_zen_api_key=_env("OPENCODE_ZEN_API_KEY"),
            opencode_zen_model=_env("OPENCODE_ZEN_MODEL", "glm-4.7-free") or "glm-4.7-free",
            opencode_zen_base_url=_env("OPENCODE_ZEN_BASE_URL", "https://opencode.ai/zen/v1")
            or "https://opencode.ai/zen/v1",
            gemini_api_key=_env("GEMINI_API_KEY"),
            flask_secret_key=_env("FLASK_SECRET_KEY", "dev") or "dev",
            llm_timeout_seconds=max(5.0, _env_float("LLM_TIMEOUT", 25.0)),
            llm_max_retries=max(0, _env_int("LLM_MAX_RETRIES", 0)),
            chat_agent_timeout_seconds=max(15.0, _env_float("CHAT_AGENT_TIMEOUT", 120.0)),
        )
