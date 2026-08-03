from fastapi import APIRouter, Depends, Query
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _rows(result):
    columns = result.keys()
    return [dict(zip(columns, row)) for row in result.all()]


@router.get("/contract-item-balances")
async def contract_item_balances(contract_id: str | None = None, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = "SELECT * FROM v_contract_item_balances"
    if contract_id:
        query += " WHERE contract_id = :cid"
        result = await db.execute(text(query), {"cid": contract_id})
    else:
        result = await db.execute(text(query))
    return _rows(result)


@router.get("/project-summary")
async def project_summary(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM v_project_commercial_summary"))
    return _rows(result)


@router.get("/retention-balances")
async def retention_balances(contract_id: str | None = None, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = "SELECT * FROM v_retention_balances"
    if contract_id:
        query += " WHERE contract_id = :cid"
        result = await db.execute(text(query), {"cid": contract_id})
    else:
        result = await db.execute(text(query))
    return _rows(result)


@router.get("/uninvoiced")
async def uninvoiced(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM v_uninvoiced_approved_amounts"))
    return _rows(result)


@router.get("/invoice-outstanding")
async def invoice_outstanding(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM v_invoice_outstanding"))
    return _rows(result)


@router.get("/collection-variances")
async def collection_variances(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM v_collection_variances"))
    return _rows(result)


@router.get("/cost-margin")
async def cost_margin(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM v_cost_margin_analysis"))
    return _rows(result)


@router.get("/pending-exceptions")
async def pending_exceptions(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM v_pending_exceptions"))
    return _rows(result)


@router.get("/audit-log")
async def audit_log(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 100"))
    return _rows(result)


@router.get("/project-overview")
async def project_overview(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """项目合同总览 — per project: contract info + approved totals + invoiced + collected."""
    from app.models.project import Project, ProjectMember
    from app.models.identity import UserRoleEnum
    from app.models.contract import Contract, ContractVersion, ContractVersionStatus
    from app.models.billing import PaymentApplication, ApplicationStatus
    from app.models.invoice import Invoice, InvoiceStatus
    from app.models.collection import Collection, CollectionStatus

    if UserRoleEnum.SYSTEM_ADMIN in current.roles:
        proj_ids = [r[0] for r in (await db.execute(
            select(Project.id).where(Project.organization_id == current.organization_id, Project.deleted_at.is_(None))
        )).all()]
    else:
        proj_ids = [r[0] for r in (await db.execute(
            select(ProjectMember.project_id).where(ProjectMember.user_id == current.user.id, ProjectMember.status == "ACTIVE")
        )).all()]

    if not proj_ids:
        return []

    rows = []
    for pid in proj_ids:
        proj = (await db.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()
        if not proj:
            continue
        # Latest active contract
        contract = (await db.execute(
            select(Contract).where(Contract.project_id == pid, Contract.deleted_at.is_(None)).order_by(Contract.created_at)
        )).scalars().first()
        contract_no = contract.external_contract_no if contract else None
        contract_name = contract.contract_name if contract else None
        contract_amount = str(contract.original_amount_inc_tax) if contract else "0"

        approved_total = (await db.execute(
            select(func.coalesce(func.sum(PaymentApplication.invoice_amount), 0))
            .where(PaymentApplication.project_id == pid, PaymentApplication.status == ApplicationStatus.POSTED)
        )).scalar_one()
        invoiced_total = (await db.execute(
            select(func.coalesce(func.sum(Invoice.amount_inc_tax), 0))
            .where(Invoice.project_id == pid, Invoice.status == InvoiceStatus.ISSUED)
        )).scalar_one()
        collected_total = (await db.execute(
            select(func.coalesce(func.sum(Collection.amount_received), 0))
            .where(Collection.project_id == pid, Collection.status == CollectionStatus.CONFIRMED)
        )).scalar_one()

        rows.append({
            "project_code": proj.internal_project_code,
            "project_name": proj.project_name,
            "contract_no": contract_no,
            "contract_name": contract_name,
            "contract_amount": str(contract_amount),
            "approved_total": str(approved_total),
            "invoiced_total": str(invoiced_total),
            "collected_total": str(collected_total),
            "remaining": str(float(approved_total) - float(invoiced_total)),
        })
    return rows


@router.get("/application-history")
async def application_history(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """请款历史 — per application: project, contract, period, status, amounts."""
    from app.models.project import Project, ProjectMember
    from app.models.identity import UserRoleEnum
    from app.models.contract import Contract
    from app.models.billing import PaymentApplication

    if UserRoleEnum.SYSTEM_ADMIN in current.roles:
        proj_ids = [r[0] for r in (await db.execute(
            select(Project.id).where(Project.organization_id == current.organization_id, Project.deleted_at.is_(None))
        )).all()]
    else:
        proj_ids = [r[0] for r in (await db.execute(
            select(ProjectMember.project_id).where(ProjectMember.user_id == current.user.id, ProjectMember.status == "ACTIVE")
        )).all()]

    if not proj_ids:
        return []

    apps = (await db.execute(
        select(PaymentApplication, Contract, Project)
        .join(Contract, Contract.id == PaymentApplication.contract_id)
        .join(Project, Project.id == PaymentApplication.project_id)
        .where(PaymentApplication.project_id.in_(proj_ids))
        .order_by(PaymentApplication.application_date.desc())
    )).all()

    return [{
        "application_no": pa.application_no,
        "project_code": proj.internal_project_code,
        "project_name": proj.project_name,
        "contract_no": c.external_contract_no,
        "period_no": pa.period_no,
        "status": pa.status if isinstance(pa.status, str) else pa.status.value,
        "gross_completed_amount": str(pa.gross_completed_amount or 0),
        "retention_held_amount": str(pa.retention_held_amount or 0),
        "tax_amount": str(pa.tax_amount or 0),
        "invoice_amount": str(pa.invoice_amount or 0),
        "application_date": pa.application_date.isoformat() if pa.application_date else None,
    } for pa, c, proj in apps]


@router.get("/receivables-aging")
async def receivables_aging(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """应收账龄 — per outstanding invoice: invoice no, amount, collected, outstanding, age days, age bucket."""
    from app.models.project import Project, ProjectMember
    from app.models.identity import UserRoleEnum
    from app.models.contract import Contract
    from app.models.invoice import Invoice, InvoiceStatus
    from app.models.collection import Collection, CollectionStatus, CollectionAllocation
    from sqlalchemy import case
    from datetime import date

    if UserRoleEnum.SYSTEM_ADMIN in current.roles:
        proj_ids = [r[0] for r in (await db.execute(
            select(Project.id).where(Project.organization_id == current.organization_id, Project.deleted_at.is_(None))
        )).all()]
    else:
        proj_ids = [r[0] for r in (await db.execute(
            select(ProjectMember.project_id).where(ProjectMember.user_id == current.user.id, ProjectMember.status == "ACTIVE")
        )).all()]

    if not proj_ids:
        return []

    invoices = (await db.execute(
        select(Invoice, Contract, Project)
        .join(Contract, Contract.id == Invoice.contract_id)
        .join(Project, Project.id == Invoice.project_id)
        .where(Invoice.project_id.in_(proj_ids), Invoice.status == InvoiceStatus.ISSUED)
        .order_by(Invoice.issue_date.desc())
    )).all()

    today = date.today()
    rows = []
    for inv, c, proj in invoices:
        # Sum collected for this invoice
        collected = (await db.execute(
            select(func.coalesce(func.sum(CollectionAllocation.allocated_amount), 0))
            .join(Collection, Collection.id == CollectionAllocation.collection_id)
            .where(CollectionAllocation.invoice_id == inv.id, Collection.status == CollectionStatus.CONFIRMED)
        )).scalar_one()
        inc_tax = inv.amount_inc_tax or 0
        outstanding = float(inc_tax) - float(collected)
        if outstanding <= 0:
            continue
        issue_date = inv.issue_date
        age_days = (today - issue_date).days if issue_date else 0
        if age_days <= 30:
            bucket = "0-30天"
        elif age_days <= 60:
            bucket = "31-60天"
        elif age_days <= 90:
            bucket = "61-90天"
        else:
            bucket = "90天+"
        rows.append({
            "invoice_no": inv.invoice_no,
            "project_code": proj.internal_project_code,
            "issue_date": issue_date.isoformat() if issue_date else None,
            "amount_inc_tax": str(inc_tax),
            "collected": str(collected),
            "outstanding": str(outstanding),
            "age_days": age_days,
            "aging_bucket": bucket,
        })
    return rows
