---
baseline_commit: NO_VCS
---

# Story 5.1: Queue 탭

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

사용자로서,
<span lang="en">Queue</span>에 저장한 학습 항목을 <span lang="en">Today</span> / <span lang="en">This Week</span> / <span lang="en">Later</span> 그룹으로 확인하고 일정을 변경할 수 있기를 원한다,
그래서 배우기로 한 기술을 잊지 않고 원하는 시점에 학습할 수 있다.

**범위 참고**: Web + Flutter 양쪽 모두 대상이며, API는 신규 `PATCH /api/v1/decisions/:id` 엔드포인트 1개만 추가한다(목록 조회는 AD-3에 따라 클라이언트가 Supabase SDK로 직접 읽는다 — 기존 `decisions_select` RLS 정책이 이미 존재하므로 신규 마이그레이션 불필요, 아래 DB 스키마 참조).

## Acceptance Criteria

**AC-1: 큐 탭 진입 시 그룹 표시**
- **Given** 큐 탭을 열면
- **Then** <span lang="en">Today</span> / <span lang="en">This Week</span> / <span lang="en">Later</span> 그룹 헤딩(22px/700, `.text-section-title`)이 이 순서로 표시되고 그 아래 각 그룹에 속한 QueueItem이 나열된다
- **And** 각 그룹에 항목이 없으면 해당 그룹 헤딩 자체가 렌더링되지 않는다(빈 헤딩만 있는 상태 금지)
- **And** `choice='queue'`인 항목이 하나도 없으면 "큐에 저장된 학습 항목이 없습니다. Signal을 읽고 Queue를 선택하면 여기에 저장됩니다." 빈 상태 메시지가 표시된다 [Source: EXPERIENCE.md line 408]

