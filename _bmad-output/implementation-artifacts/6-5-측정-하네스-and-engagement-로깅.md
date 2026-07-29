---
baseline_commit: NO_VCS
---

# Story 6.5: 측정 하네스 & Engagement 로깅

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

개발자로서,
사용자의 **노출(impression)·열람(open)·읽기완료(read-through)·결정(decision) engagement를 로깅**하고, 그 데이터로 **RAG 재랭킹 vs 콜드스타트를 held-out 지표(Learn Now율·read-through율 등)로 비교하는 오프라인 평가 하네스**를 갖고 싶다,
그래서 6.1~6.4의 "고도화"가 실제로 추천 품질을 올렸는지 **감이 아니라 데이터로 판단**할 수 있다.

> **🍎 프론트엔드 비유 (오너용):** Epic 6을 "뉴스 편집국"에 비유해 왔다. 6.1 취재(수집) → 6.2 데스크 정리(클러스터·필터) → 6.3 메타 스티커(발행시각·인기·권위 저장) → 6.4 편집장의 1면 배치(랭킹·MMR·RAG). **6.5(이 스토리)는 편집국의 "구독자 반응 분석팀"이다.**
> - **지금 문제:** 편집장(6.4)이 1면을 열심히 짰지만, **독자가 실제로 그 기사를 봤는지·눌렀는지·끝까지 읽었는지·"배우겠다" 했는지**를 아무도 기록하지 않는다. 그래서 "RAG로 개인화한 게 정말 더 잘 먹혔나?"에 답할 수 없다.
> - **이 스토리가 하는 일 2가지:**
>   1. **반응 로그를 남긴다(AC1).** 프론트로 치면 **Google Analytics의 `track()` 이벤트** 같은 것 — 카드가 화면에 떴다(impression), 눌러서 상세를 열었다(open), 끝까지 읽어 하단 바가 활성화됐다(read-through), Learn Now/Queue/Ignore를 골랐다(decision). 이 4가지를 `누가·어떤 시그널·언제`와 함께 테이블에 쌓는다. **핵심 제약: 이 로깅이 사용자 화면을 절대 느리게 하면 안 된다(best-effort, 비동기).**
>   2. **비교 리포트를 뽑는 스크립트를 만든다(AC2).** 쌓인 로그를 읽어서 "**Memory가 있어 RAG로 개인화된 사용자**"와 "**Memory가 없어 콜드스타트로 랭킹된 사용자**"의 반응률(누른 비율·읽은 비율·Learn Now율)을 표로 비교한다. 프론트로 치면 **A/B 테스트 결과 대시보드의 백엔드 배치판** — 단, 실제 무작위 A/B가 아니라 "이미 갈라진 두 집단(cohort)"을 관찰 비교하는 것(한계는 문서화).
> - **이 스토리가 "하지 않는" 일(중요):** 랭킹 로직·가중치·λ를 **다시 튜닝하지 않는다.** 6.5는 "**자를 만드는 일**"이지 "자로 재서 고치는 일"이 아니다. 측정 결과로 무엇을 바꿀지는 이 데이터가 쌓인 **다음** 결정이다. (6.4가 남긴 튜닝 후보들 — `_recency_norm` 자정 해석, `_clamp` dead 상한 — 은 여기서 손대지 않는다. Dev Notes 참고.)

## Acceptance Criteria

**AC1 — Engagement 이벤트 로깅 (FR-8.5, 비차단 best-effort)**
- **Given** 사용자가 Daily Brief를 소비하고 시그널과 상호작용할 때
- **When** `impression`(브리프에 시그널 노출) / `open`(Research Review 상세 열람) / `read_through`(ContextStickyBar 활성화 = 필수 섹션 전부 seen) / `decision`(Learn Now·Queue·Ignore) 이벤트가 발생하면
- **Then** 각 이벤트가 `event_type`·`user_id`·`signal_id`·`created_at`(타임스탬프)과 함께 **신규 `engagement_events` 테이블**에 로깅된다 (AD-3: 쓰기는 FastAPI service_role만)
- **And** 이벤트에는 오프라인 평가용 `variant`(`rag` | `coldstart` | NULL)와 `daily_brief_id`, 부가 `metadata`(position·relevance_score·choice 등)가 함께 기록된다
- **And** **로깅은 사용자 경험을 차단하지 않는다** — 모든 로깅은 best-effort(try/except로 감싸 실패해도 brief 생성/결정 생성/화면 렌더를 막지 않음). 클라이언트 이벤트 전송은 fire-and-forget(응답 대기가 UX를 막지 않음)

**AC2 — `impression` + `variant`는 서버에서 정본(canonical)으로 기록 (held-out 평가의 신뢰 기준)**
- **Given** 배치(`run_recommender`) 또는 온디맨드(`create_daily_brief_for_user`)로 brief가 생성되어 `daily_brief_signals`가 insert될 때
- **When** brief 생성이 성공하면
- **Then** 해당 brief에 노출된 각 시그널마다 **서버 사이드에서** `impression` 이벤트가 로깅된다(그 사용자·브리프의 `variant`, `position`, `relevance_score` 포함) — 클라이언트 신뢰에 의존하지 않아 variant 라벨이 항상 정확
- **And** `variant`는 `_score_signals`가 결정한 값(Memory 보유 → `rag`, 미보유/RAG폴백 → `coldstart`)을 그대로 반영한다 (pipeline_log의 `memory_rag_applied`/`memory_rag_coldstart`와 일치)
- **And** 이 서버 impression 로깅도 best-effort — 실패해도 brief는 `completed`로 진행(AD-5)

**AC3 — 클라이언트 이벤트 수집 엔드포인트 + 웹 최소 계측 (open·read_through)**
- **Given** 웹 사용자가 Research Review를 열거나 끝까지 읽을 때
- **When** 클라이언트가 이벤트를 보고하면
- **Then** **`POST /api/v1/engagement`** (AD-13 계약: Bearer JWT, `/api/v1/`, `{data,error}` 봉투)가 이벤트를 받아 `user_id`(JWT에서)·`signal_id`·`event_type`과 함께 저장한다
- **And** 웹에서 **`open`**(review-page 진입 시)과 **`read_through`**(ContextStickyBar가 `enabled`로 전환되는 순간)이 fire-and-forget으로 전송된다
- **And** 엔드포인트는 `event_type ∈ {impression, open, read_through}`만 허용(클라이언트발 `decision` 금지 — decision은 서버 정본), 잘못된 `signal_id`/타입은 조용히 무시하거나 4xx로 거절하되 **UX를 막지 않음**
- **And** Flutter 클라이언트 계측은 **이 스토리 범위 밖(deferred)** — 서버 impression + decision + 웹 open/read_through로 핵심 비교가 성립(Dev Notes D3)

