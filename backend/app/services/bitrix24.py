"""
Сервис интеграции с Bitrix24 CRM через Webhook REST API.

ЧТО: Модуль предоставляет класс Bitrix24Service для получения данных из CRM
Bitrix24 --- лиды, сделки и задачи.

ЗАЧЕМ: Bitrix24 --- CRM-система компании, где ведётся работа с пациентами
(лидами) и сделками. Данные из CRM нужны для:
  1. Мониторинга конверсии лидов в пациентов (порог >= 20%, иначе алерт info).
  2. Анализа воронки продаж: количество сделок, процент выигранных, сумма.
  3. Контроля задач: просроченные задачи сигнализируют о проблемах в процессах.
  4. Подготовки CRM-контекста для совещаний руководства.

КАК: Используется Webhook REST API Bitrix24. Webhook --- это специальный URL
вида https://{domain}.bitrix24.ru/rest/{user_id}/{secret}/, который
предоставляет доступ к REST API без OAuth-авторизации. Это упрощённый
механизм интеграции:
  - Не требует OAuth-токенов и их обновления.
  - Работает от имени конкретного пользователя Bitrix24.
  - Webhook создаётся в настройках Bitrix24: Приложения -> Вебхуки -> Входящий вебхук.
  - Вызов API: GET/POST к {webhook_url}/{метод}, например {webhook_url}/crm.lead.list.

Ограничения Webhook API:
  - Лимит: 2 запроса в секунду (для бесплатных тарифов).
  - Максимум 50 записей за один запрос (пагинация через start/next).
  - Текущая реализация НЕ обрабатывает пагинацию --- получает только первую страницу.
"""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class Bitrix24Service:
    """
    Сервис для получения данных из CRM Bitrix24 через Webhook REST API.

    ЧТО: Обёртка над Webhook REST API Bitrix24, предоставляющая методы для
    получения статистики по лидам, сделкам и задачам CRM.

    ЗАЧЕМ: Централизованный доступ к данным CRM для модуля аналитики и
    подготовки контекста совещаний. Позволяет отслеживать эффективность
    маркетинга и продаж в реальном времени.

    КАК: Все запросы выполняются через HTTP GET к webhook_url/{метод}.
    Webhook URL уже содержит авторизацию (user_id и secret в URL),
    поэтому дополнительных заголовков авторизации не требуется.

    Атрибуты:
        webhook_url (str): URL входящего вебхука Bitrix24, включающий авторизацию.
            Формат: "https://{domain}.bitrix24.ru/rest/{user_id}/{secret}".
    """

    def __init__(self):
        """
        Инициализация сервиса Bitrix24.

        ЧТО: Загружает URL вебхука Bitrix24 из конфигурации.

        ЗАЧЕМ: Webhook URL --- единственный параметр для доступа к API Bitrix24.
        Содержит в себе домен, ID пользователя и секретный ключ.
        Хранится в переменной окружения BITRIX24_WEBHOOK_URL.
        """
        settings = get_settings()
        self.webhook_url = settings.bitrix24_webhook_url

    async def get_leads_count(self, status: str | None = None) -> int:
        """
        Получает количество лидов в CRM, с опциональной фильтрацией по статусу.

        ЧТО: Запрашивает список лидов из Bitrix24 и возвращает их общее количество.

        ЗАЧЕМ: Количество лидов и их статусы нужны для:
          - Оценки эффективности маркетинга (сколько новых обращений).
          - Расчёта конверсии: лиды со статусом "CONVERTED" / всего лидов.
          - Мониторинга: если конверсия < 20% --- алерт уровня info.

        КАК: GET-запрос к {webhook_url}/crm.lead.list. Если передан status,
        добавляется фильтр filter[STATUS_ID]={status}. Bitrix24 возвращает
        total (общее количество записей, удовлетворяющих фильтру) в ответе.
        При ошибке возвращает 0.

        Аргументы:
            status (str | None): Фильтр по STATUS_ID лида. Примеры статусов:
                "NEW" --- новый, "IN_PROCESS" --- в работе, "CONVERTED" --- конвертирован,
                "JUNK" --- спам. None --- без фильтрации (все лиды).

        Возвращает:
            int: Количество лидов. 0 при ошибке.
        """
        try:
            params: dict = {}
            if status:
                params["filter[STATUS_ID]"] = status
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.webhook_url}/crm.lead.list",
                    params=params,
                )
                response.raise_for_status()
                return response.json().get("total", 0)
        except Exception as e:
            logger.error("Bitrix24 leads fetch failed: %s", e)
            return 0

    async def get_deals_stats(self) -> dict:
        """
        Получает статистику по сделкам CRM.

        ЧТО: Запрашивает список сделок из Bitrix24 и рассчитывает агрегированные
        показатели: количество сделок, выигранные, конверсия и общая сумма.

        ЗАЧЕМ: Статистика сделок показывает эффективность отдела продаж:
          - total_deals: общий объём работы менеджеров.
          - won_deals: сколько сделок успешно закрыто.
          - conversion_rate: процент выигранных сделок (эффективность).
          - total_amount: суммарная стоимость сделок в воронке.

        КАК работает:
          1. GET-запрос к {webhook_url}/crm.deal.list с выборкой полей
             ID, STAGE_ID и OPPORTUNITY (сумма сделки).
          2. Подсчёт общего количества сделок (total).
          3. Подсчёт выигранных (STAGE_ID == "WON").
          4. Расчёт конверсии: won / total * 100.
          5. Суммирование OPPORTUNITY по всем сделкам.
          6. При ошибке возвращает нулевые значения.

        Ограничение: возвращает данные только по первой странице (до 50 сделок).

        Возвращает:
            dict: Словарь с ключами:
                - "total_deals" (int): Общее количество сделок.
                - "won_deals" (int): Количество выигранных сделок.
                - "conversion_rate" (float): Процент конверсии (0-100).
                - "total_amount" (float): Суммарная стоимость всех сделок.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.webhook_url}/crm.deal.list",
                    params={"select[]": ["ID", "STAGE_ID", "OPPORTUNITY"]},
                )
                response.raise_for_status()
                deals = response.json().get("result", [])
                total = len(deals)
                won = sum(1 for d in deals if d.get("STAGE_ID") == "WON")
                total_amount = sum(float(d.get("OPPORTUNITY", 0)) for d in deals)
                return {
                    "total_deals": total,
                    "won_deals": won,
                    "conversion_rate": (won / total * 100) if total > 0 else 0,
                    "total_amount": total_amount,
                }
        except Exception as e:
            logger.error("Bitrix24 deals fetch failed: %s", e)
            return {"total_deals": 0, "won_deals": 0, "conversion_rate": 0, "total_amount": 0}

    async def get_tasks_stats(self) -> dict:
        """Get CRM tasks statistics."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.webhook_url}/tasks.task.list",
                    params={"select[]": ["ID", "STATUS", "DEADLINE"]},
                )
                response.raise_for_status()
                tasks = response.json().get("result", {}).get("tasks", [])
                total = len(tasks)
                completed = sum(1 for t in tasks if t.get("status") == "5")
                overdue = sum(1 for t in tasks if t.get("status") != "5" and t.get("deadline"))
                return {"total": total, "completed": completed, "overdue": overdue}
        except Exception as e:
            logger.error("Bitrix24 tasks fetch failed: %s", e)
            return {"total": 0, "completed": 0, "overdue": 0}
