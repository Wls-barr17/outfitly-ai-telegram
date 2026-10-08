import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from app.integrations.errors import IntegrationError
from app.services.wardrobe import WardrobeService

logger = logging.getLogger(__name__)


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None or not message.photo:
        return

    await message.reply_text("Estoy analizando la foto...")
    try:
        photo_file = await context.bot.get_file(message.photo[-1].file_id)
        image = bytes(await photo_file.download_as_bytearray())
        service: WardrobeService = context.application.bot_data["wardrobe"]
        analysis = await service.analyze_item(image, "image/jpeg")
    except IntegrationError as exc:
        logger.exception("Could not process clothing photo for user %s", user.id)
        await message.reply_text(str(exc))
        return
    except TelegramError:
        logger.exception("Could not download photo for user %s", user.id)
        await message.reply_text(
            "No pude descargar la foto desde Telegram. Inténtalo de nuevo."
        )
        return

    context.user_data["pending_clothing"] = {
        "image": image,
        "mime_type": "image/jpeg",
        "analysis": analysis.model_dump(mode="json"),
    }
    await message.reply_text(
        "He detectado esta prenda:\n"
        f"• {analysis.name or analysis.garment_type}\n"
        f"• Categoría: {analysis.category.value}\n"
        f"• Color: {analysis.color}\n"
        f"• Estilo: {analysis.style}\n"
        f"• Confianza: {analysis.confidence:.0%}\n\n¿Quieres guardarla?",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Guardar", callback_data="clothing:save"),
                    InlineKeyboardButton(
                        "❌ Cancelar", callback_data="clothing:cancel"
                    ),
                ]
            ]
        ),
    )


async def clothing_confirmation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None:
        return
    await query.answer()
    pending = context.user_data.get("pending_clothing")
    if query.data == "clothing:cancel":
        context.user_data.pop("pending_clothing", None)
        await query.edit_message_text(
            "Carga cancelada. Cuando quieras, envíame otra foto."
        )
        return
    if not pending:
        await query.edit_message_text("La carga expiró. Envíame la foto otra vez.")
        return
    try:
        from app.domain.clothing import ClothingAnalysis

        service: WardrobeService = context.application.bot_data["wardrobe"]
        analysis = ClothingAnalysis.model_validate(pending["analysis"])
        await service.save_item(
            user.id, pending["image"], pending["mime_type"], analysis
        )
    except IntegrationError:
        logger.exception("Could not save confirmed clothing for user %s", user.id)
        await query.edit_message_text("No pude guardar la prenda. Inténtalo de nuevo.")
        return
    context.user_data.pop("pending_clothing", None)
    await query.edit_message_text(
        f"✅ {analysis.name or analysis.garment_type} guardada en tu armario."
    )
