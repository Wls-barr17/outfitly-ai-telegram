from app.domain.weather import CITIES, WeatherResponse
from app.integrations.weather import OpenMeteoClient


class WeatherService:
    def __init__(self, client: OpenMeteoClient) -> None:
        self._client = client

    async def get_city_weather(self, city: str) -> WeatherResponse:
        coordinates = CITIES.get(city)
        if coordinates is None:
            raise ValueError("Ciudad colombiana no reconocida.")
        latitude, longitude, timezone = coordinates
        return await self._client.current(latitude, longitude, timezone)
