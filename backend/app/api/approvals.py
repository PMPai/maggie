import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser
from app.models.approval import Approval
from app.models.identity import UserRoleEnum
from app.models.project import Project, ProjectMember
from app.models.contract import Contract, ContractVersion, ContractVersionStatus, ContractItem
from app.models.variation import Variation, VariationStatus
from app.models.mapping import ItemMapping, MappingStatus
from app.models.billing import PaymentApplication, ApplicationStatus, PaymentApplicationLine
from app.models.matching_review import MatchingReview

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


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


@router.get("")
async def list_approvals(resource_type: str = Query(...), resource_id: str = Query(...), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Approval).where(Approval.resource_type == resource_type, Approval.resource_id == uuid.UUID(resource_id))
    )
    return [
        {"id": str(a.id), "decision": a.decision, "step_order": a.step_order, "decided_at": a.decided_at.isoformat() if a.decided_at else None}
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

    # Item mappings (PENDING_REVIEW) — ItemMapping carries project_id directly
    for m in (await db.execute(
        select(ItemMapping).where(
            ItemMapping.project_id.in_(accessible),
            ItemMapping.status == MappingStatus.PENDING_REVIEW,
        )
    )).scalars().all():
        items.append(_row("item_mapping", m.id, m.project_id, "标准项目映射审核", None, "COST_REVIEWER",
                          f"/api/item-mappings/{m.id}/approve", f"/api/item-mappings/{m.id}/reject",
                          f"/projects/{m.project_id}/mapping", m.created_at))

    # Matching reviews (PENDING) — MatchingReview carries project_id directly
    for mr in (await db.execute(
        select(MatchingReview).where(
            MatchingReview.project_id.in_(accessible),
            MatchingReview.status == "PENDING",
        )
    )).scalars().all():
        label = "提前释放保留款" if getattr(mr, "review_type", "") == "RETENTION_RELEASE" else "匹配审核"
        items.append(_row("matching_review", mr.id, mr.project_id, label, None, "COST_REVIEWER",
                          f"/api/matching-reviews/{mr.id}/decide", None,
                          f"/projects/{mr.project_id}/mapping", mr.created_at))

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

    if resource_type:
        items = [i for i in items if i["resource_type"] == resource_type]
    if waiting_for_role:
        items = [i for i in items if i["waiting_for_role"] == waiting_for_role]

    return {"items": items}