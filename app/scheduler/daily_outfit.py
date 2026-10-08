import logging
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application

from app.integrations.errors import IntegrationError

logger = logging.getLogger(__name__)
_sent: dict[tuple[int, str], bool] = {}


async def send_daily_outfits(application: Application) -> None:
    repository = application.bot_data["supabase"]
    outfit_service = application.bot_data["outfits"]
    try:
        users = await repository.list_daily_users()
    except IntegrationError:
        logger.exception("Could not load users for daily outfit scheduler")
        return
    for user in users:
        telegram_id = int(user["telegram_id"])
        try:
            timezone = ZoneInfo(user.get("timezone") or "America/Bogota")
        except ZoneInfoNotFoundError:
            timezone = ZoneInfo("America/Bogota")
        now = datetime.now(timezone)
        scheduled = str(user.get("daily_recommendation_time") or "07:00")[:5]
        key = (telegram_id, now.date().isoformat())
        if now.strftime("%H:%M") != scheduled or key in _sent:
            continue
        try:
            weather, candidates, outfit_id, city = await outfit_service.today(
                telegram_id, limit=3
            )
            if not candidates:
                await application.bot.send_message(
                    chat_id=telegram_id,
                    text=(
                        "Buenos días ☀️ Todavía no tengo suficientes prendas "
                        "para armar un outfit. Añade un top, pantalón y calzado "
                        "con /add."
                    ),
                )
                _sent[key] = True
                continue
            chosen = candidates[0]
            item_lines = [
                f"• {item.get('name') or item.get('garment_type', 'Prenda')}"
                for item in chosen.items
            ]
            text = (
                "☀️ Buenos días. Aquí está tu outfit para hoy:\n\n"
                f"📍 {city} · {weather.min_temperature:.0f}-"
                f"{weather.max_temperature:.0f}°C · "
                f"🌧️ {weather.rain_probability}% lluvia\n\n"
                + "\n".join(item_lines)
                + f"\n\n🎯 Match: {chosen.score:.0f}%\n💡 {chosen.explanation}"
            )
            keyboard = None
            if outfit_id:
                keyboard = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "❤️ Me encanta", callback_data=f"feedback:5:{outfit_id}"
                            ),
                            InlineKeyboardButton(
                                "👎 No me gusta",
                                callback_data=f"feedback:1:{outfit_id}",
                            ),
                        ]
                    ]
                )
            await application.bot.send_message(
                chat_id=telegram_id, text=text, reply_markup=keyboard
            )
            _sent[key] = True
        except Exception:
            logger.exception(
                "Daily outfit delivery failed for Telegram user %s", telegram_id
            )


def start_daily_scheduler(application: Application) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        send_daily_outfits,
        trigger="interval",
        minutes=1,
        args=[application],
        id="daily-outfit-scheduler",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    return scheduler
