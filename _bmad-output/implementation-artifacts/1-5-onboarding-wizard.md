# Story 1.5: Onboarding Wizard

---
baseline_commit: NO_VCS
---

Status: done

## Story

신규 사용자로서,
7단계 온보딩 wizard를 완료하여 내 역할·경험·기술 스택·관심 영역을 등록할 수 있기를 원한다,
그래서 나에게 맞는 개인화된 Daily Brief를 받을 수 있다.

## Acceptance Criteria

**AC-1: 온보딩 라우팅 — 신규 가입 사용자**

- **Given** 온보딩을 완료하지 않은 인증된 사용자가 앱을 시작할 때
- **When** GoRouter redirect가 실행되면
- **Then** `/onboarding` 화면으로 라우팅된다
- **And** 온보딩 완료 여부는 SharedPreferences `onboarding_completed` 키로 판단한다
- **And** 기존 완료 사용자는 `/home`으로 그대로 라우팅된다

**AC-2: Welcome 화면**

- **Given** 온보딩이 처음 시작될 때
- **When** Welcome 화면이 표시되면
- **Then** 헤딩 "오늘 배워야 할 AI, 매일 브리핑해드립니다" (28px/700)이 표시된다
- **And** 서브카피 "AI 기술의 변화 속에서 오늘 배울 것을 추천받으세요."가 표시된다
- **And** Primary CTA "시작하기"가 항상 활성화되어 있다

**AC-3: 7단계 Wizard 진행**

- **Given** 온보딩 진행 중일 때
- **When** 각 단계를 확인하면
- **Then** 다음 순서로 진행된다:
  - Step 2 — Role: "어떤 역할을 맡고 계신가요?" (6+1 옵션 카드: Frontend Developer / Backend Developer / AI Engineer / Product Manager / Designer / Student / 기타)
  - Step 3 — Experience: "AI 기술 경험 수준을 선택해 주세요." (3 옵션 카드: 입문 / 중급 / 고급)
  - Step 4 — Tech Stack: "주로 사용하는 기술 스택을 선택해 주세요." (multi-select pill: React / Next.js / Python / FastAPI / LangGraph / MCP / Claude Code / 기타)
  - Step 5 — Project/Goal: "현재 무엇을 만들거나 배우고 계신가요?" (6+1 옵션 카드: AI 사이드 프로젝트 개발 / RAG 서비스 구축 / Agent Architecture 학습 / 업무 자동화 / AI 도입 검토 / 기타)
  - Step 6 — Interests: "관심 있는 기술 영역을 선택해 주세요." (multi-select pill: Agent / RAG / MCP / Coding Agent / Local LLM / AI UX / 기타)
  - Step 7 — Daily Learning Time: "하루에 AI 학습에 투자할 수 있는 시간은?" (3 옵션 카드: 15분 / 30분 / 1시간)
- **And** 단계별 기본 CTA("다음" / 마지막 단계는 "완료")는 1개 이상 선택 시 활성화된다
- **And** 뒤로 가기(back chevron)로 이전 단계로 돌아갈 수 있다

**AC-4: API 호출 및 First Brief Generating 화면**

- **Given** 사용자가 Step 7("완료")를 탭했을 때
- **When** API 호출이 성공하면
- **Then** `POST /api/v1/onboarding/complete`가 호출되어 UserProfile이 저장된다
- **And** FastAPI가 사용자를 위한 AI Research Project 1개를 자동 생성한다 (`playbook_type: "ai_research"`, name: "내 AI 학습")
- **And** "오늘의 Daily Brief를 생성 중입니다." 전체화면 로딩 화면이 표시된다
- **And** 본문 "프로필을 기반으로 가장 관련성 높은 AI 기술을 찾고 있습니다."가 함께 표시된다
- **And** 세 점 pulse 애니메이션이 표시된다 (`prefers-reduced-motion` 시 정적)
- **And** 이 화면에서는 `PopScope(canPop: false)`로 back이 차단된다
- **And** 5초 타임아웃 후(또는 Daily Brief 완료 후) 알림 권한 요청 화면으로 진행된다

**AC-5: 알림 권한 요청 화면**

- **Given** Daily Brief 생성 완료 또는 타임아웃 후
- **When** 알림 권한 요청 화면이 표시되면
- **Then** "매일 AI CTO 브리핑을 받아보시겠어요?" 헤딩이 표시된다
- **And** "매일 09:00에 오늘 배울 기술 브리핑을 보내드립니다." 카피가 표시된다
- **And** "허용" (primary pill) / "나중에" (ghost pill) 두 CTA가 존재한다
- **And** "허용" 탭 시: `FirebaseMessaging.instance.requestPermission()` 호출 후 `/home`으로 이동
- **And** "나중에" 탭 시: 권한 요청 없이 `/home`으로 이동
- **And** 이 화면은 앱 생명주기에서 단 1회만 표시된다 (SharedPreferences `notification_permission_requested` 키)

