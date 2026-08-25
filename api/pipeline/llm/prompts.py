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
  "goal": "이 학습 경로로 사용자가 무엇을 달성하는지 1~2문장. 사용자 역할/기술스택/프로젝트 목표를 반영해 구체적으로.",
  "resources": [
    {"type": "official_docs",    "title": "공식 문서 제목", "url": "https://...", "descriptor": "간단한 설명", "objective": "이 단계에서 무엇을 배우는지 한 줄(한국어)"},
    {"type": "core_material",    "title": "핵심 자료 제목", "url": "https://...", "descriptor": "간단한 설명", "objective": "이 단계에서 무엇을 배우는지 한 줄"},
    {"type": "github",           "title": "GitHub 레포/예제 제목", "url": "https://github.com/...", "descriptor": "간단한 설명", "objective": "이 단계에서 무엇을 배우는지 한 줄"},
    {"type": "practice_example", "title": "실습 예제 제목", "url": "https://...", "descriptor": "간단한 설명", "objective": "이 단계에서 무엇을 배우는지 한 줄"},
    {"type": "applied_idea",     "title": "적용 아이디어 제목", "url": "", "descriptor": "사용자 프로젝트 목표 기반 구체적 적용 아이디어", "objective": "이 단계에서 무엇을 배우는지 한 줄"}
  ]
}
순서를 변경하지 마세요. goal과 각 objective는 반드시 채우세요. 마크다운 없이 JSON만 반환하세요."""

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


LEARNABILITY_KEEP_CATEGORIES = ["new_tool", "tool_update", "technique_research", "framework_library"]
LEARNABILITY_DROP_CATEGORIES = ["business_news", "opinion", "social_ethics", "general_news"]
LEARNABILITY_CATEGORIES = LEARNABILITY_KEEP_CATEGORIES + LEARNABILITY_DROP_CATEGORIES

LEARNABILITY_CLASSIFY_PROMPT = """당신은 AI 기술 큐레이터입니다. 주어진 토픽들이 '학습가치'가 있는지 분류하세요.
판정 기준: "프론트엔드 개발자가 이번 주에 바로 배우거나 코드에 적용할 수 있는가?"

keep=true 카테고리: new_tool(신규 도구/서비스), tool_update(도구 업데이트/릴리스),
technique_research(바로 적용 가능한 기법/연구), framework_library(프레임워크/라이브러리).
keep=false 카테고리: business_news(비즈니스/제휴/투자), opinion(오피니언/인터뷰),
social_ethics(사회·윤리·규제 논쟁), general_news(그 외 잡뉴스).

애매하면 보수적으로 keep=true 로 둡니다(과도한 삭제 금지).
각 토픽에 대해 keep에 맞는 category를 고르고, 사람이 읽기 좋은 짧은 기술명 name(한국어, 40자 이내)을 생성하세요.

