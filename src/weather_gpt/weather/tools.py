"""LangChain tools wrapping WeatherService for use in LangGraph."""

from __future__ import annotations

from langchain_core.tools import tool

from weather_gpt.weather.service import WeatherService


def build_weather_tools(service: WeatherService) -> list:
    """Creates async tools bound to the given weather service instance."""

    @tool
    async def get_current_weather(
        location: str,
        units: str | None = None,
        include_details: bool = True,
    ) -> dict:
        """Current weather for a city name or lat,lon; optional units and extended fields."""
        return await service.get_current_weather(location, units, include_details)

    @tool
    async def get_forecast(location: str, days: int = 5, units: str | None = None) -> dict:
        """Multi-day forecast for a city or coordinates (days up to 5 on free tier)."""
        return await service.get_forecast(location, days, units)

    @tool
    async def search_location(query: str, limit: int = 5) -> dict:
        """Resolves place names to lat/lon candidates for follow-up weather calls."""
        return await service.search_location(query, limit)

    @tool
    async def get_weather_by_zip(
        zip_code: str,
        country_code: str = "US",
        units: str | None = None,
    ) -> dict:
        """Current weather by postal/ZIP code and ISO country code."""
        return await service.get_weather_by_zip(zip_code, country_code, units)

    @tool
    async def get_air_quality(location: str) -> dict:
        """Air quality index and pollutants; accepts city or lat,lon."""
        return await service.get_air_quality(location)

    return [
        get_current_weather,
        get_forecast,
        search_location,
        get_weather_by_zip,
        get_air_quality,
    ]
