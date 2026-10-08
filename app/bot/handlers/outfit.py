import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.domain.weather import WeatherResponse
from app.integrations.errors import IntegrationError
from app.services.outfit import OutfitService

logger = logging.getLogger(__name__)


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return
    try:
        service: OutfitService = context.application.bot_data["outfits"]
        weather, candidates, outfit_id, city = await service.today(user.id)
    except IntegrationError as exc:
        await message.reply_text(str(exc))
        return
    if not candidates:
        await message.reply_text(
            "Todavía no puedo armar un outfit. Añade un top, un pantalón y calzado "
            "con /add."
        )
        return
    candidate = candidates[0]
    context.user_data["last_outfit"] = {
        "candidates": [item.model_dump(mode="json") for item in candidates],
        "outfit_id": outfit_id,
        "index": 0,
        "weather": weather.model_dump(mode="json"),
        "city": city,
    }
    await _send_candidate(message, city, weather, candidate.model_dump(), outfit_id)


async def _send_candidate(
    message, city, weather, candidate: dict, outfit_id: str | None
) -> None:
    labels = {
        "TOP": "👕",
        "BOTTOM": "👖",
        "OUTERWEAR": "🧥",
        "FOOTWEAR": "👟",
        "ACCESSORY": "🧢",
    }
    lines = [
        "✨ OUTFIT DE HOY",
        f"📍 {city}",
        f"🌡️ {weather.min_temperature:.0f}°C → {weather.max_temperature:.0f}°C",
        f"🌧️ {weather.rain_probability}% de lluvia",
        "",
    ]
    for item in candidate["items"]:
        category = str(item.get("category", "")).upper()
        lines.append(
            f"{labels.get(category, '✨')} "
            f"{item.get('name') or item.get('garment_type', 'Prenda')}"
        )
    lines.extend(
        [
            "",
            f"🎯 Match: {candidate['score']:.0f}%",
            "",
            f"💡 {candidate['explanation']}",
        ]
    )
    buttons = (
        [
            [
                InlineKeyboardButton(
                    "❤️ Me encanta", callback_data=f"feedback:5:{outfit_id}"
                ),
                InlineKeyboardButton(
                    "👍 Me gusta", callback_data=f"feedback:4:{outfit_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "😐 Normal", callback_data=f"feedback:3:{outfit_id}"
                ),
                InlineKeyboardButton(
                    "👎 No me gusta", callback_data=f"feedback:1:{outfit_id}"
                ),
            ],
        ]
        if outfit_id
        else []
    )
    buttons.append(
        [InlineKeyboardButton("🔄 Otro outfit", callback_data="outfit:another")]
    )
    await message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
    )


async def another_outfit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    state = context.user_data.get("last_outfit")
    if query is None or user is None:
        return
    await query.answer()
    if not state or len(state.get("candidates", [])) < 2:
        await query.message.reply_text(
            "No tengo otra combinación distinta todavía. Añade más prendas "
            "a tu armario."
        )
        return
    index = (state["index"] + 1) % len(state["candidates"])
    candidate = state["candidates"][index]
    try:
        outfit_id = await context.application.bot_data["supabase"].save_outfit(
            user.id, candidate, state["weather"]
        )
    except IntegrationError as exc:
        await query.message.reply_text(str(exc))
        return
    state["index"] = index
    state["outfit_id"] = outfit_id
    await _send_candidate(
        query.message,
        state["city"],
        WeatherResponse.model_validate(state["weather"]),
        candidate,
        outfit_id,
    )


async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None:
        return
    await query.answer()
    try:
        _, rating, outfit_id = str(query.data).split(":", 2)
        repository = context.application.bot_data["supabase"]
        await repository.save_feedback(user.id, outfit_id, int(rating))
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Gracias, tendré en cuenta tu opinión ✨")
    except (IntegrationError, ValueError):
        logger.exception("Could not save outfit feedback for user %s", user.id)
        await query.message.reply_text(
            "No pude guardar tu opinión. Inténtalo de nuevo."
        )


