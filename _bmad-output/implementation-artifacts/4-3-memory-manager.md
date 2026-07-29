---
baseline_commit: NO_VCS
---

# Story 4.3: Memory Manager

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

백엔드 개발자로서,
Outcome이 기록되면 FastAPI가 AI를 통해 Memory를 추출·저장하기를 원한다,
그래서 축적된 Memory가 이후 Daily Brief 개인화와 Research Review 품질 향상에 활용된다.

**범위 참고**: 이 스토리는 순수 백엔드(FastAPI)이며 Web/Flutter 변경이 없다. UX-DR 매핑 없음(EXPERIENCE.md/DESIGN.md 전수 검색 결과 Memory Manager 관련 UI 스펙 없음 — Epic 5의 History/Memory Timeline(5.2)에서 비로소 화면에 노출됨).

## Acceptance Criteria

**AC-1: Outcome 저장 후 BackgroundTask로 Memory 추출**
- **Given** Outcome이 `POST /api/v1/outcomes`로 저장되면 (신규 INSERT 성공 시에만 — 멱등성 재조회로 기존 outcome_id를 반환하는 경로는 제외)
- **When** FastAPI BackgroundTask가 실행되면
- **Then** Decision Loop 체인(Signal + Review + Decision + Outcome)을 기반으로 Memory가 추출된다
- **And** `memories` 테이블에 저장된다: `user_id`, `memory_type`, `summary`, `embedding`(vector 1536), `source_decision_id`
- **And** `memory_type`은 `preference | skill | project | decision_history | outcome_history` 중 적절한 값이다

**AC-2: `memories` 테이블 RLS 확인**
- **Given** `memories` 테이블의 RLS를 확인하면
- **Then** `user_id = auth.uid()` 단순 정책(SELECT only)이 이미 적용되어 있다 — **이 스토리에서 신규 마이그레이션 불필요** (기존 스키마에 이미 구현됨, 아래 Dev Notes 참조)
- **And** 모든 INSERT는 FastAPI(service_role)만 수행한다 (클라이언트 직접 쓰기 금지 — 클라이언트 코드는 이 스토리에서 건드리지 않으므로 자동 충족)

**AC-3: 임베딩 저장**
- **Given** Memory가 저장될 때
- **Then** `summary` 텍스트의 임베딩(1536차원 벡터)이 함께 저장된다
- **And** 이 임베딩은 이후 Recommender의 RAG(pgvector) 조회에 활용된다 (Epic 5 범위 — 이 스토리는 저장까지만)

**AC-4: 실패 격리**
- **Given** Memory 추출 파이프라인(LLM 호출, JSON 파싱, 임베딩 생성, INSERT) 중 어느 단계에서든 예외가 발생하면
- **Then** 예외가 BackgroundTask 밖으로 전파되지 않는다 (Outcome 저장 자체는 이미 완료된 상태이므로 사용자에게 영향 없음)
- **And** 구조화 로그(AD-12)로 실패가 기록된다
- **And** `memories`는 상태 컬럼이 없으므로 재시도 로직은 없다 (실패 시 해당 Outcome에 대한 Memory는 생성되지 않고 종료 — Research Review/Learning Path의 `failed` 상태 전이 패턴과 달리 여기서는 적용 대상 컬럼이 없음)

## Tasks / Subtasks

### [API] LLMProvider 인터페이스 확장

- [x] Task 1: `api/pipeline/llm/base.py`에 Memory 관련 타입 추가 (AC: 1, 3)
  - [x] 1.1 `MemoryContext` dataclass 추가 (다른 Context들과 동일한 위치, `LearningPathContext` 아래): `technology_name: str | None`, `decision_choice: str`, `decision_memo: str | None`, `outcome_status: str`, `outcome_useful: bool | None`, `outcome_actual_learning_time_min: int | None`, `outcome_memo: str | None`, `outcome_applied_project_note: str | None`, `review_one_line_definition: str | None = None`
  - [x] 1.2 `LLMProvider`에 `abstractmethod extract_memory(self, context: MemoryContext) -> LLMResponse` 추가 — docstring: `Decision Loop 체인에서 Memory(memory_type + summary)를 추출. JSON {"memory_type","summary"} 반환.`
  - [x] 1.3 `LLMProvider`에 `abstractmethod embed_text(self, text: str) -> list[float]` 추가 — docstring: `텍스트를 임베딩 벡터(1536차원)로 변환 (AD-7)`
