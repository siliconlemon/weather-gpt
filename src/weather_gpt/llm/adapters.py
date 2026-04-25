"""Maps provider settings to a LangChain chat model instance."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Iterator, List, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import LanguageModelInput
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from weather_gpt.chat_locale import get_chat_locale
from weather_gpt.config import Settings


def stub_placeholder_text() -> str:
    """Returns the stub LLM copy for the current chat locale."""
    if get_chat_locale() == "en":
        return (
            "To connect to the LLM, you need to provide the API key of the provider."
        )
    return (
        "Pro spojení s LLM je potřeba poskytnou klíč poskytovatele."
    )


class StubChatModel(BaseChatModel):
    """Deterministic model for tests and offline demos without external APIs."""

    @property
    def _llm_type(self) -> str:
        return "stub-weather-gpt"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Returns a single assistant message with fixed content."""
        msg = AIMessage(content=stub_placeholder_text())
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGeneration]:
        """Yields one chunk mirroring the non-streaming response."""
        yield ChatGeneration(message=AIMessage(content=stub_placeholder_text()))

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable | BaseTool],
        *,
        tool_choice: dict | str | bool | None = None,
        parallel_tool_calls: bool | None = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        """Binds tool schemas for LangGraph; generation ignores tools and returns fixed text."""
        formatted = [convert_to_openai_tool(t) for t in tools]
        bind_kw = dict(kwargs)
        if parallel_tool_calls is not None:
            bind_kw["parallel_tool_calls"] = parallel_tool_calls
        if tool_choice is not None:
            bind_kw["tool_choice"] = tool_choice
        return self.bind(tools=formatted, **bind_kw)


def build_chat_model(settings: Settings) -> BaseChatModel:
    """Instantiates the chat model for the configured LLM_PROVIDER."""
    provider = settings.llm_provider
    if provider == "stub":
        return StubChatModel()

    if provider == "opencode_zen":
        key = settings.opencode_zen_api_key
        if not key:
            raise ValueError("OPENCODE_ZEN_API_KEY is required when LLM_PROVIDER=opencode_zen")
        model = settings.llm_model or settings.opencode_zen_model
        return ChatOpenAI(
            model=model,
            api_key=key,
            base_url=settings.opencode_zen_base_url,
            temperature=0.2,
        )

    if provider == "openai":
        key = settings.openai_api_key
        if not key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        model = settings.llm_model or "gpt-4o-mini"
        kwargs: dict = {"model": model, "api_key": key, "temperature": 0.2}
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return ChatOpenAI(**kwargs)

    if provider == "anthropic":
        key = settings.anthropic_api_key
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        model = settings.llm_model or "claude-3-5-haiku-20241022"
        return ChatAnthropic(model=model, api_key=key, temperature=0.2)

    if provider == "gemini":
        key = settings.gemini_api_key
        if not key:
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
        model = settings.llm_model or "gemini-2.5-flash"
        return ChatGoogleGenerativeAI(model=model, api_key=key, temperature=0.2)

    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")
