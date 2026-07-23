"""Task status API tests."""
import pytest
from sqlalchemy import select
from app.auth.tokens import create_access_token
from app.models.identity import Organization, User


@pytest.mark.asyncio
async def test_task_status_requires_auth(client):
    resp = await client.get("/api/tasks/fake-id/status")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_task_status_unknown_returns_pending(client, db):
    org = Organization(code="task-org", name="Task Org")
    db.add(org)
    await db.flush()
    user = User(
        organization_id=org.id,
        email="taskuser@example.com",
        display_name="Task User",
        status="ACTIVE",
    )
    db.add(user)
    await db.commit()

    token = create_access_token(user.id, org.id, [])
    resp = await client.get(
        "/api/tasks/nonexistent-task-id/status",
        cookies={"access_token": token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "PENDING"
