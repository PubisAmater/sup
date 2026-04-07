"""Модуль конфигурации базы данных с поддержкой асинхронного SQLAlchemy и Row-Level Security (RLS).

Этот модуль отвечает за создание и настройку асинхронного движка SQLAlchemy,
фабрики сессий и механизма установки tenant-контекста для PostgreSQL RLS.

Архитектура мультитенантности построена на уровне базы данных: каждая строка
в таблицах привязана к конкретному tenant_id, а PostgreSQL RLS-политики
автоматически фильтруют данные на основании переменной сессии ``app.current_tenant``.
Это гарантирует, что даже при ошибке в прикладном коде данные одного тенанта
не будут доступны другому.

Поток работы:
    1. При старте приложения создаётся глобальный ``engine`` и ``async_session_factory``.
    2. Для каждого HTTP-запроса через dependency injection (см. ``app.dependencies``)
       создаётся новая ``AsyncSession``.
    3. Перед выполнением запросов вызывается ``set_tenant_context``, которая
       устанавливает PostgreSQL-переменную ``app.current_tenant`` — после этого
       все SELECT/INSERT/UPDATE/DELETE автоматически ограничены данными тенанта.
"""

import uuid
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Базовый декларативный класс для всех ORM-моделей проекта.

    Все модели данных (User, Company, Department и т.д.) наследуются от этого класса.
    SQLAlchemy использует его для автоматического обнаружения таблиц, генерации
    метаданных и выполнения миграций через Alembic.

    Пример использования::

        class User(Base):
            __tablename__ = "users"
            id = Column(UUID, primary_key=True)
            ...
    """

    pass


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Асинхронный генератор, предоставляющий сессию БД без автоматической установки tenant-контекста.

    Используется как FastAPI-зависимость в эндпоинтах, где tenant-контекст
    не требуется или устанавливается вручную (например, в auth-роутере при
    первичной аутентификации, когда tenant_id ещё не известен).

    Сессия автоматически закрывается после завершения запроса благодаря
    контекстному менеджеру ``async with``.

    Yields:
        AsyncSession: Активная асинхронная сессия SQLAlchemy.
    """
    async with async_session_factory() as session:
        yield session


async def set_tenant_context(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Устанавливает переменную PostgreSQL-сессии ``app.current_tenant`` для активации RLS-политик.

    Эта функция ДОЛЖНА вызываться в начале каждой сессии, работающей с данными
    конкретного тенанта. После вызова все SQL-запросы в рамках данной сессии
    будут автоматически фильтроваться PostgreSQL RLS-политиками, ограничивая
    доступ только к строкам с соответствующим ``tenant_id``.

    Вызывается автоматически в dependency ``get_db`` (см. ``app.dependencies``),
    которая извлекает ``tenant_id`` из JWT-токена текущего пользователя.

    Args:
        session: Активная асинхронная сессия SQLAlchemy.
        tenant_id: UUID тенанта (компании), данные которого должны быть доступны.

    Пример внутреннего SQL::

        SET app.current_tenant = '550e8400-e29b-41d4-a716-446655440000'
    """
    await session.execute(text("SET app.current_tenant = :tid"), {"tid": str(tenant_id)})
