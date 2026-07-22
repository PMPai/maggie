import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.standard import StandardItem
from app.services.matching.rule import Candidate


async def fulltext_search(text: str, org_id: uuid.UUID, db: AsyncSession) -> list[Candidate]:
    """Full-text search using PostgreSQL ILIKE."""
    from app.services.matching.normalize import normalize_text
    normalized = normalize_text(text)
    if not normalized:
        return []
    result = await db.execute(
        select(StandardItem).where(
            StandardItem.organization_id == org_id,
            StandardItem.is_active == True,
            or_(
                StandardItem.name.ilike(f"%{normalized}%"),
                StandardItem.description.ilike(f"%{normalized}%"),
            ),
        ).limit(10)
    )
    candidates = []
    for item in result.scalars().all():
        candidates.append(Candidate(standard_item=item, score=0.5, method="FULLTEXT"))
    return candidates


from sqlalchemy import or_
