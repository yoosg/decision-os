"""눈 점검 하네스의 순수 함수 테스트 (LLM 호출 없음) + run()의 실패 격리·프로바이더 가드 테스트.

LLM 실호출 자체(generate_card가 실제로 뭘 반환하는가)는 dev/ops 실행 경로라 테스트하지 않는다 —
기존 test_eval_engagement.py가 DB 읽기(load_*)를 빼고 compute_metrics만 테스트하는 것과 같다.
run()은 factory.get_llm_provider()와 core.config.settings를 몽키패치해 MockLLMProvider로
대체함으로써 네트워크 호출 없이 테스트한다(test_llm_factory.py가 같은 자리에서
`patch("pipeline.llm.factory.settings")`로 settings를 패치하는 선례를 따른다).
"""
import json

import pytest

from pipeline.llm.base import LLMProviderError
from scripts.eval_card_guardrails import (
    EVAL_TOPICS,
    render_markdown,
    run,
    summarize_card,
)
from tests.mocks import MockLLMProvider


def _card(**overrides) -> str:
    payload = {
        "project_title": "메모를 저장하는 나만의 웹페이지 만들기",
        "topic_link": "새 모델 발표의 핵심인 '기억해두기'를 직접 만들어봅니다.",
        "skill_label": "웹폼 만들고 데이터 저장하기",
        "difficulty": "first_step",
        "estimated_minutes": 30,
        "deliverable": "이름과 메모를 입력해 저장하는 간단한 웹페이지",
        "success_preview": "저장을 누르면 목록에 내가 쓴 내용이 나타난다",
        "prerequisites": "없어요, 바로 시작!",
        "how_to_start": "AI 코딩 도구를 열고 예시 프롬프트를 붙여넣으세요.",
        "example_prompt": "메모를 저장하는 웹페이지를 만들어줘.",
        # parse_and_validate_card는 milestones 3~5개를 요구한다(api/pipeline/llm/prompts.py) —
        # 1개짜리는 "정상 카드"로 읽히지만 실제로는 검증을 절대 통과 못 하는 값이라 3개로 맞춘다(M5).
        "milestones": [
            {"action": "화면 만들기", "done_signal": "입력칸이 뜬다"},
            {"action": "저장 기능 붙이기", "done_signal": "제출하면 데이터가 남는다"},
            {"action": "확인하고 다듬기", "done_signal": "저장한 내용이 다시 보인다"},
        ],
        "troubleshooting": [{"symptom": "저장이 안 됨", "fix": "콘솔 에러를 붙여넣고 물어보기"}],
        "success_checklist": ["저장한 내용이 다시 보인다"],
    }
    payload.update(overrides)
    return json.dumps(payload, ensure_ascii=False)


def test_eval_topics_cover_four_guardrail_targets():
    """토픽 4개는 스펙이 지정한 '노리는 실패' 4종을 하나씩 겨냥해야 한다."""
    assert len(EVAL_TOPICS) == 4
    for topic in EVAL_TOPICS:
        assert topic["technology_name"].strip()
        assert topic["aims_at"].strip()
        assert topic["signal_sources"], "출처가 비면 프롬프트 입력이 실제와 달라진다"


def test_summarize_card_extracts_eye_check_fields():
    result = summarize_card(_card())
    assert result["project_title"] == "메모를 저장하는 나만의 웹페이지 만들기"
    assert result["topic_link"] == "새 모델 발표의 핵심인 '기억해두기'를 직접 만들어봅니다."
    assert result["skill_label"] == "웹폼 만들고 데이터 저장하기"
    assert result["difficulty"] == "first_step"
    assert result["estimated_minutes"] == "30"
    assert result["prerequisites"] == "없어요, 바로 시작!"
    assert result["deliverable"] == "이름과 메모를 입력해 저장하는 간단한 웹페이지"


def test_summarize_card_marks_missing_field_instead_of_raising():
    """필드가 빠진 카드도 눈 점검 대상이다 — 누락 자체가 관찰할 사실이라 죽지 않는다."""
    payload = json.loads(_card())
    del payload["prerequisites"]
    result = summarize_card(json.dumps(payload, ensure_ascii=False))
    assert result["prerequisites"] == "<누락>"
    assert result["project_title"] == "메모를 저장하는 나만의 웹페이지 만들기"


def test_summarize_card_marks_invalid_json_instead_of_raising():
    result = summarize_card("이건 JSON이 아님")
    assert all("JSON 파싱 실패" in v for v in result.values())


def test_render_markdown_includes_topic_aim_and_fields():
    rows = [
        {
            "technology_name": "Omarchy — Arch Linux 기반 개발 환경",
            "aims_at": "셋업형 만들거리",
            **summarize_card(_card()),
        }
    ]
    report = render_markdown(rows)
    assert "Omarchy — Arch Linux 기반 개발 환경" in report
    assert "셋업형 만들거리" in report
    assert "없어요, 바로 시작!" in report
    assert "합격 기준" in report, "리포트만 보고도 무엇을 판정해야 하는지 알 수 있어야 한다"
    assert "새 모델 발표의 핵심인 '기억해두기'를 직접 만들어봅니다." in report, "topic_link가 빠지면 도피(개념체험형 우회) 판정을 deliverable만으로 추론해야 한다(I3)"
    assert "웹폼 만들고 데이터 저장하기" in report
    assert "30분" in report


