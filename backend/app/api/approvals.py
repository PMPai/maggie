import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser
from app.models.approval import Approval
from app.models.project import Project
from app.models.contract import Contract, ContractVersion, ContractVersionStatus, ContractItem
from app.models.variation import Variation, VariationStatus
from app.models.billing import PaymentApplication, ApplicationStatus, PaymentApplicationLine

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


async def _accessible_project_ids(current: CurrentUser, db: AsyncSession) -> list[uuid.UUID]:
    result = await db.execute(
        select(Project.id).where(
            Project.deleted_at.is_(None),
        )
    )
    return [r[0] for r in result.all()]


@router.get("")
async def list_approvals(resource_type: str = Query(...), resource_id: str = Query(...), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Approval).where(Approval.resource_type == resource_type, Approval.resource_id == uuid.UUID(resource_id))
    )
    return [
        {"id": str(a.id), "decision": a.decision, "step_order": a.step_order,
         "decided_by": str(a.decided_by), "decided_at": a.decided_at.isoformat() if a.decided_at else None,
         "comment": a.comment}
        for a in result.scalars().all()
    ]


@router.get("/pending")
async def list_pending(
    project_id: str | None = Query(None),
    resource_type: str | None = Query(None),
    waiting_for_role: str | None = Query(None),
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    accessible = await _accessible_project_ids(current, db)
    if project_id:
        pid = uuid.UUID(project_id)
        if pid not in accessible:
            return {"items": []}
        accessible = [pid]

    items: list[dict] = []
    proj_q = select(Project.id, Project.internal_project_code).where(Project.id.in_(accessible))
    code_map = {r[0]: r[1] for r in (await db.execute(proj_q)).all()}

    def _row(rtype, rid, pid, desc, amount, role, approve_url, reject_url, detail_url, created_at):
        return {
            "resource_type": rtype, "resource_id": str(rid), "description": desc,
            "project_id": str(pid) if pid else None, "project_code": code_map.get(pid) if pid else None,
            "amount": str(amount) if amount is not None else None, "waiting_for_role": role,
            "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
            "approve_url": approve_url, "reject_url": reject_url, "detail_url": detail_url,
        }

    # Variations (UNDER_REVIEW = pending approval)
    for v in (await db.execute(
        select(Variation).where(Variation.project_id.in_(accessible), Variation.status == VariationStatus.UNDER_REVIEW)
    )).scalars().all():
        items.append(_row("variation", v.id, v.project_id, v.description or v.variation_no,
                          v.amount_inc_tax, "PROJECT_MANAGER",
                          f"/api/variations/{v.id}/approve", f"/api/variations/{v.id}/reject",
                          f"/projects/{v.project_id}/variations", v.created_at))

    # Contract versions (UNDER_REVIEW)
    for cv, c in (await db.execute(
        select(ContractVersion, Contract).join(Contract, Contract.id == ContractVersion.contract_id)
        .where(Contract.project_id.in_(accessible), ContractVersion.status == ContractVersionStatus.UNDER_REVIEW)
    )).all():
        items.append(_row("contract_version", cv.id, c.project_id, f"合同版本 v{cv.version_no} - {c.contract_name}",
                          cv.amount_inc_tax, "CONTRACT_ADMIN",
                          f"/api/contracts/{c.id}/versions/{cv.id}/approve", None,
                          f"/projects/{c.project_id}", cv.created_at))

    # Payment applications (SUBMITTED -> PM; PROJECT_APPROVED -> Finance)
    for pa in (await db.execute(
        select(PaymentApplication).where(PaymentApplication.project_id.in_(accessible))
    )).scalars().all():
        if pa.status == ApplicationStatus.SUBMITTED:
            items.append(_row("payment_application_pm", pa.id, pa.project_id, f"请款 {pa.application_no}",
                              pa.invoice_amount, "PROJECT_MANAGER",
                              f"/api/payment-applications/{pa.id}/approve", None,
                              f"/applications/{pa.id}", pa.created_at))
        elif pa.status == ApplicationStatus.PROJECT_APPROVED:
            items.append(_row("payment_application_finance", pa.id, pa.project_id, f"请款 {pa.application_no}",
                              pa.invoice_amount, "FINANCE_REVIEWER",
                              f"/api/payment-applications/{pa.id}/approve", None,
                              f"/applications/{pa.id}", pa.created_at))

    # Overclaim: batch-resolve via single JOIN, project-scoped at SQL level (no per-row awaits)
    seen_items: set[uuid.UUID] = set()
    for ci_id, source_description, project_id, created_at in (await db.execute(
        select(ContractItem.id, ContractItem.source_description,
               Contract.project_id, PaymentApplicationLine.created_at)
        .join(PaymentApplicationLine, PaymentApplicationLine.contract_item_id == ContractItem.id)
        .join(ContractVersion, ContractVersion.id == ContractItem.contract_version_id)
        .join(Contract, Contract.id == ContractVersion.contract_id)
        .where(
            PaymentApplicationLine.cumulative_approved_quantity > ContractItem.contract_quantity,
            Contract.project_id.in_(accessible),
        )
    )).all():
        if ci_id in seen_items:
            continue
        seen_items.add(ci_id)
        desc = (source_description or "")[:40]
        items.append(_row("overclaim", ci_id, project_id, f"超量异常: {desc}",
                          None, "PROJECT_MANAGER", None, None,
                          f"/projects/{project_id}/budget", created_at))

    # Deductions with DRAFT status (pending approval)
    from app.models.deduction import Deduction
    for d in (await db.execute(
        select(Deduction).where(Deduction.project_id.in_(accessible), Deduction.status == "DRAFT")
    )).scalars().all():
        items.append(_row("deduction", d.id, d.project_id, f"扣款审批: {getattr(d, 'deduction_no', '')}",
                          getattr(d, "amount", None), "FINANCE_REVIEWER",
                          f"/api/deductions/{d.id}/approve", None,
                          f"/projects/{d.project_id}/deductions", d.created_at))

    # Collection variances (invoices with outstanding > 0)
    from app.models.invoice import Invoice, InvoiceStatus
    from app.models.collection import Collection, CollectionStatus, CollectionAllocation
    from sqlalchemy import func as sqlfunc
    for inv, proj_id in (await db.execute(
        select(Invoice, Contract.project_id)
        .join(Contract, Contract.id == Invoice.contract_id)
        .where(Invoice.project_id.in_(accessible), Invoice.status == InvoiceStatus.ISSUED)
    )).all():
        collected = (await db.execute(
            select(sqlfunc.coalesce(sqlfunc.sum(CollectionAllocation.allocated_amount), 0))
            .join(Collection, Collection.id == CollectionAllocation.collection_id)
            .where(CollectionAllocation.invoice_id == inv.id, Collection.status == CollectionStatus.CONFIRMED)
        )).scalar_one()
        outstanding = float(inv.amount_inc_tax or 0) - float(collected)
        if outstanding > 0.01:
            items.append(_row("collection_variance", inv.id, proj_id, f"发票 {inv.invoice_no} 未收清 (差 {outstanding:.0f})",
                              str(outstanding), "FINANCE_USER", None, None,
                              f"/projects/{proj_id}/invoices", inv.created_at if hasattr(inv, 'created_at') else None))

    if resource_type:
        items = [i for i in items if i["resource_type"] == resource_type]
    if waiting_for_role:
        items = [i for i in items if i["waiting_for_role"] == waiting_for_role]

    return {"items": items}
