# api/tests/test_llm_prompts_shared.py
import json
import pytest
from pipeline.llm.base import LLMProviderError, ReviewContext
from pipeline.llm import prompts
from tests.mocks import VALID_13_SECTION_RESPONSE


def test_format_sources_renders_bracketed_lines():
    out = prompts.format_sources([{"source_type": "github", "title": "T", "url": "http://x"}])
    assert "[github]" in out and "T" in out and "http://x" in out


def test_build_review_user_content_includes_tech_and_context():
    ctx = ReviewContext(technology_name="LangGraph", signal_sources=[], user_role="dev")
    out = prompts.build_review_user_content(ctx)
    assert "LangGraph" in out and "dev" in out


def test_parse_and_validate_review_accepts_valid_payload():
    prompts.parse_and_validate_review(VALID_13_SECTION_RESPONSE)  # no raise


def test_parse_and_validate_review_rejects_missing_section():
    partial = json.dumps({"one_line_definition": "x"})
    with pytest.raises(LLMProviderError):
        prompts.parse_and_validate_review(partial)


def test_parse_and_validate_memory_rejects_bad_type():
    with pytest.raises(LLMProviderError):
        prompts.parse_and_validate_memory(json.dumps({"memory_type": "nope", "summary": "s"}))
