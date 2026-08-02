"""GET /api/approvals/pending aggregates pending items across resource types."""
import uuid
from datetime import datetime

import pytest

from app.models.contract import Contract, TaxMode
from app.models.project import Project
from app.models.variation import Variation, VariationStatus, VariationType


@pytest.mark.asyncio
async def test_pending_approvals_unauthenticated(client):
    r = await client.get("/api/approvals/pending")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_pending_approvals_empty(client, db, auth_user):
    r = await client.get("/api/approvals/pending")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert body["items"] == []


@pytest.mark.asyncio
async def test_pending_approvals_returns_uniform_shape(client, db, auth_user):
    """Each item has the uniform keys required by the frontend table."""
    org_id = uuid.UUID(auth_user["org_id"])
    user_id = uuid.UUID(auth_user["id"])
    proj = Project(organization_id=org_id, internal_project_code="25-999",
                   project_name="Test", currency="TWD", default_tax_rate="0.05",
                   created_by=user_id, updated_by=user_id)
    db.add(proj); await db.flush()
    contract = Contract(organization_id=org_id, project_id=proj.id,
                        external_contract_no="T-1", contract_name="Test Contract",
                        currency="TWD", tax_mode=TaxMode.EXCLUSIVE, tax_rate="0.05",
                        original_amount_ex_tax="1000", original_tax_amount="50", original_amount_inc_tax="1050",
                        created_by=user_id, updated_by=user_id)
    db.add(contract); await db.flush()
    var = Variation(organization_id=org_id, project_id=proj.id, contract_id=contract.id,
                    variation_no="V-1", variation_type=VariationType.SCOPE_CHANGE, description="extra work",
                    amount_ex_tax="100", tax_amount="5", amount_inc_tax="105",
                    quantity_delta="0", status=VariationStatus.UNDER_REVIEW, effective_date=datetime.utcnow().date(),
                    created_by=user_id, updated_by=user_id)
    db.add(var); await db.commit()

    r = await client.get("/api/approvals/pending")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    item = items[0]
    required_keys = {"resource_type", "resource_id", "description", "project_id",
                     "project_code", "amount", "waiting_for_role", "created_at",
                     "approve_url", "reject_url", "detail_url"}
    assert set(item.keys()) >= required_keys
    assert item["resource_type"] == "variation"
    assert item["project_code"] == "25-999"