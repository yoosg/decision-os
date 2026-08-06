# LLM Provider Toggle (OpenAI ↔ Gemini) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `LLM_PROVIDER` 플래그 하나로 텍스트 생성 경로를 OpenAI와 Gemini 사이에서 토글할 수 있게 하고, 임베딩은 항상 OpenAI로 유지한다.

**Architecture:** `LLMProvider` ABC를 구현하는 `GeminiProvider`를 추가한다. 프롬프트 상수·user content 빌더·JSON 검증을 `pipeline/llm/prompts.py` 공유 모듈로 추출해 두 프로바이더가 재사용한다. 프로바이더 생성은 `pipeline/llm/factory.py`의 `get_llm_provider()` 한 곳으로 통일하고, 7개 호출부가 이를 쓰게 바꾼다. GeminiProvider의 `embed_text`는 내부 OpenAI 임베더에 위임하고, 프리티어 429에 대비해 재시도/백오프를 넣는다.

**Tech Stack:** Python 3.11, FastAPI, pydantic-settings 2.7, `openai>=1.82`, 신규 `google-genai`, pytest 8 (`asyncio_mode=auto`, `testpaths=tests`), `unittest.mock`.

## Global Constraints

- 작업 디렉터리: `api/` (모든 경로는 `api/` 기준). 테스트 실행도 `api/`에서.
- 임베딩은 항상 OpenAI. `memories.embedding`은 `vector(1536)`이며 재임베딩/마이그레이션 금지.
- 임베딩 차원 검증 유지: `embed_text` 결과 길이 != 1536이면 `LLMProviderError`.
- 모든 프로바이더 예외(rate-limit 포함)는 `LLMProviderError`로 표준화.
- Gemini 기본 모델: `gemini-2.5-flash` (env `GEMINI_MODEL`로 오버라이드).
- `llm_provider`는 `Literal["openai", "gemini"]`로 강제(오타 방지). 기본값 `"openai"`.
- 기존 OpenAI 동작·프롬프트·JSON 구조는 불변(리팩터는 순수 이동, 동작 변경 없음).
- 테스트는 실제 네트워크 없이 mock으로 통과해야 함(환경변수 불필요).
- Git이 초기화돼 있지 않으면 커밋 단계는 생략하고 나머지 단계만 수행.

---

### Task 1: config에 LLM 프로바이더 설정 추가

**Files:**
- Modify: `api/core/config.py` (Settings 클래스 필드 + 경고)
- Test: `api/tests/test_config_llm_provider.py`

**Interfaces:**
- Produces: `Settings.llm_provider: Literal["openai","gemini"]`, `Settings.gemini_api_key: str`, `Settings.gemini_model: str`, `Settings.gemini_max_retries: int`, `Settings.gemini_request_delay_sec: float`.

- [ ] **Step 1: Write the failing test**

```python
# api/tests/test_config_llm_provider.py
import warnings
import pytest
from pydantic import ValidationError
from core.config import Settings


def test_llm_provider_defaults_to_openai():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        s = Settings(_env_file=None)
    assert s.llm_provider == "openai"
    assert s.openai_model == "gpt-4o-mini"  # 비용 절감: 기본 모델을 mini로
    assert s.gemini_model == "gemini-2.5-flash"
    assert s.gemini_max_retries == 4
    assert s.gemini_request_delay_sec == 0.0


def test_llm_provider_accepts_gemini():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        s = Settings(_env_file=None, llm_provider="gemini")
    assert s.llm_provider == "gemini"


def test_llm_provider_rejects_unknown_value():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, llm_provider="claude")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && python -m pytest tests/test_config_llm_provider.py -v`
Expected: FAIL (`llm_provider` 속성 없음 → AttributeError/ValidationError)

- [ ] **Step 3: Write minimal implementation**

`api/core/config.py`의 `Settings` 클래스에서:

먼저 기존 `openai_model` 기본값을 비용 절감을 위해 `gpt-4o-mini`로 변경한다:

```python
    openai_model: str = "gpt-4o-mini"   # 기존 "gpt-4o" → 비용 절감(테스트 기본)
```

그리고 `collector_mode` 필드 위(또는 openai 필드 아래)에 추가:

