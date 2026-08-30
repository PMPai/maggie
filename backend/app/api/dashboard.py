"""GET /api/dashboard/summary — aggregated indicators for the management cockpit."""
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser
from app.models.identity import UserRoleEnum
from app.models.project import Project, ProjectMember
from app.models.contract import Contract, ContractVersion, ContractItem
from app.models.billing import (
    PaymentApplication, ApplicationStatus, RetentionEntry, RetentionEntryType,
    PaymentApplicationLine,
)
from app.models.invoice import Invoice, InvoiceStatus
from app.models.collection import Collection, CollectionStatus
from app.models.variation import Variation, VariationStatus
from app.models.approval import AuditLog

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _dec(v) -> str:
    return str(v) if v is not None else "0"


def _empty_summary(recent_audit: list) -> dict:
    return {
        "total_contract_amount": "0", "gross_completed_total": "0", "approved_total": "0",
        "invoiced_total": "0", "collected_total": "0", "retention_held_total": "0",
        "invoice_outstanding_total": "0", "pending_variations": 0, "pending_applications": 0,
        "pending_mappings": 0, "overclaim_exceptions": 0, "contract_version_diffs": 0,
        "per_project": [], "recent_audit": recent_audit,
    }


async def _accessible_project_ids(current: CurrentUser, db: AsyncSession) -> list[uuid.UUID]:
    if UserRoleEnum.SYSTEM_ADMIN in current.roles:
        result = await db.execute(
            select(Project.id).where(
                Project.organization_id == current.organization_id,
                Project.deleted_at.is_(None),
            )
        )
    else:
        result = await db.execute(
            select(ProjectMember.project_id).where(
                ProjectMember.user_id == current.user.id,
                ProjectMember.status == "ACTIVE",
            )
        )
    return [r[0] for r in result.all()]


