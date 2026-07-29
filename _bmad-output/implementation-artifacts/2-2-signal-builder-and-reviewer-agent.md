---
baseline_commit: NO_VCS
---

# Story 2.2: Signal Builder & Reviewer Agent

Status: done

## Story

백엔드 개발자로서,
정규화된 Signal에 대해 AI가 Research Review를 사전 생성할 수 있기를 원한다,
그래서 사용자가 SignalCard를 탭했을 때 Review가 즉시 또는 빠르게 제공된다.

## Acceptance Criteria

**AC-1: Reviewer Agent 기본 동작**

- **Given** `signals` 테이블에 `processed` 상태의 Signal이 있을 때
- **When** Reviewer Agent가 실행되면
- **Then** 각 Signal에 대해 `reviews` 테이블에 레코드가 생성된다 (`status: pending`)
- **And** 비동기 실행: `pending → processing → completed | failed`
- **And** `completed` 또는 `failed` 상태 진입 후 추가 상태 변경은 금지된다

**AC-2: LLMProvider 인터페이스**

- **Given** `LLMProvider` 인터페이스가 정의되어 있을 때
- **When** MVP 구현체를 확인하면
- **Then** OpenAI Responses API를 사용한다 (`client.responses.create()` — Chat Completions `client.chat.completions.create()` 사용 불가)
- **And** 인터페이스 메서드: `generate(context: ReviewContext) → LLMResponse`
- **And** 에러는 `LLMProviderError`로 표준화된다

**AC-3: ReviewContextBuilder 및 result JSONB 구조**

- **Given** `ReviewContextBuilder`가 Signal을 처리할 때
- **When** Research Review를 생성하면
- **Then** `reviews.result` JSONB는 `{"schema_version": 1, "review_type": "research", "payload": {...}}` 봉투를 따른다
- **And** payload에 13섹션 데이터가 포함된다: 한 줄 정의, 핵심 개념, 해결하는 문제, 왜 중요한가, 기존 기술 차이, 사용자 관련성, 학습 목표, 예상 학습 시간·난이도, 실무 적용 가능성, 위험 요소, 추천 이유, 참고 출처, HonestBox
- **And** HonestBox payload에 `severity: "standard" | "high"` 플래그가 포함된다

**AC-4: 실패 처리 및 로그**

- **Given** Review 생성이 `failed` 상태일 때
- **Then** 소스 Signal 데이터가 보존된다
- **And** 자동 재시도는 없다
- **And** FastAPI 로그에 `review_id`, `playbook_type` 필드가 포함된다

**AC-5: Signal Builder (암묵적 전제조건)**

- **Given** Normalizer가 생성한 `status='raw'` Signal이 있을 때
- **When** Signal Builder가 실행되면
- **Then** OpenAI LLM으로 AI 제목과 요약을 생성하여 `signals.title`, `signals.summary`를 갱신한다
- **And** `signals.status`가 `'raw'`에서 `'processed'`로 업데이트된다

## Tasks / Subtasks

