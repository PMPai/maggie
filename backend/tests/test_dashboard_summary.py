"""GET /api/dashboard/summary returns 11 indicators + per_project + recent_audit."""
import pytest


@pytest.mark.asyncio
async def test_dashboard_summary_unauthenticated(client, db):
    r = await client.get("/api/dashboard/summary")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_summary_shape_for_empty_user(client, db, auth_user):
    """Authenticated user with no projects gets zero-valued indicators."""
    r = await client.get("/api/dashboard/summary")
    assert r.status_code == 200
    body = r.json()
    expected_keys = {
        "total_contract_amount", "gross_completed_total", "approved_total",
        "invoiced_total", "collected_total", "retention_held_total",
        "invoice_outstanding_total", "pending_variations", "pending_applications",
        "pending_mappings", "overclaim_exceptions", "contract_version_diffs",
        "per_project", "recent_audit",
    }
    assert set(body.keys()) == expected_keys
    assert body["total_contract_amount"] == "0"
    assert body["pending_variations"] == 0
    assert body["per_project"] == []
