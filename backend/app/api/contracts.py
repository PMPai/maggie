import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser, require_project_member
from app.models.contract import Contract, ContractVersion, ContractItem, PaymentRule, ContractVersionStatus
from app.models.approval import AuditLog
from app.schemas.contract import (
    ContractCreate, ContractResponse, ContractVersionCreate, ContractVersionResponse, ContractVersionPatch,
    ContractItemCreate, ContractItemResponse, ContractItemPatch, PaymentRuleCreate, PaymentRuleResponse,
    PricingSheetCreate, PricingSheetResponse,
)

router = APIRouter(prefix="/api/contracts", tags=["contracts"])


@router.post("/projects/{project_id}/pricing-sheets", response_model=PricingSheetResponse)
async def create_pricing_sheet(project_id: str, req: PricingSheetCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Create a 计价单 (pricing sheet) — a contract with a QUOTATION version."""
    pid = uuid.UUID(project_id)
    await require_project_member(pid, current, db)
    contract = Contract(
        project_id=pid,
        external_contract_no=req.external_contract_no or f"PS-{uuid.uuid4().hex[:8]}",
        contract_name=req.contract_name,
        currency=req.currency, tax_mode=req.tax_mode, tax_rate=req.tax_rate,
        rounding_policy="ROUND_HALF_UP", rounding_granularity=Decimal("1"),
        status="DRAFT",
        created_by=current.id, updated_by=current.id,
    )
    db.add(contract)
    await db.flush()
    version = ContractVersion(
        contract_id=contract.id, version_no=1,
        version_type="QUOTATION",
        status=ContractVersionStatus.DRAFT,
        amount_ex_tax=Decimal("0"), tax_amount=Decimal("0"), amount_inc_tax=Decimal("0"),
        created_by=current.id, updated_by=current.id,
    )
    db.add(version)
    contract.active_version_id = version.id
    await db.commit()
    await db.refresh(contract)
    await db.refresh(version)
    return PricingSheetResponse(
        contract_id=str(contract.id), version_id=str(version.id),
        project_id=str(contract.project_id), contract_name=contract.contract_name,
        status=version.status, version_type=version.version_type,
    )


@router.get("/projects/{project_id}/pricing-sheets", response_model=list[PricingSheetResponse])
async def list_pricing_sheets(project_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List all 计价单 (pricing sheets) for a project — contracts with QUOTATION versions."""
    pid = uuid.UUID(project_id)
    await require_project_member(pid, current, db)
    result = await db.execute(
        select(Contract, ContractVersion)
        .join(ContractVersion, Contract.active_version_id == ContractVersion.id)
        .where(Contract.project_id == pid, Contract.deleted_at.is_(None),
               ContractVersion.version_type == "QUOTATION")
        .order_by(Contract.created_at.desc())
    )
    rows = result.all()
    return [PricingSheetResponse(
        contract_id=str(c.id), version_id=str(v.id),
        project_id=str(c.project_id), contract_name=c.contract_name,
        status=v.status, version_type=v.version_type,
    ) for c, v in rows]


@router.post("", response_model=ContractResponse)
async def create_contract(req: ContractCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pid = uuid.UUID(req.project_id)
    await require_project_member(pid, current, db)
    contract = Contract(
        project_id=pid,
        external_contract_no=req.external_contract_no, contract_name=req.contract_name,
        customer_company_id=uuid.UUID(req.customer_company_id) if req.customer_company_id else None,
        contractor_company_id=uuid.UUID(req.contractor_company_id) if req.contractor_company_id else None,
        signed_date=req.signed_date, effective_date=req.effective_date,
        currency=req.currency, tax_mode=req.tax_mode, tax_rate=req.tax_rate,
        rounding_policy=req.rounding_policy, rounding_granularity=req.rounding_granularity,
        created_by=current.id, updated_by=current.id,
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    return ContractResponse(
        id=str(contract.id), project_id=str(contract.project_id),
        external_contract_no=contract.external_contract_no, contract_name=contract.contract_name,
        currency=contract.currency, tax_mode=contract.tax_mode, tax_rate=contract.tax_rate,
        original_amount_ex_tax=contract.original_amount_ex_tax, original_tax_amount=contract.original_tax_amount,
        original_amount_inc_tax=contract.original_amount_inc_tax, status=contract.status,
        active_version_id=str(contract.active_version_id) if contract.active_version_id else None,
    )


@router.get("", response_model=list[ContractResponse])
async def list_contracts(project_id: str = Query(...), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pid = uuid.UUID(project_id)
    await require_project_member(pid, current, db)
    result = await db.execute(
        select(Contract).where(Contract.project_id == pid, Contract.deleted_at.is_(None))
    )
    contracts = result.scalars().all()
    return [ContractResponse(
        id=str(c.id), project_id=str(c.project_id), external_contract_no=c.external_contract_no,
        contract_name=c.contract_name, currency=c.currency, tax_mode=c.tax_mode, tax_rate=c.tax_rate,
        original_amount_ex_tax=c.original_amount_ex_tax, original_tax_amount=c.original_tax_amount,
        original_amount_inc_tax=c.original_amount_inc_tax, status=c.status,
        active_version_id=str(c.active_version_id) if c.active_version_id else None,
    ) for c in contracts]


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(contract_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cid = uuid.UUID(contract_id)
    result = await db.execute(select(Contract).where(Contract.id == cid, Contract.deleted_at.is_(None)))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    await require_project_member(c.project_id, current, db)
    return ContractResponse(
        id=str(c.id), project_id=str(c.project_id), external_contract_no=c.external_contract_no,
        contract_name=c.contract_name, currency=c.currency, tax_mode=c.tax_mode, tax_rate=c.tax_rate,
        original_amount_ex_tax=c.original_amount_ex_tax, original_tax_amount=c.original_tax_amount,
        original_amount_inc_tax=c.original_amount_inc_tax, status=c.status,
        active_version_id=str(c.active_version_id) if c.active_version_id else None,
    )


@router.post("/{contract_id}/versions", response_model=ContractVersionResponse)
async def create_version(contract_id: str, req: ContractVersionCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cid = uuid.UUID(contract_id)
    result = await db.execute(select(Contract).where(Contract.id == cid))
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    await require_project_member(contract.project_id, current, db)

    max_version = await db.execute(select(func.max(ContractVersion.version_no)).where(ContractVersion.contract_id == cid))
    next_no = (max_version.scalar() or 0) + 1

    version = ContractVersion(
        contract_id=cid, version_no=next_no,
        version_type=req.version_type, effective_date=req.effective_date,
        amount_ex_tax=req.amount_ex_tax, tax_amount=req.tax_amount, amount_inc_tax=req.amount_inc_tax,
        change_reason=req.change_reason, created_by=current.id, updated_by=current.id,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return ContractVersionResponse(
        id=str(version.id), contract_id=str(version.contract_id), version_no=version.version_no,
        version_type=version.version_type, amount_ex_tax=version.amount_ex_tax,
        tax_amount=version.tax_amount, amount_inc_tax=version.amount_inc_tax,
        status=version.status, change_reason=version.change_reason,
        source_document_id=str(version.source_document_id) if version.source_document_id else None,
    )


@router.get("/{contract_id}/versions", response_model=list[ContractVersionResponse])
async def list_versions(contract_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cid = uuid.UUID(contract_id)
    result = await db.execute(select(Contract).where(Contract.id == cid))
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    await require_project_member(contract.project_id, current, db)
    result = await db.execute(
        select(ContractVersion).where(ContractVersion.contract_id == cid).order_by(ContractVersion.version_no)
    )
    versions = result.scalars().all()
    return [ContractVersionResponse(
        id=str(v.id), contract_id=str(v.contract_id), version_no=v.version_no,
        version_type=v.version_type, amount_ex_tax=v.amount_ex_tax, tax_amount=v.tax_amount,
        amount_inc_tax=v.amount_inc_tax, status=v.status, change_reason=v.change_reason,
        source_document_id=str(v.source_document_id) if v.source_document_id else None,
    ) for v in versions]


@router.post("/{contract_id}/versions/{version_id}/approve", response_model=ContractVersionResponse)
async def approve_version(contract_id: str, version_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from datetime import datetime, timezone
    cid = uuid.UUID(contract_id)
    vid = uuid.UUID(version_id)
    result = await db.execute(select(Contract).where(Contract.id == cid))
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    await require_project_member(contract.project_id, current, db)

    result = await db.execute(select(ContractVersion).where(ContractVersion.id == vid, ContractVersion.contract_id == cid))
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    if version.status not in (ContractVersionStatus.DRAFT, ContractVersionStatus.UNDER_REVIEW):
        raise HTTPException(status_code=400, detail=f"Cannot approve version in status {version.status}")

    # Supersede previous approved version
    await db.execute(
        select(ContractVersion).where(ContractVersion.contract_id == cid, ContractVersion.status == "APPROVED", ContractVersion.id != vid)
    )
    # Mark previous approved as SUPERSEDED
    prev_result = await db.execute(
        select(ContractVersion).where(ContractVersion.contract_id == cid, ContractVersion.status == "APPROVED", ContractVersion.id != vid)
    )
    for pv in prev_result.scalars().all():
        pv.status = ContractVersionStatus.SUPERSEDED

    version.status = ContractVersionStatus.APPROVED
    version.approved_by = current.id
    version.approved_at = datetime.now(timezone.utc)
    # Transition QUOTATION → SIGNED_CONTRACT on approval (计价单 → 合同)
    if version.version_type == "QUOTATION":
        version.version_type = "SIGNED_CONTRACT"
    contract.active_version_id = vid
    contract.original_amount_ex_tax = version.amount_ex_tax
    contract.original_tax_amount = version.tax_amount
    contract.original_amount_inc_tax = version.amount_inc_tax
    contract.status = "ACTIVE"

    # Auto-generate PLANNED collections from items with expected_payment_date
    from app.models.collection import Collection, CollectionStatus
    items_result = await db.execute(
        select(ContractItem).where(
            ContractItem.contract_version_id == vid,
            ContractItem.expected_payment_date.isnot(None),
            ContractItem.is_billable == True,
            ContractItem.is_heading == False,
        )
    )
    for item in items_result.scalars().all():
        col = Collection(
            project_id=contract.project_id, contract_id=cid,
            receipt_no=f"PLN-{cid.hex[:8]}-{item.id.hex[:8]}",
            receipt_date=item.expected_payment_date,
            amount_received=item.line_amount or Decimal("0"),
            status=CollectionStatus.PLANNED,
            created_by=current.id, updated_by=current.id,
        )
        db.add(col)

    await db.commit()
    await db.refresh(version)
    return ContractVersionResponse(
        id=str(version.id), contract_id=str(version.contract_id), version_no=version.version_no,
        version_type=version.version_type, amount_ex_tax=version.amount_ex_tax, tax_amount=version.tax_amount,
        amount_inc_tax=version.amount_inc_tax, status=version.status, change_reason=version.change_reason,
        source_document_id=str(version.source_document_id) if version.source_document_id else None,
    )


@router.patch("/contract-versions/{version_id}", response_model=ContractVersionResponse)
async def patch_contract_version(version_id: str, req: ContractVersionPatch, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    vid = uuid.UUID(version_id)
    result = await db.execute(select(ContractVersion).where(ContractVersion.id == vid))
    cv = result.scalar_one_or_none()
    if not cv:
        raise HTTPException(status_code=404, detail="Contract version not found")
    result = await db.execute(select(Contract).where(Contract.id == cv.contract_id))
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    await require_project_member(contract.project_id, current, db)
    if cv.status not in (ContractVersionStatus.DRAFT, ContractVersionStatus.UNDER_REVIEW):
        raise HTTPException(status_code=409, detail=f"Cannot modify version in status {cv.status}")

    updates = req.model_dump(exclude_unset=True)

    # Status transition validation: only DRAFT -> UNDER_REVIEW is allowed via PATCH.
    if "status" in updates:
        requested = updates["status"]
        if requested != ContractVersionStatus.UNDER_REVIEW.value:
            raise HTTPException(status_code=422, detail="PATCH may only transition status to UNDER_REVIEW")
        if cv.status != ContractVersionStatus.DRAFT:
            raise HTTPException(status_code=409, detail=f"Cannot submit version in status {cv.status}")

    if any(k in updates for k in ("amount_ex_tax", "tax_amount", "amount_inc_tax")):
        ex = Decimal(updates.get("amount_ex_tax", cv.amount_ex_tax))
        tax = Decimal(updates.get("tax_amount", cv.tax_amount))
        inc = Decimal(updates.get("amount_inc_tax", cv.amount_inc_tax))
        if ex + tax != inc:
            raise HTTPException(status_code=422, detail="amount_ex_tax + tax_amount must equal amount_inc_tax")

    applied_fields = []
    for field, value in updates.items():
        if field == "status":
            cv.status = ContractVersionStatus.UNDER_REVIEW
            applied_fields.append("status")
        elif hasattr(cv, field):
            setattr(cv, field, value)
            applied_fields.append(field)
    cv.updated_by = current.id

    db.add(AuditLog(
        user_id=current.id,
        resource_type="contract_version", resource_id=str(vid),
        action="PATCH", detail={"version_no": cv.version_no, "fields": applied_fields},
    ))
    await db.commit()
    await db.refresh(cv)
    return ContractVersionResponse(
        id=str(cv.id), contract_id=str(cv.contract_id), version_no=cv.version_no,
        version_type=cv.version_type, amount_ex_tax=cv.amount_ex_tax,
        tax_amount=cv.tax_amount, amount_inc_tax=cv.amount_inc_tax,
        status=cv.status, change_reason=cv.change_reason,
        source_document_id=str(cv.source_document_id) if cv.source_document_id else None,
    )


@router.post("/contract-versions/{version_id}/items", response_model=ContractItemResponse)
async def create_item(version_id: str, req: ContractItemCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    vid = uuid.UUID(version_id)
    result = await db.execute(select(ContractVersion).where(ContractVersion.id == vid))
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    result = await db.execute(select(Contract).where(Contract.id == version.contract_id))
    contract = result.scalar_one()
    await require_project_member(contract.project_id, current, db)

    item = ContractItem(
        contract_version_id=vid,
        parent_item_id=uuid.UUID(req.parent_item_id) if req.parent_item_id else None,
        line_no=req.line_no, item_code=req.item_code, source_description=req.source_description,
        normalized_description=req.normalized_description, unit=req.unit,
        contract_quantity=req.contract_quantity, unit_price=req.unit_price,
        unit_cost=req.unit_cost, line_amount=req.line_amount,
        calculation_method=req.calculation_method, tax_category=req.tax_category,
        retention_applicable=req.retention_applicable, is_heading=req.is_heading, is_billable=req.is_billable,
        sort_order=req.sort_order, expected_payment_date=req.expected_payment_date,
        created_by=current.id, updated_by=current.id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return ContractItemResponse(
        id=str(item.id), contract_version_id=str(item.contract_version_id),
        parent_item_id=str(item.parent_item_id) if item.parent_item_id else None,
        line_no=item.line_no, item_code=item.item_code, source_description=item.source_description,
        unit=item.unit, contract_quantity=item.contract_quantity, unit_price=item.unit_price,
        unit_cost=item.unit_cost, line_amount=item.line_amount, calculation_method=item.calculation_method,
        is_heading=item.is_heading, is_billable=item.is_billable,
        retention_applicable=item.retention_applicable, sort_order=item.sort_order,
        expected_payment_date=item.expected_payment_date,
    )


@router.get("/contract-versions/{version_id}/items", response_model=list[ContractItemResponse])
async def list_items(version_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    vid = uuid.UUID(version_id)
    result = await db.execute(select(ContractVersion).where(ContractVersion.id == vid))
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    result = await db.execute(select(Contract).where(Contract.id == version.contract_id))
    contract = result.scalar_one()
    await require_project_member(contract.project_id, current, db)
    result = await db.execute(
        select(ContractItem).where(ContractItem.contract_version_id == vid).order_by(ContractItem.sort_order)
    )
    return [ContractItemResponse(
        id=str(i.id), contract_version_id=str(i.contract_version_id),
        parent_item_id=str(i.parent_item_id) if i.parent_item_id else None,
        line_no=i.line_no, item_code=i.item_code, source_description=i.source_description,
        unit=i.unit, contract_quantity=i.contract_quantity, unit_price=i.unit_price,
        unit_cost=i.unit_cost, line_amount=i.line_amount, calculation_method=i.calculation_method,
        is_heading=i.is_heading, is_billable=i.is_billable, retention_applicable=i.retention_applicable,
        sort_order=i.sort_order, expected_payment_date=i.expected_payment_date,
    ) for i in result.scalars().all()]


@router.patch("/contract-versions/{version_id}/items/{item_id}", response_model=ContractItemResponse)
async def patch_item(version_id: str, item_id: str, req: ContractItemPatch,
                     current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    vid = uuid.UUID(version_id)
    iid = uuid.UUID(item_id)
    result = await db.execute(select(ContractVersion).where(ContractVersion.id == vid))
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    if version.status not in (ContractVersionStatus.DRAFT, ContractVersionStatus.UNDER_REVIEW):
        raise HTTPException(status_code=409, detail=f"Cannot modify items of version in status {version.status}")
    result = await db.execute(select(Contract).where(Contract.id == version.contract_id))
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    await require_project_member(contract.project_id, current, db)
    result = await db.execute(select(ContractItem).where(ContractItem.id == iid, ContractItem.contract_version_id == vid))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    updates = req.model_dump(exclude_unset=True)
    applied_fields = []
    for field, value in updates.items():
        if hasattr(item, field):
            setattr(item, field, value)
            applied_fields.append(field)
    item.updated_by = current.id

    db.add(AuditLog(
        user_id=current.id,
        resource_type="contract_item", resource_id=str(iid),
        action="PATCH", detail={"version_id": str(vid), "fields": applied_fields},
    ))
    await db.commit()
    await db.refresh(item)
    return ContractItemResponse(
        id=str(item.id), contract_version_id=str(item.contract_version_id),
        parent_item_id=str(item.parent_item_id) if item.parent_item_id else None,
        line_no=item.line_no, item_code=item.item_code, source_description=item.source_description,
        unit=item.unit, contract_quantity=item.contract_quantity, unit_price=item.unit_price,
        unit_cost=item.unit_cost, line_amount=item.line_amount, calculation_method=item.calculation_method,
        is_heading=item.is_heading, is_billable=item.is_billable,
        retention_applicable=item.retention_applicable, sort_order=item.sort_order,
        expected_payment_date=item.expected_payment_date,
    )


@router.post("/contract-versions/{version_id}/payment-rules", response_model=PaymentRuleResponse)
async def create_payment_rule(version_id: str, req: PaymentRuleCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    vid = uuid.UUID(version_id)
    rule = PaymentRule(
        contract_version_id=vid,
        contract_item_id=uuid.UUID(req.contract_item_id) if req.contract_item_id else None,
        rule_type=req.rule_type, rule_name=req.rule_name, rate=req.rate,
        calculation_base=req.calculation_base, condition_code=req.condition_code,
        condition_description=req.condition_description, release_sequence=req.release_sequence,
        created_by=current.id, updated_by=current.id,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return PaymentRuleResponse(
        id=str(rule.id), contract_version_id=str(rule.contract_version_id),
        contract_item_id=str(rule.contract_item_id) if rule.contract_item_id else None,
        rule_type=rule.rule_type, rule_name=rule.rule_name, rate=rule.rate,
        calculation_base=rule.calculation_base, is_active=rule.is_active,
    )
