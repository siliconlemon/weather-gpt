# weather-gpt

Flask web app with a dark chat UI (Czech default, English optional), LangGraph ReAct agent, and OpenWeatherMap tools. Packaged with [uv](https://docs.astral.sh/uv/) and runnable via Docker Compose as a single service.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- OpenWeatherMap API key for live weather
- An LLM key when not using `LLM_PROVIDER=stub`

## Local setup

```bash
cp env.example .env
# Edit .env: set API_KEY, choose LLM_PROVIDER, and provider keys as needed.

uv sync --group dev
uv run flask --app weather_gpt.app:create_app run --debug --port 8000
```

Open http://127.0.0.1:8000 .

## Tests

```bash
uv run pytest tests/ -q
```

## Docker

Compose reads `.env` from the project root. Create it before the first run:

```bash
cp env.example .env
docker compose up --build
```

The app listens on port **8000**. Use `LLM_PROVIDER=opencode_zen` with `OPENCODE_ZEN_API_KEY` and a model id from the [OpenCode Zen](https://open-code.ai/docs/en/zen) documentation (free tiers and names change over time).

## OpenCode Zen

Zen exposes an OpenAI-compatible Chat Completions API. Set `OPENCODE_ZEN_BASE_URL` (default `https://opencode.ai/zen/v1`), `OPENCODE_ZEN_API_KEY`, and `OPENCODE_ZEN_MODEL` to match the model you enabled in Zen.

## Project layout

- `src/weather_gpt/` — Flask app, LangGraph chat, LLM adapters, OpenWeather service and tools
- `templates/`, `static/` — UI, i18n JSON (`static/i18n/cs.json`, `en.json`)
- `tests/` — pytest suite
