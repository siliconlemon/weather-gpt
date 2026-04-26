"""Tests for LangGraph weather agent wiring."""

import httpx
import pytest
from langchain_core.tools import tool

from tests.conftest import make_settings
from langchain_core.messages import AIMessage

from weather_gpt.graph.chat import _last_ai_text, run_weather_chat
from weather_gpt.llm.adapters import build_chat_model
from weather_gpt.weather.cache import SimpleCache
from weather_gpt.weather.service import WeatherService
from weather_gpt.weather.tools import build_weather_tools


@tool
def _ping(x: str) -> str:
    """Echoes input for a minimal tool-bound graph."""
    return x


@pytest.mark.asyncio
async def test_run_stub_reply_en() -> None:
    """Stub LLM returns the English placeholder when locale is en."""
    settings = make_settings(llm_provider="stub")
    llm = build_chat_model(settings)
    transport = httpx.MockTransport(lambda r: httpx.Response(404))
    async with httpx.AsyncClient(transport=transport) as client:
        svc = WeatherService(settings, SimpleCache(600), client)
        tools = build_weather_tools(svc)
    text = await run_weather_chat(
        llm, tools, [{"role": "user", "content": "Hello"}], locale="en"
    )
    assert "API key" in text
    assert "provider" in text


@pytest.mark.asyncio
async def test_run_stub_reply_cs() -> None:
    """Stub LLM returns the Czech placeholder when locale is cs."""
    settings = make_settings(llm_provider="stub")
    llm = build_chat_model(settings)
    transport = httpx.MockTransport(lambda r: httpx.Response(404))
    async with httpx.AsyncClient(transport=transport) as client:
        svc = WeatherService(settings, SimpleCache(600), client)
        tools = build_weather_tools(svc)
    text = await run_weather_chat(
        llm, tools, [{"role": "user", "content": "Ahoj"}], locale="cs"
    )
    assert "LLM" in text
    assert "klíč" in text


def test_last_ai_text_gemini_thinking_block() -> None:
    """Google GenAI may emit user-visible text only in thinking/reasoning blocks."""
    msgs = [
        AIMessage(
            content=[{"type": "thinking", "thinking": "Prague is about 18°C today."}]
        )
    ]
    assert _last_ai_text(msgs) == "Prague is about 18°C today."


def test_last_ai_text_prefers_plain_text_blocks() -> None:
    """When both text and thinking blocks exist, public text wins."""
    msgs = [
        AIMessage(
            content=[
                {"type": "thinking", "thinking": "internal"},
                {"type": "text", "text": "Hello"},
            ]
        )
    ]
    assert _last_ai_text(msgs) == "Hello"


@pytest.mark.asyncio
async def test_run_with_minimal_tool() -> None:
    """Agent completes with stub model and a single no-op tool."""
    settings = make_settings(llm_provider="stub")
    llm = build_chat_model(settings)
    text = await run_weather_chat(
        llm, [_ping], [{"role": "user", "content": "ping"}], locale="en"
    )
    assert len(text) > 0
