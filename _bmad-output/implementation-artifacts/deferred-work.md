# Deferred Work Log

## Deferred from: code review of 5-2-history-memory-timeline (2026-07-28)

- Chain 상세가 `signalId`만으로 "최신 completed review→최신 decision"을 재조회 — 한 signal에 완료 review/decision이 복수면 리스트에서 탭한 항목과 다른 체인이 표시됨 (`web/src/components/history/history-content.tsx:75`, `web/src/app/(app)/history/chain/[signalId]/page.tsx:29-53`, Flutter 동일 구조). `api/routers/reviews.py:50-63` 멱등성 가드가 pending/processing만 재사용하고 `completed`는 막지 않아 on-demand 재-리뷰(Story 3.2)+재결정 시 도달 가능. 스펙 설계 귀결(AC-4 라우트 `/history/chain/:signalId` + Task 8.1 "최신 해석")이며 올바른 수정은 리스트 탭이 decisionId(또는 reviewId)를 딥링크로 전달하고 상세가 그 결정 기준으로 review/outcome을 역산하도록 웹 라우트·Flutter 중첩 라우트·양쪽 provider를 함께 바꾸는 스펙 계약 확장 → 재-리뷰 흐름 활성화 전 별도 스토리로. "충실한 결정 기록" 신뢰성에 직결되므로 우선순위 있게 검토.
- review payload 내부 필드(`honest_box`/`reference_sources`/`learning_time_difficulty`)를 무방어 접근 — 부분/불완전 payload면 Server Component 렌더 중 500 (`web/src/components/home/review/review-sections.tsx:59,70,123`) — `research-review-content.tsx`에서 순수 추출된 pre-existing 로직, Home Review 경로가 동일 코드로 이미 렌더 중. payload는 reviewer 에이전트 고정 스키마 생성 + `chk_result_envelope` 제약으로 실질 well-formed. Chain 상세가 신규 소비자로 추가된 점만 새로움 → payload 파서/방어 도입 시 양 경로 동시 처리.
- `estimated_hours` 표기 크로스플랫폼 불일치: Web raw(`2.5시간`) vs Flutter `toStringAsFixed(0)` 반올림(`3시간`) (`web review-sections.tsx:62` vs `mobile/lib/features/home/widgets/review_sections.dart`) — 양측 추출 전 기존 동작 보존(pre-existing). 표기 통일 시 두 플랫폼 동시 수정.
- Flutter `reference_sources` 링크가 `onTap: () {}` no-op(죽은 어포던스), Web은 새 탭 오픈 (`mobile/lib/features/home/widgets/review_sections.dart`) — 추출 전 동작 보존(pre-existing). url_launcher 도입 시 처리.
- `outcome.useful` 필드를 web/Flutter 모델 끝까지 운반하나 렌더링 안 함(죽은 필드) (`web chain-detail-content.tsx:14`, `mobile chain_detail_provider.dart`) — minor cleanup, 향후 Outcome 상세 표시 확장 시 활용 또는 제거.

## Deferred from: code review of 5-1-queue-탭 (2026-07-27)

- Web 큐 테스트 파일이 실행 불가능한 "테스트 스펙 문서"임(Jest/Vitest 미설정) (`web/src/components/queue/__tests__/queue-item.test.tsx:1-6`) — Epic 2부터 이어진 저장소 전역 컨벤션, 이번 스토리가 만든 문제 아님. 테스트 인프라 구성 시 처리.
- `isOverdue`가 `updated_at` 기반이라 DB 트리거가 무관한 갱신에도 값을 리셋시켜 미완료 판정에 영향을 줄 수 있음 (`api/routers/decisions.py:182`) — AC-3가 문자 그대로 요구하는 공식, 스펙 차원의 한계. 별도 스토리에서 전용 컬럼(예: `queue_timing_set_at`) 도입 검토.
- 미완료 판정이 플랫폼 간 다른 시계 기준 사용(Web: 서버 1회 계산 / Flutter: 기기 로컬 시계로 매 빌드 재계산) (`mobile/lib/features/queue/providers/queue_provider.dart:24-26`) — Dev Notes 라인 359에 문서화된 스펙 갭 결정에서 기인. 기기 시계 오설정 사용자에게만 영향, 낮은 확률.
- PATCH 엔드포인트의 UPDATE 쿼리 자체에 `choice='queue'` 가드가 없어 좁은 TOCTOU 윈도우 존재 (`api/routers/decisions.py:183-188`) — 현재 choice를 변경하는 코드 경로가 없어 실질적으로 도달 불가능. choice 변경 기능이 추가되면 재검토.
- 두 기기에서 동시 PATCH 시 last-write-wins, 충돌 감지 없음 (`api/routers/decisions.py:183-188`) — 저위험(파괴적이지 않은 일정 선호도 변경).
- `reviews.signal_id`가 nullable이라 이론적으로 `/queue/review/null` 내비게이션 가능 (`web/src/app/(app)/queue/page.tsx:38`) — 실제 앱 플로우에서는 도달 불가능한 데이터 무결성 엣지 케이스.
- 큐 목록 조회 쿼리에 페이지네이션/limit 없음 (`web/src/app/(app)/queue/page.tsx:15-19`) — 현재 규모에서는 문제없음, 헤비 유저 누적 시 성능 저하 가능.
- `test_decisions.py`의 `_base_mock`이 `.eq()` 호출 인자를 검증하지 않아 필터 컬럼 회귀를 못 잡음 (`api/tests/test_decisions.py:33-53`) — Story 3.3부터 이어진 테스트 설계 패턴, 신규 PATCH 테스트도 동일 패턴 답습. 테스트 인프라 개선 패스에서 처리.

## Deferred from: code review of 4-3-memory-manager (2026-07-27)

