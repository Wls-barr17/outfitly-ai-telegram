import base64
import hmac
import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from pydantic import BaseModel, Field

from app.config.settings import Settings, get_settings
from app.domain.weather import CITIES
from app.integrations.errors import IntegrationError
from app.integrations.gemini import GeminiClient
from app.integrations.supabase import SupabaseClient
from app.integrations.weather import OpenMeteoClient
from app.services.outfit import OutfitService
from app.services.wardrobe import WardrobeService
from app.services.weather import WeatherService

logger = logging.getLogger(__name__)
runtime: dict = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.supabase_url and settings.supabase_service_role_key:
        repository = SupabaseClient(settings)
        runtime["repository"] = repository
    if settings.gemini_api_key:
        gemini = GeminiClient(settings)
        runtime["gemini"] = gemini
    weather_client = OpenMeteoClient(settings)
    runtime["weather_client"] = weather_client
    if "repository" in runtime:
        runtime["wardrobe"] = WardrobeService(
            runtime.get("gemini"),
            runtime["repository"],
            settings.max_image_size_bytes,
        )
        runtime["outfits"] = OutfitService(
            runtime["repository"], WeatherService(weather_client)
        )
    try:
        yield
    finally:
        for client in (
            runtime.pop("repository", None),
            runtime.pop("gemini", None),
            runtime.pop("weather_client", None),
        ):
            if client is not None:
                await client.aclose()
        runtime.clear()


app = FastAPI(
    title=get_settings().app_name,
    description="Your wardrobe. Your weather. Your outfit.",
    version="0.2.0",
    lifespan=lifespan,
)


async def authorized(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    token = settings.api_access_token
    if token is None or not token.get_secret_value().strip():
        raise HTTPException(
            status_code=503, detail="Private API access is not configured."
        )
    provided = (
        authorization.removeprefix("Bearer ")
        if authorization and authorization.startswith("Bearer ")
        else ""
    )
    if not hmac.compare_digest(provided, token.get_secret_value()):
        raise HTTPException(status_code=401, detail="Invalid API credentials.")


class ClothingCreate(BaseModel):
    image_base64: str = Field(min_length=1, max_length=14_000_000)
    mime_type: str = Field(pattern=r"^image/(jpeg|png|webp)$")
    confirmed: bool = False


class ClothingUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    color: str | None = Field(default=None, max_length=60)
    style: str | None = Field(default=None, max_length=60)
    is_favorite: bool | None = None
    is_available: bool | None = None


class PreferencesUpdate(BaseModel):
    city: str | None = None
    preferred_style: str | None = Field(
        default=None,
        pattern=r"^(CASUAL|SMART_CASUAL|STREETWEAR|SPORT|FORMAL|MINIMAL|URBAN)$",
    )
    daily_recommendation_enabled: bool | None = None
    daily_recommendation_time: str | None = Field(
        default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$"
    )


def _repo() -> SupabaseClient:
    repository = runtime.get("repository")
    if repository is None:
        raise HTTPException(status_code=503, detail="Database is not configured.")
    return repository


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health", tags=["health"])
async def api_health() -> dict[str, str]:
    return {"status": "ok", "service": "outfitly-ai"}


@app.get("/api/health/ready", tags=["health"])
async def ready() -> dict[str, str]:
    if "repository" not in runtime:
        raise HTTPException(status_code=503, detail="Database is not configured.")
    return {"status": "ready", "service": "outfitly-ai"}


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"name": "Outfitly.AI", "docs": "/docs"}


