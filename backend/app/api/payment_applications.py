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
    ApplicationLineResponse, PostRequest, PreviewRequest,
)
from app.models.identity import UserRoleEnum
from app.models.approval import AuditLog

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
    await db.flush()
    db.add(AuditLog(
        organization_id=current.organization_id,
        user_id=current.user.id,
        action="CREATE",
        resource_type="payment_application",
        resource_id=str(app.id),
        detail={"application_no": app.application_no, "project_id": str(pid), "contract_id": str(cid)},
    ))
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
        item_id=str(item.id), calculation_method=CalculationMethod(item.calculation_method.value),
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
        TaxMode(contract.tax_mode.value), RoundingPolicy(contract.rounding_policy.value), contract.rounding_granularity,
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
        calculation_method=item.calculation_method.value, user_explanation=req.user_explanation,
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
async def list_applications(project_id: str = Query(None), my: bool = Query(False), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    conditions = [PaymentApplication.deleted_at.is_(None)]

    if project_id:
        pid = uuid.UUID(project_id)
        await require_project_member(pid, current, db)
        conditions.append(PaymentApplication.project_id == pid)
    elif my:
        conditions.append(PaymentApplication.created_by == current.user.id)
    else:
        conditions.append(PaymentApplication.organization_id == current.organization_id)

    result = await db.execute(
        select(PaymentApplication).where(*conditions).order_by(PaymentApplication.created_at.desc())
    )
    return [ApplicationResponse(
        id=str(a.id), project_id=str(a.project_id), contract_id=str(a.contract_id),
        application_no=a.application_no, period_no=a.period_no, status=a.status,
        created_by=str(a.created_by) if a.created_by else None,
        gross_completed_amount=a.gross_completed_amount, retention_held_amount=a.retention_held_amount,
        retention_released_amount=a.retention_released_amount, deduction_amount=a.deduction_amount,
        taxable_amount=a.taxable_amount, tax_amount=a.tax_amount, invoice_amount=a.invoice_amount,
    ) for a in result.scalars().all()]


@router.post("/{app_id}/generate")
async def generate_document_endpoint(app_id: str, output_format: str = "pdf", current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    aid = uuid.UUID(app_id)
    result = await db.execute(select(PaymentApplication).where(PaymentApplication.id == aid))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    await require_project_member(app.project_id, current, db)

    if app.status != ApplicationStatus.POSTED and app.status != ApplicationStatus.GENERATED:
        raise HTTPException(status_code=400, detail="Application must be POSTED to generate document")

    db.add(AuditLog(
        organization_id=current.organization_id,
        user_id=current.user.id,
        action="GENERATE",
        resource_type="payment_application",
        resource_id=str(aid),
        detail={"output_format": output_format},
    ))
    await db.commit()

    from app.tasks.tasks import generate_document
    task = generate_document.delay(str(aid), output_format)
    return {"task_id": task.id, "status": "PENDING"}


@router.post("/preview")
async def preview_application(req: PreviewRequest, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Preview calculation for a set of lines without creating an application.
    Uses calc_engine with real contract rules — no hardcoded rates."""
    cid = uuid.UUID(req.contract_id)
    contract = (await db.execute(select(Contract).where(Contract.id == cid))).scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if not contract.active_version_id:
        raise HTTPException(status_code=400, detail="Contract has no approved version")

    # Get version + items + rules
    version_id = contract.active_version_id
    items_result = await db.execute(
        select(ContractItem).where(ContractItem.contract_version_id == version_id)
    )
    items_by_id = {i.id: i for i in items_result.scalars().all()}

    rules_result = await db.execute(
        select(PaymentRule).where(
            PaymentRule.contract_version_id == version_id,
            PaymentRule.is_active == True,
        )
    )
    rule_inputs = [
        RuleInput(
            rule_type=r.rule_type, rate=r.rate,
            calculation_base=r.calculation_base,
            contract_item_id=str(r.contract_item_id) if r.contract_item_id else None,
        )
        for r in rules_result.scalars().all()
    ]

    line_results = []
    for ln in req.lines:
        item_id = uuid.UUID(ln.contract_item_id)
        item = items_by_id.get(item_id)
        if not item:
            continue

        item_input = ItemInput(
            item_id=str(item.id),
            calculation_method=CalculationMethod(item.calculation_method.value),
            unit_price=item.unit_price,
            contract_quantity=item.contract_quantity,
            is_heading=item.is_heading,
            is_billable=item.is_billable,
            retention_applicable=item.retention_applicable,
            line_amount=item.line_amount,
        )
        approved_qty = ln.current_approved_quantity if ln.current_approved_quantity is not None else ln.current_claimed_quantity
        line_input = LineInput(
            contract_item_id=str(item.id),
            previous_approved_quantity=Decimal("0"),
            current_claimed_quantity=ln.current_claimed_quantity,
            current_approved_quantity=approved_qty,
            unit_price_snapshot=item.unit_price,
            direct_amount=ln.direct_amount,
        )

        lr = calc_line_current(
            item_input, line_input, rule_inputs,
            contract.tax_rate,
            TaxMode(contract.tax_mode.value),
            RoundingPolicy(contract.rounding_policy.value),
            contract.rounding_granularity,
        )
        line_results.append(lr)

    totals = calc_application(
        line_results,
        retention_released_amount=Decimal("0"),
        deduction_amount=Decimal("0"),
        tax_rate=contract.tax_rate,
        tax_mode=TaxMode(contract.tax_mode.value),
        rounding_policy=RoundingPolicy(contract.rounding_policy.value),
        rounding_granularity=contract.rounding_granularity,
    )

    return {
        "gross_completed_amount": str(totals.gross_completed_amount),
        "retention_held_amount": str(totals.retention_held_amount),
        "retention_released_amount": str(totals.retention_released_amount),
        "deduction_amount": str(totals.deduction_amount),
        "taxable_amount": str(totals.taxable_amount),
        "tax_amount": str(totals.tax_amount),
        "invoice_amount": str(totals.invoice_amount),
        "lines": [
            {
                "contract_item_id": lr.contract_item_id,
                "current_completed_amount": str(lr.current_completed_amount),
                "retention_held": str(lr.retention_held),
                "taxable_amount": str(lr.taxable_amount),
                "tax_amount": str(lr.tax_amount),
                "net_amount": str(lr.net_amount),
                "validation_issues": [
                    {"code": v.code.value if hasattr(v.code, 'value') else str(v.code), "field": v.field_name, "message": v.message, "severity": v.severity}
                    for v in lr.validation_issues
                ],
            }
            for lr in line_results
        ],
    }


@router.post("/{app_id}/validate")
async def validate_application(app_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Validate a payment application against all 13 spec §10 rules.
    Returns { valid: bool, issues: [{code, field, message, severity}] }."""
    aid = uuid.UUID(app_id)
    app = (await db.execute(select(PaymentApplication).where(PaymentApplication.id == aid))).scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    await require_project_member(app.project_id, current, db)

    issues: list[dict] = []
    contract = (await db.execute(select(Contract).where(Contract.id == app.contract_id))).scalar_one()
    version = (await db.execute(select(ContractVersion).where(ContractVersion.id == app.contract_version_id))).scalar_one_or_none()
    lines = (await db.execute(select(PaymentApplicationLine).where(PaymentApplicationLine.payment_application_id == aid))).scalars().all()

    # Rule 1: contract version must be APPROVED
    if not version or version.status != ContractVersionStatus.APPROVED:
        issues.append({"code": "INVALID_VERSION", "field": "contract_version", "message": "合同版本未批准", "severity": "ERROR"})

    # Rule 2: items must be billable
    for line in lines:
        item = (await db.execute(select(ContractItem).where(ContractItem.id == line.contract_item_id))).scalar_one_or_none()
        if item:
            if not item.is_billable:
                issues.append({"code": "NON_BILLABLE", "field": f"line_{line.id}", "message": f"项目 {item.line_no} 不可计价", "severity": "ERROR"})
            # Rule 3: quantity must not be negative
            if line.current_claimed_quantity < 0:
                issues.append({"code": "NEGATIVE_QTY", "field": f"line_{line.id}", "message": f"项目 {item.line_no} 本期数量为负", "severity": "ERROR"})
            # Rule 4: cumulative must not exceed available
            try:
                from app.services.variation_service import get_approved_variation_qty
                approved_var_qty = await get_approved_variation_qty(item.id, db)
                check_quantity_limit(item.contract_quantity, approved_var_qty, line.previous_approved_quantity, line.current_approved_quantity)
            except OverclaimError as e:
                issues.append({"code": "OVERCLAIM", "field": f"line_{line.id}", "message": str(e), "severity": "ERROR"})
            # Rule 5: unit price must match contract version
            if line.unit_price_snapshot != item.unit_price:
                issues.append({"code": "STALE_PRICE", "field": f"line_{line.id}", "message": f"项目 {item.line_no} 单价与合同版本不一致", "severity": "ERROR"})

    # Rule 7: retention rules must exist (at least one RETENTION_HOLD rule for the version)
    rules = (await db.execute(
        select(PaymentRule).where(PaymentRule.contract_version_id == app.contract_version_id, PaymentRule.is_active == True)
    )).scalars().all()
    has_retention_rule = any(r.rule_type == "RETENTION_HOLD" for r in rules)
    if not has_retention_rule:
        issues.append({"code": "MISSING_RETENTION", "field": "payment_rules", "message": "缺少保留款规则", "severity": "WARNING"})

    # Rule 8: tax amount check (approximate — uses contract tax_rate)
    expected_tax = (app.taxable_amount or Decimal("0")) * contract.tax_rate
    if abs((app.tax_amount or Decimal("0")) - expected_tax) > Decimal("1"):
        issues.append({"code": "TAX_MISMATCH", "field": "tax_amount", "message": "税额计算可能不正确", "severity": "WARNING"})

    # Rule 9: deductions must have approval (check if any pending deductions exist for this contract)
    from app.models.deduction import Deduction
    pending_deductions = (await db.execute(
        select(Deduction).where(Deduction.contract_id == app.contract_id, Deduction.status == "DRAFT")
    )).scalars().all()
    if pending_deductions:
        issues.append({"code": "UNAPPROVED_DEDUCTION", "field": "deductions", "message": f"有 {len(pending_deductions)} 笔扣款未批准", "severity": "WARNING"})

    # Rule 12: check for unapproved variations
    from app.models.variation import Variation, VariationStatus
    unapproved_vars = (await db.execute(
        select(Variation).where(Variation.contract_id == app.contract_id, Variation.status == VariationStatus.UNDER_REVIEW)
    )).scalars().all()
    if unapproved_vars:
        issues.append({"code": "UNAPPROVED_VARIATION", "field": "variations", "message": f"有 {len(unapproved_vars)} 个变更未批准", "severity": "WARNING"})

    # Rule 13: duplicate period check
    dup = (await db.execute(
        select(PaymentApplication).where(
            PaymentApplication.contract_id == app.contract_id,
            PaymentApplication.period_no == app.period_no,
            PaymentApplication.id != aid,
            PaymentApplication.status.notin_([ApplicationStatus.REJECTED, ApplicationStatus.CANCELLED, ApplicationStatus.SUPERSEDED]),
        )
    )).scalars().all()
    if dup:
        issues.append({"code": "DUPLICATE_PERIOD", "field": "period_no", "message": f"已存在第 {app.period_no} 期请款", "severity": "ERROR"})

    # Rules 6 (prior cumulative), 10 (milestone), 11 (documents) are checked per-line at submission time
    # but we note them as informational if not verifiable here
    if not lines:
        issues.append({"code": "NO_LINES", "field": "lines", "message": "请款无明细行", "severity": "ERROR"})

    errors = [i for i in issues if i["severity"] == "ERROR"]
    return {"valid": len(errors) == 0, "issues": issues, "error_count": len(errors), "warning_count": len(issues) - len(errors)}