**AC4 — `decision` 이벤트 서버 로깅 (uniform 이벤트 스트림)**
- **Given** `POST /api/v1/decisions`로 결정이 생성(신규 insert 성공)될 때
- **When** decision insert가 성공하면
- **Then** best-effort로 `decision` engagement 이벤트가 로깅된다(`signal_id`는 `review_id → reviews.signal_id`로 조회, `metadata`에 `choice`·`queue_timing`)
- **And** 멱등 재요청(기존 decision 반환 경로)에서는 **중복 로깅하지 않는다**(신규 insert 시에만 로깅)
- **And** 이 로깅 실패는 decision 생성 응답(201)을 막지 않는다(AD-5) — decision 원본은 `decisions` 테이블이 정본이며, engagement 이벤트는 관측 편의를 위한 사본

**AC5 — 오프라인 평가 하네스 + 비교 리포트 (FR-8.5)**
- **Given** `engagement_events`(+ `decisions`/`outcomes`)에 데이터가 쌓였을 때
- **When** 평가 스크립트(`api/scripts/eval_engagement.py`)를 실행하면
- **Then** `impression`을 `variant`(rag vs coldstart)로 분할하여 **held-out engagement 비교 리포트**를 산출한다: variant별 CTR·read-through율·Learn Now율·Outcome 유용도를 표로 출력(+ 선택적 JSON/markdown 파일 저장)
- **And** 지표 정의가 문서화된다(스크립트 상단 docstring 또는 `api/scripts/METRICS.md`): **CTR** = opens/impressions, **read-through율** = read_through/opens, **Learn Now율** = learn_now decisions/impressions, **Outcome 유용도** = useful=true/(completed·applied outcomes) — 각 분자/분모와 이벤트 출처 명시
- **And** 리포트는 이것이 **무작위 A/B가 아닌 관찰적 cohort 비교**임을 명시(선택 편향 한계 주석) — 무작위 실험 프레임워크는 deferred

**AC6 — 스키마·RLS·무회귀 (AD-3, AD-9, AD-11, AD-15)**
- **Given** 신규 `engagement_events` 마이그레이션 적용 후
- **When** 스키마·RLS를 검증하면
- **Then** 마이그레이션은 **가산적(additive)**이며 기존 테이블·행 무변경; `engagement_events`는 RLS 활성 + `user_id = auth.uid()` SELECT 정책(AD-9의 user_id 직접 컬럼 허용 케이스 — `daily_briefs`/`memories`와 동형), 쓰기는 FastAPI service_role만(AD-3)
- **And** 배치·온디맨드 두 경로 모두 정상, brief 상태머신(pending→processing→completed/failed)·중복 스킵·stuck 정리·스케줄러(AD-15)·recommender 스코어링 로직/가중치(6.4) **무변경**
- **And** `cd api && pytest -q` 전체 회귀(현재 **221 passed**) 통과 + 신규 테스트 추가(엔드포인트·서버 impression best-effort·decision 로깅·평가 지표 계산 순수함수)

> ⚠️ **스코프 경계 (중요):** 이 스토리는 **"측정 인프라(로깅 + 오프라인 평가 하네스)"** 까지만 한다.
> - **하지 말 것:** 랭킹 로직·가중치(`_W_*`)·λ·반감기 **재튜닝**(6.5는 데이터를 *만든다*, 튜닝은 이 데이터로 하는 *다음* 결정), 6.4가 남긴 튜닝 후보 수정(`_recency_norm` 자정 해석·`_clamp` dead 상한 — deferred-work.md), 무작위 A/B 실험 프레임워크·feature flag, BI 대시보드/차트 UI, Flutter 클라이언트 계측, recommender/orchestrator/clustering/normalizer 스코어링 변경, `daily_briefs` 상태머신·스케줄러 변경.
> - **`impression`의 정본은 서버(brief 생성 시)** — 클라이언트 impression은 이번엔 로깅하지 않는다(이중 카운트·variant 신뢰 문제 회피, D2).
> - **`decision`의 정본은 `decisions` 테이블** — engagement 이벤트는 uniform 스트림용 사본. 평가 스크립트는 둘 중 어느 쪽을 읽어도 되지만 일관성 위해 engagement 스트림 기준.

## Tasks / Subtasks

- [x] **Task 1 — 마이그레이션: `engagement_events` 테이블 + RLS + 인덱스** (AC: 1, 6)
  - [x] `supabase/migrations/20260801000000_engagement_events.sql` 신규(파일명 날짜는 기존 최신 `20260731...` 이후로). 모든 DDL `IF NOT EXISTS`(멱등)
  - [x] 컬럼: `id UUID PK DEFAULT gen_random_uuid()`, `user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE`, `signal_id UUID NOT NULL REFERENCES public.signals(id) ON DELETE CASCADE`, `daily_brief_id UUID REFERENCES public.daily_briefs(id) ON DELETE SET NULL`, `event_type TEXT NOT NULL CHECK (event_type IN ('impression','open','read_through','decision'))`, `variant TEXT CHECK (variant IN ('rag','coldstart'))`, `metadata JSONB`, `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
  - [x] 인덱스: `idx_engagement_user_created (user_id, created_at)`, `idx_engagement_signal_type (signal_id, event_type)`, `idx_engagement_brief (daily_brief_id)`, `idx_engagement_variant (event_type, variant)`(평가 집계용)
  - [x] RLS: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;` + SELECT 정책 `USING (user_id = auth.uid())` (AD-9 user_id 직접 컬럼 허용 — `daily_briefs`·`memories`와 동형). INSERT/UPDATE/DELETE 정책은 두지 않음 → service_role만 쓰기(AD-3, 기존 테이블과 동일 패턴 — 기존 마이그레이션의 RLS 작성 방식 그대로 따를 것)
  - [x] ⚠️ 기존 마이그레이션(`20260723000000_initial_schema.sql`)의 RLS/정책/`updated_at` 트리거 작성 컨벤션을 **먼저 읽고 동일 스타일**로 작성(트리거 불필요 — engagement_events는 append-only, updated_at 없음)

- [x] **Task 2 — engagement 로깅 헬퍼(백엔드 공용)** (AC: 1, 2, 4)
  - [x] `api/pipeline/engagement.py`(신규) 또는 기존 위치에 `log_engagement(client, user_id, signal_id, event_type, *, daily_brief_id=None, variant=None, metadata=None) -> None`: `engagement_events` insert. **전체를 try/except로 감싸 실패해도 예외를 던지지 않음**(best-effort, AD-5). 실패 시 `logger`로만 경고
  - [x] 배치 삽입 편의: `log_engagement_bulk(client, rows: list[dict]) -> None`(서버 impression 다건용, best-effort)
  - [x] AD-12 관측성: 로깅 실패 시 구조화 경고(`event="engagement_log_failed"`, `event_type`, `signal_id`)

