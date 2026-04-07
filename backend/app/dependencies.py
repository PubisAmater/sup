"""Модуль FastAPI-зависимостей (Dependency Injection) для аутентификации, авторизации и доступа к БД.

Этот модуль содержит ключевые зависимости, которые внедряются в эндпоинты FastAPI
через механизм ``Depends()``. Они обеспечивают:

- **Аутентификацию**: извлечение и валидацию JWT-токена из заголовка ``Authorization: Bearer ...``
  с помощью ``get_current_user``.
- **Tenant-изоляцию**: автоматическую установку PostgreSQL RLS-контекста для каждого
  запроса через ``get_db``, что гарантирует доступ только к данным своего тенанта.
- **Авторизацию по ролям**: проверку иерархических прав доступа через ``require_role``,
  позволяющую ограничивать эндпоинты определёнными уровнями ролей.

Типичная цепочка зависимостей в защищённом эндпоинте::

    @router.get("/employees")
    async def list_employees(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        ...

При этом ``get_db`` сам зависит от ``get_current_user``, поэтому достаточно
указать только ``Depends(get_db)`` — пользователь будет аутентифицирован автоматически.
"""

import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_access_token
from app.database import async_session_factory, set_tenant_context
from app.models.user import User
from app.utils.permissions import RoleEnum, has_permission

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Извлекает и валидирует JWT-токен из заголовка Authorization, возвращая payload пользователя.

    Эта зависимость является основой аутентификации в системе. Она:
    1. Извлекает Bearer-токен из HTTP-заголовка ``Authorization``.
    2. Декодирует и проверяет подпись JWT через ``decode_access_token``.
    3. Убеждается, что в payload присутствует поле ``sub`` (идентификатор пользователя).
    4. Возвращает полный payload токена как словарь.

    Возвращаемый словарь содержит поля:
        - ``sub``: UUID пользователя (строка).
        - ``tenant_id``: UUID тенанта/компании (строка или None).
        - ``role``: роль пользователя (строка, например ``"ceo"``, ``"line"``).
        - ``exp``: время истечения токена (unix timestamp).

    Args:
        credentials: Объект с Bearer-токеном, автоматически извлекаемый FastAPI
            из заголовка ``Authorization``.

    Returns:
        dict: Декодированный payload JWT-токена.

    Raises:
        HTTPException(401): Если токен невалиден, истёк или не содержит ``sub``.
    """
    payload = decode_access_token(credentials.credentials)
    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
        )
    return payload


async def get_db(
    current_user: dict = Depends(get_current_user),
) -> AsyncGenerator[AsyncSession, None]:
    """Предоставляет асинхронную сессию БД с автоматически установленным tenant-контекстом.

    Это основная зависимость для получения доступа к базе данных в защищённых
    эндпоинтах. Она выполняет следующие шаги:
    1. Аутентифицирует пользователя через зависимость ``get_current_user``.
    2. Создаёт новую асинхронную сессию SQLAlchemy.
    3. Если в JWT-токене пользователя присутствует ``tenant_id``, вызывает
       ``set_tenant_context`` для активации PostgreSQL RLS-политик.
    4. Передаёт сессию в эндпоинт.
    5. Автоматически закрывает сессию после завершения запроса.

    Благодаря установке tenant-контекста все запросы в рамках сессии
    автоматически ограничены данными тенанта текущего пользователя.

    Args:
        current_user: Payload JWT-токена, полученный через ``get_current_user``.

    Yields:
        AsyncSession: Сессия SQLAlchemy с установленным tenant-контекстом.
    """
    async with async_session_factory() as session:
        tenant_id = current_user.get("tenant_id")
        if tenant_id:
            await set_tenant_context(session, uuid.UUID(tenant_id))
        yield session


async def get_db_no_auth() -> AsyncGenerator[AsyncSession, None]:
    """Предоставляет асинхронную сессию БД БЕЗ аутентификации и БЕЗ tenant-контекста.

    Используется в публичных эндпоинтах, где аутентификация не требуется,
    например при регистрации, аутентификации через Telegram или проверке
    здоровья сервиса (health check).

    ВНИМАНИЕ: При использовании этой зависимости RLS-политики НЕ активируются,
    поэтому запросы будут иметь доступ ко всем строкам таблиц. Используйте
    с осторожностью и только в тех случаях, когда это действительно необходимо.

    Yields:
        AsyncSession: Сессия SQLAlchemy без tenant-контекста.
    """
    async with async_session_factory() as session:
        yield session


def require_role(*roles: RoleEnum):
    """Фабрика зависимостей для проверки ролевого доступа к эндпоинту.

    Создаёт FastAPI-зависимость, которая проверяет, что роль текущего
    пользователя имеет достаточный уровень в иерархии для доступа к эндпоинту.
    Проверка основана на иерархической модели ролей: если пользователь имеет
    роль выше требуемой (например, CEO при требовании MIDDLE), доступ разрешается.

    Достаточно, чтобы роль пользователя удовлетворяла хотя бы одной из
    переданных ролей (логическое ИЛИ).

    Пример использования::

        @router.delete("/employees/{id}")
        async def delete_employee(
            current_user: dict = Depends(require_role(RoleEnum.CEO, RoleEnum.CEO_1)),
            db: AsyncSession = Depends(get_db),
        ):
            ...  # Доступно только для CEO и выше, или CEO-1 и выше

    Args:
        *roles: Одна или несколько ролей из ``RoleEnum``. Пользователю достаточно
            иметь уровень, равный или выше любой из указанных ролей.

    Returns:
        Callable: Асинхронная FastAPI-зависимость, возвращающая payload пользователя
        при успешной проверке.

    Raises:
        HTTPException(403): Если роль пользователя недостаточна для доступа.
    """
    async def _check(current_user: dict = Depends(get_current_user)):
        user_role = RoleEnum(current_user.get("role", "line"))
        for role in roles:
            if has_permission(user_role, role):
                return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return _check
