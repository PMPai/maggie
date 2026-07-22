from app.services.llm.protocol import LLMResult


class StubClient:
    """Stub LLM client — used when LLM_ENABLED=false.
    Returns None (no LLM candidates), pipeline falls back to rule/fulltext."""

    async def rank_candidates(self, source_item_text: str, candidates: list) -> LLMResult | None:
        return None
