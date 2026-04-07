"""Роутер аутентификации системы SUP.

Содержит эндпоинты для входа в систему через Telegram Login Widget и получения
информации о текущем аутентифицированном пользователе.

Эндпоинты:
    - ``POST /auth/telegram/callback`` — обработка callback от Telegram Login Widget.
      Верифицирует HMAC-подпись данных, находит или создаёт пользователя в БД,
      возвращает JWT access-токен.
    - ``GET /auth/me`` — возвращает профиль текущего пользователя по данным
      из JWT-токена. Требует аутентификации.

Особенности:
    - Эндпоинт ``/auth/telegram/callback`` использует ``get_async_session``
      (без tenant-контекста), потому что при первичной аутентификации tenant_id
      пользователя может быть ещё не известен (новый пользователь).
    - Эндпоинт ``/auth/me`` также использует ``get_async_session`` без RLS,
      так как запрашивает пользователя по UUID из JWT-токена напрямую.
    - При создании нового пользователя ему не назначается tenant_id —
      привязка к компании происходит позже, при onboarding.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token
from app.auth.telegram import TelegramAuthData, verify_telegram_auth
from app.database import get_async_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/telegram/callback")
async def telegram_callback(
    data: TelegramAuthData,
    session: AsyncSession = Depends(get_async_session),
):
    """Обрабатывает callback от Telegram Login Widget и возвращает JWT-токен.

    Поток работы:
        1. Принимает данные аутентификации от Telegram (id, имя, hash и др.).
        2. Верифицирует HMAC-SHA256 подпись через ``verify_telegram_auth``.
        3. Ищет пользователя в БД по ``telegram_id``.
        4. Если пользователь не найден — создаёт нового с базовыми данными из Telegram.
        5. Генерирует JWT access-токен с ``sub``, ``tenant_id`` и ``role``.
        6. Возвращает токен клиенту.

    Args:
        data: Валидированные данные от Telegram Login Widget.
        session: Асинхронная сессия БД без tenant-контекста.

    Returns:
        dict: Словарь ``{"access_token": "...", "token_type": "bearer"}``.

    Raises:
        HTTPException(401): Если HMAC-подпись данных от Telegram невалидна.
    """
    auth_data = data.model_dump()
    if not verify_telegram_auth(auth_data):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram authentication",
        )

    result = await session.execute(
        select(User).where(User.telegram_id == data.id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            id=uuid.uuid4(),
            telegram_id=data.id,
            first_name=data.first_name,
            last_name=data.last_name,
            username=data.username,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    token = create_access_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "role": user.role,
        }
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Возвращает полный профиль текущего аутентифицированного пользователя.

    Извлекает UUID пользователя из поля ``sub`` JWT-токена, загружает
    полную запись пользователя из БД и возвращает её в формате ``UserRead``.

    Используется клиентским приложением для отображения профиля пользователя,
    определения его роли и tenant-привязки после входа в систему.

    Args:
        current_user: Payload JWT-токена (через ``get_current_user``).
        session: Асинхронная сессия БД без tenant-контекста.

    Returns:
        UserRead: Сериализованный профиль пользователя.

    Raises:
        HTTPException(404): Если пользователь с данным UUID не найден в БД
            (например, был удалён после выдачи токена).
    """
    result = await session.execute(
        select(User).where(User.id == uuid.UUID(current_user["sub"]))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