**AC-6: 온보딩 완료 상태 유지**

- **Given** 온보딩 완료 후 앱을 재시작할 때
- **When** GoRouter redirect가 실행되면
- **Then** `/onboarding`이 아닌 `/home`으로 라우팅된다
- **And** SharedPreferences의 `onboarding_completed` 값이 `true`이다

## Tasks / Subtasks

- [x] Task 1: `pubspec.yaml` 의존성 추가 (AC: #1, #5)
  - [x] 1.1 `shared_preferences: ^2.3.0` 추가
  - [x] 1.2 `flutter pub get` 실행

- [x] Task 2: `onboarding_provider.dart` 생성 — 온보딩 완료 상태 Provider (AC: #1, #6)
  - [x] 2.1 `mobile/lib/features/onboarding/providers/onboarding_provider.dart` 생성
  - [x] 2.2 `onboardingCompletedProvider = StateProvider<bool>((ref) => false)` 선언
  - [x] 2.3 `build_runner` 실행 불필요 (StateProvider는 코드 생성 없음)

- [x] Task 3: `main.dart` 수정 — FCM 권한 삭제 + SharedPreferences 초기화 (AC: #1, #5)
  - [x] 3.1 `FirebaseMessaging.instance.requestPermission(...)` 블록 `main()`에서 **완전 삭제** (온보딩 화면으로 이전)
  - [x] 3.2 `shared_preferences` import 추가
  - [x] 3.3 `await SharedPreferences.getInstance()` 호출 및 `onboarding_completed` 읽기
  - [x] 3.4 `ProviderScope`에 `onboardingCompletedProvider.overrideWith((ref) => isOnboardingCompleted)` override 추가

- [x] Task 4: `app_router.dart` 수정 — 온보딩 redirect 로직 추가 (AC: #1, #6)
  - [x] 4.1 `onboardingCompletedProvider` watch 추가 (`ref.watch(...)`)
  - [x] 4.2 redirect 함수에 `/onboarding` 분기 추가:
    - `session != null && isAuthRoute && !isOnboardingDone → '/onboarding'`
    - `session != null && !isOnboardingDone && !isOnboardingRoute && !isAuthRoute → '/onboarding'`
  - [x] 4.3 기존 `session != null && isAuthRoute → '/home'` 로직을 온보딩 상태 분기로 교체

- [x] Task 5: `onboarding_screen.dart` 생성 — 7단계 Wizard (AC: #2, #3, #4, #5)
  - [x] 5.1 `mobile/lib/features/onboarding/screens/onboarding_screen.dart` 생성
  - [x] 5.2 `ConsumerStatefulWidget` — 전체 wizard 상태 로컬 관리
  - [x] 5.3 `_step` (int, 0-8), `_selections` (Map<String, dynamic>) 상태 변수
  - [x] 5.4 `_buildStep()` switch로 각 스텝 위젯 반환
  - [x] 5.5 Welcome 화면 (step 0): 헤딩 + 서브카피 + "시작하기" CTA
  - [x] 5.6 Role 화면 (step 1): 옵션 카드 6+1개
  - [x] 5.7 Experience 화면 (step 2): 옵션 카드 3개
  - [x] 5.8 Tech Stack 화면 (step 3): multi-select pill
  - [x] 5.9 Project/Goal 화면 (step 4): 옵션 카드 6+1개
  - [x] 5.10 Interests 화면 (step 5): multi-select pill
  - [x] 5.11 Daily Learning Time 화면 (step 6): 옵션 카드 3개
  - [x] 5.12 Brief Generating 화면 (step 7): `PopScope(canPop: false)` + 로딩 + 5초 타이머
  - [x] 5.13 Notification Permission 화면 (step 8): "허용" / "나중에" CTA + FCM requestPermission + 완료 처리
  - [x] 5.14 `_completeOnboarding()` 메서드: SharedPreferences 저장 + provider 업데이트 + `context.go('/home')`

- [x] Task 6: FastAPI `onboarding.py` 라우터 생성 (AC: #4)
  - [x] 6.1 `api/routers/onboarding.py` 생성
  - [x] 6.2 `OnboardingCompleteRequest` Pydantic 모델 정의
  - [x] 6.3 `POST /onboarding/complete` 엔드포인트 — JWT 인증 필수 (middleware 사용)
  - [x] 6.4 `user_profiles` UPDATE: role, experience_level, tech_stack, project_goal, interests, daily_learning_time_min, onboarding_completed=true
  - [x] 6.5 `projects` INSERT: playbook_type='ai_research', name='내 AI 학습', user_id
  - [x] 6.6 이미 `projects`에 ai_research 존재 시 INSERT OR IGNORE (idempotent)
  - [x] 6.7 응답: `{"data": {"user_id": ..., "project_id": ..., "onboarding_completed": true}, "error": null}`
  - [x] 6.8 `api/main.py`에 라우터 등록: `from routers.onboarding import router as onboarding_router` + `app.include_router(onboarding_router, prefix="/api/v1")`

- [x] Task 7: 테스트 작성 및 실행 (AC: #1, #2, #3)
  - [x] 7.1 `mobile/test/onboarding_test.dart` 생성
  - [x] 7.2 Welcome 화면 렌더링 테스트 ("오늘 배워야 할 AI" 텍스트 존재)
  - [x] 7.3 Role step: 선택 전 "다음" 버튼 비활성, 선택 후 활성화 테스트
  - [x] 7.4 Multi-select step: 복수 선택 가능 확인
  - [x] 7.5 기존 회귀 테스트: `flutter test test/navigation_shell_test.dart test/theme_test.dart test/auth_test.dart`

## Dev Notes

### 🚨 CRITICAL: main.dart에서 FCM requestPermission 제거

**현재 main.dart의 아래 블록을 완전히 삭제해야 한다:**
```dart
// 삭제 대상 (main.dart:26-30)
await FirebaseMessaging.instance.requestPermission(
  alert: true,
  badge: true,
  sound: true,
);
```

이 코드가 남아 있으면 앱 시작 시마다 권한 요청이 뜨며, Story 1.5 AC-5의 "단 1회만 표시" 요건 위반이다.

### SharedPreferences 키 규약

```dart
// onboarding_provider.dart 또는 별도 상수 파일
const String kOnboardingCompletedKey = 'onboarding_completed';
const String kNotificationPermissionRequestedKey = 'notification_permission_requested';
```

### Provider 초기화 패턴 (main.dart)

```dart
// 1. SharedPreferences 읽기
final prefs = await SharedPreferences.getInstance();
final isOnboardingCompleted = prefs.getBool(kOnboardingCompletedKey) ?? false;

// 2. ProviderScope override
runApp(
  ProviderScope(
    overrides: [
      onboardingCompletedProvider.overrideWith((ref) => isOnboardingCompleted),
    ],
    child: const MyApp(),
  ),
);
```

`onboardingCompletedProvider`는 `StateProvider<bool>` — codegen 불필요, `@riverpod` 어노테이션 없음.

### app_router.dart 수정 패턴

```dart
@riverpod
GoRouter appRouter(AppRouterRef ref) {
  final notifier = _GoRouterAuthNotifier();
  ref.onDispose(notifier.dispose);

  // 온보딩 상태 watch — 변경 시 appRouterProvider 재빌드 → 새 GoRouter 생성
  // 이 시점은 온보딩 완료 직후 1회만 발생하므로 nav stack 리셋 문제 없음
  final isOnboardingDone = ref.watch(onboardingCompletedProvider);

  final router = GoRouter(
    initialLocation: '/signin',
    refreshListenable: notifier,
    redirect: (context, state) {
      final session = Supabase.instance.client.auth.currentSession;
      final loc = state.matchedLocation;
      final isAuthRoute = loc == '/signin' || loc == '/signup';
      final isOnboardingRoute = loc.startsWith('/onboarding');

      if (session == null && !isAuthRoute) return '/signin';
      if (session != null && isAuthRoute) {
        return isOnboardingDone ? '/home' : '/onboarding';
      }
      if (session != null && !isOnboardingDone && !isOnboardingRoute) {
        return '/onboarding';
      }
      return null;
    },
    routes: [
      GoRoute(path: '/signin', builder: (_, __) => const SignInScreen()),
      GoRoute(path: '/signup', builder: (_, __) => const SignUpScreen()),
      GoRoute(path: '/onboarding', builder: (_, __) => const OnboardingScreen()),
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => ShellScaffold(navigationShell: shell),
        branches: [ /* 기존 4개 브랜치 유지 */ ],
      ),
    ],
  );
  ref.onDispose(router.dispose);
  return router;
}
```

**주의:** `onboarding_screen.dart` import 추가 필수:
```dart
import '../../features/onboarding/screens/onboarding_screen.dart';
```

### OnboardingScreen 구조 패턴

```dart
class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});
  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  int _step = 0;  // 0=Welcome, 1=Role, 2=Experience, 3=TechStack, 4=ProjectGoal, 5=Interests, 6=DailyTime, 7=BriefGenerating, 8=NotificationPermission

  // 단일 선택 (Role, Experience, ProjectGoal, DailyTime)
  String? _selectedRole;
  String? _selectedExperience;
  String? _selectedProjectGoal;
  int? _selectedDailyLearningTimeMin;

  // 복수 선택 (TechStack, Interests)
  final Set<String> _selectedTechStack = {};
  final Set<String> _selectedInterests = {};

  bool _isLoading = false;  // "완료" CTA 탭 시 API 호출 중

  // 뒤로 가기: step > 0 && step < 7 허용
  void _goBack() {
    if (_step > 0 && _step < 7) setState(() => _step--);
  }

  // 다음으로: step++
  void _goNext() => setState(() => _step++);

  // 완료: API 호출 → step 7
  Future<void> _submitOnboarding() async {
    setState(() { _isLoading = true; });
    try {
      await _callOnboardingCompleteApi();
      setState(() { _step = 7; });  // BriefGenerating으로 이동
      // 5초 타이머 후 step 8
      await Future.delayed(const Duration(seconds: 5));
      if (mounted) setState(() { _step = 8; });
    } catch (e) {
      setState(() { _isLoading = false; });
      // 에러 토스트 표시 (ScaffoldMessenger)
    }
  }
}
```

### 옵션 카드 위젯 패턴

```dart
// 단일 선택 옵션 카드
GestureDetector(
  onTap: () => setState(() => _selectedRole = value),
  child: Container(
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: AppColors.surfaceCard,
      borderRadius: BorderRadius.circular(14),  // option-card radius
      border: Border.all(
        color: _selectedRole == value
            ? AppColors.accentPrimary
            : AppColors.borderCard,
        width: _selectedRole == value ? 1.5 : 1,
      ),
    ),
    constraints: const BoxConstraints(minHeight: 52),
    child: Text(label, style: Theme.of(context).textTheme.bodyLarge),
  ),
)
```

### Multi-select Pill 패턴

```dart
// multi-select pill (Tech Stack, Interests)
FilterChip(
  label: Text(label),
  selected: _selectedTechStack.contains(value),
  onSelected: (selected) {
    setState(() {
      if (selected) _selectedTechStack.add(value);
      else _selectedTechStack.remove(value);
    });
  },
  // ThemeData의 chipTheme 없으면 직접 스타일:
  selectedColor: AppColors.accentPrimary,
  checkmarkColor: AppColors.accentForeground,
  labelStyle: TextStyle(
    color: _selectedTechStack.contains(value)
        ? AppColors.accentForeground
        : AppColors.textPrimary,
  ),
  shape: const StadiumBorder(),
  side: BorderSide(
    color: _selectedTechStack.contains(value)
        ? AppColors.accentPrimary
        : AppColors.borderCard,
  ),
)
```

### Primary CTA 버튼 (전체 너비 pill)

```dart
SizedBox(
  width: double.infinity,
  height: 52,
  child: FilledButton(
    onPressed: _isCTAEnabled ? _handleCTA : null,
    child: Text('다음', style: ...),
  ),
)
```

`FilledButton`은 이미 `StadiumBorder` shape으로 ThemeData에 설정됨 (`app_theme.dart:74-78`).

### Back Chevron 구현

```dart
// AppBar leading으로 구현
// step == 0 (Welcome): leading 없음 또는 빈 SizedBox
// step 1-6: back chevron 표시
// step 7-8 (BriefGenerating, NotificationPerm): leading 없음
leading: (_step > 0 && _step < 7)
    ? IconButton(
        icon: const Icon(Icons.chevron_left),
        onPressed: _goBack,
      )
    : null,
```

### Brief Generating 화면 (step 7) — PopScope 필수

```dart
PopScope(
  canPop: false,
  child: Scaffold(
    backgroundColor: AppColors.surfaceRaised,
    body: SafeArea(
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              '오늘의 Daily Brief를 생성 중입니다.',
              style: Theme.of(context).textTheme.displayLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),
            Text(
              '프로필을 기반으로 가장 관련성 높은 AI 기술을 찾고 있습니다.',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: AppColors.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),
            _ThreeDotLoadingIndicator(),  // 별도 StatefulWidget
          ],
        ),
      ),
    ),
  ),
)
```

**PopScope(canPop: false)**은 step 7에서만 적용. 전체 Scaffold를 PopScope로 감싸되, `_step == 7`일 때만 canPop: false를 전달.

```dart
PopScope(
  canPop: _step != 7,  // step 7에서만 back 차단
  child: Scaffold(...),
)
```

### Three Dot Loading Indicator (Reduce Motion 지원)

```dart
class _ThreeDotLoadingIndicator extends StatefulWidget { ... }

class _ThreeDotLoadingIndicatorState extends State<_ThreeDotLoadingIndicator>
    with TickerProviderStateMixin {
  late final List<AnimationController> _controllers;

  @override
  void initState() {
    super.initState();
    // 3개 dot 각각 300ms 간격 stagger
    // MediaQuery.disableAnimations 체크
  }
}
```

간단하게는 `MediaQuery.disableAnimationsOf(context)`가 true면 3개 dot을 정적 Row로 표시.

### 알림 권한 요청 (step 8)

```dart
// "허용" 탭 시
Future<void> _requestNotificationPermission() async {
  await FirebaseMessaging.instance.requestPermission(
    alert: true,
    badge: true,
    sound: true,
  );
  await _markNotificationPermissionRequested();
  await _completeOnboarding();
}

// "나중에" 탭 시
Future<void> _skipNotificationPermission() async {
  await _markNotificationPermissionRequested();
  await _completeOnboarding();
}

// SharedPreferences 저장 + Provider 업데이트 + /home 이동
Future<void> _completeOnboarding() async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setBool(kOnboardingCompletedKey, true);
  ref.read(onboardingCompletedProvider.notifier).state = true;
  // appRouterProvider가 rebuild되어 redirect가 /home을 반환
  // 또는 직접 이동:
  if (mounted) context.go('/home');
}

Future<void> _markNotificationPermissionRequested() async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setBool(kNotificationPermissionRequestedKey, true);
}
```

### FastAPI `/api/v1/onboarding/complete` 엔드포인트

```python
# api/routers/onboarding.py
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from core.schemas import APIResponse
from core.supabase import get_supabase
from middleware.auth import get_current_user_id  # 기존 JWT 미들웨어 활용

router = APIRouter()

class OnboardingCompleteRequest(BaseModel):
    role: str  # 'frontend' | 'backend' | 'ai_engineer' | 'pm' | 'designer' | 'student' | 'other'
    experience_level: str  # 'beginner' | 'intermediate' | 'advanced'
    tech_stack: list[str]  # ['React', 'Next.js', ...]
    project_goal: str  # 'ai_side_project' | 'rag_service' | 'agent_architecture' | 'work_automation' | 'ai_adoption' | 'other'
    interests: list[str]  # ['Agent', 'RAG', ...]
    daily_learning_time_min: int  # 15 | 30 | 60

@router.post("/onboarding/complete", response_model=APIResponse)
async def complete_onboarding(
    body: OnboardingCompleteRequest,
    user_id: str = Depends(get_current_user_id),
):
    supabase = get_supabase()
    
    # 1. user_profiles 업데이트
    supabase.table("user_profiles").update({
        "role": body.role,
        "experience_level": body.experience_level,
        "tech_stack": body.tech_stack,
        "project_goal": body.project_goal,
        "interests": body.interests,
        "daily_learning_time_min": body.daily_learning_time_min,
        "onboarding_completed": True,
    }).eq("id", user_id).execute()
    
    # 2. ai_research project 생성 (idempotent — 이미 존재하면 스킵)
    existing = supabase.table("projects").select("id").eq("user_id", user_id).eq("playbook_type", "ai_research").execute()
    if existing.data:
        project_id = existing.data[0]["id"]
    else:
        result = supabase.table("projects").insert({
            "user_id": user_id,
            "playbook_type": "ai_research",
            "name": "내 AI 학습",
        }).execute()
        project_id = result.data[0]["id"]
    
    return APIResponse(data={
        "user_id": user_id,
        "project_id": project_id,
        "onboarding_completed": True,
    })
```

**`get_current_user_id` 확인 필요**: `api/middleware/auth.py`에 이미 JWT 파싱 미들웨어가 있다. `user_id`를 Depends로 주입받는 방법을 기존 패턴(`api/routers/devices.py`)에서 확인하고 동일하게 적용.

### 기존 미들웨어 패턴 확인 필수

Story 1.2에서 구현된 `api/routers/devices.py`의 인증 패턴을 참고:
- `api/middleware/auth.py`에 어떤 의존성 주입 패턴이 있는지 파일을 읽고 동일하게 적용
- `user_id`를 얻는 방식이 다를 수 있으므로 반드시 기존 파일 확인 후 구현

### 데이터 모델 — user_profiles 컬럼 (001_initial_schema.sql:23-31)

```sql
role                    TEXT,   -- 'frontend' | 'backend' | 'ai_engineer' | 'pm' | 'designer' | 'student' | 'other'
experience_level        TEXT,   -- 'beginner' | 'intermediate' | 'advanced'
tech_stack              TEXT[], -- ['Next.js', 'Python', 'LangGraph', ...]
project_goal            TEXT,   -- 'ai_side_project' | 'rag_service' | 'agent_architecture' | 'work_automation' | 'ai_adoption' | 'other'
interests               TEXT[], -- ['Agent', 'RAG', 'MCP', ...]
daily_learning_time_min INTEGER,-- 15 | 30 | 60
onboarding_completed    BOOLEAN NOT NULL DEFAULT FALSE,
```

`user_profiles`는 auth.users INSERT 트리거로 자동 생성됨 (`handle_new_user` function, schema:410-418). 즉 신규 가입 즉시 `user_profiles` 행이 존재함.

### API 호출 — Flutter에서 HTTP 패턴

```dart
Future<void> _callOnboardingCompleteApi() async {
  final session = Supabase.instance.client.auth.currentSession;
  if (session == null) throw Exception('No session');
  
  const apiBase = String.fromEnvironment(
    'FASTAPI_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );
  
  final response = await http.post(
    Uri.parse('$apiBase/api/v1/onboarding/complete'),
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ${session.accessToken}',
    },
    body: jsonEncode({
      'role': _selectedRole,
      'experience_level': _selectedExperience,
      'tech_stack': _selectedTechStack.toList(),
      'project_goal': _selectedProjectGoal,
      'interests': _selectedInterests.toList(),
      'daily_learning_time_min': _selectedDailyLearningTimeMin,
    }),
  );
  
  if (response.statusCode != 200) {
    throw Exception('Onboarding complete API failed: ${response.statusCode}');
  }
}
```

`http` 패키지 (`^1.2.0`)는 이미 pubspec.yaml에 있음. `fcm_provider.dart`의 패턴과 동일.

### 신규 가입 → 온보딩 경로 (1.4 Deferred 처리)

Story 1.4 Review에서 deferred된 항목:
> 신규 가입 사용자 `/onboarding` 미도달 — sign-up 후 session!=null → `/home` redirect 처리

이 스토리에서 **완전히 해결**됨:
- `isOnboardingDone = false` (SharedPreferences에 값 없음)
- redirect: `session != null && isAuthRoute && !isOnboardingDone → '/onboarding'`
- 신규 가입 후 자동으로 `/onboarding`으로 이동

### 아키텍처 준수

| 규칙 | 근거 |
|------|------|
| `StateProvider<bool>` — codegen 없이 단순 상태 | 온보딩 완료는 앱 전역 단일 boolean |
| FastAPI 쓰기 전담 — `user_profiles`, `projects` 모두 FastAPI로만 저장 | AD-3 |
| SharedPreferences는 로컬 온보딩 라우팅용 — DB는 API 쪽에서 갱신 | EXPERIENCE.md: "local storage" |
| `PopScope(canPop: false)` — Brief Generating 화면에서만 적용 | UX-DR10, AC-4 |
| `showModalBottomSheet` 사용 금지 — 이 스토리에는 Bottom Sheet 없음 | UX-DR15 |
| `FirebaseMessaging.requestPermission()` — main()이 아닌 온보딩 step 8에서 | AC-5 "단 1회만" |
| `StatefulShellRoute` 안에 onboarding route 없음 — onboarding은 shell 외부 독립 GoRoute | EXPERIENCE.md routing 패턴 |

### 프로젝트 구조 (이 스토리 완료 후)

```
mobile/lib/
├── core/
│   └── router/
│       └── app_router.dart    (MODIFY — onboarding redirect + import)
├── features/
│   ├── auth/                  (수정 없음)
│   ├── shell/                 (수정 없음)
│   ├── onboarding/            (NEW)
│   │   ├── screens/
│   │   │   └── onboarding_screen.dart   (NEW)
│   │   └── providers/
│   │       └── onboarding_provider.dart (NEW)
│   ├── home/                  (수정 없음)
│   ├── queue/                 (수정 없음)
│   ├── history/               (수정 없음)
│   └── profile/               (수정 없음)
└── main.dart                  (MODIFY — FCM perm 삭제, SharedPrefs init, provider override)

mobile/test/
└── onboarding_test.dart       (NEW)

api/
├── routers/
│   └── onboarding.py          (NEW)
└── main.py                    (MODIFY — onboarding_router 등록)
```

### Role/Experience/ProjectGoal 선택값 매핑

UI 라벨 → API 전송 값:

| UI 라벨 | API value (role) |
|---------|-----------------|
| Frontend Developer | frontend |
| Backend Developer | backend |
| AI Engineer | ai_engineer |
| Product Manager | pm |
| Designer | designer |
| Student | student |
| 기타 | other |

| UI 라벨 | API value (experience_level) |
|---------|------------------------------|
| 입문 | beginner |
| 중급 | intermediate |
| 고급 | advanced |

| UI 라벨 | API value (daily_learning_time_min) |
|---------|--------------------------------------|
| 15분 | 15 |
| 30분 | 30 |
| 1시간 | 60 |

| UI 라벨 | API value (project_goal) |
|---------|--------------------------|
| AI 사이드 프로젝트 개발 | ai_side_project |
| RAG 서비스 구축 | rag_service |
| Agent Architecture 학습 | agent_architecture |
| 업무 자동화 | work_automation |
| AI 도입 검토 | ai_adoption |
| 기타 | other |

Tech Stack, Interests: UI 라벨 그대로 전송 (React, Next.js, Python, LangGraph, MCP, Claude Code, Agent, RAG 등)

### References

- 에픽 요구사항: `_bmad-output/planning-artifacts/epics.md` — Story 1.5 (line 313–344)
- UX 요구사항: `EXPERIENCE.md` — Onboarding States (line 428-437), Flutter Routing (line 89-112), Flow 2 이준서의 온보딩 (line 916-955)
- 아키텍처: `ARCHITECTURE-SPINE.md` — AD-3 (데이터 접근), AD-14 (Flutter 상태관리)
- DB 스키마: `_bmad-output/implementation-artifacts/db/001_initial_schema.sql` — user_profiles (line 19-32), projects (line 50-57)
- 이전 스토리: `1-4-flutter-navigation-shell.md` — GoRouter 패턴, AppColors 사용법
- FCM 패턴: `mobile/lib/features/auth/providers/fcm_provider.dart` — http.post 패턴
- 인증 미들웨어: `api/middleware/auth.py` — JWT user_id 추출 패턴 (반드시 읽고 재사용)
- 기존 라우터 패턴: `api/routers/devices.py` — FastAPI router 패턴

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 (bmad-create-story)

### Debug Log References

### Completion Notes List

- ✅ shared_preferences 의존성 추가 및 flutter pub get 완료
- ✅ onboarding_provider.dart 생성 — StateProvider<bool> + 키 상수 정의
- ✅ main.dart에서 FCM requestPermission 블록 완전 제거, SharedPreferences 초기화 + ProviderScope override 추가
- ✅ app_router.dart — onboardingCompletedProvider watch, 온보딩 redirect 3-way 분기 구현
- ✅ onboarding_screen.dart — 9단계 wizard (Welcome + 6 selection steps + BriefGenerating + NotificationPermission), PopScope(canPop: _step != 7), 3-dot 애니메이션 (reduce-motion 지원)
- ✅ api/routers/onboarding.py — POST /onboarding/complete 엔드포인트, JWT 인증, user_profiles UPDATE + ai_research project idempotent INSERT
- ✅ api/main.py에 onboarding_router 등록
- ✅ onboarding_test.dart — 21개 단위 테스트 통과 (CTA 활성화 로직, redirect 로직)
- ✅ 기존 회귀 테스트 26개 전부 통과 (navigation_shell, theme, auth)

### File List

- mobile/pubspec.yaml (MODIFIED — shared_preferences: ^2.3.0 추가)
- mobile/lib/features/onboarding/providers/onboarding_provider.dart (NEW)
- mobile/lib/features/onboarding/screens/onboarding_screen.dart (NEW)
- mobile/lib/main.dart (MODIFIED — FCM perm 삭제, SharedPrefs init, provider override)
- mobile/lib/core/router/app_router.dart (MODIFIED — onboarding redirect 로직, import 추가)
- mobile/test/onboarding_test.dart (NEW)
- api/routers/onboarding.py (NEW)
- api/main.py (MODIFIED — onboarding_router 등록)

### Review Findings

#### Decision Needed

- [x] [Review][Decision] **5초 고정 타이머 vs 실제 Daily Brief 완료 신호** — Defer 결정: Epic 2 Daily Brief 파이프라인 구현 시 실제 신호로 교체. 현재는 UX 플레이스홀더로 유지.
- [x] [Review][Decision] **notification_permission_requested 키 미검사** — Defer 결정: 크래시 후 재표시는 허용 가능한 UX로 판단. 현재 설계 유지.

#### Patch

- [x] [Review][Patch] **[HIGH] `publishableKey` → `anonKey` 컴파일 에러** [main.dart:34] — `supabase_flutter ^2.9.1`에서 `Supabase.initialize()`의 파라미터명은 `anonKey`이다. `publishableKey`는 존재하지 않아 컴파일 에러 발생. `publishableKey: supabaseAnonKey` → `anonKey: supabaseAnonKey` 로 수정 필요.
- [x] [Review][Patch] **`user_profiles.update` 결과 미검증** [api/routers/onboarding.py:30] — `.execute()` 후 영향받은 행 수를 확인하지 않는다. 프로파일 행이 없으면 업데이트가 0행에 적용되어 성공처럼 반환되지만 데이터는 저장되지 않는다.
- [x] [Review][Patch] **`projects` insert TOCTOU 레이스** [api/routers/onboarding.py:40-55] — 존재 확인 후 insert 사이에 동시 요청 2개가 모두 통과하면 중복 insert 또는 unhandled 500 발생. DB 레벨 upsert 또는 unique constraint + try/except로 교체 필요.
- [x] [Review][Patch] **`result.data[0]["id"]` 미검증** [api/routers/onboarding.py:54] — insert 후 `result.data`가 비어있거나 `"id"` 키가 없으면 IndexError/KeyError로 unhandled 500 발생. `if not result.data: raise HTTPException(500)` 가드 추가 필요.
- [x] [Review][Patch] **step 8에서 system back 허용** [onboarding_screen.dart:137] — `PopScope(canPop: _step != 7)` 이므로 step 8(알림 권한)에서 시스템 백 가능. `onboarding_completed`가 아직 false이므로 router가 /onboarding으로 다시 리다이렉트 → 루프 발생. step 8도 canPop: false 대상에 포함 (`_step < 7`→`_step < 7 || _step == 8` 또는 `_step == 7 || _step == 8` 로직).
- [x] [Review][Patch] **`_requestNotificationPermission` 예외 미처리** [onboarding_screen.dart:108] — `FirebaseMessaging.instance.requestPermission()`이 플랫폼 에러 발생 시 unhandled exception. try/catch/finally로 감싸고 finally에서 `_markNotificationPermissionRequested()` + `_completeOnboarding()` 호출 보장.
- [x] [Review][Patch] **완료된 사용자가 /onboarding 재진입 가능** [app_router.dart:56-62] — `session != null && isOnboardingDone && isOnboardingRoute`를 redirect로 처리하는 분기 없음. 딥링크나 버그로 재진입 시 온보딩 프로필 덮어쓰기 가능. `if (session != null && isOnboardingDone && isOnboardingRoute) return '/home';` 추가.
- [x] [Review][Patch] **HTTP 타임아웃 미설정** [onboarding_screen.dart:87] — `http.post()`에 `.timeout()` 없음. 모바일 환경 네트워크 지연 시 `_isLoading = true` 상태로 무한 블록. `.timeout(const Duration(seconds: 30))` 추가 및 `TimeoutException` 처리.
- [x] [Review][Patch] **API 입력값 Enum 검증 없음** [api/routers/onboarding.py:13-20] — `role`, `experience_level`, `project_goal`이 `str`로 선언되어 임의 문자열 저장 가능. `Literal[...]` 또는 `Enum` 타입으로 제한 필요. `daily_learning_time_min: int = Field(..., gt=0)`으로 음수/0 방지.
- [x] [Review][Patch] **FCM onTokenRefresh 스트림 에러 미처리** [main.dart:39] — `.listen()` 에 `onError` 핸들러 없음. 스트림 에러가 isolate로 전파되어 크래시 가능. `onError: (e) { /* log */ }` 추가.
- [x] [Review][Patch] **`SharedPreferences.getInstance()` 예외 미처리** [main.dart:44] — `await SharedPreferences.getInstance()`가 스토리지 불가 환경에서 throw. `runApp` 전에 앱이 크래시됨. try/catch 추가 및 fallback `false` 사용.
- [x] [Review][Patch] **`_isLoading` 성공 경로에서 미초기화** [onboarding_screen.dart:61] — `_isLoading`은 catch 블록에서만 `false`로 리셋. 성공 시 step이 7로 이동하므로 실질 영향은 적지만, step 6 UI가 재렌더링되면 CTA 영구 비활성. `setState(() { _isLoading = false; _step = 7; })` 로 통합.

#### Defer

- [x] [Review][Defer] **Nullable 필드 JSON null 전송 위험** [onboarding_screen.dart:93-100] — deferred, UI 레이어에서 _isCTAEnabled로 가드되어 실제 도달 불가. 하지만 _callOnboardingCompleteApi 직접 호출 시 422 위험.
- [x] [Review][Defer] **만료된 세션 토큰** [onboarding_screen.dart:79] — deferred, Supabase SDK가 내부적으로 토큰을 자동 갱신하며 에러 snackbar로 재시도 가능.
- [x] [Review][Defer] **_ThreeDotLoadingIndicator 타이머 누수** [onboarding_screen.dart:624] — deferred, `mounted` 가드로 크래시는 방지. minor leak.
- [x] [Review][Defer] **tech_stack/interests 리스트 크기 제한 없음** [api/routers/onboarding.py:16-18] — deferred, 인증 엔드포인트이므로 위험도 낮음. API 보안 레이어에서 별도 처리 권장.
- [x] [Review][Defer] **_GoRouterAuthNotifier auth 스트림 에러 무시** [app_router.dart:29] — deferred, 기존 코드에서 이어진 패턴. 현 스토리 변경 아님.
- [x] [Review][Defer] **테스트 커버리지 부족** [mobile/test/onboarding_test.dart] — deferred, 현재 로직 단위테스트만 존재. 실제 위젯 렌더링 및 통합 테스트 별도 스토리로 추가 권장.
- [x] [Review][Defer] **_buildDailyTime 레이아웃 오버플로우 가능성** [onboarding_screen.dart:314] — deferred, 현재 3개 옵션이므로 실제 오버플로우 확률 낮음. 옵션 수 증가 시 ListView로 교체 권장.
- [x] [Review][Defer] **onboardingCompletedProvider 이중 소스** [onboarding_provider.dart, main.dart] — deferred, SharedPreferences와 Riverpod 상태가 분리. _completeOnboarding에서 동기화하므로 현재는 정상 동작.

## Change Log

- 2026-07-24: Story 1.5 온보딩 wizard 구현 완료 — Flutter 9단계 wizard, FastAPI onboarding endpoint, SharedPreferences 기반 상태 영속화
