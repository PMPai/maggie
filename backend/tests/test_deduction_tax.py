"""Test #9: Deduction tax handling.

`calc_deduction_tax` applies tax only to TAXABLE / TAX_ADJUSTMENT deductions;
NON_TAXABLE deductions have a zero tax amount. `get_total_deduction_amount`
sums the (approved) deduction principal amounts for a payment application.
"""
import uuid
from decimal import Decimal

import pytest

from app.models.contract import (
    Contract, ContractVersion, ContractVersionType, ContractVersionStatus,
)
from app.models.project import Project
from app.models.billing import PaymentApplication, ApplicationStatus
from app.models.deduction import (
    Deduction, DeductionType, TaxTreatment, DeductionStatus,
)
from app.services.deduction_service import calc_deduction_tax, get_total_deduction_amount


async def _setup_application(db):
    project = Project(
        internal_project_code=f"P-{uuid.uuid4().hex[:8]}",
        project_name="Test Project",
    )
    db.add(project)
    await db.flush()

    contract = Contract(
        project_id=project.id,
        external_contract_no=f"C-{uuid.uuid4().hex[:8]}",
        contract_name="Test Contract",
    )
    db.add(contract)
    await db.flush()

    version = ContractVersion(
        contract_id=contract.id,
        version_no=1,
        version_type=ContractVersionType.SIGNED_CONTRACT,
        status=ContractVersionStatus.APPROVED,
    )
    db.add(version)
    await db.flush()
    contract.active_version_id = version.id
    await db.flush()

    application = PaymentApplication(
        project_id=project.id,
        contract_id=contract.id,
        contract_version_id=version.id,
        application_no=f"A-{uuid.uuid4().hex[:8]}",
        period_no=1,
        period_start=__import__("datetime").date(2024, 1, 1),
        period_end=__import__("datetime").date(2024, 1, 31),
        application_date=__import__("datetime").date(2024, 1, 31),
        status=ApplicationStatus.DRAFT,
    )
    db.add(application)
    await db.commit()
    return project, contract, version, application


class TestCalcDeductionTax:
    def test_taxable_deduction_applies_tax(self):
        amount = Decimal("1000.00")
        tax = calc_deduction_tax(amount, TaxTreatment.TAXABLE, Decimal("0.05"))
        assert tax == Decimal("50.00")

    def test_non_taxable_deduction_has_zero_tax(self):
        amount = Decimal("1000.00")
        tax = calc_deduction_tax(amount, TaxTreatment.NON_TAXABLE, Decimal("0.05"))
        assert tax == Decimal("0")

    def test_tax_adjustment_applies_tax(self):
        amount = Decimal("1000.00")
        tax = calc_deduction_tax(amount, TaxTreatment.TAX_ADJUSTMENT, Decimal("0.05"))
        assert tax == Decimal("50.00")

    def test_zero_amount_yields_zero_tax(self):
        tax = calc_deduction_tax(Decimal("0"), TaxTreatment.TAXABLE, Decimal("0.05"))
        assert tax == Decimal("0.00")

    def test_tax_is_quantized_to_two_decimals(self):
        tax = calc_deduction_tax(Decimal("333.33"), TaxTreatment.TAXABLE, Decimal("0.05"))
        # 333.33 * 0.05 = 16.6665 -> 16.67 (ROUND_HALF_UP via quantize)
        assert tax == Decimal("16.67")


@pytest.mark.asyncio
async def test_get_total_deduction_amount_sums_approved(db):
    project, contract, version, application = await _setup_application(db)

    d1 = Deduction(
        project_id=project.id,
        contract_id=contract.id,
        payment_application_id=application.id,
        deduction_no="D-001",
        deduction_type=DeductionType.MATERIAL_DEDUCTION,
        amount=Decimal("1000.00"),
        tax_treatment=TaxTreatment.TAXABLE,
        status=DeductionStatus.APPROVED,
    )
    d2 = Deduction(
        project_id=project.id,
        contract_id=contract.id,
        payment_application_id=application.id,
        deduction_no="D-002",
        deduction_type=DeductionType.EQUIPMENT_DEDUCTION,
        amount=Decimal("500.00"),
        tax_treatment=TaxTreatment.NON_TAXABLE,
        status=DeductionStatus.APPROVED,
    )
    db.add(d1)
    db.add(d2)
    await db.commit()

    total = await get_total_deduction_amount(application.id, db)
    assert total == Decimal("1500.00")


@pytest.mark.asyncio
async def test_get_total_deduction_amount_ignores_non_approved(db):
    project, contract, version, application = await _setup_application(db)

    approved = Deduction(
        project_id=project.id,
        contract_id=contract.id,
        payment_application_id=application.id,
        deduction_no="D-003",
        deduction_type=DeductionType.MATERIAL_DEDUCTION,
        amount=Decimal("1000.00"),
        tax_treatment=TaxTreatment.TAXABLE,
        status=DeductionStatus.APPROVED,
    )
    draft = Deduction(
        project_id=project.id,
        contract_id=contract.id,
        payment_application_id=application.id,
        deduction_no="D-004",
        deduction_type=DeductionType.QUALITY_PENALTY,
        amount=Decimal("9999.00"),
        tax_treatment=TaxTreatment.TAXABLE,
        status=DeductionStatus.DRAFT,
    )
    db.add(approved)
    db.add(draft)
    await db.commit()

    total = await get_total_deduction_amount(application.id, db)
    assert total == Decimal("1000.00")


@pytest.mark.asyncio
async def test_get_total_deduction_amount_empty_is_zero(db):
    project, contract, version, application = await _setup_application(db)
    total = await get_total_deduction_amount(application.id, db)
    assert total == Decimal("0")
