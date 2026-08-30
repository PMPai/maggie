import uuid
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser, require_project_member
from app.models.invoice import Invoice, InvoiceApplicationLink, InvoiceStatus, InvoiceType
from app.models.contract import Contract
from app.schemas.invoice import (
    InvoiceCreate, InvoiceResponse, InvoiceLinkCreate, InvoiceLinkResponse,
)
from app.models.approval import AuditLog

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


def _to_response(inv: Invoice) -> InvoiceResponse:
    return InvoiceResponse(
        id=str(inv.id), project_id=str(inv.project_id), contract_id=str(inv.contract_id),
        invoice_no=inv.invoice_no, invoice_type=inv.invoice_type.value if isinstance(inv.invoice_type, InvoiceType) else inv.invoice_type,
        issue_date=inv.issue_date, due_date=inv.due_date,
        amount_ex_tax=inv.amount_ex_tax, tax_amount=inv.tax_amount, amount_inc_tax=inv.amount_inc_tax,
        tax_rate=inv.tax_rate, status=inv.status.value if isinstance(inv.status, InvoiceStatus) else inv.status,
        source=inv.source, notes=inv.notes,
    )


@router.post("", response_model=InvoiceResponse)
async def create_invoice(req: InvoiceCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pid = uuid.UUID(req.project_id)
    await require_project_member(pid, current, db)
    cid = uuid.UUID(req.contract_id)

    result = await db.execute(select(Contract).where(Contract.id == cid))
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if Decimal(req.amount_ex_tax) + Decimal(req.tax_amount) != Decimal(req.amount_inc_tax):
        raise HTTPException(status_code=400, detail="amount_ex_tax + tax_amount must equal amount_inc_tax")

    inv = Invoice(
        project_id=pid, contract_id=cid,
        invoice_no=req.invoice_no, invoice_type=InvoiceType(req.invoice_type),
        issue_date=req.issue_date, due_date=req.due_date,
        amount_ex_tax=req.amount_ex_tax, tax_amount=req.tax_amount, amount_inc_tax=req.amount_inc_tax,
        tax_rate=req.tax_rate, status=InvoiceStatus.PLANNED, source=req.source, notes=req.notes,
        created_by=current.id, updated_by=current.id,
    )
    db.add(inv)
    await db.flush()
    db.add(AuditLog(
        user_id=current.id,
        action="CREATE",
        resource_type="invoice",
        resource_id=str(inv.id),
        detail={"invoice_no": inv.invoice_no},
    ))
    await db.commit()
    await db.refresh(inv)
    return _to_response(inv)


@router.get("", response_model=list[InvoiceResponse])
async def list_invoices(project_id: str = Query(...), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pid = uuid.UUID(project_id)
    await require_project_member(pid, current, db)
    result = await db.execute(
        select(Invoice).where(Invoice.project_id == pid, Invoice.deleted_at.is_(None))
    )
    return [_to_response(i) for i in result.scalars().all()]


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    iid = uuid.UUID(invoice_id)
    result = await db.execute(select(Invoice).where(Invoice.id == iid))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    await require_project_member(inv.project_id, current, db)
    return _to_response(inv)


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(invoice_id: str, req: InvoiceCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    iid = uuid.UUID(invoice_id)
    result = await db.execute(select(Invoice).where(Invoice.id == iid))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    await require_project_member(inv.project_id, current, db)
    if inv.status != InvoiceStatus.PLANNED:
        raise HTTPException(status_code=400, detail="Can only edit planned invoices")

    if Decimal(req.amount_ex_tax) + Decimal(req.tax_amount) != Decimal(req.amount_inc_tax):
        raise HTTPException(status_code=400, detail="amount_ex_tax + tax_amount must equal amount_inc_tax")

    inv.invoice_no = req.invoice_no
    inv.invoice_type = InvoiceType(req.invoice_type)
    inv.issue_date = req.issue_date
    inv.due_date = req.due_date
    inv.amount_ex_tax = req.amount_ex_tax
    inv.tax_amount = req.tax_amount
    inv.amount_inc_tax = req.amount_inc_tax
    inv.tax_rate = req.tax_rate
    inv.source = req.source
    inv.notes = req.notes
    inv.updated_by = current.id
    await db.commit()
    await db.refresh(inv)
    return _to_response(inv)


@router.post("/{invoice_id}/links", response_model=InvoiceLinkResponse)
async def add_link(invoice_id: str, req: InvoiceLinkCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    iid = uuid.UUID(invoice_id)
    result = await db.execute(select(Invoice).where(Invoice.id == iid))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    await require_project_member(inv.project_id, current, db)

    link = InvoiceApplicationLink(
        invoice_id=iid, payment_application_id=uuid.UUID(req.payment_application_id),
        linked_amount=req.linked_amount, created_by=current.id, updated_by=current.id,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return InvoiceLinkResponse(
        id=str(link.id), invoice_id=str(link.invoice_id),
        payment_application_id=str(link.payment_application_id), linked_amount=link.linked_amount,
    )


@router.get("/{invoice_id}/links", response_model=list[InvoiceLinkResponse])
async def list_links(invoice_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    iid = uuid.UUID(invoice_id)
    result = await db.execute(select(Invoice).where(Invoice.id == iid))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    await require_project_member(inv.project_id, current, db)
    result = await db.execute(select(InvoiceApplicationLink).where(InvoiceApplicationLink.invoice_id == iid))
    return [InvoiceLinkResponse(
        id=str(l.id), invoice_id=str(l.invoice_id),
        payment_application_id=str(l.payment_application_id), linked_amount=l.linked_amount,
    ) for l in result.scalars().all()]


@router.post("/{invoice_id}/issue", response_model=InvoiceResponse)
async def issue_invoice(invoice_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    iid = uuid.UUID(invoice_id)
    result = await db.execute(select(Invoice).where(Invoice.id == iid))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    await require_project_member(inv.project_id, current, db)
    if inv.status != InvoiceStatus.PLANNED:
        raise HTTPException(status_code=400, detail="Only planned invoices can be issued")
    inv.status = InvoiceStatus.ISSUED
    if not inv.issue_date:
        inv.issue_date = date.today()
    inv.updated_by = current.id
    db.add(AuditLog(
        user_id=current.id,
        action="ISSUE",
        resource_type="invoice",
        resource_id=str(inv.id),
        detail={"invoice_no": inv.invoice_no},
    ))
    await db.commit()
    await db.refresh(inv)
    return _to_response(inv)


@router.post("/{invoice_id}/send", response_model=InvoiceResponse)
async def send_invoice(invoice_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Transition an ISSUED invoice to SENT (delivered to customer)."""
    iid = uuid.UUID(invoice_id)
    result = await db.execute(select(Invoice).where(Invoice.id == iid))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    await require_project_member(inv.project_id, current, db)
    if inv.status != InvoiceStatus.ISSUED:
        raise HTTPException(status_code=400, detail="Only issued invoices can be sent")
    inv.status = InvoiceStatus.SENT
    inv.updated_by = current.id
    db.add(AuditLog(
        user_id=current.id, action="SEND", resource_type="invoice",
        resource_id=str(inv.id), detail={"invoice_no": inv.invoice_no},
    ))
    await db.commit()
    await db.refresh(inv)
    return _to_response(inv)
