---
baseline_commit: NO_VCS
---

# Story 3.2: On-demand Research Review 생성

Status: done

## Story

사용자로서,
SignalCard를 탭했을 때 Review가 준비되지 않은 경우 생성을 기다리며 완료되면 자동으로 확인할 수 있기를 원한다,
그래서 파이프라인 사전 생성에 실패해도 Review를 볼 수 있다.

## Acceptance Criteria

**AC-1: pending/processing 진입 — 로딩 화면**
- **Given** 사용자가 SignalCard를 탭했을 때 해당 Review의 status가 `pending` 또는 `processing`이면
- **Then** 전체화면 로딩 상태가 표시된다: "Research Review를 생성하는 중입니다. 앱을 닫아도 됩니다."
- **And** "홈으로 돌아가기" CTA가 표시된다
- **And** Supabase Realtime으로 해당 `review_id` 완료를 구독한다

**AC-2: null/failed 진입 — on-demand 트리거**
- **Given** Review가 없거나 `failed` 상태일 때 사용자가 SignalCard를 탭하면
- **Then** `POST /api/v1/reviews/trigger` → 202 Accepted가 즉시 반환된다
- **And** FastAPI BackgroundTask로 ReviewContextBuilder 실행 → LLMProvider 호출 → DB 저장 순으로 처리된다
- **And** 상태 머신: `pending → processing → completed | failed`
- **And** 트리거 응답에 `review_id`가 포함되어 Realtime 구독에 사용된다

**AC-3: Realtime 완료 수신 → 자동 전환**
- **Given** Review 생성이 `completed`로 전환되면
- **When** Realtime 알림이 프론트에 도달하면
- **Then** 로딩 화면이 사라지고 13섹션 Research Review가 자동으로 표시된다 (수동 새로고침 불필요)

**AC-4: failed 상태 — 에러 화면**
- **Given** Review 생성이 `failed`로 전환되면
- **Then** 에러 메시지와 "다시 시도하기" CTA(primary)가 표시된다
- **And** "홈으로 돌아가기" CTA(secondary)가 표시된다
- **And** 소스 Signal 데이터는 보존된다

**AC-5: 로딩 애니메이션 및 Reduce Motion**
- **Then** 세 점 pulse 애니메이션이 표시된다
- **And** `prefers-reduced-motion` / Flutter `MediaQuery.disableAnimations` 시 정적 점으로 대체된다

## Tasks / Subtasks

### [API] reviews 라우터 신규 생성

