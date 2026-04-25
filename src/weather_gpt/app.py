"""Flask application factory and HTTP routes."""

from __future__ import annotations

import asyncio
import atexit
from pathlib import Path
from typing import Any

import httpx
from flask import Flask, jsonify, render_template, request

from weather_gpt.chat_loop import run_chat_coroutine
from weather_gpt.config import Settings
from weather_gpt.graph.chat import run_weather_chat
from weather_gpt.llm.adapters import build_chat_model
from weather_gpt.weather.cache import SimpleCache
from weather_gpt.weather.service import WeatherService
from weather_gpt.weather.tools import build_weather_tools

_ERR: dict[str, dict[str, str]] = {
    "cs": {
        "bad_json": "Neplatný JSON.",
        "bad_messages": "Pole messages musí být neprázdné pole objektů role/content.",
        "bad_locale": "Neplatná hodnota X-Locale (použijte cs nebo en).",
        "chat_failed": "Zpracování chatu selhalo.",
    },
    "en": {
        "bad_json": "Invalid JSON body.",
        "bad_messages": "Field messages must be a non-empty array of role/content objects.",
        "bad_locale": "Invalid X-Locale header (use cs or en).",
        "chat_failed": "Chat processing failed.",
    },
}


def _header_locale() -> tuple[str | None, bool]:
    """Returns (locale or None, invalid_header) for X-Locale; missing header is valid default."""
    raw = request.headers.get("X-Locale")
    if raw is None or raw == "":
        return None, False
    t = raw.lower().strip()
    if t in ("cs", "en"):
        return t, False
    return None, True


def _msg(key: str, loc: str) -> str:
    """Returns a localized short error string for API responses."""
    return _ERR.get(loc, _ERR["en"]).get(key, key)


def create_app(settings: Settings | None = None) -> Flask:
    """Creates the Flask app with shared HTTP client, weather service, and LangGraph agent."""
    s = settings or Settings.from_env()
    repo_root = Path(__file__).resolve().parent.parent.parent
    app = Flask(
        __name__,
        template_folder=str(repo_root / "templates"),
        static_folder=str(repo_root / "static"),
        static_url_path="/static",
    )
    app.secret_key = s.flask_secret_key
    app.config["SETTINGS"] = s

    client = httpx.AsyncClient(
        timeout=30.0,
        headers={"User-Agent": "weather-gpt/1.0"},
    )
    cache = SimpleCache(ttl_seconds=s.cache_ttl)
    weather = WeatherService(s, cache, client)
    tools = build_weather_tools(weather)
    llm = build_chat_model(s)

    def _close_client() -> None:
        try:
            asyncio.run(client.aclose())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(client.aclose())
            finally:
                loop.close()

    atexit.register(_close_client)

    @app.get("/")
    def index() -> str:
        """Serves the single-page chat UI."""
        return render_template("index.html")

    @app.get("/api/health")
    def health() -> Any:
        """Liveness probe for containers and load balancers."""
        return jsonify({"status": "ok"})

    @app.post("/api/chat")
    def chat() -> Any:
        """Runs one LangGraph agent turn from JSON messages and returns the assistant reply."""
        hl, bad_header = _header_locale()
        err_loc = hl or "cs"
        if bad_header:
            return jsonify({"error": _msg("bad_locale", err_loc)}), 400
        loc = hl or "cs"

        try:
            body = request.get_json(force=True, silent=False)
        except Exception:
            return jsonify({"error": _msg("bad_json", loc)}), 400

        if not isinstance(body, dict):
            return jsonify({"error": _msg("bad_json", loc)}), 400

        messages = body.get("messages")
        if not isinstance(messages, list) or len(messages) == 0:
            return jsonify({"error": _msg("bad_messages", loc)}), 400

        for m in messages:
            if not isinstance(m, dict) or "role" not in m or "content" not in m:
                return jsonify({"error": _msg("bad_messages", loc)}), 400

        req_loc = body.get("locale")
        if isinstance(req_loc, str) and req_loc.lower() in ("cs", "en"):
            loc = req_loc.lower()

        try:
            reply = run_chat_coroutine(run_weather_chat(llm, tools, messages, loc))
        except Exception:
            app.logger.exception("chat failed")
            return jsonify({"error": _msg("chat_failed", loc)}), 500

        return jsonify({"reply": reply, "locale": loc})

    return app
