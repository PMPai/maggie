from dataclasses import dataclass
from app.services.matching.normalize import normalize_text
from app.services.matching.alias import exact_alias_lookup
from app.services.matching.rule import rule_match
from app.services.matching.fulltext import fulltext_search
from app.services.matching.vector import vector_search


@dataclass
class MatchingResult:
    candidates: list
    method: str
    auto_apply: bool = False


async def run_pipeline(
    contract_item_id: str,
    contract_item_text: str,
    org_id,
    db,
    llm_client=None,
) -> MatchingResult:
    """Full matching pipeline: normalize → alias → rule → fulltext → vector → LLM (optional)."""
    normalized = normalize_text(contract_item_text)

    # Step 1: exact alias lookup (auto-apply if found)
    exact = await exact_alias_lookup(normalized, org_id, db)
    if exact:
        return MatchingResult(
            candidates=[(item, 1.0, "EXACT_ALIAS") for item in exact],
            method="EXACT_ALIAS",
            auto_apply=True,
        )

    # Step 2: rule + fulltext + vector candidates
    rule_candidates = await rule_match(normalized, org_id, db)
    ft_candidates = await fulltext_search(normalized, org_id, db)
    vec_candidates = await vector_search(normalized, org_id, db)

    # Merge + dedupe by standard_item.id
    seen = set()
    merged = []
    for c in rule_candidates + ft_candidates + vec_candidates:
        if c.standard_item.id not in seen:
            seen.add(c.standard_item.id)
            merged.append((c.standard_item, c.score, c.method))

    # Step 3: LLM rank (optional)
    if llm_client and merged:
        try:
            llm_result = await llm_client.rank_candidates(contract_item_text, merged)
            if llm_result:
                merged = llm_result
        except Exception:
            pass  # LLM failure → human review fallback

    merged.sort(key=lambda x: x[1], reverse=True)
    return MatchingResult(candidates=merged[:10], method="RULE")
