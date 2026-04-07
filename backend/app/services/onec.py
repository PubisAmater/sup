"""
Сервис интеграции с 1С:Бухгалтерия через OData REST API.

ЧТО: Модуль предоставляет класс OneCService для получения финансовых данных
из 1С:Бухгалтерия --- выручка, маржинальность, фонд оплаты труда (ФОТ).

ЗАЧЕМ: 1С:Бухгалтерия --- основная учётная система компании, где хранятся все
финансовые данные. Эти данные нужны для:
  1. Мониторинга выручки (алерт при отклонении >10% от среднего --- уровень critical).
  2. Расчёта маржинальности для оценки рентабельности бизнеса.
  3. Контроля ФОТ --- крупнейшая статья расходов стоматологической клиники.
  4. Подготовки финансового контекста для совещаний руководства.

КАК: Используется OData REST API 1С (стандартный интерфейс 1С:Предприятия 8.3+).
OData --- это RESTful протокол от Microsoft, который 1С поддерживает из коробки.

Ключевые особенности OData API 1С:
  - URL-формат: {base_url}/odata/standard.odata/{ИмяРегистра}
  - Фильтрация через $filter в query-параметрах (OData-синтаксис).
  - Авторизация: HTTP Basic Auth (логин/пароль пользователя 1С).
  - Ответ: JSON с массивом записей в поле "value".

Регистры накопления, которые используются:
  - AccumulationRegister_Revenue --- регистр выручки (поле Amount).
  - AccumulationRegister_ProfitLoss --- регистр прибылей и убытков
    (поля Revenue и Cost для расчёта маржинальности).
  - AccumulationRegister_Payroll --- регистр начислений зарплаты (поле Amount = ФОТ).

Фильтрация по периоду использует формат OData datetime:
  $filter=Period ge datetime'YYYY-MM-DD' and Period le datetime'YYYY-MM-DD'
"""