@app.get("/api/users/{telegram_id}", dependencies=[Depends(authorized)])
async def get_user(telegram_id: int) -> dict:
    user = await _repo().get_user(telegram_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@app.get("/api/clothing", dependencies=[Depends(authorized)])
async def list_clothing(
    telegram_id: int = Query(gt=0), category: str | None = None
) -> list[dict]:
    return await _repo().list_clothing_items(telegram_id, category)


@app.post("/api/clothing", dependencies=[Depends(authorized)], status_code=201)
async def create_clothing(
    payload: ClothingCreate, response: Response, telegram_id: int = Query(gt=0)
) -> dict:
    if "gemini" not in runtime:
        raise HTTPException(status_code=503, detail="Image analysis is not configured.")
    try:
        image = base64.b64decode(payload.image_base64, validate=True)
        service: WardrobeService = runtime["wardrobe"]
        analysis = await service.analyze_item(image, payload.mime_type)
        if not payload.confirmed:
            response.status_code = 202
            return {
                "status": "confirmation_required",
                "analysis": analysis.model_dump(mode="json"),
            }
        await service.save_item(telegram_id, image, payload.mime_type, analysis)
        response.status_code = 201
        return {"status": "saved", "analysis": analysis.model_dump(mode="json")}
    except (ValueError, IntegrationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/clothing/{item_id}", dependencies=[Depends(authorized)])
async def get_clothing(item_id: str, telegram_id: int = Query(gt=0)) -> dict:
    item = await _repo().get_clothing_item(telegram_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Clothing item not found.")
    return item


@app.put("/api/clothing/{item_id}", dependencies=[Depends(authorized)])
async def update_clothing(
    item_id: str, payload: ClothingUpdate, telegram_id: int = Query(gt=0)
) -> dict:
    item = await _repo().update_clothing_item(
        telegram_id, item_id, payload.model_dump(exclude_unset=True)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Clothing item not found.")
    return item


@app.delete("/api/clothing/{item_id}", dependencies=[Depends(authorized)])
async def delete_clothing(item_id: str, telegram_id: int = Query(gt=0)) -> dict:
    if not await _repo().delete_clothing_item(telegram_id, item_id):
        raise HTTPException(status_code=404, detail="Clothing item not found.")
    return {"status": "deleted"}


@app.get("/api/weather/{city}", dependencies=[Depends(authorized)])
async def get_weather(city: str) -> dict:
    if city not in CITIES:
        raise HTTPException(status_code=404, detail="City not found.")
    try:
        return (
            await WeatherService(runtime["weather_client"]).get_city_weather(city)
        ).model_dump()
    except IntegrationError as exc:
        raise HTTPException(
            status_code=502, detail="Weather provider unavailable."
        ) from exc


@app.get("/api/outfits/today", dependencies=[Depends(authorized)])
@app.post("/api/outfits/generate", dependencies=[Depends(authorized)])
async def generate_outfit(telegram_id: int = Query(gt=0)) -> dict:
    if "outfits" not in runtime:
        raise HTTPException(
            status_code=503, detail="Recommendation services are not configured."
        )
    try:
        weather, candidates, outfit_id, city = await runtime["outfits"].today(
            telegram_id
        )
    except IntegrationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "city": city,
        "weather": weather.model_dump(),
        "outfit_id": outfit_id,
        "candidates": [candidate.model_dump() for candidate in candidates],
    }


@app.get("/api/outfits/history", dependencies=[Depends(authorized)])
async def outfit_history(telegram_id: int = Query(gt=0)) -> list[dict]:
    return await _repo().recent_outfits(telegram_id)


@app.get("/api/preferences", dependencies=[Depends(authorized)])
async def preferences(telegram_id: int = Query(gt=0)) -> dict:
    user = await _repo().get_user(telegram_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return {
        "city": user.get("city"),
        "timezone": user.get("timezone"),
        "preferred_style": user.get("preferred_style"),
        "daily_recommendation_enabled": user.get("daily_recommendation_enabled"),
        "category_weights": await _repo().get_preferences(telegram_id),
    }


@app.put("/api/preferences", dependencies=[Depends(authorized)])
async def update_preferences(
    payload: PreferencesUpdate, telegram_id: int = Query(gt=0)
) -> dict:
    values = payload.model_dump(exclude_unset=True)
    if "city" in values and values["city"] not in CITIES:
        raise HTTPException(status_code=422, detail="Unsupported city.")
    await _repo().update_user(telegram_id, values)
    return await get_user(telegram_id)