- `run_memory_manager_from_outcome`에서 `get_supabase()`/`OpenAIProvider()` 생성이 try/except 밖에 있어 생성 실패 시 예외가 BackgroundTask 밖으로 전파될 수 있음 (`api/pipeline/memory_manager.py:98-106`) — `coach.py`의 `run_learning_path_from_pending`(`api/pipeline/coach.py:131-132`)에도 동일한 기존 패턴이 있어 이 스토리 단독으로 고치면 컨벤션 불일치 발생. 별도 스토리에서 두 파이프라인을 함께 수정할 것.
- `memories`에 상태 컬럼/재시도 로직이 없어 일시적 실패(LLM/DB 장애 등) 시 Memory가 영구적으로 조용히 유실됨 — Dev Notes AD-5 예외 섹션에서 의도적으로 결정된 스코프("실패 시 사용자는 알 수 없고 알 필요도 없음"). 향후 이 리스크가 문제되면 별도 스토리로 재검토.
- FastAPI `BackgroundTasks`는 재배포/워커 재시작 시 실행 중이던 작업이 유실될 수 있는 내구성 한계가 있음 — `coach.py`/`learning_paths.py` 등 기존 파이프라인 전부가 동일한 아키텍처를 사용 중이라 이 스토리만의 문제가 아님.
- `review.signal_id`가 가리키는 `signals` row가 삭제된 경우(dangling reference) signal 조회가 예외를 던져 전체 Memory 추출이 중단됨(널 signal_id 경로처럼 우아하게 성능 저하하지 않음) (`api/pipeline/memory_manager.py:44-49`) — 현재 앱에 signal 삭제 플로우가 없어 도달 불가능한 경로. 삭제 기능이 추가되면 재검토.

## Deferred from: code review of 4-2-outcome-기록 (2026-07-27)

- `outcomes.decision_id`에 DB unique 제약 없음 (`api/routers/outcomes.py`) — 동시 요청 시 이론상 중복 row 가능. Dev Notes "스펙 갈등 2"에서 이미 스코프 밖으로 명시적 합의됨.
- INSERT 주변의 광범위한 `except Exception` + empty-data 시 403 처리 (`api/routers/outcomes.py:99-133`) — supabase-py는 보통 빈 리스트 대신 예외를 던지므로 이 분기는 도달 불가능할 수 있음. Dev Notes 지시대로 이미 승인된 `decisions.py` 패턴을 그대로 재사용한 것.
- `decision_id`에 UUID 형식 검증 없음 (`api/routers/outcomes.py:14`) — 잘못된 값이 처리되지 않은 500으로 노출됨. `decisions.py`의 `review_id`에도 동일한 기존 갭 존재.
- `main.py` lifespan Supabase 헬스체크가 실패를 삼키고 그냥 부팅함, CORS가 `allow_credentials=True` + wildcard methods/headers로 설정됨, APScheduler `.start()`가 unhandled (`api/main.py`) — 모두 이 스토리가 건드리지 않은 기존 코드(`outcomes_router` 등록 한 줄만 신규).
- Web/Mobile의 Supabase 조회가 일시적 에러와 "not found"를 구분하지 않고 둘 다 `/home`으로 리다이렉트함 (`web/.../outcome/page.tsx`, `mobile/.../outcome_provider.dart`) — `learning-path/page.tsx`에서 재사용한 기존 패턴, 이 스토리 범위를 넘는 프로젝트 전역 컨벤션.

## Deferred from: code review of 4-1-learning-path-생성-and-화면 (2026-07-27)

- W1: `api/pipeline/reviewer.py:193`에 동일한 `OpenAIProvider()` 무인자 호출 버그가 이미 존재함 — 이 diff에 포함되지 않은 기존 파일(pre-existing)이며, `coach.py`의 신규 크리티컬 버그와 원인이 동일함; coach.py 수정 시 함께 고치는 것을 권장
- W2: Stuck pending/processing 복구 경로 부재 (타임아웃/reaper job) — P1(OpenAIProvider 무인자 호출) 수정 후 발생빈도 낮아짐; 타임아웃/reaper job은 운영 인프라 결정 사항이라 별도 스토리로 분리 (사용자 결정, 2026-07-27)

## Deferred from: code review of 3-4-contextual-chat (2026-07-27)

- W1: 레이트 리밋 없음 (`api/routers/chat.py`) — v1 범위 외 운영 이슈; API Gateway 또는 미들웨어에서 처리 권장
- W2: 프롬프트 인젝션 위험 (`api/pipeline/llm/openai_provider.py`) — Responses API의 instructions/input 분리로 일부 완화; v2에서 더 강한 시스템 프롬프트 또는 입력 전처리 추가 검토
- W3: Flutter 에러 상태 미구분 (`mobile/lib/features/home/screens/contextual_chat_screen.dart`) — 401/503/네트워크 동일 처리; v1 AC-4 준수, v2에서 상태별 사용자 안내 개선 예정
- W4: String.fromEnvironment HTTP 기본값 (`mobile/lib/features/home/screens/contextual_chat_screen.dart`) — 프로덕션 빌드 시 `--dart-define=FASTAPI_URL=...` 필수; 배포 파이프라인 설정 확인 필요
- W5: signal_id UUID 형식 미검증 (`api/routers/chat.py`) — Supabase 파라미터화 쿼리로 SQL injection 보호; 추후 UUID 형식 검증 추가 권장
- W6: 미인증 요청 테스트 없음 (`api/tests/test_chat.py`) — auth 미들웨어 별도 테스트 범위; 통합 테스트 확장 시 추가
- W7: isLoading 경쟁 조건 (`web/src/app/(app)/home/review/[signalId]/chat/page.tsx`) — 인간 인터랙션에서 발생 확률 극히 낮음; v2 동시성 강화 시 useRef 플래그 패턴 적용

## Deferred from: code review of 3-3-contextstickybar-and-decision (2026-07-27, Round 2)

