import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser, require_project_member
from app.models.billing import RetentionEntry, RetentionEntryType
from app.schemas.retention import RetentionEntryCreate, RetentionEntryResponse, RetentionBalanceResponse
from app.services.retention_service import get_balance, create_release, create_adjustment, create_reversal
from app.models.approval import AuditLog

router = APIRouter(prefix="/api/retention-entries", tags=["retention-entries"])


@router.get("", response_model=list[RetentionEntryResponse])
async def list_entries(
    contract_id: str = Query(...),
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RetentionEntry).where(
            RetentionEntry.contract_id == uuid.UUID(contract_id),
        ).order_by(RetentionEntry.created_at)
    )
    return [RetentionEntryResponse(
        id=str(e.id), project_id=str(e.project_id), contract_id=str(e.contract_id),
        payment_application_id=str(e.payment_application_id) if e.payment_application_id else None,
        contract_item_id=str(e.contract_item_id) if e.contract_item_id else None,
        entry_type=e.entry_type.value if hasattr(e.entry_type, "value") else e.entry_type,
        amount=e.amount, description=e.description,
        reversal_of_id=str(e.reversal_of_id) if e.reversal_of_id else None,
        created_at=str(e.created_at) if e.created_at else None,
    ) for e in result.scalars().all()]


@router.get("/balance", response_model=RetentionBalanceResponse)
async def get_retention_balance(
    contract_id: str = Query(...),
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    balance = await get_balance(uuid.UUID(contract_id), db)
    return RetentionBalanceResponse(contract_id=contract_id, contract_item_id=None, balance=balance)


@router.post("", response_model=RetentionEntryResponse)
async def create_entry(
    req: RetentionEntryCreate,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pid = uuid.UUID(req.project_id)
    await require_project_member(pid, current, db)
    entry_type = RetentionEntryType(req.entry_type)

    if entry_type == RetentionEntryType.RELEASE:
        entry = await create_release(
            pid, uuid.UUID(req.contract_id), db, current.user.id, current.organization_id,
            payment_application_id=uuid.UUID(req.payment_application_id) if req.payment_application_id else None,
            amount=req.amount, description=req.description,
        )
    elif entry_type == RetentionEntryType.ADJUSTMENT:
        entry = await create_adjustment(
            pid, uuid.UUID(req.contract_id), db, current.user.id, current.organization_id,
            amount=req.amount, description=req.description,
        )
    elif entry_type == RetentionEntryType.REVERSAL:
        if not req.reversal_of_id:
            raise HTTPException(status_code=400, detail="reversal_of_id required for REVERSAL")
        entry = await create_reversal(
            uuid.UUID(req.reversal_of_id), db, current.user.id, current.organization_id,
            description=req.description,
        )
    else:
        raise HTTPException(status_code=400, detail="HOLD entries are created automatically on post; use RELEASE/ADJUSTMENT/REVERSAL")

    db.add(AuditLog(
        organization_id=current.organization_id,
        user_id=current.user.id,
        action="CREATE",
        resource_type="retention_entry",
        resource_id=str(entry.id),
        detail={"entry_type": entry.entry_type.value if hasattr(entry.entry_type, "value") else entry.entry_type, "contract_id": str(entry.contract_id)},
    ))
    await db.commit()

    return RetentionEntryResponse(
        id=str(entry.id), project_id=str(entry.project_id), contract_id=str(entry.contract_id),
        payment_application_id=str(entry.payment_application_id) if entry.payment_application_id else None,
        contract_item_id=str(entry.contract_item_id) if entry.contract_item_id else None,
        entry_type=entry.entry_type.value if hasattr(entry.entry_type, "value") else entry.entry_type,
        amount=entry.amount, description=entry.description,
        reversal_of_id=str(entry.reversal_of_id) if entry.reversal_of_id else None,
        created_at=str(entry.created_at) if entry.created_at else None,
    )
