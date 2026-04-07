"""
Сервис интеграции с МИС Dental Pro для получения операционных данных клиники.

ЧТО: Модуль предоставляет класс DentalProService для получения данных из
медицинской информационной системы (МИС) Dental Pro --- количество кресел,
загрузка кресел, средний чек, список приёмов.

ЗАЧЕМ: Dental Pro --- это основная МИС стоматологической клиники, где хранятся
все данные о приёмах, расписании кресел и платежах. Эти данные нужны для:
  1. Формулы выручки: Кресла x Загрузка x Средний чек (AnalyticsService).
  2. Мониторинга операционных метрик: загрузка кресел должна быть >= 70%.
  3. Анализа динамики среднего чека для обнаружения отклонений.
  4. Подготовки данных для обсуждения на совещаниях.

КАК: Используется REST API Dental Pro. Авторизация --- Bearer-токен.
Все данные запрашиваются за указанный период (date_from, date_to).
При любых ошибках (сеть, авторизация, таймаут) методы возвращают
безопасные значения по умолчанию (0, 0.0, []) и логируют ошибку.

Какие данные берём из МИС и зачем:
  - chairs (GET /api/chairs): Количество стоматологических кресел ---
    базовый параметр формулы выручки. Определяет максимальную пропускную
    способность клиники.
  - utilization (GET /api/appointments/stats): Процент загрузки кресел ---
    показывает, какая доля рабочего времени кресел фактически занята приёмами.
    Целевой показатель >= 70%. Падение ниже --- сигнал о проблемах с записью.
  - avg_check (GET /api/payments/stats): Средний чек за период ---
    показывает среднюю выручку с одного приёма. Резкое изменение может
    указывать на изменение структуры услуг или ценовой политики.
  - appointments (GET /api/appointments): Детальный список приёмов ---
    используется для глубокого анализа: распределение по врачам, типам услуг,
    времени дня и т.д.
"""

