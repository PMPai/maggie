"""MCP tools for invoice CRUD."""
from uuid import UUID


def register_invoice_tools(mcp):
    from app.db.session import async_session_factory
    from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
    from sqlalchemy import select
    from datetime import date
    from decimal import Decimal

    @mcp.tool()
    async def list_invoices(project_id: str, status: str | None = None) -> list[dict]:
        """List invoices for a project, optionally filtered by status."""
        async with async_session_factory() as db:
            q = select(Invoice).where(
                Invoice.project_id == UUID(project_id), Invoice.deleted_at.is_(None)
            )
            if status:
                q = q.where(Invoice.status == InvoiceStatus(status))
            result = await db.execute(q)
            return [
                {
                    "id": str(i.id),
                    "invoice_no": i.invoice_no,
                    "amount_inc_tax": float(i.amount_inc_tax),
                    "status": i.status.value,
                    "issue_date": str(i.issue_date) if i.issue_date else None,
                }
                for i in result.scalars().all()
            ]

    @mcp.tool()
    async def create_invoice(project_id: str, contract_id: str, invoice_no: str,
                              amount_ex_tax: float, tax_amount: float, amount_inc_tax: float) -> dict:
        """Create a PLANNED invoice."""
        async with async_session_factory() as db:
            inv = Invoice(
                project_id=UUID(project_id), contract_id=UUID(contract_id),
                invoice_no=invoice_no, invoice_type=InvoiceType.STANDARD,
                amount_ex_tax=Decimal(str(amount_ex_tax)),
                tax_amount=Decimal(str(tax_amount)),
                amount_inc_tax=Decimal(str(amount_inc_tax)),
                status=InvoiceStatus.PLANNED,
            )
            db.add(inv)
            await db.commit()
            await db.refresh(inv)
            return {"id": str(inv.id), "status": inv.status.value}

    @mcp.tool()
    async def issue_invoice(invoice_id: str, invoice_no: str | None = None) -> dict:
        """Issue a PLANNED invoice (PLANNED → ISSUED)."""
        async with async_session_factory() as db:
            result = await db.execute(select(Invoice).where(Invoice.id == UUID(invoice_id)))
            inv = result.scalar_one_or_none()
            if not inv:
                return {"error": "Not found"}
            inv.status = InvoiceStatus.ISSUED
            if invoice_no:
                inv.invoice_no = invoice_no
            inv.issue_date = date.today()
            await db.commit()
            return {"id": str(inv.id), "status": inv.status.value}

    @mcp.tool()
    async def send_invoice(invoice_id: str) -> dict:
        """Send an ISSUED invoice (ISSUED → SENT)."""
        async with async_session_factory() as db:
            result = await db.execute(select(Invoice).where(Invoice.id == UUID(invoice_id)))
            inv = result.scalar_one_or_none()
            if not inv:
                return {"error": "Not found"}
            inv.status = InvoiceStatus.SENT
            await db.commit()
            return {"id": str(inv.id), "status": inv.status.value}
