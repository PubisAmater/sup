"""
Конфигурация приложения СУП.

Все настройки загружаются из переменных окружения или файла .env.
Использует Pydantic Settings для валидации типов.

Пример .env файла — см. .env.example в корне проекта.

get_settings() — singleton, кэшируется через @lru_cache.
Не создавайте Settings() напрямую — всегда используйте get_settings().
"""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Центральная конфигурация платформы СУП.

    Все поля имеют дефолтные значения для локальной разработки.
    В продакшене значения берутся из переменных окружения.
    """

    # --- База данных ---
    # Формат: postgresql+asyncpg://user:password@host:port/dbname
    # asyncpg — асинхронный драйвер для PostgreSQL
    database_url: str = "postgresql+asyncpg://sup:sup@localhost:5432/sup"

    # --- Redis ---
    # Используется для очередей задач (arq) и кэширования
    redis_url: str = "redis://localhost:6379/0"

    # --- Безопасность ---
    # SECRET_KEY — для подписи JWT токенов. ОБЯЗАТЕЛЬНО сменить в продакшене!
    secret_key: str = "change-me-in-production"
    # Алгоритм подписи JWT (HS256 = HMAC-SHA256)
    algorithm: str = "HS256"
    # Время жизни JWT токена в минутах (1440 = 24 часа)
    access_token_expire_minutes: int = 1440

    # --- Telegram Bot ---
    # Токен бота из @BotFather (формат: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz)
    telegram_bot_token: str = ""
    # Username бота без @ (например: sup_diadent_bot)
    telegram_bot_username: str = ""

    # --- Anthropic Claude API ---
    # API ключ для обработки совещаний ИИ (https://console.anthropic.com)
    anthropic_api_key: str = ""

    # --- Notion ---
    # API токен интеграции Notion (https://www.notion.so/my-integrations)
    notion_api_key: str = ""
    # ID баз данных Notion для синхронизации
    notion_meetings_db_id: str = ""
    notion_decisions_db_id: str = ""
    notion_tasks_db_id: str = ""

    # --- Яндекс SpeechKit ---
    # API ключ для синтеза речи (аудио-саммари отчётов)
    speechkit_api_key: str = ""
    # ID каталога в Яндекс Cloud
    speechkit_folder_id: str = ""

    # --- Google Calendar ---
    # ID календаря CEO для бронирования слотов
    google_calendar_id: str = ""
    # OAuth токен или сервисный аккаунт для Google Calendar API
    google_credentials_json: str = ""

    # --- Dental Pro (МИС) ---
    # URL REST API стоматологической информационной системы
    dental_pro_url: str = ""
    # Bearer токен для аутентификации
    dental_pro_token: str = ""

    # --- 1С:Бухгалтерия ---
    # URL OData REST API сервера 1С
    onec_url: str = ""
    # Логин и пароль для Basic Auth
    onec_username: str = ""
    onec_password: str = ""

    # --- Bitrix24 CRM ---
    # Webhook URL для REST API (формат: https://company.bitrix24.ru/rest/1/xxxxx/)
    bitrix24_webhook_url: str = ""

    # --- URLs ---
    # URL фронтенда (для CORS и ссылок в уведомлениях)
    frontend_url: str = "http://localhost:3000"
    # URL бэкенда (для бота и внутренних ссылок)
    backend_url: str = "http://localhost:8000"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Возвращает singleton экземпляр настроек. Кэшируется при первом вызове."""
    return Settings()
