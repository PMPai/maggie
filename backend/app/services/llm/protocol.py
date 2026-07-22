from typing import Protocol
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class LLMCandidate:
    standard_item_id: str
    confidence: float
    reasoning: str
    unit_compatibility: str = "UNKNOWN"
    conversion_required: bool = False
    scope_differences: list = field(default_factory=list)
    questions_for_reviewer: list = field(default_factory=list)


@dataclass
class LLMResult:
    source_item_id: str
    candidate_matches: list[LLMCandidate]
    suggested_mapping_type: str = "ONE_TO_ONE"


class LLMClient(Protocol):
    async def rank_candidates(
        self, source_item_text: str, candidates: list
    ) -> LLMResult | None:
        ...
