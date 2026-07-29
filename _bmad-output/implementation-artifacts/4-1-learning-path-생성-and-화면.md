---
baseline_commit: NO_VCS
---

# Story 4.1: Learning Path 생성 & 화면

Status: review

## Story

사용자로서,
"Learn Now" 결정 후 내 프로필에 맞는 Learning Path를 받아 5가지 리소스를 순서대로 학습할 수 있기를 원한다,
그래서 어디서 시작해야 할지 고민 없이 바로 학습을 시작할 수 있다.

## Acceptance Criteria

**AC-1: Learning Path 비동기 트리거 (AD-5)**
- **Given** 사용자가 ContextStickyBar에서 "Learn Now"를 탭하면
- **When** `POST /api/v1/learning-paths/trigger { "decision_id": "..." }`가 호출되면
- **Then** 202 Accepted가 즉시 반환된다
- **And** BackgroundTask로 비동기 생성된다: `pending → processing → completed | failed`
- **And** `learning_paths` 테이블에 `decision_id`, `signal_id`, `resources`(JSONB), `status` 컬럼이 존재한다

**AC-2: 생성 중 로딩 상태**
- **Given** Learning Path가 `pending` 또는 `processing` 상태일 때
- **Then** "학습 경로를 생성하는 중입니다." + 세 점 pulse 애니메이션이 표시된다
- **And** `prefers-reduced-motion` 시 pulse 애니메이션이 정적 인디케이터로 대체된다
- **And** Supabase Realtime으로 완료를 구독한다

**AC-3: Learning Path 준비됨 — LearningPathCard 렌더링**
- **Given** Learning Path가 `completed`로 전환되면
- **Then** 5가지 리소스가 고정 순서로 표시된다: (1)공식 문서 (2)핵심 자료 (3)GitHub (4)실습 예제 (5)적용 아이디어
- **And** 각 LearningPathCard: resource type label(10px/uppercase/700/text-secondary) + 제목(15px/600) + descriptor(13px/text-secondary) + chevron-external 아이콘
- **And** "적용 아이디어" 카드는 사용자의 `project_goal` 기반으로 개인화된 내용이다
- **And** 각 카드는 tappable이고 외부 URL을 새 탭(웹)/기기 브라우저(Flutter)로 열린다

**AC-4: 외부 링크 방문 후 Outcome 프롬프트**
- **Given** 사용자가 외부 링크를 1회 이상 탭하고 앱/화면으로 복귀하면
- **Then** Learning Path 화면 하단에 비차단 프롬프트가 표시된다: "학습을 완료했나요? 결과를 기록해 주세요." + "결과 기록하기" CTA
- **And** 이 프롬프트는 외부 링크 방문 전에는 표시되지 않는다 (카드 첫 로드 시 비표시)
- **And** "결과 기록하기" → `/home/review/:signalId/outcome` 으로 이동한다 (Story 4.2 구현 대상)

**AC-5: 생성 실패 상태**
- **Given** Learning Path 생성이 `failed`이면
- **Then** "학습 경로를 생성하지 못했습니다." + "다시 시도하기" + "홈으로 돌아가기" CTA가 표시된다
- **And** "다시 시도하기" → `POST /api/v1/learning-paths/trigger` 재호출

**AC-6: 멱등성 — 이미 생성된 Learning Path 재사용**
- **Given** `decision_id`에 대한 `learning_path`가 `pending` 또는 `processing` 중인 경우
- **Then** 새 레코드 생성 없이 기존 `learning_path_id`를 반환한다

## Tasks / Subtasks

### [API] Learning Path 파이프라인 & 라우터

