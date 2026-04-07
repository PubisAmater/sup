"""Модуль создания и валидации JSON Web Tokens (JWT) для аутентификации в системе SUP.

Реализует два основных метода работы с JWT:
- Создание токена (``create_access_token``): кодирует payload с данными пользователя
  (user_id, tenant_id, role) и устанавливает время истечения.
- Декодирование токена (``decode_access_token``): проверяет подпись, срок действия
  и возвращает payload или выбрасывает HTTP 401.

Токены подписываются секретным ключом из настроек приложения (``settings.secret_key``)
с использованием алгоритма, указанного в ``settings.algorithm`` (по умолчанию HS256).

Время жизни токена настраивается через ``settings.access_token_expire_minutes``
и может быть переопределено при вызове ``create_access_token``.

Этот модуль используется:
- В ``app.auth.router`` для генерации токена при логине через Telegram.
- В ``app.dependencies`` для валидации токена на каждом защищённом запросе.
- В ``app.middleware.tenant`` для извлечения tenant_id из токена.
"""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status

from app.config import get_settings

settings = get_settings()


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Создаёт подписанный JWT access-токен с указанным payload и временем истечения.

    Копирует переданный словарь ``data``, добавляет к нему поле ``exp``
    (время истечения) и подписывает результат секретным ключом.

    Типичный payload, передаваемый в ``data``::

        {
            "sub": "550e8400-e29b-41d4-a716-446655440000",  # UUID пользователя
            "tenant_id": "660e8400-e29b-41d4-a716-446655440001",  # UUID тенанта
            "role": "ceo"  # Роль пользователя
        }

    Args:
        data: Словарь с данными для включения в payload токена.
            Обязательно должен содержать ``sub`` (идентификатор пользователя).
        expires_delta: Время жизни токена. Если не указано, используется
            значение из ``settings.access_token_expire_minutes``.

    Returns:
        str: Закодированный JWT-токен в формате ``header.payload.signature``.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    """Декодирует и валидирует JWT access-токен, возвращая его payload.

    Выполняет полную проверку токена: верифицирует криптографическую подпись
    с использованием секретного ключа приложения и проверяет, что срок действия
    токена (поле ``exp``) не истёк.

    Эта функция вызывается в нескольких местах системы:
    - В ``app.dependencies.get_current_user`` — для аутентификации пользователя
      на каждом защищённом запросе.
    - В ``app.middleware.tenant.TenantMiddleware`` — для извлечения ``tenant_id``
      из токена до обработки запроса эндпоинтом.

    Args:
        token: Строка JWT-токена в формате ``header.payload.signature``,
            извлечённая из заголовка ``Authorization: Bearer <token>``.

    Returns:
        dict: Декодированный payload токена, содержащий поля ``sub``,
        ``tenant_id``, ``role``, ``exp`` и другие данные, заложенные
        при создании токена.

    Raises:
        HTTPException(401): С сообщением ``"Token expired"``, если срок
            действия токена истёк (``jwt.ExpiredSignatureError``).
        HTTPException(401): С сообщением ``"Invalid token"``, если токен
            повреждён, имеет неверную подпись или иную структурную ошибку
            (``jwt.InvalidTokenError``).
    """
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