```python
    # LLM 프로바이더 토글 — "openai"(기본) | "gemini"(테스트/프리티어)
    # Literal로 강제: 오타가 조용히 잘못된 경로로 빠지지 않게 로드 시 검증.
    llm_provider: Literal["openai", "gemini"] = "openai"
    gemini_api_key: str = Field(default="", repr=False)
    gemini_model: str = "gemini-2.5-flash"
    # 프리티어 rate-limit 방어: 429 시 지수 백오프 재시도 횟수 + 호출 간 최소 간격(초)
    gemini_max_retries: int = 4
    gemini_request_delay_sec: float = 0.0
```

그리고 `check_required_settings` 모델 검증기 안, `openai_api_key` 경고 블록 뒤에 추가:

```python
        if self.llm_provider == "gemini" and not self.gemini_api_key:
            warnings.warn(
                "LLM_PROVIDER=gemini but GEMINI_API_KEY is not set — Gemini calls will fail",
                RuntimeWarning,
                stacklevel=2,
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd api && python -m pytest tests/test_config_llm_provider.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit** (git 초기화된 경우만)

```bash
git add api/core/config.py api/tests/test_config_llm_provider.py
git commit -m "feat(config): add llm_provider toggle + gemini settings"
```

---

### Task 2: 프롬프트·검증 로직 공유 모듈로 추출

`OpenAIProvider` 안에만 있던 프롬프트 상수·user content 빌더·JSON 검증을 `prompts.py`로 옮기고, `OpenAIProvider`가 이를 import해서 쓰도록 바꾼다(동작 불변, 순수 이동).

**Files:**
- Create: `api/pipeline/llm/prompts.py`
- Modify: `api/pipeline/llm/openai_provider.py` (상수/헬퍼를 import로 대체)
- Test: `api/tests/test_llm_prompts_shared.py` + 기존 `api/tests/test_signal_builder_reviewer.py`(회귀)

**Interfaces:**
- Produces (module-level, from `pipeline.llm.prompts`):
  - 상수: `RESEARCH_REVIEW_SYSTEM_PROMPT`, `SIGNAL_BUILD_PROMPT`, `CONTEXTUAL_CHAT_SYSTEM_PROMPT`, `LEARNING_PATH_SYSTEM_PROMPT`, `MEMORY_EXTRACTION_SYSTEM_PROMPT`, `LEARNING_PATH_RESOURCE_TYPES`, `ALLOWED_MEMORY_TYPES`
  - 함수:
    - `format_sources(signal_sources: list[dict]) -> str`
    - `build_review_user_content(context: ReviewContext) -> str`
    - `build_learning_path_user_content(context: LearningPathContext) -> str`
    - `build_memory_user_content(context: MemoryContext) -> str`
    - `build_signal_user_input(technology_name: str, signal_sources: list[dict]) -> str`
    - `build_chat_user_input(context: ChatContext) -> str`
    - `parse_and_validate_review(raw: str) -> None` (검증 실패 시 `LLMProviderError`)
    - `parse_and_validate_learning_path(raw: str) -> None`
    - `parse_and_validate_memory(raw: str) -> None`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && python -m pytest tests/test_llm_prompts_shared.py -v`
Expected: FAIL (`pipeline.llm.prompts` 모듈 없음 → ImportError)

- [ ] **Step 3: Write minimal implementation**

`api/pipeline/llm/prompts.py` 생성. 아래 내용은 현재 `openai_provider.py`(11~78, 226~274줄)에서 상수·빌더·검증을 그대로 옮긴 것이다:

```python
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
```

이어서 `api/pipeline/llm/openai_provider.py`를 수정한다:
1. 11~78줄의 상수·`_validate_learning_path_resources`·`_LEARNING_PATH_RESOURCE_KEYS`·`LEARNING_PATH_RESOURCE_TYPES`·`ALLOWED_MEMORY_TYPES` 정의를 삭제하고, 상단 import를 다음으로 교체:

```python
import json
from openai import OpenAI, OpenAIError

from pipeline.llm.base import (
    ChatContext, LearningPathContext, LLMProvider, LLMProviderError, LLMResponse, MemoryContext,
    ReviewContext,
)
from pipeline.llm import prompts
```

