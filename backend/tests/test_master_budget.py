"""GET /api/projects/{project_id}/master-budget returns tree rows with margin + exception_status."""
import pytest
import uuid
from decimal import Decimal


@pytest.mark.asyncio
async def test_master_budget_unauthenticated(client, db):
    r = await client.get(f"/api/projects/{uuid.uuid4()}/master-budget")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_master_budget_returns_tree_shape(client, db, auth_user):
    from app.models.project import Project
    from app.models.contract import (
        Contract, ContractVersion, ContractVersionStatus, ContractVersionType,
        ContractItem, CalculationMethod, TaxMode,
    )
    org_id = uuid.UUID(auth_user["org_id"])
    user_id = uuid.UUID(auth_user["id"])
    proj = Project(organization_id=org_id, internal_project_code="25-MB",
                   project_name="MB Test", currency="TWD", default_tax_rate="0.05",
                   created_by=user_id, updated_by=user_id)
    db.add(proj); await db.flush()
    contract = Contract(organization_id=org_id, project_id=proj.id,
                        external_contract_no="MB-1", contract_name="MB Contract",
                        currency="TWD", tax_mode=TaxMode.EXCLUSIVE, tax_rate="0.05",
                        original_amount_ex_tax="10000", original_tax_amount="500", original_amount_inc_tax="10500",
                        created_by=user_id, updated_by=user_id)
    db.add(contract); await db.flush()
    cv = ContractVersion(organization_id=org_id, contract_id=contract.id, version_no=1,
                        version_type=ContractVersionType.SIGNED_CONTRACT,
                        amount_ex_tax="10000", tax_amount="500", amount_inc_tax="10500",
                        status=ContractVersionStatus.APPROVED,
                        created_by=user_id, updated_by=user_id)
    db.add(cv); await db.flush()
    contract.active_version_id = cv.id
    item = ContractItem(organization_id=org_id, contract_version_id=cv.id, line_no="1",
                        source_description="Test item", unit="m", contract_quantity=Decimal("100.0000"),
                        unit_price=Decimal("100.00"), line_amount=Decimal("10000.00"),
                        calculation_method=CalculationMethod.QUANTITY,
                        created_by=user_id, updated_by=user_id)
    db.add(item); await db.commit()

    r = await client.get(f"/api/projects/{proj.id}/master-budget")
    assert r.status_code == 200
    body = r.json()
    assert body["contract_id"] == str(contract.id)
    assert body["contract_version_id"] == str(cv.id)
    assert len(body["rows"]) == 1
    row = body["rows"][0]
    assert row["contract_quantity"] == "100.0000"
    assert row["unit_price"] == "100.00"
    assert row["remaining_quantity"] == "100.0000"
    assert row["exception_status"] == "unmapped"  # no mapping -> unmapped
