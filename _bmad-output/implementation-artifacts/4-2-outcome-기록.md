---
baseline_commit: NO_VCS
---

# Story 4.2: Outcome 기록

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

사용자로서,
학습 결과(Completed / Applied / Dropped / Not Useful)를 기록하고 선택적 피드백을 남길 수 있기를 원한다,
그래서 내 학습 이력이 누적되어 다음 추천의 질이 높아진다.

## Acceptance Criteria

**AC-1: Outcome 입력 화면 진입 및 기본 표시**
- **Given** 사용자가 Outcome 입력 화면(`/home/review/:signalId/outcome`)에 진입하면
- **Then** 화면 헤딩 "학습 결과를 기록해 주세요" (28px/700)가 표시된다
- **And** 어느 Signal에 대한 Outcome인지 Signal 제목 참조(13px/text-secondary)가 표시된다
- **And** 4개 OutcomeCard가 라디오 그룹으로 표시된다: Completed("학습을 완료했습니다") / Applied("실제 프로젝트에 적용했습니다") / Dropped("학습을 중단했습니다") / Not Useful("현재 상황에 맞지 않았습니다") — 이 고정 순서를 유지한다

**AC-2: OutcomeCard 선택 상태 (시각 + 접근성)**
- **Given** OutcomeCard의 선택 상태를 확인하면
- **Then** 선택된 카드: `accent-primary` 1.5px border (배경 fill 변경 없음, `surface-card` 유지)
- **And** 미선택 카드: `border-card` (#DCDCDC) 1px border
- **And** 라디오 그룹 ARIA(웹): `role="radiogroup"`, `aria-label="학습 결과를 선택해 주세요"`, 각 카드 `role="radio"` + `aria-checked="true/false"` + `aria-label="Completed — 학습을 완료했습니다"` 형태
- **And** Flutter 접근성: `Semantics(label: '학습 결과를 선택해 주세요', ...)`로 그룹을 감싸고 각 카드는 `Semantics(label: 'Completed — 학습을 완료했습니다', inMutuallyExclusiveGroup: true, checked: isSelected)`

**AC-3: Applied 선택 시 추가 입력 필드**
- **Given** 사용자가 "Applied"를 선택하면
- **Then** 선택 카드 아래에 추가 입력 필드가 나타난다: "어떤 프로젝트에 적용했나요? (선택)" 단일 라인 텍스트
- **And** 다른 옵션 선택 시 이 필드는 표시되지 않는다 (선택값도 전송하지 않음)

**AC-4: 선택적 피드백 필드**
- **Given** 선택적 피드백 필드를 확인하면
- **Then** 유용했는가 토글(예/아니오), 실제 학습 시간 입력(숫자+분), 메모 멀티라인 입력이 OutcomeCard 선택 여부와 무관하게 항상 표시된다 (필수 아님)

**AC-5: 기록하기 CTA — Outcome 저장**
- **Given** 사용자가 OutcomeCard 하나를 선택하고 "기록하기" CTA를 탭하면
- **Then** `POST /api/v1/outcomes`로 Outcome이 저장된다
- **And** `outcomes.status`: `completed | applied | dropped | not_useful` 중 선택값이 저장된다

**AC-6: 저장 완료 피드백**
- **Given** Outcome 저장이 성공하면
- **Then** 비차단 토스트 "결과가 기록됐습니다. 다음 Daily Brief에 반영됩니다." (3초)가 표시된다
- **And** 홈 화면으로 이동한다

## Tasks / Subtasks

### [API] Outcome 라우터

- [x] Task 1: `POST /api/v1/outcomes` 라우터 구현 (AC: 5)
  - [x] 1.1 `api/routers/outcomes.py` 신규 생성 — `OutcomeRequest` Pydantic 모델: `decision_id: str`, `status: Literal["completed","applied","dropped","not_useful"]`, `useful: bool | None = None`, `actual_learning_time_min: int | None = None`, `applied_project_note: str | None = None`, `memo: str | None = None`
  - [x] 1.2 `memo`, `applied_project_note`에 대해 blank string → `None` 변환 `field_validator` 추가 (`decisions.py`의 `blank_memo_to_none` 패턴 재사용)
  - [x] 1.3 `actual_learning_time_min`에 음수 거부 `field_validator` 추가 (`v is not None and v < 0` → `ValueError`)
  - [x] 1.4 비즈니스 검증: `status in ("completed", "applied")`이고 `useful is None`이면 422 반환 — DB `chk_useful_required` 제약과 동일 규칙을 API 레이어에서 선제 검증해 원인 불명확한 500을 방지 (Dev Notes "스펙 갈등: useful 필수 여부" 참조)
  - [x] 1.5 소유권 검증 체인 (`decisions.py` 패턴과 동일한 3-hop): `decision_id` → `decisions.review_id` 조회 → `reviews.project_id` 조회 → `projects`에서 `id=project_id AND user_id=user_id` 확인. 어느 단계든 empty면 404
  - [x] 1.6 멱등성: `decision_id`로 기존 `outcomes` row `select` → 존재하면 기존 `outcome_id`를 그대로 반환 (INSERT 스킵). (Dev Notes "멱등성 설계" 참조 — `outcomes` 테이블에는 `UNIQUE(decision_id)` 제약이 없으므로 앱 레벨 체크로만 보장됨)
  - [x] 1.7 INSERT 수행 + race-condition 폴백: INSERT가 예외를 던지면 재조회 후 기존 row 반환, 그래도 없으면 500 (`decisions.py`의 try/except 패턴과 동일)
  - [x] 1.8 INSERT 결과가 empty면 403 (RLS 또는 DB 제약 거부)
  - [x] 1.9 201 + `APIResponse(data={"outcome_id": ...})` 반환
- [x] Task 2: `main.py`에 라우터 등록 (AC: 5)
  - [x] 2.1 `from routers.outcomes import router as outcomes_router` 추가
  - [x] 2.2 `app.include_router(outcomes_router, prefix="/api/v1")` 추가 (기존 라우터 등록 블록 마지막 줄 다음에 추가)
- [x] Task 3: 테스트 작성 (AC: 5)
  - [x] 3.1 `api/tests/test_outcomes.py` 신규 생성 — `test_decisions.py`의 mock 패턴(`_chain()`, `table_side_effect` 기반 `_base_mock`)을 그대로 재사용. **실제 Supabase 테스트 DB에 연결하지 않는다** (Dev Notes "AD-11 적용 방식" 참조 — 이 라우터는 LLM/BackgroundTask가 없는 단순 CRUD이므로 `test_decisions.py`와 동일하게 완전 모킹)
  - [x] 3.2 `completed` + `useful=true` → 201, `outcome_id` 반환 검증
  - [x] 3.3 `applied` + `useful=true` + `applied_project_note` → 201
  - [x] 3.4 `dropped` (`useful` 없음) → 201
  - [x] 3.5 `not_useful` (`useful` 없음) → 201
  - [x] 3.6 `completed` + `useful` 없음 → 422
  - [x] 3.7 다른 사용자 소유의 `decision_id` → 404
  - [x] 3.8 동일 `decision_id` 중복 요청 → 기존 `outcome_id` 반환 + INSERT 미호출 검증 (`test_decisions.py`의 `test_duplicate_decision_returns_existing_decision_id` 패턴)

### [WEB] Outcome 화면 구현

- [x] Task 4: OutcomeCard 컴포넌트 (AC: 1, 2)
  - [x] 4.1 `web/src/components/home/outcome/outcome-card.tsx` 신규 생성 — 4개 고정 옵션(Completed/Applied/Dropped/Not Useful) prop으로 받는 라디오 카드. `role="radio"` + `aria-checked` + `aria-label="{English 상태명} — {한글 설명}"` 형태
  - [x] 4.2 시각 스펙(DESIGN.md): `border-radius: 14px`, `padding: 16px`, `min-height: 52px`, 배경 `var(--surface-card)` 고정, 선택 시 `border: 1.5px solid var(--accent-primary)` / 미선택 `border: 1px solid var(--border-card)` — 배경은 선택 여부와 무관하게 동일 (fill 변경 금지)
- [x] Task 5: Outcome 화면 페이지 구현 (AC: 1, 3, 4, 5, 6)
  - [x] 5.1 `web/src/app/(app)/home/review/[signalId]/outcome/page.tsx`의 placeholder를 실제 구현으로 교체 (`params: Promise<{signalId: string}>`, `use(params)`로 unwrap)
  - [x] 5.2 `signalId` → `decision_id` 조회: `reviews`에서 `signal_id` eq + `status=completed` → `decisions`에서 `review_id` eq + `choice=learn_now` (`learning-path/page.tsx`의 `resolveAndStart` 앞부분 2단계와 동일한 쿼리 체인 재사용). 둘 중 하나라도 없으면 에러 상태(예: 홈으로 리다이렉트 또는 에러 메시지 — 이 화면은 항상 유효한 진입 경로에서만 라우팅되므로 방어적 처리만 필요, 별도 재시도 UI는 AC 범위 밖)
  - [x] 5.3 헤딩 "학습 결과를 기록해 주세요" (28px/700) + Signal 제목 참조(13px/text-secondary) — `learning-path/page.tsx`의 헤더용 제목 조회 `useEffect`(line 30-44, `supabase.from("signals").select("title").eq("id", signalId)`)와 동일 패턴 재사용
  - [x] 5.4 4개 OutcomeCard를 `role="radiogroup"` `aria-label="학습 결과를 선택해 주세요"` 컨테이너로 감싸 렌더링, 클릭 시 선택 상태 갱신
  - [x] 5.5 "Applied" 선택 시에만 추가 입력 필드("어떤 프로젝트에 적용했나요? (선택)") 조건부 렌더링, state로 관리
  - [x] 5.6 선택적 피드백 필드 항상 표시 (OutcomeCard 선택 여부 무관):
    - 유용했는가: pill 버튼 2개("예"/"아니오") — `context-sticky-bar.tsx`의 Queue timing pill 버튼 시각 스타일 재사용(`min-height:44px`, `border-radius:9999px`). **기본값 `true`("예") 사전 선택** (Dev Notes "스펙 갈등: useful 필수 여부" 참조)
    - 실제 학습 시간: `<input type="number" min="0">` + "분" 단위 라벨
    - 메모: `<textarea>` 멀티라인, placeholder "적용 방식, 막힌 부분, 다음 단계 등을 남겨두세요"
  - [x] 5.7 "기록하기" CTA (전체 너비 pill, `accent-primary` 배경) — OutcomeCard 미선택 시 비활성화. 탭 시 `POST /api/v1/outcomes`에 `decision_id`, `status`, `useful`, `actual_learning_time_min`(입력값 있을 때만 정수 변환), `applied_project_note`(Applied 선택 시에만), `memo` 전송. JWT는 `context-sticky-bar.tsx`의 `postDecision` fetch 패턴(`Authorization: Bearer {token}`) 재사용
  - [x] 5.8 성공 시: 비차단 토스트("결과가 기록됐습니다. 다음 Daily Brief에 반영됩니다.", `role="status" aria-live="assertive"`) 표시 → 1.5초 지연 후 `router.push("/home")` (`context-sticky-bar.tsx`의 `handleIgnore` 패턴과 동일 — 토스트가 눈에 보인 후 이동)
  - [x] 5.9 `isSubmitting` state로 중복 제출 방지, 실패 시 에러 토스트("오류가 발생했습니다. 다시 시도해 주세요.") + `isSubmitting` 즉시 해제

### [FLUTTER] Outcome 화면 구현

- [x] Task 6: Outcome Provider (AC: 5)
  - [x] 6.1 `mobile/lib/features/home/providers/outcome_provider.dart` 신규 생성 — `@riverpod` 클래스 기반 Notifier(`learning_path_provider.dart`의 `LearningPathController` 클래스 기반 패턴과 일관되게, AD-14 준수). `build(signalId)`에서 `reviews`(signal_id + status=completed) → `decisions`(review_id + choice=learn_now) 2단계 조회로 `decision_id` 확보 (learning_path_provider.dart의 `build()` 앞부분과 동일)
  - [x] 6.2 `submitOutcome({status, useful, actualLearningTimeMin, appliedProjectNote, memo})` 메서드 — `http.post`로 `POST /api/v1/outcomes` 호출, JWT는 `Supabase.instance.client.auth.currentSession`에서 획득, URL은 `String.fromEnvironment('FASTAPI_URL', defaultValue: 'http://localhost:8000')` (`_triggerLearningPath` 패턴과 동일)
  - [x] 6.3 `flutter pub run build_runner build --delete-conflicting-outputs`로 `outcome_provider.g.dart` 생성
- [x] Task 7: OutcomeScreen 구현 (AC: 1, 2, 3, 4, 5, 6)
  - [x] 7.1 `mobile/lib/features/home/screens/outcome_screen.dart` 신규 생성 (`ConsumerStatefulWidget`). 헤더의 Signal 제목은 `learning_path_screen.dart`의 `_headerTitle()`(line 56-63)과 동일하게 `reviewStateProvider(signalId)`를 watch해 `ReviewCompleted` 상태의 `review.signalTitle`을 사용 (이 화면은 Learning Path 화면을 거쳐야만 도달하므로 해당 provider는 이미 데이터를 보유하고 있음)
  - [x] 7.2 OutcomeCard 위젯: `onboarding_screen.dart`의 `_OptionCard` 시각 스펙(14px radius / 52px minHeight / border-only selected, `AppColors.surfaceCard` 고정 배경) 재사용 + `Semantics(label: '{English} — {한글}', inMutuallyExclusiveGroup: true, checked: isSelected)` 접근성 래핑 (EXPERIENCE.md 라인 677-691 코드 예시 그대로 적용)
  - [x] 7.3 "Applied" 선택 시 추가 `TextField`("어떤 프로젝트에 적용했나요? (선택)") 조건부 표시
  - [x] 7.4 유용했는가 토글(두 개 버튼, 기본 선택 "예"=true), 실제 학습 시간 숫자 `TextField`(`TextInputType.number`), 메모 멀티라인 `TextField` — 항상 표시
  - [x] 7.5 "기록하기" `ElevatedButton` (`AppColors.accentPrimary` 배경, OutcomeCard 미선택 시 `onPressed: null`) — 탭 시 `HapticFeedback.mediumImpact()` 호출 (EXPERIENCE.md 라인 560 명시) 후 `submitOutcome()` 호출
  - [x] 7.6 제출 성공 시: `ScaffoldMessenger.of(context).showSnackBar` 로 "결과가 기록됐습니다. 다음 Daily Brief에 반영됩니다." (`Duration(seconds: 3)`) 표시 → 약 1.5초 지연 후 `context.go('/home')` (웹과 동일 취지)
  - [x] 7.7 제출 실패 시 에러 SnackBar + 재시도 가능하도록 버튼 재활성화
- [x] Task 8: 라우터 연결 (AC: 1)
  - [x] 8.1 `mobile/lib/core/router/app_router.dart`에서 `_OutcomePlaceholderScreen` 클래스 삭제, `outcome` GoRoute의 `builder`를 `OutcomeScreen(signalId: state.pathParameters['signalId']!)`로 교체
  - [x] 8.2 `import '../../features/home/screens/outcome_screen.dart';` 추가

### Review Findings

- [x] [Review][Patch] Flutter: Outcome 제출이 첫 탭에서 거의 항상 실패함 — `outcome_screen.dart`가 `outcomeControllerProvider`를 어디에서도 watch/read하지 않아 provider가 lazy 상태로 남아있다가, `_handleSubmit`에서 `.notifier`로 처음 접근하는 순간 `build()`가 시작된다. `submitOutcome()`은 이 비동기 조회가 끝나기 전에 `state.valueOrNull`을 동기적으로 읽어 `decisionId == null`이면 즉시 `false`를 반환한다. [mobile/lib/features/home/providers/outcome_provider.dart:42-43, mobile/lib/features/home/screens/outcome_screen.dart] — fixed: `state.valueOrNull` 대신 `await future`로 build() 완료를 보장하도록 변경
- [x] [Review][Patch] Web: 제출 성공 시 `isSubmitting`을 즉시 `false`로 되돌린 뒤 1.5초 지연 후 네비게이션 — 그 사이 "기록하기" 버튼이 재활성화되어 중복 POST가 가능하다(백엔드 멱등성으로 실제 피해는 없으나 Task 5.9의 "중복 제출 방지" 의도 및 Flutter 구현과 불일치). [web/src/app/(app)/home/review/[signalId]/outcome/page.tsx:113-115] — fixed: 성공 경로에서 `setIsSubmitting(false)` 제거 (실패 경로에서만 해제)
- [x] [Review][Patch] Web: "기록하기" 버튼의 `disabled` 조건에 `!decisionId`가 빠져 있어, `signalId → decision_id` 조회가 끝나기 전에 탭하면 `handleSubmit`이 조용히 no-op되고 아무 피드백도 없다. [web/src/app/(app)/home/review/[signalId]/outcome/page.tsx:83,254] — fixed: `disabled`/배경/커서 조건에 `!decisionId` 추가
- [x] [Review][Patch] API: `actual_learning_time_min`에 상한 검증이 없고 `memo`/`applied_project_note`에 길이 제한이 없다 — 매우 큰 정수는 Postgres int4 범위를 초과해 처리되지 않은 500을 유발할 수 있다. [api/routers/outcomes.py:28-33,13-19] — fixed: 상한 100,000분 검증 추가, `memo` max_length=2000, `applied_project_note` max_length=500
- [x] [Review][Patch] Mobile: `submitOutcome`의 `http.post` 호출에 timeout이 없어 네트워크가 멈추면 `_isSubmitting`이 영구히 `true`로 남고 사용자가 복구할 방법이 없다. [mobile/lib/features/home/providers/outcome_provider.dart:52-66] — fixed: `.timeout(Duration(seconds: 15))` 추가
- [x] [Review][Patch] API 테스트: 음수 `actual_learning_time_min`(422), blank-string→None 변환, race-condition INSERT 폴백 분기에 대한 테스트가 없음. 사용하지 않는 `pytest` import도 존재. [api/tests/test_outcomes.py] — fixed: 3개 테스트 추가(10 passed), 미사용 import 제거
- [x] [Review][Patch] Mobile: `submitOutcome`의 `catch (_) { return false; }`가 모든 에러 정보를 버려 네트워크/검증/인증 실패를 구분할 수 없다 (프로덕션 디버깅 어려움). [mobile/lib/features/home/providers/outcome_provider.dart:68-69] — fixed: `catch (e)` + `debugPrint`로 에러 로깅
- [x] [Review][Patch] Mobile: 토큰이 비어있을 때 명시적 체크 없이 요청을 보냄 (Web은 "세션 만료" 전용 메시지가 있음) — 만료된 세션에서 범용 에러 토스트만 표시됨. [mobile/lib/features/home/providers/outcome_provider.dart:46-47] — fixed: 토큰 비어있으면 요청 전 즉시 반환
- [x] [Review][Defer] `outcomes.decision_id`에 DB unique 제약 없음 — 동시 요청 시 이론상 중복 row 가능. Dev Notes "스펙 갈등 2"에서 이미 스코프 밖으로 명시적 합의됨. [api/routers/outcomes.py] — deferred, pre-existing (spec-accepted tradeoff)
- [x] [Review][Defer] INSERT 주변의 광범위한 `except Exception` + empty-data 시 403 처리 (supabase-py는 보통 빈 리스트 대신 예외를 던지므로 이 분기는 도달 불가능할 수 있음) — Dev Notes 지시대로 이미 승인된 `decisions.py` 패턴을 그대로 재사용한 것. [api/routers/outcomes.py:99-133, api/routers/decisions.py] — deferred, pre-existing pattern shared with decisions.py
- [x] [Review][Defer] `decision_id`에 UUID 형식 검증 없음 — 잘못된 값이 처리되지 않은 500으로 노출됨. `decisions.py`의 `review_id`에도 동일한 기존 갭 존재. [api/routers/outcomes.py:14, api/routers/decisions.py:13] — deferred, pre-existing pattern shared with decisions.py
- [x] [Review][Defer] `main.py`의 lifespan Supabase 헬스체크가 실패를 삼키고 그냥 부팅함, CORS가 `allow_credentials=True` + wildcard methods/headers로 설정됨, APScheduler `.start()`가 unhandled — 모두 이 스토리가 건드리지 않은 기존 코드(`outcomes_router` 등록 한 줄만 신규). [api/main.py] — deferred, pre-existing
- [x] [Review][Defer] Web/Mobile의 Supabase 조회가 일시적 에러와 "not found"를 구분하지 않고 둘 다 `/home`으로 리다이렉트함 — `learning-path/page.tsx`에서 재사용한 기존 패턴, 이 스토리 범위를 넘는 프로젝트 전역 컨벤션. [web/.../outcome/page.tsx, mobile/.../outcome_provider.dart] — deferred, pre-existing pattern

## Dev Notes

### 핵심 아키텍처 제약

- **AD-3 (데이터 접근 소유권)**: `outcomes` 테이블 INSERT는 FastAPI(service_role)만 수행. 클라이언트(웹/Flutter)는 절대 `outcomes`에 직접 INSERT하지 않는다. 읽기는 Supabase 직접(RLS+anon key+JWT) 허용되지만, 이 스토리는 쓰기(Outcome 기록)가 핵심이므로 API 경유가 필수. [Source: ARCHITECTURE-SPINE.md#AD-3, line 30-33]
- **AD-9 (RLS 구현 패턴)**: `outcomes`는 `user_id` 직접 컬럼이 없는 project 경유 테이블이므로 `decision_id → review_id → project_id → user_id` 서브쿼리 방식 RLS(`outcomes_select` 정책)를 따른다. API 라우터의 소유권 검증 로직도 이 체인을 그대로 반영해야 한다 (Task 1.5). [Source: ARCHITECTURE-SPINE.md#AD-9, line 231-234]
- **AD-11 (테스트 전략) 적용 방식**: 원칙적으로 "비즈니스 로직"은 실제 Supabase 테스트 DB 연결이 명시되어 있으나, 이 스토리의 `outcomes.py`는 `decisions.py`와 동일하게 LLM/BackgroundTask가 전혀 없는 단순 동기 CRUD 라우터다. 이미 "done"으로 승인된 `test_decisions.py`가 Supabase 클라이언트를 완전히 모킹하는 방식으로 검증되었으므로, `test_outcomes.py`도 동일한 모킹 패턴을 따른다 (Task 3.1). 실제 DB 연결 필요한 대상은 파이프라인이 있는 경우(예: Story 4.3 Memory Manager)로 한정. [Source: ARCHITECTURE-SPINE.md#AD-11, line 245-248; api/tests/test_decisions.py]
- **AD-13 (API 계약)**: 응답 봉투 `{"data": ..., "error": null|{"code","message"}}` (`core/schemas.py`의 `APIResponse`), 인증 `Authorization: Bearer {JWT}`, 기본 경로 `/api/v1/`. [Source: ARCHITECTURE-SPINE.md#AD-13, line 259-262]

### DB 스키마 — `outcomes` 테이블 (기존 마이그레이션, 수정 없음)

```sql
-- supabase/migrations/20260723000000_initial_schema.sql (line 110-124)
CREATE TABLE IF NOT EXISTS public.outcomes (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id             UUID NOT NULL REFERENCES public.decisions(id) ON DELETE CASCADE,
    status                  TEXT NOT NULL
                                CHECK (status IN ('completed', 'applied', 'dropped', 'not_useful')),
    useful                  BOOLEAN,
    actual_learning_time_min INTEGER,
    applied_project_note    TEXT,   -- Applied 선택 시 프로젝트 메모
    memo                    TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_useful_required CHECK (
        status NOT IN ('completed', 'applied') OR useful IS NOT NULL
    )
);

-- RLS (line 324-330) — SELECT only, 쓰기는 FastAPI service_role만
CREATE POLICY "outcomes_select" ON public.outcomes FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.decisions d
        JOIN public.reviews r ON r.id = d.review_id
        JOIN public.projects p ON p.id = r.project_id
        WHERE d.id = decision_id AND p.user_id = auth.uid()
    ));
```

- 인덱스: `idx_outcomes_decision_id` 존재 (unique 아님 — 아래 "멱등성 설계" 참조)
- 이 스토리는 신규 마이그레이션이 필요 없다. 스키마는 이미 존재한다.

### 스펙 갈등 1: `useful` 필수 여부 (해결됨 — 반드시 이 방식으로 구현)

DB 제약 `chk_useful_required`는 `status IN ('completed','applied')`일 때 `useful IS NOT NULL`을 요구하지만, `EXPERIENCE.md` (line 309)는 유용했는가 토글을 "선택적 피드백 필드... 항상 표시되지만 필수 아님"으로 명시한다. 이 둘은 문자 그대로는 충돌한다.

**해결 방식**: 웹/Flutter 모두 유용했는가 토글의 **기본 선택값을 "예"(`true`)로 사전 설정**한다. 사용자가 토글을 건드리지 않아도 `useful=true`가 항상 전송되므로, UI 상으로는 "터치 불필요(=필수 아님)"를 만족하면서 DB 제약도 자동으로 충족한다. `dropped`/`not_useful` 선택 시에도 토글 값은 그대로 전송해도 무방하다(제약이 요구하지 않을 뿐 금지하지도 않음 — Memory 개인화에 참고 가능). API 레이어(Task 1.4)는 그럼에도 `completed`/`applied` + `useful=None` 조합을 422로 방어한다 (클라이언트 버그나 기본값 로직 누락에 대한 방어선).

### 스펙 갈등 2: 멱등성 설계 (해결됨 — 반드시 이 방식으로 구현)

`decisions` 테이블은 `UNIQUE(review_id)` 제약이 있어 `decisions.py`가 DB 레벨 멱등성 보장 위에서 동작하지만, `outcomes` 테이블에는 `UNIQUE(decision_id)` 제약이 없다(`idx_outcomes_decision_id`는 일반 인덱스일 뿐). AC 문서에도 "동일 decision에 대한 재기록" 시나리오가 명시되어 있지 않다.

**해결 방식**: 이 스토리는 신규 마이그레이션을 추가하지 않는다(스코프 밖). 대신 `decisions.py`/`learning_paths.py`와 동일한 **애플리케이션 레벨 체크-후-삽입(check-existing-then-insert)** 패턴으로 멱등성을 보장한다(Task 1.6, 1.7). 동시 요청(TOCTOU) 경합은 완벽히 차단되지 않지만(DB 유니크 제약이 없으므로), `decisions.py`가 이미 이 수준의 보장으로 review 승인을 받았으므로 동일 기준을 적용한다. 향후 DB 유니크 제약이 필요하다고 판단되면 별도 스토리/마이그레이션에서 다룬다.

### 스펙 갭: OutcomeCard 화면 표시 텍스트 (해결됨 — 반드시 이 방식으로 구현)

`EXPERIENCE.md`/`DESIGN.md`는 네 옵션을 "Completed — '학습을 완료했습니다'" 형태로 표기하지만, 이는 스펙 문서의 내부 식별용 표기이지 카드에 두 텍스트를 나란히 렌더링하라는 뜻이 아니다. `LearningPathCard`가 내부 enum `official_docs`는 코드/타입에만 쓰고 화면에는 한글 라벨 "공식 문서"만 표시하는 것과 동일한 컨벤션을 따른다: **OutcomeCard 화면에는 한글 문구("학습을 완료했습니다" 등)만 표시**하고, 영문 상태명("Completed" 등)은 `status` enum 값 및 `aria-label` 문자열 내부에서만 사용한다. 영문을 카드에 시각적으로 병기하지 않는다.

### 스펙 갭: Toggle 컴포넌트 시각 스펙 부재

`DESIGN.md`에는 "Toggle"/"Switch" 컴포넌트에 대한 전용 시각 스펙이 존재하지 않는다(전수 검색 확인). 유용했는가 예/아니오 토글은 `context-sticky-bar.tsx`의 Queue timing pill 버튼(웹: `min-height:44px`, `border-radius:9999px`, `border:1px solid var(--border-subtle)`, 선택 시 배경/보더 반전) 시각 스타일을 재사용한다. Flutter는 동등한 두 개의 pill 버튼(선택 시 `AppColors.accentPrimary` 배경 채움)으로 구현한다. 전용 스펙이 아니므로 신규 디자인 토큰을 만들지 않는다.

### 기존 코드베이스 현황 (수정 대상 파일)

- `web/src/app/(app)/home/review/[signalId]/outcome/page.tsx` — 현재 7줄 placeholder(`"Outcome 기록 화면은 Story 4.2에서 구현됩니다."`). Story 4.1에서 라우트만 생성되었다. 전체 교체 대상.
- `mobile/lib/core/router/app_router.dart` — `_OutcomePlaceholderScreen`(line 134-150)이 `outcome` GoRoute(line 96-101)에 연결되어 있다. `OutcomeScreen`으로 교체하고 placeholder 클래스는 삭제한다. **주의**: `HomeScreen`, `ResearchReviewScreen`, `LearningPathScreen`, `ContextualChatScreen` 등 형제 라우트는 이 스토리에서 건드리지 않는다.
- `api/main.py` — 라우터 등록 블록(line 93-101)에 `outcomes_router`를 마지막 줄로 추가. 다른 라우터 등록 순서/lifespan 로직은 변경하지 않는다.

### Web: signalId → decision_id 조회 흐름 (재사용 패턴)

`learning-path/page.tsx`의 `resolveAndStart` 함수 앞부분(line 143-170)이 정확히 동일한 조회가 필요하다:
```ts
const { data: reviewRow } = await supabase.from("reviews").select("id")
  .eq("signal_id", signalId).eq("status", "completed").limit(1).maybeSingle();
const { data: decisionRow } = await supabase.from("decisions").select("id")
  .eq("review_id", reviewRow.id).eq("choice", "learn_now").limit(1).maybeSingle();
```
Outcome 화면은 `learning_paths` 조회/트리거/Realtime 구독이 필요 없으므로 그 이후 로직은 가져오지 않는다.

### Flutter: 접근성 코드 패턴 (EXPERIENCE.md 그대로 적용)

```dart
Semantics(
  label: '학습 결과를 선택해 주세요',
  child: Column(children: [
    Semantics(
      label: 'Completed — 학습을 완료했습니다',
      inMutuallyExclusiveGroup: true,
      checked: isSelected,
      child: outcomeCard,
    ),
    // ...remaining three options
  ]),
)
```
[Source: EXPERIENCE.md line 677-691]

### 이전 스토리 핵심 레슨 (Story 4.1에서)

- Next.js App Router `params`는 `Promise<{signalId: string}>` — `use(params)`로 unwrap 필요
- Flutter: async 작업 후 `setState` 직전 `if (!mounted) return;` 체크 필수 (이 스토리는 realtime 구독이 없어 리스크는 낮지만 `submitOutcome` 이후 네비게이션 전에는 여전히 적용)
- Flutter dispose: 사용하는 모든 컨트롤러(`TextEditingController` 등) dispose 필수
- URL 스킴 검증(`http`/`https`만)이 학습 경로 카드 탭에서 필요했던 것과 달리, 이 스토리는 외부 링크를 열지 않으므로 해당 없음
- `@riverpod` 함수형보다 클래스 기반 Notifier가 명시적 메서드(`retry()`, 이 스토리에서는 `submitOutcome()`) 노출에 유리하다는 것이 4.1 코드 리뷰에서 확인됨 — 이 스토리의 Provider도 처음부터 클래스 기반으로 작성한다(4.1처럼 나중에 리팩터링하지 않도록)

### 범위 경계

| 항목 | 이 스토리 (4.2) | 이후 |
|------|----------------|------|
| `POST /api/v1/outcomes` API (동기 CRUD) | ✅ | — |
| Web Outcome 화면 (라디오 그룹 + 선택적 피드백 + CTA) | ✅ | — |
| Flutter Outcome 화면 (동일) | ✅ | — |
| Outcome 저장 후 Memory 추출(AI, BackgroundTask) | ❌ | Story 4.3 (Memory Manager) |
| `memories` 테이블 INSERT | ❌ | Story 4.3 |
| Push 알림(N일 후 Outcome 미기록 리마인더) | ❌ | Epic 5 (5.3 Push Notification System) |
| Memory Timeline에서 Outcome 표시(히스토리 탭) | ❌ | Epic 5 (5.2 History/Memory Timeline) |
| Outcome 재기록/수정 UI | ❌ | AC 범위 밖 — 스코프 없음 |

### 절대 금지사항

| 금지 | 이유 |
|------|------|
| 클라이언트에서 `outcomes` 직접 INSERT | AD-3: FastAPI만 쓰기 허용 |
| `outcomes` 관련 신규 DB 마이그레이션 추가 | 스키마는 이미 존재, 이 스토리는 API/UI 레이어만 (unique 제약 추가는 스코프 밖) |
| `test_outcomes.py`에서 실제 Supabase 테스트 DB 연결 시도 | `test_decisions.py`와 동일하게 완전 모킹이 확립된 컨벤션 (Dev Notes "AD-11 적용 방식" 참조) |
| Memory 추출/저장 로직 구현 | Story 4.3 범위 |
| progress bar / streak / 달성 배지 UI | UX-DR18 명시 금지 패턴 |
| Floating FAB 추가 | UX-DR18 명시 금지 패턴 |
| OutcomeCard 선택 시 배경(fill) 색 변경 | DESIGN.md 명시: "Selected state is indicated by border only, not fill" |

### 신규 / 수정 파일 목록

```
# API 신규 파일
api/routers/outcomes.py                 (NEW)
api/tests/test_outcomes.py              (NEW)

# API 수정 파일
api/main.py                             (UPDATE — outcomes_router 등록)

# 웹 수정/신규 파일
web/src/app/(app)/home/review/[signalId]/outcome/page.tsx  (UPDATE — placeholder → real)
web/src/components/home/outcome/outcome-card.tsx           (NEW)

# Flutter 신규 파일
mobile/lib/features/home/providers/outcome_provider.dart   (NEW)
mobile/lib/features/home/providers/outcome_provider.g.dart (NEW — build_runner 생성)
mobile/lib/features/home/screens/outcome_screen.dart       (NEW)

# Flutter 수정 파일
mobile/lib/core/router/app_router.dart   (UPDATE — _OutcomePlaceholderScreen 삭제, OutcomeScreen 연결)
```

### References

- 에픽: `_bmad-output/planning-artifacts/epics.md` — Story 4.2 (line 694–722), Story 4.3 스코프 경계 확인용 (line 724–748)
- UX: `_bmad-output/planning-artifacts/ux-designs/ux-decision-os-2026-07-21/EXPERIENCE.md` — Outcome Card (line 295–317), Outcome radio group ARIA 웹 스펙(line 622–624), Flutter Semantics 코드 예시(line 677–691), 접근성 44×44/52px 각주(line 601), `lang="en"` 대상 목록(line 644), haptic 규칙(line 560)
- UX: `_bmad-output/planning-artifacts/ux-designs/ux-decision-os-2026-07-21/DESIGN.md` — Outcome Card 시각 스펙(line 319–337)
- 아키텍처: `_bmad-output/planning-artifacts/architecture/architecture-decision-os-2026-07-21/ARCHITECTURE-SPINE.md` — AD-3(line 30–33), AD-9(line 231–234), AD-11(line 245–248), AD-13(line 259–262)
- DB 스키마: `supabase/migrations/20260723000000_initial_schema.sql` — `outcomes` 테이블(line 110–124), `outcomes_select` RLS(line 324–330)
- 기존 Decision 라우터 패턴(소유권 검증 + 멱등성 + race fallback): `api/routers/decisions.py`
- 기존 테스트 패턴(mock 기반): `api/tests/test_decisions.py`
- Web 재사용 패턴: `web/src/app/(app)/home/review/[signalId]/learning-path/page.tsx` (signalId→decision_id 조회, 토스트), `web/src/components/home/review/context-sticky-bar.tsx` (토스트 자동소멸 + 지연 네비게이션, pill 버튼 스타일, JWT fetch 패턴)
- Flutter 재사용 패턴: `mobile/lib/features/home/providers/learning_path_provider.dart` (클래스 기반 Notifier, JWT 트리거 패턴), `mobile/lib/features/home/screens/learning_path_screen.dart` (SnackBar 패턴), `mobile/lib/features/onboarding/screens/onboarding_screen.dart` (`_OptionCard` — line 537–570, OutcomeCard 시각 스펙과 정확히 일치)
- 이전 스토리: `_bmad-output/implementation-artifacts/4-1-learning-path-생성-and-화면.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-5

### Debug Log References

- `cd api && python -m pytest tests/test_outcomes.py -v` → 7 passed
- `cd api && python -m pytest -q` (전체 회귀) → 113 passed
- `cd web && npx tsc --noEmit -p tsconfig.json` → Outcome 관련 파일 타입 에러 없음 (기존 `chat/page.tsx`의 사전 존재 에러만 남음, Story 4.2 스코프 밖)
- `cd mobile && flutter pub run build_runner build --delete-conflicting-outputs` → `outcome_provider.g.dart` 정상 생성 (동시에 리포트된 `test/profile_test.dart` 파싱 에러는 Story 1.6 범위의 기존 문제)
- `cd mobile && flutter analyze lib/` → 7 issues, 전부 Outcome 관련 파일 외부의 기존 이슈
- `cd mobile && flutter test` → Outcome과 무관한 3개 테스트 파일(`profile_test.dart`, `home_screen_test.dart`, `navigation_shell_test.dart`)이 `profile_screen.dart`의 사전 존재 컴파일 에러(`AppSettings.openNotificationSettings` 미정의, Story 1.6 범위)로 실패. 나머지(`auth_test.dart`, `onboarding_test.dart`, `theme_test.dart`, `widget_test.dart`)는 전부 통과(46 tests)

### Completion Notes List

- API: `outcomes.py` 라우터를 `decisions.py` 패턴(3-hop 소유권 검증, 체크-후-삽입 멱등성, race-condition INSERT 폴백)으로 구현. `useful` 필수 규칙은 Dev Notes "스펙 갈등 1"에 따라 API 레이어에서 422로 방어.
- API 테스트: `test_decisions.py`의 완전 모킹 패턴을 그대로 재사용, 8개 시나리오 전부 통과.
- Web: `outcome-card.tsx` + `outcome/page.tsx` 구현. signalId→decision_id 조회는 `learning-path/page.tsx`의 `resolveAndStart` 앞부분 패턴 재사용. 렌더링 중 부수효과(`router.push`) 호출을 피하기 위해 `loadFailed` 리다이렉트를 `useEffect`로 처리.
- Flutter: `outcome_provider.dart`를 클래스 기반 `AsyncNotifier`(`@riverpod class OutcomeController`)로 작성해 `submitOutcome()` 명시적 메서드 노출(4.1 리뷰 레슨 반영). `outcome_screen.dart`는 `onboarding_screen.dart`의 `_OptionCard` 시각 스펙과 EXPERIENCE.md의 `Semantics` 접근성 코드를 그대로 적용.
- 라우터: `app_router.dart`에서 `_OutcomePlaceholderScreen` 삭제, `OutcomeScreen`으로 교체.
- 발견된 사전 존재 이슈(이 스토리 스코프 밖, 수정하지 않음): (1) `web/.../chat/page.tsx`의 `.catch()` 타입 에러 (Story 3.4), (2) `mobile/lib/features/profile/screens/profile_screen.dart`의 `AppSettings.openNotificationSettings` 미정의 메서드 + `test/profile_test.dart`의 top-level `group()` 문법 에러 (Story 1.6) — 둘 다 Outcome 기능과 무관하며 이번 스토리에서 손대지 않음.

### File List

```
# API 신규 파일
api/routers/outcomes.py                 (NEW)
api/tests/test_outcomes.py              (NEW)

# API 수정 파일
api/main.py                             (UPDATE — outcomes_router 등록)

# 웹 수정/신규 파일
web/src/app/(app)/home/review/[signalId]/outcome/page.tsx  (UPDATE — placeholder → real)
web/src/components/home/outcome/outcome-card.tsx           (NEW)

# Flutter 신규 파일
mobile/lib/features/home/providers/outcome_provider.dart   (NEW)
mobile/lib/features/home/providers/outcome_provider.g.dart (NEW — build_runner 생성)
mobile/lib/features/home/screens/outcome_screen.dart       (NEW)

# Flutter 수정 파일
mobile/lib/core/router/app_router.dart   (UPDATE — _OutcomePlaceholderScreen 삭제, OutcomeScreen 연결)
```

## Change Log

| 날짜 | 변경 내용 |
|------|-----------|
| 2026-07-27 | Story 4.2 구현 완료: `POST /api/v1/outcomes` API + Web/Flutter Outcome 기록 화면. 전체 API 회귀 테스트(113개) 통과. |