2. 각 메서드에서 로컬 상수/헬퍼 호출을 `prompts.*`로 치환하고, 검증은 공유 함수로 위임:
   - `generate`: `instructions=prompts.RESEARCH_REVIEW_SYSTEM_PROMPT`, `input=f"{prompts.build_review_user_content(context)}\n\n반드시 JSON 객체로 응답하세요."`, 응답 후 `prompts.parse_and_validate_review(raw)` 호출 뒤 `return LLMResponse(content=raw, model=self._model)`.
   - `build_signal_title_summary`: `instructions=prompts.SIGNAL_BUILD_PROMPT`, `input=prompts.build_signal_user_input(technology_name, signal_sources)`.
   - `chat`: `instructions=prompts.CONTEXTUAL_CHAT_SYSTEM_PROMPT`, `input=prompts.build_chat_user_input(context)`.
   - `generate_learning_path`: `instructions=prompts.LEARNING_PATH_SYSTEM_PROMPT`, `input=f"{prompts.build_learning_path_user_content(context)}\n\n반드시 JSON 객체로 응답하세요."`, 검증 `prompts.parse_and_validate_learning_path(raw)`.
   - `extract_memory`: `instructions=prompts.MEMORY_EXTRACTION_SYSTEM_PROMPT`, `input=f"{prompts.build_memory_user_content(context)}\n\n반드시 JSON 객체로 응답하세요."`, 검증 `prompts.parse_and_validate_memory(raw)`.
   - `_build_user_content`, `_build_learning_path_content`, `_build_memory_content` 인스턴스 메서드는 삭제(공유 함수로 대체됨).
   - `embed_text`는 변경 없음.

- [ ] **Step 4: Run test to verify it passes (신규 + 회귀)**

Run: `cd api && python -m pytest tests/test_llm_prompts_shared.py tests/test_signal_builder_reviewer.py -v`
Expected: PASS (신규 5개 + 기존 signal_builder/reviewer 테스트 전부 통과 — 리팩터가 동작을 바꾸지 않음)

- [ ] **Step 5: Commit** (git 초기화된 경우만)

```bash
git add api/pipeline/llm/prompts.py api/pipeline/llm/openai_provider.py api/tests/test_llm_prompts_shared.py
git commit -m "refactor(llm): extract shared prompts and validators to prompts.py"
```

---

### Task 3: GeminiProvider 구현 (텍스트 생성 + 임베딩 위임 + 재시도)

**Files:**
- Create: `api/pipeline/llm/gemini_provider.py`
- Modify: `api/requirements.txt` (`google-genai` 추가)
- Test: `api/tests/test_gemini_provider.py`

**Interfaces:**
- Consumes: `pipeline.llm.prompts.*` (Task 2), `pipeline.llm.openai_provider.OpenAIProvider` (임베딩 위임), `pipeline.llm.base.LLMProvider/LLMResponse/LLMProviderError` 및 context dataclass들.
- Produces:
  - `class GeminiProvider(LLMProvider)`
  - `GeminiProvider(gemini_api_key: str, model: str = "gemini-2.5-flash", openai_api_key: str = "", embedding_model: str = "text-embedding-3-small", max_retries: int = 4, request_delay_sec: float = 0.0, client=None, embedder=None)`
  - 6개 생성 메서드 + `embed_text` (LLMProvider 전체 구현).
  - `_is_rate_limit(exc) -> bool`, `_generate(system_instruction, contents, as_json) -> str` (내부).

- [ ] **Step 1: Write the failing test**