- W1: `get_supabase()` 연결 오류 핸들링 없음 (`api/routers/decisions.py:43`) — 기존 패턴; 관찰성 개선 패스에서 처리
- W2: `seenSet` 클로저 로컬 변수 — dep 변경 시 seenSections 히스토리 초기화 footgun (`context-sticky-bar.tsx:69`); 현재 빈 deps로 실제 영향 없음
- W3: 동시 INSERT race path 테스트 커버리지 없음 (`test_decisions.py`) — except 분기 테스트 추가 필요; 테스트 커버리지 개선 패스에서 처리
- W4: `review_id` 포맷 검증 없음 (`decisions.py:14`) — Supabase 파라미터화 쿼리로 실질적 SQL injection 위험 없음; UUID 타입 검증 추가 고려
- W5: `triggerAPI` 인증 실패 시 generic "failed" 상태 (`review-page-content.tsx:96-110`) — UX 개선 항목; 세션 만료 감지 후 로그인 안내 필요
- W6: `test_queue_without_timing` DB 호출 없이 통과 (`test_decisions.py:113-127`) — 검증 로직 순서 변경 취약성; 테스트 인프라 개선 패스에서 처리

## Deferred from: code review of 3-3-contextstickybar-and-decision (2026-07-25)

- W1: Supabase INSERT 실패 시 로깅 없음 (`api/routers/decisions.py:81-85`) — 500 응답은 올바르나 실제 Supabase 에러 내용 미기록; 관찰성 개선 항목으로 추후 로깅 패스에서 처리
- W2: barGateOverride 빈 deps useEffect — prop이 마운트 후 변경될 경우 observer 재실행 안 됨 (`web/src/components/home/review/context-sticky-bar.tsx:42`); 실제 세션 중 barGateOverride가 변경되지 않으므로 영향 미미
- W3: FASTAPI_URL dart-define 미설정 시 localhost 기본값 (`mobile/.../research_review_screen.dart`) — 배포 설정 문제로 코드 변경 불필요; 배포 파이프라인에서 --dart-define=FASTAPI_URL=... 확인 필요
- W4: migration 파일 diff에 미포함 — decisions 테이블 및 reviews.bar_gate_override 컬럼 DDL이 diff에 없음; 별도 migration 파일로 존재할 가능성 있으나 배포 전 존재 여부 확인 필요

## Deferred from: code review of 3-2-on-demand-research-review-생성 (2026-07-25)

- race condition: 동시 POST 요청이 멱등성 체크 통과 후 중복 INSERT 가능 (`api/routers/reviews.py`) — DB unique constraint on (signal_id, project_id, status IN pending/processing) 또는 INSERT ... ON CONFLICT 필요; 스키마 변경 범위
- SSR race: SSR 시 processing 조회 후 Realtime completed 이벤트 누락 가능 (`web/.../review/[signalId]/page.tsx + review-page-content.tsx`) — subscribe 직후 DB 상태 재확인 패턴으로 해결 가능; 아키텍처 수준 개선 사항
- processing 상태 타임아웃 메커니즘 없음 (`api/pipeline/reviewer.py`) — LLM hang 시 클라이언트 무한 generating 표시; 인프라 수준 watchdog 또는 processing_started_at 기반 TTL job 필요
- Realtime fast path에서 barGateOverride 하드코딩 null (`web/src/components/home/review/review-page-content.tsx:65`) — Story 3.3 bar_gate_override 처리 구현 시 함께 수정 예정
- user가 ai_research project 여러 개일 때 첫 번째 silently pick (`api/routers/reviews.py`) — MVP 단일 플레이북 가정 유효; 다중 플레이북 지원 스토리에서 처리
- 테스트 취약성: reviews table 호출 순서 의존 call-count side-effect (`api/tests/test_reviews_trigger.py`) — 기능 정확성 무관; 테스트 인프라 개선 패스에서 named fixture 패턴으로 교체

## Deferred from: code review of 3-1-research-review-상세-화면 (2026-07-25)

- Flutter 참고 출처 GestureDetector onTap 빈 핸들러 (`research_review_screen.dart:258`) — url_launcher 미설치로 인한 의도적 제한, 설치 후 처리
- 테스트 파일이 실행 불가 스펙 문서 역할 (`research-review-content.test.tsx`) — Jest 미설치 프로젝트 패턴, 테스트 인프라 구성 시 처리
- renderSectionContent: 복잡한 타입 String() fallback — 현재 SECTION_CONFIG 키 모두 string 타입; 미래 키 추가 시 타입 가드 추가
- SECTION_CONFIG as const vs renderSectionContent string 파라미터 타입 불일치 — 런타임 영향 없음, 타입 정밀도 개선 차원
- estimated_hours 크로스플랫폼 표시 불일치 (Flutter toStringAsFixed(0) vs Web 원본) — 1.5h 케이스 차이; 플랫폼 간 동작 통일 검토
- signalId URL 파라미터 유효성 검사 없음 (`page.tsx`) — RLS 보호로 실질적 위험 없음; invalid ID는 pending state로 표시
- signals join 배열 반환 가능성 (`page.tsx:25`) — many-to-one FK 관계상 단일 객체 반환이 Supabase 표준; 스키마 변경 시 재검토
- signalTitle 빈 문자열 시 h1 공백 렌더링 — LLM 파이프라인이 title 보장, 방어적 fallback 원하면 "(제목 없음)" 추가
- Flutter ContextStickyBar `Positioned(bottom: 64)` safe-area 처리 (`research_review_screen.dart:170`) — 코드로 확인 어려움, 실기기(iPhone) QA 시 sticky bar 위치 시각적 확인 필요; ShellScaffold safe-area 처리 여부에 따라 수정 결정

## Deferred from: code review of 2-5-on-demand-daily-brief-trigger (2026-07-25)

