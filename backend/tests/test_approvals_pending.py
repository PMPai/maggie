"""GET /api/approvals/pending aggregates pending items across resource types."""
import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.models.billing import ApplicationStatus, PaymentApplication, PaymentApplicationLine
from app.models.contract import (
    CalculationMethod,
    Contract,
    ContractItem,
    ContractVersion,
    ContractVersionStatus,
    ContractVersionType,
    TaxMode,
)
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


@pytest.mark.asyncio
async def test_pending_approvals_overclaim_scenario(client, db, auth_user):
    """Overclaim (cumulative_approved_quantity > contract_quantity) surfaces as a pending item."""
    org_id = uuid.UUID(auth_user["org_id"])
    user_id = uuid.UUID(auth_user["id"])
    proj = Project(organization_id=org_id, internal_project_code="25-OC",
                   project_name="Overclaim Test", currency="TWD", default_tax_rate="0.05",
                   created_by=user_id, updated_by=user_id)
    db.add(proj); await db.flush()
    contract = Contract(organization_id=org_id, project_id=proj.id,
                        external_contract_no="T-OC", contract_name="OC Contract",
                        currency="TWD", tax_mode=TaxMode.EXCLUSIVE, tax_rate="0.05",
                        original_amount_ex_tax="1000", original_tax_amount="50", original_amount_inc_tax="1050",
                        created_by=user_id, updated_by=user_id)
    db.add(contract); await db.flush()
    version = ContractVersion(organization_id=org_id, contract_id=contract.id,
                               version_no=1, version_type=ContractVersionType.SIGNED_CONTRACT,
                               status=ContractVersionStatus.APPROVED,
                               amount_ex_tax="1000", tax_amount="50", amount_inc_tax="1050",
                               created_by=user_id, updated_by=user_id)
    db.add(version); await db.flush()
    contract.active_version_id = version.id
    await db.flush()
    item = ContractItem(organization_id=org_id, contract_version_id=version.id,
                        line_no="1", source_description="Excavation work",
                        unit="M3", contract_quantity=Decimal("10"),
                        unit_price=Decimal("100"), calculation_method=CalculationMethod.QUANTITY,
                        created_by=user_id, updated_by=user_id)
    db.add(item); await db.flush()
    app = PaymentApplication(organization_id=org_id, project_id=proj.id,
                             contract_id=contract.id, contract_version_id=version.id,
                             application_no="APP-OC-1", period_no=1,
                             period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
                             application_date=date(2026, 1, 31),
                             status=ApplicationStatus.DRAFT,
                             created_by=user_id, updated_by=user_id)
    db.add(app); await db.flush()
    line = PaymentApplicationLine(organization_id=org_id,
                                   payment_application_id=app.id, contract_item_id=item.id,
                                   contract_version_id=version.id,
                                   description_snapshot="Excavation work",
                                   unit_price_snapshot=Decimal("100"),
                                   cumulative_approved_quantity=Decimal("15"),
                                   current_approved_quantity=Decimal("15"),
                                   calculation_method="QUANTITY",
                                   created_by=user_id, updated_by=user_id)
    db.add(line); await db.commit()

    r = await client.get("/api/approvals/pending")
    assert r.status_code == 200
    items = r.json()["items"]
    overclaim = [i for i in items if i["resource_type"] == "overclaim"]
    assert len(overclaim) >= 1
    oc = overclaim[0]
    assert oc["project_code"] == "25-OC"
    assert oc["approve_url"] is None
    assert oc["detail_url"].endswith("/budget")