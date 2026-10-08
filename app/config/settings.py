from functools import lru_cache

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Outfitly.AI"
    app_env: str = "development"
    app_debug: bool = True
    telegram_bot_token: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"
    supabase_url: str | None = None
    supabase_service_role_key: SecretStr | None = None
    supabase_storage_bucket: str = "clothing-images"
    database_url: str | None = None
    weather_base_url: str = "https://api.open-meteo.com/v1/forecast"
    default_timezone: str = "America/Bogota"
    daily_outfit_default_time: str = "07:00"
    max_image_size_bytes: int = 10_000_000
    api_telegram_token: SecretStr | None = None
    api_access_token: SecretStr | None = None
    request_timeout_seconds: float = 30
    log_level: str = "INFO"

    @field_validator("daily_outfit_default_time")
    @classmethod
    def validate_daily_outfit_time(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", value):
            raise ValueError("DAILY_OUTFIT_DEFAULT_TIME must use HH:MM format")
        return value

    @model_validator(mode="after")
    def validate_configuration(self) -> "Settings":
        if self.request_timeout_seconds <= 0:
            raise ValueError("REQUEST_TIMEOUT_SECONDS must be greater than zero")
        if not self.supabase_storage_bucket.strip():
            raise ValueError("SUPABASE_STORAGE_BUCKET cannot be empty")
        if self.max_image_size_bytes <= 0:
            raise ValueError("MAX_IMAGE_SIZE_BYTES must be greater than zero")
        return self

    def validate_bot_configuration(self) -> None:
        required = {
            "TELEGRAM_BOT_TOKEN": self.telegram_bot_token,
            "GEMINI_API_KEY": self.gemini_api_key,
            "SUPABASE_URL": self.supabase_url,
            "SUPABASE_SERVICE_ROLE_KEY": self.supabase_service_role_key,
        }
        missing = []
        for name, value in required.items():
            if (
                value is None
                or (
                    isinstance(value, SecretStr)
                    and not value.get_secret_value().strip()
                )
                or (isinstance(value, str) and not value.strip())
            ):
                missing.append(name)
        if missing:
            raise ValueError(
                "Missing required bot configuration: " + ", ".join(missing)
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
