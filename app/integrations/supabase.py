import logging
from urllib.parse import quote
from uuid import uuid4

import httpx

from app.config.settings import Settings
from app.domain.clothing import ClothingAnalysis
from app.integrations.errors import IntegrationError

logger = logging.getLogger(__name__)


class SupabaseClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
        self._base_url = settings.supabase_url.rstrip("/")
        self._bucket = settings.supabase_storage_bucket
        self._client = httpx.AsyncClient(
            timeout=settings.request_timeout_seconds,
            headers={
                "apikey": settings.supabase_service_role_key.get_secret_value(),
                "Authorization": (
                    "Bearer " + settings.supabase_service_role_key.get_secret_value()
                ),
            },
        )

    async def register_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str,
        last_name: str | None = None,
        daily_time: str = "07:00",
    ) -> None:
        if await self.get_user(telegram_id):
            await self.update_user(
                telegram_id,
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": username,
                },
            )
            return
        try:
            response = await self._client.post(
                f"{self._base_url}/rest/v1/users",
                params={"on_conflict": "telegram_id"},
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                json={
                    "telegram_id": telegram_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "city": "Bogotá",
                    "timezone": "America/Bogota",
                    "preferred_style": "CASUAL",
                    "daily_recommendation_time": daily_time,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Supabase user registration failed: %s", type(exc).__name__)
            raise IntegrationError(
                "No pude guardar tu perfil de Telegram. Inténtalo de nuevo."
            ) from exc

    async def save_clothing_item(
        self,
        telegram_id: int,
        image: bytes,
        mime_type: str,
        analysis: ClothingAnalysis,
    ) -> str:
        extension = {"image/png": "png", "image/webp": "webp"}.get(mime_type, "jpg")
        clothing_id = str(uuid4())
        image_path = f"{telegram_id}/{clothing_id}/{uuid4().hex}.{extension}"
        await self._upload_image(image_path, image, mime_type)

        try:
            response = await self._client.post(
                f"{self._base_url}/rest/v1/clothing_items",
                headers={"Prefer": "return=minimal"},
                json={
                    "id": clothing_id,
                    "user_telegram_id": telegram_id,
                    "image_path": image_path,
                    **analysis.model_dump(mode="json"),
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Supabase clothing insert failed: %s", type(exc).__name__)
            try:
                await self._delete_image(image_path)
            except IntegrationError:
                logger.exception("Could not remove orphaned wardrobe image")
            raise IntegrationError(
                "La imagen se subió, pero no se pudo guardar la prenda."
            ) from exc

        return clothing_id

    async def list_clothing_items(
        self, telegram_id: int, category: str | None = None
    ) -> list[dict]:
        params: dict[str, str] = {
            "user_telegram_id": f"eq.{telegram_id}",
            "select": "*",
            "order": "created_at.desc",
            "limit": "100",
        }
        if category:
            params["category"] = f"eq.{category}"
        try:
            response = await self._client.get(
                f"{self._base_url}/rest/v1/clothing_items", params=params
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Supabase clothing query failed: %s", type(exc).__name__)
            raise IntegrationError("No pude consultar tu armario.") from exc

    async def get_clothing_item(self, telegram_id: int, item_id: str) -> dict | None:
        try:
            response = await self._client.get(
                f"{self._base_url}/rest/v1/clothing_items",
                params={
                    "user_telegram_id": f"eq.{telegram_id}",
                    "id": f"eq.{item_id}",
                    "select": "*",
                    "limit": "1",
                },
            )
            response.raise_for_status()
            rows = response.json()
            return rows[0] if rows else None
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Supabase clothing lookup failed: %s", type(exc).__name__)
            raise IntegrationError("No pude consultar la prenda.") from exc

    async def update_clothing_item(
        self, telegram_id: int, item_id: str, values: dict
    ) -> dict | None:
        allowed = {
            "name",
            "category",
            "subcategory",
            "color",
            "secondary_color",
            "style",
            "fit",
            "formality",
            "warmth",
            "is_favorite",
            "is_available",
        }
        payload = {key: value for key, value in values.items() if key in allowed}
        try:
            response = await self._client.patch(
                f"{self._base_url}/rest/v1/clothing_items",
                params={
                    "user_telegram_id": f"eq.{telegram_id}",
                    "id": f"eq.{item_id}",
                    "select": "*",
                },
                headers={"Prefer": "return=representation"},
                json=payload,
            )
            response.raise_for_status()
            rows = response.json()
            return rows[0] if rows else None
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Supabase clothing update failed: %s", type(exc).__name__)
            raise IntegrationError("No pude actualizar la prenda.") from exc

    async def delete_clothing_item(self, telegram_id: int, item_id: str) -> bool:
        item = await self.get_clothing_item(telegram_id, item_id)
        if item is None:
            return False
        try:
            response = await self._client.delete(
                f"{self._base_url}/rest/v1/clothing_items",
                params={"user_telegram_id": f"eq.{telegram_id}", "id": f"eq.{item_id}"},
            )
            response.raise_for_status()
            await self._delete_image(item["image_path"])
            return True
        except httpx.HTTPError as exc:
            logger.warning("Supabase clothing delete failed: %s", type(exc).__name__)
            raise IntegrationError("No pude borrar la prenda.") from exc

    async def get_user(self, telegram_id: int) -> dict | None:
        try:
            response = await self._client.get(
                f"{self._base_url}/rest/v1/users",
                params={
                    "telegram_id": f"eq.{telegram_id}",
                    "select": "*",
                    "limit": "1",
                },
            )
            response.raise_for_status()
            rows = response.json()
            return rows[0] if rows else None
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Supabase profile lookup failed: %s", type(exc).__name__)
            raise IntegrationError("No pude consultar tu perfil.") from exc

    async def update_user(self, telegram_id: int, values: dict) -> None:
        allowed = {
            "username",
            "first_name",
            "last_name",
            "city",
            "timezone",
            "preferred_style",
            "daily_recommendation_enabled",
            "daily_recommendation_time",
        }
        payload = {key: value for key, value in values.items() if key in allowed}
        if not payload:
            return
        try:
            response = await self._client.patch(
                f"{self._base_url}/rest/v1/users",
                params={"telegram_id": f"eq.{telegram_id}"},
                headers={"Prefer": "return=minimal"},
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Supabase profile update failed: %s", type(exc).__name__)
            raise IntegrationError("No pude actualizar tus preferencias.") from exc

    async def save_outfit(
        self, telegram_id: int, candidate: dict, weather: dict
    ) -> str:
        try:
            snapshot_response = await self._client.post(
                f"{self._base_url}/rest/v1/weather_snapshots",
                headers={"Prefer": "return=representation"},
                json={"user_telegram_id": telegram_id, **weather},
            )
            snapshot_response.raise_for_status()
            snapshot_id = str(snapshot_response.json()[0]["id"])
            response = await self._client.post(
                f"{self._base_url}/rest/v1/outfits",
                headers={"Prefer": "return=representation"},
                json={
                    "user_telegram_id": telegram_id,
                    "score": candidate["score"],
                    "explanation": candidate["explanation"],
                    "weather_snapshot": weather,
                    "weather_snapshot_id": snapshot_id,
                    "item_ids": [item["id"] for item in candidate["items"]],
                },
            )
            response.raise_for_status()
            outfit_id = str(response.json()[0]["id"])
            outfit_items_response = await self._client.post(
                f"{self._base_url}/rest/v1/outfit_items",
                headers={"Prefer": "return=minimal"},
                json=[
                    {
                        "outfit_id": outfit_id,
                        "clothing_item_id": str(item["id"]),
                    }
                    for item in candidate["items"]
                ],
            )
            outfit_items_response.raise_for_status()
            history_response = await self._client.post(
                f"{self._base_url}/rest/v1/outfit_history",
                headers={"Prefer": "return=minimal"},
                json={"user_telegram_id": telegram_id, "outfit_id": outfit_id},
            )
            history_response.raise_for_status()
            return outfit_id
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            logger.warning("Supabase outfit insert failed: %s", type(exc).__name__)
            raise IntegrationError("No pude guardar la recomendación.") from exc

    async def recent_outfits(self, telegram_id: int, limit: int = 30) -> list[dict]:
        try:
            response = await self._client.get(
                f"{self._base_url}/rest/v1/outfits",
                params={
                    "user_telegram_id": f"eq.{telegram_id}",
                    "select": "*",
                    "order": "created_at.desc",
                    "limit": str(limit),
                },
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning(
                "Supabase outfit history query failed: %s", type(exc).__name__
            )
            raise IntegrationError("No pude consultar tu historial.") from exc

    async def list_daily_users(self) -> list[dict]:
        try:
            response = await self._client.get(
                f"{self._base_url}/rest/v1/users",
                params={
                    "daily_recommendation_enabled": "eq.true",
                    "select": "telegram_id,city,timezone,daily_recommendation_time",
                    "limit": "1000",
                },
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Supabase daily users query failed: %s", type(exc).__name__)
            raise IntegrationError("No pude consultar la programación diaria.") from exc

    async def save_feedback(
        self, telegram_id: int, outfit_id: str, rating: int
    ) -> None:
        try:
            owned = await self._client.get(
                f"{self._base_url}/rest/v1/outfits",
                params={
                    "id": f"eq.{outfit_id}",
                    "user_telegram_id": f"eq.{telegram_id}",
                    "select": "id",
                    "limit": "1",
                },
            )
            owned.raise_for_status()
            if not owned.json():
                raise IntegrationError("Esa recomendación no pertenece a tu perfil.")
            response = await self._client.post(
                f"{self._base_url}/rest/v1/feedback",
                headers={"Prefer": "return=minimal"},
                json={
                    "user_telegram_id": telegram_id,
                    "outfit_id": outfit_id,
                    "rating": rating,
                },
            )
            response.raise_for_status()
            outfit_response = await self._client.get(
                f"{self._base_url}/rest/v1/outfits",
                params={
                    "id": f"eq.{outfit_id}",
                    "user_telegram_id": f"eq.{telegram_id}",
                    "select": "item_ids",
                    "limit": "1",
                },
            )
            outfit_response.raise_for_status()
            outfit_rows = outfit_response.json()
            if not outfit_rows:
                raise IntegrationError("Esa recomendación no pertenece a tu perfil.")
            item_ids = outfit_rows[0].get("item_ids", [])
            if item_ids:
                items_response = await self._client.get(
                    f"{self._base_url}/rest/v1/clothing_items",
                    params={
                        "user_telegram_id": f"eq.{telegram_id}",
                        "id": f"in.({','.join(item_ids)})",
                        "select": "subcategory",
                    },
                )
                items_response.raise_for_status()
                weights = await self.get_preferences(telegram_id)
                delta = (rating - 3) * 0.2
                for item in items_response.json():
                    key = item.get("subcategory")
                    if key:
                        weights[key] = max(
                            -3.0, min(3.0, float(weights.get(key, 0)) + delta)
                        )
                preference_response = await self._client.post(
                    f"{self._base_url}/rest/v1/user_preferences",
                    params={"on_conflict": "user_telegram_id"},
                    headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                    json={"user_telegram_id": telegram_id, "category_weights": weights},
                )
                preference_response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Supabase feedback insert failed: %s", type(exc).__name__)
            raise IntegrationError("No pude guardar tu opinión.") from exc

    async def get_preferences(self, telegram_id: int) -> dict[str, float]:
        try:
            response = await self._client.get(
                f"{self._base_url}/rest/v1/user_preferences",
                params={
                    "user_telegram_id": f"eq.{telegram_id}",
                    "select": "category_weights",
                    "limit": "1",
                },
            )
            response.raise_for_status()
            rows = response.json()
            return rows[0].get("category_weights", {}) if rows else {}
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Supabase preferences query failed: %s", type(exc).__name__)
            raise IntegrationError("No pude consultar tus preferencias.") from exc

    async def _upload_image(
        self, image_path: str, image: bytes, mime_type: str
    ) -> None:
        bucket = quote(self._bucket, safe="")
        path = quote(image_path, safe="/")
        try:
            response = await self._client.post(
                f"{self._base_url}/storage/v1/object/{bucket}/{path}",
                content=image,
                headers={"Content-Type": mime_type},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Supabase image upload failed: %s", type(exc).__name__)
            raise IntegrationError(
                "No se pudo subir la imagen a Supabase Storage."
            ) from exc

    async def _delete_image(self, image_path: str) -> None:
        bucket = quote(self._bucket, safe="")
        path = quote(image_path, safe="/")
        try:
            response = await self._client.delete(
                f"{self._base_url}/storage/v1/object/{bucket}/{path}"
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise IntegrationError("Could not remove an unused storage image.") from exc

    async def aclose(self) -> None:
        await self._client.aclose()
