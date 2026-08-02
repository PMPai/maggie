"""PATCH /api/contracts/contract-versions/{vid} updates DRAFT/UNDER_REVIEW fields; 409 for APPROVED."""
import pytest
import uuid


@pytest.mark.asyncio
async def test_patch_draft_version_updates_fields(client, db, auth_user):
    from app.models.project import Project
    from app.models.contract import Contract, ContractVersion, ContractVersionStatus, TaxMode, ContractVersionType
    org_id = uuid.UUID(auth_user["org_id"])
    user_id = uuid.UUID(auth_user["id"])
    proj = Project(organization_id=org_id, internal_project_code="25-P",
                   project_name="P", currency="TWD", default_tax_rate="0.05",
                   created_by=user_id, updated_by=user_id)
    db.add(proj); await db.flush()
    contract = Contract(organization_id=org_id, project_id=proj.id,
                        external_contract_no="P-1", contract_name="P",
                        currency="TWD", tax_mode=TaxMode.EXCLUSIVE, tax_rate="0.05",
                        original_amount_ex_tax="1000", original_tax_amount="50", original_amount_inc_tax="1050",
                        created_by=user_id, updated_by=user_id)
    db.add(contract); await db.flush()
    cv = ContractVersion(organization_id=org_id, contract_id=contract.id, version_no=1,
                         version_type=ContractVersionType.QUOTATION, amount_ex_tax="1000", tax_amount="50", amount_inc_tax="1050",
                         status=ContractVersionStatus.DRAFT,
                         created_by=user_id, updated_by=user_id)
    db.add(cv); await db.commit()

    r = await client.patch(f"/api/contracts/contract-versions/{cv.id}", json={
        "contract_name": "Updated Name", "amount_ex_tax": "2000", "tax_amount": "100", "amount_inc_tax": "2100",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["amount_inc_tax"] == "2100.00"


@pytest.mark.asyncio
async def test_patch_approved_version_returns_409(client, db, auth_user):
    from app.models.project import Project
    from app.models.contract import Contract, ContractVersion, ContractVersionStatus, TaxMode, ContractVersionType
    org_id = uuid.UUID(auth_user["org_id"])
    user_id = uuid.UUID(auth_user["id"])
    proj = Project(organization_id=org_id, internal_project_code="25-P2",
                   project_name="P2", currency="TWD", default_tax_rate="0.05",
                   created_by=user_id, updated_by=user_id)
    db.add(proj); await db.flush()
    contract = Contract(organization_id=org_id, project_id=proj.id,
                        external_contract_no="P-2", contract_name="P2",
                        currency="TWD", tax_mode=TaxMode.EXCLUSIVE, tax_rate="0.05",
                        original_amount_ex_tax="1000", original_tax_amount="50", original_amount_inc_tax="1050",
                        created_by=user_id, updated_by=user_id)
    db.add(contract); await db.flush()
    cv = ContractVersion(organization_id=org_id, contract_id=contract.id, version_no=1,
                         version_type=ContractVersionType.SIGNED_CONTRACT, amount_ex_tax="1000", tax_amount="50", amount_inc_tax="1050",
                         status=ContractVersionStatus.APPROVED,
                         created_by=user_id, updated_by=user_id)
    db.add(cv); await db.commit()

    r = await client.patch(f"/api/contracts/contract-versions/{cv.id}", json={"amount_inc_tax": "9999"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_patch_version_422_on_amount_mismatch(client, db, auth_user):
    from app.models.project import Project
    from app.models.contract import Contract, ContractVersion, ContractVersionStatus, TaxMode, ContractVersionType
    org_id = uuid.UUID(auth_user["org_id"])
    user_id = uuid.UUID(auth_user["id"])
    proj = Project(organization_id=org_id, internal_project_code="25-P3",
                   project_name="P3", currency="TWD", default_tax_rate="0.05",
                   created_by=user_id, updated_by=user_id)
    db.add(proj); await db.flush()
    contract = Contract(organization_id=org_id, project_id=proj.id,
                        external_contract_no="P-3", contract_name="P3",
                        currency="TWD", tax_mode=TaxMode.EXCLUSIVE, tax_rate="0.05",
                        original_amount_ex_tax="1000", original_tax_amount="50", original_amount_inc_tax="1050",
                        created_by=user_id, updated_by=user_id)
    db.add(contract); await db.flush()
    cv = ContractVersion(organization_id=org_id, contract_id=contract.id, version_no=1,
                         version_type=ContractVersionType.QUOTATION, amount_ex_tax="1000", tax_amount="50", amount_inc_tax="1050",
                         status=ContractVersionStatus.DRAFT,
                         created_by=user_id, updated_by=user_id)
    db.add(cv); await db.commit()

    r = await client.patch(f"/api/contracts/contract-versions/{cv.id}", json={"amount_ex_tax": "2000"})
    assert r.status_code == 422
    assert "amount" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_patch_version_submit_to_under_review(client, db, auth_user):
    from app.models.project import Project
    from app.models.contract import Contract, ContractVersion, ContractVersionStatus, TaxMode, ContractVersionType
    org_id = uuid.UUID(auth_user["org_id"])
    user_id = uuid.UUID(auth_user["id"])
    proj = Project(organization_id=org_id, internal_project_code="25-P4",
                   project_name="P4", currency="TWD", default_tax_rate="0.05",
                   created_by=user_id, updated_by=user_id)
    db.add(proj); await db.flush()
    contract = Contract(organization_id=org_id, project_id=proj.id,
                        external_contract_no="P-4", contract_name="P4",
                        currency="TWD", tax_mode=TaxMode.EXCLUSIVE, tax_rate="0.05",
                        original_amount_ex_tax="1000", original_tax_amount="50", original_amount_inc_tax="1050",
                        created_by=user_id, updated_by=user_id)
    db.add(contract); await db.flush()
    cv = ContractVersion(organization_id=org_id, contract_id=contract.id, version_no=1,
                         version_type=ContractVersionType.QUOTATION, amount_ex_tax="1000", tax_amount="50", amount_inc_tax="1050",
                         status=ContractVersionStatus.DRAFT,
                         created_by=user_id, updated_by=user_id)
    db.add(cv); await db.commit()

    r = await client.patch(f"/api/contracts/contract-versions/{cv.id}", json={"status": "UNDER_REVIEW"})
    assert r.status_code == 200
    assert r.json()["status"] == "UNDER_REVIEW"


@pytest.mark.asyncio
async def test_patch_version_submit_approved_rejected(client, db, auth_user):
    from app.models.project import Project
    from app.models.contract import Contract, ContractVersion, ContractVersionStatus, TaxMode, ContractVersionType
    org_id = uuid.UUID(auth_user["org_id"])
    user_id = uuid.UUID(auth_user["id"])
    proj = Project(organization_id=org_id, internal_project_code="25-P5",
                   project_name="P5", currency="TWD", default_tax_rate="0.05",
                   created_by=user_id, updated_by=user_id)
    db.add(proj); await db.flush()
    contract = Contract(organization_id=org_id, project_id=proj.id,
                        external_contract_no="P-5", contract_name="P5",
                        currency="TWD", tax_mode=TaxMode.EXCLUSIVE, tax_rate="0.05",
                        original_amount_ex_tax="1000", original_tax_amount="50", original_amount_inc_tax="1050",
                        created_by=user_id, updated_by=user_id)
    db.add(contract); await db.flush()
    cv = ContractVersion(organization_id=org_id, contract_id=contract.id, version_no=1,
                         version_type=ContractVersionType.SIGNED_CONTRACT, amount_ex_tax="1000", tax_amount="50", amount_inc_tax="1050",
                         status=ContractVersionStatus.APPROVED,
                         created_by=user_id, updated_by=user_id)
    db.add(cv); await db.commit()

    # APPROVED -> UNDER_REVIEW blocked by the general status guard (409)
    r = await client.patch(f"/api/contracts/contract-versions/{cv.id}", json={"status": "UNDER_REVIEW"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_patch_version_status_to_approved_rejected(client, db, auth_user):
    from app.models.project import Project
    from app.models.contract import Contract, ContractVersion, ContractVersionStatus, TaxMode, ContractVersionType
    org_id = uuid.UUID(auth_user["org_id"])
    user_id = uuid.UUID(auth_user["id"])
    proj = Project(organization_id=org_id, internal_project_code="25-P6",
                   project_name="P6", currency="TWD", default_tax_rate="0.05",
                   created_by=user_id, updated_by=user_id)
    db.add(proj); await db.flush()
    contract = Contract(organization_id=org_id, project_id=proj.id,
                        external_contract_no="P-6", contract_name="P6",
                        currency="TWD", tax_mode=TaxMode.EXCLUSIVE, tax_rate="0.05",
                        original_amount_ex_tax="1000", original_tax_amount="50", original_amount_inc_tax="1050",
                        created_by=user_id, updated_by=user_id)
    db.add(contract); await db.flush()
    cv = ContractVersion(organization_id=org_id, contract_id=contract.id, version_no=1,
                         version_type=ContractVersionType.QUOTATION, amount_ex_tax="1000", tax_amount="50", amount_inc_tax="1050",
                         status=ContractVersionStatus.DRAFT,
                         created_by=user_id, updated_by=user_id)
    db.add(cv); await db.commit()

    # DRAFT -> APPROVED not allowed via PATCH (use approve endpoint)
    r = await client.patch(f"/api/contracts/contract-versions/{cv.id}", json={"status": "APPROVED"})
    assert r.status_code == 422
