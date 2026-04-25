"""ReAct agent with OpenWeather tools and locale-aware system instructions."""

from __future__ import annotations

from typing import Any, List, Sequence

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from weather_gpt.chat_locale import reset_chat_locale, set_chat_locale


def _system_prompt(locale: str) -> str:
    """Builds the system prompt including response language."""
    lang = "Czech" if locale == "cs" else "English"
    return (
        "You are a weather assistant. Use the provided tools to fetch "
        "OpenWeatherMap data when the user asks about weather, forecasts, locations, "
        "or air quality. Summarize tool output clearly for the user.\n"
        f"Always respond in {lang} (locale {locale})."
    )


def _dicts_to_messages(items: Sequence[dict[str, Any]]) -> List[BaseMessage]:
    """Converts JSON role/content objects to LangChain messages."""
    out: List[BaseMessage] = []
    for it in items:
        role = it.get("role", "user")
        content = it.get("content", "")
        if role == "user":
            out.append(HumanMessage(content=str(content)))
        elif role == "assistant":
            out.append(AIMessage(content=str(content)))
    return out


def build_weather_agent(llm: BaseChatModel, tools: list, locale: str) -> Any:
    """Creates a LangGraph-style agent with the given model, tools, and locale."""
    return create_agent(llm, tools, system_prompt=_system_prompt(locale))


def _last_ai_text(messages: Sequence[BaseMessage]) -> str:
    """Extracts text from the final assistant message in the transcript."""
    for m in reversed(messages):
        if isinstance(m, AIMessage):
            c = m.content
            if isinstance(c, str):
                return c
            if isinstance(c, list):
                parts = []
                for block in c:
                    if isinstance(block, dict) and block.get("type") == "text":
                        parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        parts.append(block)
                return "".join(parts)
    return ""


async def run_weather_chat(
    llm: BaseChatModel,
    tools: list,
    history: Sequence[dict[str, Any]],
    locale: str,
) -> str:
    """Builds the agent for this locale, runs one turn, and returns the assistant reply."""
    token = set_chat_locale(locale)
    try:
        agent = build_weather_agent(llm, tools, locale)
        user_msgs = _dicts_to_messages(history)
        result = await agent.ainvoke({"messages": user_msgs})
        msgs = result.get("messages", [])
        return _last_ai_text(msgs)
    finally:
        reset_chat_locale(token)
