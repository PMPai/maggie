import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.standard import StandardItem, StandardItemAlias


async def exact_alias_lookup(text: str, org_id: uuid.UUID, db: AsyncSession) -> list[StandardItem]:
    """Find standard items with an approved alias matching text exactly."""
    from app.services.matching.normalize import normalize_text
    normalized = normalize_text(text)
    result = await db.execute(
        select(StandardItem).join(
            StandardItemAlias, StandardItemAlias.standard_item_id == StandardItem.id
        ).where(
            StandardItem.organization_id == org_id,
            StandardItem.is_active == True,
            StandardItemAlias.is_approved == True,
            func.lower(StandardItemAlias.alias_text) == normalized,
        )
    )
    return list(result.scalars().all())