- POST /trigger 엔드포인트 속도 제한 없음 (`api/routers/daily_briefs.py`) — 동시 요청이 여러 background task를 큐에 넣을 수 있음; 인프라 레벨(API Gateway/미들웨어)에서 처리 권장
- Background task 실패 시 클라이언트에 무음 실패 (`api/pipeline/orchestrator.py`) — AD-5 설계 방침; Supabase Realtime으로 완료 감지, `mark_stuck_jobs`로 실패 복구
- `pipeline_log`이 except 블록에서 자체 예외 발생 가능 (`api/pipeline/orchestrator.py:147-156`) — 로깅 인프라 장애는 극히 드뭄; 필요 시 중첩 try/except 추가
- `_make_mock_client()` 헬퍼가 항상 side_effect로 덮어씌워져 실질적 데드코드 (`api/tests/test_daily_briefs_trigger.py:56-64`) — 테스트 품질 이슈, 기능 정확도 영향 없음

## Deferred from: code review of 1-1-project-scaffolding-and-database-foundation (2026-07-23)

- service_role 싱글톤이 모든 작업에서 RLS 우회 (`api/core/supabase.py`) — 의도적 아키텍처; Story 1.2 JWT 미들웨어로 사용자별 범위 처리 예정
- Flutter Supabase.initialize() 누락 (`mobile/lib/main.dart`) — Story 1.1에서 실제 Supabase 호출 없음; Story 1.2 인증 구현 시 추가 예정
- Next.js 서버사이드 Supabase 클라이언트 없음 (`web/src/lib/supabase.ts`) — RSC 데이터 패칭 도입 스토리에서 추가 예정
- Supabase 싱글톤 동시 초기화 레이스 컨디션 (`api/core/supabase.py`) — Python GIL로 실질적 위험 낮음; 다중 워커 환경 전환 시 재검토
- SystemUiOverlayStyle.dark 하드코딩 (`mobile/lib/main.dart`) — 다크 모드 디자인 결정 후 처리
- 다크 모드 전체 미지원 (`web/src/app/globals.css`, `mobile/lib/core/theme/app_theme.dart`) — 아키텍처 수준 결정 사안; 별도 스토리에서 처리
- TestClient 모듈 레벨로 lifespan 공유 (`api/tests/test_health.py`) — 현재 3개 테스트에서 영향 없음
- Supabase 인증 토큰 교체 후 싱글톤 갱신 불가 (`api/core/supabase.py`) — service_role은 미교체 방식

## Deferred from: code review of 1-2-user-authentication (2026-07-23)

- FASTAPI_BASE_URL 컴파일 타임 결정 (`mobile/lib/features/auth/providers/fcm_provider.dart`) — String.fromEnvironment는 빌드 타임 해석; 운영 빌드에서 --dart-define 필수
- GoRouter 동기 session 읽기 cold start 깜빡임 (`mobile/lib/core/router/app_router.dart`) — Story 1.3/1.4 StatefulShellRoute 교체 시 해결 예정
- cors_origins 기본값 localhost:3000 (`api/core/config.py`) — 운영 배포 시 CORS_ORIGINS env var 명시적 설정 필수
- /devices/register 속도 제한 없음 (`api/routers/devices.py`) — 인증된 사용자의 대량 FCM 토큰 등록 남용 가능; 미래 작업
- Flutter platform enum 'web' 없음 (`mobile/lib/features/auth/providers/fcm_provider.dart`) — 웹 FCM 지원 범위 확정 후 추가
- WWW-Authenticate 헤더 없음 (`api/middleware/auth.py`) — RFC 6750 Bearer 스킴 준수; 현재 클라이언트에 영향 없음

## Deferred from: code review of 1-2-user-authentication Round 2 (2026-07-24)

- GoRouter 동기 currentSession, authState 스트림 미연동 (`mobile/lib/core/router/app_router.dart`) — Story 1.3/1.4 StatefulShellRoute 교체 시 해결 예정
- FCM onTokenRefresh 만료 토큰으로 등록 시도 (`mobile/lib/main.dart`) — best-effort 설계, 실패 시 다음 로그인 시 재시도; 세션 유효성 체크 또는 retry 로직 고려
- /devices/register 속도 제한 없음 (`api/routers/devices.py`) — 이미 Round 1에서 Defer됨, 미래 작업
- pytest-asyncio asyncio_mode 미설정 (`api/requirements.txt`) — 현재 async 테스트 없음; async 테스트 추가 시 설정 필요
- middleware.ts 온보딩 완료 여부 미검증 (`web/src/middleware.ts`) — 스펙 설계상 클라이언트사이드 체크만 요구; 서버사이드 온보딩 강제 필요 시 별도 작업
- 회원가입 후 이메일 확인 시 FCM 등록 누락 — 이메일 확인 정책(Decision D2) 확정 후 처리; 비활성화 정책 유지 시 해당 없음

## Deferred from: code review of 1-4-flutter-navigation-shell (2026-07-24)

- 신규 가입 사용자 `/onboarding` 미도달 (`mobile/lib/core/router/app_router.dart`) — sign-up 후 session!=null → `/home` redirect 처리; Story 1.5 온보딩 플로우에서 onboarding-seen 플래그 기반 redirect 추가 예정
- 인증된 사용자의 404 경로에 `errorBuilder` 없음 (`mobile/lib/core/router/app_router.dart`) — GoRouter 기본 에러 화면 노출; 향후 NotFoundScreen 추가 예정
- `ShellScaffold`에 `resizeToAvoidBottomInset: false` 미설정 (`mobile/lib/features/shell/shell_scaffold.dart`) — 향후 키보드 입력 화면 구현 시 동작 검토 필요
- 인증 redirect 테스트 커버리지 없음 (`mobile/test/navigation_shell_test.dart`) — Supabase mock 복잡성으로 현재 스토리 범위 초과; 전용 라우터 테스트 스토리에서 처리

## Deferred from: code review of 1-5-onboarding-wizard (2026-07-24)

