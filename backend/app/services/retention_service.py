from decimal import Decimal
from datetime import date
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.billing import RetentionEntry, RetentionEntryType


async def create_release(
    project_id, contract_id, db: AsyncSession, user_id, org_id,
    payment_application_id=None, amount=Decimal("0"), description=None,
):
    entry = RetentionEntry(
        organization_id=org_id, project_id=project_id, contract_id=contract_id,
        payment_application_id=payment_application_id,
        entry_type=RetentionEntryType.RELEASE,
        amount=amount, description=description,
        created_by=user_id, updated_by=user_id,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def create_adjustment(
    project_id, contract_id, db: AsyncSession, user_id, org_id,
    amount=Decimal("0"), description=None, contract_item_id=None,
):
    entry = RetentionEntry(
        organization_id=org_id, project_id=project_id, contract_id=contract_id,
        contract_item_id=contract_item_id,
        entry_type=RetentionEntryType.ADJUSTMENT,
        amount=amount, description=description,
        created_by=user_id, updated_by=user_id,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def create_reversal(
    original_entry_id, db: AsyncSession, user_id, org_id, description=None,
):
    result = await db.execute(select(RetentionEntry).where(RetentionEntry.id == original_entry_id))
    original = result.scalar_one_or_none()
    if not original:
        raise ValueError("Original retention entry not found")
    entry = RetentionEntry(
        organization_id=org_id, project_id=original.project_id,
        contract_id=original.contract_id,
        payment_application_id=original.payment_application_id,
        contract_item_id=original.contract_item_id,
        entry_type=RetentionEntryType.REVERSAL,
        amount=original.amount,
        description=description or f"Reversal of entry {original_entry_id}",
        reversal_of_id=original_entry_id,
        created_by=user_id, updated_by=user_id,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def get_balance(contract_id, db: AsyncSession, contract_item_id=None) -> Decimal:
    """Balance = SUM(HOLD) - SUM(RELEASE) + SUM(ADJUSTMENT) - SUM(REVERSAL of HOLD) + SUM(REVERSAL of RELEASE)"""
    result = await db.execute(
        select(
            func.coalesce(func.sum(
                RetentionEntry.amount
            ), 0).label("total")
        ).where(
            RetentionEntry.contract_id == contract_id,
            RetentionEntry.entry_type.in_([RetentionEntryType.HOLD, RetentionEntryType.ADJUSTMENT]),
        )
    )
    held = Decimal(str(result.scalar()))
    result = await db.execute(
        select(
            func.coalesce(func.sum(RetentionEntry.amount), 0)
        ).where(
            RetentionEntry.contract_id == contract_id,
            RetentionEntry.entry_type == RetentionEntryType.RELEASE,
        )
    )
    released = Decimal(str(result.scalar()))
    result = await db.execute(
        select(
            func.coalesce(func.sum(RetentionEntry.amount), 0)
        ).where(
            RetentionEntry.contract_id == contract_id,
            RetentionEntry.entry_type == RetentionEntryType.REVERSAL,
        )
    )
    reversals = Decimal(str(result.scalar()))
    return held - released - reversals


async def get_releases_for_period(
    contract_id, period_start: date, period_end: date, db: AsyncSession,
) -> Decimal:
    result = await db.execute(
        select(func.coalesce(func.sum(RetentionEntry.amount), 0)).where(
            RetentionEntry.contract_id == contract_id,
            RetentionEntry.entry_type == RetentionEntryType.RELEASE,
            RetentionEntry.created_at >= period_start,
            RetentionEntry.created_at <= period_end,
        )
    )
    return Decimal(str(result.scalar()))
