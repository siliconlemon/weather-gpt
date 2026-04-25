FROM python:3.13-slim-bookworm

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY src ./src
COPY templates ./templates
COPY static ./static

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV FLASK_APP=weather_gpt.app:create_app

EXPOSE 8000

CMD ["flask", "run", "--host", "0.0.0.0", "--port", "8000"]