- [x] Task 2: `api/pipeline/llm/openai_provider.py`에 구현 추가 (AC: 1, 3)
  - [x] 2.1 `MEMORY_EXTRACTION_SYSTEM_PROMPT` 상수 추가 (다른 `*_SYSTEM_PROMPT` 상수들과 동일 위치) — memory_type 5종 선택 기준을 명시하고 JSON `{"memory_type": "...", "summary": "..."}` 형식만 반환하도록 지시 (마크다운 금지 지시 포함, 기존 프롬프트들과 동일 컨벤션)
  - [x] 2.2 `ALLOWED_MEMORY_TYPES = ["preference", "skill", "project", "decision_history", "outcome_history"]` 상수 추가 (`LEARNING_PATH_RESOURCE_TYPES`와 동일 위치/스타일)
  - [x] 2.3 `extract_memory()` 구현: `responses.create(model=self._model, instructions=MEMORY_EXTRACTION_SYSTEM_PROMPT, input=<컨텍스트 텍스트>, text={"format": {"type": "json_object"}})` → JSON 파싱 → `memory_type in ALLOWED_MEMORY_TYPES` 검증 + `summary`가 비어있지 않은 문자열인지 검증 → 실패 시 `LLMProviderError`, 성공 시 `LLMResponse(content=raw, model=self._model)` 반환 (검증은 `generate()`/`generate_learning_path()`와 동일하게 Provider 레이어에서 수행)
  - [x] 2.4 컨텍스트 텍스트 조립 헬퍼(`_build_memory_content` 등, 기존 `_build_learning_path_content` 스타일) — 기술명/Decision 선택·메모/Outcome 상태·useful·실제학습시간(분)·메모·적용노트/Review 한줄정의를 사람이 읽을 수 있는 텍스트로 나열
  - [x] 2.5 `embed_text()` 구현: `self._client.embeddings.create(model=self._embedding_model, input=text)` → `response.data[0].embedding` 반환. `len(embedding) != 1536`이면 `LLMProviderError`. `OpenAIError` → `LLMProviderError` 래핑 (기존 메서드들과 동일 예외 처리 컨벤션)
  - [x] 2.6 `OpenAIProvider.__init__`에 `embedding_model: str = "text-embedding-3-small"` 키워드 파라미터 추가 (기존 위치 인자 순서 변경 금지 — `api_key`, `model`, `timeout` 뒤에 추가해 기존 호출부 4곳 하위 호환 유지), `self._embedding_model = embedding_model` 저장
  - [x] 2.7 `api/core/config.py`의 `Settings`에 `openai_embedding_model: str = "text-embedding-3-small"` 추가
  - [x] 2.8 `api/pipeline/memory_manager.py`(Task 4)에서 `OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model, embedding_model=settings.openai_embedding_model)`로 인스턴스화
- [x] Task 3: `api/tests/mocks.py`의 `MockLLMProvider` 갱신 (AC: 테스트 지원 — 인터페이스 확장 시 필수)
  - [x] 3.1 `extract_memory(self, context)` 추가 — `_raise_error`면 `LLMProviderError`, 아니면 `LLMResponse(content=VALID_MEMORY_RESPONSE, model="mock")` (신규 상수 `VALID_MEMORY_RESPONSE = json.dumps({"memory_type": "outcome_history", "summary": "..."})`)
  - [x] 3.2 `embed_text(self, text)` 추가 — `_raise_error`면 `LLMProviderError`, 아니면 `[0.001] * 1536` 반환

### [API] Memory Manager 파이프라인

- [x] Task 4: `api/pipeline/memory_manager.py` 신규 생성 (AC: 1, 3, 4)
  - [x] 4.1 `_fetch_one_or_raise` 헬퍼를 `coach.py`와 동일한 시그니처로 **이 파일 내에 복제**한다 (import하여 재사용하지 않는다 — `fcm.py`/`recommender.py`도 각자 모듈 전용 헬퍼를 갖는 것이 이 코드베이스의 확립된 컨벤션, Dev Notes "모듈 간 헬퍼 재사용 금지" 참조)
  - [x] 4.2 `_execute_memory_extraction(outcome_id: str, decision_id: str, client: Client, llm: LLMProvider) -> bool` 구현:
    - outcome 조회: `_fetch_one_or_raise(client, "outcomes", "id", outcome_id, "status,useful,actual_learning_time_min,applied_project_note,memo", "outcome")`
    - decision 조회: `_fetch_one_or_raise(client, "decisions", "id", decision_id, "choice,memo,review_id", "decision")`
    - review 조회: `_fetch_one_or_raise(client, "reviews", "id", decision_data["review_id"], "project_id,signal_id,result", "review")`
    - project 조회: `_fetch_one_or_raise(client, "projects", "id", review_data["project_id"], "user_id", "project")`
    - signal 조회: `review_data.get("signal_id")`가 존재할 때만 `_fetch_one_or_raise(client, "signals", "id", review_data["signal_id"], "technology_name", "signal")` — 없으면 `technology_name = None` (방어적 처리, review.signal_id는 nullable 컬럼)
    - `review_data.get("result")`에서 `payload.one_line_definition` 추출 (result가 None이면 `None`)
    - `MemoryContext` 조립(`outcome_data["actual_learning_time_min"]` → `outcome_actual_learning_time_min` 포함) 후 `llm.extract_memory(context)` 호출 → `json.loads(response.content)` → `memory_type`, `summary` 추출
    - `llm.embed_text(summary)` 호출 → `embedding`
    - `client.table("memories").insert({"user_id": project_data["user_id"], "memory_type": memory_type, "summary": summary, "embedding": embedding, "source_decision_id": decision_id}).execute()`
    - 성공 시 `pipeline_log(stage="memory_manager", brief_date="", user_count=0, event="memory_created", outcome_id=outcome_id, decision_id=decision_id, memory_type=memory_type)` 후 `True` 반환
  - [x] 4.3 `except Exception` 전체를 감싸 `_log.exception(...)` + `pipeline_log(stage="memory_manager", level="error", event="memory_extraction_failed", outcome_id=outcome_id, decision_id=decision_id, error=str(e)[:200])` 후 `False` 반환 (예외를 절대 밖으로 던지지 않음 — `coach.py`의 `_execute_learning_path_pipeline`과 동일한 catch-log-return 패턴이되, `memories`에는 상태 컬럼이 없으므로 실패 시 업데이트할 row가 없다는 차이만 있음)
  - [x] 4.4 `run_memory_manager_from_outcome(outcome_id: str, decision_id: str) -> None` — BackgroundTask 진입점. `get_supabase()` + `OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model, embedding_model=settings.openai_embedding_model)` 생성 후 `_execute_memory_extraction`으로 위임만 한다 (`coach.py`의 `run_learning_path_from_pending`과 동일 구조)

