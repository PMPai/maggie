import uuid
from dataclasses import dataclass
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.standard import StandardItem


@dataclass
class Candidate:
    standard_item: StandardItem
    score: float
    method: str = "RULE"


async def rule_match(text: str, org_id: uuid.UUID, db: AsyncSession) -> list[Candidate]:
    """Rule-based matching: keyword overlap + category hints."""
    from app.services.matching.normalize import normalize_text
    normalized = normalize_text(text)
    keywords = set(normalized.split())
    if not keywords:
        return []
    result = await db.execute(
        select(StandardItem).where(
            StandardItem.organization_id == org_id,
            StandardItem.is_active == True,
        )
    )
    candidates = []
    for item in result.scalars().all():
        item_text = normalize_text(item.name + " " + (item.description or ""))
        item_keywords = set(item_text.split())
        overlap = len(keywords & item_keywords)
        if overlap > 0:
            score = overlap / max(len(keywords), 1)
            candidates.append(Candidate(standard_item=item, score=score))
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:10]
