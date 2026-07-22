from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.deduction import Deduction, DeductionStatus, TaxTreatment


async def get_application_deductions(app_id, db: AsyncSession):
    result = await db.execute(
        select(Deduction).where(
            Deduction.payment_application_id == app_id,
            Deduction.status == DeductionStatus.APPROVED,
        )
    )
    return result.scalars().all()


def calc_deduction_tax(amount: Decimal, tax_treatment: TaxTreatment, tax_rate: Decimal) -> Decimal:
    if tax_treatment == TaxTreatment.NON_TAXABLE:
        return Decimal("0")
    return (amount * tax_rate).quantize(Decimal("0.01"))


async def get_total_deduction_amount(app_id, db: AsyncSession) -> Decimal:
    deductions = await get_application_deductions(app_id, db)
    return sum((d.amount for d in deductions), Decimal("0"))
