"""Эндпоинт проверки работоспособности сервиса (health check).

Используется для мониторинга доступности API — балансировщиками нагрузки,
Kubernetes liveness/readiness пробами и внешними системами наблюдения.
Возвращает статус и текущую версию приложения.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Проверяет, что сервис запущен и отвечает на запросы.

    Возвращает JSON со статусом ``ok`` и текущей версией API.
    Используется инфраструктурой (Docker, K8s, мониторинг) для определения
    доступности бэкенда. Не требует авторизации.

    Returns:
        dict: ``{"status": "ok", "version": "0.1.0"}``
    """
    return {"status": "ok", "version": "0.1.0"}
