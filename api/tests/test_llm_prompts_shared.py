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


def test_parse_and_validate_learning_path_accepts_goal_and_objective():
    import json
    from pipeline.llm.prompts import parse_and_validate_learning_path
    raw = json.dumps({
        "goal": "vLLM로 로컬 LLM 서빙을 직접 띄워본다",
        "resources": [
            {"type": "official_docs", "title": "T", "url": "https://a.dev", "descriptor": "d", "objective": "설치 감잡기"},
            {"type": "core_material", "title": "T", "url": "https://a.dev", "descriptor": "d", "objective": "핵심 개념"},
            {"type": "github", "title": "T", "url": "https://github.com/x/y", "descriptor": "d", "objective": "예제 읽기"},
            {"type": "practice_example", "title": "T", "url": "https://a.dev", "descriptor": "d", "objective": "따라하기"},
            {"type": "applied_idea", "title": "T", "url": "", "descriptor": "d", "objective": "내 프로젝트 적용"},
        ],
    })
    parse_and_validate_learning_path(raw)  # 예외 없이 통과해야 함


def test_parse_and_validate_learning_path_accepts_missing_goal_and_objective():
    """goal/objective가 없어도(하위호환/모델 누락) 검증은 통과해야 한다(best-effort)."""
    import json
    from pipeline.llm.prompts import parse_and_validate_learning_path
    raw = json.dumps({
        "resources": [
            {"type": "official_docs", "title": "T", "url": "https://a.dev", "descriptor": "d"},
            {"type": "core_material", "title": "T", "url": "https://a.dev", "descriptor": "d"},
            {"type": "github", "title": "T", "url": "https://github.com/x/y", "descriptor": "d"},
            {"type": "practice_example", "title": "T", "url": "https://a.dev", "descriptor": "d"},
            {"type": "applied_idea", "title": "T", "url": "", "descriptor": "d"},
        ],
    })
    parse_and_validate_learning_path(raw)  # 예외 없이 통과해야 함


def test_learning_path_prompt_mentions_goal_and_objective():
    from pipeline.llm.prompts import LEARNING_PATH_SYSTEM_PROMPT
    assert "goal" in LEARNING_PATH_SYSTEM_PROMPT
    assert "objective" in LEARNING_PATH_SYSTEM_PROMPT