- [x] **Task 3 — 서버 사이드 `impression` + `variant` 정본 기록** (AC: 2, 6)
  - [x] `recommender._score_signals`가 **variant를 함께 반환**하도록 변경: 반환을 `(ordered: list[tuple[str,float]], variant: str)`로 확장. variant는 memory 분기에서 결정 — `memory_rag_applied` 경로 → `"rag"`, `memory_rag_coldstart`/RAG폴백/llm None → `"coldstart"` (기존 memory_count 분기 재사용, 새 쿼리 추가 금지)
  - [x] `create_daily_brief_for_user`: `_score_signals` 호출부(L499)에서 variant 수신. `daily_brief_signals` insert 성공(L552 이후) **직후** best-effort로 각 시그널 impression 로깅 — `log_engagement_bulk`로 `[{user_id, signal_id, event_type:'impression', daily_brief_id, variant, metadata:{position, relevance_score}}]`. brief는 이미 `completed`로 진행(로깅은 부수효과)
  - [x] ⚠️ 로깅은 `daily_brief_signals` insert 성공 이후에만(중복 스킵/실패 경로에선 로깅 안 함). brief_id·position·score는 이미 계산된 값 재사용(추가 쿼리 금지)
  - [x] ⚠️ `_score_signals` 반환 시그니처 변경 → 기존 테스트(`test_recommender_pipeline.py`)가 `scored` 언패킹하는 부분 전부 갱신 필요(삭제 아닌 갱신). 온디맨드 경로도 동일 함수 경유 → 자동 커버

- [x] **Task 4 — `POST /api/v1/engagement` 엔드포인트 (open·read_through 수집)** (AC: 1, 3)
  - [x] `api/routers/engagement.py`(신규) + `main.py`에 `include_router(engagement_router, prefix="/api/v1")` 등록(기존 라우터 등록 패턴 L125-134 그대로)
  - [x] 요청 모델: 배치 지원 `EngagementBatch{ events: list[EngagementEvent] }`, `EngagementEvent{ signal_id: str, event_type: Literal['impression','open','read_through'], daily_brief_id: str | None, metadata: dict | None }`. `decision`은 Literal에서 제외(422)
  - [x] `user_id`는 `Depends(get_current_user)`(JWT). 각 이벤트 best-effort insert(`log_engagement`). 응답은 `APIResponse(data={"accepted": n})`, 202/200. **개별 실패가 전체 요청을 막지 않음**
  - [x] signal_id 유효성: 존재하지 않는 signal_id는 FK 위반으로 insert 실패 → best-effort로 조용히 스킵(카운트에서 제외). UX 차단 없음
  - [x] ⚠️ AD-13 봉투(`{data,error}`)·Bearer 인증·`/api/v1/` 준수. 기존 `middleware/auth.get_current_user` 재사용

- [x] **Task 5 — `decision` 이벤트 서버 로깅(멱등 안전)** (AC: 4)
  - [x] `api/routers/decisions.py`: 신규 decision insert 성공(`decision_id` 확정, L120 근처) **직후** best-effort로 `decision` 이벤트 로깅. `signal_id`는 이미 조회한 review 컨텍스트 재사용 — 현재 review SELECT(L52-58)가 `id, project_id`만 가져오므로 **`signal_id` 컬럼 추가 SELECT** 필요(`.select("id, project_id, signal_id")`)
  - [x] variant는 NULL(평가 스크립트가 impression과 (user_id, signal_id)로 조인해 attach — D5). `metadata:{choice, queue_timing}`
  - [x] ⚠️ **멱등 경로에선 로깅 금지**: 기존 decision 반환(L1.5 existing, 재조회 retry) 분기에선 로깅하지 않고, `insert_result.data` 신규 성공 경로에서만 1회 로깅
  - [x] 로깅 실패는 201 응답을 막지 않음(try/except, AD-5)

- [x] **Task 6 — 웹 클라이언트 계측(open·read_through, fire-and-forget)** (AC: 3)
  - [x] `web/src`에 얇은 헬퍼 `trackEngagement(events)`: `POST /api/v1/engagement`를 fire-and-forget(`void fetch(...)`, 실패 무시, await로 렌더 막지 않음). 기존 API 호출/인증 헤더 패턴(웹의 FastAPI 호출 유틸) 재사용
  - [x] **open**: `review-page-content.tsx`(또는 review 진입점) 마운트 시 1회 `{signal_id, event_type:'open', daily_brief_id?}` 전송. StrictMode 이중 마운트/재조회 중복 방지(ref 가드)
  - [x] **read_through**: `context-sticky-bar.tsx`의 `allSeen → setEnabled(true)` 전환 지점(L84-87)에서 1회 `{signal_id, event_type:'read_through'}` 전송. `barGateOverride==='enabled'` 즉시 활성화 케이스는 자연 열람이 아니므로 전송 여부는 D 참고(추천: override로 즉시 enabled면 미전송 — 실제 읽기 아님)
  - [x] signal_id는 review 페이지가 이미 보유(`page.tsx` params `signalId`). 기존 web 테스트(`context-sticky-bar.test.tsx`) 무회귀 — track 호출을 mock/no-op 처리해 테스트 안정
  - [x] ⚠️ Flutter 미포함(D3). 웹만 계측

- [x] **Task 7 — 오프라인 평가 하네스 + 지표 문서** (AC: 5)
  - [x] `api/scripts/__init__.py` + `api/scripts/eval_engagement.py`(신규): `engagement_events`(+ 필요 시 `outcomes`)를 읽어 variant별 지표 계산. DB 읽기는 `core.supabase.get_supabase()`(service_role, 읽기 전용). `--output <path>`로 JSON/markdown 저장 옵션, 기본은 stdout 표
  - [x] **지표 계산은 순수 함수로 분리**(테스트 가능): `compute_metrics(events: list[dict], outcomes: list[dict]) -> dict` — variant별 CTR/read-through율/Learn Now율/Outcome 유용도. 분모 0 방어(변별 불가 시 None/NaN 대신 명시적 0 또는 "n/a")
  - [x] 지표 정의 문서: `api/scripts/METRICS.md`(또는 스크립트 상단 docstring) — 각 지표의 분자/분모/이벤트 출처 + **관찰적 cohort 비교 한계(선택 편향)** 명시
  - [x] ⚠️ 스크립트는 dev/ops 도구 — 프로덕션 DB 읽기 허용(AD-11의 "테스트"가 아니라 실행 스크립트). 단위 테스트는 `compute_metrics`를 합성 이벤트로 오프라인 검증(실 DB 금지)

