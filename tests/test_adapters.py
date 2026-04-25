"""Tests for LLM adapter factory."""

import pytest

from tests.conftest import make_settings
from weather_gpt.llm.adapters import StubChatModel, build_chat_model


def test_stub_model() -> None:
    """Stub provider returns StubChatModel without API keys."""
    m = build_chat_model(make_settings(llm_provider="stub"))
    assert isinstance(m, StubChatModel)


def test_unknown_provider_raises() -> None:
    """Raises ValueError for unsupported LLM_PROVIDER."""
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        build_chat_model(make_settings(llm_provider="not-a-real-provider"))


def test_opencode_requires_key() -> None:
    """Raises ValueError when Zen is selected but the API key is missing."""
    with pytest.raises(ValueError, match="OPENCODE_ZEN_API_KEY"):
        build_chat_model(
            make_settings(llm_provider="opencode_zen", opencode_zen_api_key=None)
        )


def test_openai_requires_key() -> None:
    """Raises ValueError when OpenAI is selected but the API key is missing."""
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        build_chat_model(make_settings(llm_provider="openai", openai_api_key=None))


def test_anthropic_requires_key() -> None:
    """Raises ValueError when Anthropic is selected but the API key is missing."""
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        build_chat_model(make_settings(llm_provider="anthropic", anthropic_api_key=None))


def test_gemini_requires_key() -> None:
    """Raises ValueError when Gemini is selected but the API key is missing."""
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        build_chat_model(make_settings(llm_provider="gemini", gemini_api_key=None))
