import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"


class GoogleCalendarService:
    def __init__(self):
        settings = get_settings()
        self.calendar_id = settings.google_calendar_id
        self.credentials_json = settings.google_credentials_json

    async def find_free_slots(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        slot_duration_minutes: int = 30,
    ) -> list[dict]:
        """Find free time slots in CEO's calendar."""
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
        """Create a calendar event."""
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
                    headers={"Authorization": f"Bearer {self.credentials_json}"},
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error("Failed to create calendar event: %s", e)
            return None

    async def _list_events(self, time_min: datetime, time_max: datetime) -> list[dict]:
        """List events in the calendar."""
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
                    headers={"Authorization": f"Bearer {self.credentials_json}"},
                )
                response.raise_for_status()
                return response.json().get("items", [])
        except Exception as e:
            logger.error("Failed to list calendar events: %s", e)
            return []