import logging
from datetime import date

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class DentalProService:
    """
    Сервис для получения данных из МИС Dental Pro.

    ЧТО: Обёртка над REST API Dental Pro, предоставляющая методы для получения
    ключевых операционных метрик стоматологической клиники.

    ЗАЧЕМ: Централизованный доступ к данным МИС для модуля аналитики (AnalyticsService)
    и для подготовки контекста совещаний. Все метрики сохраняются как MetricSnapshot
    и используются для обнаружения отклонений.

    КАК: Каждый метод выполняет HTTP GET-запрос к соответствующему endpoint-у
    Dental Pro API с авторизацией через Bearer-токен. Ошибки обрабатываются
    gracefully --- при сбое возвращается значение по умолчанию.

    Атрибуты:
        base_url (str): Базовый URL сервера Dental Pro (например, "https://dental.example.com").
        api_token (str): Bearer-токен для авторизации в API Dental Pro.
    """

    def __init__(self):
        """
        Инициализация сервиса Dental Pro.

        ЧТО: Загружает URL и токен Dental Pro из конфигурации приложения.

        ЗАЧЕМ: base_url указывает на конкретный инстанс Dental Pro клиники,
        а api_token обеспечивает авторизованный доступ к API.
        Хранятся в переменных окружения DENTAL_PRO_URL и DENTAL_PRO_TOKEN.
        """
        settings = get_settings()
        self.base_url = settings.dental_pro_url
        self.api_token = settings.dental_pro_token

    @property
    def headers(self):
        """
        HTTP-заголовки для всех запросов к Dental Pro API.

        ЧТО: Формирует словарь заголовков с Bearer-авторизацией и Accept: application/json.

        ЗАЧЕМ: Все endpoint-ы Dental Pro требуют авторизации через Bearer-токен
        и возвращают данные в формате JSON.

        Возвращает:
            dict: Словарь HTTP-заголовков {"Authorization": "Bearer ...", "Accept": "application/json"}.
        """
        return {"Authorization": f"Bearer {self.api_token}", "Accept": "application/json"}

    async def get_chairs_count(self) -> int:
        """
        Получает общее количество стоматологических кресел в клинике.

        ЧТО: Запрашивает список всех кресел из Dental Pro и возвращает их количество.

        ЗАЧЕМ: Количество кресел --- это базовый параметр формулы выручки клиники:
        Выручка = Кресла x Загрузка x Средний_чек x Рабочие_дни x Часы_в_день.
        Также используется для расчёта целевой выручки (норма: 3 млн руб./мес на кресло).

        КАК: GET-запрос к /api/chairs, подсчёт элементов в массиве data.
        При ошибке возвращает 0.

        Возвращает:
            int: Количество кресел. 0 при ошибке.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/chairs", headers=self.headers
                )
                response.raise_for_status()
                return len(response.json().get("data", []))
        except Exception as e:
            logger.error("DentalPro chairs fetch failed: %s", e)
            return 0

    async def get_utilization(self, date_from: date, date_to: date) -> float:
        """
        Получает процент загрузки стоматологических кресел за период.

        ЧТО: Запрашивает статистику приёмов из Dental Pro и возвращает процент
        загрузки кресел (utilization_percent).

        ЗАЧЕМ: Загрузка кресел --- ключевой операционный показатель клиники.
        Показывает, какая доля доступного рабочего времени кресел фактически
        используется для приёма пациентов. Пороговое значение --- 70% (ниже ---
        алерт уровня warning в AnalyticsService). Падение загрузки может означать:
          - Проблемы с записью пациентов.
          - Отмены и неявки.
          - Нехватку врачей.

        КАК: GET-запрос к /api/appointments/stats с параметрами from/to.
        МИС считает загрузку на своей стороне. При ошибке возвращает 0.0.

        Аргументы:
            date_from (date): Начало периода.
            date_to (date): Конец периода.

        Возвращает:
            float: Процент загрузки (0.0-100.0). 0.0 при ошибке.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/appointments/stats",
                    params={"from": date_from.isoformat(), "to": date_to.isoformat()},
                    headers=self.headers,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("utilization_percent", 0.0)
        except Exception as e:
            logger.error("DentalPro utilization fetch failed: %s", e)
            return 0.0

    async def get_avg_check(self, date_from: date, date_to: date) -> float:
        """
        Получает средний чек за период.

        ЧТО: Запрашивает статистику платежей из Dental Pro и возвращает средний
        чек (среднюю сумму оплаты за один приём).

        ЗАЧЕМ: Средний чек --- третий параметр формулы выручки. Также используется
        для мониторинга отклонений: если средний чек отклоняется более чем на 15%
        от среднего за 30 дней, AnalyticsService генерирует алерт уровня warning.
        Резкое падение среднего чека может указывать на:
          - Сдвиг в структуре услуг (больше дешёвых процедур).
          - Скидочные акции без контроля.
          - Проблемы с допродажами.

        КАК: GET-запрос к /api/payments/stats с параметрами from/to.
        МИС считает avg_check на своей стороне. При ошибке возвращает 0.0.

        Аргументы:
            date_from (date): Начало периода.
            date_to (date): Конец периода.

        Возвращает:
            float: Средний чек в рублях. 0.0 при ошибке.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/payments/stats",
                    params={"from": date_from.isoformat(), "to": date_to.isoformat()},
                    headers=self.headers,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("avg_check", 0.0)
        except Exception as e:
            logger.error("DentalPro avg_check fetch failed: %s", e)
            return 0.0

    async def get_appointments(self, date_from: date, date_to: date) -> list[dict]:
        """
        Получает список приёмов за период.

        ЧТО: Запрашивает детальный список всех приёмов (визитов пациентов)
        из Dental Pro за указанный период.

        ЗАЧЕМ: Детальные данные о приёмах нужны для глубокого анализа:
          - Распределение приёмов по врачам и кабинетам.
          - Анализ типов оказанных услуг.
          - Выявление пиковых и провальных часов/дней.
          - Подсчёт процента отмен и неявок.
        Эти данные могут использоваться для подготовки аналитических отчётов
        к совещаниям руководства.

        КАК: GET-запрос к /api/appointments с параметрами from/to.
        Возвращает массив объектов приёмов из поля data. При ошибке ---
        пустой список.

        Аргументы:
            date_from (date): Начало периода.
            date_to (date): Конец периода.

        Возвращает:
            list[dict]: Список приёмов. Каждый элемент --- словарь с данными
            о приёме (пациент, врач, услуга, время, статус и т.д.).
            Пустой список при ошибке.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/appointments",
                    params={"from": date_from.isoformat(), "to": date_to.isoformat()},
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json().get("data", [])
        except Exception as e:
            logger.error("DentalPro appointments fetch failed: %s", e)
            return []
