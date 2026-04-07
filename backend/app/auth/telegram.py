"""Модуль верификации аутентификации через Telegram Login Widget с использованием HMAC-SHA256.

Telegram Login Widget позволяет пользователям входить в систему SUP через свой
Telegram-аккаунт. После успешной авторизации в виджете Telegram передаёт на
callback-URL набор данных пользователя (id, имя, username и др.), подписанных
HMAC-SHA256 хешем.

Алгоритм верификации (согласно документации Telegram):
    1. Из полученных данных удаляется поле ``hash``.
    2. Оставшиеся поля сортируются по ключу и объединяются в строку формата
       ``key=value``, разделённую символами новой строки (``\\n``).
    3. Из токена бота вычисляется SHA256-хеш — это секретный ключ для HMAC.
    4. С помощью этого ключа вычисляется HMAC-SHA256 от строки данных.
    5. Вычисленный хеш сравнивается с полученным ``hash`` через
       ``hmac.compare_digest`` (защита от timing-атак).

Если хеши совпадают — данные подлинные и были подписаны Telegram.

Этот модуль используется в ``app.auth.router`` при обработке callback-запроса
от Telegram Login Widget (эндпоинт ``POST /auth/telegram/callback``).

Безопасность:
    - Секретный ключ формируется из ``TELEGRAM_BOT_TOKEN``, который никогда
      не передаётся на клиент.
    - Сравнение хешей выполняется через ``hmac.compare_digest`` для защиты
      от атак по времени (timing attacks).
"""

import hashlib
import hmac
from typing import Any

from pydantic import BaseModel

from app.config import get_settings


class TelegramAuthData(BaseModel):
    """Pydantic-модель для валидации данных, поступающих от Telegram Login Widget.

    При авторизации через виджет Telegram отправляет набор полей на callback-URL.
    Эта модель обеспечивает автоматическую валидацию типов и десериализацию
    входящего JSON в структурированный объект.

    Attributes:
        id: Уникальный Telegram-идентификатор пользователя (числовой).
        first_name: Имя пользователя в Telegram (обязательное поле).
        last_name: Фамилия пользователя (может отсутствовать в Telegram).
        username: Telegram @username (может отсутствовать).
        photo_url: URL аватара пользователя в Telegram (может отсутствовать).
        auth_date: Unix-timestamp момента авторизации. Может использоваться
            для проверки актуальности данных (защита от replay-атак).
        hash: HMAC-SHA256 хеш, вычисленный Telegram для верификации подлинности данных.
    """

    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


def verify_telegram_auth(data: dict[str, Any]) -> bool:
    """Верифицирует подлинность данных аутентификации от Telegram Login Widget.

    Реализует алгоритм проверки HMAC-SHA256, описанный в официальной документации
    Telegram (https://core.telegram.org/widgets/login#checking-authorization).

    Функция извлекает ``hash`` из словаря данных, формирует data-check-string
    из оставшихся полей, вычисляет HMAC-SHA256 с ключом, полученным из токена
    бота, и сравнивает результат с полученным хешем.

    ВАЖНО: функция модифицирует входной словарь ``data`` — сначала удаляет
    ключ ``hash``, а после проверки возвращает его обратно. Это необходимо,
    чтобы поле ``hash`` не участвовало в формировании data-check-string.

    Args:
        data: Словарь с данными от Telegram Login Widget. Должен содержать
            ключ ``hash`` и другие поля (``id``, ``first_name``, ``auth_date`` и т.д.).
            Словарь модифицируется в процессе работы (hash удаляется и добавляется обратно).

    Returns:
        bool: True, если хеш корректен и данные подлинны; False, если хеш
        не совпадает или токен бота не настроен (``TELEGRAM_BOT_TOKEN`` пуст).
    """
    settings = get_settings()
    if not settings.telegram_bot_token:
        return False

    check_hash = data.pop("hash", "")
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data.items()) if v is not None
    )

    secret_key = hashlib.sha256(settings.telegram_bot_token.encode()).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    data["hash"] = check_hash
    return hmac.compare_digest(computed_hash, check_hash)
