---
baseline_commit: NO_VCS
---

# Story 3.3: ContextStickyBar & Decision

Status: done

## Story

사용자로서,
Research Review의 핵심 섹션을 읽은 후 ContextStickyBar가 활성화되어 Learn Now / Queue / Ignore 중 하나를 결정할 수 있기를 원한다,
그래서 충분한 근거를 바탕으로 학습 결정을 내릴 수 있다.

## Acceptance Criteria

**AC-1: 초기 disabled 상태**
- **Given** Research Review 상세 화면이 처음 로드될 때
- **Then** ContextStickyBar는 disabled 상태로 표시된다
- **And** Primary CTA 배경: `var(--text-disabled)` (#D1D1D1), 잠금 아이콘(SVG 14px) + "Learn Now" 텍스트
- **And** 힌트 텍스트(`id="ctx-hint"`): "추천 근거를 먼저 확인해 주세요 ↑" (11px/text-secondary)
- **And** Queue/Ignore 버튼은 hidden
- **And** 추천 텍스트는 withheld(표시 안 함)

**AC-2: 섹션 engagement 추적 → enabled 전환**
- **Given** 사용자가 섹션 1–6, 10, 11을 스크롤(또는 포커스)할 때
- **When** 각 섹션 heading이 viewport에 진입(threshold: 0.1)하거나 키보드/스크린리더 포커스를 받으면
- **Then** 해당 섹션이 "seen"으로 기록된다
- **And** 필수 섹션 세트(1–6, 10, 11) 완료 시 ContextStickyBar가 enabled 상태로 전환된다
- **And** `aria-live="polite"` 영역이 "Learn Now 버튼을 사용할 수 있습니다"를 발화한다
- **And** `prefers-reduced-motion` 시 전환 애니메이션 없이 즉시 전환된다

**AC-3: bar_gate_override 처리**
- **Given** `reviews.bar_gate_override` 값이 존재할 때
- **Then** 클라이언트 engagement 상태와 무관하게 해당 값에 따라 bar 상태를 결정한다
- **And** `bar_gate_override = "enabled"` 시 초기 로드부터 enabled 상태

**AC-4: enabled 상태 UI**
- **Given** ContextStickyBar가 enabled 상태일 때
- **Then** Primary CTA: "Learn Now" (accent-primary bg, accent-foreground text)
- **And** Secondary ghost pills: "Queue", "Ignore" (각 min-height 44px) 표시
- **And** 추천 텍스트(`payload.recommendation_reason` 기반)가 CTA 위에 공개된다
- **And** 모든 CTA는 `<button>` 요소 / Flutter에서는 탭 가능한 `GestureDetector` 또는 `TextButton`

**AC-5: Learn Now Decision**
- **Given** 사용자가 "Learn Now"를 탭하면
- **Then** `POST /api/v1/decisions` `{ review_id, choice: "learn_now" }` 요청이 전송된다
- **And** 성공 시 Learning Path 화면으로 이동한다 (`/home/review/:signalId/learning-path`)
- **And** Flutter: `HapticFeedback.mediumImpact()` 실행

**AC-6: Queue Decision**
- **Given** 사용자가 "Queue"를 탭하면
- **Then** Queue 타이밍 선택 Bottom Sheet(웹)/Modal Bottom Sheet(Flutter)가 열린다
- **And** 옵션: "Today", "This Week", "Later" (각 min-height 44px)
- **And** Bottom Sheet 제목: "언제 학습할까요?"
- **And** 한 개를 선택하면 시트가 닫히고 `POST /api/v1/decisions` `{ review_id, choice: "queue", queue_timing }` 요청이 전송된다
- **And** 비차단 토스트 "이번 주 학습 예정으로 저장됐습니다." / "오늘 학습 예정으로 저장됐습니다." / "나중에 학습 예정으로 저장됐습니다." 가 3초간 표시된다
- **And** Flutter: `HapticFeedback.mediumImpact()` 타이밍 선택 시 실행

**AC-7: Ignore Decision**
- **Given** 사용자가 "Ignore"를 탭하면
- **Then** `POST /api/v1/decisions` `{ review_id, choice: "ignore" }` 요청이 전송된다
- **And** 비차단 토스트 "이 Signal은 히스토리에서 다시 볼 수 있습니다." (3초)가 표시된다
- **And** 홈 화면으로 이동한다 (`/home`)

**AC-8: ARIA 완전 구현**
- **Given** ContextStickyBar의 ARIA를 확인하면
- **Then** disabled CTA: `aria-disabled="true"`, `aria-label="Learn Now — 비활성화됨. 리뷰 내용을 먼저 읽어 주세요"`, `aria-describedby="ctx-hint"`
- **And** enabled CTA: `aria-label="Learn Now"`
- **And** Queue CTA: `aria-label="Queue — 이 Signal을 큐에 저장"`, Ignore CTA: `aria-label="Ignore — 이 Signal을 무시"`
- **And** 힌트 텍스트의 ↑ 화살표: `<span aria-hidden="true">↑</span>` 처리

**AC-9: Queue Bottom Sheet 스펙 (Flutter)**
- **Given** Flutter에서 Queue Bottom Sheet
- **Then** `showModalBottomSheet`, `RoundedRectangleBorder(top: 24px)`, 수동 drag handle(36×4px/#DDD)
- **And** isDismissible: true, enableDrag: true

**AC-10: memo 선택 입력**
- **Given** Queue 타이밍 선택 Bottom Sheet
- **Then** 선택적 메모 입력 필드가 제공된다
- **And** `decisions.memo` TEXT 컬럼에 함께 저장된다 (FR-3.3)

## Tasks / Subtasks

### [API] decisions 라우터 신규 생성

- [x] Task 1: `api/routers/decisions.py` 신규 생성 — `POST /api/v1/decisions` (AC: #5, #6, #7)
  - [x] 1.1 `DecisionRequest` Pydantic 모델: `review_id: str`, `choice: Literal["learn_now", "queue", "ignore"]`, `queue_timing: Literal["today", "this_week", "later"] | None = None`, `memo: str | None = None`
  - [x] 1.2 `get_current_user` 의존성으로 `user_id` 추출
  - [x] 1.3 `review_id`로 `reviews` 테이블 조회 → `project_id` 획득 → `projects.user_id = user_id` 검증 (없으면 404)
  - [x] 1.4 `choice = "queue"` 시 `queue_timing is None` 이면 422 반환
  - [x] 1.5 이미 해당 `review_id`에 decision 있으면 기존 `decision_id` 반환 (멱등성)
  - [x] 1.6 `decisions` 테이블에 INSERT: `{ review_id, choice, queue_timing, memo }`
  - [x] 1.7 `return APIResponse(data={"decision_id": decision_id})` (HTTP 201)
  - [x] 1.8 `router = APIRouter(prefix="/decisions", tags=["decisions"])`, status_code=201

- [x] Task 2: `api/main.py` 수정 — decisions 라우터 등록 (AC: #5, #6, #7)
  - [x] 2.1 `from routers.decisions import router as decisions_router` import 추가
  - [x] 2.2 `app.include_router(decisions_router, prefix="/api/v1")` 추가

- [x] Task 3: `api/tests/test_decisions.py` 신규 생성 (AC: #5, #6, #7)
  - [x] 3.1 learn_now decision 저장 성공 (201 + decision_id 반환)
  - [x] 3.2 queue decision + queue_timing 저장 성공
  - [x] 3.3 ignore decision 저장 성공
  - [x] 3.4 queue decision 시 queue_timing 없으면 422
  - [x] 3.5 다른 사용자의 review_id로 요청 시 404
  - [x] 3.6 동일 review_id 중복 요청 시 기존 decision_id 반환 (멱등성)

### [WEB] ContextStickyBar 동적 구현

- [x] Task 4: `web/src/components/home/review/context-sticky-bar.tsx` 전면 교체 (AC: #1, #2, #3, #4, #5, #6, #7, #8)
  - [x] 4.1 `"use client"` 선언
  - [x] 4.2 Props: `signalId: string`, `reviewId: string`, `barGateOverride?: string | null`, `recommendationReason: string`
  - [x] 4.3 상태: `const [enabled, setEnabled] = useState(false)`, `const [seenSections, setSeenSections] = useState<Set<string>>(new Set())`
  - [x] 4.4 `const REQUIRED_SECTIONS = ['one_line_definition','key_concepts','problems_solved','why_it_matters','vs_existing_tech','user_relevance','risks','recommendation_reason']`
  - [x] 4.5 `bar_gate_override = "enabled"` 시 초기 `useState(true)` 또는 useEffect에서 즉시 `setEnabled(true)` — engagement 추적 불필요
  - [x] 4.6 IntersectionObserver 설정
  - [x] 4.7 focus 이벤트 핸들러 (VoiceOver/TalkBack)
  - [x] 4.8 `useEffect([seenSections])`: REQUIRED_SECTIONS 모두 포함 시 `setEnabled(true)`
  - [x] 4.9 aria-live 영역 텍스트: enabled 전환 시점에 "Learn Now 버튼을 사용할 수 있습니다" 주입
  - [x] 4.10 `prefers-reduced-motion` CSS 미디어 쿼리로 전환 애니메이션 제거
  - [x] 4.11 disabled UI: lock 아이콘 + "Learn Now" (text-disabled bg), hint text, Queue/Ignore hidden
  - [x] 4.12 enabled UI: "Learn Now" (accent-primary bg), Queue/Ignore ghost pills 표시, 추천 텍스트 공개
  - [x] 4.13 Learn Now 클릭 핸들러
  - [x] 4.14 Queue 클릭 핸들러
  - [x] 4.15 Ignore 클릭 핸들러
  - [x] 4.16 Queue Bottom Sheet (웹 전용 inline overlay)
  - [x] 4.17 Toast 구현

- [x] Task 5: `web/src/components/home/review/research-review-content.tsx` 수정 (AC: #2, #4)
  - [x] 5.1 Props에 `reviewId: string`, `barGateOverride?: string | null` 추가
  - [x] 5.2 `<ContextStickyBar>` 에 `reviewId`, `barGateOverride`, `recommendationReason={payload.recommendation_reason}` prop 전달
  - [x] 5.3 signalId도 ContextStickyBar에 전달

- [x] Task 6: `web/src/components/home/review/review-page-content.tsx` 수정 (AC: #3, #5)
  - [x] 6.1 `uiState.type === "completed"` 렌더링 시 `reviewId` prop 추가
  - [x] 6.2 completed 상태 진입 시 `reviewId`를 state에 보존
  - [x] 6.3 초기 completed 상태 (SSR에서 completed 로드): `initialReview.id`를 reviewId로 사용
  - [x] 6.4 Realtime completed 전환 시: `reviewIdRef.current`를 reviewId로 사용
  - [x] 6.5 `<ResearchReviewContent>` 에 `reviewId`, `barGateOverride` 전달

- [x] Task 7: `web/src/app/(app)/home/review/[signalId]/learning-path/page.tsx` 신규 생성 — placeholder (AC: #5)
  - [x] 7.1 "Learning Path 화면은 Story 4.1에서 구현됩니다." 안내 텍스트
  - [x] 7.2 "홈으로 돌아가기" `<Link href="/home">` CTA

- [x] Task 8: `web/src/components/home/review/__tests__/context-sticky-bar.test.tsx` 신규 생성
  - [x] 8.1 초기 disabled 상태: lock 아이콘, hint text, Queue/Ignore hidden 검증
  - [x] 8.2 REQUIRED_SECTIONS 모두 seen → enabled 전환 검증
  - [x] 8.3 bar_gate_override="enabled" → 즉시 enabled 검증
  - [x] 8.4 aria 속성 검증 (disabled/enabled 각 상태)
  - [x] 8.5 Queue 선택 시 Bottom Sheet 오픈 검증

### [FLUTTER] ContextStickyBar 동적 구현

- [x] Task 9: `mobile/lib/features/home/screens/research_review_screen.dart` 수정 — `_ReviewBody` StatefulWidget 전환 (AC: #1, #2, #3, #4)
  - [x] 9.1 `_ReviewBody` → `StatefulWidget` (`_ReviewBodyState`)로 전환
  - [x] 9.2 `ScrollController _scrollController` 선언 및 dispose
  - [x] 9.3 `GlobalKey` 8개 선언
  - [x] 9.4 `Set<String> _seenSections = {}` 상태 변수
  - [x] 9.5 `bool get _enabled` getter
  - [x] 9.6 `const _kRequiredSections` 상수
  - [x] 9.7 `_scrollController.addListener(_checkSectionVisibility)` 등록
  - [x] 9.8 `_checkSectionVisibility()` 구현
  - [x] 9.9 각 필수 섹션 heading 위젯에 GlobalKey 할당
  - [x] 9.10 `SingleChildScrollView`에 `controller: _scrollController` 연결
  - [x] 9.11 `_DynamicContextStickyBar`로 교체, 동적 상태 props 전달

- [x] Task 10: `mobile/lib/features/home/screens/research_review_screen.dart` — `_DynamicContextStickyBar` 구현 (AC: #1, #4, #5, #6, #7, #8, #9)
  - [x] 10.1 `_DynamicContextStickyBar` StatefulWidget
  - [x] 10.2 disabled 상태 UI
  - [x] 10.3 disabled CTA Semantics
  - [x] 10.4 enabled 상태 UI
  - [x] 10.5 enabled CTA Semantics
  - [x] 10.6 `prefers-reduced-motion` 처리 (AnimatedSwitcher)
  - [x] 10.7 Learn Now 탭 핸들러
  - [x] 10.8 Queue 탭 핸들러
  - [x] 10.9 `_showQueueBottomSheet` 구현
  - [x] 10.10 Ignore 탭 핸들러
  - [x] 10.11 Queue 성공 후 toast

- [x] Task 11: `mobile/lib/features/home/providers/research_review_provider.dart` 수정 (AC: #3)
  - [x] 11.1 `ResearchReview` 데이터 클래스에 `barGateOverride: String?` 필드 변경 (bool? → String?)
  - [x] 11.2 `_fetchCompletedReview` 내 Supabase 쿼리에 `bar_gate_override` 포함 (이미 포함됨)
  - [x] 11.3 파싱 시 `response['bar_gate_override'] as String?` 추출
  - [x] 11.4 `build_runner` 재실행 (`.g.dart` 파일 재생성)

- [x] Task 12: `mobile/lib/core/router/app_router.dart` 수정 — learning-path placeholder 추가 (AC: #5)
  - [x] 12.1 `/home/review/:signalId/learning-path` GoRoute 추가 → `_LearningPathPlaceholderScreen`
  - [x] 12.2 Queue branch는 GoRoute 내 sub-route로 처리됨

- [x] Task 13: `mobile/lib/features/home/screens/research_review_screen.dart` — API 호출 헬퍼 추가 (AC: #5, #6, #7)
  - [x] 13.1 `_postDecision({required String choice, String? queueTiming, String? memo})` async 함수
  - [x] 13.2 `Supabase.instance.client.auth.currentSession?.accessToken`으로 JWT 획득
  - [x] 13.3 `http.post('$fastapiUrl/api/v1/decisions', ...)` 호출
  - [x] 13.4 FASTAPI_URL: `const String.fromEnvironment('FASTAPI_URL', defaultValue: 'http://localhost:8000')`
  - [x] 13.5 실패 시 `ScaffoldMessenger` 에러 snackbar

## Dev Notes

### 핵심 아키텍처 제약

| 규칙 | 상세 |
|------|------|
| **AD-3** 쓰기 경로 | `decisions` INSERT: FastAPI만. 읽기: Supabase SDK 직접 |
| **AD-8** Decision CTA | 3종 고정: learn_now / queue / ignore; Queue 타이밍 3종: today / this_week / later |
| **AD-13** API 계약 | `Authorization: Bearer {JWT}`, `/api/v1/`, 응답 봉투 `{data, error}` |
| **AD-14** Flutter 상태관리 | Riverpod 2.x 단일 표준 |

### 현재 파일 상태 (이 스토리가 수정할 파일들)

**이미 구현된 것 (수정 대상):**
- `web/src/components/home/review/context-sticky-bar.tsx` — 정적 disabled 상태만. **이 스토리에서 전면 교체**
- `web/src/components/home/review/research-review-content.tsx` — `<ContextStickyBar />` 를 props 없이 렌더링 중. **reviewId, barGateOverride, recommendationReason props 추가 필요**
- `web/src/components/home/review/review-page-content.tsx` — `barGateOverride` 수신하나 `ResearchReviewContent`에 미전달. **전달 로직 추가 필요**
- `mobile/.../research_review_screen.dart` — `_ContextStickyBar` 정적 disabled 위젯. **_DynamicContextStickyBar로 전환**
- `mobile/.../research_review_provider.dart` — `barGateOverride` 필드 없음. **추가 필요**

### `decisions` 테이블 스키마

```sql
CREATE TABLE IF NOT EXISTS public.decisions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id    UUID NOT NULL REFERENCES public.reviews(id) ON DELETE CASCADE,
    choice       TEXT NOT NULL CHECK (choice IN ('learn_now', 'queue', 'ignore')),
    queue_timing TEXT CHECK (queue_timing IN ('today', 'this_week', 'later')),
    memo         TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_queue_timing CHECK (
        (choice = 'queue' AND queue_timing IS NOT NULL) OR
        (choice != 'queue')
    )
);
```
RLS 정책: `EXISTS (SELECT 1 FROM projects WHERE id = (SELECT project_id FROM reviews WHERE id = review_id) AND user_id = auth.uid())`

### API Router 패턴 (기존 `api/routers/reviews.py` 참고)

```python
# api/routers/decisions.py
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from core.schemas import APIResponse
from core.supabase import get_supabase
from middleware.auth import get_current_user

router = APIRouter(prefix="/decisions", tags=["decisions"])

class DecisionRequest(BaseModel):
    review_id: str
    choice: Literal["learn_now", "queue", "ignore"]
    queue_timing: Literal["today", "this_week", "later"] | None = None
    memo: str | None = None
```

`decisions` 쓰기는 FastAPI만 — 서비스 롤 키 사용하는 `get_supabase()` 활용.

### Web: IntersectionObserver + focus 기반 섹션 tracking

`research-review-content.tsx`의 `h2` 요소들에는 이미 `data-section-key` 속성이 있다. ContextStickyBar에서 이 속성으로 querySelectorAll 조회:

```typescript
const REQUIRED_SECTIONS = new Set([
  'one_line_definition','key_concepts','problems_solved','why_it_matters',
  'vs_existing_tech','user_relevance','risks','recommendation_reason'
]);

useEffect(() => {
  const elements = document.querySelectorAll('[data-section-key]');
  const seenSet = new Set<string>();
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const key = (entry.target as HTMLElement).dataset.sectionKey!;
        seenSet.add(key);
        setSeenSections(new Set(seenSet));
      }
    });
  }, { threshold: 0.1 });
  
  const focusHandlers: Array<[Element, () => void]> = [];
  elements.forEach(el => {
    observer.observe(el);
    const handler = () => {
      const key = (el as HTMLElement).dataset.sectionKey!;
      seenSet.add(key);
      setSeenSections(new Set(seenSet));
    };
    el.addEventListener('focus', handler);
    focusHandlers.push([el, handler]);
  });
  
  return () => {
    observer.disconnect();
    focusHandlers.forEach(([el, h]) => el.removeEventListener('focus', h));
  };
}, []); // 컴포넌트 마운트 후 1회만 실행 (review가 완료 상태로 렌더링된 이후)
```

**주의**: `useEffect([], [])` 의존성 빈 배열로 충분. review payload는 already rendered.

### Web: `review-page-content.tsx` 수정 — reviewId 전달

현재 `uiState.type === "completed"` 에서 `reviewId`를 전달하지 않는다. 수정:

```typescript
type ReviewUIState =
  | { type: "completed"; reviewId: string; payload: ReviewPayload; signalTitle: string; barGateOverride?: string | null }
  | { type: "generating" }
  | { type: "failed" };

// 초기 completed 상태:
if (initialReview?.status === "completed" && initialReview.payload) {
  return {
    type: "completed",
    reviewId: initialReview.id,  // 추가
    payload: initialReview.payload,
    signalTitle: initialReview.signalTitle,
    barGateOverride: initialReview.barGateOverride,
  };
}

// Realtime completed 수신:
setUIState({
  type: "completed",
  reviewId: reviewIdRef.current!,  // 추가
  payload: fetched,
  signalTitle,
  barGateOverride: data?.bar_gate_override as string | null,
});
```

### Web: Queue Bottom Sheet (웹은 모달 패널 직접 구현)

Flutter의 `showModalBottomSheet`와 달리 웹은 CSS position fixed로 구현:

```tsx
{queueSheetOpen && (
  <>
    {/* scrim */}
    <div
      role="presentation"
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 50 }}
      onClick={() => setQueueSheetOpen(false)}
    />
    {/* sheet */}
    <div
      role="dialog"
      aria-modal="true"
      aria-label="학습 일정 선택"
      style={{
        position: 'fixed', bottom: 0, left: 0, right: 0,
        background: 'var(--surface-base)',
        borderRadius: '24px 24px 0 0',
        padding: '12px 20px 40px',
        zIndex: 51,
      }}
    >
      {/* drag handle */}
      <div style={{ width: 36, height: 4, background: '#DDD', borderRadius: 9999, margin: '0 auto 16px' }} />
      <p className="text-body-large" style={{ marginBottom: 16 }}>언제 학습할까요?</p>
      {/* Today / This Week / Later 버튼 3개 */}
      {/* 메모 입력 */}
    </div>
  </>
)}
```

### Flutter: ScrollController 기반 섹션 visibility 추적

`VisibilityDetector` 패키지가 없으므로 ScrollController + RenderBox 방식 사용:

```dart
void _checkSectionVisibility() {
  final screenHeight = MediaQuery.of(context).size.height;
  final threshold = screenHeight * 0.9; // 90%까지 내려오면 seen

  final keyMap = {
    'one_line_definition': _keyOneLineDef,
    'key_concepts': _keyKeyConcepts,
    'problems_solved': _keyProblemsSolved,
    'why_it_matters': _keyWhyItMatters,
    'vs_existing_tech': _keyVsExisting,
    'user_relevance': _keyUserRelevance,
    'risks': _keyRisks,
    'recommendation_reason': _keyRecommendation,
  };

  bool changed = false;
  keyMap.forEach((key, gKey) {
    if (_seenSections.contains(key)) return;
    final ctx = gKey.currentContext;
    if (ctx == null) return;
    final box = ctx.findRenderObject() as RenderBox?;
    if (box == null) return;
    final pos = box.localToGlobal(Offset.zero);
    if (pos.dy < threshold) {
      _seenSections.add(key);
      changed = true;
    }
  });

  if (changed) {
    final wasEnabled = _previousEnabled;
    final nowEnabled = _enabled;
    setState(() {});
    if (!wasEnabled && nowEnabled) {
      SemanticsService.announce(
        'Learn Now 버튼을 사용할 수 있습니다',
        TextDirection.ltr,
      );
      _previousEnabled = true;
    }
  }
}
```

`_scrollController.addListener(_checkSectionVisibility)` — `initState`에서 등록, `dispose`에서 제거.

### Flutter: FASTAPI_URL 환경변수 패턴 확인

기존 `research_review_provider.dart`에서 http 패키지로 API 호출 시 `--dart-define` 패턴 사용 중:

```dart
const fastapiUrl = String.fromEnvironment('FASTAPI_URL', defaultValue: 'http://localhost:8000');
```

동일 패턴 사용. `decisions` 엔드포인트 URL: `$fastapiUrl/api/v1/decisions`

### Flutter: `barGateOverride` prop 전달 경로

```
ResearchReview(barGateOverride: String?)  // research_review_provider.dart
  ↓
_ReviewBody(review: ResearchReview)       // research_review_screen.dart
  ↓
_DynamicContextStickyBar(barGateOverride: review.barGateOverride)
```

`ResearchReview` 데이터 클래스에 필드 추가 후 `fromJson` 업데이트:
```dart
barGateOverride: json['bar_gate_override'] as String?,
```

### 범위 경계

| 항목 | 이 스토리 (3.3) | 이후 스토리 |
|------|----------------|------------|
| IntersectionObserver 섹션 tracking | ✅ | — |
| ContextStickyBar enable/disable 로직 | ✅ | — |
| Learn Now / Queue / Ignore Decision API | ✅ | — |
| Queue 타이밍 Bottom Sheet | ✅ | — |
| bar_gate_override 처리 | ✅ | — |
| Learning Path 화면 구현 | placeholder만 | Story 4.1 |
| Outcome 입력 화면 | ❌ | Story 4.2 |
| Memory 기록 | ❌ | Story 4.3 |
| Contextual Chat 화면 | ❌ | Story 3.4 |

### 절대 금지사항

| 금지 | 이유 |
|------|------|
| `decisions` 테이블 클라이언트 직접 쓰기 | AD-3: FastAPI만 쓰기 가능 |
| ContextStickyBar 활성화를 사용자가 임의로 건너뛸 수 있는 경로 | UX 원칙: Review Before Action |
| Learn Now / Queue / Ignore 중복 동작 확인 다이얼로그 | 의도적으로 없음 — 마찰은 bar 활성화 과정에 내재 |
| "잠시만 기다려 주세요" 카피 | UX 금지 패턴 |
| Floating FAB 또는 Chat 버튼 추가 | 명시적 금지 패턴 |
| 섹션 읽기 진행률 bar/streak 표시 | 게임화 금지 |
| `showDialog` / `AlertDialog` (Flutter) | `showModalBottomSheet` 사용 필수 |

### 신규 / 수정 파일 목록

```
# API 신규 파일
api/routers/decisions.py                          (NEW)
api/tests/test_decisions.py                       (NEW)

# API 수정 파일
api/main.py                                       (UPDATE — decisions_router 등록)

# 웹 수정 파일
web/src/components/home/review/context-sticky-bar.tsx         (UPDATE — 전면 교체)
web/src/components/home/review/research-review-content.tsx    (UPDATE — props 추가)
web/src/components/home/review/review-page-content.tsx        (UPDATE — reviewId/barGateOverride 전달)

# 웹 신규 파일
web/src/app/(app)/home/review/[signalId]/learning-path/page.tsx  (NEW — placeholder)
web/src/components/home/review/__tests__/context-sticky-bar.test.tsx (NEW)

# Flutter 수정 파일
mobile/lib/features/home/providers/research_review_provider.dart  (UPDATE — barGateOverride 추가)
mobile/lib/features/home/providers/research_review_provider.g.dart (UPDATE — build_runner 재생성)
mobile/lib/features/home/screens/research_review_screen.dart       (UPDATE — 동적 bar 전환)
mobile/lib/core/router/app_router.dart                             (UPDATE — learning-path 라우트 추가)
```

### References

- 에픽: `_bmad-output/planning-artifacts/epics.md` — Story 3.3 (line 581–628)
- 아키텍처: `ARCHITECTURE-SPINE.md` — AD-3(데이터 접근), AD-8(MVP 범위), AD-13(API 계약)
- UX: `EXPERIENCE.md` — Context Sticky Bar (line 154–183), Queue Sub-Selection Sheet (line 479–482), Decision Loop Patterns (line 762–806), Accessibility Floor ContextStickyBar ARIA (line 612–618), Flutter Semantics ContextStickyBar (line 658–675)
- DB 스키마: `_bmad-output/implementation-artifacts/db/001_initial_schema.sql` — decisions 테이블
- 기존 리뷰 API 패턴: `api/routers/reviews.py`
- 기존 ContextStickyBar stub: `web/src/components/home/review/context-sticky-bar.tsx`
- 기존 Flutter bar stub: `mobile/lib/features/home/screens/research_review_screen.dart` — `_ContextStickyBar`
- 기존 ResearchReviewContent: `web/src/components/home/review/research-review-content.tsx`
- 기존 ReviewPageContent: `web/src/components/home/review/review-page-content.tsx`
- 이전 스토리: `_bmad-output/implementation-artifacts/3-2-on-demand-research-review-생성.md` — Deferred: "Realtime fast path에서 barGateOverride 하드코딩 null — Story 3.3에서 처리"
- Flutter http 패턴: `mobile/lib/features/home/providers/research_review_provider.dart`
- Flutter 상태 관리: Riverpod 2.x @riverpod 패턴

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Flutter `SemanticsService.announce` �� `sendAnnouncement(View.of(context), ...)` 으로 변경 (v3.35.0+ API)
- `ResearchReview.barGateOverride` bool? → String? 타입 변경 (스토리 스펙 정합)

### Completion Notes List

- `api/routers/decisions.py` 신규: POST /api/v1/decisions (learn_now / queue / ignore), 멱등성, 소유권 검증
- `api/main.py` 수정: decisions_router 등록
- `api/tests/test_decisions.py` 신규: 6개 테스트 (모두 통과)
- `web/src/components/home/review/context-sticky-bar.tsx` 전면 교체: IntersectionObserver + focus 섹션 추적, bar_gate_override 처리, 3가지 CTA 동작, Queue Bottom Sheet, Toast
- `web/src/components/home/review/research-review-content.tsx` 수정: reviewId/barGateOverride/recommendationReason props 추가
- `web/src/components/home/review/review-page-content.tsx` 수정: ReviewUIState에 reviewId 필드 추가, 전달 로직 완성
- `web/src/app/(app)/home/review/[signalId]/learning-path/page.tsx` 신규: placeholder
- `web/src/components/home/review/__tests__/context-sticky-bar.test.tsx` 신규: 5개 테스트 스펙
- `mobile/lib/features/home/providers/research_review_provider.dart` 수정: barGateOverride bool? → String?
- `mobile/lib/features/home/screens/research_review_screen.dart` 전면 교체: _ReviewBody StatefulWidget, _DynamicContextStickyBar, ScrollController+GlobalKey 섹션 tracking, API 헬퍼
- `mobile/lib/core/router/app_router.dart` 수정: learning-path GoRoute + _LearningPathPlaceholderScreen
- `mobile/lib/features/home/providers/research_review_provider.g.dart` 및 `mobile/lib/core/router/app_router.g.dart` 재생성

### File List

api/routers/decisions.py
api/main.py
api/tests/test_decisions.py
web/src/components/home/review/context-sticky-bar.tsx
web/src/components/home/review/research-review-content.tsx
web/src/components/home/review/review-page-content.tsx
web/src/app/(app)/home/review/[signalId]/learning-path/page.tsx
web/src/components/home/review/__tests__/context-sticky-bar.test.tsx
mobile/lib/features/home/providers/research_review_provider.dart
mobile/lib/features/home/providers/research_review_provider.g.dart
mobile/lib/features/home/screens/research_review_screen.dart
mobile/lib/core/router/app_router.dart
mobile/lib/core/router/app_router.g.dart

### Review Findings

#### Decision Needed

- [x] [Review][Patch] D1→Patch [MEDIUM] Queue 성공 후 홈으로 이동 추가 — 재결정 방지. Web: `handleQueueTiming` 성공 시 `router.push('/home')` 추가. Flutter: Queue timing 선택 성공 시 `context.go('/home')` 추가. [context-sticky-bar.tsx:159-181, research_review_screen.dart:726-763]
- [x] [Review][Decision] D2: AC-6 Queue 타이밍 레이블 언어 불일치 — dismissed. 한국어 레이블은 의도적 로컬라이제이션으로 확정.

#### Patches

- [x] [Review][Patch] P1 [HIGH] AC-7 (Web): Ignore 토스트 미표시 — `router.push("/home")` 가 `setToastMessage` 직후 동기 실행되어 컴포넌트가 unmount되기 전에 토스트가 렌더링되지 않음. [context-sticky-bar.tsx:147-153]
- [x] [Review][Patch] P2 [HIGH] AC-3 (Web): Realtime 경로에서 barGateOverride 유실 — `result.payload`가 Realtime 변경 레코드에 포함된 경우 `barGateOverride: null`로 하드코딩됨. bar_gate_override="enabled"인 리뷰가 생성 중인 상태에서 열리면 enabled 전환 불가. [review-page-content.tsx:67]
- [x] [Review][Patch] P3 [HIGH] Flutter: `_checkSectionVisibility` mounted 체크 누락 — 스크롤 리스너가 dispose 이후에도 실행 가능하여 `setState` 호출 시 런타임 예외 발생 가능. [research_review_screen.dart:251-282]
- [x] [Review][Patch] P4 [MEDIUM] API: SELECT-then-INSERT 레이스 컨디션 — 동일 review_id로 동시 요청 시 두 요청이 모두 기존 decision 체크를 통과해 중복 INSERT 가능. DB unique constraint 또는 upsert 필요. [decisions.py:59-86]
- [x] [Review][Patch] P5 [MEDIUM] Web: handleQueueTiming 실패 시 사용자 피드백 없음 — catch 블록이 비어있어 네트워크/API 오류 시 사용자는 아무런 안내를 받지 못함. [context-sticky-bar.tsx:176-178]
- [x] [Review][Patch] P6 [MEDIUM] Web: handleQueueTiming isSubmitting 가드 누락 — Bottom Sheet 내 타이밍 버튼에 isSubmitting 체크가 없어 빠른 연속 탭 시 중복 제출 가능. [context-sticky-bar.tsx:159]
- [x] [Review][Patch] P7 [MEDIUM] Web: navigation 실패 시 isSubmitting 고착 — handleLearnNow·handleIgnore 모두 router.push 실패 시 isSubmitting 리셋 로직이 없어 버튼이 영구 비활성화됨. [context-sticky-bar.tsx:136-157]
- [x] [Review][Patch] P8 [MEDIUM] Web: 세션 만료 시 postDecision 무음 실패 — token이 null이면 Authorization 헤더 없이 요청 전송 → 401 반환 → catch에서 isSubmitting만 리셋, 사용자 피드백 없음. [context-sticky-bar.tsx:110-134]
- [x] [Review][Patch] P9 [MEDIUM] Web: Queue Bottom Sheet 포커스 트랩 없음 — `aria-modal="true"` 설정됐으나 브라우저/VoiceOver 지원 불일치로 키보드 포커스가 오버레이 뒤 요소로 탈출 가능. [context-sticky-bar.tsx:215-302]
- [x] [Review][Patch] P10 [MEDIUM] Web: `<style>` 전역 `*` 선택자로 prefers-reduced-motion 처리 — 컴포넌트 마운트 시 문서 전체의 transition/animation 제거. CSS Modules 또는 scoped 선택자로 교체 필요. [context-sticky-bar.tsx:458-462]
- [x] [Review][Patch] P11 [MEDIUM] Flutter: Queue Bottom Sheet 타이밍 버튼 동시 탭 가능 — OutlinedButton.onPressed에 `_isSubmitting` 가드 없어 빠른 연속 탭 시 중복 API 호출 가능. [research_review_screen.dart:726]
- [x] [Review][Patch] P12 [MEDIUM] Flutter: 초기 뷰포트 내 섹션이 ScrollListener 미실행으로 관측 안 됨 — 스크롤 없이 모든 필수 섹션이 화면에 들어오는 기기(태블릿 등)에서 바가 영구 잠금. Web IntersectionObserver는 즉시 fire하나 Flutter ScrollController는 스크롤 이벤트 필요. [research_review_screen.dart:241]
- [x] [Review][Patch] P13 [MEDIUM] Web: recommendationReason 길이 제한 없음 — enabled 상태에서 AI 생성 텍스트가 무제한으로 렌더링되어 sticky bar를 밀어낼 수 있음. Flutter는 maxLines:2 적용됨. [context-sticky-bar.tsx:389-399]
- [x] [Review][Patch] P14 [LOW] API: non-queue choice에 queue_timing 허용 — learn_now/ignore 요청에 queue_timing이 포함돼도 422 반환 없이 DB에 저장됨. [decisions.py:15-17]
- [x] [Review][Patch] P15 [LOW] API: memo 빈 문자열 NULL 미정규화 — `""` 전송 시 NULL 대신 빈 문자열 저장. [decisions.py:17]
- [x] [Review][Patch] P16 [LOW] AC-8 (Flutter): ↑ 화살표 스크린리더 미제외 — 힌트 텍스트의 ↑ 문자가 `ExcludeSemantics`로 감싸지 않아 스크린리더가 "위 화살표"를 발화. [research_review_screen.dart:797]
- [x] [Review][Patch] P17 [LOW] AC-8 (Flutter): disabled CTA Semantics hint 프로퍼티 누락 — web의 `aria-describedby="ctx-hint"` 에 해당하는 `hint:` 프로퍼티가 Semantics에 없음. [research_review_screen.dart:805]
- [x] [Review][Patch] P18 [LOW] 테스트: `_decisions_count` 함수 속성이 테스트 간 누수 — 함수 객체에 상태를 붙이는 패턴으로 동일 프로세스 내 순차 실행 시 카운터 오염. [test_decisions.py:44-52]
- [x] [Review][Patch] P19 [LOW] 테스트: queue/ignore 201 응답 body 미검증 — status_code만 확인하여 응답 봉투 구조 변경 시 무음 통과. [test_decisions.py:116, 154]
- [x] [Review][Patch] P20 [LOW] 테스트: 멱등성 테스트가 분기 유효성 미검증 — decisions 테이블 mock이 SELECT·INSERT 모두 동일 id를 반환해 멱등성 분기 삭제 후에도 통과. [test_decisions.py:231-255]

#### Deferred

- [x] [Review][Defer] W1: Supabase INSERT 실패 시 로깅 없음 [decisions.py:81-85] — deferred, 관찰성 개선 항목
- [x] [Review][Defer] W2: barGateOverride 빈 deps useEffect — 마운트 후 prop 변경 시 observer 미재실행 [context-sticky-bar.tsx:42] — deferred, 실제 prop이 세션 중 변경되지 않아 영향 미미
- [x] [Review][Defer] W3: FASTAPI_URL dart-define 미설정 시 localhost 기본값 — deferred, 배포 설정 문제로 코드 변경 불필요
- [x] [Review][Defer] W4: migration 파일 diff에 미포함 — deferred, 별도 경로에 존재할 가능성 있음. 배포 전 확인 필요

### Review Findings (Round 2)

#### Decision Needed

- [x] [Review][Decision] DN1: AC-2 Flutter 포커스/키보드 섹션 tracking 미구현 — 스크롤 리스너만 있어 키보드/스크린리더 포커스로는 섹션이 "seen" 처리되지 않음. FocusNode 기반 tracking 추가 여부 결정 필요. [research_review_screen.dart] → Patch 적용: FocusNode 8개 추가, _ReviewSection에 focusNode prop 연결

#### Patches

- [x] [Review][Patch] P1 [MEDIUM] `except Exception`이 race 외 모든 오류 포착 — 네트워크 타임아웃·스키마 오류 등 비-race 예외를 포착하여 오류 컨텍스트 소멸, 500 반환 [decisions.py:84-110]
- [x] [Review][Patch] P2 [MEDIUM] `handleIgnore` 성공 시 `isSubmitting` 미복구 — 1.5s 지연 사이 bar가 동결, App Router 공유 레이아웃에서 컴포넌트 미unmount 시 영구 동결 가능 [context-sticky-bar.tsx:184-194]
- [x] [Review][Patch] P3 [MEDIUM] `handleLearnNow` catch 블록 사용자 피드백 없음 — API 실패 시 isSubmitting만 리셋, 오류 toast 없음 [context-sticky-bar.tsx:155-160]
- [x] [Review][Patch] P4 [MEDIUM] Flutter `_postDecision` 세션 만료 시 빈 토큰 전송 — `accessToken ?? ''`로 빈 bearer 전송, pre-check 없어 generic snackbar만 표시 [research_review_screen.dart:609-624]
- [x] [Review][Patch] P5 [MEDIUM] Queue Sheet 포커스 트랩: focusable 요소 없을 시 포커스 이동 안 됨 — dialog mount 직후 focusable NodeList가 비어 있으면 first가 undefined [context-sticky-bar.tsx:105-131]
- [x] [Review][Patch] P6 [MEDIUM] Queue 버튼 `isSubmitting` 가드 없음 — Learn Now/Ignore 진행 중 Queue 버튼 탭 시 Bottom Sheet 오픈 → 동시 decision POST 가능 [context-sticky-bar.tsx:469-483]
- [x] [Review][Patch] P7 [MEDIUM] `triggerAndSubscribe` 언마운트 cleanup race — 컴포넌트 unmount가 await 중 발생 시 cleanup이 cleanupRef 할당 전 실행 → channel 영구 누수 [review-page-content.tsx:58-77]
- [x] [Review][Patch] P8 [MEDIUM] `reviewIdRef.current!` non-null 단언 안전하지 않음 — realtime 콜백 내에서 ref가 null일 시 throw [review-page-content.tsx:67]
- [x] [Review][Patch] P9 [MEDIUM] `handleRetry` 동시 호출 시 channel 누수 — 첫 triggerAPI가 느릴 때 retry 재호출 시 두 채널이 동시 실행되고 하나 누수 [review-page-content.tsx:146-161]
- [x] [Review][Patch] P10 [MEDIUM] AC-8: Web disabled CTA 네이티브 `disabled` 속성으로 키보드 포커스 불가 — `disabled` + `aria-disabled="true"` 혼용으로 탭 접근 차단, aria-describedby ctx-hint 읽기 불가 [context-sticky-bar.tsx:390]
- [x] [Review][Patch] P11 [MEDIUM] AC-10: Queue memo textarea 접근성 레이블 없음 — placeholder만 사용, `<label>` 또는 `aria-label` 없어 스크린리더 미인식 [context-sticky-bar.tsx:326-341]
- [x] [Review][Patch] P12 [MEDIUM] Supabase INSERT RLS 위반 시 misleading 500 — RLS 차단 시 exception 아닌 empty data 반환 → 오류 분기 `if not insert_result.data` → 500, 원인 불명확 [decisions.py:84-116]
- [x] [Review][Patch] P13 [MEDIUM] Flutter `_previousEnabled` setState 외부 뮤테이션 — 고속 스크롤 시 `sendAnnouncement` 중복 발화 가능 [research_review_screen.dart:274-285]
- [x] [Review][Patch] P14 [LOW] `_base_mock` 카운터 호출 순서 의존 — 프로덕션 코드 호출 순서 변경 시 mock이 잘못된 데이터 반환 [test_decisions.py:22-50]
- [x] [Review][Patch] P15 [LOW] Queue Bottom Sheet 제목 `<p>` 태그 — 시맨틱 heading 아님 (dialog 내 제목은 heading 권장) [context-sticky-bar.tsx:295-302]

#### Deferred

- [x] [Review][Defer] W1: `get_supabase()` 연결 오류 핸들링 없음 [decisions.py:43] — deferred, 기존 패턴, 이 스토리 범위 밖
- [x] [Review][Defer] W2: `seenSet` 클로저 로컬 변수 — dep 변경 시 history 초기화 footgun [context-sticky-bar.tsx:69] — deferred, 현재 빈 deps로 실제 영향 없음
- [x] [Review][Defer] W3: 동시 INSERT race path 테스트 커버리지 없음 [test_decisions.py] — deferred, 테스트 커버리지 개선 항목
- [x] [Review][Defer] W4: `review_id` 포맷 검증 없음 [decisions.py:14] — deferred, Supabase 파라미터화 쿼리로 실질적 위험 낮음
- [x] [Review][Defer] W5: `triggerAPI` 인증 실패 시 generic "failed" 상태 — UX 개선 항목 [review-page-content.tsx:96-110]
- [x] [Review][Defer] W6: `test_queue_without_timing` DB 호출 없이 통과 — 로직 순서 변경 취약성 [test_decisions.py:113-127]

## Change Log

- 2026-07-25: Story 3.3 생성 — ContextStickyBar 동적 activation, Learn Now / Queue / Ignore Decision API, 섹션 engagement tracking (web IntersectionObserver, Flutter ScrollController+RenderBox), bar_gate_override 처리.
- 2026-07-25: Story 3.3 구현 완료 — API decisions 라우터 (6 테스트 통과), Web ContextStickyBar 동적 구현, Flutter _ReviewBody StatefulWidget 전환 + _DynamicContextStickyBar, learning-path placeholder. Status → review.
- 2026-07-25: 코드 리뷰 완료 — 2개 decision_needed, 20개 patch, 4개 defer, 7개 dismiss. Status → in-progress.
- 2026-07-27: 코드 리뷰 Round 2 — 1개 decision_needed, 15개 patch, 6개 defer, 9개 dismiss. Status → in-progress.
- 2026-07-27: 코드 리뷰 Round 2 패치 전체 적용 완료 (DN1 + P1–P15). Status → done.
