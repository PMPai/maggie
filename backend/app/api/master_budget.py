"""GET /api/projects/{project_id}/master-budget - tree rows with cost/margin/exception_status."""
import uuid
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser, require_project_member
from app.models.contract import (
    Contract, ContractVersion, ContractVersionStatus, ContractItem,
)
from app.models.billing import (
    PaymentApplication, PaymentApplicationLine, ApplicationStatus,
    RetentionEntry, RetentionEntryType,
)
from app.models.invoice import Invoice, InvoiceStatus
from app.models.collection import Collection, CollectionStatus
from app.models.variation import VariationLine

router = APIRouter(prefix="/api/projects", tags=["master-budget"])


def _str(v) -> str:
    return str(v) if v is not None else "0"


@router.get("/{project_id}/master-budget")
async def get_master_budget(
    project_id: str,
    contract_id: str | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pid = uuid.UUID(project_id)
    await require_project_member(pid, current, db)

    # Select contract
    if contract_id:
        contract = (await db.execute(
            select(Contract).where(
                Contract.id == uuid.UUID(contract_id),
                Contract.project_id == pid,
                Contract.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
    else:
        contract = (await db.execute(
            select(Contract)
            .where(Contract.project_id == pid, Contract.deleted_at.is_(None))
            .order_by(Contract.created_at)
            .limit(1)
        )).scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="No contract found for project")

    # Active version (or latest APPROVED)
    version = (await db.execute(
        select(ContractVersion).where(ContractVersion.id == contract.active_version_id)
    )).scalar_one_or_none()
    if not version:
        version = (await db.execute(
            select(ContractVersion)
            .where(
                ContractVersion.contract_id == contract.id,
                ContractVersion.status == ContractVersionStatus.APPROVED,
            )
            .order_by(ContractVersion.version_no.desc())
        )).scalars().first()
    if not version:
        raise HTTPException(status_code=404, detail="No approved contract version")

    items = (await db.execute(
        select(ContractItem)
        .where(ContractItem.contract_version_id == version.id)
        .order_by(ContractItem.sort_order)
    )).scalars().all()

    # Variation deltas per contract_item
    item_ids = [i.id for i in items]
    var_delta_by_item: dict[uuid.UUID, Decimal] = {}
    if item_ids:
        var_lines = (await db.execute(
            select(VariationLine).where(VariationLine.contract_item_id.in_(item_ids))
        )).scalars().all()
        for vl in var_lines:
            var_delta_by_item[vl.contract_item_id] = (
                var_delta_by_item.get(vl.contract_item_id, Decimal("0"))
                + (vl.quantity_delta or Decimal("0"))
            )

    # Posted application lines cumulative
    posted_app_ids = [r[0] for r in (await db.execute(
        select(PaymentApplication.id).where(
            PaymentApplication.contract_id == contract.id,
            PaymentApplication.status == ApplicationStatus.POSTED,
        )
    )).all()]
    pal_by_item: dict[uuid.UUID, list[PaymentApplicationLine]] = {}
    if posted_app_ids:
        pals = (await db.execute(
            select(PaymentApplicationLine).where(
                PaymentApplicationLine.payment_application_id.in_(posted_app_ids)
            )
        )).scalars().all()
        for pal in pals:
            pal_by_item.setdefault(pal.contract_item_id, []).append(pal)

    # Latest application (current period) — exclude terminal/rejected statuses
    # so a REJECTED/CANCELLED/SUPERSEDED app is never picked as "current period".
    latest_app = (await db.execute(
        select(PaymentApplication)
        .where(
            PaymentApplication.contract_id == contract.id,
            PaymentApplication.status.notin_([
                ApplicationStatus.REJECTED,
                ApplicationStatus.CANCELLED,
                ApplicationStatus.SUPERSEDED,
            ]),
        )
        .order_by(PaymentApplication.period_no.desc())
    )).scalars().first()
    current_pal_by_item: dict[uuid.UUID, Decimal] = {}
    if latest_app:
        for pal in (await db.execute(
            select(PaymentApplicationLine).where(
                PaymentApplicationLine.payment_application_id == latest_app.id
            )
        )).scalars().all():
            current_pal_by_item[pal.contract_item_id] = (
                pal.current_approved_quantity or Decimal("0")
            )

    # Retention balance per contract (HOLD - RELEASE - REVERSAL)
    retention_total = Decimal("0")
    for re_ in (await db.execute(
        select(RetentionEntry).where(RetentionEntry.contract_id == contract.id)
    )).scalars().all():
        if re_.entry_type == RetentionEntryType.HOLD:
            retention_total += re_.amount or Decimal("0")
        elif re_.entry_type in (RetentionEntryType.RELEASE, RetentionEntryType.REVERSAL):
            retention_total -= re_.amount or Decimal("0")

    # Invoiced + collected per project
    inv_total = Decimal("0")
    for i in (await db.execute(
        select(Invoice).where(
            Invoice.project_id == pid, Invoice.status == InvoiceStatus.ISSUED
        )
    )).scalars().all():
        inv_total += i.amount_inc_tax or Decimal("0")

    coll_total = Decimal("0")
    for c in (await db.execute(
        select(Collection).where(
            Collection.project_id == pid, Collection.status == CollectionStatus.CONFIRMED
        )
    )).scalars().all():
        coll_total += c.amount_received or Decimal("0")

    rows = []
    for item in items:
        var_delta = var_delta_by_item.get(item.id, Decimal("0"))
        available = (item.contract_quantity or Decimal("0")) + var_delta
        pals = pal_by_item.get(item.id, [])
        cum_qty = max(
            (p.cumulative_approved_quantity or Decimal("0") for p in pals),
            default=Decimal("0"),
        )
        current_qty = current_pal_by_item.get(item.id, Decimal("0"))
        remaining = available - cum_qty

        completed_amount = cum_qty * (item.unit_price or Decimal("0"))
        claimed_amount = sum(
            (p.current_completed_amount or Decimal("0") for p in pals),
            Decimal("0"),
        )

        if item.unit_cost is not None:
            unit_cost_val = float(item.unit_cost)
            line_amount_val = float(item.line_amount or 0)
            margin = (float(item.unit_price or 0) - unit_cost_val) * float(item.contract_quantity or 0)
            margin_pct = (margin / line_amount_val * 100) if line_amount_val else 0
            std_cost_per_unit = item.unit_cost
            std_cost_total = item.unit_cost * (item.contract_quantity or Decimal("0"))
            price_variance = (item.unit_price or Decimal("0")) - item.unit_cost
        else:
            margin = None
            margin_pct = None
            std_cost_per_unit = None
            std_cost_total = None
            price_variance = None

        today = date.today()
        if remaining < 0:
            exception = "overclaim"
        elif item.expected_payment_date and item.expected_payment_date < today:
            exception = "overdue"
        else:
            exception = "none"

        rows.append({
            "contract_item_id": str(item.id),
            "parent_item_id": str(item.parent_item_id) if item.parent_item_id else None,
            "line_no": item.line_no,
            "description": item.source_description,
            "unit": item.unit,
            "contract_quantity": _str(item.contract_quantity),
            "unit_price": _str(item.unit_price),
            "approved_quantity": _str(item.contract_quantity),
            "approved_unit_price": _str(item.unit_price),
            "variation_delta": _str(var_delta),
            "previous_cumulative_quantity": _str(cum_qty - current_qty),
            "current_period_quantity": _str(current_qty),
            "cumulative_approved_quantity": _str(cum_qty),
            "remaining_quantity": _str(remaining),
            "completed_amount": _str(completed_amount),
            "claimed_amount": _str(claimed_amount),
            "retention_balance": _str(retention_total),
            "invoiced_amount": _str(inv_total),
            "collected_amount": _str(coll_total),
            "standard_cost_per_unit": _str(std_cost_per_unit) if std_cost_per_unit is not None else None,
            "standard_cost_total": _str(std_cost_total) if std_cost_total is not None else None,
            "expected_margin": _str(margin) if margin is not None else None,
            "margin_pct": _str(margin_pct) if margin_pct is not None else None,
            "price_variance": _str(price_variance) if price_variance is not None else None,
            "expected_payment_date": item.expected_payment_date.isoformat() if item.expected_payment_date else None,
            "actual_payment_date": item.actual_payment_date.isoformat() if item.actual_payment_date else None,
            "exception_status": exception,
        })

    return {
        "contract_id": str(contract.id),
        "contract_version_id": str(version.id),
        "rows": rows,
    }