import logging
from datetime import date

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class OneCService:
    """
    Сервис для получения финансовых данных из 1С:Бухгалтерия через OData REST API.

    ЧТО: Обёртка над OData API 1С, предоставляющая три метода для получения
    ключевых финансовых показателей: выручка, маржинальность и ФОТ.

    ЗАЧЕМ: Централизованный доступ к финансовым данным 1С для модуля аналитики
    и подготовки контекста совещаний. Позволяет отслеживать финансовое состояние
    бизнеса в реальном времени.

    КАК: Все запросы выполняются через HTTP GET с Basic Auth авторизацией.
    OData-фильтры передаются в query-параметре $filter. Результат ---
    JSON-массив записей регистра накопления, из которого суммируются нужные поля.

    Атрибуты:
        base_url (str): Базовый URL публикации 1С (например, "http://1c-server/accounting").
        username (str): Имя пользователя 1С для Basic Auth.
        password (str): Пароль пользователя 1С для Basic Auth.
    """

    def __init__(self):
        """
        Инициализация сервиса 1С.

        ЧТО: Загружает URL сервера 1С и учётные данные из конфигурации.

        ЗАЧЕМ: base_url указывает на опубликованную информационную базу 1С,
        username/password --- учётные данные пользователя с правами на чтение
        регистров через OData. Хранятся в переменных окружения ONEC_URL,
        ONEC_USERNAME, ONEC_PASSWORD.
        """
        settings = get_settings()
        self.base_url = settings.onec_url
        self.username = settings.onec_username
        self.password = settings.onec_password

    async def get_revenue(self, date_from: date, date_to: date) -> float:
        """
        Получает суммарную выручку за период из регистра накопления 1С.

        ЧТО: Запрашивает записи регистра AccumulationRegister_Revenue за
        указанный период и суммирует поле Amount.

        ЗАЧЕМ: Выручка --- ключевой финансовый показатель. Используется для:
          - Мониторинга: алерт уровня critical при отклонении >10% от среднего.
          - Формулы выручки: сравнение фактической выручки с целевой.
          - Контекст совещаний: динамика выручки за период.

        КАК: GET-запрос к /odata/standard.odata/AccumulationRegister_Revenue
        с OData-фильтром по полю Period. Суммирование Amount по всем записям.
        При ошибке возвращает 0.0.

        Аргументы:
            date_from (date): Начало периода.
            date_to (date): Конец периода.

        Возвращает:
            float: Суммарная выручка в рублях. 0.0 при ошибке.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/odata/standard.odata/AccumulationRegister_Revenue",
                    params={"$filter": f"Period ge datetime'{date_from}' and Period le datetime'{date_to}'"},
                    auth=(self.username, self.password),
                )
                response.raise_for_status()
                data = response.json().get("value", [])
                return sum(item.get("Amount", 0) for item in data)
        except Exception as e:
            logger.error("1C revenue fetch failed: %s", e)
            return 0.0

    async def get_margin(self, date_from: date, date_to: date) -> float:
        """
        Рассчитывает маржинальность (процент прибыли) за период.

        ЧТО: Запрашивает записи регистра AccumulationRegister_ProfitLoss,
        суммирует Revenue и Cost, рассчитывает маржинальность по формуле:
        margin = (Revenue - Cost) / Revenue * 100%.

        ЗАЧЕМ: Маржинальность показывает, какая доля выручки остаётся после
        вычета прямых затрат. Для стоматологической клиники нормальная
        маржинальность --- 40-60%. Падение может указывать на:
          - Рост стоимости материалов.
          - Снижение цен на услуги.
          - Изменение структуры оказываемых услуг (больше дешёвых процедур).

        КАК: GET-запрос к /odata/standard.odata/AccumulationRegister_ProfitLoss.
        Суммирование полей Revenue и Cost отдельно, затем расчёт процента.
        Если Revenue == 0, возвращает 0.0 (защита от деления на ноль).
        При ошибке возвращает 0.0.

        Аргументы:
            date_from (date): Начало периода.
            date_to (date): Конец периода.

        Возвращает:
            float: Маржинальность в процентах (0.0-100.0). 0.0 при ошибке
            или нулевой выручке.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/odata/standard.odata/AccumulationRegister_ProfitLoss",
                    params={"$filter": f"Period ge datetime'{date_from}' and Period le datetime'{date_to}'"},
                    auth=(self.username, self.password),
                )
                response.raise_for_status()
                data = response.json().get("value", [])
                revenue = sum(item.get("Revenue", 0) for item in data)
                cost = sum(item.get("Cost", 0) for item in data)
                return ((revenue - cost) / revenue * 100) if revenue > 0 else 0.0
        except Exception as e:
            logger.error("1C margin fetch failed: %s", e)
            return 0.0

    async def get_payroll(self, date_from: date, date_to: date) -> float:
        """
        Получает суммарный фонд оплаты труда (ФОТ) за период.

        ЧТО: Запрашивает записи регистра AccumulationRegister_Payroll за
        указанный период и суммирует поле Amount.

        ЗАЧЕМ: ФОТ --- крупнейшая статья расходов стоматологической клиники
        (обычно 30-50% от выручки). Контроль ФОТ необходим для:
          - Оценки рентабельности: соотношение ФОТ к выручке.
          - Бюджетирования: план/факт по ФОТ.
          - Принятия решений о найме/сокращении персонала.

        КАК: GET-запрос к /odata/standard.odata/AccumulationRegister_Payroll
        с OData-фильтром по полю Period. Суммирование Amount по всем записям.
        При ошибке возвращает 0.0.

        Аргументы:
            date_from (date): Начало периода.
            date_to (date): Конец периода.

        Возвращает:
            float: Суммарный ФОТ в рублях. 0.0 при ошибке.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/odata/standard.odata/AccumulationRegister_Payroll",
                    params={"$filter": f"Period ge datetime'{date_from}' and Period le datetime'{date_to}'"},
                    auth=(self.username, self.password),
                )
                response.raise_for_status()
                data = response.json().get("value", [])
                return sum(item.get("Amount", 0) for item in data)
        except Exception as e:
            logger.error("1C payroll fetch failed: %s", e)
            return 0.0
