from app.domain.clothing import ClothingAnalysis
from app.integrations.errors import IntegrationError
from app.integrations.gemini import GeminiClient
from app.integrations.supabase import SupabaseClient


class WardrobeService:
    def __init__(
        self,
        gemini: GeminiClient | None,
        supabase: SupabaseClient,
        max_image_size_bytes: int = 10_000_000,
    ) -> None:
        self._gemini = gemini
        self._supabase = supabase
        self._max_image_size_bytes = max_image_size_bytes

    async def add_item(
        self, telegram_id: int, image: bytes, mime_type: str
    ) -> ClothingAnalysis:
        analysis = await self.analyze_item(image, mime_type)
        await self.save_item(telegram_id, image, mime_type, analysis)
        return analysis

    async def analyze_item(self, image: bytes, mime_type: str) -> ClothingAnalysis:
        if not image:
            raise IntegrationError("La imagen está vacía.")
        if len(image) > self._max_image_size_bytes:
            raise IntegrationError("La imagen supera el tamaño máximo configurado.")
        signatures = {
            "image/jpeg": (b"\xff\xd8\xff",),
            "image/png": (b"\x89PNG\r\n\x1a\n",),
            "image/webp": (b"RIFF",),
        }
        allowed = signatures.get(mime_type)
        if allowed is None or not any(image.startswith(prefix) for prefix in allowed):
            raise IntegrationError("Formato de imagen no válido. Usa JPG, PNG o WEBP.")
        if mime_type == "image/webp" and image[8:12] != b"WEBP":
            raise IntegrationError("La imagen WEBP está dañada.")
        if mime_type == "image/jpeg" and not image.endswith(b"\xff\xd9"):
            raise IntegrationError("La imagen JPEG está incompleta o dañada.")
        if mime_type == "image/png" and b"IEND" not in image[-16:]:
            raise IntegrationError("La imagen PNG está incompleta o dañada.")
        if self._gemini is None:
            raise IntegrationError("El análisis de imágenes no está configurado.")
        return await self._gemini.analyze_clothing(image, mime_type)

    async def save_item(
        self, telegram_id: int, image: bytes, mime_type: str, analysis: ClothingAnalysis
    ) -> None:
        await self._supabase.save_clothing_item(
            telegram_id=telegram_id,
            image=image,
            mime_type=mime_type,
            analysis=analysis,
        )