### [API] Outcome 라우터에 BackgroundTask 연결

- [x] Task 5: `api/routers/outcomes.py` 수정 (AC: 1)
  - [x] 5.1 `from fastapi import BackgroundTasks` 추가 (기존 `APIRouter, Depends, HTTPException, status`에 추가), `from pipeline.memory_manager import run_memory_manager_from_outcome` 추가
  - [x] 5.2 `create_outcome` 함수 시그니처에 `background_tasks: BackgroundTasks` 파라미터 추가 (`learning_paths.py`의 `trigger_learning_path`와 동일 위치: body 다음, user_id 앞 또는 뒤 — 기존 파라미터 순서 유지하며 추가)
  - [x] 5.3 **신규 INSERT 성공 경로에만** (현재 파일의 `outcome_id = insert_result.data[0]["id"]` 직후, `return APIResponse(...)` 직전) `background_tasks.add_task(run_memory_manager_from_outcome, outcome_id, body.decision_id)` 추가
  - [x] 5.4 **호출하지 않는 경로 명확화** (누락 방지): (a) 멱등성 early-return(기존 `existing` outcome 반환, 현재 파일 97-98줄) — 호출 안 함, (b) INSERT 예외 후 race-fallback 재조회 반환(현재 파일 123-124줄) — 호출 안 함. 두 경로 모두 "이미 다른 요청이 INSERT를 완료했다"는 의미이므로, 그 다른 요청의 성공 경로에서 이미 한 번 트리거되었거나 될 것이다. 여기서 추가 호출하면 동일 Outcome에 대해 Memory가 중복 생성될 수 있다.

### [API] 테스트

- [x] Task 6: `api/tests/test_outcomes.py` 갱신 — **기존 8개 테스트 회귀 방지 필수** (AC: 회귀 방지)
  - [x] 6.1 `POST /api/v1/outcomes`를 호출하는 기존 10개 테스트(스토리 작성 시점 8개로 추정되었으나 실제로는 10개) 전부에 `patch("routers.outcomes.run_memory_manager_from_outcome")`를 `with` 블록에 추가했다 — 추가하지 않으면 `background_tasks.add_task`가 `TestClient` 컨텍스트 내에서 실제로 실행되어 목킹되지 않은 `get_supabase()`(빈 `SUPABASE_URL`)를 호출해 기존 테스트가 깨진다. `test_trigger_learning_path_returns_202_with_learning_path_id`(`test_learning_paths.py`)의 패턴을 그대로 따랐다
  - [x] 6.2 `test_completed_with_useful_returns_201`에 `mock_run.assert_called_once_with(TEST_OUTCOME_ID, TEST_DECISION_ID)` 검증 추가 (신규 테스트 함수 대신 기존 성공 경로 테스트를 보강 — 동일 시나리오의 중복 테스트 함수를 만들지 않기 위한 판단)
  - [x] 6.3 `test_duplicate_decision_id_returns_existing_outcome_id`(멱등성 경로)에 `mock_run.assert_not_called()` 검증 추가
  - [x] 6.4 `test_insert_exception_falls_back_to_existing_outcome`(race-fallback 경로)에 `mock_run.assert_not_called()` 검증 추가
