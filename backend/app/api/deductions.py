from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser
from app.models.deduction import Deduction, DeductionStatus, DeductionType, TaxTreatment
from app.schemas.deduction import DeductionCreate, DeductionResponse

router = APIRouter(prefix="/api/deductions", tags=["deductions"])


@router.post("", response_model=DeductionResponse)
async def create_deduction(req: DeductionCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    deduction = Deduction(
        organization_id=current.organization_id,
        project_id=req.project_id, contract_id=req.contract_id, payment_application_id=req.payment_application_id,
        deduction_no=req.deduction_no, deduction_type=DeductionType(req.deduction_type),
        description=req.description, reason=req.reason, amount=req.amount,
        tax_treatment=TaxTreatment(req.tax_treatment), tax_amount=req.tax_amount, effective_date=req.effective_date,
        created_by=current.user.id, updated_by=current.user.id,
    )
    db.add(deduction)
    await db.commit()
    await db.refresh(deduction)
    return DeductionResponse(
        id=str(deduction.id), project_id=str(deduction.project_id), contract_id=str(deduction.contract_id),
        payment_application_id=str(deduction.payment_application_id) if deduction.payment_application_id else None,
        deduction_no=deduction.deduction_no, deduction_type=deduction.deduction_type.value,
        description=deduction.description, reason=deduction.reason, amount=deduction.amount,
        tax_treatment=deduction.tax_treatment.value, tax_amount=deduction.tax_amount,
        effective_date=deduction.effective_date, status=deduction.status.value,
        approved_by=str(deduction.approved_by) if deduction.approved_by else None,
        approved_at=deduction.approved_at,
    )


@router.get("", response_model=list[DeductionResponse])
async def list_deductions(project_id: str = Query(None), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(Deduction).where(Deduction.organization_id == current.organization_id, Deduction.deleted_at.is_(None))
    if project_id:
        stmt = stmt.where(Deduction.project_id == project_id)
    result = await db.execute(stmt)
    return [DeductionResponse(
        id=str(d.id), project_id=str(d.project_id), contract_id=str(d.contract_id),
        payment_application_id=str(d.payment_application_id) if d.payment_application_id else None,
        deduction_no=d.deduction_no, deduction_type=d.deduction_type.value,
        description=d.description, reason=d.reason, amount=d.amount,
        tax_treatment=d.tax_treatment.value, tax_amount=d.tax_amount,
        effective_date=d.effective_date, status=d.status.value,
        approved_by=str(d.approved_by) if d.approved_by else None,
        approved_at=d.approved_at,
    ) for d in result.scalars().all()]


@router.get("/{deduction_id}", response_model=DeductionResponse)
async def get_deduction(deduction_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Deduction).where(Deduction.id == deduction_id, Deduction.organization_id == current.organization_id, Deduction.deleted_at.is_(None))
    )
    d = result.scalars().first()
    if not d:
        raise HTTPException(status_code=404, detail="Deduction not found")
    return DeductionResponse(
        id=str(d.id), project_id=str(d.project_id), contract_id=str(d.contract_id),
        payment_application_id=str(d.payment_application_id) if d.payment_application_id else None,
        deduction_no=d.deduction_no, deduction_type=d.deduction_type.value,
        description=d.description, reason=d.reason, amount=d.amount,
        tax_treatment=d.tax_treatment.value, tax_amount=d.tax_amount,
        effective_date=d.effective_date, status=d.status.value,
        approved_by=str(d.approved_by) if d.approved_by else None,
        approved_at=d.approved_at,
    )


@router.post("/{deduction_id}/approve", response_model=DeductionResponse)
async def approve_deduction(deduction_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Deduction).where(Deduction.id == deduction_id, Deduction.organization_id == current.organization_id, Deduction.deleted_at.is_(None))
    )
    d = result.scalars().first()
    if not d:
        raise HTTPException(status_code=404, detail="Deduction not found")
    d.status = DeductionStatus.APPROVED
    d.approved_by = current.user.id
    from datetime import date
    d.approved_at = date.today()
    d.updated_by = current.user.id
    await db.commit()
    await db.refresh(d)
    return DeductionResponse(
        id=str(d.id), project_id=str(d.project_id), contract_id=str(d.contract_id),
        payment_application_id=str(d.payment_application_id) if d.payment_application_id else None,
        deduction_no=d.deduction_no, deduction_type=d.deduction_type.value,
        description=d.description, reason=d.reason, amount=d.amount,
        tax_treatment=d.tax_treatment.value, tax_amount=d.tax_amount,
        effective_date=d.effective_date, status=d.status.value,
        approved_by=str(d.approved_by) if d.approved_by else None,
        approved_at=d.approved_at,
    )
