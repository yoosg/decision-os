import json
import pytest

from pipeline.llm.base import LLMProviderError
from pipeline.llm import prompts


def _ok(results):
    return json.dumps({"results": results})


def test_parse_valid_returns_results():
    raw = _ok([
        {"id": 0, "keep": False, "category": "business_news", "name": "OpenAI 협력 사례"},
        {"id": 1, "keep": True, "category": "tool_update", "name": "LangGraph 0.3"},
    ])
    out = prompts.parse_and_validate_learnability(raw, expected_count=2)
    assert len(out) == 2
    assert out[1]["keep"] is True and out[1]["name"] == "LangGraph 0.3"


def test_count_mismatch_raises():
    raw = _ok([{"id": 0, "keep": True, "category": "new_tool", "name": "X"}])
    with pytest.raises(LLMProviderError):
        prompts.parse_and_validate_learnability(raw, expected_count=2)


def test_bad_category_raises():
    raw = _ok([{"id": 0, "keep": True, "category": "nonsense", "name": "X"}])
    with pytest.raises(LLMProviderError):
        prompts.parse_and_validate_learnability(raw, expected_count=1)


def test_missing_key_raises():
    raw = _ok([{"id": 0, "keep": True, "category": "new_tool"}])  # name 없음
    with pytest.raises(LLMProviderError):
        prompts.parse_and_validate_learnability(raw, expected_count=1)


def test_empty_name_raises():
    raw = _ok([{"id": 0, "keep": True, "category": "new_tool", "name": "  "}])
    with pytest.raises(LLMProviderError):
        prompts.parse_and_validate_learnability(raw, expected_count=1)


def test_user_input_includes_titles_and_ids():
    s = prompts.build_learnability_user_input([
        {"id": 0, "label": "General AI", "title": "OpenAI 협력 과정"},
    ])
    assert "OpenAI 협력 과정" in s and "0" in s
