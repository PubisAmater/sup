"""Lightweight demo API server — serves real data without auth for screenshots."""
import asyncio
import uuid
from datetime import date, datetime, timedelta

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import async_session_factory
from app.models import *

app = FastAPI(title="SUP Demo API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


async def get_session():
    async with async_session_factory() as s:
        yield s


@app.get("/")
async def root():
    return {"service": "SUP API", "version": "0.1.0"}


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/v1/dashboard/stats")
async def dashboard_stats():
    async with async_session_factory() as s:
        emp = (await s.execute(select(func.count(Employee.id)))).scalar() or 0
        now = datetime.now()
        week_start = now - timedelta(days=now.weekday())
        meetings = (await s.execute(
            select(func.count(Meeting.id)).where(Meeting.scheduled_at >= week_start)
        )).scalar() or 0
        tasks_ip = (await s.execute(
            select(func.count(Task.id)).where(Task.status.in_(["todo", "in_progress"]))
        )).scalar() or 0
        overdue = (await s.execute(
            select(func.count(Task.id))
            .where(Task.due_date < date.today())
            .where(Task.status.in_(["todo", "in_progress"]))
        )).scalar() or 0
        return {"employees_count": emp, "meetings_this_week": meetings,
                "tasks_in_progress": tasks_ip, "overdue_tasks": overdue}


@app.get("/api/v1/meetings/")
async def list_meetings(status: str | None = None):
    async with async_session_factory() as s:
        q = select(Meeting).order_by(Meeting.scheduled_at.desc())
        if status:
            q = q.where(Meeting.status == status)
        result = await s.execute(q)
        meetings = result.scalars().all()
        return [_meeting_dict(m) for m in meetings]


@app.get("/api/v1/meetings/{meeting_id}")
async def get_meeting(meeting_id: uuid.UUID):
    async with async_session_factory() as s:
        result = await s.execute(
            select(Meeting).options(selectinload(Meeting.decisions)).where(Meeting.id == meeting_id)
        )
        m = result.scalar_one_or_none()
        if not m:
            return {"error": "not found"}
        d = _meeting_dict(m)
        d["transcript"] = m.transcript
        d["decisions"] = [_decision_dict(dec) for dec in m.decisions]
        return d


@app.get("/api/v1/meetings/{meeting_id}/analysis")
async def get_analysis(meeting_id: uuid.UUID):
    async with async_session_factory() as s:
        result = await s.execute(
            select(Meeting).options(selectinload(Meeting.decisions)).where(Meeting.id == meeting_id)
        )
        m = result.scalar_one_or_none()
        if not m:
            return {"error": "not found"}
        tasks = (await s.execute(select(Task).where(Task.meeting_id == meeting_id))).scalars().all()
        return {
            "meeting_id": str(m.id), "processing_status": m.processing_status,
            "processing_error": m.processing_error, "summary": m.summary,
            "decisions": [_decision_dict(d) for d in m.decisions],
            "tasks": [_task_dict(t) for t in tasks],
        }


@app.get("/api/v1/tasks/")
async def list_tasks(status: str | None = None, priority: str | None = None):
    async with async_session_factory() as s:
        q = select(Task).order_by(Task.created_at.desc())
        if status:
            q = q.where(Task.status == status)
        if priority:
            q = q.where(Task.priority == priority)
        result = await s.execute(q)
        return [_task_dict(t) for t in result.scalars().all()]


@app.get("/api/v1/tasks/overdue")
async def overdue_tasks():
    async with async_session_factory() as s:
        result = await s.execute(
            select(Task).where(Task.due_date < date.today()).where(Task.status.in_(["todo", "in_progress"]))
        )
        return [_task_dict(t) for t in result.scalars().all()]


@app.get("/api/v1/tasks/{task_id}")
async def get_task(task_id: uuid.UUID):
    async with async_session_factory() as s:
        result = await s.execute(select(Task).where(Task.id == task_id))
        t = result.scalar_one_or_none()
        return _task_dict(t) if t else {"error": "not found"}


@app.get("/api/v1/employees/")
async def list_employees(department: str | None = None):
    async with async_session_factory() as s:
        q = select(Employee)
        if department:
            q = q.where(Employee.department == department)
        result = await s.execute(q)
        return [_employee_dict(e) for e in result.scalars().all()]


@app.get("/api/v1/employees/{employee_id}")
async def get_employee(employee_id: uuid.UUID):
    async with async_session_factory() as s:
        result = await s.execute(select(Employee).where(Employee.id == employee_id))
        e = result.scalar_one_or_none()
        return _employee_dict(e) if e else {"error": "not found"}


@app.get("/api/v1/reports/")
async def list_reports():
    async with async_session_factory() as s:
        result = await s.execute(select(WeeklyReport).order_by(WeeklyReport.period_end.desc()))
        return [_report_dict(r) for r in result.scalars().all()]


@app.get("/api/v1/reports/{report_id}")
async def get_report(report_id: uuid.UUID):
    async with async_session_factory() as s:
        result = await s.execute(select(WeeklyReport).where(WeeklyReport.id == report_id))
        r = result.scalar_one_or_none()
        return _report_dict(r) if r else {"error": "not found"}


@app.get("/api/v1/metrics/alerts")
async def list_alerts(resolved: bool | None = None):
    async with async_session_factory() as s:
        q = select(MetricAlert).order_by(MetricAlert.created_at.desc())
        if resolved is not None:
            q = q.where(MetricAlert.is_resolved == resolved)
        result = await s.execute(q)
        return [_alert_dict(a) for a in result.scalars().all()]


@app.get("/api/v1/metrics/revenue-formula")
async def revenue_formula():
    async with async_session_factory() as s:
        async def latest(name):
            r = await s.execute(
                select(MetricSnapshot.metric_value)
                .where(MetricSnapshot.metric_name == name)
                .order_by(MetricSnapshot.recorded_at.desc()).limit(1)
            )
            return r.scalar() or 0

        chairs = await latest("chairs_count")
        util = await latest("utilization_percent")
        avg_check = await latest("avg_check")
        target = chairs * 3_000_000
        actual = chairs * (util / 100) * avg_check * 22 * 8
        return {
            "chairs": int(chairs), "utilization_percent": round(util, 1),
            "avg_check": round(avg_check, 0), "revenue": round(actual, 0),
            "target_revenue": round(target, 0),
            "gap_percent": round((1 - actual / target) * 100, 1) if target > 0 else 0,
        }


@app.get("/api/v1/scores/leaderboard")
async def leaderboard():
    async with async_session_factory() as s:
        result = await s.execute(
            select(ScoreEntry.user_id, User.first_name, User.last_name,
                   func.sum(ScoreEntry.points).label("total"))
            .join(User, ScoreEntry.user_id == User.id)
            .group_by(ScoreEntry.user_id, User.first_name, User.last_name)
            .order_by(func.sum(ScoreEntry.points).desc())
        )
        return [
            {"user_id": str(r.user_id), "first_name": r.first_name,
             "last_name": r.last_name, "total_points": r.total or 0, "rank": i + 1}
            for i, r in enumerate(result.all())
        ]


@app.get("/api/v1/scores/user/{user_id}")
async def user_scores(user_id: uuid.UUID):
    async with async_session_factory() as s:
        result = await s.execute(
            select(ScoreEntry).where(ScoreEntry.user_id == user_id).order_by(ScoreEntry.created_at.desc())
        )
        return [_score_dict(e) for e in result.scalars().all()]


@app.get("/api/v1/calendar/slots")
async def calendar_slots():
    # Demo slots
    slots = []
    now = datetime.now()
    for d in range(7):
        day = now + timedelta(days=d)
        if day.weekday() < 5:
            for h in [9, 10, 11, 14, 15, 16]:
                start = day.replace(hour=h, minute=0, second=0, microsecond=0)
                end = start + timedelta(minutes=30)
                slots.append({"start": start.isoformat(), "end": end.isoformat()})
    return {"slots": slots}


def _meeting_dict(m):
    return {
        "id": str(m.id), "tenant_id": str(m.tenant_id), "title": m.title,
        "description": m.description, "scheduled_at": m.scheduled_at.isoformat() if m.scheduled_at else None,
        "duration_minutes": m.duration_minutes, "organizer_id": str(m.organizer_id),
        "status": m.status, "processing_status": m.processing_status,
        "summary": m.summary, "notion_page_id": m.notion_page_id,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }

def _decision_dict(d):
    return {
        "id": str(d.id), "tenant_id": str(d.tenant_id), "meeting_id": str(d.meeting_id),
        "content": d.content, "decided_by": str(d.decided_by),
        "assignee_id": str(d.assignee_id) if d.assignee_id else None,
        "due_date": d.due_date.isoformat() if d.due_date else None,
        "priority": d.priority, "status": d.status,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }

def _task_dict(t):
    return {
        "id": str(t.id), "tenant_id": str(t.tenant_id), "title": t.title,
        "description": t.description, "assignee_id": str(t.assignee_id),
        "meeting_id": str(t.meeting_id) if t.meeting_id else None,
        "decision_id": str(t.decision_id) if t.decision_id else None,
        "status": t.status, "priority": t.priority,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "notion_page_id": t.notion_page_id,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }

def _employee_dict(e):
    return {
        "id": str(e.id), "tenant_id": str(e.tenant_id),
        "user_id": str(e.user_id) if e.user_id else None,
        "position": e.position, "department": e.department,
        "hired_at": e.hired_at.isoformat() if e.hired_at else None,
        "is_active": e.is_active,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }

def _report_dict(r):
    return {
        "id": str(r.id), "tenant_id": str(r.tenant_id), "user_id": str(r.user_id),
        "period_start": r.period_start.isoformat(), "period_end": r.period_end.isoformat(),
        "completed_tasks": r.completed_tasks, "metrics_json": r.metrics_json,
        "requests": r.requests, "status": r.status,
        "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }

def _alert_dict(a):
    return {
        "id": str(a.id), "tenant_id": str(a.tenant_id),
        "metric_snapshot_id": str(a.metric_snapshot_id) if a.metric_snapshot_id else None,
        "alert_type": a.alert_type, "message": a.message,
        "severity": a.severity, "is_resolved": a.is_resolved,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }

def _score_dict(e):
    return {
        "id": str(e.id), "tenant_id": str(e.tenant_id), "user_id": str(e.user_id),
        "score_type": e.score_type, "points": e.points, "reason": e.reason,
        "granted_by": str(e.granted_by) if e.granted_by else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