반드시 아래 JSON 객체만 반환하세요(마크다운 없이). results 배열은 입력 토픽과 같은 개수·같은 id를 가져야 합니다:
{"results": [{"id": 0, "keep": true, "category": "tool_update", "name": "..."}]}"""

_LEARNABILITY_KEYS = {"id", "keep", "category", "name"}


def build_learnability_user_input(topics: list[dict]) -> str:
    lines = [
        f'- id={t.get("id")} | label={t.get("label", "")} | title={t.get("title", "")}'
        for t in topics
    ]
    return "다음 토픽들을 분류하세요:\n" + "\n".join(lines) + "\n\nJSON 객체로 반환하세요."


def parse_and_validate_learnability(raw: str, expected_count: int) -> list[dict]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise LLMProviderError(f"LLM 응답이 유효한 JSON이 아님: {e}") from e
    if not isinstance(parsed, dict):
        raise LLMProviderError(f"LLM 응답이 JSON 객체가 아님: {type(parsed).__name__}")
    results = parsed.get("results")
    if not isinstance(results, list) or len(results) != expected_count:
        raise LLMProviderError(f"results 개수 불일치: 기대 {expected_count}, 실제 {results!r}")
    for r in results:
        if not isinstance(r, dict) or not _LEARNABILITY_KEYS.issubset(r.keys()):
            raise LLMProviderError(f"result 항목 키 누락: {r}")
        if r["category"] not in LEARNABILITY_CATEGORIES:
            raise LLMProviderError(f"category 허용 목록 밖: {r['category']}")
        if not isinstance(r["name"], str) or not r["name"].strip():
            raise LLMProviderError(f"name 비어있음: {r!r}")
        if not isinstance(r["keep"], bool):
            raise LLMProviderError(f"keep 이 bool 아님: {r!r}")
    return results


REQUIRED_CARD_BLOCKS = [
    "skill_label", "difficulty", "estimated_minutes",
    "deliverable", "success_preview", "prerequisites",
    "how_to_start", "example_prompt",
    "milestones", "troubleshooting", "success_checklist",
]

CARD_DIFFICULTIES = ["first_step", "basic", "challenge"]

PROJECT_CARD_SYSTEM_PROMPT = """당신은 '개발 입문자'를 위한 학습 코치입니다. 주어진 기술/토픽으로 입문자가 직접 만들어보는(바이브코딩) '프로젝트 카드'를 JSON으로 작성하세요.
전문용어를 피하고 쉬운 말로, 누구에게나 동일한 '표준' 내용으로 작성합니다(특정 개인 맞춤 아님).
반드시 아래 11개 키를 모두 포함한 JSON 객체만 반환하세요(마크다운 코드블록 없이):
{
  "skill_label": "이 카드로 배우는 것 (한 줄, 예: '웹폼 만들고 데이터 저장하기')",
  "difficulty": "first_step|basic|challenge 중 하나",
  "estimated_minutes": 30,
  "deliverable": "완성하면 손에 쥐어지는 결과물 (2-3문장)",
  "success_preview": "이렇게 보이면 성공 — 완성 화면/상태 묘사 (1-2문장)",
  "prerequisites": "시작 전 준비물/세팅. 없으면 '없어요, 바로 시작!'",
  "how_to_start": "표준 진입점과 첫 단계 (2-4문장, 누구에게나 동일)",
  "example_prompt": "AI 코딩 도구에 복붙할 수 있는 표준 예시 프롬프트 (구체적으로)",
  "milestones": [{"action": "무엇을 함", "done_signal": "끝나면 이렇게 보임"}],
  "troubleshooting": [{"symptom": "자주 나는 문제/에러", "fix": "복붙하거나 시도할 복구 방법"}],
  "success_checklist": ["다 됐는지 확인할 체크 항목"]
}
규칙:
- milestones는 큰 단계 3~5개만(잘게 쪼개지 말 것 — 지시서가 아니라 지도).
- troubleshooting 최소 1개, success_checklist 최소 1개.
- estimated_minutes는 양의 정수(분).
- 모든 문구는 한국어, 입문자가 겁먹지 않는 친근한 말투."""

_CARD_MILESTONE_KEYS = {"action", "done_signal"}
_CARD_TROUBLE_KEYS = {"symptom", "fix"}


def build_card_user_content(context: ReviewContext) -> str:
    return (
        f"기술/토픽: {context.technology_name}\n\n"
        f"출처:\n{format_sources(context.signal_sources)}\n\n"
        f"위 토픽으로 '개발 입문자'가 직접 만들어볼 수 있는 프로젝트 카드를 JSON으로 작성하세요."
    )


def parse_and_validate_card(raw: str) -> None:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise LLMProviderError(f"LLM 응답이 유효한 JSON이 아님: {e}") from e
    if not isinstance(parsed, dict):
        raise LLMProviderError(f"LLM 응답이 JSON 객체가 아님: {type(parsed).__name__}")
    missing = [k for k in REQUIRED_CARD_BLOCKS if k not in parsed]
    if missing:
        raise LLMProviderError(f"프로젝트 카드에 필수 블록 누락: {missing}")
    if parsed["difficulty"] not in CARD_DIFFICULTIES:
        raise LLMProviderError(f"difficulty 허용 목록 밖: {parsed['difficulty']}")
    minutes = parsed["estimated_minutes"]
    if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
        raise LLMProviderError(f"estimated_minutes가 양의 정수가 아님: {minutes!r}")
    milestones = parsed["milestones"]
    if not isinstance(milestones, list) or not (3 <= len(milestones) <= 5):
        raise LLMProviderError(f"milestones는 3~5개여야 함: {milestones!r}")
    for m in milestones:
        if not isinstance(m, dict) or not _CARD_MILESTONE_KEYS.issubset(m.keys()):
            raise LLMProviderError(f"milestone 항목 키 누락: {m!r}")
    trouble = parsed["troubleshooting"]
    if not isinstance(trouble, list) or len(trouble) < 1:
        raise LLMProviderError(f"troubleshooting은 최소 1개여야 함: {trouble!r}")
    for t in trouble:
        if not isinstance(t, dict) or not _CARD_TROUBLE_KEYS.issubset(t.keys()):
            raise LLMProviderError(f"troubleshooting 항목 키 누락: {t!r}")
    checklist = parsed["success_checklist"]
    if not isinstance(checklist, list) or len(checklist) < 1:
        raise LLMProviderError(f"success_checklist는 최소 1개여야 함: {checklist!r}")
    for c in checklist:
        if not isinstance(c, str) or not c.strip():
            raise LLMProviderError(f"success_checklist 항목이 빈 문자열: {c!r}")