```python
# api/tests/test_gemini_provider.py
import json
from unittest.mock import MagicMock
import pytest

from pipeline.llm.base import (
    ChatContext, LearningPathContext, LLMProviderError, MemoryContext, ReviewContext,
)
from pipeline.llm.gemini_provider import GeminiProvider
from tests.mocks import VALID_13_SECTION_RESPONSE


def _client_returning(*texts):
    """models.generate_content가 순서대로 text를 반환하는 fake genai client."""
    client = MagicMock()
    responses = [MagicMock(text=t) for t in texts]
    client.models.generate_content.side_effect = responses
    return client


def _provider(client, embedder=None):
    return GeminiProvider(
        gemini_api_key="k", model="gemini-2.5-flash",
        openai_api_key="ok", embedding_model="text-embedding-3-small",
        max_retries=4, request_delay_sec=0.0, client=client, embedder=embedder,
    )


def test_build_signal_title_summary_returns_content():
    client = _client_returning('{"title": "제목", "summary": "요약"}')
    resp = _provider(client).build_signal_title_summary("LangGraph", [])
    assert json.loads(resp.content)["title"] == "제목"
    # JSON 모드로 호출됐는지 확인
    kwargs = client.models.generate_content.call_args.kwargs
    assert kwargs["config"].response_mime_type == "application/json"


def test_generate_validates_13_sections():
    client = _client_returning(VALID_13_SECTION_RESPONSE)
    ctx = ReviewContext(technology_name="LangGraph", signal_sources=[])
    resp = _provider(client).generate(ctx)
    assert "one_line_definition" in resp.content


def test_generate_raises_on_missing_section():
    client = _client_returning('{"one_line_definition": "x"}')
    ctx = ReviewContext(technology_name="LangGraph", signal_sources=[])
    with pytest.raises(LLMProviderError):
        _provider(client).generate(ctx)


def test_chat_returns_plain_text_without_json_mode():
    client = _client_returning("안녕하세요, 답변입니다.")
    ctx = ChatContext(signal_id="s1", user_message="질문")
    resp = _provider(client).chat(ctx)
    assert resp.content == "안녕하세요, 답변입니다."
    kwargs = client.models.generate_content.call_args.kwargs
    assert kwargs["config"].response_mime_type is None


def test_embed_text_delegates_to_openai_embedder():
    embedder = MagicMock()
    embedder.embed_text.return_value = [0.0] * 1536
    out = _provider(_client_returning(), embedder=embedder).embed_text("hi")
    assert len(out) == 1536
    embedder.embed_text.assert_called_once_with("hi")


def test_retry_on_rate_limit_then_succeeds(monkeypatch):
    import pipeline.llm.gemini_provider as gp
    monkeypatch.setattr(gp.time, "sleep", lambda *_: None)
    client = MagicMock()
    client.models.generate_content.side_effect = [
        Exception("429 RESOURCE_EXHAUSTED: quota"),
        MagicMock(text='{"title": "t", "summary": "s"}'),
    ]
    resp = _provider(client).build_signal_title_summary("X", [])
    assert json.loads(resp.content)["title"] == "t"
    assert client.models.generate_content.call_count == 2


def test_retry_exhausted_raises_llm_error(monkeypatch):
    import pipeline.llm.gemini_provider as gp
    monkeypatch.setattr(gp.time, "sleep", lambda *_: None)
    client = MagicMock()
    client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED")
    with pytest.raises(LLMProviderError):
        _provider(client).build_signal_title_summary("X", [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && python -m pytest tests/test_gemini_provider.py -v`
Expected: FAIL (`pipeline.llm.gemini_provider` 모듈 없음 → ImportError)

- [ ] **Step 3: Write minimal implementation**

`api/requirements.txt` 끝에 한 줄 추가:

```
google-genai>=1.0.0
```

그리고 `pip install -r requirements.txt` (또는 `pip install "google-genai>=1.0.0"`)로 설치.

`api/pipeline/llm/gemini_provider.py` 생성:

