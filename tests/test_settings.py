import pytest

from app.config.settings import Settings


def test_bot_configuration_reports_all_missing_secrets() -> None:
    settings = Settings(_env_file=None)

    with pytest.raises(ValueError) as error:
        settings.validate_bot_configuration()

    message = str(error.value)
    assert "TELEGRAM_BOT_TOKEN" in message
    assert "GEMINI_API_KEY" in message
    assert "SUPABASE_URL" in message
    assert "SUPABASE_SERVICE_ROLE_KEY" in message
