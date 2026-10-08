import asyncio
import logging
from contextlib import AsyncExitStack

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.bot.handlers.clothing import clothing_confirmation, receive_photo
from app.bot.handlers.outfit import (
    another_outfit,
    delete_item,
    feedback,
    history,
    my_closet,
    stats,
    today,
)
from app.bot.handlers.start import (
    add_command,
    city_command,
    help_command,
    preferences_command,
    profile_callback,
    settings_command,
    start,
)
from app.config.settings import get_settings
from app.integrations.gemini import GeminiClient
from app.integrations.supabase import SupabaseClient
from app.integrations.weather import OpenMeteoClient
from app.scheduler.daily_outfit import start_daily_scheduler
from app.services.outfit import OutfitService
from app.services.wardrobe import WardrobeService
from app.services.weather import WeatherService


async def run_bot() -> None:
    settings = get_settings()
    settings.validate_bot_configuration()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    application = (
        Application.builder()
        .token(settings.telegram_bot_token.get_secret_value())
        .build()
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler(["today", "outfit"], today))
    application.add_handler(CommandHandler(["clothes", "mycloset"], my_closet))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("delete", delete_item))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("city", city_command))
    application.add_handler(CommandHandler("preferences", preferences_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(
        CallbackQueryHandler(clothing_confirmation, pattern=r"^clothing:")
    )
    application.add_handler(CallbackQueryHandler(feedback, pattern=r"^feedback:"))
    application.add_handler(
        CallbackQueryHandler(another_outfit, pattern=r"^outfit:another$")
    )
    application.add_handler(
        CallbackQueryHandler(
            profile_callback, pattern=r"^(city:|style:|daily:|menu:|delete:)"
        )
    )
    application.add_handler(MessageHandler(filters.PHOTO, receive_photo))

    async with AsyncExitStack() as resources:
        supabase = SupabaseClient(settings)
        resources.push_async_callback(supabase.aclose)
        gemini = GeminiClient(settings)
        resources.push_async_callback(gemini.aclose)
        weather_client = OpenMeteoClient(settings)
        resources.push_async_callback(weather_client.aclose)
        application.bot_data["supabase"] = supabase
        application.bot_data["settings"] = settings
        application.bot_data["wardrobe"] = WardrobeService(
            gemini, supabase, settings.max_image_size_bytes
        )
        application.bot_data["outfits"] = OutfitService(
            supabase, WeatherService(weather_client)
        )

        initialized = False
        started = False
        scheduler = None
        try:
            await application.initialize()
            initialized = True
            await application.start()
            started = True
            if application.updater is None:
                raise RuntimeError("Telegram polling updater is unavailable")
            await application.updater.start_polling()
            scheduler = start_daily_scheduler(application)
            logging.getLogger(__name__).info("Outfitly.AI Telegram bot is running")
            await asyncio.Event().wait()
        finally:
            if scheduler is not None and scheduler.running:
                scheduler.shutdown(wait=False)
            if application.updater is not None and application.updater.running:
                await application.updater.stop()
            if started and application.running:
                await application.stop()
            if initialized:
                await application.shutdown()


def main() -> None:
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Telegram bot stopped")


if __name__ == "__main__":
    main()
