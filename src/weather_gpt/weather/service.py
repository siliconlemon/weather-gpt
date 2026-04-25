"""Async OpenWeatherMap client with caching and daily call tracking."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

import httpx

from weather_gpt.config import Settings
from weather_gpt.weather.cache import SimpleCache

logger = logging.getLogger(__name__)


def aqi_description(aqi: int) -> str:
    """Human-readable explanation for OpenWeather AQI level 1–5."""
    descriptions = {
        1: "Air quality is satisfactory, and air pollution poses little or no risk.",
        2: "Air quality is acceptable. However, there may be a risk for some people who are unusually sensitive.",
        3: "Members of sensitive groups may experience health effects. The general public is less likely to be affected.",
        4: "Some members of the general public may experience health effects; members of sensitive groups may experience more serious health effects.",
        5: "Health alert: The risk of health effects is increased for everyone.",
    }
    return descriptions.get(aqi, "Unknown air quality level")


def _is_coord_string(location: str) -> bool:
    """Detects lat,lon style location strings."""
    inner = location.replace(",", "").replace(".", "").replace("-", "").replace(" ", "")
    return "," in location and inner.isdigit()


class WeatherService:
    """Fetches and caches weather, forecast, geocoding, and air quality data."""

    def __init__(
        self,
        settings: Settings,
        cache: SimpleCache,
        client: httpx.AsyncClient,
    ) -> None:
        self._s = settings
        self._cache = cache
        self._client = client
        self._call_count = 0
        self._call_date = datetime.now().date()

    def _track_api_call(self) -> None:
        """Increments daily counter and logs when approaching the configured limit."""
        today = datetime.now().date()
        if self._call_date != today:
            self._call_count = 0
            self._call_date = today
        self._call_count += 1
        if self._call_count > self._s.max_daily_calls * 0.9:
            logger.warning(
                "Approaching API limit: %s/%s",
                self._call_count,
                self._s.max_daily_calls,
            )

    def api_status(self) -> Dict[str, Any]:
        """Returns usage and cache summary for diagnostics."""
        return {
            "status": "operational",
            "api_key_configured": bool(self._s.api_key),
            "base_url": self._s.base_url,
            "daily_limit": self._s.max_daily_calls,
            "calls_today": self._call_count,
            "calls_remaining": self._s.max_daily_calls - self._call_count,
            "cache_stats": self._cache.stats(),
            "timestamp": datetime.now().isoformat(),
        }

    async def get_current_weather(
        self,
        location: str,
        units: str | None = None,
        include_details: bool = True,
    ) -> Dict[str, Any]:
        """Returns current weather for a city name or lat,lon pair."""
        u = units or self._s.default_units
        cache_key = f"current:{location}:{u}"
        cached = self._cache.get(cache_key)
        if cached:
            logger.info("Returning cached weather for %s", location)
            return {"source": "cache", **cached}

        if not self._s.api_key:
            return {"error": "OpenWeatherMap API key is not configured"}

        try:
            if _is_coord_string(location):
                lat, lon = location.split(",", 1)
                params: dict[str, str | float] = {
                    "lat": lat.strip(),
                    "lon": lon.strip(),
                    "appid": self._s.api_key,
                    "units": u,
                    "lang": self._s.default_lang,
                }
            else:
                params = {
                    "q": location,
                    "appid": self._s.api_key,
                    "units": u,
                    "lang": self._s.default_lang,
                }

            self._track_api_call()
            response = await self._client.get(f"{self._s.base_url}/weather", params=params)
            response.raise_for_status()
            data = response.json()

            result: Dict[str, Any] = {
                "location": {
                    "name": data.get("name"),
                    "country": data["sys"].get("country"),
                    "coordinates": data["coord"],
                },
                "current": {
                    "temperature": data["main"]["temp"],
                    "feels_like": data["main"]["feels_like"],
                    "condition": data["weather"][0]["main"],
                    "description": data["weather"][0]["description"],
                    "icon": f"https://openweathermap.org/img/w/{data['weather'][0]['icon']}.png",
                },
                "units": u,
                "timestamp": datetime.fromtimestamp(data["dt"]).isoformat(),
            }

            if include_details:
                result["details"] = {
                    "humidity": f"{data['main']['humidity']}%",
                    "pressure": f"{data['main']['pressure']} hPa",
                    "wind": {
                        "speed": data["wind"]["speed"],
                        "direction": data["wind"].get("deg", 0),
                        "unit": "m/s" if u == "metric" else "mph" if u == "imperial" else "m/s",
                    },
                    "clouds": f"{data['clouds']['all']}%",
                    "visibility": f"{data.get('visibility', 'N/A')} meters",
                    "sunrise": datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M"),
                    "sunset": datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M"),
                }

            self._cache.set(cache_key, result)
            return {"source": "api", **result}

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"error": f"Location '{location}' not found"}
            return {"error": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.exception("Error fetching weather")
            return {"error": str(e)}

    async def get_forecast(
        self,
        location: str,
        days: int = 5,
        units: str | None = None,
    ) -> Dict[str, Any]:
        """Returns grouped multi-day forecast (3-hour steps from OWM)."""
        u = units or self._s.default_units
        cache_key = f"forecast:{location}:{days}:{u}"
        cached = self._cache.get(cache_key)
        if cached:
            return {"source": "cache", **cached}

        if not self._s.api_key:
            return {"error": "OpenWeatherMap API key is not configured"}

        try:
            if _is_coord_string(location):
                lat, lon = location.split(",", 1)
                params: dict[str, str | int] = {"lat": lat.strip(), "lon": lon.strip()}
            else:
                params = {"q": location}

            params.update(
                {
                    "appid": self._s.api_key,
                    "units": u,
                    "cnt": min(days * 8, 40),
                }
            )

            self._track_api_call()
            response = await self._client.get(f"{self._s.base_url}/forecast", params=params)
            response.raise_for_status()
            data = response.json()

            daily_forecasts: dict[str, list[dict[str, Any]]] = {}
            for item in data["list"]:
                d = datetime.fromtimestamp(item["dt"]).date().isoformat()
                if d not in daily_forecasts:
                    daily_forecasts[d] = []
                daily_forecasts[d].append(
                    {
                        "time": datetime.fromtimestamp(item["dt"]).strftime("%H:%M"),
                        "temperature": item["main"]["temp"],
                        "feels_like": item["main"]["feels_like"],
                        "condition": item["weather"][0]["main"],
                        "description": item["weather"][0]["description"],
                        "humidity": f"{item['main']['humidity']}%",
                        "wind_speed": item["wind"]["speed"],
                        "precipitation": item.get("rain", {}).get("3h", 0)
                        + item.get("snow", {}).get("3h", 0),
                        "clouds": f"{item['clouds']['all']}%",
                    }
                )

            result = {
                "location": {
                    "name": data["city"]["name"],
                    "country": data["city"]["country"],
                    "coordinates": data["city"]["coord"],
                },
                "forecast": daily_forecasts,
                "units": u,
                "timezone": data["city"]["timezone"],
            }

            self._cache.set(cache_key, result)
            return {"source": "api", **result}

        except Exception as e:
            logger.exception("Error fetching forecast")
            return {"error": str(e)}

    async def search_location(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Geocodes a free-text query into coordinate candidates."""
        if not self._s.api_key:
            return {"error": "OpenWeatherMap API key is not configured"}

        try:
            params = {
                "q": query,
                "limit": min(limit, 5),
                "appid": self._s.api_key,
            }
            self._track_api_call()
            response = await self._client.get(f"{self._s.geo_url}/direct", params=params)
            response.raise_for_status()
            data = response.json()

            if not data:
                return {"results": [], "message": f"No locations found for '{query}'"}

            results = []
            for loc in data:
                results.append(
                    {
                        "name": loc.get("name"),
                        "country": loc.get("country"),
                        "state": loc.get("state", ""),
                        "lat": loc.get("lat"),
                        "lon": loc.get("lon"),
                        "coordinates_string": f"{loc.get('lat')},{loc.get('lon')}",
                    }
                )

            return {"query": query, "count": len(results), "results": results}

        except Exception as e:
            logger.exception("Error searching location")
            return {"error": str(e)}

    async def get_weather_by_zip(
        self,
        zip_code: str,
        country_code: str = "US",
        units: str | None = None,
    ) -> Dict[str, Any]:
        """Returns current weather for a postal code and country code."""
        u = units or self._s.default_units
        if not self._s.api_key:
            return {"error": "OpenWeatherMap API key is not configured"}

        try:
            params = {
                "zip": f"{zip_code},{country_code}",
                "appid": self._s.api_key,
                "units": u,
            }
            self._track_api_call()
            response = await self._client.get(f"{self._s.base_url}/weather", params=params)
            response.raise_for_status()
            data = response.json()

            return {
                "location": {
                    "zip": zip_code,
                    "country": country_code,
                    "name": data.get("name"),
                    "coordinates": data["coord"],
                },
                "current": {
                    "temperature": data["main"]["temp"],
                    "feels_like": data["main"]["feels_like"],
                    "condition": data["weather"][0]["main"],
                    "description": data["weather"][0]["description"],
                    "humidity": f"{data['main']['humidity']}%",
                    "pressure": f"{data['main']['pressure']} hPa",
                },
                "units": u,
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"error": f"ZIP code '{zip_code}' not found in country '{country_code}'"}
            return {"error": f"API error: {e.response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    async def get_air_quality(self, location: str) -> Dict[str, Any]:
        """Returns air pollution index and components; resolves city names via geocoding."""
        if not self._s.api_key:
            return {"error": "OpenWeatherMap API key is not configured"}

        try:
            if "," not in location or not _is_coord_string(location):
                search = await self.search_location(location, limit=1)
                if not search.get("results"):
                    return {"error": f"Could not find coordinates for '{location}'"}
                first = search["results"][0]
                lat, lon = str(first["lat"]), str(first["lon"])
            else:
                lat, lon = location.split(",", 1)
                lat, lon = lat.strip(), lon.strip()

            params = {"lat": lat, "lon": lon, "appid": self._s.api_key}
            self._track_api_call()
            response = await self._client.get(f"{self._s.base_url}/air_pollution", params=params)
            response.raise_for_status()
            data = response.json()

            if not data.get("list"):
                return {"error": "No air quality data available"}

            air_data = data["list"][0]
            aqi = air_data["main"]["aqi"]
            aqi_levels = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}

            return {
                "location": {"lat": lat, "lon": lon},
                "air_quality": {
                    "aqi": aqi,
                    "level": aqi_levels.get(aqi, "Unknown"),
                    "description": aqi_description(aqi),
                },
                "pollutants": {
                    "co": f"{air_data['components']['co']} μg/m³",
                    "no2": f"{air_data['components']['no2']} μg/m³",
                    "o3": f"{air_data['components']['o3']} μg/m³",
                    "so2": f"{air_data['components']['so2']} μg/m³",
                    "pm2_5": f"{air_data['components']['pm2_5']} μg/m³",
                    "pm10": f"{air_data['components']['pm10']} μg/m³",
                },
                "timestamp": datetime.fromtimestamp(air_data["dt"]).isoformat(),
            }

        except Exception as e:
            logger.exception("Error fetching air quality")
            return {"error": str(e)}
