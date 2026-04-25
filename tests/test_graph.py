"""Tests for LangGraph weather agent wiring."""

import httpx
import pytest
from langchain_core.tools import tool

from tests.conftest import make_settings
from weather_gpt.graph.chat import run_weather_chat
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
    assert "Stub mode" in text
    assert "LLM_PROVIDER" in text


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
    assert "ukázkový" in text
    assert "LLM_PROVIDER" in text


@pytest.mark.asyncio
async def test_run_with_minimal_tool() -> None:
    """Agent completes with stub model and a single no-op tool."""
    settings = make_settings(llm_provider="stub")
    llm = build_chat_model(settings)
    text = await run_weather_chat(
        llm, [_ping], [{"role": "user", "content": "ping"}], locale="en"
    )
    assert len(text) > 0
