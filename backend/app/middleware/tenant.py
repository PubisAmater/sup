"""Middleware для извлечения tenant_id из JWT-токена и привязки его к запросу.

Этот middleware является частью мультитенантной архитектуры системы SUP.
Он выполняется на каждый входящий HTTP-запрос ДО обработки эндпоинтом и решает
следующую задачу: извлечь идентификатор тенанта (компании) из JWT-токена
в заголовке ``Authorization`` и сохранить его в ``request.state.tenant_id``.

Это позволяет любому компоненту приложения (эндпоинтам, зависимостям, другим
middleware) получить tenant_id без повторного декодирования токена.

Поток работы:
    1. Для публичных путей (``/docs``, ``/auth``, ``/api/v1/health`` и др.)
       middleware пропускает запрос без обработки.
    2. Для защищённых путей middleware пытается извлечь Bearer-токен
       из заголовка ``Authorization``.
    3. При успешном декодировании JWT — сохраняет ``tenant_id`` из payload
       в ``request.state.tenant_id``.
    4. При ошибке декодирования — логирует предупреждение и устанавливает
       ``tenant_id = None`` (аутентификация обрабатывается на уровне зависимостей).

Примечание: данный middleware НЕ блокирует запросы с невалидным токеном.
Блокировка происходит позже, на уровне FastAPI-зависимости ``get_current_user``.
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.auth.jwt import decode_access_token

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {"/", "/docs", "/openapi.json", "/redoc", "/auth", "/api/v1/health"}


class TenantMiddleware(BaseHTTPMiddleware):
    """Starlette-middleware для извлечения tenant_id из JWT и сохранения в request.state.

    Наследуется от ``BaseHTTPMiddleware``, что обеспечивает стандартный
    жизненный цикл middleware в Starlette/FastAPI: перехват запроса,
    обработка, передача дальше по цепочке через ``call_next``.

    Атрибуты request.state после обработки:
        - ``tenant_id`` (str | None): Идентификатор тенанта из JWT-токена
          или None, если токен отсутствует/невалиден.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Перехватывает входящий запрос, извлекает tenant_id из JWT и передаёт запрос дальше.

        Для публичных путей (определённых в ``PUBLIC_PATHS``) — пропускает запрос
        без обработки токена. Для остальных путей — пытается извлечь Bearer-токен
        из заголовка ``Authorization``, декодировать JWT и сохранить ``tenant_id``
        в ``request.state``.

        При любой ошибке декодирования (невалидный токен, истёкший срок)
        устанавливает ``tenant_id = None`` и пропускает запрос дальше —
        блокировка неаутентифицированных запросов происходит на уровне
        FastAPI-зависимостей, а не в middleware.

        Args:
            request: Входящий HTTP-запрос Starlette.
            call_next: Функция для передачи запроса следующему обработчику в цепочке.

        Returns:
            Response: HTTP-ответ от следующего обработчика в цепочке.
        """
        request.state.tenant_id = None

        path = request.url.path
        if any(path.startswith(p) for p in PUBLIC_PATHS):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = decode_access_token(token)
                request.state.tenant_id = payload.get("tenant_id")
            except Exception as e:
                logger.debug("Failed to decode token in tenant middleware: %s", e)

        return await call_next(request)
