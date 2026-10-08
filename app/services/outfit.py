from app.domain.weather import WeatherResponse
from app.integrations.errors import IntegrationError
from app.integrations.supabase import SupabaseClient
from app.recommendation.engine import OutfitCandidate, RecommendationEngine
from app.services.weather import WeatherService


class OutfitService:
    def __init__(
        self,
        repository: SupabaseClient,
        weather: WeatherService,
        engine: RecommendationEngine | None = None,
    ) -> None:
        self._repository = repository
        self._weather = weather
        self._engine = engine or RecommendationEngine()

    async def today(
        self, telegram_id: int, limit: int = 3
    ) -> tuple[WeatherResponse, list[OutfitCandidate], str | None, str]:
        user = await self._repository.get_user(telegram_id)
        if user is None:
            raise IntegrationError("Primero inicia el bot con /start.")
        city = user.get("city") or "Bogotá"
        weather = await self._weather.get_city_weather(city)
        items = await self._repository.list_clothing_items(telegram_id)
        history = await self._repository.recent_outfits(telegram_id)
        recent_ids = [row.get("item_ids", []) for row in history[:7]]
        preferences = await self._repository.get_preferences(telegram_id)
        candidates = self._engine.generate(
            items,
            temperature=weather.temperature,
            rain_probability=weather.rain_probability,
            preferred_style=user.get("preferred_style", "CASUAL"),
            history=recent_ids,
            preferences=preferences,
            limit=limit,
        )
        outfit_id = None
        if candidates:
            outfit_id = await self._repository.save_outfit(
                telegram_id,
                candidates[0].model_dump(),
                weather.model_dump(),
            )
        return weather, candidates, outfit_id, city
