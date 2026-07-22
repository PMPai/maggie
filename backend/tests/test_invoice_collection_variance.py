"""Test #12: Invoice / collection variance is not auto-reconciled.

When a collection received does not exactly match the invoiced amount, the
outstanding balance reflects the variance (343552 invoice - 343522 collected
= 30). No FinancialAdjustment is created automatically; the variance must be
handled explicitly by a human.
"""
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.contract import Contract
from app.models.identity import Organization
from app.models.project import Project
from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.models.collection import (
    Collection, CollectionStatus, CollectionAllocation,
)
from app.models.financial_adjustment import FinancialAdjustment
from app.services.collection_service import get_invoice_outstanding


async def _setup_contract(db):
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
    await db.commit()
    return org, project, contract


@pytest.mark.asyncio
async def test_invoice_outstanding_reflects_variance(db):
    org, project, contract = await _setup_contract(db)

    invoice = Invoice(
        organization_id=org.id,
        project_id=project.id,
        contract_id=contract.id,
        invoice_no="INV-001",
        invoice_type=InvoiceType.STANDARD,
        issue_date=date(2024, 2, 1),
        due_date=date(2024, 3, 1),
        amount_ex_tax=Decimal("327192.00"),
        tax_amount=Decimal("16360.00"),
        amount_inc_tax=Decimal("343552.00"),
        tax_rate=Decimal("0.05"),
        status=InvoiceStatus.ISSUED,
        source="MANUAL",
    )
    db.add(invoice)
    await db.flush()

    collection = Collection(
        organization_id=org.id,
        project_id=project.id,
        contract_id=contract.id,
        receipt_no="R-001",
        receipt_date=date(2024, 2, 10),
        amount_received=Decimal("343522.00"),
        payment_method="BANK_TRANSFER",
        status=CollectionStatus.CONFIRMED,
    )
    db.add(collection)
    await db.flush()

    allocation = CollectionAllocation(
        collection_id=collection.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("343522.00"),
    )
    db.add(allocation)
    await db.commit()

    outstanding = await get_invoice_outstanding(invoice.id, db)
    # 343552 - 343522 = 30
    assert outstanding == Decimal("30.00")


@pytest.mark.asyncio
async def test_variance_is_not_auto_reconciled(db):
    """No FinancialAdjustment is created automatically for the variance."""
    org, project, contract = await _setup_contract(db)

    invoice = Invoice(
        organization_id=org.id,
        project_id=project.id,
        contract_id=contract.id,
        invoice_no="INV-002",
        invoice_type=InvoiceType.STANDARD,
        amount_ex_tax=Decimal("327192.00"),
        tax_amount=Decimal("16360.00"),
        amount_inc_tax=Decimal("343552.00"),
        tax_rate=Decimal("0.05"),
        status=InvoiceStatus.ISSUED,
        source="MANUAL",
    )
    db.add(invoice)
    await db.flush()

    collection = Collection(
        organization_id=org.id,
        project_id=project.id,
        contract_id=contract.id,
        receipt_no="R-002",
        amount_received=Decimal("343522.00"),
        status=CollectionStatus.CONFIRMED,
    )
    db.add(collection)
    await db.flush()

    allocation = CollectionAllocation(
        collection_id=collection.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("343522.00"),
    )
    db.add(allocation)
    await db.commit()

    result = await db.execute(
        select(FinancialAdjustment).where(
            (FinancialAdjustment.invoice_id == invoice.id)
            | (FinancialAdjustment.collection_id == collection.id)
        )
    )
    adjustments = result.scalars().all()
    assert adjustments == []

    outstanding = await get_invoice_outstanding(invoice.id, db)
    assert outstanding == Decimal("30.00")


@pytest.mark.asyncio
async def test_full_payment_zero_outstanding(db):
    org, project, contract = await _setup_contract(db)

    invoice = Invoice(
        organization_id=org.id,
        project_id=project.id,
        contract_id=contract.id,
        invoice_no="INV-003",
        invoice_type=InvoiceType.STANDARD,
        amount_ex_tax=Decimal("1000.00"),
        tax_amount=Decimal("50.00"),
        amount_inc_tax=Decimal("1050.00"),
        tax_rate=Decimal("0.05"),
        status=InvoiceStatus.ISSUED,
        source="MANUAL",
    )
    db.add(invoice)
    await db.flush()

    collection = Collection(
        organization_id=org.id,
        project_id=project.id,
        contract_id=contract.id,
        receipt_no="R-003",
        amount_received=Decimal("1050.00"),
        status=CollectionStatus.CONFIRMED,
    )
    db.add(collection)
    await db.flush()

    allocation = CollectionAllocation(
        collection_id=collection.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("1050.00"),
    )
    db.add(allocation)
    await db.commit()

    outstanding = await get_invoice_outstanding(invoice.id, db)
    assert outstanding == Decimal("0.00")
