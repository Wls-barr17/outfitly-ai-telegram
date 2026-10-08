# Telegram bot

Create a bot with BotFather and set TELEGRAM_BOT_TOKEN. Run python -m app.bot.runner; it uses long polling. /start upserts a Telegram profile, /add requests a photo, and the bot asks before saving an AI classification. /today creates an outfit recommendation with feedback buttons.

Users explicitly enable daily recommendations with /settings. APScheduler checks enabled profiles every minute and compares local time to the stored delivery time. Keep a single bot process running to avoid duplicate sends.