- Nullable 필드 JSON null 전송 (`onboarding_screen.dart:_callOnboardingCompleteApi`) — UI _isCTAEnabled로 가드되어 실제 도달 불가. 직접 메서드 호출 시 서버 422 반환.
- 만료 세션 토큰 레이스 (`onboarding_screen.dart:_callOnboardingCompleteApi`) — Supabase SDK 자동 갱신 및 에러 snackbar로 재시도 가능.
- _ThreeDotLoadingIndicator Future.delayed 타이머 누수 (`onboarding_screen.dart`) — `mounted` 가드로 크래시 방지. minor.
- tech_stack/interests 리스트 크기 무제한 (`api/routers/onboarding.py`) — 인증 엔드포인트라 위험도 낮음. API 보안 레이어에서 처리 권장.
- _GoRouterAuthNotifier auth 스트림 에러 무시 (`app_router.dart`) — 기존 코드에서 이어진 패턴. 현 스토리 변경 아님.
- 위젯 렌더링 및 통합 테스트 부족 (`mobile/test/onboarding_test.dart`) — 현재 로직 단위테스트만 존재. 전용 테스트 스토리에서 추가 권장.
- _buildDailyTime 레이아웃 오버플로우 가능성 (`onboarding_screen.dart`) — 3개 옵션으로 현재 안전. 옵션 수 증가 시 ListView로 교체 필요.
- onboardingCompletedProvider 이중 소스 (`onboarding_provider.dart`, `main.dart`) — SharedPreferences와 Riverpod 상태 분리. _completeOnboarding에서 동기화하므로 현재 정상 동작.

## Deferred from: code review of 1-6-profile-screen (2026-07-24)

- W-1: FASTAPI_BASE_URL 기본값 localhost:8000 (`profile_provider.dart:55-58`) — 기존 프로바이더(fcm_provider.dart)와 동일 패턴; 운영 빌드 dart-define으로 해결, 스토리 범위 외
- W-2: get_profile .limit(1) 미적용 (`api/routers/users.py:17`) — DB PK 제약으로 실제 중복 불가; 방어적 개선 사항
- W-3: get_supabase() 싱글톤 미보장 (`api/routers/users.py:15,42`) — core/supabase.py 기존 패턴; 아키텍처 레벨 개선 사항
- W-4: AsyncLoading 상태에서 requireValue 호출 위험 (`profile_provider.dart:75`) — _isSaveEnabled UI 가드로 실제 도달 불가; 방어적 코드 개선
- W-5: 변경 없이 저장 버튼 활성화 (`profile_screen.dart:25-29`) — 전체 null 프로필의 UX 엣지케이스; 불필요한 PATCH 발생 가능하나 기능 정확성 무관

## Deferred from: code review of 2-2-signal-builder-and-reviewer-agent (2026-07-24)

- `processing` 상태 전이 반환값 미검증 (`reviewer.py:70-74`) — Supabase 업데이트 결과 미확인; 외부 except로 커버되나 silent failure 가능
- Signal 오류 시 `raw` 상태 영구 잔류 (`signal_builder.py`) — `signals` 테이블에 `failed` 상태 없음; 스키마 변경 필요하여 스코프 외
- context_snapshot + result 비원자적 쓰기 (`reviewer.py:104-106, 136-140`) — 크래시 시 `processing` 상태 고착; 트랜잭션 지원 필요, 아키텍처 수준 개선
- INSERT 실패 시 로그 `review_id=None` (`reviewer.py:154-157`) — AD-12 경계 케이스; review_id 없을 때 로그 필드 None
- `projects` 쿼리 LIMIT 없음 (`reviewer.py:168-174`) — MVP 스케일에서 무해; 사용자 증가 시 페이지네이션 추가 예정
- `review_all_for_signal` 동시 호출 시 중복 review 생성 (`reviewer.py:161-180`) — 멱등성 없음; MVP 단일 파이프라인에서 발생 불가
- 잘못된 `signal_id`로 프로젝트별 `failed` review 생성 (`reviewer.py:161-180`) — 호출자(Story 2.3) 검증 책임
- `LLMProvider.generate()` 동기 메서드 (`llm/base.py:41`) — async 이벤트 루프 차단 가능; Story 2.3 APScheduler 설계 시 async 여부 검토 필요

## Deferred from: code review of 2-1-signal-pipeline-foundation (2026-07-24)

- `RawArticle` 런타임 유효성 검사 없음 (빈 문자열, URL 형식) — Story 2.2에서 실제 Collector 도입 시 처리
- 빈 `articles` 리스트 경고 로그 없음 (`normalizer.py`) — 배치 컨텍스트에서 치명적 아님
- `BaseCollector` 예외 계약 미정의 — Story 2.2 실제 Collector 구현 시 처리
- `pipeline_log` `brief_date` 파라미터 문자열 형식 미검증 (`logger.py`) — 현재 내부 호출에만 사용
- 동일 URL 중복 RawArticle → `signal_sources` 중복 삽입 가능 (`normalizer.py`) — Collector가 중복 URL 방지 책임
- `signal_date` 미래 날짜 미검증 — 배치 스케줄러가 올바른 날짜 보장
- AC-1 스키마 검증 자동화 테스트 없음 — Story 1.1에서 이미 검증됨

## Deferred from: code review of 2-3-recommender-and-daily-brief-batch-pipeline (2026-07-24)

