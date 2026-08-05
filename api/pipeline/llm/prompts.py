import json
from urllib.parse import urlparse

from pipeline.llm.base import (
    ChatContext, LearningPathContext, LLMProviderError, MemoryContext,
    ReviewContext, REQUIRED_SECTIONS,
)

RESEARCH_REVIEW_SYSTEM_PROMPT = """당신은 AI 기술 전문가입니다. 주어진 기술 Signal에 대한 Research Review를 JSON 형식으로 작성하세요.
반드시 다음 13개 키를 포함한 JSON 객체만 반환하세요 (마크다운 코드블록 없이):
{
  "one_line_definition": "한 줄 정의",
  "key_concepts": "핵심 개념 설명",
  "problems_solved": "해결하는 문제",
  "why_it_matters": "왜 중요한가",
  "vs_existing_tech": "기존 기술과 차이",
  "user_relevance": "사용자 관련성",
  "learning_goals": "학습 목표",
  "learning_time_difficulty": {"estimated_hours": 0, "difficulty": "beginner|intermediate|advanced"},
  "practical_applicability": "실무 적용 가능성",
  "risks": "위험 요소",
  "recommendation_reason": "추천 이유",
  "reference_sources": ["출처 URL 또는 설명"],
  "honest_box": {"content": "솔직한 평가", "severity": "standard"}
}
honest_box.severity는 "standard" 또는 "high" 중 하나."""

SIGNAL_BUILD_PROMPT = """다음 AI 기술 Signal의 출처 목록을 바탕으로 JSON으로 반환하세요:
{"title": "기술 단위 통합 제목 (한국어, 50자 이내)", "summary": "핵심 내용 요약 (한국어, 2-3문장)"}
마크다운 없이 JSON만 반환."""

CONTEXTUAL_CHAT_SYSTEM_PROMPT = """당신은 AI 기술 전문가입니다. 사용자가 특정 기술의 Research Review를 읽은 후 질문합니다.
Review의 내용을 기반으로 명확하고 유용한 답변을 제공하세요. 한국어로 답변하세요.
답변은 2-5문장 이내로 간결하게 작성하세요."""

LEARNING_PATH_SYSTEM_PROMPT = """당신은 AI 기술 학습 전문가입니다. 주어진 기술 Signal에 대한 Learning Path를 JSON 형식으로 작성하세요.
반드시 다음 형식을 따르는 JSON 객체만 반환하세요:
{
  "resources": [
    {"type": "official_docs",    "title": "공식 문서 제목", "url": "https://...", "descriptor": "간단한 설명"},
    {"type": "core_material",    "title": "핵심 자료 제목", "url": "https://...", "descriptor": "간단한 설명"},
    {"type": "github",           "title": "GitHub 레포/예제 제목", "url": "https://github.com/...", "descriptor": "간단한 설명"},
    {"type": "practice_example", "title": "실습 예제 제목", "url": "https://...", "descriptor": "간단한 설명"},
    {"type": "applied_idea",     "title": "적용 아이디어 제목", "url": "", "descriptor": "사용자 프로젝트 목표 기반 구체적 적용 아이디어"}
  ]
}
순서를 변경하지 마세요. 마크다운 없이 JSON만 반환하세요."""

LEARNING_PATH_RESOURCE_TYPES = [
    "official_docs", "core_material", "github", "practice_example", "applied_idea",
]

MEMORY_EXTRACTION_SYSTEM_PROMPT = """당신은 사용자의 학습/의사결정 이력에서 재사용 가능한 Memory를 추출하는 전문가입니다.
주어진 Decision Loop 체인(Signal-Review-Decision-Outcome)을 분석해 아래 5가지 memory_type 중 가장 적절한 하나를 선택하고 summary를 작성하세요:
- preference: 사용자의 기술 선호/성향
- skill: 사용자가 습득했거나 시도한 기술/역량
- project: 사용자의 프로젝트 맥락/목표
- decision_history: 특정 기술에 대한 의사결정 이력
- outcome_history: 학습/적용 결과 이력
반드시 다음 형식의 JSON 객체만 반환하세요 (마크다운 코드블록 없이):
{"memory_type": "preference|skill|project|decision_history|outcome_history 중 하나", "summary": "한국어 요약 (1-2문장)"}"""

ALLOWED_MEMORY_TYPES = ["preference", "skill", "project", "decision_history", "outcome_history"]

_LEARNING_PATH_RESOURCE_KEYS = {"type", "title", "url", "descriptor"}


def format_sources(signal_sources: list[dict]) -> str:
    return "\n".join(
        f"- [{s.get('source_type', 'other')}] {s.get('title', '')} ({s.get('url', '')})"
        for s in signal_sources
    )


