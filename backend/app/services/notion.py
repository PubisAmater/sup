"""
Сервис интеграции с Notion API для синхронизации совещаний, решений и задач.

ЧТО: Модуль предоставляет класс NotionService, который синхронизирует данные
о совещаниях, решениях и задачах из внутренней БД приложения в базы данных Notion.

ЗАЧЕМ: Notion используется как единая база знаний компании. Все протоколы совещаний,
принятые решения и поставленные задачи должны быть доступны сотрудникам в привычном
интерфейсе Notion, а не только во внутренней системе.

КАК: Используется Notion API v2022-06-28 (последняя стабильная версия). Для каждой
сущности (Meeting, Decision, Task) существует отдельная база данных в Notion с
преднастроенными свойствами. Сервис реализует upsert-логику: если страница уже
существует (есть existing_page_id) --- обновляет её, иначе --- создаёт новую.

Маппинг полей на Notion properties:
  Meeting -> Notion "Совещания":
    - title            -> "Название" (title)
    - status           -> "Статус" (select)
    - scheduled_at     -> "Дата" (date)
    - organizer_name   -> "Организатор" (rich_text)
    - summary          -> Контент страницы (paragraph block, макс. 2000 символов)

  Decision -> Notion "Решения":
    - content          -> "Решение" (title, обрезается до 200 символов)
    - status           -> "Статус" (select)
    - priority         -> "Приоритет" (select)
    - assignee_name    -> "Ответственный" (rich_text)
    - due_date         -> "Срок" (date)
    - meeting_title    -> "Совещание" (rich_text)

  Task -> Notion "Задачи":
    - title            -> "Задача" (title)
    - status           -> "Статус" (select)
    - priority         -> "Приоритет" (select)
    - assignee_name    -> "Исполнитель" (rich_text)
    - due_date         -> "Срок" (date)
    - description      -> Контент страницы (paragraph block, макс. 2000 символов)
"""

import logging
import uuid

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

NOTION_API_URL = "https://api.notion.com/v1"


