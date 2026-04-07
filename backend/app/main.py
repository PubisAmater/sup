"""Главный модуль приложения SUP — точка входа и фабрика FastAPI-приложения.

Реализует паттерн Application Factory: функция ``create_app()`` создаёт,
конфигурирует и возвращает экземпляр FastAPI-приложения. Этот паттерн позволяет:

- Создавать несколько экземпляров приложения с разными настройками (например,
  для тестов и продакшена).
- Изолировать конфигурацию от глобального состояния модуля.
- Легко подключать middleware, роутеры и обработчики жизненного цикла.

Структура приложения:
    - **Lifespan**: управляет жизненным циклом — при завершении корректно
      закрывает пул соединений SQLAlchemy (``engine.dispose()``).
    - **CORS Middleware**: разрешает кросс-доменные запросы с фронтенд-URL,
      указанного в настройках (``settings.frontend_url``).
    - **TenantMiddleware**: извлекает ``tenant_id`` из JWT-токена и сохраняет
      в ``request.state`` для последующего использования.
    - **Роутеры**: подключает auth-роутер (``/auth``) и версионированный
      API-роутер (``/api/v1``).

Запуск приложения (uvicorn)::

    uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import v1_router
from app.auth.router import router as auth_router
from app.config import get_settings
from app.database import engine
from app.middleware.tenant import TenantMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управляет жизненным циклом FastAPI-приложения.

    Реализует паттерн async context manager для lifespan events в FastAPI.
    Код до ``yield`` выполняется при старте приложения (startup), код после —
    при завершении (shutdown).

    При завершении корректно закрывает пул соединений SQLAlchemy, освобождая
    все активные подключения к PostgreSQL. Это предотвращает утечку соединений
    при перезапусках сервера.

    Args:
        app: Экземпляр FastAPI-приложения.

    Yields:
        None: Приложение работает между startup и shutdown.
    """
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    """Фабричная функция для создания и конфигурации экземпляра FastAPI-приложения.

    Выполняет следующие шаги:
        1. Загружает настройки приложения из переменных окружения через ``get_settings()``.
        2. Создаёт экземпляр FastAPI с метаданными (title, description, version)
           и обработчиком жизненного цикла (lifespan).
        3. Подключает CORS Middleware для разрешения кросс-доменных запросов
           с фронтенд-URL.
        4. Подключает TenantMiddleware для извлечения tenant_id из JWT.
        5. Регистрирует роутеры: auth (``/auth``) и API v1 (``/api/v1``).
        6. Добавляет корневой эндпоинт ``GET /`` для health check.

    Returns:
        FastAPI: Полностью сконфигурированный экземпляр приложения, готовый
        к запуску через ASGI-сервер (uvicorn, hypercorn и др.).
    """
    settings = get_settings()

    app = FastAPI(
        title="SUP API",
        description="Система Управления Персоналом",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TenantMiddleware)

    app.include_router(auth_router)
    app.include_router(v1_router)

    @app.get("/")
    async def root():
        return {"service": "SUP API", "version": "0.1.0"}

    return app
