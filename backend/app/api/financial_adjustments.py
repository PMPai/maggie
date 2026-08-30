import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser, require_project_member
from app.models.financial_adjustment import FinancialAdjustment
from app.schemas.financial_adjustment import FinancialAdjustmentCreate, FinancialAdjustmentResponse
from app.models.approval import AuditLog

router = APIRouter(prefix="/api/financial-adjustments", tags=["financial-adjustments"])


def _to_response(adj: FinancialAdjustment) -> FinancialAdjustmentResponse:
    return FinancialAdjustmentResponse(
        id=str(adj.id), project_id=str(adj.project_id), adjustment_no=adj.adjustment_no,
        adjustment_type=adj.adjustment_type,
        invoice_id=str(adj.invoice_id) if adj.invoice_id else None,
        collection_id=str(adj.collection_id) if adj.collection_id else None,
        amount=adj.amount, description=adj.description, reason=adj.reason,
        status=adj.status, approved_by=str(adj.approved_by) if adj.approved_by else None,
        approved_at=adj.approved_at,
    )


@router.post("", response_model=FinancialAdjustmentResponse)
async def create_adjustment(req: FinancialAdjustmentCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pid = uuid.UUID(req.project_id)
    await require_project_member(pid, current, db)

    adj = FinancialAdjustment(
        project_id=pid,
        adjustment_no=req.adjustment_no, adjustment_type=req.adjustment_type,
        invoice_id=uuid.UUID(req.invoice_id) if req.invoice_id else None,
        collection_id=uuid.UUID(req.collection_id) if req.collection_id else None,
        amount=req.amount, description=req.description, reason=req.reason,
        status="PENDING", created_by=current.id, updated_by=current.id,
    )
    db.add(adj)
    await db.commit()
    await db.refresh(adj)
    return _to_response(adj)


@router.get("", response_model=list[FinancialAdjustmentResponse])
async def list_adjustments(project_id: str = Query(...), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pid = uuid.UUID(project_id)
    await require_project_member(pid, current, db)
    result = await db.execute(
        select(FinancialAdjustment).where(FinancialAdjustment.project_id == pid, FinancialAdjustment.deleted_at.is_(None))
    )
    return [_to_response(a) for a in result.scalars().all()]


@router.get("/{adjustment_id}", response_model=FinancialAdjustmentResponse)
async def get_adjustment(adjustment_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    aid = uuid.UUID(adjustment_id)
    result = await db.execute(select(FinancialAdjustment).where(FinancialAdjustment.id == aid))
    adj = result.scalar_one_or_none()
    if not adj:
        raise HTTPException(status_code=404, detail="Adjustment not found")
    await require_project_member(adj.project_id, current, db)
    return _to_response(adj)


@router.post("/{adjustment_id}/approve", response_model=FinancialAdjustmentResponse)
async def approve_adjustment(adjustment_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    aid = uuid.UUID(adjustment_id)
    result = await db.execute(select(FinancialAdjustment).where(FinancialAdjustment.id == aid))
    adj = result.scalar_one_or_none()
    if not adj:
        raise HTTPException(status_code=404, detail="Adjustment not found")
    await require_project_member(adj.project_id, current, db)
    if adj.status != "PENDING":
        raise HTTPException(status_code=400, detail="Only pending adjustments can be approved")

    adj.status = "APPROVED"
    adj.approved_by = current.id
    adj.approved_at = date.today()
    adj.updated_by = current.id
    db.add(AuditLog(
        user_id=current.id,
        action="APPROVE",
        resource_type="financial_adjustment",
        resource_id=str(adj.id),
        detail={"adjustment_no": adj.adjustment_no},
    ))
    await db.commit()
    await db.refresh(adj)
    return _to_response(adj)