```python
import time

from google import genai
from google.genai import types

from pipeline.llm import prompts
from pipeline.llm.base import (
    ChatContext, LearningPathContext, LLMProvider, LLMProviderError, LLMResponse,
    MemoryContext, ReviewContext,
)
from pipeline.llm.openai_provider import OpenAIProvider

_RATE_LIMIT_MARKERS = ("429", "RESOURCE_EXHAUSTED", "rate limit", "quota")


class GeminiProvider(LLMProvider):
    """Gemini 텍스트 생성 구현체. 임베딩은 OpenAI에 위임(설계 결정 1)."""

    def __init__(
        self,
        gemini_api_key: str,
        model: str = "gemini-2.5-flash",
        openai_api_key: str = "",
        embedding_model: str = "text-embedding-3-small",
        max_retries: int = 4,
        request_delay_sec: float = 0.0,
        client=None,
        embedder=None,
    ) -> None:
        self._client = client or genai.Client(api_key=gemini_api_key)
        self._model = model
        self._max_retries = max_retries
        self._request_delay_sec = request_delay_sec
        # 임베딩은 항상 OpenAI. 테스트 주입 가능(embedder).
        self._embedder = embedder or OpenAIProvider(
            api_key=openai_api_key, embedding_model=embedding_model
        )

    @staticmethod
    def _is_rate_limit(exc: Exception) -> bool:
        code = getattr(exc, "code", None)
        if code in (429, 503):
            return True
        text = str(exc)
        return any(m in text for m in _RATE_LIMIT_MARKERS)

    def _generate(self, system_instruction: str, contents: str, as_json: bool) -> str:
        """generate_content 호출 + 프리티어 429 백오프 재시도. 실패 시 LLMProviderError."""
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json" if as_json else None,
        )
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                if self._request_delay_sec:
                    time.sleep(self._request_delay_sec)
                response = self._client.models.generate_content(
                    model=self._model, contents=contents, config=config,
                )
                return response.text or ""
            except Exception as e:  # noqa: BLE001 — 재시도 분류 후 표준화
                last_exc = e
                if self._is_rate_limit(e) and attempt < self._max_retries - 1:
                    time.sleep(2 ** (attempt + 1))  # 2s, 4s, 8s...
                    continue
                raise LLMProviderError(str(e)) from e
        raise LLMProviderError(str(last_exc))

    def generate(self, context: ReviewContext) -> LLMResponse:
        raw = self._generate(
            prompts.RESEARCH_REVIEW_SYSTEM_PROMPT,
            prompts.build_review_user_content(context), as_json=True,
        )
        prompts.parse_and_validate_review(raw)
        return LLMResponse(content=raw, model=self._model)

    def build_signal_title_summary(self, technology_name: str, signal_sources: list[dict]) -> LLMResponse:
        raw = self._generate(
            prompts.SIGNAL_BUILD_PROMPT,
            prompts.build_signal_user_input(technology_name, signal_sources), as_json=True,
        )
        return LLMResponse(content=raw, model=self._model)

    def chat(self, context: ChatContext) -> LLMResponse:
        raw = self._generate(
            prompts.CONTEXTUAL_CHAT_SYSTEM_PROMPT,
            prompts.build_chat_user_input(context), as_json=False,
        )
        return LLMResponse(content=raw, model=self._model)

    def generate_learning_path(self, context: LearningPathContext) -> LLMResponse:
        raw = self._generate(
            prompts.LEARNING_PATH_SYSTEM_PROMPT,
            prompts.build_learning_path_user_content(context), as_json=True,
        )
        prompts.parse_and_validate_learning_path(raw)
        return LLMResponse(content=raw, model=self._model)

    def extract_memory(self, context: MemoryContext) -> LLMResponse:
        raw = self._generate(
            prompts.MEMORY_EXTRACTION_SYSTEM_PROMPT,
            prompts.build_memory_user_content(context), as_json=True,
        )
        prompts.parse_and_validate_memory(raw)
        return LLMResponse(content=raw, model=self._model)

    def embed_text(self, text: str) -> list[float]:
        return self._embedder.embed_text(text)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd api && python -m pytest tests/test_gemini_provider.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit** (git 초기화된 경우만)

```bash
git add api/pipeline/llm/gemini_provider.py api/requirements.txt api/tests/test_gemini_provider.py
git commit -m "feat(llm): add GeminiProvider with retry and OpenAI embedding delegation"
```

---

### Task 4: 프로바이더 팩토리

**Files:**
- Create: `api/pipeline/llm/factory.py`
- Test: `api/tests/test_llm_factory.py`

**Interfaces:**
- Consumes: `core.config.settings`, `OpenAIProvider`, `GeminiProvider`.
- Produces: `get_llm_provider() -> LLMProvider` — `settings.llm_provider` 값에 따라 프로바이더 인스턴스 반환.

- [ ] **Step 1: Write the failing test**

```python
# api/tests/test_llm_factory.py
from unittest.mock import patch
from pipeline.llm.factory import get_llm_provider
from pipeline.llm.openai_provider import OpenAIProvider
from pipeline.llm.gemini_provider import GeminiProvider


def test_factory_returns_openai_by_default():
    with patch("pipeline.llm.factory.settings") as s:
        s.llm_provider = "openai"
        s.openai_api_key = "k"; s.openai_model = "gpt-4o"
        s.openai_embedding_model = "text-embedding-3-small"
        assert isinstance(get_llm_provider(), OpenAIProvider)


def test_factory_returns_gemini_when_flagged():
    with patch("pipeline.llm.factory.settings") as s:
        s.llm_provider = "gemini"
        s.gemini_api_key = "gk"; s.gemini_model = "gemini-2.5-flash"
        s.gemini_max_retries = 4; s.gemini_request_delay_sec = 0.0
        s.openai_api_key = "ok"; s.openai_embedding_model = "text-embedding-3-small"
        # genai.Client가 실제 생성되지 않도록 주입 경로를 우회: client 패치
        with patch("pipeline.llm.gemini_provider.genai.Client"):
            assert isinstance(get_llm_provider(), GeminiProvider)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && python -m pytest tests/test_llm_factory.py -v`
Expected: FAIL (`pipeline.llm.factory` 모듈 없음 → ImportError)

- [ ] **Step 3: Write minimal implementation**

`api/pipeline/llm/factory.py` 생성:

```python
from core.config import settings
from pipeline.llm.base import LLMProvider
from pipeline.llm.gemini_provider import GeminiProvider
from pipeline.llm.openai_provider import OpenAIProvider