- [x] **Task 8 — 테스트** (AC: 1~6)
  - [x] `api/tests/test_engagement.py`(신규): (1) `POST /engagement` 배치 수집 — 유효 이벤트 accepted 카운트, `decision` 타입 422, 존재 안 하는 signal_id best-effort 스킵, 인증 필요. (2) `log_engagement` best-effort — insert 예외 시 raise 안 함. Supabase `MagicMock`
  - [x] `test_recommender_pipeline.py` 확장: `_score_signals` variant 반환 검증(memory 있음 → 'rag', 없음/폴백 → 'coldstart'); `create_daily_brief_for_user`가 impression bulk 로깅 호출(mock 검증) + **로깅 실패해도 brief completed**(best-effort). 기존 `scored` 언패킹 테스트 시그니처 갱신
  - [x] `test_decisions.py`(있으면 확장, 없으면 신규): 신규 decision → 이벤트 1회 로깅, 멱등 재요청 → 로깅 0회, 로깅 실패 → 201 유지
  - [x] `test_eval_engagement.py`(신규): `compute_metrics` 순수함수 — 합성 이벤트로 variant별 CTR/read-through/Learn Now율/유용도 정확 계산, 분모 0 방어, rag vs coldstart 비교 출력 구조
  - [x] web: `context-sticky-bar.test.tsx` 무회귀 + open/read_through track 호출 검증(fetch mock, fire-and-forget이라 await 없음 확인)
  - [x] **오프라인 원칙(절대):** 실 네트워크·실 OpenAI·실 DB 금지. Supabase/fetch `MagicMock`
  - [x] **회귀:** `cd api && pytest -q` → **221 + 신규** 전부 green

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Code dev-story)

### Debug Log References

- 전체 회귀: `cd api && python3 -m pytest -q` → **247 passed** (기준선 221 + 신규 26).
- 웹 타입체크: `cd web && npx tsc --noEmit` → 신규/변경 파일(engagement.ts·review-page-content.tsx·context-sticky-bar.tsx) 클린. 사전 존재 에러 1건(`chat/page.tsx` `.then().catch()` 타이핑)만 잔존 — 이번 스토리와 무관.

### Completion Notes List

- **AC1/AC2 (서버 impression 정본 + variant):** `_score_signals`를 `(ordered, variant)` 튜플 반환으로 확장 — variant는 memory 분기 결과와 동일하게 파생(memory_rag_applied 경로 → `rag`, 그 외 → `coldstart`). `create_daily_brief_for_user`가 `daily_brief_signals` insert 성공 직후 `log_engagement_bulk`로 시그널당 impression(variant·position·relevance_score) 기록. 추가 쿼리 없이 기존 계산값 재사용. 로깅 호출을 try/except로 이중 감싸 실패해도 brief는 completed로 진행(best-effort, AD-5).
- **AC1/AC4 (decision 서버 로깅, 멱등 안전):** `decisions.py`의 review SELECT에 `signal_id` 추가(추가 쿼리 없음), 신규 insert 성공 경로에서만 `log_engagement`로 decision 이벤트 1회 기록(멱등/재조회 분기는 미로깅). 로깅 실패는 201을 막지 않음(try/except).
- **AC3 (수집 엔드포인트 + 웹 계측):** `POST /api/v1/engagement`(Bearer JWT·`{data,error}` 봉투) — `event_type ∈ {impression, open, read_through}`만 허용(decision은 Literal 제외 → 422). 존재하지 않는 signal_id는 best-effort 스킵(accepted 카운트 제외). 웹은 `trackEngagement`(fire-and-forget, `void fetch`)로 review-page 진입 시 `open`(ref 가드로 StrictMode 이중 마운트 방지), ContextStickyBar `enabled` 전환 순간 `read_through` 전송(override 즉시 활성화는 미전송 — 자연 열람 아님). Flutter 계측은 범위 밖(D3).
- **AC5 (오프라인 평가 하네스):** `api/scripts/eval_engagement.py` — `compute_metrics`(순수 함수)가 impression variant로 코호트를 나눠 CTR·read-through율·Learn Now율·Outcome 유용도를 계산(분모 0 → `"n/a"`, impression 없는 이벤트는 `unknown` 버킷). decision/open/outcome은 `(user_id, signal_id)`로 impression variant를 조인해 attach(D5). `--output`으로 JSON/markdown 저장. 지표 정의·관찰적 cohort 한계는 `api/scripts/METRICS.md` + 스크립트 docstring에 문서화.
- **AC6 (스키마·RLS·무회귀):** `20260801000000_engagement_events.sql` — 가산적(신규 테이블 1개, 기존 무변경), 모든 DDL `IF NOT EXISTS`(멱등), RLS 활성 + `user_id = auth.uid()` SELECT 정책, 쓰기 정책 부재 → service_role만(AD-3). recommender 스코어링 산식·가중치·MMR·상태머신·스케줄러 무변경 — 표면적은 "로깅 훅 + 신규 테이블 + 평가 스크립트"에 국한.
- **스코프 준수:** 랭킹 로직/가중치/λ/반감기 재튜닝 없음. 6.4 deferred 항목(`_recency_norm` 자정 해석·`_clamp` dead 상한) 미변경. 무작위 A/B·feature flag·BI UI·Flutter 계측 없음.
- **오너 확인 결정(D1~D5):** 스토리 명시대로 5개 모두 추천안대로 진행(신규 테이블 / 서버 impression 정본 / 웹 전용 계측 / 관찰적 cohort / decision variant NULL+조인).
- **실 DB 적용은 오너 단계(선택):** 단위 테스트는 전부 오프라인 mock. 마이그레이션 실 적용 + end-to-end 검증은 [[local-run-setup]]/[[seed-test-user-supabase]] 참고(Supabase MCP `apply_migration` 또는 로컬 CLI).
- **웹 테스트:** 이 프로젝트는 웹 테스트 러너 미설정 — `context-sticky-bar.test.tsx`는 비실행 스펙 문서다. read_through 계측 스펙 케이스(override 미전송·enabled 전환 1회·fire-and-forget)를 문서로 추가.

### File List

**신규**
- `supabase/migrations/20260801000000_engagement_events.sql`
- `api/pipeline/engagement.py`
- `api/routers/engagement.py`
- `api/scripts/__init__.py`
- `api/scripts/eval_engagement.py`
- `api/scripts/METRICS.md`
- `api/tests/test_engagement.py`
- `api/tests/test_eval_engagement.py`
- `web/src/lib/engagement.ts`

**수정**
- `api/pipeline/recommender.py` (`_score_signals` variant 반환 + impression 서버 로깅)
- `api/routers/decisions.py` (signal_id SELECT + decision 이벤트 로깅)
- `api/main.py` (engagement 라우터 등록)
- `api/tests/test_recommender_pipeline.py` (variant 반환·impression 로깅 테스트 + `_order` 언패킹 갱신)
- `api/tests/test_decisions.py` (decision 이벤트·멱등·best-effort 테스트)
- `web/src/components/home/review/review-page-content.tsx` (open track)
- `web/src/components/home/review/context-sticky-bar.tsx` (read_through track)
- `web/src/components/home/review/__tests__/context-sticky-bar.test.tsx` (계측 스펙 케이스)

