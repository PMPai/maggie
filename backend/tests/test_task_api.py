"""Task status API tests."""
import pytest


@pytest.mark.asyncio
async def test_task_status_unknown_returns_pending(client):
    resp = await client.get("/api/tasks/nonexistent-task-id/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "PENDING"
