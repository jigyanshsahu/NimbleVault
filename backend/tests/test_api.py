"""
Integration tests for FastAPI endpoints.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import get_db


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Verify GET /health returns 200 with service info."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "NimbleVault" in data["service"]


@pytest.mark.asyncio
async def test_list_jobs_endpoint():
    """Verify GET /api/jobs returns a list."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/jobs")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_update_title_validation_error():
    """Verify PATCH /api/jobs/{id}/title rejects invalid/empty payload."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            "/api/jobs/non-existent-id/title",
            json={"title": "  "},
        )
        # Should fail validation before hitting database
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_sync_endpoint():
    """Verify POST /api/sync audits database against YouTube and returns summary."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/sync")
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "reconciled_count" in data
            assert "reconciled_files" in data
            assert data["reconciled_count"] == 0
            assert data["reconciled_files"] == []
    finally:
        app.dependency_overrides.pop(get_db, None)