- [x] Task 7: `api/tests/test_memory_manager.py` 신규 생성 (AC: 1, 3, 4)
  - [x] 7.1 `_execute_memory_extraction`에 `MagicMock` client + `MockLLMProvider`를 직접 주입해 테스트 (`test_execute_learning_path_pipeline_completes` 패턴 — client/llm 직접 주입, `get_supabase`/`OpenAIProvider` 생성부는 patch하지 않음). AD-11 "실 DB" 문구는 Dev Notes "스펙 갈등" 섹션의 결정에 따라 완전 모킹으로 구현
  - [x] 7.2 정상 흐름: `memories.insert()`가 `user_id`, `memory_type`(허용값), `summary`, `embedding`(길이 1536 리스트), `source_decision_id`로 호출되는지 검증, 반환값 `True`
  - [x] 7.3 LLM이 `LLMProviderError` 발생 시 예외가 전파되지 않고 `False` 반환 + `memories.insert()` 미호출 검증
  - [x] 7.4 `extract_memory` 응답의 `memory_type`이 허용 목록 밖 또는 JSON 파싱 실패 시 `False` 반환 + INSERT 미호출 (2개 테스트로 분리 검증)
  - [x] 7.5 `review_data.signal_id`가 `None`인 경우 signal 조회를 스킵하고 `technology_name=None`으로 정상 진행하는지 검증
  - [x] 7.6 `run_memory_manager_from_outcome` 위임 테스트: `monkeypatch`로 `memory_manager.get_supabase`/`memory_manager.OpenAIProvider`/`memory_manager._execute_memory_extraction`을 대체해 위임 인자만 검증
  - [x] 7.7 `OpenAIProvider.extract_memory()`: `patch("pipeline.llm.openai_provider.OpenAI")`로 `responses.create` 목킹 후 정상 JSON 파싱 + 잘못된 `memory_type` 시 `LLMProviderError` 검증
  - [x] 7.8 `OpenAIProvider.embed_text()`: 목킹 후 반환값 검증 + 길이 불일치 시 `LLMProviderError` 검증 + `OpenAIError` 래핑 검증

### Review Findings

- [x] [Review][Patch] `test_execute_memory_extraction_returns_false_on_json_parse_failure`가 Task 7.4 요구사항(False 반환 + INSERT 미호출)의 "INSERT 미호출" 검증을 누락함 [api/tests/test_memory_manager.py:147-163] — patched, insert_called 추적 검증 추가 (전체 127개 테스트 회귀 없음)
- [x] [Review][Defer] `run_memory_manager_from_outcome`에서 `get_supabase()`/`OpenAIProvider()` 생성이 try/except 밖에 있어 생성 실패 시 예외가 BackgroundTask 밖으로 전파될 수 있음 [api/pipeline/memory_manager.py:98-106] — deferred, `coach.py`의 `run_learning_path_from_pending`(api/pipeline/coach.py:131-132)에도 동일한 기존 패턴이 있어 이 스토리 단독으로 고치면 컨벤션 불일치 발생. 별도 스토리에서 두 파이프라인을 함께 수정할 것.
- [x] [Review][Defer] `memories`에 상태 컬럼/재시도 로직이 없어 일시적 실패(LLM/DB 장애 등) 시 Memory가 영구적으로 조용히 유실됨 — deferred, Dev Notes AD-5 예외 섹션에서 의도적으로 결정된 스코프("실패 시 사용자는 알 수 없고 알 필요도 없음"). 향후 이 리스크가 문제되면 별도 스토리로 재검토.
- [x] [Review][Defer] FastAPI `BackgroundTasks`는 재배포/워커 재시작 시 실행 중이던 작업이 유실될 수 있는 내구성 한계가 있음 — deferred, `coach.py`/`learning_paths.py` 등 기존 파이프라인 전부가 동일한 아키텍처를 사용 중이라 이 스토리만의 문제가 아님.
- [x] [Review][Defer] `review.signal_id`가 가리키는 `signals` row가 삭제된 경우(dangling reference) signal 조회가 예외를 던져 전체 Memory 추출이 중단됨(널 signal_id 경로처럼 우아하게 성능 저하하지 않음) [api/pipeline/memory_manager.py:44-49] — deferred, 현재 앱에 signal 삭제 플로우가 없어 도달 불가능한 경로. 삭제 기능이 추가되면 재검토.

## Dev Notes

### 핵심 아키텍처 제약