- `role` / `project_goal` 미사용 스코어링 (`recommender.py:10-32`) — role은 신호 텍스트 키워드 매칭 효과 낮음, project_goal은 자유입력 문장으로 서브스트링 정밀도 낮음; LLM 임베딩 기반 유사도 도입 시 함께 처리 예정
- StubCollector 프로덕션 오케스트레이터에 하드코딩 (`orchestrator.py:7`) — 실제 Collector 도입 시 환경 플래그 또는 DI 패턴으로 교체 예정
- `scheduler.shutdown(wait=False)` — 파이프라인 실행 중 앱 종료 시 brief가 'pending' 상태로 잔류 가능; AC-6 mark_stuck_jobs 구현 후 함께 처리
- 만료된 FCM 토큰 `user_devices`에서 미삭제 — UNREGISTERED 에러 발생 시 해당 토큰 삭제 로직 추가 권장; 현재는 매일 재시도
- 관련성 점수 서브스트링 매칭 오탐 (`recommender.py:25-30`) — 단어 경계(word boundary) 미적용으로 짧은 기술명(예: "Go", "R")이 다른 단어 내부에서 매칭될 수 있음; MVP 범위로 수용
- APScheduler `max_instances=1` 명시적 미설정 (`main.py:55-61`) — APScheduler 3.x 기본값이 1이므로 실질적 위험 없음; 명시적 설정으로 의도 명확화 권장
- empty/None `fcm_token` 사전 가드 없음 (`fcm.py`) — FCM이 InvalidArgument 예외로 처리하여 로그 기록됨; 불필요한 API 호출 방지를 위한 사전 가드 권장

## Deferred from: code review of 1-3-web-navigation-shell (2026-07-24)

- `pb-16` 고정 패딩이 iOS safe-area 수정 후 동적 대응 필요 (`web/src/app/(app)/layout.tsx:17`) — P2 패치(safe-area-inset-bottom) 적용 후 `main`의 하단 패딩도 `env(safe-area-inset-bottom)` 고려 필요
- Placeholder 페이지에 개발 스토리 번호 노출 (`home/queue/history/profile/page.tsx`) — 실제 콘텐츠 구현 스토리에서 제거
- 4개 placeholder 페이지 페이지별 `metadata` 미설정 (`home/queue/history/profile/page.tsx`) — 실제 페이지 구현 시 각 스토리에서 추가 예정

## Deferred from: code review of 2-4-home-screen-daily-brief-display (2026-07-25)

- Web: `auth.getSession()` 대신 `auth.getUser()` 사용 권장 (`daily-brief-content.tsx:125`) — 보안 개선이나 FastAPI가 JWT 서명 검증하므로 즉각 위험 없음; 전체 코드베이스 일관성 패스에서 처리
- Web: 생성 중 상태 `<p>`에 `aria-live="polite"`/`role="status"` 추가 (`daily-brief-content.tsx:152`) — 접근성 개선 사항; 별도 접근성 패스에서 처리
- Flutter: `SeenSignalIds` `keepAlive` 필요성 재평가 (`daily_brief_provider.dart:108`) — `context.push()` 수정 후 AutoDispose 영향 재평가; StatefulShellBranch 동작 확인 후 필요 시 처리
- Web: `NEXT_PUBLIC_FASTAPI_URL` `.env.local.example`에 누락 — ops/docs 이슈; 배포 설정 정리 시 추가
- Web: `userId` 빈 문자열 가드 부재 (`page.tsx:14`) — 미들웨어/RLS가 인증 보장하므로 실질적 위험 낮음; 방어 코딩 패스에서 처리

## Deferred from: code review of 1-7-web-onboarding + 1-8-web-profile (2026-07-28)
- Web: 401(만료됐지만 존재하는 토큰)을 일반 에러와 미구분, 재로그인 미유도 — 앱 전반 패턴(onboarding/page.tsx, profile-content.tsx, outcome/page.tsx, context-sticky-bar). 세션 만료 UX 일괄 개선 시 처리.
- Web: `NEXT_PUBLIC_FASTAPI_URL` localhost 폴백 — 미설정 prod 빌드에서 client가 localhost 타깃. 코드베이스 전역 패턴, ops/env 정리 시 처리.
- Web: `handleLogout` try/catch·중복탭 가드 부재 (profile-content.tsx) — signOut() reject 시 push 미실행·피드백 없음. 저위험 minor.
- Web: 웹 전역 온보딩 완료 게이트 부재 (1-7) — 인증됨+onboarding_completed=false 사용자의 /home·/profile 직접 URL 접근 시 온보딩 스킵. 진입점 라우팅으로 정상 흐름 커버·미들웨어 DB조회 비용 회피 위해 수용. 전역 게이트는 향후 개선.

## Deferred from: code review of 5-3-push-notification-system (2026-07-28)
- `updated_at` 자동 갱신 트리거가 Queue 'today' 판정을 약화 (fcm.py:319-322) — 무관한 결정 갱신도 `_kst_date==run_date`를 다시 만족시켜 재알림/오알림 가능. 설계 결정 2/5.1에서 이미 알려진 스펙 한계로 수용. 전용 `queue_timing_set_at` 컬럼 도입 시 근본 해결.
- 소유권 조인 N+1 + 무제한 클라이언트측 스캔 (fcm.py:301-343, 452-490) — decision당 `_fetch_review/_fetch_project_user/_fetch_signal_title/_fetch_user_tokens` 순차 조회, `_PAGE_SIZE=1000` 후보 전량 페이징. 대규모 시 느림·misfire_grace_time(300s) 초과 위험. review/user 단위 캐싱 또는 임베드 조인으로 개선.
- 홈 하이라이트 미해제 (home_screen.dart:195-201) — 대상 signal_id가 today 리스트에 없거나 사용자가 카드 미탭 후 홈 이탈 시 하이라이트가 세션 넘어 잔존. 설계 결정 7이 자동 해제를 선택사항으로 defer. 리스트 부재 시 clear 또는 타임아웃 페이드 추가 시 해소.
- Job `run_date`가 `date.today()`(시스템 TZ) 사용 (orchestrator.py:213, 246) — 비UTC/비KST 호스트에서 KST 필터(`_kst_date`)와 어긋나 하루치 대상 누락 가능. 기존 `run_push_job` 패턴 답습, 실 발송 시각(10:00/20:00 KST)이 UTC 날짜 경계 미교차라 UTC 배포 하 무해. `datetime.now(KST).date()`로 명시화 시 견고.
- Queue 리마인더 일일 멱등성 마커 부재 (fcm.py:294) — outcome job의 `sent_at` 같은 '오늘 발송함' 마커 없음. 스케줄러 misfire 재시도/근접 재기동 시 동일 run_date에 중복 발송 가능.
- `outcome_reminder_sent_at` UPDATE가 성공 전송 후 예외 시 미기록 (fcm.py:485-490) — UPDATE가 외부 try에서 catch되어 sent_at 미기록 → 다음날 재발송('1회' 보장 깨짐, 희귀). 전송/기록 분리 또는 기록 실패 추적으로 개선.