def get_llm_provider() -> LLMProvider:
    """settings.llm_provider 플래그에 따라 LLM 프로바이더를 생성한다(토글 단일 지점)."""
    if settings.llm_provider == "gemini":
        return GeminiProvider(
            gemini_api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            openai_api_key=settings.openai_api_key,
            embedding_model=settings.openai_embedding_model,
            max_retries=settings.gemini_max_retries,
            request_delay_sec=settings.gemini_request_delay_sec,
        )
    return OpenAIProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        embedding_model=settings.openai_embedding_model,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd api && python -m pytest tests/test_llm_factory.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit** (git 초기화된 경우만)

```bash
git add api/pipeline/llm/factory.py api/tests/test_llm_factory.py
git commit -m "feat(llm): add get_llm_provider factory for provider toggle"
```

---

### Task 5: 호출부 7곳을 팩토리로 전환

`OpenAIProvider(...)`를 직접 생성하던 곳을 `get_llm_provider()`로 교체한다. 각 파일은 임베딩/모델 인자를 팩토리가 처리하므로 인자를 넘기지 않는다.

**Files:**
- Modify: `api/routers/chat.py:31`
- Modify: `api/pipeline/coach.py:132`
- Modify: `api/pipeline/reviewer.py:197`
- Modify: `api/pipeline/orchestrator.py:43` 및 `:125`
- Modify: `api/pipeline/memory_manager.py:101`
- Modify: `api/_resume_brief_2026_08_05.py:19`
- Test: `api/tests/test_call_sites_use_factory.py`

**Interfaces:**
- Consumes: `pipeline.llm.factory.get_llm_provider` (Task 4).

- [ ] **Step 1: Write the failing test**

```python
# api/tests/test_call_sites_use_factory.py
"""프로바이더 생성이 팩토리로 일원화됐는지 보증(회귀 방지).
production 코드에서 OpenAIProvider(...) 직접 생성이 없어야 한다
(팩토리 모듈과 openai_provider 정의 파일은 예외)."""
import pathlib
import re

API = pathlib.Path(__file__).resolve().parent.parent
ALLOWED = {"pipeline/llm/factory.py", "pipeline/llm/openai_provider.py",
           "pipeline/llm/gemini_provider.py"}
TARGET_FILES = [
    "routers/chat.py", "pipeline/coach.py", "pipeline/reviewer.py",
    "pipeline/orchestrator.py", "pipeline/memory_manager.py",
]


def test_no_direct_openai_provider_construction_in_call_sites():
    pattern = re.compile(r"OpenAIProvider\s*\(")
    for rel in TARGET_FILES:
        src = (API / rel).read_text(encoding="utf-8")
        assert not pattern.search(src), f"{rel} still constructs OpenAIProvider directly"


def test_call_sites_import_factory():
    for rel in TARGET_FILES:
        src = (API / rel).read_text(encoding="utf-8")
        assert "get_llm_provider" in src, f"{rel} does not use get_llm_provider"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && python -m pytest tests/test_call_sites_use_factory.py -v`
Expected: FAIL (호출부가 아직 `OpenAIProvider(...)` 직접 생성 중)

- [ ] **Step 3: Write minimal implementation**

각 파일에서 `from pipeline.llm.openai_provider import OpenAIProvider` import를 `from pipeline.llm.factory import get_llm_provider`로 바꾸고(파일에 OpenAIProvider의 다른 용도가 없으면), 생성 구문을 교체:

