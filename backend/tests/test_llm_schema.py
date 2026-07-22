"""Test #17: LLM output schema validation.

The StubClient returns None (no LLM candidates) so the pipeline falls back to
rule/fulltext matching. The OpenAIClient._parse_response must parse the
validated JSON schema into an LLMResult, return None on invalid JSON, and
tolerate missing fields by applying sensible defaults.
"""
import json

import pytest

from app.services.llm.protocol import LLMResult, LLMCandidate
from app.services.llm.stub import StubClient
from app.services.llm.openai_impl import OpenAIClient


@pytest.mark.asyncio
async def test_stub_client_returns_none():
    client = StubClient()
    result = await client.rank_candidates("source item text", [])
    assert result is None


def _make_client():
    return OpenAIClient(base_url="http://localhost:1234", api_key="sk-test", model="test-model")


def test_parse_valid_json_returns_llm_result():
    client = _make_client()
    payload = {
        "source_item_id": "src-1",
        "candidate_matches": [
            {
                "standard_item_id": "std-1",
                "confidence": 0.92,
                "reasoning": "Same unit and similar description.",
                "unit_compatibility": "SAME",
                "conversion_required": False,
                "scope_differences": [],
                "questions_for_reviewer": [],
            }
        ],
        "suggested_mapping_type": "ONE_TO_ONE",
    }
    result = client._parse_response(json.dumps(payload), [])
    assert isinstance(result, LLMResult)
    assert result.source_item_id == "src-1"
    assert result.suggested_mapping_type == "ONE_TO_ONE"
    assert len(result.candidate_matches) == 1

    match = result.candidate_matches[0]
    assert isinstance(match, LLMCandidate)
    assert match.standard_item_id == "std-1"
    assert match.confidence == pytest.approx(0.92)
    assert match.unit_compatibility == "SAME"
    assert match.conversion_required is False


def test_parse_invalid_json_returns_none():
    client = _make_client()
    result = client._parse_response("not valid json {{{", [])
    assert result is None


def test_parse_missing_fields_handles_gracefully():
    """Missing optional fields must not crash; defaults are applied."""
    client = _make_client()
    payload = {
        "source_item_id": "src-2",
        "candidate_matches": [
            {"standard_item_id": "std-2"},
        ],
    }
    result = client._parse_response(json.dumps(payload), [])
    assert isinstance(result, LLMResult)
    assert result.source_item_id == "src-2"
    # suggested_mapping_type defaults to ONE_TO_ONE when absent
    assert result.suggested_mapping_type == "ONE_TO_ONE"

    match = result.candidate_matches[0]
    assert match.standard_item_id == "std-2"
    # confidence defaults to 0.0
    assert match.confidence == 0.0
    # unit_compatibility defaults to UNKNOWN
    assert match.unit_compatibility == "UNKNOWN"
    # conversion_required defaults to False
    assert match.conversion_required is False
    assert match.scope_differences == []
    assert match.questions_for_reviewer == []


def test_parse_empty_candidate_matches():
    client = _make_client()
    payload = {
        "source_item_id": "src-3",
        "candidate_matches": [],
        "suggested_mapping_type": "NOT_COMPARABLE",
    }
    result = client._parse_response(json.dumps(payload), [])
    assert isinstance(result, LLMResult)
    assert result.source_item_id == "src-3"
    assert result.suggested_mapping_type == "NOT_COMPARABLE"
    assert result.candidate_matches == []


def test_parse_missing_source_item_id_defaults_to_empty():
    client = _make_client()
    payload = {"candidate_matches": []}
    result = client._parse_response(json.dumps(payload), [])
    assert isinstance(result, LLMResult)
    assert result.source_item_id == ""
    assert result.candidate_matches == []


def test_parse_multiple_candidates_preserved_in_order():
    client = _make_client()
    payload = {
        "source_item_id": "src-4",
        "candidate_matches": [
            {"standard_item_id": "std-a", "confidence": 0.9},
            {"standard_item_id": "std-b", "confidence": 0.6},
            {"standard_item_id": "std-c", "confidence": 0.3},
        ],
        "suggested_mapping_type": "ONE_TO_MANY",
    }
    result = client._parse_response(json.dumps(payload), [])
    assert isinstance(result, LLMResult)
    assert [m.standard_item_id for m in result.candidate_matches] == ["std-a", "std-b", "std-c"]
    assert result.suggested_mapping_type == "ONE_TO_MANY"
