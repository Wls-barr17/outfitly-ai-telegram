import logging
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.domain.weather import CITIES
from app.integrations.errors import IntegrationError
from app.integrations.supabase import SupabaseClient

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return

    supabase: SupabaseClient = context.application.bot_data["supabase"]
    try:
        settings = context.application.bot_data["settings"]
        await supabase.register_user(
            user.id,
            user.username,
            user.first_name,
            user.last_name,
            settings.daily_outfit_default_time,
        )
    except IntegrationError:
        logger.exception("Unable to register Telegram user %s", user.id)
        await message.reply_text(
            "No pude guardar tu perfil. Inténtalo de nuevo en unos momentos."
        )
        return

    await message.reply_text(
        "👋 ¡Hola! Soy Outfitly.AI, tu estilista personal.\n\n"
        "Combino tu armario con el clima para ayudarte a decidir qué ponerte.",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("✨ Outfit de hoy", callback_data="menu:today")],
                [
                    InlineKeyboardButton("Agregar ropa", callback_data="menu:add"),
                    InlineKeyboardButton("👕 Mi armario", callback_data="menu:closet"),
                ],
                [
                    InlineKeyboardButton(
                        "🌎 Cambiar ciudad", callback_data="menu:city"
                    ),
                    InlineKeyboardButton(
                        "✨ Preferencias", callback_data="menu:preferences"
                    ),
                ],
            ]
        ),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is not None:
        await message.reply_text(
            "/today — outfit de hoy\n/add — subir una prenda\n"
            "/clothes — ver tu armario\n/city — elegir ciudad\n"
            "/preferences — elegir estilo\n/history — historial\n"
            "/settings — recomendaciones diarias\n/help — ayuda"
        )


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "📸 Envíame una foto clara de una prenda; la analizaré para que "
            "confirmes antes de guardarla."
        )


async def city_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        cities = list(CITIES)
        await update.effective_message.reply_text(
            "Elige tu ciudad:",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(city, callback_data=f"city:{city}")
                        for city in cities[index : index + 2]
                    ]
                    for index in range(0, len(cities), 2)
                ]
            ),
        )


async def preferences_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_message:
        styles = (
            "CASUAL",
            "SMART_CASUAL",
            "STREETWEAR",
            "SPORT",
            "FORMAL",
            "MINIMAL",
            "URBAN",
        )
        await update.effective_message.reply_text(
            "Elige tu estilo preferido:",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            style.replace("_", " ").title(),
                            callback_data=f"style:{style}",
                        )
                        for style in styles[index : index + 2]
                    ]
                    for index in range(0, len(styles), 2)
                ]
            ),
        )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None:
        return
    if context.args:
        try:
            parsed = datetime.strptime(context.args[0], "%H:%M").strftime("%H:%M")
            if user is None:
                return
            await context.application.bot_data["supabase"].update_user(
                user.id,
                {
                    "daily_recommendation_time": parsed,
                    "daily_recommendation_enabled": True,
                },
            )
        except (ValueError, IntegrationError):
            await message.reply_text(
                "Usa una hora válida en formato 24 h, por ejemplo /settings 07:30."
            )
            return
        await message.reply_text(f"✅ Outfit diario programado para las {parsed}.")
        return
    await message.reply_text(
        "Puedes programar una hora con /settings HH:MM o activar/desactivar aquí:",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🔔 Activar", callback_data="daily:on"),
                    InlineKeyboardButton("🔕 Desactivar", callback_data="daily:off"),
                ]
            ]
        ),
    )


async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None:
        return
    await query.answer()
    data = str(query.data)
    try:
        if data.startswith("city:"):
            city = data.removeprefix("city:")
            if city not in CITIES:
                await query.edit_message_text("Esa ciudad no está disponible.")
                return
            await context.application.bot_data["supabase"].update_user(
                user.id, {"city": city, "timezone": "America/Bogota"}
            )
            await query.edit_message_text(f"✅ Ciudad actualizada: {city}.")
        elif data.startswith("style:"):
            style = data.split(":", 1)[1]
            await context.application.bot_data["supabase"].update_user(
                user.id, {"preferred_style": style}
            )
            await query.edit_message_text(
                f"✅ Estilo preferido: {style.replace('_', ' ').title()}."
            )
        elif data.startswith("daily:"):
            enabled = data.endswith("on")
            await context.application.bot_data["supabase"].update_user(
                user.id, {"daily_recommendation_enabled": enabled}
            )
            await query.edit_message_text(
                "✅ Recomendación diaria "
                + ("activada." if enabled else "desactivada.")
            )
        elif data == "delete:cancel":
            await query.edit_message_text("Borrado cancelado.")
        elif data.startswith("delete:confirm:"):
            item_id = data.removeprefix("delete:confirm:")
            deleted = await context.application.bot_data[
                "supabase"
            ].delete_clothing_item(user.id, item_id)
            await query.edit_message_text(
                "🗑️ Prenda borrada."
                if deleted
                else "No encontré esa prenda en tu armario."
            )
        elif data.startswith("menu:"):
            action = data.split(":", 1)[1]
            if action == "today":
                from app.bot.handlers.outfit import today

                await query.edit_message_text("Preparando tu outfit...")
                await today(update, context)
            elif action == "add":
                await query.edit_message_text(
                    "📸 Envíame una foto clara de una prenda."
                )
            elif action == "closet":
                from app.bot.handlers.outfit import my_closet

                await query.edit_message_text("Abriendo tu armario...")
                await my_closet(update, context)
            elif action == "city":
                await query.edit_message_text("Elige tu ciudad a continuación.")
                await city_command(update, context)
            elif action == "preferences":
                await query.edit_message_text("Elige tu estilo a continuación.")
                await preferences_command(update, context)
    except IntegrationError:
        logger.exception("Could not update profile for Telegram user %s", user.id)
        await query.edit_message_text(
            "No pude actualizar tu perfil. Inténtalo más tarde."
        )
