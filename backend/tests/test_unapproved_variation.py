"""Test #4: Unapproved variation is not claimable.

Only variations with status=APPROVED contribute to the available quantity
for a contract item. Unapproved variations must not allow overclaim.
"""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.contract import (
    Contract, ContractVersion, ContractVersionType, ContractVersionStatus,
    ContractItem, CalculationMethod,
)
from app.models.identity import Organization
from app.models.project import Project
from app.models.variation import (
    Variation, VariationType, VariationStatus,
)
from app.services.calc_engine import check_quantity_limit, OverclaimError
from app.services.variation_service import get_approved_variation_qty


async def _setup_base(db):
    org = Organization(code=f"org-{uuid.uuid4().hex[:8]}", name="Test Org")
    db.add(org)
    await db.flush()

    project = Project(
        organization_id=org.id,
        internal_project_code=f"P-{uuid.uuid4().hex[:8]}",
        project_name="Test Project",
    )
    db.add(project)
    await db.flush()

    contract = Contract(
        organization_id=org.id,
        project_id=project.id,
        external_contract_no=f"C-{uuid.uuid4().hex[:8]}",
        contract_name="Test Contract",
    )
    db.add(contract)
    await db.flush()

    version = ContractVersion(
        organization_id=org.id,
        contract_id=contract.id,
        version_no=1,
        version_type=ContractVersionType.SIGNED_CONTRACT,
        status=ContractVersionStatus.APPROVED,
    )
    db.add(version)
    await db.flush()
    contract.active_version_id = version.id
    await db.flush()

    item = ContractItem(
        organization_id=org.id,
        contract_version_id=version.id,
        line_no="1",
        source_description="Excavation",
        unit="M3",
        contract_quantity=Decimal("100"),
        unit_price=Decimal("1000"),
        calculation_method=CalculationMethod.QUANTITY,
    )
    db.add(item)
    await db.commit()
    return org, project, contract, version, item


@pytest.mark.asyncio
async def test_unapproved_variation_returns_zero_qty(db):
    org, project, contract, version, item = await _setup_base(db)

    variation = Variation(
        organization_id=org.id,
        project_id=project.id,
        contract_id=contract.id,
        contract_item_id=item.id,
        variation_no="V-001",
        variation_type=VariationType.QUANTITY_ADJUSTMENT,
        quantity_delta=Decimal("50"),
        status=VariationStatus.UNDER_REVIEW,
    )
    db.add(variation)
    await db.commit()

    approved_qty = await get_approved_variation_qty(item.id, db)
    assert approved_qty == Decimal("0")


@pytest.mark.asyncio
async def test_approved_variation_returns_qty(db):
    org, project, contract, version, item = await _setup_base(db)

    variation = Variation(
        organization_id=org.id,
        project_id=project.id,
        contract_id=contract.id,
        contract_item_id=item.id,
        variation_no="V-002",
        variation_type=VariationType.QUANTITY_ADJUSTMENT,
        quantity_delta=Decimal("50"),
        status=VariationStatus.APPROVED,
    )
    db.add(variation)
    await db.commit()

    approved_qty = await get_approved_variation_qty(item.id, db)
    assert approved_qty == Decimal("50")


@pytest.mark.asyncio
async def test_unapproved_variation_does_not_affect_available_qty(db):
    org, project, contract, version, item = await _setup_base(db)

    # An under-review variation that would, if approved, expand the contract qty.
    variation = Variation(
        organization_id=org.id,
        project_id=project.id,
        contract_id=contract.id,
        contract_item_id=item.id,
        variation_no="V-003",
        variation_type=VariationType.QUANTITY_ADJUSTMENT,
        quantity_delta=Decimal("50"),
        status=VariationStatus.UNDER_REVIEW,
    )
    db.add(variation)
    await db.commit()

    # Approved variation qty is 0, so the available qty is just the contract qty.
    approved_qty = await get_approved_variation_qty(item.id, db)
    assert approved_qty == Decimal("0")

    # Previous approved 80, claiming 30 -> cumulative 110 > available 100 -> blocked.
    with pytest.raises(OverclaimError) as exc:
        check_quantity_limit(
            contract_quantity=Decimal("100"),
            approved_variation_qty=approved_qty,
            previous_approved_quantity=Decimal("80"),
            current_claimed_quantity=Decimal("30"),
        )
    assert "exceeds available" in str(exc.value)


@pytest.mark.asyncio
async def test_approved_variation_allows_extra_claim(db):
    org, project, contract, version, item = await _setup_base(db)

    variation = Variation(
        organization_id=org.id,
        project_id=project.id,
        contract_id=contract.id,
        contract_item_id=item.id,
        variation_no="V-004",
        variation_type=VariationType.QUANTITY_ADJUSTMENT,
        quantity_delta=Decimal("50"),
        status=VariationStatus.APPROVED,
    )
    db.add(variation)
    await db.commit()

    approved_qty = await get_approved_variation_qty(item.id, db)
    assert approved_qty == Decimal("50")

    # Available = 100 + 50 = 150; cumulative 80 + 30 = 110 <= 150 -> allowed.
    check_quantity_limit(
        contract_quantity=Decimal("100"),
        approved_variation_qty=approved_qty,
        previous_approved_quantity=Decimal("80"),
        current_claimed_quantity=Decimal("30"),
    )