- [x] Task 1: `api/routers/reviews.py` 신규 생성 — `POST /api/v1/reviews/trigger` (AC: #2)
  - [x] 1.1 `TriggerReviewRequest` Pydantic 모델: `signal_id: str`
  - [x] 1.2 `get_current_user` 의존성으로 `user_id` 추출
  - [x] 1.3 `user_id`로 `projects` 테이블에서 `playbook_type='ai_research'`인 `project_id` 조회 (없으면 404)
  - [x] 1.4 **멱등성**: `signal_id + project_id`로 이미 `pending` 또는 `processing` 상태 Review 존재 확인 → 있으면 기존 `review_id` 반환 (새 트리거 없이)
  - [x] 1.5 없거나 `failed`이면: `reviews` 테이블에 `status='pending'` 레코드 동기 INSERT → `review_id` 획득
  - [x] 1.6 `background_tasks.add_task(run_review_from_pending, review_id, signal_id, project_id)`
  - [x] 1.7 `return APIResponse(data={"review_id": review_id, "status": "pending"})` (HTTP 202)

- [x] Task 2: `api/pipeline/reviewer.py` 수정 — 기존 pending 레코드 재개 함수 추가 (AC: #2)
  - [x] 2.1 신규 함수 `run_review_from_pending(review_id: str, signal_id: str, project_id: str)` 추가
  - [x] 2.2 step 1(insert) 생략, step 2(processing 전이)부터 시작 — 기존 `review_signal()` 로직 재사용
  - [x] 2.3 `get_supabase()` 및 `OpenAIProvider()` 를 함수 내부에서 생성 (BackgroundTask는 DI 불가)
  - [x] 2.4 기존 `review_signal()` 함수는 **변경하지 않는다** (일괄 배치 파이프라인이 사용 중)

- [x] Task 3: `api/main.py` 수정 — reviews 라우터 등록 (AC: #2)
  - [x] 3.1 `from routers.reviews import router as reviews_router` import 추가
  - [x] 3.2 `app.include_router(reviews_router, prefix="/api/v1")` 추가

### [WEB] Next.js on-demand 생성 + Realtime 구독

- [x] Task 4: `web/src/app/(app)/home/review/[signalId]/page.tsx` 수정 — Server Component 쿼리 변경 (AC: #1, #2)
  - [x] 4.1 Supabase 쿼리에서 `.eq("status", "completed")` 조건 **제거** — 모든 status 조회
  - [x] 4.2 select 필드에 `id, status` 추가: `.select("id, status, result, bar_gate_override, signals(title)")`
  - [x] 4.3 기존 `ResearchReviewContent` 직접 렌더링 대신 `ReviewPageContent` 클라이언트 컴포넌트에 `initialReview` prop으로 전달
  - [x] 4.4 `initialReview` 타입: `{ id: string; status: string; signalTitle: string; payload?: ReviewPayload; barGateOverride?: string | null } | null`

- [x] Task 5: `web/src/components/home/review/review-page-content.tsx` 신규 생성 — 상태 머신 Client Component (AC: #1, #2, #3, #4)
  - [x] 5.1 `"use client"` 선언
  - [x] 5.2 Props: `signalId: string`, `initialReview: InitialReview | null` (Task 4 타입)
  - [x] 5.3 UI 상태 정의:
    ```
    type ReviewUIState =
      | { type: "completed"; payload: ReviewPayload; signalTitle: string; barGateOverride?: string | null }
      | { type: "generating" }
      | { type: "failed" }
    ```
  - [x] 5.4 `useEffect` 초기화:
    - `initialReview?.status === "completed"` → 즉시 `completed` 상태 설정 (Realtime 구독 없음)
    - `initialReview?.status === "pending" | "processing"` → `generating` 상태 + `reviewId = initialReview.id` → Realtime 구독 시작
    - `initialReview === null || initialReview?.status === "failed"` → trigger API 호출 → 응답에서 `reviewId` 획득 → `generating` 상태 + Realtime 구독 시작
  - [x] 5.5 trigger API 호출 패�� 구현
  - [x] 5.6 Realtime 구독 패턴 ��현 (채널 cleanup 포함)
  - [x] 5.7 `completed` 수신 시: `row.result?.payload`를 `ReviewPayload`로 캐스팅, REPLICA IDENTITY 미설정 시 별도 조회 fallback
  - [x] 5.8 `uiState.type === "completed"` → `<ResearchReviewContent>` 렌더링
  - [x] 5.9 `uiState.type === "generating"` → `<ReviewGeneratingState>` 렌더링
  - [x] 5.10 `uiState.type === "failed"` → `<ReviewFailedState onRetry={handleRetry}>` 렌더링

- [x] Task 6: `web/src/components/home/review/review-generating-state.tsx` 신규 생성 (AC: #1, #5)
  - [x] 6.1 "Research Review를 생성하는 중입니다. 앱을 닫아도 됩니다." 텍스트 + `<ThreeDotLoading />`
  - [x] 6.2 "홈으로 돌아가기" `<Link href="/home">` CTA
  - [x] 6.3 `ThreeDotLoading`이 `prefers-reduced-motion` 처리함 확인 — globals.css에 `.dot-pulse { animation: none; }` 미디어 쿼리 존재

- [x] Task 7: `web/src/components/home/review/review-failed-state.tsx` 신규 생성 (AC: #4)
  - [x] 7.1 Props: `onRetry: () => void`
  - [x] 7.2 "Research Review를 생성하지 못했습니다." 텍스트
  - [x] 7.3 "다시 시도하기" button (primary) → `onRetry` 호출
  - [x] 7.4 "홈으로 돌아가기" `<Link href="/home">` (secondary)

### [FLUTTER] Flutter on-demand 생성 + Realtime 구독

- [x] Task 8: `mobile/lib/features/home/providers/research_review_provider.dart` 전면 교체 (AC: #1, #2, #3, #4)
  - [x] 8.1 새 상태 sealed class 정의: `ReviewGenerating`, `ReviewCompleted(review)`, `ReviewFailed`
  - [x] 8.2 기존 `LearningTimeDifficulty`, `HonestBoxData`, `ReviewPayload`, `ResearchReview` 데이터 클래스 보존
  - [x] 8.3 `@riverpod Stream<ReviewState> reviewState(...)` 로 교체 (async* generator, status별 분기)
  - [x] 8.4 trigger API 호출 패턴 구현 (`http` 패키지 사용)
  - [x] 8.5 Realtime 구독 패턴 구현 (`PostgresChangeFilterType.eq`, StreamController 활용)
  - [x] 8.6 `http` 패키지 확인: `pubspec.yaml`에 `http: ^1.2.0` 이미 존재
  - [x] 8.7 `build_runner` 재실행 완료 — `research_review_provider.g.dart` 생성됨

- [x] Task 9: `mobile/lib/features/home/screens/research_review_screen.dart` 수정 (AC: #1, #2, #3, #4, #5)
  - [x] 9.1 `ref.watch(reviewStateProvider(signalId))`로 변경
  - [x] 9.2 `AsyncValue<ReviewState>` switch 패턴 핸들링 (loading/error/data)
  - [x] 9.3 `_PendingBody` → `_GeneratingBody` 교체: 카피 "앱을 닫아도 됩니다.", `_DotPulse` 위젯, `MediaQuery.disableAnimationsOf` 분기
  - [x] 9.4 `_FailedBody` 신규 위젯: "다시 시도하기" ElevatedButton + "홈으로 돌아가기" TextButton

### Review Findings

- [x] [Review][Patch] handleRetry Realtime 채널 누수 — retry 시 triggerAndSubscribe()가 반환하는 cleanup 클로저를 React가 호출하지 않음; 채널이 닫히지 않아 메모리 누수 + 중복 이벤트 발생 [web/src/components/home/review/review-page-content.tsx:150-165]
- [x] [Review][Patch] Realtime fallback 경로에서 payload 없으면 generating 상태 영구 고착 — result.payload가 null이고 fallback DB fetch도 null 반환 시 setUIState 호출 없음; failed로 전환해야 함 [web/src/components/home/review/review-page-content.tsx:73-81]
- [x] [Review][Patch] `_fetchCompletedReview`가 reviewId 아닌 signalId로 조회 — 동일 signal에 completed review가 여러 개일 때 잘못된 review payload가 표시될 수 있음 [mobile/lib/features/home/providers/research_review_provider.dart:244-256]
- [x] [Review][Patch] Flutter: completed parse 실패 시 새 파이프라인 트리거 — _parseReview null 반환 시 return 없이 fall-through하여 trigger API 재호출; ReviewFailed yield 후 return 해야 함 [mobile/lib/features/home/providers/research_review_provider.dart:156-162]
- [x] [Review][Patch] Flutter: StreamController 미종료 누수 — pending/processing 및 null/failed 분기 모두 controller.close() 없음; 반복 네비게이션 시 누적 [mobile/lib/features/home/providers/research_review_provider.dart:168,182]
- [x] [Review][Patch] signal_id 소유권 검증 없음 — trigger_review가 user의 project_id는 확인하나 signal_id가 해당 project에 속하는지 미검증; 인증된 사용자가 임의의 signal_id로 pipeline 트리거 가능 [api/routers/reviews.py:trigger_review]
- [x] [Review][Patch] run_review_from_pending이 review_signal 로직을 전체 복제 — step 2-7 중복; 공통 헬퍼 추출로 단일 변경점 유지 필요 [api/pipeline/reviewer.py:165-288]
- [x] [Review][Defer] race condition: 동시 POST 요청이 멱등성 체크 통과 후 중복 INSERT 가능 [api/routers/reviews.py] — deferred, DB unique constraint 필요 (스키마 변경 범위)
- [x] [Review][Defer] SSR race: SSR 시 processing 상태 조회 후 completed 전환 시 Realtime 이벤트 누락 가능 [web/src/app/(app)/home/review/[signalId]/page.tsx] — deferred, 아키텍처 수준 개선 사항
- [x] [Review][Defer] processing 상태 타임아웃 메커니즘 없음 — LLM hang 시 무한 generating 표시 [api/pipeline/reviewer.py] — deferred, 인프라 수준 watchdog/TTL 필요
- [x] [Review][Defer] Realtime fast path에서 barGateOverride 하드코딩 null [web/src/components/home/review/review-page-content.tsx:65] — deferred, Story 3.3에서 bar_gate_override 처리 예정
- [x] [Review][Defer] user가 ai_research project 여러 개일 때 첫 번째 silently pick [api/routers/reviews.py] — deferred, MVP 단일 플레이북 가정 유효; 다중 플레이북 지원 시 처리
- [x] [Review][Defer] 테스트 취약성: reviews table 호출 순서 의존 call-count side-effect [api/tests/test_reviews_trigger.py] — deferred, 기능 정확성 무관; 테스트 인프라 개선 시 처리

## Dev Notes

### 핵심 아키텍처 제약

| 규칙 | 상세 |
|------|------|
| **AD-3** 데이터 접근 소유권 | reviews INSERT/UPDATE: FastAPI(service_role)만. 읽기: Supabase SDK 직접 |
| **AD-5** 비동기 AI 작업 | trigger→202→BackgroundTask→상태머신. `failed` 시 자동재시도 없음, 사용자 재트리거 |
| **AD-13** API 계약 | `Authorization: Bearer {JWT}`, `/api/v1/`, 응답 봉투 `{data, error}` |
| **AD-14** Flutter 상태관리 | 비동기 Review 상태는 `StreamProvider`로 Supabase Realtime 구독 |

### API 라우터 신규 생성 — 주의사항

`api/routers/reviews.py` 는 새 파일이다. `main.py`에 반드시 등록해야 한다. 기존 라우터 등록 패턴:

```python
# api/main.py 상단 import 블록
from routers.reviews import router as reviews_router
# ...
app.include_router(reviews_router, prefix="/api/v1")
```

`get_supabase()` 는 `core.supabase` 모듈에서 import, `OpenAIProvider`는 `pipeline.llm.openai_provider`에서 import.

### `run_review_from_pending` 구현 참고

기존 `review_signal()` 함수(`api/pipeline/reviewer.py`)는 내부에서 pending INSERT를 포함한다. 새 `run_review_from_pending(review_id, signal_id, project_id)` 함수는 **step 2(processing 전이)부터** 시작해야 한다. 기존 `review_signal()`의 step 2~end 로직을 `review_id`를 파라미터로 받도록 추출하거나 복사한다. 기존 함수는 절대 변경하지 않는다 — 배치 파이프라인 `review_all_for_signal()`이 직접 호출한다.

### Web: page.tsx → 수정 범위

현재 `page.tsx`(Server Component)의 핵심 변경:
```typescript
// 변경 전: status='completed' 필터
.eq("status", "completed")

// 변경 후: status 무관 전체 조회, id 필드 추가
.select("id, status, result, bar_gate_override, signals(title)")
// .eq("status", "completed") 줄 삭제
```

Server Component는 SSR로 초기 review row를 가져오고, Client Component (`ReviewPageContent`)에게 `initialReview` prop으로 전달. Realtime 구독은 Client Component에서만 한다.

`signalTitle` 추출 로직은 기존 `as Record<string, unknown>` 타입가드 패턴 그대로 유지.

### Web: completed 수신 후 signalTitle 문제

Realtime `UPDATE` payload에는 `signals(title)` join 데이터가 포함되지 않는다(Postgres CDC는 raw 컬럼만 전송). 따라서 `completed` 상태 수신 시 아래 두 가지 전략 중 하나:
1. **권장**: `page.tsx` Server Component에서 초기 fetch 시 `signalTitle`을 별도로 추출해 `ReviewPageContent`에 prop으로 전달. Realtime 완료 수신 시 이미 가진 `signalTitle` 재사용.
2. 또는: 완료 수신 시 `supabase.from("signals").select("title").eq("id", signalId).single()` 별도 호출.

전략 1이 더 단순하다. `signalTitle`은 Signal 탭 시 이미 알 수 있는 정보이므로 Server Component에서 확보 가능.

### Web: ThreeDotLoading 기존 컴포넌트 재사용

`web/src/components/home/three-dot-loading.tsx` 이미 존재. `dot-pulse` 애니메이션 클래스는 `globals.css`에 정의되어 있다. import 경로:
```typescript
import { ThreeDotLoading } from "@/components/home/three-dot-loading";
```
`ThreeDotLoading`이 `prefers-reduced-motion`을 처리하는지 현재 코드에서 확인 필요. 미처리 시 `ReviewGeneratingState` 컴포넌트 wrapper에서 `@media (prefers-reduced-motion)` CSS로 `.dot-pulse` 애니메이션을 `animation: none`으로 재정의.

### Flutter: http 패키지 및 FASTAPI_URL

trigger API 호출에 `http` 패키지 필요. `pubspec.yaml`에 `http:` 있는지 확인. FASTAPI_URL은 `--dart-define=FASTAPI_URL=...` 또는 `flutter_dotenv`로 주입. 기존 프로젝트에서 사용 중인 env 패턴 확인 필요.

Flutter에서 `dio` 패키지를 이미 사용 중이면 `http` 대신 `dio`로 통일.

```bash
grep -r "import 'package:http\|import 'package:dio" mobile/lib/ | head -5
```

### Flutter: Realtime 구독 payload 주의

Supabase Realtime `postgres_changes` UPDATE payload의 `newRecord`에는 `result` JSONB 컬럼이 포함될 수 있지만, **REPLICA IDENTITY 설정에 따라 포함 안 될 수 있다** (아키텍처 spine Deferred 항목). `result` 없으면 별도 Supabase 쿼리로 조회:

```dart
Future<ResearchReview?> _fetchCompletedReview(String signalId) async {
  final response = await Supabase.instance.client
    .from('reviews')
    .select('id, result, bar_gate_override, signals(title)')
    .eq('signal_id', signalId)
    .eq('status', 'completed')
    .eq('playbook_type', 'ai_research')
    .maybeSingle();
  // ... 기존 파싱 로직
}
```

### Flutter: StreamProvider와 Riverpod 코드 생성

`@riverpod Stream<ReviewState> reviewState(...)` 형태로 선언하면 `riverpod_annotation`이 `reviewStateProvider` 를 생성한다. `build_runner`는 변경 후 반드시 재실행해야 한다.

`Stream`을 `async*` generator로 반환하는 `@riverpod` provider는 ref.onDispose 내에서 Realtime 채널을 해제해야 한다. `async*` 내부에서는 직접 `ref.onDispose` 호출이 제한될 수 있으므로, `StreamController`를 사용하거나 별도 `dispose` 핸들러 패턴 검토:

```dart
@riverpod
Stream<ReviewState> reviewState(ReviewStateRef ref, String signalId) async* {
  RealtimeChannel? channel;
  ref.onDispose(() => channel != null ? Supabase.instance.client.removeChannel(channel!) : null);
  
  // ... yield 로직
}
```

### 절대 금지사항

| 금지 | 이유 |
|------|------|
| `review_signal()` 함수 수정 | 배치 파이프라인이 직접 호출 중 — 수정 시 회귀 |
| FastAPI `/api/v1/reviews/trigger` 에서 reviews UPDATE/DELETE | 트리거 엔드포인트는 INSERT(pending)만 수행, 이후는 BackgroundTask |
| "잠시만 기다려 주세요" 카피 사용 | UX 스펙 명시적 금지 — 반드시 "앱을 닫아도 됩니다." 사용 |
| Realtime 채널 cleanup 없는 구독 | 메모리 누수 + 중복 이벤트 — 반드시 unmount 시 removeChannel |
| completed 수신 후 전체 페이지 새로고침(`router.refresh()`) | Realtime 완료 시 자동 전환 (수동 새로고침 불필요) |
| failed 상태에서 자동 재시도 | AD-5: 자동재시도 없음, 사용자가 "다시 시도하기" 명시적 선택 |

### 이 스토리의 범위 경계

| 항목 | 이 스토리 (3.2) | 이후 스토리 |
|------|----------------|------------|
| pending/processing → 로딩 화면 | ✅ | — |
| null/failed → trigger + 로딩 | ✅ | — |
| Realtime 완료 자동 전환 | ✅ | — |
| IntersectionObserver 섹션 tracking | ❌ | Story 3.3 |
| ContextStickyBar enable/disable 로직 | disabled 정적 상태 유지 | Story 3.3 |
| Learn Now / Queue / Ignore 결정 CTA | ❌ | Story 3.3 |
| bar_gate_override 처리 | ❌ | Story 3.3 |
| Contextual Chat 화면 | ❌ | Story 3.4 |

### 신규 / 수정 파일 목록

```
# API 신규 파일
api/routers/reviews.py                          (NEW)

# API 수정 파일
api/pipeline/reviewer.py                        (UPDATE — run_review_from_pending 추가)
api/main.py                                     (UPDATE — reviews_router 등록)

# 웹 수정 파일
web/src/app/(app)/home/review/[signalId]/page.tsx  (UPDATE — 쿼리 변경, ReviewPageContent로 위임)

# 웹 신규 파일
web/src/components/home/review/review-page-content.tsx    (NEW — 상태 머신 Client Component)
web/src/components/home/review/review-generating-state.tsx (NEW)
web/src/components/home/review/review-failed-state.tsx     (NEW)

# Flutter 수정 파일
mobile/lib/features/home/providers/research_review_provider.dart (UPDATE — StreamProvider 전환)
mobile/lib/features/home/providers/research_review_provider.g.dart (UPDATE — build_runner 재생성)
mobile/lib/features/home/screens/research_review_screen.dart      (UPDATE — 새 상태 처리)
```

### References

- 에픽: `_bmad-output/planning-artifacts/epics.md` — Story 3.2 (line 554–589)
- 아키텍처: `ARCHITECTURE-SPINE.md` — AD-3(데이터 접근), AD-5(비동기 AI 작업 시퀀스), AD-9(RLS), AD-13(API 계약), AD-14(Flutter StreamProvider)
- UX: `EXPERIENCE.md` — Research Review States table (line 397–402), 로딩 카피 금지 패턴 (line 122–123), Reduce Motion 규칙 (line 633–638), Flutter dot-pulse 스펙 (line 572–573)
- 기존 Realtime 패턴: `web/src/components/home/daily-brief-content.tsx` (line 118–144, 167–180)
- 기존 trigger API 패턴: `api/routers/daily_briefs.py`
- API 응답 스키마: `api/core/schemas.py` — `APIResponse`
- 인증 미들웨어: `api/middleware/auth.py` — `get_current_user` Depends
- DB 스키마: `supabase/migrations/20260723000000_initial_schema.sql` — reviews 테이블 (line 61–91)
- 기존 reviewer 파이프라인: `api/pipeline/reviewer.py` — `review_signal()`, `run_review_from_pending` 추가 위치
- ThreeDotLoading: `web/src/components/home/three-dot-loading.tsx`
- Flutter provider 패턴: `mobile/lib/features/home/providers/daily_brief_provider.dart` (StreamProvider 참고)
- 이전 스토리: `_bmad-output/implementation-artifacts/3-1-research-review-상세-화면.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `FilterType` → `PostgresChangeFilterType` 수정: supabase Flutter v2.x API 변경 사항
- `channel!` nullable 경고 수정: `final ch = channel; if (ch != null)` 패턴 사용
- TypeScript 타입 에러 수정: `(reviewRow?.signals as unknown) as Record<string, unknown> | null` 이중 캐스팅

### Completion Notes List

- **API**: `POST /api/v1/reviews/trigger` 엔드포인트 신규 생성. 멱등���(pending/processing 중복 방지), 202 응답, BackgroundTask 패턴 구현.
- **API**: `run_review_from_pending()` 함수 추가. 기존 `review_signal()`의 step 2~7 로직을 review_id 파라미터로 재사용. 기존 함수 미변경.
- **Web**: `page.tsx` Server Component가 status 무관 최신 review 조회 → `ReviewPageContent` Client Component에 `initialReview` prop 위임.
- **Web**: `ReviewPageContent` 상태 머신: completed(즉시 렌더)/pending+processing(Realtime 구독)/null+failed(trigger API → Realtime). 채널 cleanup 포함.
- **Web**: `ReviewGeneratingState` — `ThreeDotLoading` (globals.css prefers-reduced-motion 처리됨) + "앱을 닫아도 됩니다." 카피.
- **Web**: `ReviewFailedState` — "다시 시도하기"(primary) + "홈으로 돌아가기"(secondary).
- **Flutter**: `research_review_provider.dart` StreamProvider 전환. sealed ReviewState, async* generator, StreamController 기반 Realtime 구독.
- **Flutter**: `research_review_screen.dart` switch 패턴 핸들링. `_GeneratingBody`(`_DotPulse`, disableAnimations 분기), `_FailedBody`(onRetry) 신규 위젯.
- **Tests**: `tests/test_reviews_trigger.py` 6개 테스트 추가. 전체 85개 ���과. TypeScript 타입 체크 통과. Flutter analyze 통과.

### File List

- `api/routers/reviews.py` (NEW)
- `api/pipeline/reviewer.py` (UPDATE — run_review_from_pending 추가, import 추가)
- `api/main.py` (UPDATE — reviews_router 등록)
- `api/tests/test_reviews_trigger.py` (NEW)
- `web/src/app/(app)/home/review/[signalId]/page.tsx` (UPDATE — 쿼리 변경, ReviewPageContent 위임)
- `web/src/components/home/review/review-page-content.tsx` (NEW)
- `web/src/components/home/review/review-generating-state.tsx` (NEW)
- `web/src/components/home/review/review-failed-state.tsx` (NEW)
- `mobile/lib/features/home/providers/research_review_provider.dart` (UPDATE — StreamProvider 전환)
- `mobile/lib/features/home/providers/research_review_provider.g.dart` (UPDATE — build_runner 재생성)
- `mobile/lib/features/home/screens/research_review_screen.dart` (UPDATE — 새 상태 ��리)

## Change Log

- 2026-07-25: Story 3.2 구현 완료. API trigger 엔드포인트 + BackgroundTask 파이프라인, Web 상태 머신 Client Component + Realtime 구독, Flutter StreamProvider + sealed ReviewState 전환.
