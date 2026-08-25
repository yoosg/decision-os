import json

import pytest

from pipeline.llm.base import LLMProviderError, ReviewContext
from pipeline.llm.prompts import (
    REQUIRED_CARD_BLOCKS,
    build_card_user_content,
    parse_and_validate_card,
)


def _valid_card() -> dict:
    return {
        "skill_label": "웹폼 만들고 데이터 저장하기",
        "difficulty": "first_step",
        "estimated_minutes": 30,
        "deliverable": "이름과 메모를 입력해 저장하는 간단한 웹페이지",
        "success_preview": "저장을 누르면 목록에 내가 쓴 내용이 나타난다",
        "prerequisites": "없어요, 바로 시작!",
        "how_to_start": "AI 코딩 도구를 열고 아래 예시 프롬프트를 붙여넣어 시작하세요.",
        "example_prompt": "이름과 메모를 입력받아 저장하는 간단한 웹페이지를 만들어줘.",
        "milestones": [
            {"action": "화면 뼈대 만들기", "done_signal": "입력칸이 화면에 뜬다"},
            {"action": "저장 기능 붙이기", "done_signal": "제출하면 데이터가 남는다"},
            {"action": "확인하고 다듬기", "done_signal": "저장한 내용이 다시 보인다"},
        ],
        "troubleshooting": [
            {"symptom": "저장을 눌러도 반응이 없다", "fix": "'저장 버튼을 눌렀을 때 저장되도록 고쳐줘'라고 요청하세요."},
        ],
        "success_checklist": ["입력칸이 보인다", "저장하면 목록에 나타난다"],
    }


def test_valid_card_passes():
    parse_and_validate_card(json.dumps(_valid_card()))  # 예외 없이 통과


def test_missing_block_raises():
    card = _valid_card()
    del card["deliverable"]
    with pytest.raises(LLMProviderError, match="필수 블록 누락"):
        parse_and_validate_card(json.dumps(card))


def test_bad_difficulty_raises():
    card = _valid_card()
    card["difficulty"] = "expert"
    with pytest.raises(LLMProviderError, match="difficulty"):
        parse_and_validate_card(json.dumps(card))


def test_milestones_out_of_range_raises():
    card = _valid_card()
    card["milestones"] = card["milestones"][:2]  # 2개 → 3~5 위반
    with pytest.raises(LLMProviderError, match="milestones"):
        parse_and_validate_card(json.dumps(card))


def test_non_positive_minutes_raises():
    card = _valid_card()
    card["estimated_minutes"] = 0
    with pytest.raises(LLMProviderError, match="estimated_minutes"):
        parse_and_validate_card(json.dumps(card))


def test_all_required_blocks_present_in_valid_fixture():
    card = _valid_card()
    assert all(k in card for k in REQUIRED_CARD_BLOCKS)


def test_build_card_user_content_includes_topic_and_sources():
    ctx = ReviewContext(
        technology_name="간단한 챗봇",
        signal_sources=[{"source_type": "github", "url": "https://x", "title": "예제"}],
    )
    out = build_card_user_content(ctx)
    assert "간단한 챗봇" in out
    assert "https://x" in out