- `api/routers/chat.py:31` — `return OpenAIProvider(api_key=settings.openai_api_key)` → `return get_llm_provider()` (이 함수에서 `settings` 다른 사용 없으면 관련 import 정리).
- `api/pipeline/coach.py:132` — `llm = OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)` → `llm = get_llm_provider()`.
- `api/pipeline/reviewer.py:197` — `llm = OpenAIProvider(\n    api_key=..., model=..., embedding_model=...,\n)` → `llm = get_llm_provider()`.
- `api/pipeline/orchestrator.py:43` (run_daily_pipeline) — `llm = OpenAIProvider(api_key=..., model=..., embedding_model=...)` → `llm = get_llm_provider()`.
- `api/pipeline/orchestrator.py:125` (run_ondemand_brief, try 블록 안) — `llm = OpenAIProvider(...)` → `llm = get_llm_provider()` (기존 `try/except: llm=None` 폴백 구조 유지).
- `api/pipeline/memory_manager.py:101` — `llm = OpenAIProvider(...)` → `llm = get_llm_provider()`.
- `api/_resume_brief_2026_08_05.py:19` — 동일하게 `llm = get_llm_provider()`로 교체하고 import 정리(일회성 스크립트, 회귀 테스트 대상 아님).

각 파일에서 `OpenAIProvider`가 더 이상 참조되지 않으면 해당 import 줄을 제거한다. `settings`가 다른 곳에서 여전히 쓰이면 `settings` import는 남긴다.

- [ ] **Step 4: Run test to verify it passes (전체 스위트 회귀 포함)**

Run: `cd api && python -m pytest tests/test_call_sites_use_factory.py -v && python -m pytest -q`
Expected: PASS (신규 2개 + 기존 전체 스위트 통과. import/시그니처 회귀 없음)

- [ ] **Step 5: Commit** (git 초기화된 경우만)

```bash
git add api/routers/chat.py api/pipeline/coach.py api/pipeline/reviewer.py api/pipeline/orchestrator.py api/pipeline/memory_manager.py api/_resume_brief_2026_08_05.py api/tests/test_call_sites_use_factory.py
git commit -m "refactor(llm): route all provider construction through get_llm_provider"
```

---

### Task 6: 수동 롤아웃 검증 (코드 아님 — 실행 확인)

TDD 대상이 아닌 실제 토글/복구 검증 단계. 코드 변경 없음.

- [ ] **Step 1: `.env` 설정**

`api/.env`에서:
- `#GEMINI_API_KEY=...` 줄의 `#` 제거(활성화).
- `LLM_PROVIDER=gemini` 추가(없으면).
- (선택) `GEMINI_MODEL=gemini-2.5-flash`.

- [ ] **Step 2: 백엔드 재기동**

`api/`에서 uvicorn 프로세스를 재시작해 새 .env를 로드한다(설정은 프로세스 시작 시 로드됨).

- [ ] **Step 3: 오늘 브리핑 복구 실행**

Run: `cd api && python _resume_brief_2026_08_05.py`
Expected: `[resume] build_signals -> processed: N` (N>0), `[resume] daily briefs created: M` (M>0). 프리티어 한도로 중간에 끊기면 재실행 시 남은 신호만 이어서 처리.

- [ ] **Step 4: 화면 확인**

`http://localhost:3000/home` 접속 → "생성 중" 무한 로딩 해소, 브리핑 카드 표시 확인.

- [ ] **Step 5: 토글 원복 확인**

`.env`에서 `LLM_PROVIDER=openai`로 되돌리고 재기동 → OpenAI 경로로 동작 확인(크레딧 있을 때). 검증 후 다시 `gemini`로.

---

## Self-Review

**Spec coverage:**
- 토글 플래그 → Task 1(config) + Task 4(factory). ✅
- 텍스트 생성 6메서드 Gemini화 → Task 3. ✅
- 임베딩 항상 OpenAI(위임) → Task 3 `embed_text` + `test_embed_text_delegates`. ✅
- 프리티어 rate-limit 재시도/백오프 → Task 3 `_generate`/`_is_rate_limit` + 재시도 테스트. ✅
- 프롬프트·검증 공유 추출 → Task 2. ✅
- 7개 호출부 통일 → Task 5. ✅
- config/env(`llm_provider`,`gemini_*`) + `google-genai` 의존성 → Task 1 + Task 3. ✅
- 롤아웃/검증 → Task 6. ✅

**Placeholder scan:** 모든 코드 스텝에 실제 코드/명령 포함. "적절히 처리" 류 표현 없음. ✅

**Type consistency:** `get_llm_provider()`(Task4)가 Task5 호출부에서 동일 이름으로 사용됨. `GeminiProvider` 생성자 인자(Task3)와 팩토리 호출(Task4) 일치. `prompts.*` 함수명(Task2)이 Task3에서 동일하게 참조됨. `embed_text` 위임 대상 `self._embedder.embed_text` 일치. ✅
