import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_transcript_no_auth(async_client: AsyncClient):
    """Uploading transcript without auth should fail."""
    response = await async_client.post(
        "/api/v1/meetings/00000000-0000-0000-0000-000000000001/transcript",
        json={"transcript": "test"},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_analysis_no_auth(async_client: AsyncClient):
    """Getting analysis without auth should fail."""
    response = await async_client.get(
        "/api/v1/meetings/00000000-0000-0000-0000-000000000001/analysis",
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_dashboard_stats_no_auth(async_client: AsyncClient):
    """Dashboard stats without auth should fail."""
    response = await async_client.get("/api/v1/dashboard/stats")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_overdue_tasks_no_auth(async_client: AsyncClient):
    """Overdue tasks without auth should fail."""
    response = await async_client.get("/api/v1/tasks/overdue")
    assert response.status_code in (401, 403)
