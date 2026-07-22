from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.variation import Variation, VariationStatus
from app.models.billing import PaymentApplicationLine


async def get_approved_variation_qty(contract_item_id, db: AsyncSession) -> Decimal:
    result = await db.execute(
        select(func.coalesce(func.sum(Variation.quantity_delta), 0)).where(
            Variation.contract_item_id == contract_item_id,
            Variation.status == VariationStatus.APPROVED,
        )
    )
    return Decimal(str(result.scalar()))
