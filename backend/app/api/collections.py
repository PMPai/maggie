import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser, require_project_member
from app.models.collection import Collection, CollectionAllocation, CollectionStatus
from app.models.contract import Contract
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.collection import (
    CollectionCreate, CollectionResponse, CollectionAllocationCreate, CollectionAllocationResponse,
)
from app.services.collection_service import get_invoice_outstanding

router = APIRouter(prefix="/api/collections", tags=["collections"])


def _to_response(col: Collection) -> CollectionResponse:
    return CollectionResponse(
        id=str(col.id), project_id=str(col.project_id), contract_id=str(col.contract_id),
        receipt_no=col.receipt_no, receipt_date=col.receipt_date,
        amount_received=col.amount_received, payment_method=col.payment_method,
        bank_reference=col.bank_reference, notes=col.notes,
        status=col.status.value if isinstance(col.status, CollectionStatus) else col.status,
    )


@router.post("", response_model=CollectionResponse)
async def create_collection(req: CollectionCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pid = uuid.UUID(req.project_id)
    await require_project_member(pid, current, db)
    cid = uuid.UUID(req.contract_id)

    result = await db.execute(select(Contract).where(Contract.id == cid))
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    col = Collection(
        organization_id=current.organization_id, project_id=pid, contract_id=cid,
        receipt_no=req.receipt_no, receipt_date=req.receipt_date,
        amount_received=req.amount_received, payment_method=req.payment_method,
        bank_reference=req.bank_reference, notes=req.notes,
        status=CollectionStatus(req.status),
        created_by=current.user.id, updated_by=current.user.id,
    )
    db.add(col)
    await db.commit()
    await db.refresh(col)
    return _to_response(col)


@router.get("", response_model=list[CollectionResponse])
async def list_collections(project_id: str = Query(...), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pid = uuid.UUID(project_id)
    await require_project_member(pid, current, db)
    result = await db.execute(
        select(Collection).where(Collection.project_id == pid, Collection.deleted_at.is_(None))
    )
    return [_to_response(c) for c in result.scalars().all()]


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(collection_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cid = uuid.UUID(collection_id)
    result = await db.execute(select(Collection).where(Collection.id == cid))
    col = result.scalar_one_or_none()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    await require_project_member(col.project_id, current, db)
    return _to_response(col)


@router.post("/{collection_id}/allocate", response_model=CollectionAllocationResponse)
async def allocate(collection_id: str, req: CollectionAllocationCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cid = uuid.UUID(collection_id)
    result = await db.execute(select(Collection).where(Collection.id == cid))
    col = result.scalar_one_or_none()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    await require_project_member(col.project_id, current, db)
    if col.status != CollectionStatus.CONFIRMED:
        raise HTTPException(status_code=400, detail="Can only allocate confirmed collections")

    inv_id = uuid.UUID(req.invoice_id)
    outstanding = await get_invoice_outstanding(inv_id, db)
    if req.allocated_amount > outstanding:
        raise HTTPException(status_code=400, detail=f"Allocated amount exceeds invoice outstanding ({outstanding})")

    allocation = CollectionAllocation(
        collection_id=cid, invoice_id=inv_id,
        allocated_amount=req.allocated_amount, created_by=current.user.id, updated_by=current.user.id,
    )
    db.add(allocation)

    # Update invoice status to partially paid / paid
    remaining = outstanding - req.allocated_amount
    result = await db.execute(select(Invoice).where(Invoice.id == inv_id))
    inv = result.scalar_one_or_none()
    if inv and inv.status == InvoiceStatus.ISSUED:
        inv.status = InvoiceStatus.PAID if remaining <= Decimal("0") else InvoiceStatus.PARTIALLY_PAID
        inv.updated_by = current.user.id

    await db.commit()
    await db.refresh(allocation)
    return CollectionAllocationResponse(
        id=str(allocation.id), collection_id=str(allocation.collection_id),
        invoice_id=str(allocation.invoice_id), allocated_amount=allocation.allocated_amount,
    )


@router.get("/{collection_id}/allocations", response_model=list[CollectionAllocationResponse])
async def list_allocations(collection_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cid = uuid.UUID(collection_id)
    result = await db.execute(select(Collection).where(Collection.id == cid))
    col = result.scalar_one_or_none()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    await require_project_member(col.project_id, current, db)
    result = await db.execute(select(CollectionAllocation).where(CollectionAllocation.collection_id == cid))
    return [CollectionAllocationResponse(
        id=str(a.id), collection_id=str(a.collection_id),
        invoice_id=str(a.invoice_id), allocated_amount=a.allocated_amount,
    ) for a in result.scalars().all()]
