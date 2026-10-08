import logging
import time

import httpx

from app.config.settings import Settings
from app.domain.weather import WeatherResponse
from app.integrations.errors import IntegrationError

logger = logging.getLogger(__name__)
_CACHE_TTL_SECONDS = 600
_weather_cache: dict[tuple[float, float, str], tuple[float, WeatherResponse]] = {}


class OpenMeteoClient:
    def __init__(self, settings: Settings) -> None:
        self._url = settings.weather_base_url
        self._client = httpx.AsyncClient(timeout=settings.request_timeout_seconds)

    async def current(
        self, latitude: float, longitude: float, timezone: str
    ) -> WeatherResponse:
        key = (round(latitude, 4), round(longitude, 4), timezone)
        cached = _weather_cache.get(key)
        if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1].model_copy(deep=True)
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "current": (
                "temperature_2m,apparent_temperature,relative_humidity_2m,"
                "precipitation,weather_code,wind_speed_10m"
            ),
            "daily": (
                "temperature_2m_min,temperature_2m_max,"
                "precipitation_probability_max,uv_index_max"
            ),
            "forecast_days": 1,
        }
        try:
            response = await self._client.get(self._url, params=params)
            response.raise_for_status()
            data = response.json()
            current, daily = data["current"], data["daily"]
            result = WeatherResponse(
                temperature=current["temperature_2m"],
                feels_like=current["apparent_temperature"],
                min_temperature=daily["temperature_2m_min"][0],
                max_temperature=daily["temperature_2m_max"][0],
                humidity=current["relative_humidity_2m"],
                rain_probability=daily["precipitation_probability_max"][0] or 0,
                precipitation=current["precipitation"],
                wind_speed=current["wind_speed_10m"],
                uv_index=daily["uv_index_max"][0],
                weather_code=current["weather_code"],
            )
            _weather_cache[key] = (time.monotonic(), result)
            return result.model_copy(deep=True)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            logger.warning("Open-Meteo lookup failed: %s", type(exc).__name__)
            raise IntegrationError(
                "No pude consultar el clima ahora. Inténtalo de nuevo."
            ) from exc

    async def aclose(self) -> None:
        await self._client.aclose()