## Deferred from: code review of 5-4-memory-기반-개인화-and-접근성-마감 (2026-07-28)
- user_id 격리 불변식(AC-A3) 실행 가능한 회귀 테스트 부재 (test_recommender_pipeline.py) — 코드(RPC `WHERE user_id`)는 정확하나 테스트는 파라미터 전달만 모킹 검증. 실 DB 왕복 테스트 인프라 미구성(스펙 Testing에서 인정). 실 Supabase 테스트 DB 도입 시 다중 사용자 row 배제 회귀 테스트 추가.
- 온디맨드 brief가 트리거마다 당일 Signal 전체 재임베딩 (orchestrator.py:156) — 단일 사용자·소규모지만 반복 트리거 시 임베딩 비용 누적. 당일 Signal 임베딩 캐시(예: signals 테이블 임베딩 컬럼 또는 단기 캐시) 도입 시 해소.
- `compute_relevance_score` 부분문자열 매칭 (recommender.py:27-42) — 예: tech_stack "go"가 "google"에 오매칭. 선행 스토리(2.3) 이슈가 이제 RAG base로 유입. 토큰 경계/단어 매칭으로 개선.
- 웹 생성중 라이브리전 조건부 마운트 (daily-brief-content.tsx:192-203) — AC-B6 문자적 충족이나 생성중일 때만 DOM 삽입. 라이브리전을 항상 렌더하고 텍스트만 토글하면 일부 SR/브라우저 조합에서 안내 신뢰성↑.
- Flutter `_buildGenerating` 라이브리전이 `signalsAsync.error/loading`에도 매핑 (home_screen.dart:110-111) — brief 완료 후 signal 재조회 로딩/에러 상태에서 TalkBack이 "생성 중"을 오안내 가능. 에러→전용 실패 위젯 매핑으로 개선.
- `.btn-primary` CSS 미정의 (review-failed-state.tsx:16) — 오류 화면 primary CTA가 무스타일. 재시도 CTA는 인라인 padding(≈44pt)로 기능 동작. 별도 디자인/스타일 티켓. (스토리 5.4 Completion Notes에 이미 기록됨)
- `--text-tertiary #9CA3AF` 대비 미달 토큰 사용 (globals.css:18, chat/page.tsx:200) — 채팅 타임스탬프 등 가시 텍스트에 4.5:1 미달 회색. 라벨 병행 방식 채택으로 기능 무손실이나 시각 대비는 미달. 토큰 상향 또는 tertiary 텍스트 용도 재검토.
- Memory RAG RPC 사용자×Signal 이중 루프 호출 (recommender.py:194-209) — `match_memories`가 per-signal·per-user로 호출되어 배치당 O(사용자수 × Signal수) HNSW 왕복. 값비싼 임베딩은 배치 1회 최적화됐으나 DB 왕복은 미최적화. 사용자 수 급증 또는 배치 소요가 스케줄러 윈도우에 근접할 때 재검토: 사용자당 memories 1회 로드 후 로컬 코사인 스코어링, 또는 다중벡터 배치 RPC. (2026-07-28 코드리뷰 Decision 2 → defer)

## Deferred from: 로컬 실행/검증 (웹+Flutter 기동 + 5.4 Memory RAG end-to-end 확인, 2026-07-28)

> Story 5.4 검증 위해 백엔드(FastAPI)+웹(Next.js)+앱(Flutter/Android 에뮬레이터)을 실제로 띄우고
> 파이프라인→Memory RAG 재랭킹까지 돌리는 과정에서 드러난 선행 버그들. 모두 5.4와 무관하며,
> 실API/실기기에서만 표면화됨(단위 테스트는 LLM/DB 모킹이라 미검출). 상태를 각 항목에 표기.

