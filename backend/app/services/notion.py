import uuid

import httpx

from app.config import get_settings

NOTION_API_URL = "https://api.notion.com/v1"


class NotionService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.notion_api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

    async def sync_meeting(self, meeting_id: uuid.UUID, data: dict) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{NOTION_API_URL}/pages",
                headers=self.headers,
                json=data,
            )
            response.raise_for_status()
            return response.json()

    async def sync_task(self, task_id: uuid.UUID, data: dict) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{NOTION_API_URL}/pages",
                headers=self.headers,
                json=data,
            )
            response.raise_for_status()
            return response.json()

    async def query_database(self, database_id: str, filter_params: dict | None = None) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{NOTION_API_URL}/databases/{database_id}/query",
                headers=self.headers,
                json=filter_params or {},
            )
            response.raise_for_status()
            return response.json()
