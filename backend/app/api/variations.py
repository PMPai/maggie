from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser
from app.models.variation import Variation, VariationStatus, VariationType
from app.schemas.variation import VariationCreate, VariationResponse
from app.models.approval import AuditLog

router = APIRouter(prefix="/api/variations", tags=["variations"])


@router.post("", response_model=VariationResponse)
async def create_variation(req: VariationCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    variation = Variation(
        organization_id=current.organization_id,
        project_id=req.project_id, contract_id=req.contract_id, contract_item_id=req.contract_item_id,
        variation_no=req.variation_no, variation_type=VariationType(req.variation_type),
        description=req.description, reason=req.reason,
        amount_ex_tax=req.amount_ex_tax, tax_amount=req.tax_amount, amount_inc_tax=req.amount_inc_tax,
        quantity_delta=req.quantity_delta, effective_date=req.effective_date,
        source_document_id=req.source_document_id,
        created_by=current.user.id, updated_by=current.user.id,
    )
    db.add(variation)
    await db.commit()
    await db.refresh(variation)
    return VariationResponse(
        id=str(variation.id), project_id=str(variation.project_id), contract_id=str(variation.contract_id),
        contract_item_id=str(variation.contract_item_id) if variation.contract_item_id else None,
        variation_no=variation.variation_no, variation_type=variation.variation_type.value,
        description=variation.description, reason=variation.reason,
        amount_ex_tax=variation.amount_ex_tax, tax_amount=variation.tax_amount, amount_inc_tax=variation.amount_inc_tax,
        quantity_delta=variation.quantity_delta, effective_date=variation.effective_date,
        status=variation.status.value,
        approved_by=str(variation.approved_by) if variation.approved_by else None,
        approved_at=variation.approved_at,
    )


@router.get("", response_model=list[VariationResponse])
async def list_variations(project_id: str = Query(None), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(Variation).where(Variation.organization_id == current.organization_id, Variation.deleted_at.is_(None))
    if project_id:
        stmt = stmt.where(Variation.project_id == project_id)
    result = await db.execute(stmt)
    return [VariationResponse(
        id=str(v.id), project_id=str(v.project_id), contract_id=str(v.contract_id),
        contract_item_id=str(v.contract_item_id) if v.contract_item_id else None,
        variation_no=v.variation_no, variation_type=v.variation_type.value,
        description=v.description, reason=v.reason,
        amount_ex_tax=v.amount_ex_tax, tax_amount=v.tax_amount, amount_inc_tax=v.amount_inc_tax,
        quantity_delta=v.quantity_delta, effective_date=v.effective_date,
        status=v.status.value,
        approved_by=str(v.approved_by) if v.approved_by else None,
        approved_at=v.approved_at,
    ) for v in result.scalars().all()]


@router.get("/{variation_id}", response_model=VariationResponse)
async def get_variation(variation_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Variation).where(Variation.id == variation_id, Variation.organization_id == current.organization_id, Variation.deleted_at.is_(None))
    )
    v = result.scalars().first()
    if not v:
        raise HTTPException(status_code=404, detail="Variation not found")
    return VariationResponse(
        id=str(v.id), project_id=str(v.project_id), contract_id=str(v.contract_id),
        contract_item_id=str(v.contract_item_id) if v.contract_item_id else None,
        variation_no=v.variation_no, variation_type=v.variation_type.value,
        description=v.description, reason=v.reason,
        amount_ex_tax=v.amount_ex_tax, tax_amount=v.tax_amount, amount_inc_tax=v.amount_inc_tax,
        quantity_delta=v.quantity_delta, effective_date=v.effective_date,
        status=v.status.value,
        approved_by=str(v.approved_by) if v.approved_by else None,
        approved_at=v.approved_at,
    )


@router.post("/{variation_id}/approve", response_model=VariationResponse)
async def approve_variation(variation_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Variation).where(Variation.id == variation_id, Variation.organization_id == current.organization_id, Variation.deleted_at.is_(None))
    )
    v = result.scalars().first()
    if not v:
        raise HTTPException(status_code=404, detail="Variation not found")
    v.status = VariationStatus.APPROVED
    v.approved_by = current.user.id
    from datetime import date
    v.approved_at = date.today()
    v.updated_by = current.user.id
    db.add(AuditLog(
        organization_id=current.organization_id,
        user_id=current.user.id,
        action="APPROVE",
        resource_type="variation",
        resource_id=str(v.id),
        detail={"variation_no": v.variation_no},
    ))
    await db.commit()
    await db.refresh(v)
    return VariationResponse(
        id=str(v.id), project_id=str(v.project_id), contract_id=str(v.contract_id),
        contract_item_id=str(v.contract_item_id) if v.contract_item_id else None,
        variation_no=v.variation_no, variation_type=v.variation_type.value,
        description=v.description, reason=v.reason,
        amount_ex_tax=v.amount_ex_tax, tax_amount=v.tax_amount, amount_inc_tax=v.amount_inc_tax,
        quantity_delta=v.quantity_delta, effective_date=v.effective_date,
        status=v.status.value,
        approved_by=str(v.approved_by) if v.approved_by else None,
        approved_at=v.approved_at,
    )


@router.post("/{variation_id}/reject", response_model=VariationResponse)
async def reject_variation(variation_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Variation).where(Variation.id == variation_id, Variation.organization_id == current.organization_id, Variation.deleted_at.is_(None))
    )
    v = result.scalars().first()
    if not v:
        raise HTTPException(status_code=404, detail="Variation not found")
    v.status = VariationStatus.REJECTED
    v.updated_by = current.user.id
    db.add(AuditLog(
        organization_id=current.organization_id,
        user_id=current.user.id,
        action="REJECT",
        resource_type="variation",
        resource_id=str(v.id),
        detail={"variation_no": v.variation_no},
    ))
    await db.commit()
    await db.refresh(v)
    return VariationResponse(
        id=str(v.id), project_id=str(v.project_id), contract_id=str(v.contract_id),
        contract_item_id=str(v.contract_item_id) if v.contract_item_id else None,
        variation_no=v.variation_no, variation_type=v.variation_type.value,
        description=v.description, reason=v.reason,
        amount_ex_tax=v.amount_ex_tax, tax_amount=v.tax_amount, amount_inc_tax=v.amount_inc_tax,
        quantity_delta=v.quantity_delta, effective_date=v.effective_date,
        status=v.status.value,
        approved_by=str(v.approved_by) if v.approved_by else None,
        approved_at=v.approved_at,
    )
