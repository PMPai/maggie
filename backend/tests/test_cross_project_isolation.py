"""Test #18: Cross-project data isolation.

Entities created in one project must not be visible when querying for another
project. Filtering by project_id enforces isolation at the data-access layer.
"""
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.contract import (
    Contract, ContractVersion, ContractVersionType, ContractVersionStatus,
)
from app.models.identity import Organization, User
from app.models.project import Project, ProjectMember, ProjectMemberRoleEnum
from app.models.variation import Variation, VariationType, VariationStatus
from app.models.deduction import (
    Deduction, DeductionType, TaxTreatment, DeductionStatus,
)
from app.models.invoice import Invoice, InvoiceType, InvoiceStatus


async def _make_world(db, code_prefix):
    org = Organization(
        code=f"org-{code_prefix}-{uuid.uuid4().hex[:6]}",
        name=f"Org {code_prefix}",
    )
    db.add(org)
    await db.flush()

    user = User(
        organization_id=org.id,
        email=f"user-{code_prefix}@example.com",
        display_name=f"User {code_prefix}",
    )
    db.add(user)
    await db.flush()

    project = Project(
        organization_id=org.id,
        internal_project_code=f"P-{code_prefix}-{uuid.uuid4().hex[:6]}",
        project_name=f"Project {code_prefix}",
    )
    db.add(project)
    await db.flush()

    member = ProjectMember(
        project_id=project.id,
        user_id=user.id,
        project_role=ProjectMemberRoleEnum.PROJECT_MANAGER,
    )
    db.add(member)
    await db.flush()

    contract = Contract(
        organization_id=org.id,
        project_id=project.id,
        external_contract_no=f"C-{code_prefix}-{uuid.uuid4().hex[:6]}",
        contract_name=f"Contract {code_prefix}",
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
    return org, user, project, contract, version


async def _count(db, model, project_id):
    result = await db.execute(
        select(model).where(model.project_id == project_id)
    )
    return result.scalars().all()


@pytest.mark.asyncio
async def test_two_projects_two_users_isolated(db):
    org_a, user_a, project_a, contract_a, version_a = await _make_world(db, "A")
    org_b, user_b, project_b, contract_b, version_b = await _make_world(db, "B")

    # Create a variation in project A only.
    variation_a = Variation(
        organization_id=org_a.id,
        project_id=project_a.id,
        contract_id=contract_a.id,
        variation_no="VAR-A-001",
        variation_type=VariationType.QUANTITY_ADJUSTMENT,
        quantity_delta=Decimal("20"),
        status=VariationStatus.APPROVED,
    )
    db.add(variation_a)

    # Create a deduction in project A only.
    deduction_a = Deduction(
        organization_id=org_a.id,
        project_id=project_a.id,
        contract_id=contract_a.id,
        deduction_no="DED-A-001",
        deduction_type=DeductionType.MATERIAL_DEDUCTION,
        amount=Decimal("1000.00"),
        tax_treatment=TaxTreatment.TAXABLE,
        status=DeductionStatus.APPROVED,
    )
    db.add(deduction_a)

    # Create an invoice in project A only.
    invoice_a = Invoice(
        organization_id=org_a.id,
        project_id=project_a.id,
        contract_id=contract_a.id,
        invoice_no="INV-A-001",
        invoice_type=InvoiceType.STANDARD,
        amount_ex_tax=Decimal("1000.00"),
        tax_amount=Decimal("50.00"),
        amount_inc_tax=Decimal("1050.00"),
        tax_rate=Decimal("0.05"),
        status=InvoiceStatus.ISSUED,
        source="MANUAL",
    )
    db.add(invoice_a)
    await db.commit()

    # Project A sees its own entities.
    a_variations = await _count(db, Variation, project_a.id)
    a_deductions = await _count(db, Deduction, project_a.id)
    a_invoices = await _count(db, Invoice, project_a.id)
    assert len(a_variations) == 1
    assert a_variations[0].variation_no == "VAR-A-001"
    assert len(a_deductions) == 1
    assert a_deductions[0].deduction_no == "DED-A-001"
    assert len(a_invoices) == 1
    assert a_invoices[0].invoice_no == "INV-A-001"

    # Project B cannot see project A's entities.
    b_variations = await _count(db, Variation, project_b.id)
    b_deductions = await _count(db, Deduction, project_b.id)
    b_invoices = await _count(db, Invoice, project_b.id)
    assert b_variations == []
    assert b_deductions == []
    assert b_invoices == []


@pytest.mark.asyncio
async def test_project_members_isolated(db):
    org_a, user_a, project_a, contract_a, version_a = await _make_world(db, "A")
    org_b, user_b, project_b, contract_b, version_b = await _make_world(db, "B")

    # user_a is a member of project_a only; user_b of project_b only.
    members_a = (
        await db.execute(
            select(ProjectMember).where(ProjectMember.project_id == project_a.id)
        )
    ).scalars().all()
    members_b = (
        await db.execute(
            select(ProjectMember).where(ProjectMember.project_id == project_b.id)
        )
    ).scalars().all()

    a_user_ids = {m.user_id for m in members_a}
    b_user_ids = {m.user_id for m in members_b}
    assert user_a.id in a_user_ids
    assert user_b.id not in a_user_ids
    assert user_b.id in b_user_ids
    assert user_a.id not in b_user_ids


@pytest.mark.asyncio
async def test_entities_created_in_project_b_not_visible_in_a(db):
    org_a, user_a, project_a, contract_a, version_a = await _make_world(db, "A")
    org_b, user_b, project_b, contract_b, version_b = await _make_world(db, "B")

    invoice_b = Invoice(
        organization_id=org_b.id,
        project_id=project_b.id,
        contract_id=contract_b.id,
        invoice_no="INV-B-001",
        invoice_type=InvoiceType.STANDARD,
        amount_ex_tax=Decimal("2000.00"),
        tax_amount=Decimal("100.00"),
        amount_inc_tax=Decimal("2100.00"),
        tax_rate=Decimal("0.05"),
        status=InvoiceStatus.ISSUED,
        source="MANUAL",
    )
    db.add(invoice_b)
    await db.commit()

    a_invoices = await _count(db, Invoice, project_a.id)
    b_invoices = await _count(db, Invoice, project_b.id)
    assert a_invoices == []
    assert len(b_invoices) == 1
    assert b_invoices[0].invoice_no == "INV-B-001"