class NotionService:
    """
    Сервис для двусторонней синхронизации данных с Notion.

    ЧТО: Предоставляет методы для создания и обновления страниц в трёх базах данных
    Notion: совещания, решения и задачи. Также позволяет запрашивать данные из любой
    базы данных Notion через метод query_database().

    ЗАЧЕМ: Централизация данных о совещаниях в Notion --- руководители и сотрудники
    видят актуальные решения и задачи в привычном инструменте без необходимости
    входить в отдельную систему.

    КАК: Работает через Notion REST API v2022-06-28. Каждый метод sync_* реализует
    upsert-паттерн: если передан existing_page_id --- вызывается PATCH для обновления,
    иначе --- POST для создания новой страницы. Авторизация через Bearer-токен
    (Internal Integration Token из настроек Notion).

    Атрибуты:
        api_key (str): Notion Internal Integration Token.
        meetings_db_id (str): ID базы данных Notion для совещаний.
        decisions_db_id (str): ID базы данных Notion для решений.
        tasks_db_id (str): ID базы данных Notion для задач.
        headers (dict): HTTP-заголовки для всех запросов к Notion API.
    """

    def __init__(self):
        """
        Инициализация сервиса Notion.

        ЧТО: Загружает API-ключ и идентификаторы трёх баз данных Notion из конфигурации,
        формирует HTTP-заголовки для всех запросов.

        ЗАЧЕМ: Для работы с Notion API необходимы:
          - Internal Integration Token (api_key) --- создаётся в Notion Integrations.
          - ID баз данных --- каждая сущность (совещание, решение, задача)
            хранится в отдельной базе Notion с преднастроенными свойствами.

        Заголовки включают:
          - Authorization: Bearer-токен интеграции.
          - Notion-Version: 2022-06-28 --- фиксированная версия API для стабильности.
          - Content-Type: application/json.
        """
        settings = get_settings()
        self.api_key = settings.notion_api_key
        self.meetings_db_id = settings.notion_meetings_db_id
        self.decisions_db_id = settings.notion_decisions_db_id
        self.tasks_db_id = settings.notion_tasks_db_id
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

    async def sync_meeting(
        self,
        meeting_id: uuid.UUID,
        title: str,
        status: str,
        scheduled_at: str | None = None,
        organizer_name: str | None = None,
        summary: str | None = None,
        existing_page_id: str | None = None,
    ) -> str | None:
        """
        Синхронизирует совещание в базу данных Notion "Совещания".

        ЧТО: Создаёт новую страницу или обновляет существующую в Notion-базе совещаний.

        ЗАЧЕМ: Все совещания должны быть доступны в Notion для просмотра командой.
        Страница содержит название, статус, дату, организатора и резюме (как контент).

        КАК: Upsert-логика:
          - Если existing_page_id передан --- PATCH-запрос на обновление свойств страницы.
          - Если не передан --- POST-запрос на создание новой страницы в meetings_db_id.
          - summary передаётся как paragraph block (контент страницы), обрезается до 2000
            символов (ограничение Notion API на один текстовый блок).

        Маппинг полей -> Notion properties:
          - title -> "Название" (title): Заголовок страницы.
          - status -> "Статус" (select): Выпадающий список.
          - scheduled_at -> "Дата" (date): Дата и время в ISO 8601.
          - organizer_name -> "Организатор" (rich_text): Текстовое поле.
          - summary -> контент страницы (paragraph block).

        Аргументы:
            meeting_id (uuid.UUID): ID совещания в внутренней БД (для логирования).
            title (str): Название совещания.
            status (str): Статус ("scheduled", "in_progress", "completed" и др.).
            scheduled_at (str | None): Дата/время в ISO 8601.
            organizer_name (str | None): Имя организатора.
            summary (str | None): Резюме совещания (обрезается до 2000 символов).
            existing_page_id (str | None): ID существующей Notion-страницы для обновления.

        Возвращает:
            str | None: ID страницы Notion (новой или обновлённой). None при ошибке.
        """
        properties = {
            "Название": {"title": [{"text": {"content": title}}]},
            "Статус": {"select": {"name": status}},
        }
        if scheduled_at:
            properties["Дата"] = {"date": {"start": scheduled_at}}
        if organizer_name:
            properties["Организатор"] = {"rich_text": [{"text": {"content": organizer_name}}]}

        children = []
        if summary:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": summary[:2000]}}]
                },
            })

        try:
            if existing_page_id:
                return await self._update_page(existing_page_id, properties)
            else:
                return await self._create_page(self.meetings_db_id, properties, children)
        except Exception as e:
            logger.error("Failed to sync meeting %s to Notion: %s", meeting_id, e)
            return None

    async def sync_decision(
        self,
        decision_id: uuid.UUID,
        content: str,
        status: str,
        priority: str = "medium",
        assignee_name: str | None = None,
        due_date: str | None = None,
        meeting_title: str | None = None,
        existing_page_id: str | None = None,
    ) -> str | None:
        """
        Синхронизирует решение в базу данных Notion "Решения".

        ЧТО: Создаёт новую страницу или обновляет существующую в Notion-базе решений.

        ЗАЧЕМ: Решения --- ключевой результат совещаний. Их хранение в Notion позволяет
        отслеживать выполнение и искать противоречия с новыми решениями.

        КАК: Upsert-логика аналогична sync_meeting(). Текст решения (content) используется
        как title страницы и обрезается до 200 символов (ограничение Notion для title).

        Маппинг полей -> Notion properties:
          - content -> "Решение" (title): Текст решения, до 200 символов.
          - status -> "Статус" (select): Статус выполнения.
          - priority -> "Приоритет" (select): high/medium/low.
          - assignee_name -> "Ответственный" (rich_text): Имя ответственного.
          - due_date -> "Срок" (date): Дедлайн в ISO 8601.
          - meeting_title -> "Совещание" (rich_text): Название совещания-источника.

        Аргументы:
            decision_id (uuid.UUID): ID решения в внутренней БД (для логирования).
            content (str): Текст решения (обрезается до 200 символов для title).
            status (str): Статус решения.
            priority (str): Приоритет ("high", "medium", "low"). По умолчанию "medium".
            assignee_name (str | None): Имя ответственного.
            due_date (str | None): Срок выполнения в ISO 8601.
            meeting_title (str | None): Название совещания, на котором принято решение.
            existing_page_id (str | None): ID существующей Notion-страницы для обновления.

        Возвращает:
            str | None: ID страницы Notion. None при ошибке.
        """
        properties = {
            "Решение": {"title": [{"text": {"content": content[:200]}}]},
            "Статус": {"select": {"name": status}},
            "Приоритет": {"select": {"name": priority}},
        }
        if assignee_name:
            properties["Ответственный"] = {"rich_text": [{"text": {"content": assignee_name}}]}
        if due_date:
            properties["Срок"] = {"date": {"start": due_date}}
        if meeting_title:
            properties["Совещание"] = {"rich_text": [{"text": {"content": meeting_title}}]}

        try:
            if existing_page_id:
                return await self._update_page(existing_page_id, properties)
            else:
                return await self._create_page(self.decisions_db_id, properties)
        except Exception as e:
            logger.error("Failed to sync decision %s to Notion: %s", decision_id, e)
            return None

    async def sync_task(
        self,
        task_id: uuid.UUID,
        title: str,
        status: str,
        priority: str = "medium",
        assignee_name: str | None = None,
        due_date: str | None = None,
        description: str | None = None,
        existing_page_id: str | None = None,
    ) -> str | None:
        """
        Синхронизирует задачу в базу данных Notion "Задачи".

        ЧТО: Создаёт новую страницу или обновляет существующую в Notion-базе задач.

        ЗАЧЕМ: Задачи, поставленные на совещаниях, должны быть видны исполнителям
        в Notion. Notion-база задач служит единым трекером для всех поручений.

        КАК: Upsert-логика аналогична sync_meeting(). description передаётся как
        paragraph block (контент страницы), обрезается до 2000 символов.

        Маппинг полей -> Notion properties:
          - title -> "Задача" (title): Краткое название задачи.
          - status -> "Статус" (select): Статус выполнения.
          - priority -> "Приоритет" (select): high/medium/low.
          - assignee_name -> "Исполнитель" (rich_text): Имя исполнителя.
          - due_date -> "Срок" (date): Дедлайн в ISO 8601.
          - description -> контент страницы (paragraph block, до 2000 символов).

        Аргументы:
            task_id (uuid.UUID): ID задачи в внутренней БД (для логирования).
            title (str): Краткое название задачи.
            status (str): Статус задачи.
            priority (str): Приоритет ("high", "medium", "low"). По умолчанию "medium".
            assignee_name (str | None): Имя исполнителя.
            due_date (str | None): Срок выполнения в ISO 8601.
            description (str | None): Подробное описание (обрезается до 2000 символов).
            existing_page_id (str | None): ID существующей Notion-страницы для обновления.

        Возвращает:
            str | None: ID страницы Notion. None при ошибке.
        """
        properties = {
            "Задача": {"title": [{"text": {"content": title}}]},
            "Статус": {"select": {"name": status}},
            "Приоритет": {"select": {"name": priority}},
        }
        if assignee_name:
            properties["Исполнитель"] = {"rich_text": [{"text": {"content": assignee_name}}]}
        if due_date:
            properties["Срок"] = {"date": {"start": due_date}}

        children = []
        if description:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": description[:2000]}}]
                },
            })

        try:
            if existing_page_id:
                return await self._update_page(existing_page_id, properties)
            else:
                return await self._create_page(self.tasks_db_id, properties, children)
        except Exception as e:
            logger.error("Failed to sync task %s to Notion: %s", task_id, e)
            return None

    async def query_database(self, database_id: str, filter_params: dict | None = None) -> dict:
        """
        Выполняет запрос к базе данных Notion с опциональными фильтрами.

        ЧТО: Отправляет POST-запрос к Notion Database Query API и возвращает
        результаты (страницы базы данных).

        ЗАЧЕМ: Универсальный метод для чтения данных из любой базы Notion.
        Используется для получения списка решений (при проверке противоречий),
        задач (при синхронизации статусов) и других данных.

        КАК: POST-запрос к /databases/{database_id}/query с JSON-телом,
        содержащим параметры фильтрации (формат Notion Filter API).
        Если filter_params не передан --- возвращает все страницы.

        Аргументы:
            database_id (str): ID базы данных Notion для запроса.
            filter_params (dict | None): Параметры фильтрации в формате Notion API.
                Пример: {"filter": {"property": "Статус", "select": {"equals": "active"}}}.

        Возвращает:
            dict: Полный ответ Notion API, содержащий поле "results" со списком
            страниц и "has_more" для пагинации.

        Исключения:
            httpx.HTTPStatusError: При ошибке Notion API.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{NOTION_API_URL}/databases/{database_id}/query",
                headers=self.headers,
                json=filter_params or {},
            )
            response.raise_for_status()
            return response.json()

    async def _create_page(
        self, database_id: str, properties: dict, children: list | None = None
    ) -> str | None:
        """
        Создаёт новую страницу в указанной базе данных Notion.

        ЧТО: Внутренний метод для создания страницы через POST /pages.

        ЗАЧЕМ: Используется всеми sync_* методами при создании новых записей
        (когда existing_page_id не передан).

        КАК: POST-запрос к Notion Pages API с телом, содержащим parent
        (database_id), properties (свойства) и опционально children (блоки контента).

        Аргументы:
            database_id (str): ID целевой базы данных Notion.
            properties (dict): Свойства страницы в формате Notion API.
            children (list | None): Блоки контента (paragraph, heading и др.).

        Возвращает:
            str | None: ID созданной страницы Notion.

        Исключения:
            httpx.HTTPStatusError: При ошибке Notion API.
        """
        body: dict = {
            "parent": {"database_id": database_id},
            "properties": properties,
        }
        if children:
            body["children"] = children

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{NOTION_API_URL}/pages",
                headers=self.headers,
                json=body,
            )
            response.raise_for_status()
            return response.json()["id"]

    async def _update_page(self, page_id: str, properties: dict) -> str | None:
        """
        Обновляет свойства существующей страницы Notion.

        ЧТО: Внутренний метод для обновления свойств страницы через PATCH /pages/{id}.

        ЗАЧЕМ: Используется всеми sync_* методами при обновлении существующих записей
        (когда existing_page_id передан). Обновляет только свойства (properties),
        контент страницы (children) не обновляется --- это ограничение текущей реализации.

        КАК: PATCH-запрос к Notion Pages API с JSON-телом {"properties": {...}}.
        Notion обновляет только переданные свойства, остальные остаются без изменений.

        Аргументы:
            page_id (str): ID существующей страницы Notion.
            properties (dict): Обновляемые свойства в формате Notion API.

        Возвращает:
            str | None: ID обновлённой страницы (тот же page_id).

        Исключения:
            httpx.HTTPStatusError: При ошибке Notion API.
        """
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{NOTION_API_URL}/pages/{page_id}",
                headers=self.headers,
                json={"properties": properties},
            )
            response.raise_for_status()
            return page_id
