import json
from app.services.llm.protocol import LLMResult, LLMCandidate
from app.services.llm.stub import StubClient


class OpenAIClient:
    """OpenAI-compatible LLM client.
    Calls an OpenAI-compatible API to rank/extract candidate matches.
    LLM output must match the validated JSON schema (spec §12)."""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def rank_candidates(self, source_item_text: str, candidates: list) -> LLMResult | None:
        import httpx

        prompt = self._build_prompt(source_item_text, candidates)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a construction contract item matching assistant. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]

        return self._parse_response(content, candidates)

    def _build_prompt(self, source_item_text: str, candidates: list) -> str:
        candidate_list = [
            {"id": str(c[0].id), "name": c[0].name, "unit": c[0].unit or ""}
            for c in candidates[:20]
        ]
        return (
            f"Source contract item: '{source_item_text}'\n"
            f"Candidate standard items: {json.dumps(candidate_list, ensure_ascii=False)}\n"
            "Rank the candidates by relevance. Output JSON:\n"
            '{"source_item_id": "<id>", "candidate_matches": [{"standard_item_id": "<id>", '
            '"confidence": 0.0, "reasoning": "...", "unit_compatibility": "SAME|CONVERTIBLE|INCOMPATIBLE|UNKNOWN", '
            '"conversion_required": false, "scope_differences": [], "questions_for_reviewer": []}], '
            '"suggested_mapping_type": "ONE_TO_ONE|ONE_TO_MANY|MANY_TO_ONE|NOT_COMPARABLE"}'
        )

    def _parse_response(self, content: str, candidates: list) -> LLMResult | None:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return None

        source_id = data.get("source_item_id", "")
        matches = []
        for m in data.get("candidate_matches", []):
            matches.append(LLMCandidate(
                standard_item_id=m.get("standard_item_id", ""),
                confidence=float(m.get("confidence", 0.0)),
                reasoning=m.get("reasoning", ""),
                unit_compatibility=m.get("unit_compatibility", "UNKNOWN"),
                conversion_required=bool(m.get("conversion_required", False)),
                scope_differences=m.get("scope_differences", []),
                questions_for_reviewer=m.get("questions_for_reviewer", []),
            ))

        return LLMResult(
            source_item_id=source_id,
            candidate_matches=matches,
            suggested_mapping_type=data.get("suggested_mapping_type", "ONE_TO_ONE"),
        )


def get_llm_client(settings) -> OpenAIClient | StubClient:
    if not settings.LLM_ENABLED or not settings.LLM_API_KEY:
        return StubClient()
    return OpenAIClient(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        model=settings.LLM_MODEL,
    )