- [x] Task 1: `openai` 패키지 추가 및 환경변수 설정 (AC: #2, #5)
  - [x] 1.1 `api/requirements.txt`에 `openai>=1.82.0` 추가
  - [x] 1.2 `api/core/config.py`에 `openai_api_key: str = Field(default="", repr=False)` 추가 (기존 패턴 유지: 빈 문자열 기본값 + warnings.warn)
  - [x] 1.3 `openai_model: str = "gpt-4o"` 설정 추가 (하드코딩 방지)

- [x] Task 2: LLM 모듈 — 인터페이스 + OpenAI Responses API 구현체 생성 (AC: #2)
  - [x] 2.1 `api/pipeline/llm/__init__.py` 생성 (빈 파일)
  - [x] 2.2 `api/pipeline/llm/base.py` 생성 — `ReviewContext` dataclass, `LLMResponse` dataclass, `LLMProviderError` exception, `LLMProvider` ABC
  - [x] 2.3 `api/pipeline/llm/openai_provider.py` 생성 — `OpenAIProvider(LLMProvider)` 구현체
    - `__init__(self, api_key: str, model: str = "gpt-4o")`
    - `generate(self, context: ReviewContext) → LLMResponse` — `client.responses.create()` 사용 (Chat Completions 절대 사용 금지)
    - JSON 응답 파싱하여 13섹션 검증 포함
    - 모든 OpenAI 예외를 `LLMProviderError`로 래핑

- [x] Task 3: Signal Builder 생성 (AC: #5)
  - [x] 3.1 `api/pipeline/signal_builder.py` 생성
  - [x] 3.2 `build_signals(signal_ids: list[str], client: Client, api_key: str, model: str, brief_date: str) -> list[str]` 구현
    - raw 상태 signal_id만 처리 (processed 스킵)
    - Signal + signal_sources 조회 → LLM 직접 호출 (`openai.OpenAI.responses.create()`)
    - LLM 응답에서 `title`(기술 단위 통합 제목), `summary`(2-3문장 요약) 추출
    - `signals` 테이블 UPDATE: `title`, `summary`, `status='processed'`
    - 실패 시 해당 Signal 스킵 후 계속 처리, `pipeline_log()` 사용

- [x] Task 4: Reviewer Agent 생성 (AC: #1, #3, #4)
  - [x] 4.1 `api/pipeline/reviewer.py` 생성
  - [x] 4.2 `review_signal(signal_id: str, project_id: str, client: Client, llm: LLMProvider, brief_date: str) -> str | None` 구현
    - reviews INSERT: `project_id`, `signal_id`, `playbook_type='ai_research'`, `review_type='research'`, `status='pending'`
    - `status='processing'` + `processing_started_at=NOW()` 업데이트
    - Signal 조회 + signal_sources 조회 + projects→user_id 조회 + user_profiles 조회
    - `ReviewContext` 빌드 (기술명, 출처목록, 사용자 role/tech_stack/interests/experience_level)
    - `context_snapshot` JSONB 저장: `{"schema_version": 1, "review_type": "research", "payload": {signal, sources, user_profile}}`
    - LLMProvider.generate() 호출 → 13섹션 result JSONB 빌드
    - 성공: `status='completed'`, `result=jsonb`, `completed_at=NOW()` 업데이트, review_id 반환
    - 실패: `status='failed'`, `error_message=str(e)`, `completed_at=NOW()` 업데이트, None 반환
    - 모든 로그에 `review_id`, `playbook_type` 포함 (AD-12)
    - `completed`/`failed` 진입 후 추가 상태 변경 없음 (불변 — DB 조회로 현재 상태 확인 불필요, 코드 흐름으로 보장)
  - [x] 4.3 `review_all_for_signal(signal_id: str, client: Client, llm: LLMProvider, brief_date: str) -> list[str]` 구현
    - 모든 `ai_research` 프로젝트의 `project_id` 조회
    - 각 project에 대해 `review_signal()` 호출
    - review_id 목록 반환

- [x] Task 5: 단위 테스트 작성 (AC: #1–#5)
  - [x] 5.1 `api/tests/test_signal_builder_reviewer.py` 생성
  - [x] 5.2 Signal Builder: LLM Mock으로 `status='processed'` 업데이트 검증
  - [x] 5.3 Signal Builder: `status='raw'`가 아닌 signal_id 스킵 검증
  - [x] 5.4 LLMProvider 인터페이스: 추상 메서드 `generate()` 존재 검증
  - [x] 5.5 OpenAIProvider: `client.responses.create()` 호출 검증 (Mock)
  - [x] 5.6 OpenAIProvider: 예외 발생 시 `LLMProviderError` 래핑 검증
  - [x] 5.7 Reviewer: `review_signal()` → reviews INSERT pending 검증
  - [x] 5.8 Reviewer: 상태 전이 `pending → processing → completed` 검증 (Mock)
  - [x] 5.9 Reviewer: LLM 실패 시 `status='failed'`, `error_message` 저장 검증
  - [x] 5.10 Reviewer: result JSONB 봉투 구조 검증 (`schema_version`, `review_type`, `payload` 키 필수)
  - [x] 5.11 Reviewer: payload 13섹션 키 존재 검증
  - [x] 5.12 Reviewer: HonestBox `severity` 값이 `"standard"` 또는 `"high"`임을 검증
  - [x] 5.13 Reviewer: `completed`/`failed` 진입 후 상태 변경 없음 검증

## Dev Notes

### ⚠️ 핵심 전제: Story 2.1 구현 결과

Story 2.1 완료 후 다음이 존재함:
- `api/pipeline/models.py` — `RawArticle` dataclass (content 필드 포함)
- `api/pipeline/normalizer.py` — `normalize()` 함수 (upsert 방식, ON CONFLICT DO NOTHING)
- `api/pipeline/logger.py` — `pipeline_log(stage, brief_date, user_count, level, **extra)`
- `api/pipeline/collector/base.py` — `BaseCollector` ABC
- `api/pipeline/collector/stub.py` — `StubCollector` (하드코딩 5개 기사)
- `_bmad-output/implementation-artifacts/db/002_signals_unique_constraint.sql` — signals(technology_name, signal_date) UNIQUE 제약 추가됨

**Story 2.1 deferred → Story 2.2에서 처리:**
- `RawArticle` 런타임 유효성 검사 (빈 문자열, URL 형식) [`api/pipeline/models.py:7-13`]
- `BaseCollector` 예외 계약 미정의 [`api/pipeline/collector/base.py:9`]

### 절대 금지 사항

| 금지 | 이유 |
|------|------|
| `client.chat.completions.create()` 사용 | AD-6: OpenAI Responses API만 허용 |
| `client.responses.create()` 대신 다른 OpenAI 엔드포인트 | AD-6 명시적 제약 |
| `result` JSONB 봉투 없는 자유 형식 | AD-4 CHECK 제약 (`schema_version`, `review_type`, `payload` 필수) |
| `context_snapshot` 봉투 없는 자유 형식 | AD-4 CHECK 제약 (동일) |
| `completed`/`failed` 후 추가 상태 변경 | AD-5 불변 상태 규칙 |
| LLM 호출 실패 시 자동 재시도 | AD-5 명시적 금지 |
| 클라이언트에서 reviews 직접 쓰기 | AD-3: FastAPI만 쓰기 |

### DB 스키마 참조

```sql
-- reviews 테이블 (001_initial_schema.sql:61-91)
CREATE TABLE IF NOT EXISTS public.reviews (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id            UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    signal_id             UUID,  -- signals(id) FK (ALTER TABLE로 연결됨)
    playbook_type         TEXT NOT NULL,         -- 'ai_research'
    review_type           TEXT NOT NULL,         -- 'research'
    status                TEXT NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    bar_gate_override     TEXT CHECK (bar_gate_override IN ('force_enable', 'force_disable')),
    context_snapshot      JSONB,  -- ENVELOPE REQUIRED
    result                JSONB,  -- ENVELOPE REQUIRED
    error_message         TEXT,
    processing_started_at TIMESTAMPTZ,   -- stuck 감지용 (AD-12)
    completed_at          TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_context_snapshot_envelope CHECK (
        context_snapshot IS NULL OR (
            context_snapshot ? 'schema_version' AND
            context_snapshot ? 'review_type'    AND
            context_snapshot ? 'payload'
        )
    ),
    CONSTRAINT chk_result_envelope CHECK (
        result IS NULL OR (
            result ? 'schema_version' AND
            result ? 'review_type'    AND
            result ? 'payload'
        )
    )
);
```

```sql
-- signals 테이블 (status raw→processed 업데이트, 001_initial_schema.sql:154-164)
-- Story 2.1 Normalizer가 status='raw'로 INSERT
-- Signal Builder가 title/summary 갱신 후 status='processed'로 UPDATE
CREATE TABLE IF NOT EXISTS public.signals (
    id               UUID PRIMARY KEY,
    technology_name  TEXT NOT NULL,
    title            TEXT NOT NULL,   -- Signal Builder가 AI 제목으로 갱신
    summary          TEXT,            -- Signal Builder가 AI 요약으로 채움
    signal_date      DATE NOT NULL,
    status           TEXT NOT NULL DEFAULT 'raw'
                         CHECK (status IN ('raw', 'processed', 'archived')),
    ...
);
-- UNIQUE (technology_name, signal_date) -- 002_signals_unique_constraint.sql 적용됨
```

```sql
-- projects 테이블 (user_id 조회에 필요, 001_initial_schema.sql:50-57)
CREATE TABLE IF NOT EXISTS public.projects (
    id            UUID PRIMARY KEY,
    user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    playbook_type TEXT NOT NULL CHECK (playbook_type IN ('ai_research')),
    name          TEXT NOT NULL,
    ...
);
```

### LLM 모듈 설계

```python
# api/pipeline/llm/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class LLMProviderError(Exception):
    """LLM 공급자 에러 표준화 (AD-6)."""
    pass


@dataclass
class ReviewContext:
    """Research Review 생성 컨텍스트."""
    technology_name: str
    signal_sources: list[dict]          # [{source_type, url, title}, ...]
    user_role: str | None = None
    user_tech_stack: list[str] = field(default_factory=list)
    user_interests: list[str] = field(default_factory=list)
    user_experience_level: str | None = None


@dataclass
class LLMResponse:
    """LLM 공급자 응답 표준화."""
    content: str    # JSON 문자열 (13섹션 payload)
    model: str = ""


class LLMProvider(ABC):
    """LLM 공급자 추상 인터페이스 (AD-6)."""

    @abstractmethod
    def generate(self, context: ReviewContext) -> LLMResponse:
        ...
```

```python
# api/pipeline/llm/openai_provider.py
import json
from openai import OpenAI, OpenAIError
from pipeline.llm.base import LLMProvider, LLMProviderError, LLMResponse, ReviewContext


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


class OpenAIProvider(LLMProvider):
    """OpenAI Responses API 구현체 (AD-6: Chat Completions 사용 불가)."""

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def generate(self, context: ReviewContext) -> LLMResponse:
        user_content = self._build_user_content(context)
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=RESEARCH_REVIEW_SYSTEM_PROMPT,  # Responses API system
                input=user_content,
            )
            return LLMResponse(content=response.output_text, model=self._model)
        except OpenAIError as e:
            raise LLMProviderError(str(e)) from e

    def _build_user_content(self, context: ReviewContext) -> str:
        sources_text = "\n".join(
            f"- [{s.get('source_type', 'other')}] {s.get('title', '')} ({s.get('url', '')})"
            for s in context.signal_sources
        )
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
            f"출처:\n{sources_text}\n\n"
            f"사용자 컨텍스트:\n" + "\n".join(user_ctx)
        )
```

**중요**: `instructions` 파라미터가 Responses API의 system prompt 역할을 함. `client.responses.create()`는 `model`과 `input` 외에 `instructions`(선택)를 받음. `output_text` 속성으로 텍스트 응답 접근.

### Signal Builder 설계

```python
# api/pipeline/signal_builder.py
import json
from openai import OpenAI, OpenAIError

from pipeline.logger import pipeline_log

SIGNAL_BUILD_PROMPT = """다음 AI 기술 Signal의 출처 목록을 바탕으로 JSON으로 반환하세요:
{"title": "기술 단위 통합 제목 (한국어, 50자 이내)", "summary": "핵심 내용 요약 (한국어, 2-3문장)"}
마크다운 없이 JSON만 반환."""


def build_signals(
    signal_ids: list[str],
    client,          # supabase.Client
    api_key: str,
    model: str = "gpt-4o",
    brief_date: str = "",
) -> list[str]:
    """raw 상태 Signal → LLM 제목/요약 생성 + status='processed'. 처리된 signal_id 목록 반환."""
    if not signal_ids:
        return []

    openai_client = OpenAI(api_key=api_key)
    processed_ids: list[str] = []

    for signal_id in signal_ids:
        try:
            signal_result = client.table("signals").select("*").eq("id", signal_id).execute()
            if not signal_result.data:
                continue
            signal_data = signal_result.data[0]

            # raw 상태만 처리
            if signal_data["status"] != "raw":
                pipeline_log(stage="signal_builder", brief_date=brief_date, user_count=0,
                             event="signal_already_processed", signal_id=signal_id)
                continue

            sources_result = client.table("signal_sources").select("source_type,url,title").eq("signal_id", signal_id).execute()
            sources_text = "\n".join(
                f"- [{s.get('source_type')}] {s.get('title', '')} ({s.get('url', '')})"
                for s in (sources_result.data or [])
            )
            user_input = f"기술: {signal_data['technology_name']}\n출처:\n{sources_text}"

            response = openai_client.responses.create(
                model=model,
                instructions=SIGNAL_BUILD_PROMPT,
                input=user_input,
            )
            parsed = json.loads(response.output_text)
            title = parsed.get("title") or signal_data["title"]
            summary = parsed.get("summary") or ""

            client.table("signals").update({
                "title": title,
                "summary": summary,
                "status": "processed",
            }).eq("id", signal_id).execute()

            processed_ids.append(signal_id)
            pipeline_log(stage="signal_builder", brief_date=brief_date, user_count=0,
                         event="signal_built", signal_id=signal_id,
                         technology_name=signal_data["technology_name"])

        except OpenAIError as e:
            pipeline_log(stage="signal_builder", brief_date=brief_date, user_count=0,
                         level="error", event="llm_call_failed", signal_id=signal_id, error=str(e))
            continue
        except Exception as e:
            pipeline_log(stage="signal_builder", brief_date=brief_date, user_count=0,
                         level="error", event="signal_build_failed", signal_id=signal_id, error=str(e))
            continue

    return processed_ids
```

### Reviewer Agent 설계

```python
# api/pipeline/reviewer.py
import json
import logging
from datetime import datetime, timezone

from supabase import Client

from pipeline.llm.base import LLMProvider, LLMProviderError, ReviewContext
from pipeline.logger import pipeline_log

_log = logging.getLogger(__name__)

REQUIRED_SECTIONS = [
    "one_line_definition", "key_concepts", "problems_solved", "why_it_matters",
    "vs_existing_tech", "user_relevance", "learning_goals", "learning_time_difficulty",
    "practical_applicability", "risks", "recommendation_reason",
    "reference_sources", "honest_box",
]


def review_signal(
    signal_id: str,
    project_id: str,
    client: Client,
    llm: LLMProvider,
    brief_date: str = "",
) -> str | None:
    """
    Signal 하나에 대한 Research Review 생성.
    상태 머신: pending → processing → completed | failed (불변)
    반환: review_id (성공) 또는 None (실패)
    """
    review_id: str | None = None
    try:
        # 1) Review 레코드 생성 (pending)
        insert_result = client.table("reviews").insert({
            "project_id": project_id,
            "signal_id": signal_id,
            "playbook_type": "ai_research",
            "review_type": "research",
            "status": "pending",
        }).execute()
        if not insert_result.data:
            pipeline_log(stage="reviewer", brief_date=brief_date, user_count=0,
                         level="error", event="review_insert_failed",
                         signal_id=signal_id, playbook_type="ai_research")
            return None
        review_id = insert_result.data[0]["id"]

        # 2) processing 상태 전이
        client.table("reviews").update({
            "status": "processing",
            "processing_started_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", review_id).execute()

        # 3) Signal + sources + user profile 조회
        signal_data = client.table("signals").select("*").eq("id", signal_id).execute().data
        if not signal_data:
            raise RuntimeError(f"signal {signal_id} not found")
        signal_data = signal_data[0]

        sources = client.table("signal_sources").select("source_type,url,title").eq("signal_id", signal_id).execute().data or []

        project_data = client.table("projects").select("user_id").eq("id", project_id).execute().data
        if not project_data:
            raise RuntimeError(f"project {project_id} not found")
        user_id = project_data[0]["user_id"]

        profile = client.table("user_profiles").select(
            "role,tech_stack,interests,experience_level"
        ).eq("id", user_id).execute().data
        profile = profile[0] if profile else {}

        # 4) context_snapshot 저장 (result 저장 전에 저장)
        context_snapshot = {
            "schema_version": 1,
            "review_type": "research",
            "payload": {
                "signal": {
                    "id": signal_id,
                    "technology_name": signal_data["technology_name"],
                    "title": signal_data["title"],
                    "summary": signal_data.get("summary"),
                    "signal_date": str(signal_data["signal_date"]),
                },
                "sources": sources,
                "user_profile": {
                    "role": profile.get("role"),
                    "tech_stack": profile.get("tech_stack", []),
                    "interests": profile.get("interests", []),
                    "experience_level": profile.get("experience_level"),
                },
            },
        }
        client.table("reviews").update({
            "context_snapshot": context_snapshot,
        }).eq("id", review_id).execute()

        # 5) ReviewContext 빌드 + LLM 호출
        context = ReviewContext(
            technology_name=signal_data["technology_name"],
            signal_sources=sources,
            user_role=profile.get("role"),
            user_tech_stack=profile.get("tech_stack") or [],
            user_interests=profile.get("interests") or [],
            user_experience_level=profile.get("experience_level"),
        )
        llm_response = llm.generate(context)

        # 6) 13섹션 파싱 및 검증
        payload = json.loads(llm_response.content)
        missing = [k for k in REQUIRED_SECTIONS if k not in payload]
        if missing:
            raise ValueError(f"LLM 응답에 필수 섹션 누락: {missing}")

        honest_box = payload.get("honest_box", {})
        if honest_box.get("severity") not in ("standard", "high"):
            payload["honest_box"]["severity"] = "standard"  # 방어적 기본값

        result = {
            "schema_version": 1,
            "review_type": "research",
            "payload": payload,
        }

        # 7) completed 상태 전이 (불변 — 이후 상태 변경 없음)
        client.table("reviews").update({
            "status": "completed",
            "result": result,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", review_id).execute()

        pipeline_log(stage="reviewer", brief_date=brief_date, user_count=0,
                     event="review_completed", review_id=review_id, playbook_type="ai_research",
                     signal_id=signal_id)
        return review_id

    except (LLMProviderError, ValueError, RuntimeError, Exception) as e:
        if review_id:
            client.table("reviews").update({
                "status": "failed",
                "error_message": str(e)[:500],
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", review_id).execute()
        pipeline_log(stage="reviewer", brief_date=brief_date, user_count=0,
                     level="error", event="review_failed",
                     review_id=review_id, playbook_type="ai_research",
                     signal_id=signal_id, error=str(e)[:200])
        return None


def review_all_for_signal(
    signal_id: str,
    client: Client,
    llm: LLMProvider,
    brief_date: str = "",
) -> list[str]:
    """processed Signal에 대해 모든 ai_research 프로젝트의 Review 생성."""
    projects = client.table("projects").select("id").eq("playbook_type", "ai_research").execute().data or []
    review_ids: list[str] = []
    for project in projects:
        rid = review_signal(signal_id, project["id"], client, llm, brief_date)
        if rid:
            review_ids.append(rid)
    return review_ids
```

### 기존 FastAPI 패턴 재사용

```python
# 기존 패턴 (api/core/config.py:8-11) — 동일하게 따를 것
class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_role_key: str = Field(default="", repr=False)
    supabase_jwt_secret: str = Field(default="", repr=False)
    # 추가:
    openai_api_key: str = Field(default="", repr=False)
    openai_model: str = "gpt-4o"

    @model_validator(mode="after")
    def check_required_settings(self) -> "Settings":
        # 기존 경고 유지 + openai_api_key 경고 추가
        if not self.openai_api_key:
            warnings.warn(
                "OPENAI_API_KEY is not set — LLM calls will fail",
                RuntimeWarning,
                stacklevel=2,
            )
        return self
```

```python
# 기존 Supabase 클라이언트 패턴 (api/core/supabase.py) — 그대로 재사용
# from core.supabase import get_supabase
# client = get_supabase()
```

```python
# 기존 pipeline_log 패턴 (api/pipeline/logger.py) — 그대로 재사용
# pipeline_log(stage="reviewer", brief_date=brief_date, user_count=0,
#              review_id=review_id, playbook_type="ai_research")
```

### 테스트 전략 (AD-11)

- `LLMProvider` 인터페이스만 Mock (OpenAI 실제 호출 없음)
- Supabase: 기존 `_make_mock_client` 패턴 확장 (test_pipeline_foundation.py 참고)
- **실제 Supabase 연결은 불필요** — Signal Builder / Reviewer 단위 테스트는 MagicMock으로 충분
- `test_pipeline_foundation.py`의 `_make_mock_client` 패턴을 직접 복사하지 말고, 테스트 파일 내 새 mock 헬퍼 구성

```python
# 테스트 Mock LLMProvider 예시
class MockLLMProvider(LLMProvider):
    def __init__(self, content: str):
        self._content = content

    def generate(self, context: ReviewContext) -> LLMResponse:
        return LLMResponse(content=self._content, model="mock")

VALID_13_SECTION_RESPONSE = json.dumps({
    "one_line_definition": "정의",
    "key_concepts": "개념",
    "problems_solved": "문제",
    "why_it_matters": "중요성",
    "vs_existing_tech": "차이",
    "user_relevance": "관련성",
    "learning_goals": "목표",
    "learning_time_difficulty": {"estimated_hours": 5, "difficulty": "intermediate"},
    "practical_applicability": "적용",
    "risks": "위험",
    "recommendation_reason": "추천",
    "reference_sources": ["https://example.com"],
    "honest_box": {"content": "솔직한 평가", "severity": "standard"},
})
```

### 신규 파일 목록

```
api/pipeline/llm/__init__.py                    (NEW — 빈 파일)
api/pipeline/llm/base.py                        (NEW — LLMProvider 인터페이스)
api/pipeline/llm/openai_provider.py             (NEW — OpenAI Responses API 구현체)
api/pipeline/signal_builder.py                  (NEW — Signal Builder)
api/pipeline/reviewer.py                        (NEW — Reviewer Agent)
api/tests/test_signal_builder_reviewer.py       (NEW — 단위 테스트)
```

### 수정 파일 목록

```
api/requirements.txt     (UPDATE — openai>=1.82.0 추가)
api/core/config.py       (UPDATE — openai_api_key, openai_model 설정 추가)
```

**수정 불필요**: `api/main.py`, `api/pipeline/models.py`, `api/pipeline/normalizer.py`, `api/pipeline/logger.py` — 변경 없음.

### 아키텍처 준수 체크리스트

| 규칙 | 근거 | 세부 사항 |
|------|------|----------|
| OpenAI Responses API만 사용 (`responses.create()`) | AD-6 | Chat Completions 절대 사용 금지 |
| `LLMProvider` 추상화 — 구현체 교체 가능 | AD-6 | OpenAI 외 구현체 추가 시 base.py 상속만 |
| `reviews` 쓰기는 FastAPI(service_role)만 | AD-3 | 클라이언트 직접 쓰기 금지 |
| `completed`/`failed` 불변 상태 | AD-5 | 종료 상태 후 UPDATE 없음 |
| result/context_snapshot JSONB 봉투 필수 | AD-4 + DB CHECK 제약 | `schema_version`, `review_type`, `payload` 최상위 키 |
| 로그에 `review_id`, `playbook_type` 포함 | AD-12 | 모든 reviewer 로그 필수 |
| LLM 호출 자동 재시도 없음 | AD-5 | failed 시 사용자 재트리거 방식 |
| 새 Playbook = 새 `ReviewContextBuilder` 구현 | AD-6 | `review_all_for_signal`은 ai_research 전용 |

### Story 2.3 연계 고려사항

- `build_signals()`, `review_all_for_signal()` 함수는 Story 2.3 APScheduler 배치 파이프라인에서 순서대로 호출됨
- Story 2.3 파이프라인 순서: `Collector.collect()` → `normalize()` → `build_signals()` → `review_all_for_signal()` → `Recommender` → `Daily Brief`
- `review_all_for_signal()`은 현재 등록된 **모든** ai_research 프로젝트에 대해 Review를 생성함 (MVP: 사용자 수 적음)
- Story 2.3에서 APScheduler를 `main.py` lifespan에 등록할 예정 — 지금은 scheduler 코드 없음

### Story 2.1 이전 학습 사항

- **Supabase 클라이언트**: `api/core/supabase.py` — `get_supabase()` 싱글톤
- **APIResponse 봉투**: 파이프라인 내부 함수는 `APIResponse` 불필요 (HTTP 엔드포인트에서만 사용)
- **테스트 Mock 패턴**: `api/tests/test_pipeline_foundation.py` — `MagicMock()` + `table_side_effect()` 패턴
- **JSON 로거**: `api/main.py:16-26` — `python-json-logger` 이미 설정됨; `pipeline_log()`로 자동 상속
- **requirements.txt 패턴**: 기존 패키지 버전 명시 방식 동일하게 따를 것 (`openai==X.X.X` 형식 가능)
- **빈 tech_name 검증 패턴**: `normalizer.py`의 `if not tech_name or not tech_name.strip()` 패턴 참고

### References

- 에픽 요구사항: `_bmad-output/planning-artifacts/epics.md` — Story 2.2 (line 408-437)
- 에픽 전체 구조: `_bmad-output/planning-artifacts/epics.md` — Epic 2 (line 377-519)
- DB 스키마: `_bmad-output/implementation-artifacts/db/001_initial_schema.sql` — reviews (line 61-91), signals (line 154-164), projects (line 50-57)
- UNIQUE 제약: `_bmad-output/implementation-artifacts/db/002_signals_unique_constraint.sql`
- 아키텍처 AD-3(데이터접근), AD-4(데이터모델), AD-5(비동기), AD-6(AI Review엔진), AD-11(테스트), AD-12(관찰가능성): `_bmad-output/planning-artifacts/architecture/architecture-decision-os-2026-07-21/ARCHITECTURE-SPINE.md`
- 이전 스토리: `_bmad-output/implementation-artifacts/2-1-signal-pipeline-foundation.md`
- 기존 config 패턴: `api/core/config.py`
- 기존 테스트 패턴: `api/tests/test_pipeline_foundation.py`
- 기존 파이프라인 로그: `api/pipeline/logger.py`
- 기존 normalizer: `api/pipeline/normalizer.py`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 (bmad-create-story → bmad-dev-story)

### Debug Log References

### Completion Notes List

- Task 1: `openai>=1.82.0` requirements.txt 추가, `openai_api_key` + `openai_model` config.py에 추가 (기존 warnings.warn 패턴 준수)
- Task 2: `api/pipeline/llm/` 모듈 신설 — `LLMProviderError`, `ReviewContext`, `LLMResponse`, `LLMProvider` ABC (base.py), `OpenAIProvider` Responses API 구현체 (openai_provider.py). `client.responses.create()` 전용, Chat Completions 사용 안 함. 13섹션 파싱 및 검증 포함.
- Task 3: `api/pipeline/signal_builder.py` — `build_signals()` 구현. raw 상태 signal만 처리, LLM 직접 호출로 title/summary 생성, processed 상태로 업데이트.
- Task 4: `api/pipeline/reviewer.py` — `review_signal()` + `review_all_for_signal()` 구현. 상태 머신 pending→processing→completed|failed, JSONB 봉투 구조 준수, 종료 상태 불변.
- Task 5: `api/tests/test_signal_builder_reviewer.py` 18개 테스트 — 테이블별 mock 딕셔너리 캐싱 패턴 사용. 47/47 전체 통과, regression 없음.

### File List

- api/requirements.txt (수정)
- api/core/config.py (수정)
- api/pipeline/llm/__init__.py (신규)
- api/pipeline/llm/base.py (신규)
- api/pipeline/llm/openai_provider.py (신규)
- api/pipeline/signal_builder.py (신규)
- api/pipeline/reviewer.py (신규)
- api/tests/test_signal_builder_reviewer.py (신규)

### Review Findings

**[결정 필요]**
- [x] [Review][Patch] Responses API JSON 모드 적용 — `client.responses.create()`에 `text={"format": {"type": "json_object"}}` 추가로 마크다운 래핑 방지 [`openai_provider.py:43-48`]

**[패치 필요]**
- [x] [Review][Patch] `honest_box` null/비딕셔너리 값으로 AttributeError 발생 — LLM이 `"honest_box": null` 반환 시 `payload.get("honest_box", {})` → `None`, 이후 `None.get("severity")` AttributeError. 13섹션 키 존재 검증이 값 타입은 검증 안 함 [`reviewer.py:125-127`]
- [x] [Review][Patch] Signal Builder가 LLMProvider 추상화 우회 — `OpenAI` 직접 import·호출; `LLMProvider` 인터페이스 미사용으로 AD-6, AC-2, AD-11 위반. 테스트도 `patch("pipeline.signal_builder.OpenAI")`로 직접 목 [`signal_builder.py` 전체]
- [x] [Review][Patch] Signal Builder DB 업데이트 반환값 미검증 — 업데이트 실패(네트워크, 제약 위반)해도 `processed_ids.append(signal_id)` 실행 → 호출자가 거짓 성공 응답 받음 [`signal_builder.py:59-65`]
- [x] [Review][Patch] `except` 블록 내 DB 호출 실패 시 원본 예외 마스킹 — `except Exception as e` 내부 DB 업데이트가 예외 발생 시 새 예외가 `e`를 대체; `review_all_for_signal` 루프 중단 가능 [`reviewer.py:147-153`]
- [x] [Review][Patch] `REQUIRED_SECTIONS` 두 모듈 중복 정의 — 변경 시 두 곳 모두 수정 필요; 에러 타입도 불일치 (`LLMProviderError` vs `ValueError`) [`openai_provider.py:7`, `reviewer.py:12`]
- [x] [Review][Patch] 테스트 `test_reviewer_honest_box_invalid_severity_defaults_to_standard` assertion 오류 — `severity == "standard"` 검증 대신 `severity in ("standard", "high")` 검증; 테스트 이름과 불일치 [`tests/test_signal_builder_reviewer.py:519`]
- [x] [Review][Patch] LLM이 JSON 배열/스칼라 반환 시 섹션 검사 오동작 — `parsed`가 딕셔너리가 아닐 때 `k not in parsed`가 리스트 멤버십으로 동작해 13섹션 모두 "존재"로 판단, 손상된 review 저장 [`openai_provider.py:51-54`]
- [x] [Review][Patch] `learning_time_difficulty` 하위 필드 런타임 미검증 — AC-3에서 `estimated_hours`, `difficulty` 포함 명시했으나 코드에서 상위 키 존재만 확인 [`reviewer.py:121-123`]
- [x] [Review][Patch] `source_type` None 기본값 누락 — `signal_builder.py`에서 `s.get('source_type')` 기본값 없어 `None`이면 LLM 입력에 `"[None]"` 포함 (`openai_provider.py`는 `'other'` 기본값 있음) [`signal_builder.py:45`]

**[지연]**
- [x] [Review][Defer] `processing` 상태 전이 반환값 미검증 [`reviewer.py:70-74`] — deferred, pre-existing
- [x] [Review][Defer] Signal이 오류 시 `raw` 상태로 영구 잔류 — `signals` 테이블에 `failed` 상태 없음 (스키마 제약) [`signal_builder.py`] — deferred, pre-existing
- [x] [Review][Defer] context_snapshot + result 비원자적 쓰기 — 처리 중 프로세스 종료 시 `processing` 상태 고착 [`reviewer.py:104-106, 136-140`] — deferred, pre-existing
- [x] [Review][Defer] INSERT 실패 시 로그의 `review_id=None` — AD-12 경계 케이스, review_id가 존재하지 않는 시점의 로그 [`reviewer.py:154-157`] — deferred, pre-existing
- [x] [Review][Defer] `projects` 쿼리에 LIMIT 없음 — MVP 스케일에서 무해하나 프로젝트 수 증가 시 메모리 이슈 가능 [`reviewer.py:168-174`] — deferred, pre-existing
- [x] [Review][Defer] `review_all_for_signal` 동시 호출 시 중복 review 생성 — 멱등성 없음; MVP 단일 파이프라인에서 발생 불가 [`reviewer.py:161-180`] — deferred, pre-existing
- [x] [Review][Defer] 잘못된 `signal_id` 전달 시 프로젝트별 `failed` review 레코드 생성 — 호출자(Story 2.3 파이프라인) 책임 [`reviewer.py:161-180`] — deferred, pre-existing
- [x] [Review][Defer] `LLMProvider.generate()` 동기 메서드 — async FastAPI 이벤트 루프 차단 가능; 현재 APScheduler 스레드풀에서 호출되어 무해; Story 2.3 설계 시 검토 [`llm/base.py:41`] — deferred, pre-existing

## Change Log

- 2026-07-24: Story 2.2 Signal Builder & Reviewer Agent 스토리 파일 생성 — ready-for-dev
- 2026-07-24: Story 2.2 구현 완료 — Signal Builder, LLM 모듈, Reviewer Agent, 단위 테스트 18개 추가 (47/47 통과)
- 2026-07-24: 코드 리뷰 완료 — 결정 1개, 패치 9개, 지연 8개, 무시 8개
