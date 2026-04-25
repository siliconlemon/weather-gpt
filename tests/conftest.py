"""Shared pytest fixtures."""

import dataclasses

import pytest

from weather_gpt.config import Settings


def make_settings(**overrides: object) -> Settings:
    """Builds a Settings instance for tests with optional field overrides."""
    s = Settings(
        api_key="test-api-key",
        base_url="http://test.invalid/data/2.5",
        geo_url="http://test.invalid/geo/1.0",
        default_units="metric",
        default_lang="en",
        cache_ttl=600,
        max_daily_calls=1000,
        llm_provider="stub",
        llm_model=None,
        openai_api_key=None,
        openai_base_url=None,
        anthropic_api_key=None,
        opencode_zen_api_key=None,
        opencode_zen_model="glm-4.7-free",
        opencode_zen_base_url="https://opencode.ai/zen/v1",
        gemini_api_key=None,
        flask_secret_key="test-secret",
        llm_timeout_seconds=25.0,
        llm_max_retries=0,
        chat_agent_timeout_seconds=120.0,
    )
    return dataclasses.replace(s, **overrides)  # type: ignore[arg-type]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    """Flask test client with stub LLM and a fake OpenWeather key."""
    monkeypatch.setenv("LOG_TO_FILE", "false")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("API_KEY", "test-api-key")
    monkeypatch.delenv("OPENCODE_ZEN_API_KEY", raising=False)

    from weather_gpt.app import create_app

    return create_app().test_client()