async def my_closet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return
    try:
        items = await context.application.bot_data["supabase"].list_clothing_items(
            user.id
        )
    except IntegrationError as exc:
        await message.reply_text(str(exc))
        return
    if not items:
        await message.reply_text(
            "Tu armario está vacío. Usa /add y envíame una foto para empezar."
        )
        return
    names = [
        f"• {item.get('name') or item['garment_type']} — {item['color']} "
        f"({item['category']})\n  ID: {item['id']}"
        for item in items[:30]
    ]
    await message.reply_text("👕 Tu armario\n\n" + "\n".join(names))


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return
    try:
        rows = await context.application.bot_data["supabase"].recent_outfits(
            user.id, 10
        )
    except IntegrationError as exc:
        await message.reply_text(str(exc))
        return
    if not rows:
        await message.reply_text(
            "Aún no tienes outfits en el historial. Usa /today para empezar."
        )
        return
    await message.reply_text(
        "📅 Tus últimas recomendaciones:\n"
        + "\n".join(
            f"• {str(row['created_at'])[:10]} — {row['score']:.0f}%" for row in rows
        )
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return
    try:
        items = await context.application.bot_data["supabase"].list_clothing_items(
            user.id
        )
        outfits = await context.application.bot_data["supabase"].recent_outfits(
            user.id, 100
        )
    except IntegrationError as exc:
        await message.reply_text(str(exc))
        return
    counts: dict[str, int] = {}
    for item in items:
        category = str(item.get("category", "OTHER"))
        counts[category] = counts.get(category, 0) + 1
    breakdown = "\n".join(f"• {key.title()}: {count}" for key, count in counts.items())
    await message.reply_text(
        f"📊 Tu armario: {len(items)} prendas\n"
        f"{breakdown or 'Todavía no hay prendas.'}\n\n"
        f"✨ Outfits recomendados: {len(outfits)}"
    )


async def delete_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    if not context.args:
        await message.reply_text("Indica el identificador de la prenda: /delete ID")
        return
    item_id = context.args[0]
    if len(item_id) > 40:
        await message.reply_text("El identificador no parece válido.")
        return
    await message.reply_text(
        f"¿Quieres borrar la prenda {item_id}?",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Borrar", callback_data=f"delete:confirm:{item_id}"
                    ),
                    InlineKeyboardButton("Cancelar", callback_data="delete:cancel"),
                ]
            ]
        ),
    )


async def edit_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return
    if len(context.args) < 3:
        await message.reply_text(
            "Uso: /edit ID nombre|color|estilo|disponible|favorita VALOR"
        )
        return
    item_id, field, raw_value = (
        context.args[0],
        context.args[1].lower(),
        " ".join(context.args[2:]),
    )
    fields = {
        "nombre": ("name", raw_value),
        "color": ("color", raw_value),
        "estilo": ("style", raw_value),
        "disponible": (
            "is_available",
            raw_value.lower() in {"si", "sí", "true", "1", "on"},
        ),
        "favorita": (
            "is_favorite",
            raw_value.lower() in {"si", "sí", "true", "1", "on"},
        ),
    }
    if field not in fields or len(raw_value) > 100 or len(item_id) > 40:
        await message.reply_text("Campo o valor no válido.")
        return
    if field in {"disponible", "favorita"} and raw_value.lower() not in {
        "si",
        "sí",
        "no",
        "true",
        "false",
        "1",
        "0",
        "on",
        "off",
    }:
        await message.reply_text("Para ese campo usa sí o no.")
        return
    key, value = fields[field]
    try:
        result = await context.application.bot_data["supabase"].update_clothing_item(
            user.id, item_id, {key: value}
        )
    except IntegrationError as exc:
        await message.reply_text(str(exc))
        return
    if result is None:
        await message.reply_text("No encontré esa prenda en tu armario.")
        return
    await message.reply_text("✅ Prenda actualizada.")
