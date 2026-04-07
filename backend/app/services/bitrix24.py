import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class Bitrix24Service:
    """Integration with Bitrix24 CRM via REST API."""

    def __init__(self):
        settings = get_settings()
        self.webhook_url = settings.bitrix24_webhook_url

    async def get_leads_count(self, status: str | None = None) -> int:
        """Get count of leads, optionally filtered by status."""
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
        """Get deals statistics."""
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
