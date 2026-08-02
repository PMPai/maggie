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
from app.models.mapping import ItemMapping, MappingStatus
from app.models.approval import AuditLog

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _dec(v) -> str:
    return str(v) if v is not None else "0"


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

    if not project_ids:
        return {
            "total_contract_amount": "0", "gross_completed_total": "0", "approved_total": "0",
            "invoiced_total": "0", "collected_total": "0", "retention_held_total": "0",
            "invoice_outstanding_total": "0", "pending_variations": 0, "pending_applications": 0,
            "pending_mappings": 0, "overclaim_exceptions": 0, "contract_version_diffs": 0,
            "per_project": [], "recent_audit": [],
        }

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
    pending_map = (await db.execute(
        select(func.count()).select_from(ItemMapping).where(
            ItemMapping.project_id.in_(project_ids),
            ItemMapping.status == MappingStatus.PENDING_REVIEW,
        )
    )).scalar_one()

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

    # Recent audit (last 5 for this org)
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
