import logging
from datetime import date

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class DentalProService:
    """Integration with Dental Pro MIS (Medical Information System)."""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.dental_pro_url
        self.api_token = settings.dental_pro_token

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.api_token}", "Accept": "application/json"}

    async def get_chairs_count(self) -> int:
        """Get total number of dental chairs."""
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
        """Get chair utilization percentage for period."""
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
        """Get average check amount for period."""
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
        """Get appointments list for period."""
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