@router.get("/summary")
async def get_summary(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project_ids = await _accessible_project_ids(current, db)

    # Recent audit (org-scoped, last 5) — runs unconditionally so empty-project
    # users (e.g. SYSTEM_ADMIN with no projects) still see their org's audit trail.
    audit_rows = (await db.execute(
        select(AuditLog)
        .where(AuditLog.organization_id == current.organization_id)
        .order_by(AuditLog.created_at.desc())
        .limit(5)
    )).scalars().all()
    recent_audit = [
        {
            "id": str(a.id),
            "action": a.action,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in audit_rows
    ]

    if not project_ids:
        return _empty_summary(recent_audit)

    contract_ids_subq = select(Contract.id).where(Contract.project_id.in_(project_ids))

    # Contract amounts (sum of original_amount_inc_tax on non-deleted contracts)
    total_contract = (await db.execute(
        select(func.coalesce(func.sum(Contract.original_amount_inc_tax), 0))
        .where(Contract.project_id.in_(project_ids), Contract.deleted_at.is_(None))
    )).scalar_one()

    # Gross completed (POSTED applications)
    gross_total = (await db.execute(
        select(func.coalesce(func.sum(PaymentApplication.gross_completed_amount), 0))
        .where(
            PaymentApplication.project_id.in_(project_ids),
            PaymentApplication.status == ApplicationStatus.POSTED,
        )
    )).scalar_one()

    # Approved total (invoice_amount of POSTED applications)
    approved_total = (await db.execute(
        select(func.coalesce(func.sum(PaymentApplication.invoice_amount), 0))
        .where(
            PaymentApplication.project_id.in_(project_ids),
            PaymentApplication.status == ApplicationStatus.POSTED,
        )
    )).scalar_one()

    # Invoiced (ISSUED invoices)
    invoiced_total = (await db.execute(
        select(func.coalesce(func.sum(Invoice.amount_inc_tax), 0))
        .where(Invoice.project_id.in_(project_ids), Invoice.status == InvoiceStatus.ISSUED)
    )).scalar_one()

    # Collected (CONFIRMED collections)
    collected_total = (await db.execute(
        select(func.coalesce(func.sum(Collection.amount_received), 0))
        .where(
            Collection.project_id.in_(project_ids),
            Collection.status == CollectionStatus.CONFIRMED,
        )
    )).scalar_one()

    # Retention held = HOLD - (RELEASE + REVERSAL)
    held = (await db.execute(
        select(func.coalesce(func.sum(RetentionEntry.amount), 0)).where(
            RetentionEntry.contract_id.in_(contract_ids_subq),
            RetentionEntry.entry_type == RetentionEntryType.HOLD,
        )
    )).scalar_one()
    released = (await db.execute(
        select(func.coalesce(func.sum(RetentionEntry.amount), 0)).where(
            RetentionEntry.contract_id.in_(contract_ids_subq),
            RetentionEntry.entry_type.in_(
                [RetentionEntryType.RELEASE, RetentionEntryType.REVERSAL]
            ),
        )
    )).scalar_one()
    retention_held = (held or 0) - (released or 0)

    invoice_outstanding = (invoiced_total or 0) - (collected_total or 0)

    # Pending counts
    pending_var = (await db.execute(
        select(func.count()).select_from(Variation).where(
            Variation.project_id.in_(project_ids),
            Variation.status == VariationStatus.UNDER_REVIEW,
        )
    )).scalar_one()
    pending_app = (await db.execute(
        select(func.count()).select_from(PaymentApplication).where(
            PaymentApplication.project_id.in_(project_ids),
            PaymentApplication.status.in_(
                [ApplicationStatus.SUBMITTED, ApplicationStatus.PROJECT_APPROVED]
            ),
        )
    )).scalar_one()
    pending_map = 0

    # Overclaim: payment_application_lines where cumulative > contract_quantity
    overclaim = (await db.execute(
        select(func.count()).select_from(PaymentApplicationLine)
        .join(ContractItem, ContractItem.id == PaymentApplicationLine.contract_item_id)
        .where(
            PaymentApplicationLine.cumulative_approved_quantity > ContractItem.contract_quantity,
            ContractItem.contract_version_id.in_(
                select(ContractVersion.id).where(
                    ContractVersion.contract_id.in_(contract_ids_subq)
                )
            ),
        )
    )).scalar_one()

    # Contract version diffs: contracts with >1 version having distinct amount_inc_tax
    diffs = (await db.execute(
        select(func.count()).select_from(
            select(Contract.id)
            .join(ContractVersion, ContractVersion.contract_id == Contract.id)
            .where(Contract.project_id.in_(project_ids))
            .group_by(Contract.id)
            .having(func.count(func.distinct(ContractVersion.amount_inc_tax)) > 1)
        )
    )).scalar_one()

    # Per-project breakdown
    per_project = []
    for pid in project_ids:
        proj = (await db.execute(
            select(Project).where(Project.id == pid, Project.deleted_at.is_(None))
        )).scalar_one_or_none()
        if not proj:
            continue
        c_amt = (await db.execute(
            select(func.coalesce(func.sum(Contract.original_amount_inc_tax), 0))
            .where(Contract.project_id == pid, Contract.deleted_at.is_(None))
        )).scalar_one()
        a_amt = (await db.execute(
            select(func.coalesce(func.sum(PaymentApplication.invoice_amount), 0))
            .where(
                PaymentApplication.project_id == pid,
                PaymentApplication.status == ApplicationStatus.POSTED,
            )
        )).scalar_one()
        per_project.append({
            "project_id": str(pid),
            "code": proj.internal_project_code,
            "name": proj.project_name,
            "contract_amount": _dec(c_amt),
            "approved_total": _dec(a_amt),
            "retention_held": _dec(0),
        })

    return {
        "total_contract_amount": _dec(total_contract),
        "gross_completed_total": _dec(gross_total),
        "approved_total": _dec(approved_total),
        "invoiced_total": _dec(invoiced_total),
        "collected_total": _dec(collected_total),
        "retention_held_total": _dec(retention_held),
        "invoice_outstanding_total": _dec(invoice_outstanding),
        "pending_variations": pending_var,
        "pending_applications": pending_app,
        "pending_mappings": pending_map,
        "overclaim_exceptions": overclaim,
        "contract_version_diffs": diffs,
        "per_project": per_project,
        "recent_audit": recent_audit,
    }


@router.get("/cash-flow")
async def get_cash_flow(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Projected cash inflow by month based on expected_payment_date on contract items + actual collections."""
    from collections import defaultdict
    from decimal import Decimal

    project_ids = await _accessible_project_ids(current, db)
    if not project_ids:
        return {"months": []}

    contract_ids_subq = select(Contract.id).where(Contract.project_id.in_(project_ids), Contract.deleted_at.is_(None))

    # Expected: sum line_amount grouped by month of expected_payment_date
    expected_rows = (await db.execute(
        select(
            func.to_char(ContractItem.expected_payment_date, 'YYYY-MM').label('month'),
            func.sum(ContractItem.line_amount).label('amount'),
        )
        .join(ContractVersion, ContractVersion.id == ContractItem.contract_version_id)
        .join(Contract, Contract.id == ContractVersion.contract_id)
        .where(
            Contract.id.in_(contract_ids_subq),
            ContractItem.expected_payment_date.is_not(None),
            ContractItem.is_heading.is_(False),
        )
        .group_by('month')
        .order_by('month')
    )).all()

    # Actual: sum collections grouped by month of receipt_date
    from app.models.collection import Collection, CollectionStatus
    actual_rows = (await db.execute(
        select(
            func.to_char(Collection.receipt_date, 'YYYY-MM').label('month'),
            func.sum(Collection.amount_received).label('amount'),
        )
        .where(
            Collection.project_id.in_(project_ids),
            Collection.status == CollectionStatus.CONFIRMED,
        )
        .group_by('month')
        .order_by('month')
    )).all()

    # Merge into a unified month list
    months_map: dict[str, dict] = {}
    for r in expected_rows:
        m = r.month
        months_map.setdefault(m, {"month": m, "expected": Decimal("0"), "actual": Decimal("0")})
        months_map[m]["expected"] += r.amount or Decimal("0")
    for r in actual_rows:
        m = r.month
        months_map.setdefault(m, {"month": m, "expected": Decimal("0"), "actual": Decimal("0")})
        months_map[m]["actual"] += r.amount or Decimal("0")

    months = sorted(months_map.values(), key=lambda x: x["month"])
    # Convert decimals to strings for JSON
    return {"months": [{"month": m["month"], "expected": str(m["expected"]), "actual": str(m["actual"])} for m in months]}


@router.get("/payment-trend")
async def get_payment_trend(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Monthly posted payment application amounts — trend over time."""
    from app.models.billing import PaymentApplication, ApplicationStatus

    project_ids = await _accessible_project_ids(current, db)
    if not project_ids:
        return {"months": []}

    rows = (await db.execute(
        select(
            func.to_char(PaymentApplication.application_date, 'YYYY-MM').label('month'),
            func.sum(PaymentApplication.invoice_amount).label('amount'),
        )
        .where(
            PaymentApplication.project_id.in_(project_ids),
            PaymentApplication.status.in_([ApplicationStatus.POSTED, ApplicationStatus.GENERATED, ApplicationStatus.SENT]),
        )
        .group_by('month')
        .order_by('month')
    )).all()

    return {"months": [{"month": r.month, "amount": str(r.amount or 0)} for r in rows]}
