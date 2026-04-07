"""
Сервис интеграции с Google Calendar API для управления расписанием.

ЧТО: Модуль предоставляет класс GoogleCalendarService для поиска свободных
временных слотов в календаре и создания новых событий через Google Calendar API v3.

ЗАЧЕМ: Система автоматически планирует повторные совещания и контрольные встречи
на основе решений, принятых на совещаниях. Для этого нужно знать, когда
руководитель свободен, и уметь создавать события в его календаре.

КАК: Используется Google Calendar REST API v3. Авторизация --- через OAuth-токен
или API-ключ (настройка google_credentials_json). Часовой пояс по умолчанию ---
Europe/Moscow. Рабочее время --- пн-пт с 9:00 до 18:00.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"


class GoogleCalendarService:
    """
    Сервис для работы с Google Calendar API.

    ЧТО: Предоставляет методы для поиска свободных слотов в календаре руководителя
    и создания новых событий с приглашением участников.

    ЗАЧЕМ: Автоматизация планирования встреч --- система может самостоятельно
    найти удобное время и создать событие, не отвлекая секретаря.

    КАК: Работает через Google Calendar REST API v3. Все запросы отправляются
    с Bearer-токеном авторизации. Используется httpx.AsyncClient для
    асинхронных HTTP-запросов.

    Атрибуты:
        calendar_id (str): Идентификатор календаря Google (email или "primary").
        api_key (str): OAuth-токен или API-ключ для авторизации.
    """

    def __init__(self):
        """
        Инициализация сервиса Google Calendar.

        ЧТО: Загружает идентификатор календаря и учётные данные из конфигурации.

        ЗАЧЕМ: calendar_id определяет, с чьим календарём работает сервис
        (обычно это календарь CEO / руководителя). google_credentials_json ---
        это OAuth-токен доступа для авторизации API-вызовов.
        """
        settings = get_settings()
        self.calendar_id = settings.google_calendar_id
        self.api_key = settings.google_credentials_json  # OAuth token or API key

    async def find_free_slots(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        slot_duration_minutes: int = 30,
    ) -> list[dict]:
        """
        Находит свободные временные слоты в календаре руководителя.

        ЧТО: Анализирует занятость календаря за указанный период и возвращает
        список свободных слотов заданной продолжительности.

        ЗАЧЕМ: Позволяет автоматически подобрать время для новых совещаний,
        контрольных встреч и follow-up обсуждений, не конфликтуя с существующими
        событиями в календаре.

        КАК работает алгоритм поиска свободных слотов:
          1. Определяет временной диапазон поиска:
             - date_from: по умолчанию --- текущий момент (UTC).
             - date_to: по умолчанию --- через 7 дней от date_from.
          2. Загружает все события календаря за этот период через _list_events().
          3. Формирует список занятых интервалов (busy_times) из start/end событий.
          4. Итерирует по временной оси с шагом slot_duration_minutes (по умолчанию 30 мин):
             - Начинает с 9:00 первого дня.
             - Проверяет только рабочие дни (пн-пт, weekday < 5).
             - Проверяет только рабочие часы (9:00-18:00).
             - Для каждого потенциального слота проверяет пересечение с busy_times:
               слот свободен, если НИ ОДНО занятое время не пересекается с ним
               (start < slot_end AND end > slot_start).
             - При достижении 18:00 перескакивает на 9:00 следующего дня.
          5. Возвращает список словарей {"start": ISO, "end": ISO} для свободных слотов.
          6. При любой ошибке возвращает пустой список.

        Ограничения:
          - Не учитывает часовые пояса участников (всё в UTC).
          - Рабочее время жёстко задано: 9:00-18:00, пн-пт.
          - Не учитывает праздничные дни.

        Аргументы:
            date_from (datetime | None): Начало периода поиска. По умолчанию --- сейчас (UTC).
            date_to (datetime | None): Конец периода поиска. По умолчанию --- через 7 дней.
            slot_duration_minutes (int): Длительность слота в минутах. По умолчанию 30.

        Возвращает:
            list[dict]: Список свободных слотов. Каждый элемент --- словарь:
                {"start": "<ISO 8601>", "end": "<ISO 8601>"}.
                Пустой список при ошибке или отсутствии свободного времени.
        """
        if not date_from:
            date_from = datetime.now(timezone.utc)
        if not date_to:
            date_to = date_from + timedelta(days=7)

        try:
            events = await self._list_events(date_from, date_to)
            busy_times = [
                (
                    datetime.fromisoformat(e["start"].get("dateTime", e["start"].get("date"))),
                    datetime.fromisoformat(e["end"].get("dateTime", e["end"].get("date"))),
                )
                for e in events
            ]

            slots = []
            current = date_from.replace(hour=9, minute=0, second=0, microsecond=0)
            while current < date_to:
                if current.weekday() < 5 and 9 <= current.hour < 18:
                    slot_end = current + timedelta(minutes=slot_duration_minutes)
                    is_free = not any(
                        start < slot_end and end > current for start, end in busy_times
                    )
                    if is_free:
                        slots.append({
                            "start": current.isoformat(),
                            "end": slot_end.isoformat(),
                        })
                current += timedelta(minutes=slot_duration_minutes)
                if current.hour >= 18:
                    current = current.replace(hour=9, minute=0) + timedelta(days=1)

            return slots
        except Exception as e:
            logger.error("Failed to fetch calendar slots: %s", e)
            return []

    async def create_event(
        self,
        title: str,
        start: datetime,
        end: datetime,
        description: str | None = None,
        attendees: list[str] | None = None,
    ) -> dict | None:
        """
        Создаёт новое событие в Google Calendar.

        ЧТО: Создаёт событие с указанным названием, временем, описанием и списком
        приглашённых участников через Google Calendar API.

        ЗАЧЕМ: Используется для автоматического планирования контрольных встреч,
        follow-up совещаний и других событий, вытекающих из решений совещания.
        Участники автоматически получают приглашение на email.

        КАК работает:
          1. Формирует JSON-тело события с обязательными полями:
             - summary: название события.
             - start/end: время начала и окончания в ISO 8601, часовой пояс Europe/Moscow.
          2. Добавляет опциональные поля:
             - description: текстовое описание (например, контекст из решения).
             - attendees: список email-адресов приглашённых. Google Calendar
               автоматически отправит им email-приглашения.
          3. Отправляет POST-запрос к Google Calendar API.
          4. Возвращает полный объект созданного события (включая event_id, htmlLink).
          5. При ошибке логирует и возвращает None.

        Аргументы:
            title (str): Название события (отображается в календаре).
            start (datetime): Дата и время начала события.
            end (datetime): Дата и время окончания события.
            description (str | None): Описание события. Может содержать контекст
                решения или повестку встречи.
            attendees (list[str] | None): Список email-адресов участников.
                Каждый получит приглашение от Google Calendar.

        Возвращает:
            dict | None: Объект созданного события Google Calendar (содержит id,
            htmlLink, status и др.) или None при ошибке.
        """
        body = {
            "summary": title,
            "start": {"dateTime": start.isoformat(), "timeZone": "Europe/Moscow"},
            "end": {"dateTime": end.isoformat(), "timeZone": "Europe/Moscow"},
        }
        if description:
            body["description"] = description
        if attendees:
            body["attendees"] = [{"email": e} for e in attendees]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{GOOGLE_CALENDAR_API}/calendars/{self.calendar_id}/events",
                    json=body,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error("Failed to create calendar event: %s", e)
            return None

    async def _list_events(self, time_min: datetime, time_max: datetime) -> list[dict]:
        """
        Загружает список событий календаря за указанный период.

        ЧТО: Получает все события (включая повторяющиеся, развёрнутые в отдельные
        экземпляры) из Google Calendar за заданный временной диапазон.

        ЗАЧЕМ: Вспомогательный метод для find_free_slots() --- нужен для
        определения занятых временных интервалов в календаре.

        КАК работает:
          1. Отправляет GET-запрос к /calendars/{id}/events с параметрами:
             - timeMin/timeMax: границы временного диапазона в ISO 8601.
             - singleEvents=true: развернуть повторяющиеся события в отдельные.
             - orderBy=startTime: сортировка по времени начала.
          2. Возвращает массив items из ответа --- список объектов событий.
          3. При ошибке логирует и возвращает пустой список.

        Аргументы:
            time_min (datetime): Начало временного диапазона.
            time_max (datetime): Конец временного диапазона.

        Возвращает:
            list[dict]: Список событий Google Calendar. Каждое содержит поля
            start, end, summary, id и др. Пустой список при ошибке.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{GOOGLE_CALENDAR_API}/calendars/{self.calendar_id}/events",
                    params={
                        "timeMin": time_min.isoformat(),
                        "timeMax": time_max.isoformat(),
                        "singleEvents": "true",
                        "orderBy": "startTime",
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                return response.json().get("items", [])
        except Exception as e:
            logger.error("Failed to list calendar events: %s", e)
            return []