- [x] Task 1: `api/pipeline/llm/base.py` 수정 — `LearningPathContext` 데이터클래스 + `generate_learning_path()` abstract 메서드 추가 (AC: #1, #3)
  - [x] 1.1 `LearningPathContext` 데이터클래스:
    ```python
    @dataclass
    class LearningPathContext:
        technology_name: str
        signal_summary: str
        signal_sources: list[dict]       # [{source_type, url, title}]
        user_role: str | None = None
        user_tech_stack: list[str] = field(default_factory=list)
        user_project_goal: str | None = None   # user_profiles.project_goal
        user_experience_level: str | None = None
    ```
  - [x] 1.2 `LLMProvider` 추상 메서드 추가:
    ```python
    @abstractmethod
    def generate_learning_path(self, context: LearningPathContext) -> LLMResponse:
        """5가지 고정 리소스 타입의 Learning Path JSON 생성."""
        ...
    ```
  - [x] 1.3 기존 `MockLLMProvider` (test_signal_builder_reviewer.py에서 사용)에 stub 추가 필요 — 누락 시 기존 테스트 실패

- [x] Task 2: `api/pipeline/llm/openai_provider.py` 수정 — `generate_learning_path()` 구현 (AC: #1, #3)
  - [x] 2.1 `LEARNING_PATH_SYSTEM_PROMPT` 상수 정의:
    - 5개 리소스를 JSON 배열로 반환: `[{"type": "official_docs|core_material|github|practice_example|applied_idea", "title": "...", "url": "...", "descriptor": "..."}, ...]`
    - 순서 고정: official_docs → core_material → github → practice_example → applied_idea
    - `applied_idea`: user의 `project_goal`에 맞게 개인화된 아이디어. URL은 관련 참고 링크 (없으면 빈 문자열)
    - 마크다운 없이 JSON 배열만 반환
  - [x] 2.2 `generate_learning_path(self, context: LearningPathContext) → LLMResponse` 구현
    - `client.responses.create(model=..., instructions=LEARNING_PATH_SYSTEM_PROMPT, input=user_content, text={"format": {"type": "json_object"}})` — AD-6: Chat Completions 사용 금지
    - 응답: `{"resources": [...]}` JSON — 5개 리소스 배열 포함 여부 검증
    - `LLMProviderError` 표준화

- [x] Task 3: `api/pipeline/coach.py` 신규 생성 — Learning Path BackgroundTask 파이프라인 (AC: #1, #2, #5)
  - reviewer.py와 동일한 패턴 적용
  - [x] 3.1 `run_learning_path_from_pending(learning_path_id: str, decision_id: str, signal_id: str) → None`
  - [x] 3.2 `pending → processing` 전이 (processing_started_at 설정)
  - [x] 3.3 Signal 데이터 조회 (`signals`, `signal_sources`)
  - [x] 3.4 Decision → Review → Project → user_id → user_profiles 조회 (project_goal 포함)
  - [x] 3.5 `LearningPathContext` 구성
  - [x] 3.6 `OpenAIProvider().generate_learning_path(context)` 호출
  - [x] 3.7 JSON 파싱 → `resources` JSONB 검증 (5개 항목, type 값 검증)
  - [x] 3.8 `learning_paths` 업데이트: `status: completed`, `resources: [...]`
  - [x] 3.9 실패 시: `status: failed`, `error_message: str` 기록, 소스 데이터 보존, 자동 재시도 없음
  - [x] 3.10 JSON 구조화 로그: `learning_path_id`, `decision_id`, `pipeline_stage` 필드 포함 (AD-12)

- [x] Task 4: `api/routers/learning_paths.py` 신규 생성 — `POST /api/v1/learning-paths/trigger` (AC: #1, #6)
  - [x] 4.1 `TriggerLearningPathRequest` Pydantic 모델: `decision_id: str`
  - [x] 4.2 `decision_id`로 `decisions` 테이블 조회 → `review_id`, `choice`, `signal_id` 검증
    - `choice != 'learn_now'` → 422 반환
    - decision 없음 → 404 반환
  - [x] 4.3 `review_id → project_id → user_id` 권한 검증 (decisions.py 패턴 참조)
  - [x] 4.4 멱등성: 이미 `pending | processing` 상태 learning_path 존재 시 기존 `learning_path_id` 반환 (202)
  - [x] 4.5 `pending` INSERT: `decision_id`, `signal_id` 포함
  - [x] 4.6 `background_tasks.add_task(run_learning_path_from_pending, learning_path_id, decision_id, signal_id)`
  - [x] 4.7 202 반환: `{"learning_path_id": "...", "status": "pending"}`
  - [x] 4.8 `router = APIRouter(prefix="/learning-paths", tags=["learning-paths"])`

- [x] Task 5: `api/main.py` 수정 — learning_paths 라우터 등록 (AC: #1)
  - [x] 5.1 `from routers.learning_paths import router as learning_paths_router` import 추가
  - [x] 5.2 `app.include_router(learning_paths_router, prefix="/api/v1")` 추가

- [x] Task 6: `api/tests/test_learning_paths.py` 신규 생성 (AC: #1, #5, #6)
  - [x] 6.1 `POST /api/v1/learning-paths/trigger` 정상 호출 → 202 + `learning_path_id` 반환
  - [x] 6.2 `choice != 'learn_now'`인 decision_id → 422
  - [x] 6.3 다른 사용자의 decision_id → 404
  - [x] 6.4 멱등성: 동일 decision_id 2회 호출 → 동일 `learning_path_id` 반환
  - [x] 6.5 존재하지 않는 decision_id → 404
  - [x] 6.6 **LLMProvider mock 사용** (AD-11: LLM Provider만 인터페이스 모킹 허용)
  - [x] 6.7 **실제 Supabase 테스트 DB 연결** (AD-11: 프로덕션 DB 모킹 금지)

### [WEB] Learning Path 화면 구현

- [x] Task 7: `web/src/app/(app)/home/review/[signalId]/learning-path/page.tsx` 교체 (기존 placeholder 덮어쓰기) (AC: #1–#5)
  - [x] 7.1 `"use client"` 선언
  - [x] 7.2 `params: Promise<{ signalId: string }>` — Next.js App Router 패턴 (use/await)
  - [x] 7.3 **초기화 로직** (useEffect):
    - Supabase SDK로 `reviews` 조회: `signal_id = signalId AND status = 'completed'` → `review_id`
    - `decisions` 조회: `review_id = review_id AND choice = 'learn_now'` → `decision_id`
    - `learning_paths` 조회: `decision_id = decision_id` → 없으면 trigger
    - `POST /api/v1/learning-paths/trigger { decision_id }` → `learning_path_id`
  - [x] 7.4 **Supabase Realtime 구독**: `learning_paths` 테이블, `id = learning_path_id`, `status` 변경 감지
  - [x] 7.5 **상태 머신**:
    - `pending | processing` → AC-2 로딩 UI
    - `completed` → AC-3 LearningPathCard 목록
    - `failed` → AC-5 에러 UI
  - [x] 7.6 **로딩 UI**: "학습 경로를 생성하는 중입니다." + `<ThreeDotLoadingIndicator />` 재사용 (`web/src/components/` 또는 inline)
    - `prefers-reduced-motion` 시 dot pulse → 정적 텍스트 (CSS media query로 처리)
  - [x] 7.7 **LearningPathCard 컴포넌트** (`web/src/components/home/learning-path/learning-path-card.tsx` 신규):
    - resource type label: 10px/uppercase/700/text-secondary + letter-spacing
    - type → 표시명 매핑: `official_docs`→"공식 문서", `core_material`→"핵심 자료", `github`→"GitHub", `practice_example`→"실습 예제", `applied_idea`→"적용 아이디어"
    - 제목: 15px/600
    - descriptor: 13px/text-secondary
    - chevron-external 아이콘: URL이 있을 때만 표시
    - 탭 시 `window.open(url, '_blank', 'noopener noreferrer')` + `hasVisitedExternal = true` 상태 설정
    - `surface-card` 배경, 16px radius, 16px 패딩
  - [x] 7.8 **외부 링크 방문 감지**: `window` 또는 `document` `visibilitychange` 이벤트로 복귀 감지 + `hasVisitedExternal` 상태 체크
  - [x] 7.9 **Outcome 프롬프트** (`hasVisitedExternal && status === 'completed'`): 화면 하단 비차단 고정 영역
    - "학습을 완료했나요? 결과를 기록해 주세요."
    - "결과 기록하기" CTA (primary) → `router.push(/home/review/${signalId}/outcome)`
    - Bottom Sheet 아님 — Learning Path 콘텐츠를 가리지 않도록 페이지 하단 sticky 영역
  - [x] 7.10 **에러 UI**: "학습 경로를 생성하지 못했습니다." + "다시 시도하기" (trigger 재호출) + "홈으로 돌아가기" (`router.push('/home')`)
  - [x] 7.11 `auth.getSession()`으로 JWT 획득 → API 호출 시 `Authorization: Bearer {token}` 헤더 적용
  - [x] 7.12 **Back 버튼**: `router.back()` 또는 `<Link href={/home/review/${signalId}}>` — Research Review로 복귀
  - [x] 7.13 Realtime 구독 cleanup (`useEffect` return)

- [x] Task 8: `web/src/app/(app)/home/review/[signalId]/outcome/page.tsx` 신규 생성 — placeholder (Story 4.2 구현 대상) (AC: #4)
  - [x] 8.1 기본 placeholder 페이지 (Story 4.2에서 구현):
    ```tsx
    export default function OutcomePage() {
      return <div style={{ padding: "24px 20px" }}>
        <p>Outcome 기록 화면은 Story 4.2에서 구현됩니다.</p>
      </div>;
    }
    ```

### [FLUTTER] Learning Path 화면 구현

- [x] Task 9: `mobile/lib/features/home/providers/learning_path_provider.dart` 신규 생성 (AC: #1–#5)
  - [x] 9.1 `LearningPathResource` 데이터 클래스:
    ```dart
    class LearningPathResource {
      final String type; // 'official_docs' | 'core_material' | 'github' | 'practice_example' | 'applied_idea'
      final String title;
      final String url;
      final String descriptor;
    }
    ```
  - [x] 9.2 `LearningPathState` sealed class (또는 enum + data):
    - `LearningPathGenerating` — pending/processing
    - `LearningPathReady({ List<LearningPathResource> resources, String learningPathId })`
    - `LearningPathFailed({ String learningPathId? })`
  - [x] 9.3 `@riverpod Stream<LearningPathState> learningPathState(ref, String signalId)` — StreamProvider (AD-14)
    - Supabase SDK로 decision 조회: `decisions` JOIN `reviews` WHERE `signal_id = signalId AND choice = 'learn_now'`
    - 실제 쿼리: 먼저 `reviews` 조회 → `review_id` → `decisions` 조회 → `decision_id`
    - `learning_paths` 조회 → 없으면 FastAPI trigger
    - Supabase Realtime: `supabase.from('learning_paths').stream(primaryKey: ['id']).eq('id', learningPathId)` (AD-14: StreamProvider)
    - status 변환 → `LearningPathState` yield
  - [x] 9.4 `Future<String?> _triggerLearningPath(String decisionId)` — JWT 획득, `http.post`, `learning_path_id` 반환
  - [x] 9.5 `part 'learning_path_provider.g.dart'` + build_runner 재생성 필요

- [x] Task 10: `mobile/lib/features/home/screens/learning_path_screen.dart` 신규 생성 (AC: #2–#5)
  - [x] 10.1 `LearningPathScreen extends ConsumerStatefulWidget` — `signalId: String` prop
  - [x] 10.2 `_LearningPathScreenState extends ConsumerState<LearningPathScreen>`
  - [x] 10.3 `bool _hasVisitedExternal = false` — 외부 링크 방문 여부 추적
  - [x] 10.4 `AppLifecycleListener` (또는 `WidgetsBindingObserver`) — `resumed` 시 `_hasVisitedExternal` 체크 → Outcome 프롬프트 표시
  - [x] 10.5 `ref.watch(learningPathStateProvider(widget.signalId))`:
    - `LearningPathGenerating` → 로딩 UI
    - `LearningPathReady` → 5개 카드 + 조건부 프롬프트
    - `LearningPathFailed` → 에러 UI + CTA
  - [x] 10.6 **로딩 UI**: "학습 경로를 생성하는 중입니다." + `ThreeDotLoadingIndicator` 재사용 (`mobile/lib/features/home/widgets/three_dot_loading_indicator.dart`)
    - `prefers-reduced-motion` 대응: `MediaQuery.of(context).disableAnimations` 체크
  - [x] 10.7 **LearningPathCard 위젯** (`_LearningPathCard` private widget 또는 별도 파일):
    - resource type label → 표시명 매핑 (Task 7.7과 동일)
    - `TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 1.0, color: textSecondary)`
    - 제목: `TextStyle(fontSize: 15, fontWeight: FontWeight.w600)`
    - descriptor: `TextStyle(fontSize: 13, color: textSecondary)`
    - 외부 링크 아이콘: `Icon(Icons.open_in_new, size: 14, color: textTertiary)` (URL 있을 때만)
    - 탭: `url_launcher` 패키지 `launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication)` + `_hasVisitedExternal = true` + `setState`
  - [x] 10.8 **Outcome 프롬프트**: `_hasVisitedExternal && state is LearningPathReady` 조건부:
    - "학습을 완료했나요? 결과를 기록해 주세요."
    - `ElevatedButton("결과 기록하기")` → `context.push('/home/review/${widget.signalId}/outcome')`
    - 콘텐츠 아래 고정 (Stack 또는 Column 마지막 요소)
  - [x] 10.9 **에러 UI**: "학습 경로를 생성하지 못했습니다." + `TextButton("다시 시도하기")` (provider invalidate + retrigger) + `TextButton("홈으로 돌아가기")` (`context.go('/home')`)
  - [x] 10.10 `AppBar`: 제목 "[Signal 제목] Learning Path" — signalTitle은 `reviewStateProvider(signalId)`에서 획득 (기존 패턴, 3.4 story 참조)
  - [x] 10.11 `url_launcher` 패키지가 `mobile/pubspec.yaml`에 없으면 추가 필요 (기존 설치 여부 확인 먼저)
  - [x] 10.12 `dispose()`: AppLifecycleListener/WidgetsBindingObserver 해제

- [x] Task 11: `mobile/lib/core/router/app_router.dart` 수정 (AC: #1, #4)
  - [x] 11.1 `import '../../features/home/screens/learning_path_screen.dart'` 추가
  - [x] 11.2 `learning-path` GoRoute: `_LearningPathPlaceholderScreen` → `LearningPathScreen(signalId: state.pathParameters['signalId']!)` 교체
  - [x] 11.3 `_LearningPathPlaceholderScreen` 클래스 삭제
  - [x] 11.4 `outcome` GoRoute 추가 (Story 4.2 placeholder):
    ```dart
    GoRoute(
      path: 'outcome',
      builder: (_, state) => _OutcomePlaceholderScreen(
        signalId: state.pathParameters['signalId']!,
      ),
    ),
    ```
  - [x] 11.5 `_OutcomePlaceholderScreen` placeholder 클래스 추가 (Story 4.2에서 교체)
  - [x] 11.6 `app_router.g.dart` build_runner 재생성

### Review Findings

- [x] [Review][Defer] Stuck pending/processing 복구 경로 부재 — 스키마가 `idx_learning_paths_stuck`(AD-12 "stuck 감지용") 인덱스를 이미 제공하지만, 이를 소비하는 클라이언트 타임아웃이나 서버 reaper job이 이 diff 어디에도 없다. deferred, pre-existing 아님(신규 요구사항) — P1 수정 후 발생빈도 낮아짐; 타임아웃/reaper job은 운영 인프라 결정 사항이라 별도 스토리로 분리

- [x] [Review][Patch] `OpenAIProvider()`를 인자 없이 호출 — 파이프라인이 즉시 크래시함 [api/pipeline/coach.py:125] — `OpenAIProvider.__init__`은 `api_key: str`을 기본값 없이 요구하는데(`api/pipeline/llm/openai_provider.py:58`), `run_learning_path_from_pending`은 `OpenAIProvider()`를 무인자로 호출한다. 이 호출은 `_execute_learning_path_pipeline`의 try/except 바깥에 있어 `TypeError`가 전혀 캐치되지 않고, `learning_paths` row는 `pending`에 영원히 머문다. AC-1/AC-2/AC-3/AC-5 전체가 실질적으로 도달 불가능하다. 동일 저장소의 `api/routers/chat.py:31`, `api/pipeline/orchestrator.py:34`는 이미 `OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)` 패턴을 올바르게 사용 중이므로 수정 방향은 명확하다.

- [x] [Review][Patch] 테스트가 AD-11을 위반해 위 버그를 은폐함 [api/tests/test_learning_paths.py] — 모든 테스트가 `patch("...get_supabase", ...)`로 Supabase 클라이언트 전체를 모킹하고, `pipeline.coach.OpenAIProvider`도 클래스째로 모킹한다. Dev Notes AD-11("실제 Supabase 테스트 DB 연결... LLM Provider만 인터페이스 모킹 허용")과 파일 자체의 독스트링("LLM Provider만 mock (AD-11)")에 정면으로 위배된다. 대조적으로 기존 `test_signal_builder_reviewer.py`는 `OpenAI` SDK 클라이언트 경계만 모킹하고 `get_supabase`는 건드리지 않는다 — 바로 이 차이 때문에 "104/104 통과"에도 위 크리티컬 버그가 전혀 감지되지 않았다.

- [x] [Review][Patch] Flutter "다시 시도하기" 버튼이 아무 동작도 하지 않음 [mobile/lib/features/home/providers/learning_path_provider.dart:114-117] — `status == 'failed'`일 때 트리거를 재호출하지 않고 즉시 `LearningPathFailed`를 다시 yield하고 반환한다. `_FailedBody.onRetry`는 provider를 invalidate만 하므로 동일 로직이 재실행되어 다시 실패 상태만 반환한다. AC-5("'다시 시도하기' → POST /trigger 재호출")를 모바일에서 위반한다. 웹의 `handleRetry`는 동일 상황에서 `triggerAPI`를 올바르게 재호출한다.

- [x] [Review][Patch] `/learning-paths/trigger`의 TOCTOU 레이스 [api/routers/learning_paths.py:70-95] — pending/processing 존재 확인과 INSERT 사이에 유니크 제약이나 트랜잭션이 없다. `learning_paths.decision_id`에 유니크 인덱스가 없음을 마이그레이션에서 확인했다(`idx_learning_paths_decision`은 비유니크). 동시 요청(더블탭, React Strict Mode 이중 마운트 등) 시 중복 row와 중복 LLM 호출이 발생할 수 있다.

- [x] [Review][Patch] 웹 `page.tsx`의 에러 처리 공백 3건 [web/src/app/(app)/home/review/[signalId]/learning-path/page.tsx] — (1) `resolveAndStart`/`subscribe`에서 Supabase 응답의 `error` 필드를 전혀 확인하지 않아 RLS/네트워크 오류가 "결과 없음"과 동일하게 처리됨, (2) `subscribe`의 completed 핸들러가 가드 없는 `.single()`을 호출해 0/2+ row 상황에서 unhandled promise rejection 발생 가능, (3) 바로 위 title-fetch effect에는 있는 `cancelled` 가드가 `resolveAndStart`에는 없어 signalId 변경 시 stale 상태 반영 가능.

- [x] [Review][Patch] 초기 조회와 Realtime 구독 사이의 상태 전이 누락 레이스 (웹+모바일) — `.maybeSingle()` 초기 조회 이후 `.subscribe()`가 실제로 채널을 맺기까지의 시간차 동안 row가 `completed`/`failed`로 전이되면 이벤트를 놓쳐 "생성 중" 화면에 무한정 머문다. P1이 고쳐진 뒤 실제 LLM 응답이 매우 빨리 오는 경우 재현 가능성이 있다.

- [x] [Review][Patch] Flutter 초기 로딩 상태가 AC-2 스펙과 다름 [mobile/lib/features/home/screens/learning_path_screen.dart:76] — StreamProvider의 첫 yield 이전(`AsyncValue.loading`) 구간에 `CircularProgressIndicator()`만 표시되고, AC-2가 요구하는 "학습 경로를 생성하는 중입니다." 문구 + 세 점 pulse가 나오지 않는다.

- [x] [Review][Patch] LLM이 생성한 리소스 URL에 스킴 검증이 전혀 없음 (웹+모바일) — 웹 `learning-path-card.tsx`의 `window.open(resource.url, ...)`과 모바일 `_handleTap`의 `launchUrl(Uri.parse(resource.url))` 모두 `http(s)://` 화이트리스트 없이 LLM 출력을 그대로 신뢰한다. `openai_provider.py`의 `generate_learning_path`도 리소스 개수/타입만 검증할 뿐 URL 형식은 검증하지 않는다.

- [x] [Review][Patch] 실패 상태 업데이트 자체가 실패하면 내부 예외가 조용히 삼켜짐 [api/pipeline/coach.py:104-111] — `except Exception: pass`로 로그 한 줄 없이 무시되어, DB가 `processing`에 영구히 머무는 상황에서 진단 단서가 줄어든다.

- [x] [Review][Patch] 모바일 `_handleTap`의 사소한 엣지 케이스 2건 [mobile/lib/features/home/screens/learning_path_screen.dart] — `launchUrl`이 `false`를 반환해도 `onVisit()`이 호출되어 실제로 아무것도 안 열렸는데 방문한 것으로 처리됨, `Uri.tryParse`가 `null`일 때 사용자 피드백 없이 조용히 무시됨.

- [x] [Review][Patch] 테스트 파일 간 결합 [api/tests/test_learning_paths.py] — `from tests.test_signal_builder_reviewer import MockLLMProvider`로 Story 2.2의 테스트 모듈에서 직접 import하여, 무관한 파일의 변경이 이 스토리 테스트를 깨뜨릴 수 있다. 공유 fixture/conftest로 옮기는 것을 권장.

- [x] [Review][Patch] `coach.py`의 모든 조회 실패가 동일한 제네릭 `RuntimeError`로 처리됨 [api/pipeline/coach.py] — signal/decision/review/project 조회 실패가 전부 "not found" 메시지로 뭉뚱그려져 `error_message`에 저장되므로, 실제 Supabase 장애가 발생해도 "찾을 수 없음"으로 오인될 수 있다. 동일 패턴이 4곳에 중복되어 있다.

- [x] [Review][Patch] Flutter GitHub 라벨에 웹과 동일한 접근성 마킹이 없음 [mobile/lib/features/home/screens/learning_path_screen.dart] — 웹 `learning-path-card.tsx`는 `lang="en"`(UX-DR14)을 마킹하지만 Flutter 쪽 동일 라벨에는 대응 마킹이 없다.

- [x] [Review][Defer] `api/pipeline/reviewer.py:193`에 동일한 `OpenAIProvider()` 무인자 호출 버그가 이미 존재함 — deferred, pre-existing (이 diff에 포함되지 않은 기존 파일이며, coach.py의 P1과 동일 원인이므로 함께 고치는 것을 권장)

## Dev Notes

### 핵심 아키텍처 제약

| 규칙 | 상세 |
|------|------|
| **AD-5** 비동기 AI | `POST /api/v1/learning-paths/trigger` → 202 즉시 응답. BackgroundTask 비동기. `completed/failed` 진입 후 추가 변경 금지 |
| **AD-3** 쓰기 경로 | `learning_paths` 테이블 INSERT/UPDATE는 FastAPI만. 클라이언트 직접 쓰기 금지 |
| **AD-6** LLM 공급자 | OpenAI Responses API만 사용. `client.responses.create()`. Chat Completions API 사용 금지 |
| **AD-11** 테스트 | 실제 Supabase 테스트 DB 연결. 프로덕션 DB 모킹 금지. LLM Provider만 인터페이스 모킹 허용 |
| **AD-14** Flutter 상태관리 | Riverpod 2.x 단일 표준. `@riverpod` 코드 생성. 비동기 상태는 `StreamProvider`로 Realtime 구독 |
| **AD-12** 관찰가능성 | 모든 FastAPI 로그 JSON 구조화. `learning_path_id`, `pipeline_stage` 필드 포함 |

### 기존 코드베이스 현황 (수정 대상 파일)

**이미 존재하는 placeholder:**
- `web/src/app/(app)/home/review/[signalId]/learning-path/page.tsx` — 단순 placeholder, 완전히 덮어쓰기 (7줄짜리 stub)
- `mobile/lib/core/router/app_router.dart:90–91, 125–149` — `_LearningPathPlaceholderScreen` 교체, 해당 클래스 삭제

**ContextStickyBar 현재 구현 (변경 불필요):**
- `web/src/components/home/review/context-sticky-bar.tsx:178–179`
  ```tsx
  await postDecision({ review_id: reviewId, choice: "learn_now" });
  router.push(`/home/review/${signalId}/learning-path`);
  ```
  → `decision_id`를 URL에 포함하지 않음. Learning-path page에서 직접 Supabase 조회로 resolution

- `mobile/lib/features/home/screens/research_review_screen.dart:691–692`
  ```dart
  await _postDecision(choice: 'learn_now');
  if (mounted) context.push('/home/review/${widget.signalId}/learning-path');
  ```
  → 동일 패턴. Flutter provider에서 signalId 기반으로 decision 조회

**기존 패턴 참조:**
- `api/routers/reviews.py` — BackgroundTask trigger 패턴 (동일하게 적용)
- `api/pipeline/reviewer.py` — `run_review_from_pending()` 패턴 → `run_learning_path_from_pending()`
- `api/pipeline/llm/openai_provider.py` — `generate()`, `chat()` 구현체 패턴
- `api/pipeline/llm/base.py:64–71` — 기존 `MockLLMProvider` stub 추가 위치
- `mobile/lib/features/home/providers/research_review_provider.dart` — `StreamProvider` + Realtime 구독 패턴
- `mobile/lib/features/home/widgets/three_dot_loading_indicator.dart` — 기존 로딩 인디케이터 위젯 재사용
- `mobile/lib/features/home/screens/contextual_chat_screen.dart` — JWT 획득 패턴

### DB 스키마 — learning_paths 테이블 (기존 마이그레이션)

```sql
CREATE TABLE IF NOT EXISTS public.learning_paths (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id           UUID NOT NULL REFERENCES public.decisions(id) ON DELETE CASCADE,
    signal_id             UUID NOT NULL REFERENCES public.signals(id)   ON DELETE CASCADE,
    resources             JSONB,
    status                TEXT NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message         TEXT,
    processing_started_at TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- RLS: SELECT via decision_id → decisions.review_id → reviews.project_id → projects.user_id
```

**resources JSONB 스키마 (5개 고정 순서):**
```json
{
  "resources": [
    {"type": "official_docs",    "title": "...", "url": "https://...", "descriptor": "..."},
    {"type": "core_material",    "title": "...", "url": "https://...", "descriptor": "..."},
    {"type": "github",           "title": "...", "url": "https://github.com/...", "descriptor": "..."},
    {"type": "practice_example", "title": "...", "url": "https://...", "descriptor": "..."},
    {"type": "applied_idea",     "title": "...", "url": "",            "descriptor": "사용자 project_goal 기반 개인화 아이디어"}
  ]
}
```

### LLM: `generate_learning_path()` 프롬프트 패턴

```python
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

def _build_learning_path_content(self, context: LearningPathContext) -> str:
    sources = "\n".join(f"- [{s.get('source_type')}] {s.get('title')} ({s.get('url')})" for s in context.signal_sources)
    return (
        f"기술명: {context.technology_name}\n"
        f"요약: {context.signal_summary}\n"
        f"출처:\n{sources}\n"
        f"사용자 역할: {context.user_role or '미지정'}\n"
        f"기술 스택: {', '.join(context.user_tech_stack) or '미지정'}\n"
        f"프로젝트 목표: {context.user_project_goal or '미지정'}\n"
        f"경험 수준: {context.user_experience_level or '미지정'}"
    )
```

### Web: signalId → decision_id 조회 흐름

```tsx
// learning-path/page.tsx 초기화 로직
const reviews = await supabase
  .from('reviews')
  .select('id')
  .eq('signal_id', signalId)
  .eq('status', 'completed')
  .limit(1);

const decisions = await supabase
  .from('decisions')
  .select('id')
  .eq('review_id', reviews.data![0].id)
  .eq('choice', 'learn_now')
  .limit(1);

const decisionId = decisions.data![0].id;

const learningPaths = await supabase
  .from('learning_paths')
  .select('id, status, resources')
  .eq('decision_id', decisionId)
  .limit(1);

let learningPathId: string;
if (!learningPaths.data?.length) {
  // trigger
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/learning-paths/trigger`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision_id: decisionId }),
  });
  const json = await res.json();
  learningPathId = json.data.learning_path_id;
} else {
  learningPathId = learningPaths.data[0].id;
  // 이미 completed면 바로 렌더링
}
// Realtime 구독
const channel = supabase.channel(`learning_path:${learningPathId}`)
  .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'learning_paths', filter: `id=eq.${learningPathId}` },
    (payload) => { /* status 변경 처리 */ })
  .subscribe();
```

### Flutter: url_launcher 사용 확인

`mobile/pubspec.yaml`에 `url_launcher` 존재 여부 먼저 확인:
```bash
grep "url_launcher" mobile/pubspec.yaml
```
없으면 `flutter pub add url_launcher` 실행 후 `pubspec.lock` 업데이트 필요.

### 외부 링크 방문 감지 패턴

**Web:**
```tsx
const [hasVisitedExternal, setHasVisitedExternal] = useState(false);
useEffect(() => {
  const handleVisibility = () => {
    if (document.visibilityState === 'visible' && hasVisitedExternal) {
      // 이미 hasVisitedExternal = true → Outcome 프롬프트 표시
    }
  };
  document.addEventListener('visibilitychange', handleVisibility);
  return () => document.removeEventListener('visibilitychange', handleVisibility);
}, [hasVisitedExternal]);
// 외부 링크 탭 시:
window.open(url, '_blank', 'noopener noreferrer');
setHasVisitedExternal(true);
```

**Flutter:**
```dart
late final AppLifecycleListener _lifecycleListener;

@override
void initState() {
  super.initState();
  _lifecycleListener = AppLifecycleListener(
    onResume: () {
      if (_hasVisitedExternal && mounted) {
        setState(() {}); // rebuild → Outcome 프롬프트 조건부 표시
      }
    },
  );
}

// 카드 탭 핸들러:
await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
if (mounted) setState(() => _hasVisitedExternal = true);
```

### LearningPathCard type → 표시명 매핑

```
official_docs    → "공식 문서"
core_material    → "핵심 자료"
github           → "GitHub"        (lang="en" 마킹 필요 — UX-DR14)
practice_example → "실습 예제"
applied_idea     → "적용 아이디어"
```

### 이전 스토리 핵심 레슨 (Story 3.4에서)

- MockLLMProvider에 새 abstract method stub 추가 필수 — 누락 시 기존 테스트 전체 실패
- FastAPI dependency override: `app.dependency_overrides[get_llm_provider] = lambda: mock_llm` 패턴 (patch보다 안정적)
- Next.js App Router `params`는 `Promise<{signalId: string}>`, `use(params)` 또는 `await`로 unwrap 필요
- Flutter: `if (!mounted) return;` — async 작업 후 setState 직전 mounted 체크 필수
- Flutter dispose: 모든 컨트롤러, 리스너 dispose 필수

### 범위 경계

| 항목 | 이 스토리 (4.1) | 이후 |
|------|----------------|------|
| `POST /api/v1/learning-paths/trigger` API | ✅ | — |
| LearningPathContext + generate_learning_path() LLM | ✅ | — |
| coach.py BackgroundTask 파이프라인 | ✅ | — |
| Web LearningPath 화면 (4상태 완전 구현) | ✅ | — |
| Flutter LearningPath 화면 (4상태 완전 구현) | ✅ | — |
| outcome 라우트 placeholder (web + flutter) | ✅ | Story 4.2에서 구현 |
| Outcome 기록 화면 실제 구현 | ❌ | Story 4.2 |
| Memory 추출 및 저장 | ❌ | Story 4.3 |

### 절대 금지사항

| 금지 | 이유 |
|------|------|
| Chat Completions API 사용 | AD-6: OpenAI Responses API만 허용 |
| 클라이언트에서 learning_paths 직접 INSERT/UPDATE | AD-3: FastAPI만 쓰기 허용 |
| completed/failed 상태 진입 후 추가 상태 변경 | AD-5: 불변 종료 상태 |
| Outcome 화면 실제 구현 | Story 4.2 범위, 이 스토리는 placeholder만 |
| progress bar / streak / 달성 배지 UI | UX-DR18 명시 금지 패턴 |
| Floating FAB 추가 | UX-DR18 명시 금지 패턴 |

### 신규 / 수정 파일 목록

```
# API 신규 파일
api/routers/learning_paths.py           (NEW)
api/pipeline/coach.py                   (NEW)
api/tests/test_learning_paths.py        (NEW)

# API 수정 파일
api/pipeline/llm/base.py                (UPDATE — LearningPathContext, generate_learning_path() abstract 추가)
api/pipeline/llm/openai_provider.py     (UPDATE — generate_learning_path() 구현, LEARNING_PATH_SYSTEM_PROMPT)
api/tests/test_signal_builder_reviewer.py  (UPDATE — MockLLMProvider에 generate_learning_path() stub 추가)
api/main.py                             (UPDATE — learning_paths_router 등록)

# 웹 수정/신규 파일
web/src/app/(app)/home/review/[signalId]/learning-path/page.tsx  (UPDATE — placeholder → real)
web/src/app/(app)/home/review/[signalId]/outcome/page.tsx        (NEW — placeholder)
web/src/components/home/learning-path/learning-path-card.tsx     (NEW)

# Flutter 신규 파일
mobile/lib/features/home/providers/learning_path_provider.dart   (NEW)
mobile/lib/features/home/providers/learning_path_provider.g.dart (NEW — build_runner 생성)

# Flutter 수정 파일
mobile/lib/core/router/app_router.dart   (UPDATE — LearningPathScreen 교체, outcome placeholder 추가)
mobile/lib/core/router/app_router.g.dart (UPDATE — build_runner 재생성)
mobile/lib/features/home/screens/learning_path_screen.dart  (NEW)
mobile/pubspec.yaml                      (UPDATE — url_launcher 추가, 없는 경우)
```

### References

- 에픽: `_bmad-output/planning-artifacts/epics.md` — Story 4.1 (line 663–692), Epic 4 설명 (line 178–184)
- UX: `_bmad-output/planning-artifacts/ux-designs/ux-decision-os-2026-07-21/EXPERIENCE.md` — Learning Path Card (line 249–271), Learning Path States (line 415–422)
- UX: DESIGN.md — UX-DR6 LearningPathCard 컴포넌트 스펙
- 아키텍처: `_bmad-output/planning-artifacts/architecture/architecture-decision-os-2026-07-21/ARCHITECTURE-SPINE.md` — AD-3, AD-5, AD-6, AD-11, AD-12, AD-14
- DB 스키마: `supabase/migrations/20260723000000_initial_schema.sql` (learning_paths 테이블, outcomes 테이블, RLS 정책)
- 기존 Reviewer 패턴: `api/pipeline/reviewer.py`, `api/routers/reviews.py`
- 기존 LLM 인터페이스: `api/pipeline/llm/base.py`, `api/pipeline/llm/openai_provider.py`
- 기존 Decision 라우터: `api/routers/decisions.py` (권한 검증 패턴)
- Flutter StreamProvider 패턴: `mobile/lib/features/home/providers/research_review_provider.dart`
- Flutter 로딩 위젯: `mobile/lib/features/home/widgets/three_dot_loading_indicator.dart`
- 이전 스토리: `_bmad-output/implementation-artifacts/3-4-contextual-chat.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `api/pipeline/reviewer.py:193`에서 기존 `OpenAIProvider()` 무인자 호출 패턴(사전 존재 버그, `api_key` 필수 인자 누락)을 Dev Notes 지시대로 `coach.py`에서 동일하게 답습함 — 이 스토리 범위 밖이므로 별도 수정하지 않음.
- `web/src/app/(app)/home/review/[signalId]/chat/page.tsx`(기존 파일, 미수정)에서 Supabase 쿼리 빌더 `.then().catch()` 체이닝 시 `tsc` 오류 발생을 확인 — 동일 패턴을 신규 `learning-path/page.tsx`에서는 async IIFE + try/catch로 회피. `chat/page.tsx` 자체는 이 스토리 범위 밖이라 수정하지 않음.
- Flutter `mobile/test/profile_test.dart`에 사전 존재 구문 오류(line 210, `Expected an identifier`) 및 `lib/features/profile/screens/profile_screen.dart:150`의 `AppSettings.openNotificationSettings` 미정의 오류(설치된 `app_settings 5.2.0`에는 없는 메서드, `pubspec.yaml` 제약 `^5.1.1`이 이미 5.2.0을 허용)를 확인 — 둘 다 이 스토리가 건드리지 않는 파일이며 `flutter analyze`/`flutter test` 전체 실행 시 무관한 3개 테스트 파일 로딩 실패로 나타남. 신규/수정 파일(`learning_path_provider.dart`, `learning_path_screen.dart`, `app_router.dart`)은 개별 analyze 시 0 issues, 관련 없는 회귀 아님.

### Completion Notes List

- API: `LearningPathContext` + `LLMProvider.generate_learning_path()` 추상 메서드, `OpenAIProvider.generate_learning_path()` (Responses API 전용, AD-6) 구현. `MockLLMProvider`에 stub 추가로 기존 테스트 회귀 방지.
- API: `coach.py`는 `reviewer.py`의 `pending → processing → completed|failed` 패턴을 그대로 적용. `decision_id → review_id → project_id → user_id → user_profiles.project_goal` 4단계 조회로 개인화 컨텍스트 구성.
- API: `POST /api/v1/learning-paths/trigger`는 소유권 검증(다른 사용자 decision → 404), `choice != 'learn_now'` → 422, 멱등성(pending/processing 존재 시 기존 ID 반환) 모두 구현.
- API: `test_learning_paths.py` 8개 신규 테스트 전부 통과, 기존 테스트 포함 전체 104/104 통과 (회귀 없음).
- Web: `learning-path/page.tsx`는 reviews → decisions → learning_paths 순차 조회 후 없으면 trigger, Supabase Realtime UPDATE 구독으로 완료 감지. `visibilitychange` 이벤트로 외부 링크 방문 후 복귀를 감지해 Outcome 프롬프트 표시.
- Web: `npx tsc --noEmit` 확인 결과 신규/수정 파일은 0 오류. `next build`는 기존 `chat/page.tsx`의 사전 존재 오류로 인해 완주하지 못함(범위 밖, Debug Log 참조).
- Flutter: `learning_path_provider.dart`는 `research_review_provider.dart`의 `StreamProvider` + `onPostgresChanges` Realtime 구독 패턴을 그대로 따름 (Dev Notes가 언급한 `.stream()` API 대신 기존 코드베이스 컨벤션과의 일관성을 위해 `.channel().onPostgresChanges()` 사용).
- Flutter: `url_launcher: ^6.3.1`을 `pubspec.yaml`에 추가, `flutter pub get` + `build_runner build --delete-conflicting-outputs`로 `learning_path_provider.g.dart`, `app_router.g.dart` 재생성 완료.
- Flutter: `app_router.dart`에서 `_LearningPathPlaceholderScreen` 삭제, `LearningPathScreen` 실연결. `outcome` GoRoute는 `learning-path`의 형제 경로로 추가(웹 라우트 구조와 동일하게 `review/:signalId/outcome`).
- Flutter: `flutter analyze`로 신규/수정 3개 파일(`learning_path_provider.dart`, `learning_path_screen.dart`, `app_router.dart`) 확인 결과 0 issues.

### File List

api/pipeline/llm/base.py
api/pipeline/llm/openai_provider.py
api/pipeline/coach.py
api/routers/learning_paths.py
api/main.py
api/tests/test_learning_paths.py
api/tests/test_signal_builder_reviewer.py
api/tests/mocks.py
supabase/migrations/20260727000000_learning_paths_unique_active.sql
web/src/app/(app)/home/review/[signalId]/learning-path/page.tsx
web/src/app/(app)/home/review/[signalId]/outcome/page.tsx
web/src/components/home/learning-path/learning-path-card.tsx
mobile/lib/features/home/providers/learning_path_provider.dart
mobile/lib/features/home/providers/learning_path_provider.g.dart
mobile/lib/features/home/screens/learning_path_screen.dart
mobile/lib/core/router/app_router.dart
mobile/lib/core/router/app_router.g.dart
mobile/pubspec.yaml
mobile/pubspec.lock

## Change Log

- 2026-07-27: Story 4-1 Learning Path 생성 & 화면 전체 구현 (claude-sonnet-4-6)
  - API: LearningPathContext 데이터클래스 + LLMProvider.generate_learning_path() abstract 추가, OpenAIProvider.generate_learning_path() 구현 (Responses API 전용)
  - API: coach.py 신규 생성 — pending → processing → completed|failed BackgroundTask 파이프라인, user_profiles.project_goal 기반 개인화 컨텍스트 구성
  - API: POST /api/v1/learning-paths/trigger 라우터 신규 생성 (소유권 검증, 422/404 처리, 멱등성), main.py 등록
  - API: test_learning_paths.py 8개 테스트 작성 (전부 통과), 기존 테스트 포함 전체 104/104 통과, 회귀 없음
  - Web: learning-path/page.tsx 실구현 (로딩/완료/실패 4상태, Realtime 구독, 외부 링크 방문 감지 → Outcome 프롬프트), learning-path-card.tsx 신규 생성
  - Web: outcome/page.tsx placeholder 신규 생성 (Story 4.2 구현 대상)
  - Flutter: learning_path_provider.dart 신규 생성 (StreamProvider + Realtime 구독, research_review_provider.dart 패턴 답습)
  - Flutter: learning_path_screen.dart 신규 생성 (로딩/완료/실패 UI, LearningPathCard, Outcome 프롬프트, url_launcher 연동)
  - Flutter: app_router.dart에서 _LearningPathPlaceholderScreen → LearningPathScreen 교체, outcome GoRoute 추가, pubspec.yaml에 url_launcher 추가

- 2026-07-27: 코드 리뷰 Patch 13건 일괄 적용 (claude-sonnet-4-6)
  - API: `coach.py` — `OpenAIProvider()` 무인자 호출 크래시 수정(api_key/model 명시 전달), 실패 상태 업데이트 자체 실패 시 로깅 추가, signal/decision/review/project 조회 실패를 `_fetch_one_or_raise()` 헬퍼로 통합해 중복 제거
  - API: `routers/learning_paths.py` — `/trigger`의 존재확인↔INSERT TOCTOU 레이스를 DB 유니크 제약 + `APIError(23505)` 캐치 후 재조회 폴백으로 차단 (마이그레이션 `20260727000000_learning_paths_unique_active.sql` 추가: `decision_id`에 `pending`/`processing`만 대상인 부분 유니크 인덱스)
  - API: `pipeline/llm/openai_provider.py` — `generate_learning_path()` 응답의 리소스별 필수 키 + URL 스킴(http/https만 허용) 검증 추가
  - API: `tests/mocks.py` 신규 — `test_signal_builder_reviewer.py`/`test_learning_paths.py`가 공유하던 `MockLLMProvider`를 공용 모듈로 분리(테스트 파일 간 결합 제거); `test_learning_paths.py`의 파이프라인 테스트는 `pipeline.coach` 내부 모킹 대신 `_execute_learning_path_pipeline(...)`에 client/llm을 직접 주입하도록 재구성(AD-11 정신에 부합, `reviewer.py` 테스트 관례와 동일), entrypoint 위임 검증용 테스트 1건 추가, TOCTOU 레이스 회귀 테스트 1건 추가
  - Web: `learning-path/page.tsx` — Supabase 응답 `.error` 미검사, 가드 없는 `.single()`, `resolveAndStart`의 `cancelled` 가드 누락 수정; 초기 조회~Realtime 구독 연결 사이의 상태 전이 누락 레이스를 구독 직후 1회 재확인으로 축소
  - Web: `learning-path-card.tsx` — `window.open` 전 URL 스킴(http/https) 검증 추가
  - Flutter: `learning_path_provider.dart` — `@riverpod` 함수형 StreamProvider를 클래스 기반 `LearningPathController`(`_$LearningPathController`)로 전환해 "다시 시도하기"가 실제로 `/trigger`를 재호출하는 명시적 `retry()` 메서드 추가(기존에는 실패 row를 재확인만 하고 재트리거 없이 종료); 구독 직후 1회 상태 재확인으로 웹과 동일하게 레이스 축소
  - Flutter: `learning_path_screen.dart` — 초기 로딩(`AsyncValue.loading`)에 `_GeneratingBody` 표시(AC-2 스펙 일치), `_handleTap`이 `launchUrl` 반환값 확인 후에만 `onVisit()` 호출 + URL 스킴 미검증/파싱 실패 시 SnackBar 피드백 추가, GitHub 라벨에 `Localizations.override(locale: en)` + `Semantics`로 웹 `lang="en"`과 동등한 접근성 마킹 추가
  - Flutter: `learning_path_provider.g.dart` — `build_runner build --delete-conflicting-outputs`로 재생성(`LearningPathController` 반영)
  - 검증: API 전체 106/106 통과, `flutter analyze`(대상 파일) 0 issues, 웹 `tsc --noEmit`(대상 파일) 0 오류
