"""
OpenWeatherMap MCP Server
=========================
A comprehensive MCP server for weather data using OpenWeatherMap API.
Provides current weather, forecasts, air quality, and location search.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dotenv import load_dotenv
import httpx
from fastmcp import FastMCP

# Load environment variables
load_dotenv()

# ============================================================================
# Configuration
# ============================================================================

class Config:
    """Configuration from environment variables."""
    
    # API Settings
    API_KEY = os.getenv("API_KEY", "e1549ae776638792c28052a7856357c5")
    BASE_URL = os.getenv("BASE_URL", "https://api.openweathermap.org/data/2.5")
    GEO_URL = os.getenv("GEO_URL", "https://api.openweathermap.org/geo/1.0")
    
    # Default Settings
    DEFAULT_UNITS = os.getenv("DEFAULT_UNITS", "metric")  # metric, imperial, standard
    DEFAULT_LANG = os.getenv("DEFAULT_LANG", "en")
    
    # Cache Settings
    CACHE_TTL = int(os.getenv("CACHE_TTL", "600"))  # 10 minutes default
    
    # Server Settings
    SERVER_NAME = os.getenv("SERVER_NAME", "OpenWeatherMap MCP Server")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Rate Limiting
    MAX_DAILY_CALLS = int(os.getenv("MAX_DAILY_CALLS", "1000"))

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# Cache Implementation
# ============================================================================

class SimpleCache:
    """Simple in-memory cache with TTL."""
    
    def __init__(self, ttl_seconds: int = 600):
        self.cache = {}
        self.ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Set cache value with timestamp."""
        self.cache[key] = (value, datetime.now())
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.now()
        active = sum(1 for _, (_, ts) in self.cache.items() if now - ts < self.ttl)
        return {
            "total_entries": len(self.cache),
            "active_entries": active,
            "expired_entries": len(self.cache) - active,
            "ttl_seconds": self.ttl.total_seconds()
        }

# ============================================================================
# Server Creation
# ============================================================================