- **[FIXED, 워킹트리·미커밋] 백엔드 인증이 HS256만 검증 → Supabase 비대칭(ES256) 토큰 전부 401** (`api/middleware/auth.py`). 이 프로젝트는 최신 Supabase의 JWT 서명키(ES256, JWKS)로 사용자 토큰을 발급하는데 백엔드는 레거시 HS256 공유 secret만 검증 → 온보딩 완료 등 모든 인증 엔드포인트가 401. **프로덕션 영향 큼.** JWKS로 ES256/RS256 검증(+HS256 레거시 폴백)하도록 수정. auth 테스트 5건 통과. → 커밋 필요, 실배포 전 필수.
- **[FIXED, 워킹트리·미커밋] PyJWKClient SSL CERTIFICATE_VERIFY_FAILED** (`api/middleware/auth.py`). macOS python.org 배포판이 시스템 CA를 못 참조해 JWKS 조회 실패 → 위 검증이 401로 귀결. `certifi` CA 번들로 `ssl.create_default_context` 주입해 해결. (운영 환경에 따라 재현 여부 다름 — Linux 컨테이너는 보통 CA 정상이나, 방어적으로 명시 주입 유지 권장.)
- **[FIXED, 마이그레이션 적용됨] signals(technology_name, signal_date) UNIQUE 제약 부재.** normalizer가 `upsert(on_conflict="technology_name,signal_date")`로 하루 1기술 1시그널을 보장하는데 대응 UNIQUE 제약이 initial_schema/이후 마이그레이션 어디에도 없음 → upsert가 "ON CONFLICT 대상 제약 없음" 예외 → normalizer try/except가 삼켜 **파이프라인이 시그널을 0건 생성(무증상)**. 원격에 `uq_signals_technology_date` 적용 + 로컬 마이그레이션 `20260730000000_signals_unique_technology_date.sql` 추가.
- **[APPLIED, 원격 반영] 원격 DB 마이그레이션 드리프트 2건.** 로컬엔 있으나 원격 미적용: `20260724000001_daily_briefs_processing_started_at`(파이프라인 `mark_stuck_jobs`가 이 컬럼 참조 → 42703로 파이프라인 중단), `20260727000000_learning_paths_unique_active`. 둘 다 원격에 적용 완료. → CI/배포에 마이그레이션 자동 적용 파이프라인 필요(수동 apply 누락 방지).
- **[FIXED, 워킹트리·미커밋] OpenAI Responses API json_object 포맷이 input에 'json' 필요.** `openai_provider.py`의 4개 메서드(`generate`/`build_signal_title_summary`/`generate_learning_path`/`extract_memory`)가 `text={"format":{"type":"json_object"}}`를 쓰면서 프롬프트를 `instructions=`로만 전달 → input에 'json'이 없어 **400 BadRequest**(시그널 빌드/리뷰/러닝패스/메모리추출 전부 실패). 각 메서드의 `input`에 JSON 지시 문구 추가로 수정. 실API로 review(13섹션)·memory·signal 빌드 통과 확인. **테스트가 LLM을 모킹해서 이 API 계약 위반을 못 잡았음(프로세스 갭).**
- **[CONFIG] Flutter FASTAPI_BASE_URL 기본값이 http://localhost:8000.** Android 에뮬레이터에서 localhost는 에뮬레이터 자신 → 호스트 백엔드 미도달. `--dart-define=FASTAPI_BASE_URL=http://10.0.2.2:8000`로 실행해야 함. 에뮬레이터/실기기별 기본값 문서화 또는 빌드 프로파일 분리 권장. (참고: `web/.env.local.example`의 `FASTAPI_BASE_URL`도 코드가 실제로 읽는 `NEXT_PUBLIC_FASTAPI_URL`과 불일치 — 기존 defer 항목 web env와 동일 계열.)
- **[FIXED, 워킹트리·미커밋] Flutter 빌드 3건.** `app_settings` API 드리프트(`openNotificationSettings()`→`openAppSettings(type: AppSettingsType.notification)`, `profile_screen.dart`); `compileSdk` 33→36(`android/app/build.gradle.kts`); 플러그인 서브프로젝트 compileSdk 강제 override(`android/build.gradle.kts`, app_settings가 최신 AndroidX와 충돌). Gradle 9.1/AGP 9.0.1이 JDK 26 미지원이라 JDK 21로 빌드(`flutter config --jdk-dir`).
- **[PROCESS] normalizer의 광범위 try/except가 예외를 삼켜 무증상 실패 유발.** 위 UNIQUE 제약 부재가 `signal_upsert_failed`로 로깅만 되고 파이프라인은 성공(error:null, signals:0)으로 반환됨 → 진단 난이도↑. 치명 오류(제약 부재 등)는 표면화하거나 집계 리포트에 반영 권장.
- **[LIKELY LATENT] Reviewer/LearningPath/MemoryExtract도 위 json 버그로 실API에서 실패했을 것** — 이번 수정으로 함께 해소. 리뷰/러닝패스/메모리 생성이 실제로 성공하는지 실데이터 회귀 테스트(실 OpenAI 1회 왕복) 추가 권장.

## Deferred from: 리뷰 상세 + Contextual Chat 실기기 둘러보기 (2026-07-28)

> 앱에서 리뷰 상세/채팅을 실제로 열어보며 추가로 드러난 버그들. 모두 실동작에서만 표면화.

- **[FIXED, 워킹트리] Contextual Chat 엔드포인트 스키마 불일치(2건)** (`api/routers/chat.py`). ①`signals.select("id, project_id")` — signals엔 project_id 컬럼이 없음(시그널은 전역 공유). ②`client.table("users")` — 실제 테이블은 `user_profiles`. 둘 다 쿼리 예외 → 광범위 except가 **503 "Service temporarily unavailable"**로 감쌈(채팅 전면 불가). 소유권 검증을 "사용자 프로젝트에 속한 완료된 리뷰 존재"로 교체 + 테이블명 수정. 실API로 근거 기반 응답 정상 확인.
- **[FIXED, 워킹트리] 리뷰 상세의 'AI에게 질문하기' 링크가 ContextStickyBar에 가려짐** (`mobile/.../research_review_screen.dart`). 스크롤뷰 bottom 패딩 160 < 스티키바(Positioned bottom:64 + 바 높이 ~180) → 채팅 진입점이 영구 미노출/탭 불가. 패딩 288로 상향해 링크가 바 위로 노출되도록 수정.
- **[PROCESS] 리뷰가 json 버그로 'failed' 상태였음** — 파이프라인의 Reviewer가 openai json_object 버그(위 섹션)로 전부 실패해 리뷰 상세가 비어 있었음. json 수정 후 재생성하니 13섹션 리뷰 정상. 실API 회귀 테스트 부재가 근본 원인(모킹만 존재).
- **[OBSERVATION] 홈이 일시적 brief 조회 에러에서 자동 회복 안 함** — 온디맨드 삭제/재생성 순간 등에 provider가 error(_buildFailed)로 빠지면 재조회를 안 해 stale "생성하지 못했습니다" 표시. 앱 재시작으로만 복구됨. pull-to-refresh 또는 error 상태 자동 retry 권장.
- **[NOTE] 접근성 Semantics 라벨 실동작 확인** — uiautomator 트리에 5.4의 content-desc 라벨('AI가 확인하지 못한 정보', 섹션 헤더, '전송' 등)이 정상 노출됨(TalkBack 대응 근거). 긍정 확인.