## Dev Notes

### 아키텍처 준수 (반드시 따를 것)

- **AD-3 (데이터 접근 소유권):** `engagement_events` 쓰기는 **FastAPI service_role만**. 클라이언트(웹)는 직접 INSERT 금지 — 반드시 `POST /api/v1/engagement` 경유. RLS는 SELECT만 `user_id = auth.uid()` 허용(읽기), 쓰기 정책 부재 → service_role만 가능(기존 테이블과 동일 패턴).
- **AD-9 (RLS 패턴):** `engagement_events`는 `user_id` 직접 컬럼 보유 → `user_id = auth.uid()` 단순 정책 허용 케이스(`daily_briefs`·`memories`·`learning_paths`와 동형, project 경유 서브쿼리 불필요).
- **AD-5 (격리 / safe degradation):** **모든 engagement 로깅은 best-effort.** 서버 impression 로깅 실패 → brief는 여전히 completed. decision 이벤트 로깅 실패 → 201 정상. 클라이언트 전송 실패 → 화면 무영향(fire-and-forget). engagement는 관측 데이터일 뿐, 핵심 플로우를 절대 막지 않는다.
- **AD-12 (관찰 가능성):** 로깅 실패는 구조화 경고(`engagement_log_failed`)로 남겨 "왜 데이터가 비었나" 추적 가능. 평가 스크립트도 처리 건수·기간을 로깅.
- **AD-13 (API 계약):** `POST /api/v1/engagement`는 Bearer JWT·`/api/v1/`·`{data,error}` 봉투·`middleware/auth.get_current_user` 재사용. 웹/모바일 분기 엔드포인트 금지(Flutter도 같은 엔드포인트를 쓰게 될 것 — 이번엔 미계측일 뿐).
- **AD-15 (Batch First + On-demand):** 서버 impression은 `create_daily_brief_for_user`(배치·온디맨드 공통 경로)에 붙어 **두 경로 모두** 자동 계측. 실행 모델·순서·스케줄러 무변경.
- **AD-11 (테스트 전략):** 엔드포인트·로깅 헬퍼·평가 순수함수는 FastAPI 단위 테스트(Supabase mock). 실 DB·실 LLM·실 네트워크 금지. 평가 스크립트 본체(실 DB 읽기)는 테스트 대상 아님 — `compute_metrics`만 합성 데이터로 검증.

### 설계 결정 (Dev가 반드시 이 방향으로 구현)

**D1 — 신규 `engagement_events` 테이블 (activities 확장이 아님):**
AC는 "신규 테이블 또는 기존 확장"을 허용한다.
- **채택:** 신규 `engagement_events`. `activities`(project_id 스코프, UI 타임라인 감사 로그)와 목적·스코프·쿼리 패턴이 다르다 — engagement는 `user_id`+`signal_id`+`variant` 스코프, 고빈도 append, held-out 평가용 집계 쿼리(variant/event_type 인덱스). `activities`에 억지로 넣으면 project_id 강제·스키마 오염.
- **사이드이펙트:** 테이블 1개 추가(마이그레이션). 단, 가산적이고 기존 무변경이라 회귀 위험 낮음.

**D2 — `impression`은 서버 정본, 클라이언트 impression 미로깅:**
impression을 "카드가 화면에 떴다"로 클라이언트에서 잡을 수도 있으나,
- **채택:** brief 생성 시 서버에서 시그널당 1건 impression 로깅. **이유:** (a) `variant` 라벨이 서버에서만 신뢰 가능(클라 조작·유실 없음), (b) held-out 평가의 분모(impressions)가 결정론적, (c) 클라 계측 없이도 Learn Now율(=decisions/impressions) 비교가 완결. 클라 impression은 이중 카운트·신뢰 문제를 만든다.
- **사이드이펙트:** "brief에 담김"과 "실제 눈에 보임"의 차이(사용자가 home을 안 열면 impression은 있으나 open 없음). 이는 오히려 CTR(open/impression)의 자연스러운 정의 — home 미방문은 낮은 CTR로 반영됨. 정밀 뷰포트 impression이 필요하면 향후 클라 계측 추가(deferred).

**D3 — 클라이언트 계측은 웹만(Flutter deferred):**
- **채택:** 웹에서 open·read_through만 계측. Flutter는 이번 범위 밖.
- **이유:** 6.5의 목표는 "측정 데이터 + 평가 절차 확보". 서버 impression + 서버 decision + 웹 open/read_through면 **핵심 비교(Learn Now율·read-through율 by variant)가 성립**한다. Flutter 계측은 표면적만 키우고 핵심 결론을 바꾸지 않음.
- **사이드이펙트:** Flutter 사용자의 open/read_through는 미집계 → 그 지표는 웹 코호트 기준. 리포트에 "웹 계측 한정" 명시. Flutter 계측은 동일 엔드포인트라 향후 추가 저비용.

**D4 — `variant`는 관찰적 cohort (무작위 A/B 아님):**
- **채택:** variant = 그 사용자·brief가 실제 탄 랭킹 경로(Memory 보유 → `rag`, 미보유 → `coldstart`). 이는 무작위 배정이 아니라 "이미 갈라진 두 집단"의 관찰 비교.
- **이유:** 무작위 A/B(같은 사용자에게 rag/coldstart를 랜덤 배정)는 실험 인프라·사용자 경험 트레이드오프가 크고 MVP 스코프 밖. 관찰 비교로도 "RAG가 콜드스타트보다 나은가"의 1차 신호는 얻는다.
- **사이드이펙트:** 선택 편향(Memory 보유 사용자 = 이미 활발한 사용자일 수 있어 engagement가 원래 높음). **리포트에 이 한계를 반드시 명시.** 엄밀한 인과는 향후 무작위 실험(deferred)에서.

**D5 — `decision` 이벤트는 variant NULL, 평가 시 impression과 조인:**
- **채택:** decision 이벤트에 variant를 직접 안 넣고(결정 시점에 재계산 비용·불일치 위험), 평가 스크립트가 `(user_id, signal_id)`로 impression(variant 보유)과 조인해 variant를 attach.
- **이유:** decision router 핫패스에 memory 재조회를 넣지 않음(성능·단순성). variant 정본은 impression 한 곳.
- **사이드이펙트:** impression 없이 decision만 있는 이례 케이스(예: impression 로깅만 실패)는 variant 미상 → 평가에서 'unknown' 버킷으로 분리(누락 대신 가시화).

### 수집할 기존 파일 — 현재 상태 / 변경 / 보존

