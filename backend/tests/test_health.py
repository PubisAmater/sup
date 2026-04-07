import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root(async_client: AsyncClient):
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "SUP API"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_dashboard_stats_requires_auth(async_client: AsyncClient):
    response = await async_client.get("/api/v1/dashboard/stats")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_meetings_list_requires_auth(async_client: AsyncClient):
    response = await async_client.get("/api/v1/meetings/")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_tasks_list_requires_auth(async_client: AsyncClient):
    response = await async_client.get("/api/v1/tasks/")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_employees_list_requires_auth(async_client: AsyncClient):
    response = await async_client.get("/api/v1/employees/")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_reports_list_requires_auth(async_client: AsyncClient):
    response = await async_client.get("/api/v1/reports/")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_scores_leaderboard_requires_auth(async_client: AsyncClient):
    response = await async_client.get("/api/v1/scores/leaderboard")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_metrics_requires_auth(async_client: AsyncClient):
    response = await async_client.get("/api/v1/metrics/")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_calendar_requires_auth(async_client: AsyncClient):
    response = await async_client.get("/api/v1/calendar/slots")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_auth_me_requires_auth(async_client: AsyncClient):
    response = await async_client.get("/auth/me")
    assert response.status_code in (401, 403)
