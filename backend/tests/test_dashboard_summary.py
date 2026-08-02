"""GET /api/dashboard/summary returns 11 indicators + per_project + recent_audit."""
import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.models.contract import (
    Contract, ContractVersion, ContractVersionStatus, ContractVersionType,
)
from app.models.billing import (
    PaymentApplication, ApplicationStatus, RetentionEntry, RetentionEntryType,
)
from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.models.collection import Collection, CollectionStatus
from app.models.project import Project


@pytest.mark.asyncio
async def test_dashboard_summary_unauthenticated(client, db):
    r = await client.get("/api/dashboard/summary")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_summary_shape_for_empty_user(client, db, auth_user):
    """Authenticated user with no projects gets zero-valued indicators."""
    r = await client.get("/api/dashboard/summary")
    assert r.status_code == 200
    body = r.json()
    expected_keys = {
        "total_contract_amount", "gross_completed_total", "approved_total",
        "invoiced_total", "collected_total", "retention_held_total",
        "invoice_outstanding_total", "pending_variations", "pending_applications",
        "pending_mappings", "overclaim_exceptions", "contract_version_diffs",
        "per_project", "recent_audit",
    }
    assert set(body.keys()) == expected_keys
    assert body["total_contract_amount"] == "0"
    assert body["pending_variations"] == 0
    assert body["per_project"] == []
    assert body["recent_audit"] == []


@pytest.mark.asyncio
async def test_dashboard_summary_populated_path(client, db, auth_user):
    """Seeded data surfaces as non-zero indicators on the dashboard summary."""
    user_id = uuid.UUID(auth_user["id"])
    org_id = uuid.UUID(auth_user["org_id"])

    project = Project(
        organization_id=org_id,
        internal_project_code="PROJ-001",
        project_name="Populated Path Project",
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(project)
    await db.flush()

    contract = Contract(
        organization_id=org_id,
        project_id=project.id,
        external_contract_no="EXT-001",
        contract_name="Main Contract",
        currency="TWD",
        original_amount_ex_tax=Decimal("100000.00"),
        original_tax_amount=Decimal("5000.00"),
        original_amount_inc_tax=Decimal("105000.00"),
        status="APPROVED",
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(contract)
    await db.flush()

    version = ContractVersion(
        organization_id=org_id,
        contract_id=contract.id,
        version_no=1,
        version_type=ContractVersionType.SIGNED_CONTRACT,
        amount_ex_tax=Decimal("100000.00"),
        tax_amount=Decimal("5000.00"),
        amount_inc_tax=Decimal("105000.00"),
        status=ContractVersionStatus.APPROVED,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(version)
    await db.flush()
    contract.active_version_id = version.id

    app = PaymentApplication(
        organization_id=org_id,
        project_id=project.id,
        contract_id=contract.id,
        contract_version_id=version.id,
        application_no="APP-001",
        period_no=1,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        application_date=date(2026, 2, 1),
        status=ApplicationStatus.POSTED,
        currency="TWD",
        gross_completed_amount=Decimal("50000.00"),
        invoice_amount=Decimal("47500.00"),
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(app)
    await db.flush()

    invoice = Invoice(
        organization_id=org_id,
        project_id=project.id,
        contract_id=contract.id,
        invoice_no="INV-001",
        invoice_type=InvoiceType.STANDARD,
        issue_date=date(2026, 2, 2),
        amount_ex_tax=Decimal("40000.00"),
        tax_amount=Decimal("2000.00"),
        amount_inc_tax=Decimal("42000.00"),
        status=InvoiceStatus.ISSUED,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(invoice)
    await db.flush()

    collection = Collection(
        organization_id=org_id,
        project_id=project.id,
        contract_id=contract.id,
        receipt_no="RCT-001",
        receipt_date=date(2026, 2, 10),
        amount_received=Decimal("20000.00"),
        payment_method="BANK_TRANSFER",
        status=CollectionStatus.CONFIRMED,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(collection)
    await db.flush()

    retention = RetentionEntry(
        organization_id=org_id,
        project_id=project.id,
        contract_id=contract.id,
        payment_application_id=app.id,
        entry_type=RetentionEntryType.HOLD,
        amount=Decimal("3000.00"),
        description="Period 1 retention hold",
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(retention)
    await db.commit()

    r = await client.get("/api/dashboard/summary")
    assert r.status_code == 200
    body = r.json()

    assert body["total_contract_amount"] == "105000.00"
    assert body["gross_completed_total"] == "50000.00"
    assert body["approved_total"] == "47500.00"
    assert body["invoiced_total"] == "42000.00"
    assert body["collected_total"] == "20000.00"
    assert body["retention_held_total"] == "3000.00"
    assert body["pending_variations"] == 0
    assert isinstance(body["recent_audit"], list)
    assert len(body["per_project"]) == 1
    assert body["per_project"][0]["code"] == "PROJ-001"