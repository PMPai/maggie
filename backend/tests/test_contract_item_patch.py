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
    org_id = uuid.UUID(auth_user["org_id"])
    user_id = uuid.UUID(auth_user["id"])
    proj = Project(organization_id=org_id, internal_project_code="25-PI",
                   project_name="PI", currency="TWD", default_tax_rate="0.05",
                   created_by=user_id, updated_by=user_id)
    db.add(proj); await db.flush()
    contract = Contract(organization_id=org_id, project_id=proj.id,
                        external_contract_no="PI-1", contract_name="PI",
                        currency="TWD", tax_mode=TaxMode.EXCLUSIVE, tax_rate="0.05",
                        original_amount_ex_tax="1000", original_tax_amount="50", original_amount_inc_tax="1050",
                        created_by=user_id, updated_by=user_id)
    db.add(contract); await db.flush()
    cv = ContractVersion(organization_id=org_id, contract_id=contract.id, version_no=1,
                         version_type=ContractVersionType.QUOTATION, amount_ex_tax="1000", tax_amount="50", amount_inc_tax="1050",
                         status=ContractVersionStatus.DRAFT,
                         created_by=user_id, updated_by=user_id)
    db.add(cv); await db.flush()
    item = ContractItem(organization_id=org_id, contract_version_id=cv.id,
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
    org_id = uuid.UUID(auth_user["org_id"])
    user_id = uuid.UUID(auth_user["id"])
    proj = Project(organization_id=org_id, internal_project_code="25-PI2",
                   project_name="PI2", currency="TWD", default_tax_rate="0.05",
                   created_by=user_id, updated_by=user_id)
    db.add(proj); await db.flush()
    contract = Contract(organization_id=org_id, project_id=proj.id,
                        external_contract_no="PI-2", contract_name="PI2",
                        currency="TWD", tax_mode=TaxMode.EXCLUSIVE, tax_rate="0.05",
                        original_amount_ex_tax="1000", original_tax_amount="50", original_amount_inc_tax="1050",
                        created_by=user_id, updated_by=user_id)
    db.add(contract); await db.flush()
    cv = ContractVersion(organization_id=org_id, contract_id=contract.id, version_no=1,
                         version_type=ContractVersionType.SIGNED_CONTRACT,
                         amount_ex_tax="1000", tax_amount="50", amount_inc_tax="1050",
                         status=ContractVersionStatus.APPROVED,
                         created_by=user_id, updated_by=user_id)
    db.add(cv); await db.flush()
    item = ContractItem(organization_id=org_id, contract_version_id=cv.id,
                       line_no="1", source_description="Item 1", unit="M",
                       contract_quantity="10", unit_price="100", line_amount="1000",
                       calculation_method=CalculationMethod.QUANTITY,
                       created_by=user_id, updated_by=user_id)
    db.add(item); await db.commit()

    r = await client.patch(f"/api/contracts/contract-versions/{cv.id}/items/{item.id}",
                           json={"contract_quantity": "25"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_patch_item_rejects_non_member(client, db, auth_user):
    """A CONTRACT_ADMIN who is not a project member must be rejected (403)."""
    from app.models.project import Project
    from app.models.contract import (
        Contract, ContractVersion, ContractVersionStatus, ContractItem,
        TaxMode, ContractVersionType, CalculationMethod,
    )
    from app.models.identity import User, Role, UserRole, UserRoleEnum
    from app.auth.tokens import create_access_token
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    org_id = uuid.UUID(auth_user["org_id"])
    user_id = uuid.UUID(auth_user["id"])
    proj = Project(organization_id=org_id, internal_project_code="25-PINM",
                   project_name="PINM", currency="TWD", default_tax_rate="0.05",
                   created_by=user_id, updated_by=user_id)
    db.add(proj); await db.flush()
    contract = Contract(organization_id=org_id, project_id=proj.id,
                        external_contract_no="PINM-1", contract_name="PINM",
                        currency="TWD", tax_mode=TaxMode.EXCLUSIVE, tax_rate="0.05",
                        original_amount_ex_tax="1000", original_tax_amount="50", original_amount_inc_tax="1050",
                        created_by=user_id, updated_by=user_id)
    db.add(contract); await db.flush()
    cv = ContractVersion(organization_id=org_id, contract_id=contract.id, version_no=1,
                         version_type=ContractVersionType.QUOTATION, amount_ex_tax="1000", tax_amount="50", amount_inc_tax="1050",
                         status=ContractVersionStatus.DRAFT,
                         created_by=user_id, updated_by=user_id)
    db.add(cv); await db.flush()
    item = ContractItem(organization_id=org_id, contract_version_id=cv.id,
                        line_no="1", source_description="Item 1", unit="M",
                        contract_quantity="10", unit_price="100", line_amount="1000",
                        calculation_method=CalculationMethod.QUANTITY,
                        created_by=user_id, updated_by=user_id)
    db.add(item); await db.commit()

    # Second user: CONTRACT_ADMIN but NOT a ProjectMember of proj.
    other = User(id=uuid.uuid4(), organization_id=org_id, email="nonmember-item@example.com",
                 display_name="Non Member", password_hash="x", status="ACTIVE")
    db.add(other); await db.flush()
    role = Role(id=uuid.uuid4(), name=UserRoleEnum.CONTRACT_ADMIN)
    db.add(role); await db.flush()
    db.add(UserRole(user_id=other.id, role_id=role.id, organization_id=org_id))
    await db.commit()

    token = create_access_token(other.id, org_id, [UserRoleEnum.CONTRACT_ADMIN])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as other_client:
        other_client.cookies.set("access_token", token)
        r = await other_client.patch(f"/api/contracts/contract-versions/{cv.id}/items/{item.id}",
                                     json={"contract_quantity": "25"})
    assert r.status_code == 403
    assert "member" in r.json()["detail"].lower()