def build_signal_user_input(technology_name: str, signal_sources: list[dict]) -> str:
    return (
        f"기술: {technology_name}\n출처:\n{format_sources(signal_sources)}\n\n"
        f"결과를 JSON 객체로 반환하세요."
    )


def build_chat_user_input(context: ChatContext) -> str:
    review_summary = ""
    if context.review_payload:
        one_line = context.review_payload.get("one_line_definition", "")
        recommendation = context.review_payload.get("recommendation_reason", "")
        review_summary = f"Review 요약: {one_line}\n추천 이유: {recommendation}"
    return f"{review_summary}\n\n사용자 질문: {context.user_message}"


def build_review_user_content(context: ReviewContext) -> str:
    user_ctx = []
    if context.user_role:
        user_ctx.append(f"역할: {context.user_role}")
    if context.user_experience_level:
        user_ctx.append(f"경험: {context.user_experience_level}")
    if context.user_tech_stack:
        user_ctx.append(f"기술스택: {', '.join(context.user_tech_stack)}")
    if context.user_interests:
        user_ctx.append(f"관심사: {', '.join(context.user_interests)}")
    return (
        f"기술: {context.technology_name}\n\n"
        f"출처:\n{format_sources(context.signal_sources)}\n\n"
        f"사용자 컨텍스트:\n" + "\n".join(user_ctx)
    )


def build_learning_path_user_content(context: LearningPathContext) -> str:
    sources = "\n".join(
        f"- [{s.get('source_type')}] {s.get('title')} ({s.get('url')})"
        for s in context.signal_sources
    )
    return (
        f"기술명: {context.technology_name}\n"
        f"요약: {context.signal_summary}\n"
        f"출처:\n{sources}\n"
        f"사용자 역할: {context.user_role or '미지정'}\n"
        f"기술 스택: {', '.join(context.user_tech_stack) or '미지정'}\n"
        f"프로젝트 목표: {context.user_project_goal or '미지정'}\n"
        f"경험 수준: {context.user_experience_level or '미지정'}"
    )


def build_memory_user_content(context: MemoryContext) -> str:
    return (
        f"기술명: {context.technology_name or '미지정'}\n"
        f"Review 한줄정의: {context.review_one_line_definition or '미지정'}\n"
        f"Decision 선택: {context.decision_choice}\n"
        f"Decision 메모: {context.decision_memo or '없음'}\n"
        f"Outcome 상태: {context.outcome_status}\n"
        f"Outcome 유용함: {context.outcome_useful if context.outcome_useful is not None else '미지정'}\n"
        f"Outcome 실제 학습 시간(분): "
        f"{context.outcome_actual_learning_time_min if context.outcome_actual_learning_time_min is not None else '미지정'}\n"
        f"Outcome 메모: {context.outcome_memo or '없음'}\n"
        f"Outcome 적용 노트: {context.outcome_applied_project_note or '없음'}"
    )


def _validate_learning_path_resources(resources: list) -> None:
    for r in resources:
        if not isinstance(r, dict) or not _LEARNING_PATH_RESOURCE_KEYS.issubset(r.keys()):
            raise LLMProviderError(f"resource 항목에 필수 키 누락: {r}")
        url = r.get("url") or ""
        if url and urlparse(url).scheme not in ("http", "https"):
            raise LLMProviderError(f"resource url 스킴이 http/https가 아님: {url}")


def parse_and_validate_review(raw: str) -> None:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise LLMProviderError(f"LLM 응답이 JSON 객체가 아님: {type(parsed).__name__}")
    missing = [k for k in REQUIRED_SECTIONS if k not in parsed]
    if missing:
        raise LLMProviderError(f"LLM 응답에 필수 섹션 누락: {missing}")


def parse_and_validate_learning_path(raw: str) -> None:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise LLMProviderError(f"LLM 응답이 JSON 객체가 아님: {type(parsed).__name__}")
    resources = parsed.get("resources")
    if not isinstance(resources, list) or len(resources) != 5:
        raise LLMProviderError(f"LLM 응답에 5개 리소스 배열이 없음: {resources}")
    _validate_learning_path_resources(resources)


def parse_and_validate_memory(raw: str) -> None:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise LLMProviderError(f"LLM 응답이 JSON 객체가 아님: {type(parsed).__name__}")
    memory_type = parsed.get("memory_type")
    summary = parsed.get("summary")
    if memory_type not in ALLOWED_MEMORY_TYPES:
        raise LLMProviderError(f"memory_type이 허용 목록 밖: {memory_type}")
    if not isinstance(summary, str) or not summary.strip():
        raise LLMProviderError(f"summary가 비어있음: {summary!r}")