def test_render_markdown_omits_minute_suffix_for_missing_value():
    """estimated_minutes가 <누락>이면 '<누락>분'처럼 이어붙이지 않는다(M4)."""
    rows = [
        {
            "technology_name": "토픽",
            "aims_at": "노림",
            **summarize_card(_card()),
        }
    ]
    rows[0]["estimated_minutes"] = "<누락>"
    report = render_markdown(rows)
    assert "<누락>분" not in report
    assert "<누락>" in report


def test_render_markdown_header_shows_provenance():
    """provider/model/생성시각이 리포트 헤더에 찍혀야, 파일만 보고도 어떤 프로바이더 결과인지 안다(I2)."""
    rows = [
        {
            "technology_name": "토픽",
            "aims_at": "노림",
            **summarize_card(_card()),
        }
    ]
    meta = {"provider": "openai", "model": "gpt-4o", "generated_at": "2026-09-04 00:00 UTC"}
    report = render_markdown(rows, meta)
    assert "openai" in report
    assert "gpt-4o" in report
    assert "2026-09-04 00:00 UTC" in report


def test_render_markdown_without_meta_still_renders():
    """meta 없이도(예: 과거 저장물 재렌더) 깨지지 않는다."""
    rows = [
        {
            "technology_name": "토픽",
            "aims_at": "노림",
            **summarize_card(_card()),
        }
    ]
    report = render_markdown(rows)
    assert "합격 기준" in report


def test_run_continues_past_a_failed_topic_instead_of_losing_the_rest(monkeypatch):
    """4개 중 하나가 LLMProviderError로 죽어도 나머지 3개는 수집돼야 한다(I1).

    generate_card는 내부에서 이미 parse_and_validate_card로 검증하므로(성공 시 raw는 항상
    온전한 JSON) — 여기서 잡을 실패는 malformed JSON이 아니라 타임아웃/429 같은
    LLMProviderError다. try/except 없이 for loop에 맡기면 그 예외가 loop 전체를 죽인다.
    """
    call_count = {"n": 0}

    class FlakyProvider(MockLLMProvider):
        def generate_card(self, context):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise LLMProviderError("일시적 타임아웃")
            return super().generate_card(context)

    monkeypatch.setattr(
        "pipeline.llm.factory.get_llm_provider", lambda: FlakyProvider()
    )
    monkeypatch.setattr("core.config.settings.llm_provider", "openai")

    rows, meta = run()

    assert call_count["n"] == len(EVAL_TOPICS), "실패한 토픽 이후에도 나머지 토픽 호출이 계속돼야 한다"
    assert len(rows) == len(EVAL_TOPICS), "실패한 토픽도 (성공 대신) 실패 행으로 결과에 남아야 한다"
    failed_row = rows[1]
    assert failed_row["technology_name"] == EVAL_TOPICS[1]["technology_name"]
    assert "생성 실패" in failed_row["project_title"]
    assert "일시적 타임아웃" in failed_row["project_title"]
    ok_rows = [r for i, r in enumerate(rows) if i != 1]
    for r in ok_rows:
        assert "생성 실패" not in r["project_title"]
    assert meta["provider"] == "openai"
    assert meta["model"] == "mock"


def test_run_exits_without_calling_provider_when_not_openai(monkeypatch):
    """openai가 아닌 프로바이더면 --allow-non-openai 없이는 호출 자체가 없어야 한다(I2).

    로컬 .env가 gemini일 수 있는데, 이 가드가 없으면 잘못된 모델로 유료 호출 4회를 태우고도
    리포트만 보면 어느 프로바이더였는지 알 수 없다.
    """
    calls = {"n": 0}

    def fake_get_llm_provider():
        calls["n"] += 1
        return MockLLMProvider()

    monkeypatch.setattr("pipeline.llm.factory.get_llm_provider", fake_get_llm_provider)
    monkeypatch.setattr("core.config.settings.llm_provider", "gemini")

    with pytest.raises(SystemExit):
        run()

    assert calls["n"] == 0, "가드를 통과하기 전에 프로바이더가 생성/호출되면 안 된다"


def test_run_allows_non_openai_with_explicit_flag(monkeypatch):
    monkeypatch.setattr(
        "pipeline.llm.factory.get_llm_provider", lambda: MockLLMProvider()
    )
    monkeypatch.setattr("core.config.settings.llm_provider", "gemini")

    rows, meta = run(allow_non_openai=True)

    assert len(rows) == len(EVAL_TOPICS)
    assert meta["provider"] == "gemini"