**AC-2: QueueItem 구성 요소**
- **Given** QueueItem을 확인하면
- **Then** 타이밍 배지(<span lang="en">TODAY/THIS WEEK/LATER</span>, 10px/uppercase/700/letter-spacing 0.5px, `surface-card-alt`(#ECECEC) 배경 + `text-secondary` 텍스트) + Signal 제목(15px/600) + 예상 시간(12px/`text-secondary`) + "일정 변경" 텍스트 링크(12px/`text-secondary`/underline) + chevron 아이콘(`text-tertiary`)이 표시된다
- **And** 항목의 tap target `min-height: 44px`
- **And** 접근성 composite label: `aria-label="Today 예약됨, [Signal 제목], 약 [N]분"` (배지 값에 따라 <span lang="en">Today/This Week/Later</span> 치환) [Source: EXPERIENCE.md line 625]
- **And** "일정 변경" 링크는 별도 `aria-label="일정 변경 — [Signal 제목]"`을 가진 독립된 상호작용 요소다 [Source: EXPERIENCE.md line 703]

**AC-3: 미완료(overdue) 배지**
- **Given** 자정이 지난 <span lang="en">Today</span> 항목이 남아 있을 때 (해당 decision의 `queue_timing='today'`이고 `updated_at`의 KST 날짜가 오늘의 KST 날짜보다 이전)
- **Then** "미완료" 배지(`status-warning` 텍스트, 배경 fill 없음 — 텍스트 전용, 사용자에게 경고감을 주지 않기 위함)가 표시된다
- **And** 이 배지는 그룹 소속을 바꾸지 않는다 — 항목은 여전히 <span lang="en">Today</span> 그룹에 남는다

**AC-4: 일정 변경(reschedule)**
- **Given** "일정 변경" 링크를 탭하면
- **Then** <span lang="en">Today</span> / <span lang="en">This Week</span> / <span lang="en">Later</span> 선택 <span lang="en">Bottom Sheet</span>가 열린다 ( `showModalBottomSheet` / `role="dialog"` — `AlertDialog`/`showDialog` 금지, UX-DR18)
- **And** 현재 선택된 타이밍은 `accent-primary` 보더(채움 아님)로 표시된다 [Source: EXPERIENCE.md line 291]
- **And** 선택 즉시 낙관적 업데이트로 배지가 변경되고 비동기로 저장된다 — 실패 시 이전 배지 값으로 롤백하고 오류 토스트를 표시한다
- **And** `PATCH /api/v1/decisions/:id`로 `queue_timing`이 업데이트된다 (메모 필드 없음 — 순수 타이밍 변경)

**AC-5: QueueItem 탭 → Research Review 이동**
- **Given** QueueItem을 탭하면 ("일정 변경" 링크 영역 제외)
- **Then** 해당 Signal의 Research Review 상세 화면으로 이동한다 — 경로는 `/queue/review/:signalId` (큐 탭 브랜치/스택 내 push, Home 탭의 스택과 독립적) [Source: EXPERIENCE.md line 103]

## Tasks / Subtasks

### [API] `PATCH /api/v1/decisions/:id` 엔드포인트

- [x] Task 1: `api/routers/decisions.py`에 PATCH 핸들러 추가 (AC: 4)
  - [x] 1.1 `DecisionUpdateRequest(BaseModel)` 추가: `queue_timing: Literal["today", "this_week", "later"]` (필수 — 이 엔드포인트는 타이밍 변경 전용, 기존 `DecisionRequest`는 그대로 두고 재사용하지 않는다)
  - [x] 1.2 `@router.patch("/{decision_id}", response_model=APIResponse)` 함수 `update_decision(decision_id: str, body: DecisionUpdateRequest, user_id: Annotated[str, Depends(get_current_user)]) -> APIResponse` 추가 (기존 `create_decision`과 같은 파일, 아래에 이어서 작성)
  - [x] 1.3 4-hop 소유권 검증 — **소유권 확인(3, 4단계)을 반드시 비즈니스 규칙 검증(2단계)보다 먼저 완료한다**: 순서를 바꾸면 소유하지 않은 `decision_id`라도 "404(없음)" 대신 "422(choice가 queue 아님)"를 받아 그 decision이 존재하고 `choice`가 무엇인지 추론할 수 있는 정보 노출이 발생한다(기존 `create_decision`의 3-hop 패턴에 decision→review 조회 1단계를 앞에 추가):
    1. `client.table("decisions").select("id, review_id, choice").eq("id", decision_id).execute().data` — 없으면 404 `"Decision not found"`
    2. `client.table("reviews").select("id, project_id").eq("id", review_id).execute().data` — 없으면 404 `"Decision not found"` (기존 POST와 동일 문구로 존재 여부를 노출하지 않음)
    3. `client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute().data` — 없으면 404 `"Decision not found"`
    4. **소유권 확인이 끝난 뒤에만** `choice != "queue"`를 검사 — 422 `"queue_timing can only be updated for queue decisions"` (P14 패턴과 동일하게 스키마 불변식을 라우터에서 명시적으로 재확인)
  - [x] 1.4 `client.table("decisions").update({"queue_timing": body.queue_timing}).eq("id", decision_id).execute()` 실행 — `trg_decisions_updated_at` 트리거가 `updated_at`을 자동 갱신한다(별도 코드로 `updated_at`을 세팅하지 않는다)
  - [x] 1.5 `update_result.data`가 비어 있으면 403 `"Decision update was denied"` (기존 POST의 empty-data 방어 패턴과 동일 — service_role은 RLS를 우회하므로 실무에서는 거의 발생하지 않지만 컨벤션 일치를 위해 유지)
  - [x] 1.6 `return APIResponse(data={"decision_id": decision_id, "queue_timing": body.queue_timing})`
  - [x] 1.7 POST 핸들러의 `queue_timing`/`choice` 검증 로직(P14, 1.4)은 변경하지 않는다 — PATCH는 별도 함수로 완전히 분리

- [x] Task 2: `api/tests/test_decisions.py`에 PATCH 테스트 추가 (AC: 4) — 기존 `_chain`/`_make_token` 헬퍼 재사용, `_base_mock`은 PATCH 시나리오에 맞지 않으므로 이 태스크의 테스트는 자체 `table_side_effect`를 작성한다 (기존 6개 POST 테스트의 `table_side_effect` 인라인 정의 패턴을 그대로 따름)
  - [x] 2.1 성공: `choice='queue'`인 decision → `queue_timing` 업데이트 → 200 + `{"decision_id":..., "queue_timing": "later"}` 반환
  - [x] 2.2 `choice='learn_now'` decision에 PATCH 시도 → 422
  - [x] 2.3 존재하지 않는 `decision_id` → 404
  - [x] 2.4 다른 사용자 소유 decision(project.user_id 불일치) → 404
  - [x] 2.5 잘못된 `queue_timing` 값(예: `"tomorrow"`) → 422 (Pydantic `Literal` 검증, FastAPI 자동 처리 — 별도 코드 불필요, 테스트로만 확인)

### [Web] Queue 페이지

- [x] Task 3: `web/src/app/(app)/queue/page.tsx` 전면 교체 (현재 스텁 — Story 5.1 이전 placeholder) (AC: 1, 2, 3)
  - [x] 3.1 `home/page.tsx`와 동일한 Server Component 패턴: `createServerSupabaseClient()` → `supabase.auth.getUser()`로 `userId` 획득
  - [x] 3.2 `decisions` 조회: `.from("decisions").select("id, queue_timing, updated_at, reviews(signal_id, signals(title))").eq("choice", "queue").order("created_at", { ascending: true })` — `decisions`에는 `user_id`가 없으므로 필터링은 RLS(`decisions_select`, 3-hop `EXISTS`)에 위임한다(클라이언트 직접 조회이므로 anon key + 로그인 세션의 RLS가 자동 적용됨, AD-3/AD-9)
  - [x] 3.3 `user_profiles` 조회: `.from("user_profiles").select("daily_learning_time_min").eq("id", userId).maybeSingle()` — 예상 시간 값(신규 설계 결정, 아래 Dev Notes 참조). `daily_learning_time_min`이 `null`이면 기본값 30 사용
  - [x] 3.4 조회 결과를 `queue_timing`별로 그룹핑(`today`/`this_week`/`later` 순서 고정) + 각 항목에 `isOverdue` 플래그 계산(KST 날짜 비교, 아래 Dev Notes "재사용 패턴" 및 3.5 참조) 후 `QueueContent`에 props로 전달
  - [x] 3.5 KST 변환 헬퍼(`kstDateString(isoString: string): string`)를 이 파일 또는 `web/src/lib/kst.ts`(신규, 재사용 가능하도록) 중 선택 — 신규 유틸 파일 생성을 권장(History 탭 5.2에서도 KST 날짜 비교가 필요할 가능성이 높으므로, 단 이 스토리는 5.2를 구현하지 않는다): `new Date(new Date(iso).getTime() + 9*60*60*1000).toISOString().split("T")[0]` (Asia/Seoul은 DST 없는 고정 UTC+9 — NFR 한국 시장 한정)
  - [x] 3.6 `metadata`: `{ title: "큐 | Decision OS" }` (기존 페이지들과 동일 컨벤션)

- [x] Task 4: `web/src/components/queue/queue-content.tsx` 신규 (Client Component) (AC: 1, 3, 4)
  - [x] 4.1 `"use client"` — props: `groups: { today: QueueItemData[]; this_week: QueueItemData[]; later: QueueItemData[] }`, `estimatedMinutes: number`, `userId: string` (타입은 이 파일에서 정의, `QueueItemData = { decisionId: string; signalId: string; title: string; queueTiming: "today"|"this_week"|"later"; isOverdue: boolean }`)
  - [x] 4.2 로컬 state로 groups를 보유(낙관적 업데이트를 위해 서버에서 받은 초기값을 `useState`로 감싼다 — `daily-brief-content.tsx`가 `initialBrief`/`initialSignals`를 state로 감싸는 것과 동일 패턴)
  - [x] 4.3 그룹 순서(<span lang="en">Today</span> → <span lang="en">This Week</span> → <span lang="en">Later</span>) 순회하며 항목이 있는 그룹만 `<h2 className="text-section-title">` 헤딩 렌더링, 항목 없으면 전체 그룹 스킵. 모든 그룹이 비면 빈 상태 메시지(AC-1 문구 그대로) 렌더링
  - [x] 4.4 각 항목에 `QueueItem` 렌더링, `onReschedule` 콜백으로 해당 항목의 reschedule sheet를 열도록 상태 관리(현재 열려있는 `decisionId`를 state로 보유)
  - [x] 4.5 `handleReschedule(decisionId, newTiming)`: 낙관적으로 로컬 state의 해당 항목 `queueTiming`을 즉시 변경(그룹 간 이동 포함 — 새 그룹으로 옮기고 `isOverdue`는 `false`로 리셋) → `PATCH`을 `postDecisionPatch()` 헬퍼(context-sticky-bar.tsx의 `postDecision` 패턴을 그대로 모델로 삼아 `PATCH ${fastapiUrl}/api/v1/decisions/${decisionId}` 호출, body `{ queue_timing: newTiming }`)로 호출 → 실패 시 이전 groups 스냅샷으로 롤백 + 토스트("저장 중 오류가 발생했습니다. 다시 시도해 주세요." — 기존 문구 재사용)
  - [x] 4.6 항목 탭(reschedule 링크 영역 제외) 시 `router.push(`/queue/review/${signalId}`)` (AC-5, Task 6과 연결)

- [x] Task 5: `web/src/components/queue/queue-item.tsx` 신규 (Presentational) (AC: 2, 3)
  - [x] 5.1 Props: `title, queueTiming, estimatedMinutes, isOverdue, onTap, onReschedule`
  - [x] 5.2 **중첩 인터랙티브 요소 금지** — 바깥 컨테이너는 `<div>`(비인터랙티브), 그 안에 형제(sibling)로 (a) 메인 영역 `<button onClick={onTap}>`(배지+제목+시간+미완료배지+chevron 포함, `flex:1`) + (b) "일정 변경" `<button onClick={onReschedule}>` — `<button>` 안에 `<button>`을 넣지 않는다 (signal-card.tsx는 단일 `<button>`이었지만 QueueItem은 중첩 상호작용이 있어 그 패턴을 그대로 복제할 수 없음)
  - [x] 5.3 스타일: `min-height: 44px`, `background: var(--surface-card)`, `border-radius: var(--radius-card)`, `padding: var(--card-padding)` (signal-card.tsx 참조, 단 레이아웃은 세로 배치 — 배지 행 위, 제목/시간/링크 아래)
  - [x] 5.4 타이밍 배지: `.text-badge` 클래스(10px/700/uppercase) + `backgroundColor: var(--surface-card-alt)`, `color: var(--text-secondary)`, `<span lang="en">`로 <span lang="en">TODAY/THIS WEEK/LATER</span> 표기
  - [x] 5.5 미완료 배지: `isOverdue`일 때만 렌더링, `color: var(--status-warning)`, `background: transparent`(fill 없음), 텍스트 "미완료"
  - [x] 5.6 예상 시간: `.text-caption` 클래스 + `color: var(--text-tertiary)`, 텍스트 `약 {estimatedMinutes}분`
  - [x] 5.7 composite `aria-label`(메인 버튼): `` `${timingLabelEn} 예약됨, ${title}, 약 ${estimatedMinutes}분` `` (`timingLabelEn`은 <span lang="en">Today/This Week/Later</span> —배지 데이터 변환 매핑 함수 별도 작성)
  - [x] 5.8 "일정 변경" 버튼 `aria-label`: `` `일정 변경 — ${title}` ``, 텍스트는 시각적으로 "일정 변경"만 표시(12px/underline/`text-secondary`)

- [x] Task 6: `web/src/components/queue/reschedule-sheet.tsx` 신규 (Bottom Sheet) (AC: 4)
  - [x] 6.1 `context-sticky-bar.tsx`의 큐 <span lang="en">Bottom Sheet</span> 마크업(overlay + `role="dialog"` + `aria-modal="true"` + drag handle + `borderRadius: "24px 24px 0 0"`)을 그대로 재사용하되 **다음 차이점을 반드시 반영**:
    - 라벨은 한국어("오늘/이번 주/나중에")가 아니라 영어 `<span lang="en">Today</span>` / `<span lang="en">This Week</span>` / `<span lang="en">Later</span>` (AC-4, EXPERIENCE.md는 pill 라벨을 영어로 명시)
    - 현재 선택된 타이밍의 pill은 `border: "1.5px solid var(--accent-primary)"`로 강조(다른 pill은 기존과 동일한 `1px solid var(--border-subtle)`) — 선택 상태 표시는 신규 기능이며 원본 큐 결정 시트에는 없었다
    - `<textarea>` 메모 필드 **없음** — 일정 변경은 타이밍만 다룬다
  - [x] 6.2 Props: `currentTiming, onSelect(timing), onClose` — 부모(`queue-content.tsx`)가 낙관적 업데이트/PATCH 호출을 책임지므로 이 컴포넌트는 순수 UI + 선택 콜백만 담당
  - [x] 6.3 포커스 트랩 + `Escape` 닫힘 + 오버레이 클릭 닫힘은 `context-sticky-bar.tsx`의 기존 `useEffect` 키보드 트랩 로직을 참고해 동일하게 구현

- [x] Task 7: `web/src/app/(app)/queue/review/[signalId]/page.tsx` 신규 (AC: 5)
  - [x] 7.1 `web/src/app/(app)/home/review/[signalId]/page.tsx`를 **그대로 복제**(동일한 Supabase 조회 로직, 동일한 `ReviewPageContent` 사용) — 이 스토리는 신규 Research Review 렌더링 로직을 만들지 않고 기존 컴포넌트를 다른 URL에서 재사용한다
  - [x] 7.2 `metadata`도 동일하게 `{ title: "Research Review | Decision OS" }`
  - [x] 7.3 **알려진 갭(이 스토리 범위 밖, Dev Notes "절대 금지사항" 다음 섹션 참조)**: `ReviewPageContent` 내부의 `ContextStickyBar`/`ResearchReviewContent`는 뒤로가기·Chat·Learn Now 후속 이동을 `/home` 또는 `/home/review/...`로 하드코딩하고 있어, `/queue/review/...`로 진입해도 이후 내비게이션은 Home 경로로 빠진다. 이 스토리는 이 동작을 수정하지 않는다(AC-5는 최초 push까지만 요구).

- [x] Task 8: 웹 테스트 스펙 문서 추가 (AC: 1, 2, 3, 4) — 이 리포지토리는 Jest/Vitest 러너가 설정되어 있지 않다(`signal-card.test.tsx` 상단 주석 참조). 아래 파일들도 동일하게 **실행 불가능한 스펙 문서**로 작성하며, 파일 상단에 동일한 안내 주석(`// @ts-nocheck`, "테스트 러너 없이..." 문구)을 포함한다
  - [x] 8.1 `web/src/components/queue/__tests__/queue-item.test.tsx` — 배지 텍스트, 미완료 배지 조건부 렌더링, aria-label 조합, 메인 버튼/일정 변경 버튼 각각 독립적으로 클릭 이벤트 발생(중첩 아님을 검증)
  - [x] 8.2 `web/src/components/queue/__tests__/queue-content.test.tsx` — 그룹별 필터링/빈 그룹 숨김, 전체 빈 상태 메시지, 낙관적 업데이트 후 실패 시 롤백

### [Flutter] Queue 화면

- [x] Task 9: `mobile/lib/features/queue/providers/queue_provider.dart` 신규 (AC: 1, 2, 3, 4) — Riverpod `@riverpod` codegen 사용(`daily_brief_provider.dart`와 동일 컨벤션)
  - [x] 9.1 `QueueItemData` 클래스: `decisionId, signalId, title, queueTiming, updatedAt(DateTime), isOverdue(getter)` — `isOverdue`는 `queueTiming == 'today' && _kstDateStr(updatedAt).compareTo(_kstDateStr(DateTime.now())) < 0`(문자열 `yyyy-MM-dd` 포맷은 사전식 비교가 날짜 비교와 일치함)
  - [x] 9.2 **`QueueItems` 클래스 기반 Notifier로 구현 — 단순 `Future` 함수형 프로바이더가 아니다** (`daily_brief_provider.dart`의 `SeenSignalIds`(line 115-121)와 동일한 `@riverpod class X extends _$X` 컨벤션을 따르되 `build()`가 비동기라는 점만 다름). 낙관적 업데이트(AC-4)가 상태를 직접 변경해야 하므로 읽기 전용 `Future` 프로바이더로는 불충분하다:
    ```dart
    @riverpod
    class QueueItems extends _$QueueItems {
      @override
      Future<List<QueueItemData>> build() async {
        // 9.3의 쿼리 실행 후 List<QueueItemData> 반환
      }

      Future<void> reschedule(String decisionId, String newTiming) async {
        final previous = state;
        final current = state.valueOrNull ?? [];
        // 낙관적 업데이트: 해당 항목만 queueTiming 교체, updatedAt은 즉시 갱신하지 않는다(실서버 값과의 불일치는 다음 새로고침에서 자연 정정됨)
        state = AsyncData([
          for (final item in current)
            if (item.decisionId == decisionId)
              item.copyWith(queueTiming: newTiming)
            else
              item,
        ]);
        try {
          await _patchQueueTiming(decisionId, newTiming); // 9.6
        } catch (e) {
          state = previous; // 롤백
          rethrow; // 호출부(queue_screen.dart)가 catch하여 오류 SnackBar 표시
        }
      }
    }
    ```
  - [x] 9.3 `build()` 쿼리: `Supabase.instance.client.from('decisions').select('id, queue_timing, updated_at, reviews(signal_id, signals(title))').eq('choice', 'queue').order('created_at', ascending: true)` — `user_id` 필터 없음(RLS `decisions_select`가 처리, AD-9). `.stream()` 사용 금지 — nested embed(`reviews(signals(...))`) 미지원(`dailyBriefSignals`와 동일 이유)
  - [x] 9.4 `@riverpod Future<int> estimatedLearningMinutes(EstimatedLearningMinutesRef ref) async` — `user_profiles`에서 `daily_learning_time_min` 조회, `userId = Supabase.instance.client.auth.currentUser?.id`, null이면 기본값 `30` 반환 (Task 3.3과 동일 설계 결정). 이 프로바이더는 읽기 전용이므로 단순 함수형 `Future` 프로바이더 유지(9.2와 달리 클래스 불필요)
  - [x] 9.5 KST 변환 헬퍼는 이 파일 상단에 private 함수로 작성(`String _kstDateStr(DateTime dt)`) — `daily_brief_provider.dart`의 `_todayISO()`와 유사한 위치/스타일이나 KST 오프셋 보정 로직 추가
  - [x] 9.6 `_patchQueueTiming(String decisionId, String timing) async` private 함수를 이 파일에 작성 — `_DynamicContextStickyBar._postDecision`(research_review_screen.dart line 653-685)과 동일한 세션 토큰 조회/검증 구조를 따르되 `http.patch(Uri.parse('$fastapiUrl/api/v1/decisions/$decisionId'), headers: {...}, body: jsonEncode({'queue_timing': timing}))` 호출. `import 'package:http/http.dart' as http;` 추가 필요

- [x] Task 10: `mobile/lib/features/queue/widgets/queue_item.dart` 신규 (AC: 2, 3, 5)
  - [x] 10.1 `ListTile`과 동일한 원리로 구성: 바깥 `Row`(또는 `Column` + `Row`)에 (a) `Expanded(child: InkWell(onTap: onTap, child: 배지+제목+시간+chevron))` + (b) 형제 `TextButton(onPressed: onReschedule, child: Text('일정 변경'))` — **두 탭 영역이 서로 다른 위젯 트리 분기**(하나가 다른 하나의 자손이 아님)이어야 `onTap`/`onReschedule`이 서로 간섭하지 않는다(Flutter의 `ListTile(onTap:..., trailing: IconButton(onPressed:...))`와 동일한 검증된 패턴)
  - [x] 10.2 배지: `Container` + `BoxDecoration(color: AppColors.surfaceCardAlt, borderRadius: BorderRadius.circular(9999))`, 텍스트 색상 `AppColors.textSecondary`, 10px/uppercase/700
  - [x] 10.3 미완료 배지: `isOverdue`일 때만, 텍스트 색상 `AppColors.statusWarning`, 배경 없음
  - [x] 10.4 `minHeight: 44` 제약(`ConstrainedBox` 또는 `SizedBox`)
  - [x] 10.5 Semantics: EXPERIENCE.md line 695-703 스펙 그대로 — 메인 영역은 `Semantics(label: '$timingLabel 예약됨, $title, 약 ${estimatedMinutes}분', button: true, child: ExcludeSemantics(child: <시각적 콘텐츠>))`, 일정 변경 버튼은 별도 `Semantics(label: '일정 변경 — $title')`
  - [x] 10.6 `splashFactory: NoSplash.splashFactory` (UX-DR18 — 카드류에 잉크 스플래시 금지)

- [x] Task 11: `mobile/lib/features/queue/widgets/reschedule_sheet.dart` 신규 (AC: 4)
  - [x] 11.1 `research_review_screen.dart`의 `_showQueueBottomSheet`(라인 732-844)를 구조적 모델로 삼되 **다음을 반영**: 라벨을 `('Today', 'today')`, `('This Week', 'this_week')`, `('Later', 'later')`로 변경(원본은 `('오늘','today')` 등 한글), 메모 `TextField` 없음, `currentTiming`과 일치하는 옵션의 `OutlinedButton`에 `side: BorderSide(color: AppColors.accentPrimary, width: 1.5)` 적용(나머지는 기본 `OutlinedButton` 보더)
  - [x] 11.2 `showModalBottomSheet(shape: RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))), builder: ...)` — drag handle 수동 렌더링(36×4px, `#DDDDDD`, `Material`의 `DragHandle` 위젯 사용 금지, EXPERIENCE.md line 570)
  - [x] 11.3 옵션 탭 시 `HapticFeedback.mediumImpact()` 후 `Navigator.of(sheetContext).pop(selectedTiming)` — 실제 PATCH 호출/낙관적 업데이트는 호출부(`queue_screen.dart`)가 `showModalBottomSheet`의 반환값(`Future<String?>`)을 받아 처리(원본의 시트 내부에서 직접 API 호출하는 방식과 달리, 낙관적 업데이트 로직을 화면 레벨에서 관리하기 위함 — Task 12.4 참조)

- [x] Task 12: `mobile/lib/features/queue/screens/queue_screen.dart` 전면 교체 (현재 스텁) (AC: 1, 3, 4, 5)
  - [x] 12.1 `ConsumerWidget`으로 전환, `ref.watch(queueItemsProvider)` + `ref.watch(estimatedLearningMinutesProvider)` 각각 `.when(loading/error/data)` 처리
  - [x] 12.2 데이터를 `queue_timing`별로 그룹핑 후 <span lang="en">Today</span> → <span lang="en">This Week</span> → <span lang="en">Later</span> 순서로 섹션 헤딩(`Theme.of(context).textTheme.displayMedium`, 기존 `queue_screen.dart` 스텁의 "큐" 타이틀 스타일과 동일 텍스트 스타일 사용) + `QueueItem` 리스트 렌더링, 빈 그룹은 헤딩 자체를 생략
  - [x] 12.3 전체 빈 상태: AC-1 문구 그대로, 기존 `Theme.of(context).textTheme.bodyLarge` 스타일 재사용(현재 스텁의 안내 텍스트 스타일과 동일)
  - [x] 12.4 `onReschedule`: `showModalBottomSheet`로 `RescheduleSheet` 열고 반환값(선택된 타이밍 또는 `null`)을 받아 — `null`이 아니면 `await ref.read(queueItemsProvider.notifier).reschedule(decisionId, newTiming)`를 `try/catch`로 호출한다. 낙관적 갱신/PATCH 호출/실패 시 롤백은 모두 9.2의 `QueueItems.reschedule()` 내부 로직이 이미 처리하므로 이 태스크는 호출 + 실패 시 오류 `SnackBar` 표시만 담당한다(`catch (e) { ScaffoldMessenger.of(context).showSnackBar(...) }`)
  - [x] 12.5 항목 탭 시 `context.push('/queue/review/${item.signalId}')` (AC-5)

- [x] Task 13: `mobile/lib/core/router/app_router.dart` 수정 (AC: 5)
  - [x] 13.1 `/queue` `StatefulShellBranch`(현재 117줄, flat `GoRoute` 1개)를 Home 브랜치(81-112줄)와 동일한 구조로 확장: `GoRoute(path: '/queue', builder: (_, __) => const QueueScreen(), routes: [GoRoute(path: 'review/:signalId', builder: (_, state) => ResearchReviewScreen(signalId: state.pathParameters['signalId']!))])`
  - [x] 13.2 **Home 브랜치처럼 `learning-path`/`outcome`/`chat` 하위 라우트를 큐 브랜치에도 중복 추가하지 않는다** — `ResearchReviewScreen` 내부의 해당 이동(`context.push('/home/review/.../learning-path')` 등, `research_review_screen.dart` 라인 445, 692)은 여전히 `/home/...` 절대경로로 하드코딩되어 있으므로, 큐 브랜치 하위에 동일 이름의 라우트를 만들어도 실제로 도달하지 않는다(알려진 갭, 아래 Dev Notes 참조). 이 스토리는 그 하드코딩을 고치지 않는다 — AC-5는 최초 push까지만 요구
  - [x] 13.3 `ResearchReviewScreen`은 신규 위젯을 만들지 않고 기존 클래스를 그대로 재사용(import 추가만, `home_screen.dart`처럼 이미 `app_router.dart` 상단에 import되어 있음)

- [x] Task 14: `mobile/test/queue_test.dart` 신규 (AC: 1, 2, 3, 4, 5)
  - [x] 14.1 `QueueItem` 위젯: 배지 텍스트, 미완료 배지 조건부 렌더링, 메인 탭/일정 변경 탭이 서로 다른 콜백을 독립적으로 호출하는지(`tester.tap`으로 각각 검증)
  - [x] 14.2 `RescheduleSheet`: 현재 선택된 타이밍 옵션에 강조 보더 적용 여부, 옵션 탭 시 `Navigator.pop`으로 값 반환
  - [x] 14.3 그룹핑 로직(순수 함수로 분리했다면 유닛 테스트, 아니면 `QueueScreen` 위젯 테스트로 빈 그룹 헤딩 미표시 검증)
  - [x] 14.4 `navigation_shell_test.dart`의 `_buildTestRouter()` 패턴을 확장한 라우팅 테스트: `/queue`에서 QueueItem 탭 시 `/queue/review/:signalId`로 push되고 `BottomNavigationBar`가 여전히 큐 탭(index 1)을 가리키는지 검증(브랜치 스택 유지 확인)

### Review Findings

- [x] [Review][Decision] Composite aria-label에 영어 타이밍 단어가 한국어 문장에 그대로 삽입되어 한국어 스크린리더 오독 위험 — AC-2·EXPERIENCE.md(라인 625)가 정확히 이 포맷(`"${label} 예약됨, ..."`)을 명시하므로 구현은 스펙에 100% 부합함. **결정(2026-07-27, 사용자): 현상태 유지 — 스펙 그대로 둔다.** 코드 변경 없음. [web/src/components/queue/queue-item.tsx:25], [mobile/lib/features/queue/widgets/queue_item.dart:45]

- [x] [Review][Patch] 동시 재일정(reschedule) 경쟁 상태 — 실패 롤백이 전체 스냅샷을 복원하며 그사이 성공한 다른 항목의 낙관적 업데이트를 덮어씀 [web/src/components/queue/queue-content.tsx:67-87], [mobile/lib/features/queue/providers/queue_provider.dart:89-105]
- [x] [Review][Patch] AC-2("예상 시간 12px/text-secondary")와 Task 5.6("text-tertiary") 스펙 자체 모순 — 구현은 Task 5.6(오기)을 따라 두 플랫폼 모두 text-tertiary 사용, AC-2와 EXPERIENCE.md(라인 283, 디자인 소스)는 text-secondary 요구 [web/src/components/queue/queue-item.tsx:87], [mobile/lib/features/queue/widgets/queue_item.dart:93-95]
- [x] [Review][Patch] Flutter 재일정 실패 시 한국어 안내 문구 대신 원문 영어 예외 메시지("Decision update failed: 500")가 그대로 노출됨 — `e is Exception` 분기가 항상 참이 되어 폴백 한국어 문구가 죽은 코드가 됨 [mobile/lib/features/queue/screens/queue_screen.dart:28-34]
- [x] [Review][Patch] Web 오류 토스트에 자동 사라짐 타이머 누락 — 동일 스토리가 "기존 문구 재사용"을 지시한 context-sticky-bar.tsx의 3초 자동 dismiss 패턴을 복제하지 않아 Flutter의 3초 SnackBar와 불일치하며 무기한 유지됨 [web/src/components/queue/queue-content.tsx:55]
- [x] [Review][Patch] `QueueContent`의 `userId` prop이 선언·전달만 되고 컴포넌트 내부에서 전혀 사용되지 않는 죽은 코드 [web/src/components/queue/queue-content.tsx:22,51]

- [x] [Review][Defer] Web 큐 테스트 파일이 실행 불가능한 "테스트 스펙 문서"임(Jest/Vitest 미설정) [web/src/components/queue/__tests__/queue-item.test.tsx:1-6] — deferred, pre-existing (Epic 2부터 이어진 저장소 전역 컨벤션, 이번 스토리가 만든 문제 아님)
- [x] [Review][Defer] `isOverdue`가 `updated_at` 기반이라 DB 트리거가 무관한 갱신에도 값을 리셋시켜 미완료 판정에 영향을 줄 수 있음 [api/routers/decisions.py:182] — deferred, pre-existing (AC-3가 문자 그대로 요구하는 공식, 스펙 차원의 한계)
- [x] [Review][Defer] 미완료 판정이 플랫폼 간 다른 시계 기준 사용(Web: 서버 1회 계산 / Flutter: 기기 로컬 시계로 매 빌드 재계산) [mobile/lib/features/queue/providers/queue_provider.dart:24-26] — deferred, pre-existing (Dev Notes 라인 359에 문서화된 스펙 갭 결정에서 기인)
- [x] [Review][Defer] PATCH 엔드포인트의 UPDATE 쿼리 자체에 `choice='queue'` 가드가 없어 좁은 TOCTOU 윈도우 존재 [api/routers/decisions.py:183-188] — deferred, pre-existing (현재 choice를 변경하는 코드 경로가 없어 실질적으로 도달 불가능, 방어적 가드는 추후 검토)
- [x] [Review][Defer] 두 기기에서 동시 PATCH 시 last-write-wins, 충돌 감지 없음 [api/routers/decisions.py:183-188] — deferred, pre-existing (저위험 — 파괴적이지 않은 일정 선호도 변경)
- [x] [Review][Defer] `reviews.signal_id`가 nullable이라 이론적으로 `/queue/review/null` 내비게이션 가능 [web/src/app/(app)/queue/page.tsx:38] — deferred, pre-existing (실제 앱 플로우에서는 도달 불가능한 데이터 무결성 엣지 케이스)
- [x] [Review][Defer] 큐 목록 조회 쿼리에 페이지네이션/limit 없음 [web/src/app/(app)/queue/page.tsx:15-19] — deferred, pre-existing (현재 규모에서는 문제없음, 향후 헤비 유저 대응 시 검토)
- [x] [Review][Defer] `test_decisions.py`의 `_base_mock`이 `.eq()` 호출 인자를 검증하지 않아 필터 컬럼 회귀를 못 잡음 [api/tests/test_decisions.py:33-53] — deferred, pre-existing (Story 3.3부터 이어진 테스트 설계 패턴)

## Dev Notes

### 핵심 아키텍처 제약

- **AD-3 (데이터 접근 소유권)**: 큐 목록 **읽기**는 클라이언트가 Supabase SDK로 직접 조회한다(신규 API 엔드포인트 불필요) — 기존 `decisions_select` RLS 정책이 이미 이를 지원한다. **쓰기**(`queue_timing` 변경)는 반드시 FastAPI(service_role)를 경유한다 — 신규 `PATCH /api/v1/decisions/:id`. [Source: ARCHITECTURE-SPINE.md#AD-3]
- **AD-9 (RLS 패턴)**: `decisions`는 `user_id` 직접 컬럼이 없는 간접 소유 테이블 → `reviews`→`projects` 조인 `EXISTS` 서브쿼리 정책(`decisions_select`, 이미 존재, 아래 DB 스키마 참조). 신규 마이그레이션 불필요. [Source: ARCHITECTURE-SPINE.md#AD-9]
- **AD-5는 이 스토리에 적용되지 않음**: `decisions` 테이블에는 상태 컬럼이 없다(state machine 대상 아님) — `4-3-memory-manager.md`가 `memories`에 대해 내린 것과 동일한 판단.
- **UX-DR9 (4탭 내비게이션 + 브랜치 스택)**: Flutter는 `StatefulShellRoute.indexedStack`으로 탭별 독립 `Navigator` 스택을 가진다. AC-5의 "큐 탭 브랜치 스택 내 push"는 `/queue` 브랜치 아래 `review/:signalId` 중첩 `GoRoute`를 추가하는 것으로 충족된다(Home 브랜치의 기존 구조를 그대로 모델로 사용). Web(Next.js)에는 탭별 독립 스택 개념이 없지만, `/queue/review/:signalId`라는 **별도 URL**을 만들어 브라우저 뒤로가기가 `/queue`로 돌아가도록 한다 — EXPERIENCE.md가 이 경로를 플랫폼 공통 스펙으로 명시한다(line 103). [Source: EXPERIENCE.md line 95-103]
- **UX-DR18 (금지된 상호작용 패턴)**: FAB 없음, 캐러셀 없음, V1 드래그 재정렬 없음, 롱프레스 없음, `AlertDialog`/`showDialog` 대신 `showModalBottomSheet`만 사용, 카드류에 잉크 스플래시 없음(`NoSplash.splashFactory`). [Source: EXPERIENCE.md line 493-511]
- **WCAG 2.2 AA (UX-DR13)**: 최소 44×44 tap target, composite `aria-label`/Semantics, 색상 단독으로 정보 전달 금지(미완료 배지는 텍스트 "미완료" + 색상을 함께 사용 — 이미 충족).

### DB 스키마 — `decisions` 테이블 (기존 마이그레이션, 수정 없음 — 신규 마이그레이션 불필요)

```sql
-- _bmad-output/implementation-artifacts/db/001_initial_schema.sql (line 93-106)
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

-- RLS (line 302-308) — SELECT only, 쓰기는 FastAPI service_role만
CREATE POLICY "decisions_select" ON public.decisions FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.reviews r
        JOIN public.projects p ON p.id = r.project_id
        WHERE r.id = review_id AND p.user_id = auth.uid()
    ));

-- updated_at 자동 갱신 트리거 (line 386-388) — KST 미완료 판정의 핵심 근거
CREATE TRIGGER trg_decisions_updated_at
    BEFORE UPDATE ON public.decisions
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

`user_profiles.daily_learning_time_min`(line 19-32, `INTEGER` — `15 | 30 | 60`, nullable)도 이 스토리에서 읽기 전용으로 참조한다.

### 설계 결정 1: "예상 시간"의 데이터 소스 (스펙 갭)

epics.md/DESIGN.md/EXPERIENCE.md 어디에도 QueueItem의 "예상 시간(review + learning time)"이 어느 필드에서 오는지 명시되어 있지 않다(Signal 단위 예상 시간 필드는 스키마에 없음 — `signals` 테이블 전수 확인 완료). EXPERIENCE.md line 625의 aria-label 예시가 정확히 `"약 30분"`이고, 이는 `user_profiles.daily_learning_time_min`의 3개 허용값(15/30/60) 중 중앙값과 일치한다. **결정**: `user_profiles.daily_learning_time_min`을 모든 QueueItem에 동일하게 적용되는 예상 시간으로 사용한다(Signal별 개별 값이 아님). `null`이면 기본값 `30`(위 예시와 일치)을 사용한다. 이 값은 Story 5.1 범위에서 신규로 계산/저장하지 않고 온보딩(Story 1.5)에서 이미 수집된 기존 컬럼을 읽기만 한다.

### 설계 결정 2: "미완료(overdue)" 판정 알고리즘 (스펙 갭)

epics.md는 "자정이 지난 Today 항목"이라고만 서술하고 판정 메커니즘을 명시하지 않는다(비교 대상 컬럼이 명시되어 있지 않음 — `decisions`에 "스케줄된 날짜" 컬럼이 없다). **결정**: `decisions.updated_at`을 근거로 사용한다. `queue_timing='today'`로 결정이 저장되거나 재조정(reschedule)될 때마다 `trg_decisions_updated_at` 트리거가 `updated_at`을 현재 시각으로 갱신한다. 따라서 "`queue_timing == 'today'`이고 `updated_at`의 KST 날짜가 오늘의 KST 날짜보다 이전"이면 "자정이 지난 뒤에도 여전히 today로 남아있는 항목"으로 정확히 판정할 수 있다 — 별도 컬럼/마이그레이션 불필요. NFR상 한국 시장 전용이므로 Asia/Seoul(UTC+9, DST 없음) 고정 오프셋으로 충분하며 타임존 라이브러리 도입은 불필요하다(Web: 수동 UTC+9 밀리초 연산, Flutter: `DateTime.toUtc().add(Duration(hours: 9))`).

### 재사용 패턴 (그대로 따를 것)

- **`create_decision`** (`api/routers/decisions.py`, 신규 `update_decision`의 구조적 모델): Pydantic 요청 모델 + 소유권 검증(존재하지 않으면 404, "Review not found"/"Decision not found"로 존재 여부 비노출) + `.execute().data` empty-check → 403. PATCH는 decision_id로 시작해 review_id, project_id로 거슬러 올라가는 한 단계 더 긴 체인이라는 점만 다르다.
- **`postDecision` / `_postDecision`** (`context-sticky-bar.tsx` line 142-172 / `research_review_screen.dart` line 653-685): 세션 토큰 조회 → 없으면 사용자 메시지 후 throw → `fetch`/`http.post` 호출 → 실패 시 예외. 이 스토리의 PATCH 헬퍼(`postDecisionPatch`/`_patchQueueTiming`)는 동일 구조에서 HTTP 메서드와 URL(`/decisions/${id}` vs `/decisions`)만 다르다.
- **큐 결정 <span lang="en">Bottom Sheet</span>** (`context-sticky-bar.tsx` line 259-349 / `research_review_screen.dart` `_showQueueBottomSheet` line 732-844): overlay + drag handle + `RoundedRectangleBorder(top: 24)` + pill 버튼 3개. Task 6/11의 reschedule sheet가 이 마크업/위젯 트리를 그대로 재사용하되 라벨(영어)과 선택 상태 강조(신규)만 다르다.
- **`dailyBriefSignals`의 Future+nested-embed 패턴** (`daily_brief_provider.dart` line 77-113): `.select('a, b, rel(c, d)')` 형태의 nested embed는 **`Future` 기반 일회성 쿼리에서만 동작**한다(`.stream()`은 단일 테이블만 지원 — `dailyBriefStream`처럼). `queueItems` 프로바이더가 이 제약을 그대로 따른다.
- **`app_router.dart`의 Home 브랜치 중첩 라우트 구조** (line 81-112): `/queue` 브랜치에 `review/:signalId`를 추가할 때 그대로 모델로 삼는다.

### 기존 코드베이스 현황 (수정 대상 파일)

- `api/routers/decisions.py` (122줄, 전체 정독 완료) — 현재 `POST ""` 핸들러 1개만 존재. `PATCH "/{decision_id}"`를 같은 `router`(prefix `/decisions`)에 추가한다. `DecisionRequest`는 건드리지 않는다(신규 `DecisionUpdateRequest` 별도 정의). `api/main.py`는 이미 `decisions_router`를 `/api/v1` 프리픽스로 등록해 두었으므로 **수정 불필요**(같은 라우터에 메서드만 추가하는 것이므로 등록 로직은 그대로).
- `api/tests/test_decisions.py` (226줄, 전체 정독 완료) — 6개 기존 POST 테스트, `_make_token`/`_chain`/`_base_mock` 헬퍼 보유. `_base_mock`은 POST(review→project→decisions select+insert) 시나리오 전용이라 PATCH 테스트에는 맞지 않는다 — Task 2는 자체 `table_side_effect`를 작성한다(기존 3.5/3.6 테스트가 그렇게 하듯).
- `web/src/app/(app)/queue/page.tsx` (11줄, 전체 정독 완료) — 현재 "Story 5.1에서 구현 예정" 플레이스홀더. 전면 교체.
- `mobile/lib/features/queue/screens/queue_screen.dart` (31줄, 전체 정독 완료) — 동일한 플레이스홀더(`StatelessWidget`). `ConsumerWidget`으로 교체.
- `web/src/components/layout/bottom-nav.tsx` (78줄, 전체 정독 완료) — `/queue` 탭이 이미 4탭 내비게이션에 존재(`{ href: "/queue", label: "큐", icon: "📋" }`, `isActive`는 `pathname.startsWith(tab.href + "/")`로 `/queue/review/...`도 자동으로 큐 탭 활성화 처리됨). **변경 불필요.**
- `mobile/lib/core/router/app_router.dart` (134줄, 전체 정독 완료) — `/queue` 브랜치(115-118줄)는 현재 flat `GoRoute` 1개. Task 13에서 Home 브랜치(81-112줄)와 동일 구조로 확장.
- `mobile/lib/features/home/screens/research_review_screen.dart` (신규 생성 없음, 재사용만) — `ResearchReviewScreen(signalId: ...)` 생성자는 이미 `signalId` 하나만 받는 순수 위젯이라 큐 브랜치에서 그대로 재사용 가능. 단, 내부 이동 로직(아래 "알려진 갭" 참조)은 수정하지 않는다.
- `web/src/app/(app)/home/review/[signalId]/page.tsx` / `web/src/components/home/review/review-page-content.tsx` (각각 57줄/186줄, 전체 정독 완료) — `ReviewPageContent`는 `signalId, signalTitle, initialReview`만 props로 받는 순수 컴포넌트라 새 URL(`/queue/review/[signalId]/page.tsx`)에서 그대로 재사용 가능. 내부의 `ResearchReviewContent`/`ContextStickyBar`는 수정하지 않는다.

### 알려진 갭 — 큐 진입 후 Research Review 내부 내비게이션은 여전히 `/home`으로 하드코딩됨 (이 스토리 범위 밖)

`ResearchReviewScreen`/`ResearchReviewContent`/`ContextStickyBar`(Web) 내부의 후속 이동은 진입 경로와 무관하게 절대경로 `/home` 또는 `/home/review/...`로 하드코딩되어 있다:

- Flutter `research_review_screen.dart`: `context.go('/home')`(70, 172, 717, 814, 1018줄), `context.push('/home/review/${widget.review.signalId}/chat')`(445줄), `context.push('/home/review/${widget.signalId}/learning-path')`(692줄)
- Web `research-review-content.tsx`: `href="/home"`(107줄), `href={`/home/review/${signalId}/chat`}`(173줄); `context-sticky-bar.tsx`: `router.push('/home')`(219줄), `router.push('/home')`(Ignore, 194줄 경로)

즉, `/queue/review/:signalId`(또는 Flutter의 큐 브랜치 `review/:signalId`)로 진입한 뒤 Learn Now/Chat/Ignore/뒤로가기를 누르면 사용자는 큐 탭이 아니라 **Home 탭**으로 이동하게 된다. 이는 AC-5("QueueItem 탭 → Research Review 이동")의 요구사항 범위를 벗어난다 — AC-5는 최초 push 1회만 명시한다. **이 스토리는 이 하드코딩을 고치지 않는다.** 향후 스토리에서 "진입 브랜치를 기억해 이후 이동도 그 브랜치로 되돌린다"는 요구사항이 명시적으로 생기면 그때 `ResearchReviewScreen`/`ContextStickyBar`/`ResearchReviewContent`에 진입-브랜치 파라미터를 추가하는 별도 작업으로 다룬다.

### 범위 경계

| 항목 | 이 스토리 (5.1) | 이후 |
|------|----------------|------|
| 큐 목록 조회(그룹핑, 빈 상태) | ✅ | — |
| 미완료 배지(KST 기반) | ✅ | — |
| 일정 변경 Bottom Sheet + `PATCH /decisions/:id` | ✅ | — |
| QueueItem → Research Review 최초 push | ✅ | — |
| Research Review 내부 후속 이동의 브랜치 인지(Learn Now/Chat/뒤로가기가 큐로 복귀) | ❌ | 별도 스토리(알려진 갭 참조) |
| 큐 항목 드래그 재정렬 | ❌ | V2(UX-DR18 명시) |
| 큐 항목 스와이프 삭제/연기 | ❌ | V2(EXPERIENCE.md line 493) |
| Push 알림(미완료 리마인드 등) | ❌ | Story 5.3 |
| Memory 기반 개인화(예상 시간 개인화 등) | ❌ | Story 5.4 |
| `decisions`/`user_profiles` 신규 마이그레이션 | ❌ | 불필요 — 이미 존재 |

### 절대 금지사항

| 금지 | 이유 |
|------|------|
| `decisions`/`user_profiles` 관련 신규 DB 마이그레이션 추가 | 스키마·RLS·트리거 모두 이미 존재 |
| `queue_timing` 목록 조회용 신규 GET API 엔드포인트 추가 | AD-3 — 읽기는 클라이언트가 Supabase SDK로 직접 수행 |
| Flutter `queueItems` 프로바이더에 `.stream()` 사용 | nested embed(`reviews(signals(...))`) 미지원 — `Future` 프로바이더만 사용 |
| Web QueueItem을 단일 `<button>`으로 감싸 "일정 변경" 링크를 그 안에 중첩 | `<button>` 안 `<button>`은 유효하지 않은 HTML/접근성 위반 — 형제 요소로 분리 |
| 일정 변경 Bottom Sheet에 한국어 라벨("오늘/이번 주/나중에") 사용 | AC-4/EXPERIENCE.md가 영어 pill 라벨(`Today`/`This Week`/`Later`)을 명시 — Story 3.3의 원본 큐 결정 시트와 다름 |
| 일정 변경 Bottom Sheet에 메모 `TextField`/`textarea` 추가 | 일정 변경은 타이밍 전용, 메모는 최초 Decision 생성 시에만 |
| `showDialog`/`AlertDialog`로 일정 변경 UI 구현 | UX-DR18 — `showModalBottomSheet`만 허용 |
| 큐 항목에 드래그 재정렬/스와이프/롱프레스 인터랙션 추가 | UX-DR18 — V1에서 명시적으로 금지 |
| `ResearchReviewScreen`/`ContextStickyBar`/`ResearchReviewContent`의 하드코딩된 `/home` 이동을 이 스토리에서 "김에" 수정 | 알려진 갭으로 명시적으로 범위 밖 처리됨 — 컨벤션 불일치 방지, 별도 스토리로 |
| KST 변환에 타임존 라이브러리(`timezone`/`Intl` 고급 API 등) 도입 | Asia/Seoul은 DST 없는 고정 UTC+9 — 수동 오프셋 연산으로 충분, 불필요한 의존성 추가 금지 |

### 신규 / 수정 파일 목록

```
# API 수정 파일
api/routers/decisions.py                                  (UPDATE — PATCH /{decision_id} 추가)
api/tests/test_decisions.py                                (UPDATE — PATCH 테스트 5건 추가)

# Web 신규 파일
web/src/components/queue/queue-content.tsx                 (NEW)
web/src/components/queue/queue-item.tsx                    (NEW)
web/src/components/queue/reschedule-sheet.tsx               (NEW)
web/src/lib/kst.ts                                          (NEW — KST 날짜 변환 유틸)
web/src/app/(app)/queue/review/[signalId]/page.tsx          (NEW)
web/src/components/queue/__tests__/queue-item.test.tsx      (NEW — 스펙 문서)
web/src/components/queue/__tests__/queue-content.test.tsx   (NEW — 스펙 문서)

# Web 수정 파일
web/src/app/(app)/queue/page.tsx                            (UPDATE — 스텁 → 실제 구현)

# Flutter 신규 파일
mobile/lib/features/queue/providers/queue_provider.dart     (NEW)
mobile/lib/features/queue/widgets/queue_item.dart           (NEW)
mobile/lib/features/queue/widgets/reschedule_sheet.dart     (NEW)
mobile/test/queue_test.dart                                 (NEW)

# Flutter 수정 파일
mobile/lib/features/queue/screens/queue_screen.dart         (UPDATE — 스텁 → 실제 구현)
mobile/lib/core/router/app_router.dart                      (UPDATE — /queue 브랜치에 review/:signalId 중첩 라우트 추가)

# 변경 없음 (확인만)
web/src/components/layout/bottom-nav.tsx                    (이미 /queue 탭 존재, startsWith 매칭으로 하위 경로도 자동 활성화)
```

### References

- 에픽: `_bmad-output/planning-artifacts/epics.md` — Story 5.1 AC 원문(line 756-783), Epic 5 개요(line 752-754)
- 아키텍처: `ARCHITECTURE-SPINE.md` — AD-3(데이터 접근 소유권), AD-9(RLS 패턴), AD-5(이 스토리 미적용 이유는 위 Dev Notes 참조)
- UX: `ux-decision-os-2026-07-21/DESIGN.md` line 302-317(Queue Item 시각 스펙), `EXPERIENCE.md` line 95-103(브랜치/라우팅), line 274-291(Queue Item 행동 스펙), line 404-413(Queue States), line 479-511(Bottom Sheet/금지 패턴), line 601-705(접근성 — 44px tap target, aria-label/Semantics 스펙)
- DB 스키마: `_bmad-output/implementation-artifacts/db/001_initial_schema.sql` — `decisions`(line 93-106), `user_profiles`(line 19-32), `decisions_select` RLS(line 302-308), `trg_decisions_updated_at`(line 386-388)
- 재사용 패턴: `api/routers/decisions.py`(PATCH 구조 모델), `web/src/components/home/review/context-sticky-bar.tsx`(Bottom Sheet/postDecision 모델), `mobile/lib/features/home/screens/research_review_screen.dart`(Bottom Sheet/_postDecision 모델, 알려진 갭의 근거), `mobile/lib/features/home/providers/daily_brief_provider.dart`(Future vs Stream 프로바이더 패턴), `mobile/lib/core/router/app_router.dart`(중첩 라우트 구조 모델), `web/src/app/(app)/home/review/[signalId]/page.tsx` + `review-page-content.tsx`(Research Review 재사용 모델)
- 이전 스토리: `_bmad-output/implementation-artifacts/4-3-memory-manager.md` — 이 스토리 파일의 형식/컨벤션 모델(AC 서식, Dev Notes 구조, 스펙 갭 문서화 방식)

## Dev Agent Record

### Agent Model Used

Claude (dev-story 워크플로우 실행)

### Debug Log References

- API: `python3 -m pytest` 전체 132/132 통과(신규 PATCH 테스트 5건 포함, 회귀 없음).
- Web: `npx tsc --noEmit` 실행 결과 신규/수정 파일(큐 관련)에는 오류 없음. 단 스토리 범위 밖의 기존 파일 `web/src/app/(app)/home/review/[signalId]/chat/page.tsx`에서 사전 존재하는 무관한 타입 오류 1건 발견(`Property 'catch' does not exist on type 'PromiseLike<void>'`) — 이 스토리에서 생성/수정한 파일이 아니므로 수정하지 않음(범위 밖).
- Flutter: `flutter pub get` + `dart run build_runner build --delete-conflicting-outputs`로 `queue_provider.g.dart` 생성 성공. `flutter analyze lib/features/queue lib/core/router/app_router.dart` 이슈 0건. `flutter test test/queue_test.dart` 10/10 통과. `flutter test test/theme_test.dart test/widget_test.dart test/onboarding_test.dart test/auth_test.dart` 회귀 없이 전부 통과.
- Flutter: `test/navigation_shell_test.dart`(기존 파일, 이 스토리에서 미수정)를 포함한 일부 기존 테스트는 이 스토리와 무관한 사전 존재 이슈로 컴파일이 실패한다 — `mobile/lib/features/profile/screens/profile_screen.dart`가 `app_settings` 패키지 5.2.0(현재 lock 버전)에 없는 `AppSettings.openNotificationSettings()`를 호출하고 있어 해당 파일을 import하는 모든 테스트 파일의 컴파일이 깨진다. 이는 Story 5.1의 작업 범위(Queue 탭)와 무관하며 이 스토리에서 수정하지 않았다. `mobile/test/queue_test.dart`는 이 이슈를 우회하기 위해 프로필 탭을 플레이스홀더 `Scaffold`로 대체한 자체 테스트 라우터를 사용한다(파일 상단 주석 참조).

### Completion Notes List

- API `PATCH /api/v1/decisions/:id` 엔드포인트를 4-hop 소유권 검증(비즈니스 규칙 검증보다 먼저 소유권 확인)으로 구현, 기존 `create_decision` 컨벤션과 일치시킴.
- Web: `queue/page.tsx`(Server Component) → `queue-content.tsx`(Client, 낙관적 업데이트+롤백) → `queue-item.tsx`(Presentational, 중첩 버튼 없는 형제 구조) → `reschedule-sheet.tsx`(Bottom Sheet, 영어 라벨+선택 강조) 계층으로 구현. `/queue/review/[signalId]/page.tsx`는 기존 `ReviewPageContent`를 그대로 재사용(신규 렌더링 로직 없음).
- Flutter: `queue_provider.dart`에 `QueueItems`(클래스 기반 `AsyncNotifier`, `reschedule()` 낙관적 업데이트+실패 시 롤백) + `estimatedLearningMinutes`(단순 `Future` 프로바이더) 구현. `queue_item.dart`/`reschedule_sheet.dart` 위젯은 Web과 동일한 설계 결정(영어 pill 라벨, 형제 탭 영역, 미완료 배지 텍스트 전용)을 미러링. `app_router.dart`의 `/queue` 브랜치에 `review/:signalId` 중첩 라우트 추가(Home 브랜치와 동일 구조).
- 두 스펙 갭 설계 결정(예상 시간 = `user_profiles.daily_learning_time_min`, 기본값 30 / 미완료 판정 = `queue_timing='today'` && `updated_at` KST 날짜 비교)을 Web·Flutter 양쪽에 동일하게 적용.
- "알려진 갭"(Research Review 내부 이동이 여전히 `/home`으로 하드코딩됨)은 Dev Notes 지시대로 이 스토리에서 수정하지 않음.
- Web 테스트 2건(`queue-item.test.tsx`, `queue-content.test.tsx`)은 이 저장소 컨벤션에 따라 실행 불가능한 스펙 문서로 작성(Jest/Vitest 러너 미설정). Flutter 테스트(`queue_test.dart`)는 실제로 실행 가능하며 10/10 통과 확인.

### File List

```
# API 수정 파일
api/routers/decisions.py
api/tests/test_decisions.py

# Web 신규 파일
web/src/components/queue/queue-content.tsx
web/src/components/queue/queue-item.tsx
web/src/components/queue/reschedule-sheet.tsx
web/src/lib/kst.ts
web/src/app/(app)/queue/review/[signalId]/page.tsx
web/src/components/queue/__tests__/queue-item.test.tsx
web/src/components/queue/__tests__/queue-content.test.tsx

# Web 수정 파일
web/src/app/(app)/queue/page.tsx

# Flutter 신규 파일
mobile/lib/features/queue/providers/queue_provider.dart
mobile/lib/features/queue/providers/queue_provider.g.dart
mobile/lib/features/queue/widgets/queue_item.dart
mobile/lib/features/queue/widgets/reschedule_sheet.dart
mobile/test/queue_test.dart

# Flutter 수정 파일
mobile/lib/features/queue/screens/queue_screen.dart
mobile/lib/core/router/app_router.dart
```

## Change Log

| 날짜 | 변경 내용 |
|------|----------|
| 2026-07-27 | Story 5.1 생성 (create-story 워크플로우) — Epic 5 첫 스토리, epic-5 상태 backlog → in-progress. |
| 2026-07-27 | dev-story 실행 완료 — API PATCH 엔드포인트, Web Queue 탭(5개 신규 파일+1개 교체), Flutter Queue 화면(4개 신규 파일+2개 수정) 구현. 전체 ACs 충족, 모든 Task/Subtask 완료. Status: ready-for-dev → in-progress → review. |
