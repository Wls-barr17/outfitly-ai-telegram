import base64
import json
import logging

import httpx

from app.config.settings import Settings
from app.domain.clothing import ClothingAnalysis
from app.integrations.errors import IntegrationError

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for image analysis")
        self._api_key = settings.gemini_api_key.get_secret_value()
        self._model = settings.gemini_model
        self._client = httpx.AsyncClient(timeout=settings.request_timeout_seconds)

    async def analyze_clothing(self, image: bytes, mime_type: str) -> ClothingAnalysis:
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent"
        )
        prompt = (
            "You are a clothing catalog classifier. Identify the main garment. "
            "Return JSON only with name (string or null), category (TOP, BOTTOM, "
            "OUTERWEAR, FOOTWEAR, ACCESSORY), subcategory (one of T_SHIRT, SHIRT, "
            "POLO, SWEATER, HOODIE, SWEATSHIRT, TANK_TOP, JEANS, PANTS, CHINOS, "
            "SHORTS, JOGGERS, SWEATPANTS, JACKET, COAT, BOMBER, WINDBREAKER, "
            "RAIN_JACKET, SNEAKERS, RUNNING_SHOES, CASUAL_SHOES, BOOTS, SANDALS, "
            "CAP, HAT, SUNGLASSES, WATCH, BELT, SCARF, BAG, OTHER or null), "
            "garment_type, color, secondary_color (nullable), pattern (nullable), "
            "material (nullable; only if visually evident), style, fit (nullable), "
            "season (nullable), formality (integer 1-5), warmth (integer 1-5), "
            "water_resistance (integer 0-5), description (string), confidence "
            "(number 0-1). Never guess a brand or unseen property. Do not infer "
            "personal attributes about a person."
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": _encode_base64(image),
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING", "nullable": True},
                        "category": {
                            "type": "STRING",
                            "enum": [
                                "TOP",
                                "BOTTOM",
                                "OUTERWEAR",
                                "FOOTWEAR",
                                "ACCESSORY",
                            ],
                        },
                        "subcategory": {"type": "STRING", "nullable": True},
                        "garment_type": {"type": "STRING"},
                        "color": {"type": "STRING"},
                        "secondary_color": {"type": "STRING", "nullable": True},
                        "pattern": {"type": "STRING", "nullable": True},
                        "material": {"type": "STRING", "nullable": True},
                        "style": {"type": "STRING"},
                        "fit": {"type": "STRING", "nullable": True},
                        "season": {"type": "STRING", "nullable": True},
                        "formality": {"type": "INTEGER"},
                        "warmth": {"type": "INTEGER"},
                        "water_resistance": {"type": "INTEGER"},
                        "description": {"type": "STRING", "nullable": True},
                        "confidence": {"type": "NUMBER"},
                    },
                    "required": [
                        "category",
                        "garment_type",
                        "color",
                        "style",
                        "formality",
                        "warmth",
                        "water_resistance",
                        "confidence",
                    ],
                },
            },
        }

        try:
            response = await self._client.post(
                endpoint,
                headers={"x-goog-api-key": self._api_key},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            analysis = ClothingAnalysis.model_validate(json.loads(text))
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            logger.warning("Gemini clothing analysis failed: %s", type(exc).__name__)
            raise IntegrationError(
                "Gemini no pudo analizar la imagen. Verifica la API key e inténtalo "
                "de nuevo."
            ) from exc

        return analysis

    async def aclose(self) -> None:
        await self._client.aclose()


def _encode_base64(image: bytes) -> str:
    return base64.b64encode(image).decode("ascii")
