import logging
from datetime import date

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class OneCService:
    """Integration with 1C:Accounting via OData REST API."""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.onec_url
        self.username = settings.onec_username
        self.password = settings.onec_password

    async def get_revenue(self, date_from: date, date_to: date) -> float:
        """Get total revenue for period."""
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
        """Get profit margin percentage for period."""
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
        """Get total payroll (ФОТ) for period."""
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