- **`api/pipeline/recommender.py`** (변경):
  - `_score_signals`(L303-): 현재 `list[tuple[str,float]]` 반환. **variant 동반 반환으로 확장**(Task 3). memory 분기(L358-409)에서 variant 결정 — 새 쿼리 없이 기존 `memory_count` 재사용. 스코어링 산식·가중치·MMR **무변경**.
  - `create_daily_brief_for_user`(L~460-575): `_score_signals` 호출(L499) 언패킹 갱신, `daily_brief_signals` insert(L542-552) **직후** best-effort impression bulk 로깅 추가. brief 상태머신·중복 스킵·insert 골격 **무변경**.
  - `run_recommender`: **무변경**(사용자 루프가 create_daily_brief_for_user 호출 → 자동 계측).
- **`api/routers/decisions.py`** (변경, 최소): review SELECT에 `signal_id` 추가(L52-58), 신규 insert 성공 직후(L120 근처) best-effort decision 이벤트 로깅. 멱등·검증·에러 경로 **무변경**.
- **`api/routers/reviews.py`** (보존, 무변경): open은 클라이언트발이라 서버 trigger에 훅 안 붙임(trigger는 "생성"이지 "열람"이 아님 — 이미 생성된 review 재열람도 open). open 정의 = 사용자가 상세를 봄 = 웹 계측.
- **`api/main.py`** (변경, 최소): engagement 라우터 등록 1줄(L133 근처).
- **`api/pipeline/logger.py`** (보존, 참고): `pipeline_log` 패턴을 engagement 실패 경고에 재사용 가능(또는 표준 logger).
- **`web/src/components/home/review/context-sticky-bar.tsx`** (변경): `allSeen→setEnabled(true)` 전환(L84-87)에 read_through track 1회. 나머지 IntersectionObserver 로직 **무변경**.
- **`web/src/components/home/review/review-page-content.tsx`** (변경): 마운트 시 open track 1회(ref 가드).
- **`supabase/migrations/`** (신규 1개): `20260801000000_engagement_events.sql`. 기존 마이그레이션 **무변경**. 기존 RLS/정책 작성 스타일을 그대로 따를 것.

### 라이브러리 / 버전

- **신규 의존성 없음.** 백엔드 표준 라이브러리 + 기존 FastAPI/Supabase 클라이언트. 평가 스크립트도 표준 라이브러리(집계는 순수 파이썬 dict/카운팅 — numpy·pandas 도입 금지, 6.2/6.3/6.4와 동일 "인프로세스 순수 파이썬" 원칙 유지).
- DB: pgvector 무관(스칼라 이벤트 로깅). 신규 벡터 컬럼·RPC 없음.
- LLM: 호출 없음(로깅·집계는 LLM 무관).
- 웹: 기존 fetch/인증 유틸 재사용, 신규 패키지 없음.

### 회귀 주의 (반드시 확인)

- **`_score_signals` 반환 시그니처 변경(핵심 회귀 지점):** `(list, variant)` 튜플로 바뀌므로 `create_daily_brief_for_user`의 `scored = _score_signals(...)`(L499)와 **모든 기존 테스트의 언패킹**을 갱신. 놓치면 `scored`가 튜플이 되어 enumerate가 깨진다 — 테스트로 잡되 삭제 아닌 갱신.
- **best-effort 불변:** impression/decision 로깅 실패가 brief completed·decision 201을 **절대** 막으면 안 됨. try/except가 로깅 전체를 감싸는지, 예외가 밖으로 새지 않는지 테스트로 증명(로깅 mock에 `side_effect=Exception`).
- **멱등 중복 로깅:** decision 멱등 재요청(동일 review_id 재POST)이 decision 이벤트를 중복 생성하면 Learn Now율 분자가 부풀려짐. **신규 insert 경로에서만** 로깅 — 멱등/재조회 분기 제외. 테스트로 검증.
- **variant 일관성:** impression의 variant가 pipeline_log(`memory_rag_applied`/`coldstart`)와 어긋나면 평가가 틀림. 같은 memory_count 분기에서 파생하도록(중복 판정 로직 신설 금지).
- **RLS 회귀:** `engagement_events` RLS 정책이 기존 테이블 접근에 영향 없어야 함(독립 테이블). 웹은 이 테이블을 직접 SELECT하지 않음(서버 경유 평가) — 정책은 방어적 최소.
- **웹 fire-and-forget:** track 호출이 `await`로 렌더/네비게이션을 막지 않는지, StrictMode 이중 마운트로 open이 2번 안 가는지(ref 가드). 기존 `context-sticky-bar.test.tsx`·`research-review-content.test.tsx` 무회귀.
- **마이그레이션 멱등:** `IF NOT EXISTS`로 재적용 안전. FK CASCADE/SET NULL 방향 확인(user·signal 삭제 시 이벤트 정리, brief 삭제 시 이벤트 보존+NULL).
- `cd api && pytest -q` → 현재 **221 passed**. 6.5 후 그대로 통과 + 신규.

### 파일 구조 (신규/수정)

```
supabase/migrations/20260801000000_engagement_events.sql   (신규 — 테이블+RLS+인덱스, 가산적)
api/pipeline/engagement.py                                 (신규 — log_engagement / log_engagement_bulk, best-effort)
api/routers/engagement.py                                  (신규 — POST /api/v1/engagement, open·read_through 수집)
api/scripts/__init__.py                                    (신규)
api/scripts/eval_engagement.py                             (신규 — 오프라인 평가 하네스 + compute_metrics 순수함수)
api/scripts/METRICS.md                                     (신규 — 지표 정의·한계 문서)
api/pipeline/recommender.py                                (수정 — _score_signals variant 반환 + impression 서버 로깅)
api/routers/decisions.py                                   (수정 — signal_id SELECT + decision 이벤트 로깅)
api/main.py                                                (수정 — engagement 라우터 등록 1줄)
web/src/.../review/context-sticky-bar.tsx                  (수정 — read_through track)
web/src/.../review/review-page-content.tsx                 (수정 — open track)
web/src/lib/... (track 헬퍼)                                (신규/수정 — trackEngagement fire-and-forget)
api/tests/test_engagement.py                               (신규)
api/tests/test_eval_engagement.py                          (신규)
api/tests/test_recommender_pipeline.py                     (수정 — variant 반환·impression 로깅·언패킹 갱신)
api/tests/test_decisions.py                                (신규/수정 — decision 이벤트·멱등·best-effort)
web/src/.../__tests__/context-sticky-bar.test.tsx          (수정 — track 호출 검증·무회귀)
```
> recommender **스코어링 산식·가중치·MMR·clustering·normalizer·orchestrator·스케줄러 무변경.** 표면적은 "로깅 훅 + 신규 테이블 + 평가 스크립트"에 국한 — 기존 파이프라인 로직 불변.

### 테스트 표준