- **AD-7 (Memory) [ADOPTED]**: `memories` 쓰기는 FastAPI만(AD-3). Memory는 Outcome 기록 후 FastAPI가 AI로 추출·저장. `memory_type`: `preference | skill | project | decision_history | outcome_history`. `summary` 임베딩(VECTOR 1536) 저장. Decision Loop 완결점은 Signal→Review→Decision→Outcome→**Memory**. [Source: ARCHITECTURE-SPINE.md#AD-7, line 217-220]
- **AD-3 (데이터 접근 소유권)**: `memories` INSERT는 FastAPI(service_role)만. 이 스토리는 클라이언트 코드를 전혀 건드리지 않으므로 자동 충족. [Source: ARCHITECTURE-SPINE.md#AD-3, line 30-33]
- **AD-9 (RLS 패턴)**: `memories`는 `user_id` 직접 컬럼 보유 테이블 → `user_id = auth.uid()` 단순 정책. **이미 마이그레이션에 구현되어 있다** (`memories_select` 정책, 아래 DB 스키마 참조) — 이 스토리는 신규 마이그레이션을 추가하지 않는다. [Source: ARCHITECTURE-SPINE.md#AD-9, line 231-234]
- **AD-6 패턴 재사용 (LLMProvider 인터페이스 확장 방식)**: 기존 `LLMProvider`는 `generate`/`build_signal_title_summary`/`chat`/`generate_learning_path` 4개 메서드를 스토리마다 하나씩 추가해왔다. 이 스토리도 동일 컨벤션으로 `extract_memory`(텍스트 추출)와 `embed_text`(임베딩, 완전히 다른 OpenAI API — `embeddings.create` vs `responses.create`)를 **별도 메서드로 분리** 추가한다. 하나의 메서드로 합치지 않는 이유: (1) 두 호출은 서로 다른 엔드포인트/응답 타입, (2) `embed_text`는 범용 문자열 임베딩 프리미티브로 Epic 5 Recommender RAG에서도 재사용될 가능성이 높음(단, 이 스토리에서 그 재사용을 구현하지 않는다 — YAGNI). [Source: ARCHITECTURE-SPINE.md#AD-6, line 188-191; api/pipeline/llm/base.py]
- **AD-12 (관찰가능성)**: 파이프라인 로그는 `pipeline_log()` 헬퍼로 구조화 (`api/pipeline/logger.py`) — `stage="memory_manager"`로 호출.
- **AD-5는 이 스토리에 문자 그대로 적용되지 않음**: AD-5의 `pending → processing → completed | failed` 상태 머신은 Research Review와 Learning Path에 명시적으로 한정된 패턴이다(둘 다 상태 컬럼과 사용자 대면 UI가 있음). `memories` 테이블에는 상태 컬럼이 없다(DB 스키마 참조) — Memory 추출은 순수 fire-and-forget BackgroundTask이며, 실패 시 그냥 Memory가 생성되지 않고 종료된다(사용자는 이 실패를 알 수 없고 알 필요도 없음 — Outcome 저장 자체는 이미 성공). **상태 컬럼을 추가하거나 상태 머신을 흉내내지 말 것.**

### DB 스키마 — `memories` 테이블 (기존 마이그레이션, 수정 없음 — 신규 마이그레이션 불필요)

```sql
-- _bmad-output/implementation-artifacts/db/001_initial_schema.sql (line 123-138)
CREATE TABLE IF NOT EXISTS public.memories (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    memory_type        TEXT NOT NULL
                           CHECK (memory_type IN (
                               'preference', 'skill', 'project',
                               'decision_history', 'outcome_history'
                           )),
    summary            TEXT NOT NULL,
    embedding          VECTOR(1536),
    source_decision_id UUID REFERENCES public.decisions(id) ON DELETE SET NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- HNSW 벡터 인덱스 (line 260-264, Recommender RAG용 — 이 스토리는 저장만, 조회는 Epic 5)
CREATE INDEX IF NOT EXISTS idx_memories_embedding
    ON public.memories USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- RLS (line 319-321) — SELECT only, 쓰기는 FastAPI service_role만
ALTER TABLE public.memories ENABLE ROW LEVEL SECURITY;
CREATE POLICY "memories_select" ON public.memories FOR SELECT
    USING (user_id = auth.uid());
```

INSERT 시 `embedding` 필드는 Python `list[float]`(길이 1536)을 그대로 dict에 담아 `.insert()`에 전달한다 — `supabase-py`(postgrest)가 JSON 배열로 직렬화하며 pgvector가 이를 파싱한다. 이 패턴은 코드베이스에 선례가 없으므로(grep 결과 0건) 신중히 구현하되, 별도 문자열 변환(`"[0.1,0.2,...]"`) 없이 순수 리스트로 전달한다.

### 스펙 갈등: AD-11 "실제 Supabase 테스트 DB" 문구 vs 코드베이스 확립된 관례

에픽 AC 원문("테스트 환경에서 Memory Manager를 검증할 때 → 실제 Supabase 테스트 DB에 연결하여 테스트한다")과 `ARCHITECTURE-SPINE.md#AD-11`("비즈니스 로직·파이프라인 단계 → 실제 Supabase 테스트 DB 연결, 프로덕션 DB 모킹 금지")은 문자 그대로 읽으면 이 스토리에 실 DB 연결 테스트를 요구한다. 실제로 Story 4.2의 Dev Notes는 "실 DB 연결 필요한 대상은 파이프라인이 있는 경우(예: Story 4.3 Memory Manager)로 한정"이라고 명시적으로 이 스토리를 지목했다.

**그러나** 이 코드베이스에는 (1) `conftest.py`가 없고, (2) 테스트 DB 자격증명을 주입하는 CI/환경변수 체계가 전혀 없으며, (3) 파이프라인을 가진 기존 스토리(2.2 Signal Builder/Reviewer, 2.3 Recommender, 4.1 Learning Path) 전부가 **"환경변수 불필요"를 명시하며 완전 모킹**으로 구현·코드리뷰·"done" 승인되었다(`test_signal_builder_reviewer.py` 파일 상단 docstring, `test_learning_paths.py` 상단 docstring 참조). 이 스토리에서 갑자기 실 DB 연결을 요구하면: 로컬에 `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY`가 없는 개발 환경에서 테스트가 실패하고, CI가 없어 실행 자체가 검증되지 않는다.

**해결 방식(반드시 이대로 구현)**: Task 7의 모든 테스트는 기존 파이프라인 테스트와 동일하게 **완전 모킹**(`MagicMock` client + `MockLLMProvider`)으로 작성한다. AD-11의 "실 DB" 문구는 조직적 지향점으로 남겨두고, 이 스토리가 그 인프라(conftest, CI 테스트 DB)를 새로 구축하는 것은 스코프 밖이다. 향후 실 DB 테스트 인프라가 구축되면 별도 스토리에서 전체 파이프라인 테스트를 일괄 전환한다.

### 재사용 패턴 (그대로 따를 것)

- **`_execute_learning_path_pipeline` / `run_learning_path_from_pending`** (`api/pipeline/coach.py`): 이 스토리의 `_execute_memory_extraction`/`run_memory_manager_from_outcome`가 구조적으로 그대로 모델로 삼는 대상. 순차 조회(`_fetch_one_or_raise`) → LLM 호출 → 검증 → INSERT/UPDATE → 성공 로그, `except Exception`으로 감싸 실패 로그 후 `bool` 반환, 예외를 밖으로 던지지 않음.
- **BackgroundTask 등록 + 라우터 테스트 패턴** (`api/routers/learning_paths.py` + `api/tests/test_learning_paths.py`): `background_tasks.add_task(fn, ...)`을 성공 경로에만 호출, 라우터 테스트는 `patch("routers.<module>.<fn>")`으로 실제 파이프라인 실행을 차단하고 `mock_run.assert_called_once_with(...)`로 위임 인자만 검증. 파이프라인 자체는 별도 테스트에서 client/llm 직접 주입으로 검증.
- **OpenAIProvider 검증-후-반환 패턴** (`generate_learning_path`의 `_validate_learning_path_resources`): 응답 JSON 구조/값 검증은 Provider 구현체 내부에서 수행 후 `LLMProviderError` 발생 또는 검증된 `LLMResponse` 반환. 파이프라인 레이어(`memory_manager.py`)는 Provider의 계약을 신뢰하고 재검증하지 않는다(단, JSON 파싱 실패 등 방어 코드는 유지).
- **모듈 간 헬퍼 재사용 금지**: `_fetch_one_or_raise`는 `coach.py`에만 존재하며 다른 파이프라인 모듈(`fcm.py`, `recommender.py`)도 각자 전용 프라이빗 헬퍼를 갖는다(공유 유틸 모듈 없음). `memory_manager.py`도 `from pipeline.coach import _fetch_one_or_raise`로 가져오지 말고 동일 함수를 복제한다.

### 기존 코드베이스 현황 (수정 대상 파일)

- `api/routers/outcomes.py` (40줄, 전체 정독 완료) — 현재 `create_outcome`은 순수 동기 CRUD(BackgroundTask 없음). 3-hop 소유권 검증(`decisions→reviews→projects`) + 체크-후-삽입 멱등성 + race-fallback 구조. **정확히 3곳의 `return` 지점**이 있다: (a) 97-98줄 멱등성 early-return, (b) 123-124줄 race-fallback 재조회 반환, (c) 139줄 신규 INSERT 성공 반환. `background_tasks.add_task`는 **(c)에서만** 호출한다.
- `api/pipeline/llm/base.py` (79줄, 전체 정독 완료) — `ReviewContext`/`LearningPathContext`/`ChatContext` dataclass + `LLMProvider` ABC(4개 abstractmethod). `MemoryContext` + 2개 abstractmethod를 추가하되 기존 4개는 변경하지 않는다.
- `api/pipeline/llm/openai_provider.py` (198줄, 전체 정독 완료) — `OpenAIProvider(LLMProvider)`가 4개 메서드 전부 구현 중. `__init__(self, api_key, model="gpt-4o", timeout=30.0)`. 호출부 4곳(`coach.py`, `reviewer.py`, `orchestrator.py`, `chat.py`) 전부 키워드 인자 사용 — `embedding_model` 키워드 파라미터 추가는 하위 호환.
- `api/core/config.py` (56줄, 전체 정독 완료) — `Settings`에 `openai_embedding_model` 필드 추가만, 기존 필드/`check_required_settings` 검증 로직은 변경하지 않는다.
- `api/tests/mocks.py` (67줄, 전체 정독 완료) — `MockLLMProvider`는 `LLMProvider` ABC를 구현하므로, 인터페이스에 abstractmethod 2개를 추가하면 **이 파일을 갱신하지 않을 경우 기존 모든 파이프라인 테스트가 `TypeError: Can't instantiate abstract class`로 즉시 깨진다.** Task 3은 선택이 아니라 필수.
- `api/main.py` — **이 스토리에서 변경하지 않는다.** Memory Manager는 신규 API 엔드포인트/라우터가 없다(순수 내부 BackgroundTask). APScheduler 등록도 불필요(Outcome 저장 시점에만 트리거, 배치 아님).

### 범위 경계

| 항목 | 이 스토리 (4.3) | 이후 |
|------|----------------|------|
| Outcome 저장 후 Memory 추출 BackgroundTask | ✅ | — |
| `memories` 테이블 INSERT (임베딩 포함) | ✅ | — |
| `LLMProvider.extract_memory` / `embed_text` | ✅ | — |
| Memory를 Review/Daily Brief 생성 시 RAG로 조회(pgvector 검색) | ❌ | Epic 5 (FR-6.3, Recommender 개인화) |
| Memory Timeline 화면(히스토리 탭에서 Memory 조회 UI) | ❌ | Epic 5 (Story 5.2) |
| `memories` 테이블 마이그레이션/RLS 변경 | ❌ | 불필요 — 이미 존재 |
| Outcome 재기록/수정 시 Memory 갱신 | ❌ | AC 범위 밖 — Outcome은 재기록 UI 자체가 없음(4.2 스코프 결정) |

### 절대 금지사항

| 금지 | 이유 |
|------|------|
| `memories` 관련 신규 DB 마이그레이션 추가 | 스키마·RLS·인덱스 모두 이미 존재 (AC-2) |
| Memory 추출 실패 시 Outcome INSERT를 롤백하거나 502/500을 반환 | Outcome 저장은 BackgroundTask 등록 이전에 이미 커밋 완료된 상태 — Memory 실패가 Outcome 성공에 영향을 줘서는 안 됨 |
| `memories`에 `status`/`pending`/`processing` 컬럼 추가 또는 상태 머신 흉내 | AD-5는 이 테이블에 적용되지 않음(Dev Notes 참조) — 스키마에 없는 컬럼을 UPDATE하려 하면 즉시 에러 |
| 멱등성 early-return·race-fallback 경로에서 `background_tasks.add_task` 호출 | 중복 Memory 생성 위험 (Task 5.4 참조) |
| `pipeline.coach`에서 `_fetch_one_or_raise`를 import | 모듈 간 헬퍼 재사용 금지 컨벤션 위반 — 복제할 것 |
| Epic 5 Recommender RAG(pgvector 검색 쿼리) 구현 | 이 스토리는 저장까지만, 조회는 Epic 5 |
| `test_outcomes.py`의 기존 8개 테스트를 `run_memory_manager_from_outcome` patch 없이 방치 | BackgroundTask가 실제 실행되어 미설정 `get_supabase()` 호출로 테스트가 깨짐 (Task 6.1 필수) |

### 신규 / 수정 파일 목록

```
# API 신규 파일
api/pipeline/memory_manager.py          (NEW)
api/tests/test_memory_manager.py        (NEW)

# API 수정 파일
api/pipeline/llm/base.py                (UPDATE — MemoryContext + 2개 abstractmethod)
api/pipeline/llm/openai_provider.py     (UPDATE — extract_memory, embed_text 구현 + embedding_model 파라미터)
api/core/config.py                      (UPDATE — openai_embedding_model 설정)
api/tests/mocks.py                      (UPDATE — MockLLMProvider에 extract_memory/embed_text 추가, 필수)
api/routers/outcomes.py                 (UPDATE — BackgroundTasks 파라미터 + add_task 호출)
api/tests/test_outcomes.py              (UPDATE — 기존 8개 테스트에 patch 추가 + 신규 3개 테스트)

# main.py 변경 없음, Web/Flutter 변경 없음
```

### References

- 에픽: `_bmad-output/planning-artifacts/epics.md` — Story 4.3 (line 724-748), FR-6.1/6.2 (line 45-47), AD-7 원문(line 70)
- 아키텍처: `_bmad-output/planning-artifacts/architecture/architecture-decision-os-2026-07-21/ARCHITECTURE-SPINE.md` — AD-7(line 217-220), AD-3(line 30-33), AD-9(line 231-234), AD-11(line 245-248), AD-6(line 188-213), AD-5(line 155-158, 이 스토리에 미적용 이유는 위 Dev Notes 참조), `memories` ER 다이어그램(line 144-150), AD-15 Agent Workflow 다이어그램의 `MEM["Memory Manager"]` 노드(line 288, 302-303 — 사용자 액션 트리거만 명시, 배치 아님을 확인)
- DB 스키마: `_bmad-output/implementation-artifacts/db/001_initial_schema.sql` — `memories` 테이블(line 122-138), HNSW 인덱스(line 260-264), RLS(line 276, 319-321), `outcomes`/`decisions`/`reviews`/`projects`/`signals` 스키마(line 50-164)
- 파이프라인 재사용 패턴: `api/pipeline/coach.py`(구조 전체 모델), `api/pipeline/llm/base.py`·`api/pipeline/llm/openai_provider.py`(인터페이스 확장 패턴), `api/pipeline/logger.py`(`pipeline_log` 시그니처)
- 라우터/테스트 재사용 패턴: `api/routers/learning_paths.py`, `api/tests/test_learning_paths.py`(BackgroundTask 등록 + patch 기반 테스트 컨벤션의 원본)
- 이전 스토리: `_bmad-output/implementation-artifacts/4-2-outcome-기록.md` — `outcomes.py`의 정확한 현재 상태(범위 경계 표에서 Memory 추출을 명시적으로 4.3에 위임), AD-11 적용 방식에 대한 선례 논의(line 137)

## Dev Agent Record

### Agent Model Used

Claude (bmad-dev-story workflow)

### Debug Log References

- `python3 -m pytest -q` (api/) → 127 passed, 0 failed, 0 regressions
- `python3 -m pytest tests/test_outcomes.py -q` → 10 passed
- `python3 -m pytest tests/test_memory_manager.py -q` → 11 passed
- `python3 -m py_compile` 전체 신규/수정 파일 → 구문 오류 없음

### Completion Notes List

- `LLMProvider`에 `extract_memory`/`embed_text` 2개 abstractmethod와 `MemoryContext` dataclass를 AD-6 컨벤션대로 추가. `MockLLMProvider`도 함께 갱신해 기존 파이프라인 테스트(`TypeError: Can't instantiate abstract class`) 회귀를 방지함.
- `OpenAIProvider`에 `extract_memory()`(Responses API + JSON 검증)와 `embed_text()`(Embeddings API + 1536차원 검증)를 구현. `embedding_model` 키워드 파라미터를 하위 호환 방식으로 추가(기존 4개 호출부 영향 없음).
- `api/pipeline/memory_manager.py` 신규 생성: `_fetch_one_or_raise`를 `coach.py`와 별개로 복제(모듈 간 헬퍼 재사용 금지 컨벤션 준수), `_execute_memory_extraction`은 Decision Loop 체인(outcome→decision→review→project→signal)을 순차 조회 후 LLM 호출·검증·INSERT하며 모든 예외를 내부에서 흡수해 `bool`만 반환(`coach.py`의 catch-log-return 패턴과 동일). `run_memory_manager_from_outcome`는 BackgroundTask 진입점으로 위임만 수행.
- `api/routers/outcomes.py`: `create_outcome`에 `BackgroundTasks` 파라미터를 추가하고, **신규 INSERT 성공 경로에서만** `background_tasks.add_task(run_memory_manager_from_outcome, ...)`를 호출. 멱등성 early-return과 race-fallback 경로는 의도적으로 호출하지 않음(중복 Memory 생성 방지).
- `api/tests/test_outcomes.py`: `POST /api/v1/outcomes`를 호출하는 기존 10개 테스트(스토리 작성 시점엔 8개로 추정됐으나 실제 파일에는 10개 존재) 전부에 `patch("routers.outcomes.run_memory_manager_from_outcome")`를 추가해 `TestClient` 컨텍스트 내 실제 BackgroundTask 실행으로 인한 회귀를 차단. 신규 assertion 3건(6.2~6.4)은 별도 테스트 함수를 새로 만드는 대신 이미 해당 시나리오(성공/멱등성/race-fallback)를 검증하던 기존 테스트에 `mock_run` 검증을 보강하는 방식으로 구현 — 동일 시나리오의 중복 테스트를 피하기 위한 판단.
- `api/tests/test_memory_manager.py` 신규 생성 (11개 테스트): 파이프라인 단계는 `MagicMock` client + `MockLLMProvider`/커스텀 stub을 직접 주입해 완전 모킹으로 검증(AD-11 "실 DB" 원칙은 이 코드베이스의 확립된 관례에 따라 스코프 밖으로 명시적으로 남겨둠, Dev Notes "스펙 갈등" 참조). `OpenAIProvider.extract_memory`/`embed_text`는 `patch("pipeline.llm.openai_provider.OpenAI")`로 목킹해 검증.
- 신규 DB 마이그레이션 없음(AC-2 요구사항대로 `memories` 테이블/RLS는 기존 스키마 그대로 사용). `main.py`/Web/Flutter 변경 없음.
- 전체 회귀 테스트 127개 통과, 신규 테스트 11개 모두 통과.

### File List

**신규**
- `api/pipeline/memory_manager.py`
- `api/tests/test_memory_manager.py`

**수정**
- `api/pipeline/llm/base.py`
- `api/pipeline/llm/openai_provider.py`
- `api/core/config.py`
- `api/tests/mocks.py`
- `api/routers/outcomes.py`
- `api/tests/test_outcomes.py`

## Change Log

| 날짜 | 변경 내용 |
|------|----------|
| 2026-07-27 | Story 4.3 구현 완료 — Outcome 저장 후 BackgroundTask로 Memory(preference/skill/project/decision_history/outcome_history) 추출·임베딩·저장 파이프라인 추가. 신규 DB 마이그레이션 없음. 전체 테스트 127개 통과(회귀 0건), 신규 테스트 11개 추가. |
| 2026-07-27 | 코드 리뷰(bmad-code-review) 완료 — patch 1건 적용(JSON 파싱 실패 테스트에 INSERT 미호출 검증 추가), defer 4건 기록(deferred-work.md 참조), dismiss 15건. Status → done. |
