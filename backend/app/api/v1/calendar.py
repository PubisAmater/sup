"""Интеграция с Google Calendar: поиск свободных слотов и бронирование.

Модуль предоставляет два эндпоинта для работы с Google Calendar:
- Поиск свободных временных слотов заданной продолжительности в диапазоне дат;
- Бронирование слота (создание события в Google Calendar).

Используется для планирования совещаний с учётом занятости участников.
Работает через сервис ``GoogleCalendarService``, который инкапсулирует
взаимодействие с Google Calendar API.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends, Query

from app.dependencies import get_current_user
from app.services.google_calendar import GoogleCalendarService

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/slots")
async def list_free_slots(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    duration: int = Query(30, ge=15, le=120),
    current_user: dict = Depends(get_current_user),
):
    """Ищет свободные временные слоты в Google Calendar.

    Анализирует занятость календаря и возвращает доступные окна
    заданной продолжительности. Используется при планировании совещаний
    для автоматического подбора удобного времени.

    Args:
        date_from: Начало диапазона поиска (по умолчанию — сейчас).
        date_to: Конец диапазона поиска (по умолчанию — через 7 дней).
        duration: Длительность слота в минутах (15-120, по умолчанию 30).
        current_user: Данные текущего пользователя из JWT.

    Returns:
        dict: ``{"slots": [...]}`` — список свободных временных окон.
    """
    calendar = GoogleCalendarService()
    slots = await calendar.find_free_slots(
        date_from=date_from,
        date_to=date_to,
        slot_duration_minutes=duration,
    )
    return {"slots": slots}


@router.post("/book")
async def book_slot(
    title: str = Body(...),
    start: datetime = Body(...),
    end: datetime = Body(...),
    description: str | None = Body(None),
    current_user: dict = Depends(get_current_user),
):
    """Бронирует временной слот, создавая событие в Google Calendar.

    Создаёт новое событие в календаре с указанными параметрами.
    Используется после выбора свободного слота при создании совещания.

    Args:
        title: Название события (совещания).
        start: Время начала события.
        end: Время окончания события.
        description: Описание события (необязательно).
        current_user: Данные текущего пользователя из JWT.

    Returns:
        dict: ``{"status": "booked", "event": {...}}`` при успехе
              или ``{"status": "failed", "message": "..."}`` при ошибке.
    """
    calendar = GoogleCalendarService()
    event = await calendar.create_event(
        title=title,
        start=start,
        end=end,
        description=description,
    )
    if event:
        return {"status": "booked", "event": event}
    return {"status": "failed", "message": "Could not create calendar event"}
