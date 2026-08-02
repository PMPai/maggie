"""GET /api/projects/{project_id}/master-budget returns tree rows with margin + exception_status."""
import pytest
import uuid
from datetime import date
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


@pytest.mark.asyncio
async def test_master_budget_margin_and_overclaim(client, db, auth_user):
    """Mapped + posted path: standard_cost/margin computed; second row overclaims."""
    from app.models.project import Project
    from app.models.contract import (
        Contract, ContractVersion, ContractVersionStatus, ContractVersionType,
        ContractItem, CalculationMethod, TaxMode,
    )
    from app.models.billing import (
        PaymentApplication, PaymentApplicationLine, ApplicationStatus,
    )
    from app.models.mapping import ItemMapping, MappingStatus, MappingType, MatchMethod, UnitCompatibility
    from app.models.standard import StandardItem, StandardCostVersion

    org_id = uuid.UUID(auth_user["org_id"])
    user_id = uuid.UUID(auth_user["id"])

    proj = Project(organization_id=org_id, internal_project_code="25-MB2",
                   project_name="MB Margin Test", currency="TWD", default_tax_rate="0.05",
                   created_by=user_id, updated_by=user_id)
    db.add(proj); await db.flush()
    contract = Contract(organization_id=org_id, project_id=proj.id,
                        external_contract_no="MB-2", contract_name="MB Margin Contract",
                        currency="TWD", tax_mode=TaxMode.EXCLUSIVE, tax_rate="0.05",
                        original_amount_ex_tax="20000", original_tax_amount="1000", original_amount_inc_tax="21000",
                        created_by=user_id, updated_by=user_id)
    db.add(contract); await db.flush()
    cv = ContractVersion(organization_id=org_id, contract_id=contract.id, version_no=1,
                        version_type=ContractVersionType.SIGNED_CONTRACT,
                        amount_ex_tax="20000", tax_amount="1000", amount_inc_tax="21000",
                        status=ContractVersionStatus.APPROVED,
                        created_by=user_id, updated_by=user_id)
    db.add(cv); await db.flush()
    contract.active_version_id = cv.id

    # Row 1: mapped item with margin computation
    item1 = ContractItem(organization_id=org_id, contract_version_id=cv.id, line_no="1",
                         source_description="Mapped work", unit="m",
                         contract_quantity=Decimal("100.0000"), unit_price=Decimal("100.00"),
                         line_amount=Decimal("10000.00"),
                         calculation_method=CalculationMethod.QUANTITY,
                         created_by=user_id, updated_by=user_id)
    db.add(item1); await db.flush()
    # Row 2: unmapped item, overclaim (cumulative > available)
    item2 = ContractItem(organization_id=org_id, contract_version_id=cv.id, line_no="2",
                         source_description="Overclaim work", unit="m",
                         contract_quantity=Decimal("10.0000"), unit_price=Decimal("100.00"),
                         line_amount=Decimal("1000.00"),
                         calculation_method=CalculationMethod.QUANTITY,
                         created_by=user_id, updated_by=user_id)
    db.add(item2); await db.flush()

    # Standard item + cost version (unit_cost = 80)
    std_item = StandardItem(organization_id=org_id, code="STD-1", name="Standard item 1",
                            unit="m", created_by=user_id, updated_by=user_id)
    db.add(std_item); await db.flush()
    scv = StandardCostVersion(organization_id=org_id, standard_item_id=std_item.id,
                              version_no=1, effective_from=date(2026, 1, 1),
                              unit_cost=Decimal("80.00"),
                              created_by=user_id, updated_by=user_id)
    db.add(scv); await db.flush()

    # APPROVED mapping for item1 -> std_item
    mapping = ItemMapping(organization_id=org_id, project_id=proj.id,
                          contract_item_id=item1.id, standard_item_id=std_item.id,
                          mapping_type=MappingType.ONE_TO_ONE, match_method=MatchMethod.MANUAL,
                          unit_compatibility=UnitCompatibility.SAME,
                          status=MappingStatus.APPROVED,
                          created_by=user_id, updated_by=user_id)
    db.add(mapping); await db.flush()

    # POSTED payment application (period 1)
    app = PaymentApplication(organization_id=org_id, project_id=proj.id,
                             contract_id=contract.id, contract_version_id=cv.id,
                             application_no="APP-MB-1", period_no=1,
                             period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
                             application_date=date(2026, 1, 31),
                             status=ApplicationStatus.POSTED,
                             created_by=user_id, updated_by=user_id)
    db.add(app); await db.flush()

    # Line 1: cumulative = 50 (mapped, margin path)
    line1 = PaymentApplicationLine(organization_id=org_id,
                                   payment_application_id=app.id, contract_item_id=item1.id,
                                   contract_version_id=cv.id,
                                   description_snapshot="Mapped work",
                                   unit_price_snapshot=Decimal("100.00"),
                                   current_approved_quantity=Decimal("50.0000"),
                                   cumulative_approved_quantity=Decimal("50.0000"),
                                   current_completed_amount=Decimal("5000.00"),
                                   calculation_method="QUANTITY",
                                   created_by=user_id, updated_by=user_id)
    db.add(line1); await db.flush()
    # Line 2: cumulative = 15 > available 10 (overclaim)
    line2 = PaymentApplicationLine(organization_id=org_id,
                                   payment_application_id=app.id, contract_item_id=item2.id,
                                   contract_version_id=cv.id,
                                   description_snapshot="Overclaim work",
                                   unit_price_snapshot=Decimal("100.00"),
                                   current_approved_quantity=Decimal("15.0000"),
                                   cumulative_approved_quantity=Decimal("15.0000"),
                                   current_completed_amount=Decimal("1500.00"),
                                   calculation_method="QUANTITY",
                                   created_by=user_id, updated_by=user_id)
    db.add(line2); await db.commit()

    r = await client.get(f"/api/projects/{proj.id}/master-budget")
    assert r.status_code == 200
    body = r.json()
    assert body["contract_id"] == str(contract.id)
    rows = body["rows"]
    assert len(rows) == 2

    row_by_line = {row["line_no"]: row for row in rows}
    row1 = row_by_line["1"]
    row2 = row_by_line["2"]

    # Margin path assertions (row 1)
    assert row1["standard_cost_per_unit"] == "80.00"
    assert Decimal(row1["standard_cost_total"]) == Decimal("4000")        # 80 * 50
    assert Decimal(row1["expected_margin"]) == Decimal("1000")            # 5000 - 4000
    assert row1["margin_pct"] is not None
    assert Decimal(row1["margin_pct"]) == Decimal("20.0")
    assert row1["exception_status"] == "none"
    assert row1["cumulative_approved_quantity"] == "50.0000"
    assert row1["remaining_quantity"] == "50.0000"                          # 100 - 50

    # Overclaim path assertions (row 2)
    assert row2["exception_status"] == "overclaim"
    assert Decimal(row2["remaining_quantity"]) < 0                         # 10 - 15 = -5
    assert row2["cumulative_approved_quantity"] == "15.0000"
