"""Tests for WeatherService with mocked HTTP."""

import httpx
import pytest

from tests.conftest import make_settings
from weather_gpt.weather.cache import SimpleCache
from weather_gpt.weather.service import WeatherService


def _weather_payload() -> dict:
    """Minimal valid OpenWeather current weather JSON."""
    return {
        "name": "Testville",
        "sys": {"country": "TV", "sunrise": 1700000000, "sunset": 1700040000},
        "coord": {"lat": 1.0, "lon": 2.0},
        "main": {
            "temp": 12.3,
            "feels_like": 11.0,
            "humidity": 55,
            "pressure": 1012,
        },
        "weather": [{"main": "Clouds", "description": "cloudy", "icon": "03d"}],
        "dt": 1700000000,
        "wind": {"speed": 3.5, "deg": 200},
        "clouds": {"all": 40},
        "visibility": 10000,
    }


@pytest.mark.asyncio
async def test_get_current_weather_mocked() -> None:
    """get_current_weather parses a successful API response."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert "appid" in str(request.url)
        return httpx.Response(200, json=_weather_payload())

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        svc = WeatherService(make_settings(), SimpleCache(600), client)
        out = await svc.get_current_weather("Testville")
    assert out.get("source") == "api"
    assert out["location"]["name"] == "Testville"
    assert out["current"]["temperature"] == 12.3


@pytest.mark.asyncio
async def test_missing_api_key() -> None:
    """Without an API key the service returns a clear error dict."""
    transport = httpx.MockTransport(lambda r: httpx.Response(500))
    async with httpx.AsyncClient(transport=transport) as client:
        svc = WeatherService(make_settings(api_key=None), SimpleCache(600), client)
        out = await svc.get_current_weather("X")
    assert "error" in out
