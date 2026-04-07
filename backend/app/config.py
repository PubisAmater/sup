from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://sup:sup@localhost:5432/sup"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # Telegram
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # Notion
    notion_api_key: str = ""
    notion_meetings_db_id: str = ""
    notion_decisions_db_id: str = ""
    notion_tasks_db_id: str = ""

    # Yandex SpeechKit
    speechkit_api_key: str = ""
    speechkit_folder_id: str = ""

    # Google Calendar
    google_calendar_id: str = ""
    google_credentials_json: str = ""

    # Dental Pro (MIS)
    dental_pro_url: str = ""
    dental_pro_token: str = ""

    # 1C
    onec_url: str = ""
    onec_username: str = ""
    onec_password: str = ""

    # Bitrix24
    bitrix24_webhook_url: str = ""

    # URLs
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