- **프레임워크:** pytest 8.3.4, `pytest.ini`(`testpaths=tests`, `asyncio_mode=auto`), `test_*.py`, `api/tests/`. 웹은 기존 vitest/jest 설정(`__tests__`).
- **오프라인 원칙(절대):** 실 네트워크·실 OpenAI·실 DB 금지. Supabase `MagicMock`(기존 라우터/파이프라인 테스트 패턴), 웹 `fetch` mock. 평가 지표는 합성 이벤트 리스트로 결정적 검증.
- **커버리지 대상:** (1) `POST /engagement` 수집·타입 검증·인증·best-effort 스킵, (2) `log_engagement` 예외 무전파, (3) `_score_signals` variant 반환, (4) 서버 impression bulk 로깅 + 실패해도 brief completed, (5) decision 이벤트 1회·멱등 0회·실패 시 201, (6) `compute_metrics` variant별 지표·분모 0 방어, (7) 웹 open/read_through track·무회귀, (8) 전체 회귀 221 passed.

### Project Structure Notes

- 백엔드는 `api/` 루트 실행(PYTHONPATH=`api`, import `pipeline.*`·`routers.*`·`core.*`). 로컬 실행/DB 접속은 [[local-run-setup]] 참고.
- 마이그레이션은 Supabase MCP `apply_migration` 또는 로컬 CLI로 적용. 실 DB 검증(engagement 흐름 end-to-end)이 필요하면 [[seed-test-user-supabase]] 패턴으로 시드 후 brief 배치 실행 → engagement_events 확인 → `eval_engagement.py` 실행. 단, 단위 테스트는 전부 오프라인 mock.
- 이 스토리는 [[epic-6-real-data-ingestion]]의 5번째(마지막) 단계(6.1 수집·6.2 클러스터·6.3 스키마·6.4 랭킹·**6.5 측정**). 6.5가 쌓는 데이터가 이후 랭킹 재튜닝(6.4 deferred 항목 포함)의 근거가 된다.
- 충돌/변이: recommender 반환 시그니처 변경(테스트 동반 갱신)이 유일한 주의점. 그 외는 신규 파일·가산 마이그레이션·최소 훅.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.5 측정 하네스 & Engagement 로깅 (AC: impression/open/read-through/decision 로깅·held-out 비교·지표 정의), #Epic 6 FR-8.5(L57,L900), #스파이크 근거(L902)]
- [Source: _bmad-output/implementation-artifacts/6-4-recommender-v2.md#Dev Notes(variant=memory_rag_applied/coldstart, scorer 표식), #스코프 경계(6.5로 넘긴 튜닝: RAG weight·정규화 블렌드)]
- [Source: _bmad-output/implementation-artifacts/deferred-work.md#L5(_clamp dead 상한·테스트 명명 — 6.5 튜닝 시), #L7(_recency_norm 자정 해석 — 6.5 튜닝 시), #L268(클러스터 임계치 실측 검증 — 6.5 이후)] — **이 스토리에선 손대지 않음(측정만)**
- [Source: api/pipeline/recommender.py L303-428 (_score_signals — variant 반환 확장), L358-409 (memory 분기 = variant 출처), L499 (호출부 언패킹), L542-552 (daily_brief_signals insert = impression 훅), L42-43 (_clamp)]
- [Source: api/routers/decisions.py L52-58 (review SELECT — signal_id 추가), L85-120 (insert·멱등·decision_id — 신규 성공 경로에서만 로깅)]
- [Source: api/routers/reviews.py L14-82 (trigger — open 훅 대상 아님, open은 웹 계측)]
- [Source: api/main.py L13-21,L125-134 (라우터 import·등록 패턴 — engagement 추가)]
- [Source: api/pipeline/logger.py (pipeline_log — AD-12 관측성 패턴)]
- [Source: supabase/migrations/20260723000000_initial_schema.sql L145-152 (activities — 확장 대신 신규 이유 D1), L180-211 (daily_briefs/daily_brief_signals — FK·position), L109-123 (outcomes.useful/status — 유용도 지표), RLS/정책 작성 스타일]
- [Source: supabase/migrations/20260731000000_signals_schema_v2.sql (가산적 마이그레이션 스타일 — IF NOT EXISTS 멱등 참고)]
- [Source: web/src/components/home/review/context-sticky-bar.tsx L31-87 (enabled 전환 = read_through 훅), review-page-content.tsx (open 훅), page.tsx(signalId param)]
- [Source: architecture/architecture-decision-os-2026-07-21/ARCHITECTURE-SPINE.md#AD-3(쓰기 FastAPI만), #AD-5(safe degradation), #AD-9(user_id 직접 RLS), #AD-11(테스트), #AD-12(관측성), #AD-13(API 계약), #AD-15(Batch+On-demand)]

### 🟡 오너 확인이 필요한 결정 (dev-story 착수 전 권장)

CLAUDE.md 규칙(추천안·이유·사이드이펙트)에 따라 다섯 가지를 짚습니다. **다섯 개 모두 "추천안대로" 진행해도 무방하며**, 위 Tasks/Dev Notes는 추천 방향으로 작성되어 있습니다.

- **D1 — 신규 `engagement_events` 테이블 (추천) vs `activities` 확장**
  - **추천 이유:** engagement는 `user_id`+`signal_id`+`variant` 스코프의 고빈도 append + 평가용 집계 쿼리. `activities`(project 스코프 UI 감사 로그)와 목적·인덱스가 달라 섞으면 오염된다.
  - **사이드이펙트:** 테이블 1개 추가. 가산적이라 회귀 위험은 낮음.

- **D2 — `impression` 서버 정본 (추천) vs 클라이언트 뷰포트 계측**
  - **추천 이유:** variant 라벨 신뢰성·평가 분모 결정성. 서버만으로 Learn Now율 비교가 완결.
  - **사이드이펙트:** "brief에 담김 ≠ 실제로 봄". CTR이 home 미방문을 낮은 값으로 반영(정의상 자연스러움). 정밀 뷰포트 impression은 향후 클라 계측(deferred).

- **D3 — 클라이언트 계측 웹만 (추천) vs 웹+Flutter**
  - **추천 이유:** 서버 impression+decision + 웹 open/read_through로 핵심 비교 성립. Flutter는 표면적만 키움.
  - **사이드이펙트:** Flutter open/read_through 미집계 → 해당 지표는 웹 코호트 한정(리포트 명시). 동일 엔드포인트라 추후 저비용 추가.

- **D4 — 관찰적 cohort 비교 (추천) vs 무작위 A/B 실험**
  - **추천 이유:** 무작위 A/B는 실험 인프라·UX 트레이드오프가 커 MVP 밖. 관찰 비교로 1차 신호 확보.
  - **사이드이펙트:** 선택 편향(Memory 보유=활발 사용자일 수 있음) → 엄밀 인과 아님. 리포트에 한계 명시. 무작위 실험은 deferred.

- **D5 — decision 이벤트 variant NULL + 평가 시 조인 (추천) vs 결정 시점 variant 재계산**
  - **추천 이유:** decision 핫패스에 memory 재조회를 넣지 않음(성능·단순성). variant 정본은 impression 한 곳.
  - **사이드이펙트:** impression 없이 decision만 있는 이례 케이스는 'unknown' 버킷 → 누락 대신 가시화.

## Change Log

- 2026-07-29: Story 6.5 컨텍스트 생성(create-story) — engagement 로깅(신규 `engagement_events` 테이블, 서버 impression+variant 정본, decision 서버 로깅, `POST /engagement` + 웹 open/read_through 계측) + 오프라인 평가 하네스(`eval_engagement.py` + `compute_metrics` + 지표 문서, 관찰적 cohort RAG vs 콜드스타트 비교) 설계. 스코프: 측정 인프라만 — 랭킹 재튜닝은 이 데이터로 하는 다음 결정(6.4 deferred 항목 미변경). Status → ready-for-dev.
- 2026-07-29: Story 6.5 구현(dev-story) — 마이그레이션(engagement_events + RLS + 4 인덱스, 가산적)·로깅 헬퍼(`engagement.py` best-effort)·`_score_signals` variant 반환 + 서버 impression 정본 로깅·`POST /api/v1/engagement`(decision 422·존재 안 하는 signal best-effort 스킵)·decision 서버 로깅(멱등 0회·실패 무영향)·웹 open/read_through fire-and-forget 계측·오프라인 평가 하네스(`compute_metrics` + `METRICS.md`) 구현. 신규 테스트 26개 추가, `cd api && pytest -q` → **247 passed**(221→247, 무회귀). recommender 스코어링·상태머신·스케줄러 무변경. Status → review.
- 2026-07-29: Story 6.5 코드 리뷰(bmad-code-review, 3-layer) — AC1~AC6·D1~D5 충족·스코프 준수 확인. 3 decision(2 현행유지 dismiss, 1 → patch)·3 patch 적용(variant 충돌 unknown 분리·open signalId 가드·eval output 확장자 가드)·7 defer·15 dismiss. 신규 테스트 2개 추가 → `cd api && pytest -q` **249 passed**(무회귀), 웹 타입체크 클린. Status → done.

## Review Findings

_코드 리뷰 2026-07-29 (bmad-code-review, 3-layer: Blind Hunter / Edge Case Hunter / Acceptance Auditor). 범위: 6.5 신규 9 + 수정 8 파일. Acceptance Auditor 결과 AC1~AC6·D1~D5 모두 충족, 스코프 경계(랭킹 재튜닝 없음) 준수 확인._

### Decision Needed (오너 판단 필요) — 3건 모두 해결(2026-07-29)

- [x] [Review][Decision] 평가 지표 분모 dedup 의미 [api/scripts/eval_engagement.py:90-119] — **결정: 현행 유지("노출 건수" 기준)**. 코드 무변경. 비율 왜곡(>1.0) 가능성은 리포트 헤더의 관찰적 코호트 한계 주석으로 커버.
- [x] [Review][Decision] RLS가 `variant` 코호트 라벨을 클라이언트 SELECT에 노출 [supabase/migrations/20260801000000_engagement_events.sql:64-65] — **결정: 현행 유지(SELECT 허용)**. daily_briefs·memories와 동형 패턴, 웹은 이 테이블 직접 조회 안 함. 코드 무변경.
- [x] [Review][Decision] decision 이벤트 다중-brief 귀속 [api/routers/decisions.py:130-138] — **결정: D5 유지 + 충돌시 'unknown' 분리** → 아래 Patch(variant 충돌 last-write-wins)로 처리.

### Patch (수정 권장 — 이번 변경이 유발, 수정 명확) — 3건 모두 적용(2026-07-29)

- [x] [Review][Patch] variant 충돌 시 무음 last-write-wins — **적용**: `variant_by_key`가 같은 (user,signal)에 상이한 variant impression을 만나면 'unknown'으로 분리(충돌 가시화, Decision 3 반영). 신규 테스트 `test_conflicting_variant_for_same_key_goes_unknown`. [api/scripts/eval_engagement.py:64-77]
- [x] [Review][Patch] `open` 이벤트가 signalId 변경 시 재전송 안 됨 — **적용**: `openTrackedRef`(boolean) → `openTrackedSignalRef`(마지막 추적 signalId 비교)로 변경. 같은 signalId는 중복 방지, 바뀌면 새 open 전송. [web/src/components/home/review/review-page-content.tsx:51-59]
- [x] [Review][Patch] eval `--output` 미지원 확장자 무음 오기록 — **적용**: `.json`/`.md`가 아니면 경고 출력 + exit 2(DB 접근 전 반환). 신규 테스트 `test_main_rejects_unsupported_output_extension`. [api/scripts/eval_engagement.py:214-219]

### Deferred (기존/스코프 밖 또는 향후 하드닝 — deferred-work.md에도 기록)

- [x] [Review][Defer] `_recency_norm`이 `brief_date`를 "현재"로 사용 → 과거 날짜 재생성 시 relevance_score 비재현 [api/pipeline/recommender.py:103-117] — deferred, 6.4 코드·6.5 스코프 밖(deferred-work 기존 항목)
- [x] [Review][Defer] `log_engagement_bulk` all-or-nothing — 한 개 나쁜 signal_id가 brief 전체 impression 유실 [api/pipeline/engagement.py:62-82] — deferred, 스토리가 "부분 성공/재시도 안 함(격리 우선)"을 명시적 선택. 향후 측정 완결성 필요 시 per-row fallback
- [x] [Review][Defer] `variant` 어휘 3중 중복(migration CHECK / recommender / eval, 단일 소스 없음) [api/pipeline/recommender.py:363,406] — deferred, 유지보수(공용 상수화)
- [x] [Review][Defer] `POST /engagement` 배치 크기 상한 없음 → 한 요청이 대량 insert 유발 가능 [api/routers/engagement.py:36-71] — deferred, 인증+best-effort라 위험 낮음. 하드닝(MAX_BATCH)
- [x] [Review][Defer] `NEXT_PUBLIC_FASTAPI_URL` 미설정 시 prod에서 localhost:8000로 전송→유실 [web/src/lib/engagement.ts:36-37] — deferred, 앱 전역 기존 패턴(reviews/decisions 동일). 앱 차원 env 검증
- [x] [Review][Defer] `load_outcomes_enriched` 전체 테이블 스캔 + 깨진 lineage 무음 드롭 [api/scripts/eval_engagement.py:183-206] — deferred, dev 도구·소규모 데이터. 스케일 시 필터/경고
- [x] [Review][Defer] `/engagement` 엔드포인트가 `log_engagement` 헬퍼 재사용 안 하고 insert 로직 중복 [api/routers/engagement.py:55-69] — deferred, DRY 리팩터(기능 동일·AD-12 경고 존재)
