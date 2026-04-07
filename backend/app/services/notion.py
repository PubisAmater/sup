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
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{NOTION_API_URL}/pages/{page_id}",
                headers=self.headers,
                json={"properties": properties},
            )
            response.raise_for_status()
            return page_id
