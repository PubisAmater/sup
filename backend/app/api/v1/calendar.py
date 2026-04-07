from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends, Query

from app.dependencies import get_current_user
from app.services.google_calendar import GoogleCalendarService

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/slots")
async def list_free_slots(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    duration: int = Query(30, ge=15, le=120),
    current_user: dict = Depends(get_current_user),
):
    calendar = GoogleCalendarService()
    slots = await calendar.find_free_slots(
        date_from=date_from,
        date_to=date_to,
        slot_duration_minutes=duration,
    )
    return {"slots": slots}


@router.post("/book")
async def book_slot(
    title: str = Body(...),
    start: datetime = Body(...),
    end: datetime = Body(...),
    description: str | None = Body(None),
    current_user: dict = Depends(get_current_user),
):
    calendar = GoogleCalendarService()
    event = await calendar.create_event(
        title=title,
        start=start,
        end=end,
        description=description,
    )
    if event:
        return {"status": "booked", "event": event}
    return {"status": "failed", "message": "Could not create calendar event"}
