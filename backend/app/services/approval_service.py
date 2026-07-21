import uuid
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.billing import PaymentApplication, PaymentApplicationLine, ApplicationStatus, RetentionEntry, RetentionEntryType
from app.models.contract import Contract, ContractVersion, ContractItem, PaymentRule, ContractVersionStatus
from app.services.calc_engine import (
    ItemInput, LineInput, RuleInput, calc_line_current, calc_application,
    check_quantity_limit, OverclaimError, TaxMode, RoundingPolicy, CalculationMethod,
)
from app.models.approval import Approval, AuditLog


async def audit_log(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, action: str, resource_type: str, resource_id: str, detail: dict = None):
    log = AuditLog(organization_id=org_id, user_id=user_id, action=action, resource_type=resource_type, resource_id=resource_id, detail=detail)
    db.add(log)
    await db.flush()


async def submit_application(app_id: uuid.UUID, db: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID) -> PaymentApplication:
    """Transition application from DRAFT to SUBMITTED after validation."""
    result = await db.execute(select(PaymentApplication).where(PaymentApplication.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.status != ApplicationStatus.DRAFT:
        raise HTTPException(status_code=400, detail=f"Cannot submit application in status {app.status}")
    app.status = ApplicationStatus.SUBMITTED
    app.updated_by = user_id
    await audit_log(db, org_id, user_id, "SUBMIT_APPLICATION", "payment_application", str(app_id))
    await db.commit()
    await db.refresh(app)
    return app


async def approve_application(app_id: uuid.UUID, step: str, db: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID) -> PaymentApplication:
    """Approve application at a given step (project or finance)."""
    result = await db.execute(select(PaymentApplication).where(PaymentApplication.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Record approval
    approval = Approval(
        resource_type="PAYMENT_APPLICATION", resource_id=app_id,
        step_order=1 if step == "project" else 2,
        role_required="PROJECT_MANAGER" if step == "project" else "FINANCE_REVIEWER",
        decision="APPROVED", decided_by=user_id,
        created_by=user_id, updated_by=user_id,
    )
    db.add(approval)

    if step == "project":
        if app.status != ApplicationStatus.SUBMITTED:
            raise HTTPException(status_code=400, detail=f"Cannot project-approve from {app.status}")
        app.status = ApplicationStatus.PROJECT_APPROVED
    elif step == "finance":
        if app.status != ApplicationStatus.PROJECT_APPROVED:
            raise HTTPException(status_code=400, detail=f"Cannot finance-approve from {app.status}")
        app.status = ApplicationStatus.FINANCE_APPROVED

    app.updated_by = user_id
    await audit_log(db, org_id, user_id, f"APPROVE_{step.upper()}", "payment_application", str(app_id))
    await db.commit()
    await db.refresh(app)
    return app


async def post_application(app_id: uuid.UUID, action_id: str, db: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID) -> PaymentApplication:
    """Post application — idempotent via posted_action_id."""
    result = await db.execute(select(PaymentApplication).where(PaymentApplication.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Idempotency: if already posted with same action_id, return as-is
    if app.status == ApplicationStatus.POSTED and app.posted_action_id == action_id:
        return app

    # If already posted with different action_id, reject
    if app.status == ApplicationStatus.POSTED:
        raise HTTPException(status_code=400, detail="Application already posted")

    if app.status != ApplicationStatus.FINANCE_APPROVED:
        raise HTTPException(status_code=400, detail=f"Cannot post application in status {app.status}")

    app.status = ApplicationStatus.POSTED
    app.posted_at = datetime.now(timezone.utc)
    app.posted_action_id = action_id
    app.updated_by = user_id

    # Create retention HOLD entries for each line
    lines_result = await db.execute(
        select(PaymentApplicationLine).where(PaymentApplicationLine.payment_application_id == app_id)
    )
    for line in lines_result.scalars().all():
        if line.retention_held > 0:
            entry = RetentionEntry(
                organization_id=org_id, project_id=app.project_id, contract_id=app.contract_id,
                payment_application_id=app_id, contract_item_id=line.contract_item_id,
                entry_type=RetentionEntryType.HOLD, amount=line.retention_held,
                description=f"Retention held for period {app.period_no}",
                created_by=user_id, updated_by=user_id,
            )
            db.add(entry)

    await audit_log(db, org_id, user_id, "POST_APPLICATION", "payment_application", str(app_id), {"action_id": action_id})
    await db.commit()
    await db.refresh(app)
    return app
