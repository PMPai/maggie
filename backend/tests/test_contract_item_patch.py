"""PATCH /api/contracts/contract-versions/{vid}/items/{iid} updates editable item fields; 409 for APPROVED."""
import pytest
import uuid


@pytest.mark.asyncio
async def test_patch_item_updates_quantity(client, db, auth_user):
    from app.models.project import Project
    from app.models.contract import (
        Contract, ContractVersion, ContractVersionStatus, ContractItem,
        TaxMode, ContractVersionType, CalculationMethod,
    )
    user_id = uuid.UUID(auth_user["id"])
    proj = Project(internal_project_code="25-PI",
                   project_name="PI", currency="TWD", default_tax_rate="0.05",
                   created_by=user_id, updated_by=user_id)
    db.add(proj); await db.flush()
    contract = Contract(project_id=proj.id,
                        external_contract_no="PI-1", contract_name="PI",
                        currency="TWD", tax_mode=TaxMode.EXCLUSIVE, tax_rate="0.05",
                        original_amount_ex_tax="1000", original_tax_amount="50", original_amount_inc_tax="1050",
                        created_by=user_id, updated_by=user_id)
    db.add(contract); await db.flush()
    cv = ContractVersion(contract_id=contract.id, version_no=1,
                         version_type=ContractVersionType.QUOTATION, amount_ex_tax="1000", tax_amount="50", amount_inc_tax="1050",
                         status=ContractVersionStatus.DRAFT,
                         created_by=user_id, updated_by=user_id)
    db.add(cv); await db.flush()
    item = ContractItem(contract_version_id=cv.id,
                       line_no="1", source_description="Item 1", unit="M",
                       contract_quantity="10", unit_price="100", line_amount="1000",
                       calculation_method=CalculationMethod.QUANTITY,
                       created_by=user_id, updated_by=user_id)
    db.add(item); await db.commit()

    r = await client.patch(f"/api/contracts/contract-versions/{cv.id}/items/{item.id}",
                           json={"contract_quantity": "25", "line_amount": "2500"})
    assert r.status_code == 200
    body = r.json()
    assert body["contract_quantity"] == "25.0000"
    assert body["line_amount"] == "2500.00"


@pytest.mark.asyncio
async def test_patch_item_approved_version_returns_409(client, db, auth_user):
    from app.models.project import Project
    from app.models.contract import (
        Contract, ContractVersion, ContractVersionStatus, ContractItem,
        TaxMode, ContractVersionType, CalculationMethod,
    )
    user_id = uuid.UUID(auth_user["id"])
    proj = Project(internal_project_code="25-PI2",
                   project_name="PI2", currency="TWD", default_tax_rate="0.05",
                   created_by=user_id, updated_by=user_id)
    db.add(proj); await db.flush()
    contract = Contract(project_id=proj.id,
                        external_contract_no="PI-2", contract_name="PI2",
                        currency="TWD", tax_mode=TaxMode.EXCLUSIVE, tax_rate="0.05",
                        original_amount_ex_tax="1000", original_tax_amount="50", original_amount_inc_tax="1050",
                        created_by=user_id, updated_by=user_id)
    db.add(contract); await db.flush()
    cv = ContractVersion(contract_id=contract.id, version_no=1,
                         version_type=ContractVersionType.SIGNED_CONTRACT,
                         amount_ex_tax="1000", tax_amount="50", amount_inc_tax="1050",
                         status=ContractVersionStatus.APPROVED,
                         created_by=user_id, updated_by=user_id)
    db.add(cv); await db.flush()
    item = ContractItem(contract_version_id=cv.id,
                       line_no="1", source_description="Item 1", unit="M",
                       contract_quantity="10", unit_price="100", line_amount="1000",
                       calculation_method=CalculationMethod.QUANTITY,
                       created_by=user_id, updated_by=user_id)
    db.add(item); await db.commit()

    r = await client.patch(f"/api/contracts/contract-versions/{cv.id}/items/{item.id}",
                           json={"contract_quantity": "25"})
    assert r.status_code == 409
