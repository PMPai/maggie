import uuid
from app.services.matching.rule import Candidate


async def vector_search(text: str, org_id: uuid.UUID, db) -> list[Candidate]:
    """Vector search using pgvector embeddings (optional).
    Returns empty list if pgvector or embeddings not available."""
    return []
