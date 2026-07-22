import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser, require_project_member
from app.models.billing import PaymentApplication, PaymentApplicationLine, ApplicationStatus
from app.models.contract import Contract, ContractVersion, ContractItem, PaymentRule, ContractVersionStatus
from app.services.calc_engine import (
    ItemInput, LineInput, RuleInput, calc_line_current, calc_application,
    check_quantity_limit, OverclaimError, TaxMode, RoundingPolicy, CalculationMethod,
)
from app.services.approval_service import submit_application, approve_application, post_application
from app.schemas.billing import (
    ApplicationCreate, ApplicationResponse, ApplicationLineCreate,
    ApplicationLineResponse, PostRequest,
)
from app.models.identity import UserRoleEnum

router = APIRouter(prefix="/api/payment-applications", tags=["payment-applications"])


@router.post("", response_model=ApplicationResponse)
async def create_application(req: ApplicationCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pid = uuid.UUID(req.project_id)
    await require_project_member(pid, current, db)
    cid = uuid.UUID(req.contract_id)

    # Get contract + active version
    result = await db.execute(select(Contract).where(Contract.id == cid))
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if not contract.active_version_id:
        raise HTTPException(status_code=400, detail="Contract has no approved version")

    app = PaymentApplication(
        organization_id=current.organization_id, project_id=pid, contract_id=cid,
        contract_version_id=contract.active_version_id, application_no=req.application_no,
        period_no=req.period_no, period_start=req.period_start, period_end=req.period_end,
        application_date=req.application_date, currency=contract.currency,
        created_by=current.user.id, updated_by=current.user.id,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return ApplicationResponse(
        id=str(app.id), project_id=str(app.project_id), contract_id=str(app.contract_id),
        application_no=app.application_no, period_no=app.period_no, status=app.status,
        gross_completed_amount=app.gross_completed_amount, retention_held_amount=app.retention_held_amount,
        retention_released_amount=app.retention_released_amount, deduction_amount=app.deduction_amount,
        taxable_amount=app.taxable_amount, tax_amount=app.tax_amount, invoice_amount=app.invoice_amount,
    )


@router.post("/{app_id}/lines", response_model=ApplicationLineResponse)
async def add_line(app_id: str, req: ApplicationLineCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    aid = uuid.UUID(app_id)
    result = await db.execute(select(PaymentApplication).where(PaymentApplication.id == aid))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.status != ApplicationStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Cannot add lines to non-draft application")
    await require_project_member(app.project_id, current, db)

    # Get contract item snapshot
    item_id = uuid.UUID(req.contract_item_id)
    result = await db.execute(select(ContractItem).where(ContractItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Contract item not found")

    # Get retention rules
    rules_result = await db.execute(
        select(PaymentRule).where(PaymentRule.contract_version_id == app.contract_version_id, PaymentRule.is_active == True)
    )
    rules = rules_result.scalars().all()
    rule_inputs = [RuleInput(rule_type=r.rule_type, rate=r.rate, calculation_base=r.calculation_base, contract_item_id=str(r.contract_item_id) if r.contract_item_id else None) for r in rules]

    # Get contract for tax info
    result = await db.execute(select(Contract).where(Contract.id == app.contract_id))
    contract = result.scalar_one()

    # Calculate
    item_input = ItemInput(
        item_id=str(item.id), calculation_method=CalculationMethod(item.calculation_method),
        unit_price=item.unit_price, contract_quantity=item.contract_quantity,
        is_heading=item.is_heading, is_billable=item.is_billable,
        retention_applicable=item.retention_applicable, line_amount=item.line_amount,
    )
    line_input = LineInput(
        contract_item_id=str(item.id), previous_approved_quantity=Decimal("0"),
        current_claimed_quantity=req.current_claimed_quantity, current_approved_quantity=req.current_approved_quantity,
        unit_price_snapshot=item.unit_price, direct_amount=req.direct_amount,
        user_explanation=req.user_explanation or "",
    )

    # Check quantity limit — include approved variations
    try:
        from app.services.variation_service import get_approved_variation_qty
        approved_var_qty = await get_approved_variation_qty(item_id, db)
        check_quantity_limit(item.contract_quantity, approved_var_qty, Decimal("0"), req.current_approved_quantity)
    except OverclaimError as e:
        raise HTTPException(status_code=400, detail=str(e))

    line_result = calc_line_current(
        item_input, line_input, rule_inputs, contract.tax_rate,
        TaxMode(contract.tax_mode), RoundingPolicy(contract.rounding_policy), contract.rounding_granularity,
    )

    line = PaymentApplicationLine(
        organization_id=current.organization_id, payment_application_id=aid,
        contract_item_id=item_id, contract_version_id=app.contract_version_id,
        description_snapshot=item.source_description, unit_snapshot=item.unit,
        unit_price_snapshot=item.unit_price, previous_approved_quantity=Decimal("0"),
        current_claimed_quantity=req.current_claimed_quantity, current_approved_quantity=req.current_approved_quantity,
        cumulative_approved_quantity=line_result.cumulative_approved_quantity,
        current_completed_amount=line_result.current_completed_amount,
        retention_rate=Decimal("0.10") if item.retention_applicable else Decimal("0"),
        retention_held=line_result.retention_held, taxable_amount=line_result.taxable_amount,
        tax_amount=line_result.tax_amount, net_amount=line_result.net_amount,
        calculation_method=item.calculation_method, user_explanation=req.user_explanation,
        validation_status="VALID" if not line_result.validation_issues else "INVALID",
        created_by=current.user.id, updated_by=current.user.id,
    )
    db.add(line)
    await db.commit()
    await db.refresh(line)
    return ApplicationLineResponse(
        id=str(line.id), contract_item_id=str(line.contract_item_id),
        description_snapshot=line.description_snapshot, unit_snapshot=line.unit_snapshot,
        unit_price_snapshot=line.unit_price_snapshot, previous_approved_quantity=line.previous_approved_quantity,
        current_claimed_quantity=line.current_claimed_quantity, current_approved_quantity=line.current_approved_quantity,
        cumulative_approved_quantity=line.cumulative_approved_quantity,
        current_completed_amount=line.current_completed_amount, retention_held=line.retention_held,
        taxable_amount=line.taxable_amount, tax_amount=line.tax_amount, net_amount=line.net_amount,
        validation_status=line.validation_status,
    )


@router.get("/{app_id}/lines", response_model=list[ApplicationLineResponse])
async def list_lines(app_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    aid = uuid.UUID(app_id)
    result = await db.execute(select(PaymentApplication).where(PaymentApplication.id == aid))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    await require_project_member(app.project_id, current, db)
    result = await db.execute(select(PaymentApplicationLine).where(PaymentApplicationLine.payment_application_id == aid))
    return [ApplicationLineResponse(
        id=str(l.id), contract_item_id=str(l.contract_item_id),
        description_snapshot=l.description_snapshot, unit_snapshot=l.unit_snapshot,
        unit_price_snapshot=l.unit_price_snapshot, previous_approved_quantity=l.previous_approved_quantity,
        current_claimed_quantity=l.current_claimed_quantity, current_approved_quantity=l.current_approved_quantity,
        cumulative_approved_quantity=l.cumulative_approved_quantity,
        current_completed_amount=l.current_completed_amount, retention_held=l.retention_held,
        taxable_amount=l.taxable_amount, tax_amount=l.tax_amount, net_amount=l.net_amount,
        validation_status=l.validation_status,
    ) for l in result.scalars().all()]


@router.post("/{app_id}/submit", response_model=ApplicationResponse)
async def submit(app_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    aid = uuid.UUID(app_id)
    result = await db.execute(select(PaymentApplication).where(PaymentApplication.id == aid))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    await require_project_member(app.project_id, current, db)
    return await submit_application(aid, db, current.user.id, current.organization_id)


@router.post("/{app_id}/approve", response_model=ApplicationResponse)
async def approve(app_id: str, step: str = Query(...), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    aid = uuid.UUID(app_id)
    result = await db.execute(select(PaymentApplication).where(PaymentApplication.id == aid))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    await require_project_member(app.project_id, current, db)
    return await approve_application(aid, step, db, current.user.id, current.organization_id)


@router.post("/{app_id}/post", response_model=ApplicationResponse)
async def post(app_id: str, req: PostRequest, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    aid = uuid.UUID(app_id)
    result = await db.execute(select(PaymentApplication).where(PaymentApplication.id == aid))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    await require_project_member(app.project_id, current, db)
    return await post_application(aid, req.action_id, db, current.user.id, current.organization_id)


@router.get("/{app_id}", response_model=ApplicationResponse)
async def get_application(app_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    aid = uuid.UUID(app_id)
    result = await db.execute(select(PaymentApplication).where(PaymentApplication.id == aid))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    await require_project_member(app.project_id, current, db)
    return ApplicationResponse(
        id=str(app.id), project_id=str(app.project_id), contract_id=str(app.contract_id),
        application_no=app.application_no, period_no=app.period_no, status=app.status,
        gross_completed_amount=app.gross_completed_amount, retention_held_amount=app.retention_held_amount,
        retention_released_amount=app.retention_released_amount, deduction_amount=app.deduction_amount,
        taxable_amount=app.taxable_amount, tax_amount=app.tax_amount, invoice_amount=app.invoice_amount,
    )


@router.get("", response_model=list[ApplicationResponse])
async def list_applications(project_id: str = Query(...), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pid = uuid.UUID(project_id)
    await require_project_member(pid, current, db)
    result = await db.execute(
        select(PaymentApplication).where(PaymentApplication.project_id == pid, PaymentApplication.deleted_at.is_(None))
    )
    return [ApplicationResponse(
        id=str(a.id), project_id=str(a.project_id), contract_id=str(a.contract_id),
        application_no=a.application_no, period_no=a.period_no, status=a.status,
        gross_completed_amount=a.gross_completed_amount, retention_held_amount=a.retention_held_amount,
        retention_released_amount=a.retention_released_amount, deduction_amount=a.deduction_amount,
        taxable_amount=a.taxable_amount, tax_amount=a.tax_amount, invoice_amount=a.invoice_amount,
    ) for a in result.scalars().all()]
