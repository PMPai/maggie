from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.collection import Collection, CollectionAllocation
from app.models.invoice import Invoice


async def get_invoice_outstanding(invoice_id, db: AsyncSession) -> Decimal:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        return Decimal("0")
    allocated_result = await db.execute(
        select(func.coalesce(func.sum(CollectionAllocation.allocated_amount), 0)).where(
            CollectionAllocation.invoice_id == invoice_id
        )
    )
    allocated = Decimal(str(allocated_result.scalar()))
    return invoice.amount_inc_tax - allocated