def create_weather_server() -> FastMCP:
    """Create the OpenWeatherMap MCP server."""
    
    logger.info(f"Creating {Config.SERVER_NAME}")
    
    mcp = FastMCP(
        name=Config.SERVER_NAME,
        instructions="""
        OpenWeatherMap MCP Server
        
        This server provides comprehensive weather data from OpenWeatherMap API.
        
        Available tools:
        - get_current_weather: Current weather for any location
        - get_forecast: 5-day weather forecast
        - search_location: Find locations by name
        - get_weather_by_zip: Weather by ZIP code
        - get_air_quality: Air pollution data
        
        Features:
        - Automatic caching (10 min default)
        - Unit conversion (metric/imperial)
        - Multi-language support
        - Rate limit awareness (1000 calls/day free tier)
        """
    )
    
    # Initialize cache and HTTP client
    cache = SimpleCache(ttl_seconds=Config.CACHE_TTL)
    
    client = httpx.AsyncClient(
        timeout=30.0,
        headers={"User-Agent": "FastMCP-Weather-Server/1.0"}
    )
    
    # API call counter (simple daily counter)
    api_calls = {"count": 0, "date": datetime.now().date()}
    
    def track_api_call():
        """Track API calls for rate limiting awareness."""
        today = datetime.now().date()
        if api_calls["date"] != today:
            api_calls["count"] = 0
            api_calls["date"] = today
        api_calls["count"] += 1
        
        if api_calls["count"] > Config.MAX_DAILY_CALLS * 0.9:
            logger.warning(f"Approaching API limit: {api_calls['count']}/{Config.MAX_DAILY_CALLS}")
    
    # ========== Weather Tools ==========
    
    @mcp.tool
    async def get_current_weather(
        location: str,
        units: str = Config.DEFAULT_UNITS,
        include_details: bool = True
    ) -> Dict[str, Any]:
        """
        Get current weather for a location.
        
        Args:
            location: City name (e.g., "London") or "lat,lon" coordinates
            units: Temperature units - "metric" (Celsius), "imperial" (Fahrenheit), "standard" (Kelvin)
            include_details: Include extended details like humidity, pressure, etc.
        
        Returns:
            Current weather data with temperature, conditions, and optional details
        """
        # Check cache
        cache_key = f"current:{location}:{units}"
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"Returning cached weather for {location}")
            return {"source": "cache", **cached}
        
        try:
            # Determine if location is coordinates or city name
            if "," in location and location.replace(",", "").replace(".", "").replace("-", "").replace(" ", "").isdigit():
                # Coordinates format: "lat,lon"
                lat, lon = location.split(",")
                params = {
                    "lat": lat.strip(),
                    "lon": lon.strip(),
                    "appid": Config.API_KEY,
                    "units": units,
                    "lang": Config.DEFAULT_LANG
                }
            else:
                # City name
                params = {
                    "q": location,
                    "appid": Config.API_KEY,
                    "units": units,
                    "lang": Config.DEFAULT_LANG
                }
            
            # Make API call
            track_api_call()
            response = await client.get(f"{Config.BASE_URL}/weather", params=params)
            response.raise_for_status()
            data = response.json()
            
            # Format response
            result = {
                "location": {
                    "name": data.get("name"),
                    "country": data["sys"].get("country"),
                    "coordinates": data["coord"]
                },
                "current": {
                    "temperature": data["main"]["temp"],
                    "feels_like": data["main"]["feels_like"],
                    "condition": data["weather"][0]["main"],
                    "description": data["weather"][0]["description"],
                    "icon": f"https://openweathermap.org/img/w/{data['weather'][0]['icon']}.png"
                },
                "units": units,
                "timestamp": datetime.fromtimestamp(data["dt"]).isoformat()
            }
            
            if include_details:
                result["details"] = {
                    "humidity": f"{data['main']['humidity']}%",
                    "pressure": f"{data['main']['pressure']} hPa",
                    "wind": {
                        "speed": data["wind"]["speed"],
                        "direction": data["wind"].get("deg", 0),
                        "unit": "m/s" if units == "metric" else "mph" if units == "imperial" else "m/s"
                    },
                    "clouds": f"{data['clouds']['all']}%",
                    "visibility": f"{data.get('visibility', 'N/A')} meters",
                    "sunrise": datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M"),
                    "sunset": datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M")
                }
            
            # Cache result
            cache.set(cache_key, result)
            
            return {"source": "api", **result}
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"error": f"Location '{location}' not found"}
            return {"error": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error fetching weather: {e}")
            return {"error": str(e)}
    
    @mcp.tool
    async def get_forecast(
        location: str,
        days: int = 5,
        units: str = Config.DEFAULT_UNITS
    ) -> Dict[str, Any]:
        """
        Get weather forecast for a location.
        
        Args:
            location: City name or "lat,lon" coordinates
            days: Number of days (max 5 for free tier)
            units: Temperature units
        
        Returns:
            5-day forecast with 3-hour intervals
        """
        # Check cache
        cache_key = f"forecast:{location}:{days}:{units}"
        cached = cache.get(cache_key)
        if cached:
            return {"source": "cache", **cached}
        
        try:
            # Parse location
            if "," in location and location.replace(",", "").replace(".", "").replace("-", "").replace(" ", "").isdigit():
                lat, lon = location.split(",")
                params = {"lat": lat.strip(), "lon": lon.strip()}
            else:
                params = {"q": location}
            
            params.update({
                "appid": Config.API_KEY,
                "units": units,
                "cnt": min(days * 8, 40)  # 8 forecasts per day (3-hour intervals)
            })
            
            track_api_call()
            response = await client.get(f"{Config.BASE_URL}/forecast", params=params)
            response.raise_for_status()
            data = response.json()
            
            # Group forecasts by day
            daily_forecasts = {}
            for item in data["list"]:
                date = datetime.fromtimestamp(item["dt"]).date().isoformat()
                if date not in daily_forecasts:
                    daily_forecasts[date] = []
                
                daily_forecasts[date].append({
                    "time": datetime.fromtimestamp(item["dt"]).strftime("%H:%M"),
                    "temperature": item["main"]["temp"],
                    "feels_like": item["main"]["feels_like"],
                    "condition": item["weather"][0]["main"],
                    "description": item["weather"][0]["description"],
                    "humidity": f"{item['main']['humidity']}%",
                    "wind_speed": item["wind"]["speed"],
                    "precipitation": item.get("rain", {}).get("3h", 0) + item.get("snow", {}).get("3h", 0),
                    "clouds": f"{item['clouds']['all']}%"
                })
            
            result = {
                "location": {
                    "name": data["city"]["name"],
                    "country": data["city"]["country"],
                    "coordinates": data["city"]["coord"]
                },
                "forecast": daily_forecasts,
                "units": units,
                "timezone": data["city"]["timezone"]
            }
            
            cache.set(cache_key, result)
            return {"source": "api", **result}
            
        except Exception as e:
            logger.error(f"Error fetching forecast: {e}")
            return {"error": str(e)}
    
    @mcp.tool
    async def search_location(
        query: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Search for locations by name using geocoding API.
        
        Args:
            query: Location name to search
            limit: Maximum results (1-5)
        
        Returns:
            List of matching locations with coordinates
        """
        try:
            params = {
                "q": query,
                "limit": min(limit, 5),
                "appid": Config.API_KEY
            }
            
            track_api_call()
            response = await client.get(f"{Config.GEO_URL}/direct", params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return {"results": [], "message": f"No locations found for '{query}'"}
            
            results = []
            for location in data:
                results.append({
                    "name": location.get("name"),
                    "country": location.get("country"),
                    "state": location.get("state", ""),
                    "lat": location.get("lat"),
                    "lon": location.get("lon"),
                    "coordinates_string": f"{location.get('lat')},{location.get('lon')}"
                })
            
            return {
                "query": query,
                "count": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error searching location: {e}")
            return {"error": str(e)}
    
    @mcp.tool
    async def get_weather_by_zip(
        zip_code: str,
        country_code: str = "US",
        units: str = Config.DEFAULT_UNITS
    ) -> Dict[str, Any]:
        """
        Get weather by ZIP/postal code.
        
        Args:
            zip_code: ZIP or postal code
            country_code: ISO 3166 country code (e.g., "US", "GB", "DE")
            units: Temperature units
        
        Returns:
            Current weather for the ZIP code location
        """
        try:
            params = {
                "zip": f"{zip_code},{country_code}",
                "appid": Config.API_KEY,
                "units": units
            }
            
            track_api_call()
            response = await client.get(f"{Config.BASE_URL}/weather", params=params)
            response.raise_for_status()
            data = response.json()
            
            return {
                "location": {
                    "zip": zip_code,
                    "country": country_code,
                    "name": data.get("name"),
                    "coordinates": data["coord"]
                },
                "current": {
                    "temperature": data["main"]["temp"],
                    "feels_like": data["main"]["feels_like"],
                    "condition": data["weather"][0]["main"],
                    "description": data["weather"][0]["description"],
                    "humidity": f"{data['main']['humidity']}%",
                    "pressure": f"{data['main']['pressure']} hPa"
                },
                "units": units
            }
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"error": f"ZIP code '{zip_code}' not found in country '{country_code}'"}
            return {"error": f"API error: {e.response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    @mcp.tool
    async def get_air_quality(
        location: str
    ) -> Dict[str, Any]:
        """
        Get air quality/pollution data for a location.
        
        Args:
            location: "lat,lon" coordinates (required for air quality API)
        
        Returns:
            Air quality index and pollutant concentrations
        """
        try:
            # Air quality API requires coordinates
            if "," not in location:
                # First get coordinates for city
                search = await search_location(location, limit=1)
                if not search.get("results"):
                    return {"error": f"Could not find coordinates for '{location}'"}
                
                first_result = search["results"][0]
                lat = first_result["lat"]
                lon = first_result["lon"]
            else:
                lat, lon = location.split(",")
                lat = lat.strip()
                lon = lon.strip()
            
            params = {
                "lat": lat,
                "lon": lon,
                "appid": Config.API_KEY
            }
            
            track_api_call()
            response = await client.get(f"{Config.BASE_URL}/air_pollution", params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("list"):
                return {"error": "No air quality data available"}
            
            air_data = data["list"][0]
            aqi = air_data["main"]["aqi"]
            
            # AQI interpretation
            aqi_levels = {
                1: "Good",
                2: "Fair", 
                3: "Moderate",
                4: "Poor",
                5: "Very Poor"
            }
            
            return {
                "location": {"lat": lat, "lon": lon},
                "air_quality": {
                    "aqi": aqi,
                    "level": aqi_levels.get(aqi, "Unknown"),
                    "description": mcp._get_aqi_description(aqi)
                },
                "pollutants": {
                    "co": f"{air_data['components']['co']} μg/m³",
                    "no2": f"{air_data['components']['no2']} μg/m³",
                    "o3": f"{air_data['components']['o3']} μg/m³",
                    "so2": f"{air_data['components']['so2']} μg/m³",
                    "pm2_5": f"{air_data['components']['pm2_5']} μg/m³",
                    "pm10": f"{air_data['components']['pm10']} μg/m³"
                },
                "timestamp": datetime.fromtimestamp(air_data["dt"]).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error fetching air quality: {e}")
            return {"error": str(e)}
    
    def _get_aqi_description(aqi: int) -> str:
        """Get description for AQI level."""
        descriptions = {
            1: "Air quality is satisfactory, and air pollution poses little or no risk.",
            2: "Air quality is acceptable. However, there may be a risk for some people who are unusually sensitive.",
            3: "Members of sensitive groups may experience health effects. The general public is less likely to be affected.",
            4: "Some members of the general public may experience health effects; members of sensitive groups may experience more serious health effects.",
            5: "Health alert: The risk of health effects is increased for everyone."
        }
        return descriptions.get(aqi, "Unknown air quality level")
    
    # Helper for AQI descriptions
    mcp._get_aqi_description = _get_aqi_description
    
    # ========== Resources ==========
    
    @mcp.resource("weather://api/status")
    def api_status() -> Dict[str, Any]:
        """Get API status and usage statistics."""
        return {
            "status": "operational",
            "api_key_configured": bool(Config.API_KEY),
            "base_url": Config.BASE_URL,
            "daily_limit": Config.MAX_DAILY_CALLS,
            "calls_today": api_calls["count"],
            "calls_remaining": Config.MAX_DAILY_CALLS - api_calls["count"],
            "cache_stats": cache.stats(),
            "timestamp": datetime.now().isoformat()
        }
    
    @mcp.resource("weather://cache/stats")
    def cache_statistics() -> Dict[str, Any]:
        """Get cache statistics."""
        return cache.stats()
    
    @mcp.resource("weather://units/info")
    def units_info() -> Dict[str, Any]:
        """Information about available units."""
        return {
            "available_units": {
                "metric": {
                    "temperature": "Celsius",
                    "wind_speed": "meter/sec",
                    "description": "Metric system (most countries)"
                },
                "imperial": {
                    "temperature": "Fahrenheit",
                    "wind_speed": "miles/hour",
                    "description": "Imperial system (US)"
                },
                "standard": {
                    "temperature": "Kelvin",
                    "wind_speed": "meter/sec",
                    "description": "Scientific standard"
                }
            },
            "default": Config.DEFAULT_UNITS
        }
    
    # ========== Prompts ==========
    
    @mcp.prompt("weather_analysis")
    def weather_analysis_prompt(location: str) -> str:
        """Generate weather analysis prompt."""
        return f"""
        Analyze the weather conditions for {location}:
        
        1. Get current weather conditions
        2. Fetch 5-day forecast
        3. Check air quality if available
        4. Provide insights on:
           - Weather trends over the next few days
           - Any extreme conditions to be aware of
           - Recommendations for outdoor activities
           - Clothing suggestions
           - Health considerations based on air quality
        
        Use the available weather tools to gather comprehensive data.
        """
    
    @mcp.prompt("travel_weather")
    def travel_weather_prompt(destinations: str) -> str:
        """Generate travel weather comparison prompt."""
        return f"""
        Compare weather conditions for travel planning:
        
        Destinations: {destinations}
        
        Please:
        1. Get current weather for each destination
        2. Fetch forecasts for the next 5 days
        3. Compare temperatures, conditions, and precipitation
        4. Identify the best weather windows
        5. Provide packing recommendations
        6. Suggest weather-appropriate activities for each location
        
        Use get_current_weather for each destination and get_forecast tools for comprehensive analysis.
        """
    
    logger.info(f"{Config.SERVER_NAME} created successfully")
    return mcp

# ============================================================================
# Main Execution
# ============================================================================

# Create server instance
mcp = create_weather_server()

def main():
    """Main entry point."""
    import sys
    
    if "--test" in sys.argv:
        # Test mode
        import asyncio
        from fastmcp import Client
        
        async def test():
            async with Client(mcp) as client:
                print("Testing OpenWeatherMap MCP Server...")
                
                # List tools
                tools = await client.list_tools()
                print(f"\nAvailable tools: {[t.name for t in tools]}")
                
                # Test current weather
                result = await client.call_tool(
                    "get_current_weather",
                    {"location": "London", "units": "metric"}
                )
                print(f"\nLondon weather: {result.data}")
                
                # List resources
                resources = await client.list_resources()
                print(f"\nAvailable resources: {[r.uri for r in resources]}")
        
        asyncio.run(test())
    else:
        # Run server
        transport = os.getenv("TRANSPORT", "stdio")
        if transport == "http":
            port = int(os.getenv("PORT", "8000"))
            mcp.run(transport="http", port=port)
        else:
            mcp.run(transport="stdio")

if __name__ == "__main__":
    main()