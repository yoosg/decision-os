"""눈 점검 하네스의 순수 함수 테스트 (LLM 호출 없음).

LLM 실호출 경로(run)는 dev/ops 실행 경로라 테스트하지 않는다 —
기존 test_eval_engagement.py가 DB 읽기(load_*)를 빼고 compute_metrics만 테스트하는 것과 같다.
"""
import json

from scripts.eval_card_guardrails import (
    EVAL_TOPICS,
    render_markdown,
    summarize_card,
)


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
        "milestones": [{"action": "화면 만들기", "done_signal": "입력칸이 뜬다"}],
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
