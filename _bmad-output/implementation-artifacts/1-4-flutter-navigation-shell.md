---
baseline_commit: NO_VCS
---

# Story 1.4: Flutter Navigation Shell

Status: done

## Story

Flutter 앱 사용자로서,
4개 탭으로 구성된 하단 내비게이션으로 앱을 탐색할 수 있기를 원한다,
그래서 탭별로 독립적인 내비게이션 스택이 유지되어 탭을 오가도 이전 위치가 보존된다.

## Acceptance Criteria

**AC-1: StatefulShellRoute.indexedStack — 4탭 브랜치**

- **Given** Flutter 앱이 실행 중일 때
- **When** GoRouter 설정을 확인하면
- **Then** `StatefulShellRoute.indexedStack`으로 4개 탭 브랜치(홈/큐/히스토리/프로필)가 설정되어 있다
- **And** 각 탭은 독립적인 `GlobalKey<NavigatorState>`를 보유한다
- **And** 탭 루트 경로: `/home`, `/queue`, `/history`, `/profile`

**AC-2: 탭 스택 독립성 — 이전 위치 보존**

- **Given** 사용자가 홈 탭의 특정 화면으로 내비게이션한 후 큐 탭으로 이동했을 때
- **When** 다시 홈 탭을 탭하면
- **Then** 홈 탭의 이전 화면 위치가 그대로 복원된다

**AC-3: Android back 버튼 — 최상위 탭에서 앱 종료**

- **Given** Android 사용자가 홈/큐/히스토리/프로필 최상위 탭에 있을 때
- **When** 시스템 back 버튼을 누르면
- **Then** 앱이 종료된다 (back 인터셉션 없음)

**AC-4: edge-to-edge + 상태 바 스타일**

- **Given** 앱이 실행 중일 때
- **When** 화면을 확인하면
- **Then** `SafeArea`가 모든 화면 본문에 적용되어 있다
- **And** `SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge)` 설정이 적용되어 있다
- **And** `SystemChrome.setSystemUIOverlayStyle(SystemUiOverlayStyle.dark)`로 상태 바 아이콘이 다크 모드이다

## Tasks / Subtasks

- [x] Task 1: `app_router.dart` — StatefulShellRoute.indexedStack + 스트림 기반 인증 (AC: #1, #2, #3)
  - [x] 1.1 모듈 레벨에 `GlobalKey<NavigatorState>` 4개 선언 (`_homeNavKey`, `_queueNavKey`, `_historyNavKey`, `_profileNavKey`)
  - [x] 1.2 `_GoRouterAuthNotifier extends ChangeNotifier` private 클래스 정의 — `onAuthStateChange` 스트림 구독 + `notifyListeners()` 브릿지 (deferred cold start flash 수정)
  - [x] 1.3 `@riverpod GoRouter appRouter(...)` 함수 수정:
        — `_GoRouterAuthNotifier` 생성 + `ref.onDispose(notifier.dispose)` 등록
        — `refreshListenable: notifier` 설정
        — `/signin`, `/signup` GoRoute 유지
        — `/onboarding` GoRoute 유지 (placeholder)
        — `StatefulShellRoute.indexedStack` 추가 (4개 브랜치, 각 GlobalKey 사용)
        — 홈/큐/히스토리/프로필 각 브랜치 GoRoute 연결
  - [x] 1.4 `redirect` 로직: 동기 `currentSession` 체크, auth 경로 ↔ 앱 경로 분기 유지
  - [x] 1.5 `build_runner` 실행: `dart run build_runner build --delete-conflicting-outputs` → `app_router.g.dart` 재생성

- [x] Task 2: `shell_scaffold.dart` 생성 — BottomNavigationBar + 상단 border (AC: #1, #2)
  - [x] 2.1 `mobile/lib/features/shell/shell_scaffold.dart` 생성
  - [x] 2.2 `ShellScaffold extends StatelessWidget` — `StatefulNavigationShell navigationShell` 파라미터
  - [x] 2.3 `Scaffold(body: navigationShell, bottomNavigationBar: ...)` 구조
  - [x] 2.4 `BottomNavigationBar`를 `DecoratedBox`로 감싸 상단 1px border 추가:
        `BoxDecoration(border: Border(top: BorderSide(color: AppColors.borderSubtle, width: 1)), color: AppColors.surfaceBase)`
  - [x] 2.5 `BottomNavigationBar` 설정: `currentIndex: navigationShell.currentIndex`, `onTap: (i) => navigationShell.goBranch(i, initialLocation: i == navigationShell.currentIndex)`, `elevation: 0`, `backgroundColor: AppColors.surfaceBase`, 4개 `BottomNavigationBarItem`

- [x] Task 3: 4개 Placeholder 화면 생성 (AC: #4)
  - [x] 3.1 `mobile/lib/features/home/screens/home_screen.dart` — `SafeArea` 래핑, 한국어 제목 + `<lang=en>` 영어 고유명사는 Flutter에서 `SelectableText`나 직접 텍스트로 구분 처리 불필요 (Flutter는 lang 속성 없음, 한국어 TTS는 OS 처리)
  - [x] 3.2 `mobile/lib/features/queue/screens/queue_screen.dart` — `SafeArea` 래핑
  - [x] 3.3 `mobile/lib/features/history/screens/history_screen.dart` — `SafeArea` 래핑
  - [x] 3.4 `mobile/lib/features/profile/screens/profile_screen.dart` — `SafeArea` 래핑
  - [x] 3.5 `PopScope` 미사용 확인 — 최상위 탭에서 back 인터셉션 없음 (AC-3)

- [x] Task 4: `main.dart` SystemChrome 설정 검증 (AC: #4)
  - [x] 4.1 `SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge)` 이미 구현됨 — 확인만
  - [x] 4.2 `SystemChrome.setSystemUIOverlayStyle(SystemUiOverlayStyle.dark)` 이미 구현됨 — 확인만

- [x] Task 5: 테스트 작성 및 실행
  - [x] 5.1 `mobile/test/navigation_shell_test.dart` — `ShellScaffold` 위젯 테스트: 4개 탭 항목 존재 확인, 탭 전환 시 인덱스 업데이트 확인
  - [x] 5.2 기존 `theme_test.dart`, `auth_test.dart` 회귀 테스트 실행 (`flutter test`)

## Dev Notes

### 🚨 CRITICAL: Deferred Cold Start Flash 수정 (이 스토리에서 반드시 해결)

**deferred-work.md에서 이 스토리로 인계된 항목:**

```
GoRouter 동기 session 읽기 cold start 깜빡임 (app_router.dart) — Story 1.3/1.4 StatefulShellRoute 교체 시 해결 예정
GoRouter authState 스트림 미연동 — Story 1.3/1.4 StatefulShellRoute 교체 시 해결 예정
```

**수정 방법:** `refreshListenable`에 auth state stream을 브릿지하는 `ChangeNotifier` 연결.
앱 시작 시 GoRouter가 `refreshListenable` 변경 시마다 redirect를 재평가하므로 cold start 후 세션이 복원되면 즉시 올바른 화면으로 이동.

### GoRouter 14.x StatefulShellRoute 패턴

**Navigator 키 — 모듈 레벨 선언 (함수 내부 X):**

```dart
// app_router.dart 최상단 (part 'app_router.g.dart'; 아래)
final _homeNavKey    = GlobalKey<NavigatorState>(debugLabel: 'home');
final _queueNavKey   = GlobalKey<NavigatorState>(debugLabel: 'queue');
final _historyNavKey = GlobalKey<NavigatorState>(debugLabel: 'history');
final _profileNavKey = GlobalKey<NavigatorState>(debugLabel: 'profile');
```

모듈 레벨로 선언해야 앱 전체 생명주기 동안 동일 키 인스턴스 보장.
`@riverpod` 함수 내부에 넣으면 provider 재생성 시 키가 교체되어 탭 스택이 초기화됨.

**Auth ChangeNotifier 브릿지:**

```dart
class _GoRouterAuthNotifier extends ChangeNotifier {
  late final StreamSubscription<AuthState> _sub;

  _GoRouterAuthNotifier() {
    _sub = Supabase.instance.client.auth.onAuthStateChange
        .listen((_) => notifyListeners());
  }

  @override
  void dispose() {
    _sub.cancel();
    super.dispose();
  }
}
```

**완성된 appRouter 구조:**

```dart
@riverpod
GoRouter appRouter(AppRouterRef ref) {
  final notifier = _GoRouterAuthNotifier();
  ref.onDispose(notifier.dispose);

  return GoRouter(
    initialLocation: '/signin',
    refreshListenable: notifier,
    redirect: (context, state) {
      final session = Supabase.instance.client.auth.currentSession;
      final loc = state.matchedLocation;
      final isAuthRoute = loc == '/signin' || loc == '/signup';

      if (session == null && !isAuthRoute) return '/signin';
      if (session != null && isAuthRoute) return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/signin',    builder: (_, __) => const SignInScreen()),
      GoRoute(path: '/signup',    builder: (_, __) => const SignUpScreen()),
      GoRoute(path: '/onboarding',
        builder: (_, __) => const Scaffold(
          body: Center(child: Text('Onboarding — Story 1.5')),
        ),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => ShellScaffold(navigationShell: shell),
        branches: [
          StatefulShellBranch(
            navigatorKey: _homeNavKey,
            routes: [GoRoute(path: '/home', builder: (_, __) => const HomeScreen())],
          ),
          StatefulShellBranch(
            navigatorKey: _queueNavKey,
            routes: [GoRoute(path: '/queue', builder: (_, __) => const QueueScreen())],
          ),
          StatefulShellBranch(
            navigatorKey: _historyNavKey,
            routes: [GoRoute(path: '/history', builder: (_, __) => const HistoryScreen())],
          ),
          StatefulShellBranch(
            navigatorKey: _profileNavKey,
            routes: [GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen())],
          ),
        ],
      ),
    ],
  );
}
```

### ShellScaffold — Border + BottomNavigationBar

```dart
// mobile/lib/features/shell/shell_scaffold.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';

class ShellScaffold extends StatelessWidget {
  const ShellScaffold({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: DecoratedBox(
        decoration: const BoxDecoration(
          border: Border(
            top: BorderSide(color: AppColors.borderSubtle, width: 1),
          ),
          color: AppColors.surfaceBase,
        ),
        child: BottomNavigationBar(
          currentIndex: navigationShell.currentIndex,
          onTap: (index) => navigationShell.goBranch(
            index,
            initialLocation: index == navigationShell.currentIndex,
          ),
          type: BottomNavigationBarType.fixed,
          backgroundColor: AppColors.surfaceBase,
          selectedItemColor: AppColors.textPrimary,
          unselectedItemColor: AppColors.textSecondary,
          elevation: 0,
          selectedFontSize: 10,
          unselectedFontSize: 10,
          items: const [
            BottomNavigationBarItem(icon: Icon(Icons.home_outlined),    activeIcon: Icon(Icons.home),    label: '홈'),
            BottomNavigationBarItem(icon: Icon(Icons.inbox_outlined),   activeIcon: Icon(Icons.inbox),   label: '큐'),
            BottomNavigationBarItem(icon: Icon(Icons.history_outlined), activeIcon: Icon(Icons.history), label: '히스토리'),
            BottomNavigationBarItem(icon: Icon(Icons.person_outlined),  activeIcon: Icon(Icons.person),  label: '프로필'),
          ],
        ),
      ),
    );
  }
}
```

**`goBranch(index, initialLocation: index == navigationShell.currentIndex)` 이유:**
- 이미 해당 탭에 있는 상태에서 탭을 다시 탭하면 해당 브랜치의 초기 경로로 리셋 (탭 재탭 리셋 동작)
- 다른 탭으로 이동할 때는 마지막 위치를 복원 (indexedStack 기본 동작)

### Placeholder 화면 패턴

```dart
// mobile/lib/features/home/screens/home_screen.dart
import 'package:flutter/material.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF9F9F9), // surface-raised
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('홈', style: Theme.of(context).textTheme.displayMedium),
              const SizedBox(height: 8),
              Text(
                'Daily Brief가 여기에 표시됩니다. — Story 2.4에서 구현 예정',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  color: const Color(0xFF595D6A),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

나머지 3개 화면(Queue, History, Profile)도 동일 패턴. 각 화면명과 예정 스토리 번호만 변경.

⚠️ **SafeArea는 각 개별 화면에서 적용** — `ShellScaffold`가 아닌 각 탭 화면에서.
⚠️ **`PopScope` 사용 금지** — 최상위 탭에서 back 버튼이 앱을 종료해야 함 (AC-3). GoRouter의 기본 동작이 탭 루트에서 back 가능한 경로가 없을 때 앱을 종료함.

### Android Back Button 동작

`StatefulShellRoute` + GoRouter 14.x에서: 각 브랜치 루트 경로에 있을 때 Android back 버튼을 누르면 GoRouter가 pop을 시도하지만 pop할 것이 없으므로 Flutter 기본 동작(앱 종료)이 실행됨.

**절대 하지 말 것:**
- `PopScope(canPop: false)` — 이것은 back을 막아 앱 종료를 방해함
- `WillPopScope` — deprecated이며 같은 문제

### build_runner 실행 명령

```bash
cd mobile
dart run build_runner build --delete-conflicting-outputs
```

`app_router.g.dart`는 코드 생성 결과물 — 수동 편집 금지. 커밋 포함.

### 테스트 전략

**단위/위젯 테스트 (`flutter test`):**

```dart
// mobile/test/navigation_shell_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:decision_os/features/shell/shell_scaffold.dart';
// ...

void main() {
  testWidgets('ShellScaffold BottomNavigationBar 4개 항목 표시', (tester) async {
    // BottomNavigationBar에 4개 항목이 있는지 확인
  });
}
```

기존 테스트 회귀 방지:
- `flutter test test/theme_test.dart` — ThemeData 검증 (기존 14개 통과 확인)
- `flutter test test/auth_test.dart` — Auth 관련 (기존 통과 확인)
- `flutter test test/widget_test.dart` — 기존 위젯 테스트

### 아키텍처 준수

| 규칙 | 근거 |
|------|------|
| Riverpod 2.x `@riverpod` 코드 생성 | AD-14 |
| GoRouter `StatefulShellRoute.indexedStack` | UX-DR9 |
| `GlobalKey<NavigatorState>` 모듈 레벨 선언 | 안정성 |
| SafeArea 각 화면 본문 적용 | UX-DR13 (WCAG 2.2 AA) |
| `PopScope` 미사용 (back → 앱 종료) | Story 1.4 AC-3 |
| `BottomNavigationBarThemeData` 기존 테마 사용 | `app_theme.dart` 기존 설정 |

### 프로젝트 구조 (이 스토리 완료 후)

```
mobile/lib/
├── core/
│   ├── router/
│   │   ├── app_router.dart    (MODIFY — StatefulShellRoute + stream auth)
│   │   └── app_router.g.dart  (REGENERATE)
│   └── theme/
│       └── app_theme.dart     (수정 없음)
├── features/
│   ├── auth/                  (수정 없음)
│   ├── shell/
│   │   └── shell_scaffold.dart  (NEW)
│   ├── home/
│   │   └── screens/
│   │       └── home_screen.dart  (NEW)
│   ├── queue/
│   │   └── screens/
│   │       └── queue_screen.dart  (NEW)
│   ├── history/
│   │   └── screens/
│   │       └── history_screen.dart  (NEW)
│   └── profile/
│       └── screens/
│           └── profile_screen.dart  (NEW)
├── firebase_options.dart  (수정 없음)
└── main.dart              (수정 없음 — SystemChrome 이미 설정됨)
```

### References

- 에픽 정의: `_bmad-output/planning-artifacts/epics.md` — Story 1.4 (line 285–311)
- 아키텍처: `ARCHITECTURE-SPINE.md` — AD-14 (Flutter 상태관리), AD-2 (스택)
- UX 요구사항: `DESIGN.md` — UX-DR9 (4탭 내비게이션), UX-DR13 (접근성), UX-DR15 (Material 3)
- 이전 스토리: `1-3-web-navigation-shell.md` — 웹 내비게이션 패턴 참고 (Flutter는 별도)
- 이전 스토리: `1-2-user-authentication.md` — GoRouter auth guard 패턴
- Deferred: `deferred-work.md` — GoRouter cold start flash (이 스토리에서 해결)
- Flutter pub: `go_router ^14.8.1`, `flutter_riverpod ^2.6.1`, `riverpod_annotation ^2.6.1`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 (bmad-create-story)

### Debug Log References

### Completion Notes List

- `app_router.dart` 수정: 모듈 레벨 GlobalKey 4개, `_GoRouterAuthNotifier` (auth stream → ChangeNotifier 브릿지), `StatefulShellRoute.indexedStack` 4브랜치 구성. cold start flash 해결.
- `shell_scaffold.dart` 신규 생성: `DecoratedBox`로 상단 1px border 적용한 `BottomNavigationBar`, `goBranch(index, initialLocation: ...)` 탭 재탭 리셋 동작 구현.
- 홈/큐/히스토리/프로필 4개 플레이스홀더 화면 생성: 각각 `SafeArea` 래핑, `PopScope` 미사용.
- `main.dart` SystemChrome 설정 확인: `edgeToEdge` + `SystemUiOverlayStyle.dark` 이미 구현됨.
- `build_runner` 실행으로 `app_router.g.dart` 재생성 완료.
- 신규 테스트 2개 (`navigation_shell_test.dart`) + 기존 회귀 25개 모두 통과.

### File List

- `mobile/lib/core/router/app_router.dart` (수정)
- `mobile/lib/core/router/app_router.g.dart` (재생성)
- `mobile/lib/features/shell/shell_scaffold.dart` (신규)
- `mobile/lib/features/home/screens/home_screen.dart` (신규)
- `mobile/lib/features/queue/screens/queue_screen.dart` (신규)
- `mobile/lib/features/history/screens/history_screen.dart` (신규)
- `mobile/lib/features/profile/screens/profile_screen.dart` (신규)
- `mobile/test/navigation_shell_test.dart` (신규)

### Review Findings

- [x] [Review][Patch] `onAuthStateChange` 스트림 `onError` 핸들러 누락 — 스트림 에러 시 구독 무음 종료, 이후 auth redirect 미동작 [mobile/lib/core/router/app_router.dart:27]
- [x] [Review][Patch] `GoRouter` 미dispose — `ref.onDispose(router.dispose)` 누락으로 hot-restart 시 내부 리스너 누수 [mobile/lib/core/router/app_router.dart:40]
- [x] [Review][Patch] `find.text('큐')` 모호한 finder — 동일 텍스트 위젯 다수 시 StateError; `find.descendant(of: find.byType(BottomNavigationBar), matching: find.text('큐'))` 로 범위 한정 필요 [mobile/test/navigation_shell_test.dart:69]
- [x] [Review][Defer] 신규 가입 사용자 `/onboarding` 미도달 [mobile/lib/core/router/app_router.dart:51] — deferred, sign-up 후 session!=null → `/home` redirect 처리; Story 1.5 온보딩 플로우에서 onboarding-seen 플래그 기반 redirect 추가 예정
- [x] [Review][Defer] 인증된 사용자의 404 경로에 `errorBuilder` 없음 [mobile/lib/core/router/app_router.dart:42] — deferred, GoRouter 기본 에러 화면 노출; 향후 NotFoundScreen 추가 예정
- [x] [Review][Defer] `ShellScaffold`에 `resizeToAvoidBottomInset: false` 미설정 [mobile/lib/features/shell/shell_scaffold.dart:12] — deferred, 향후 키보드 입력 화면 구현 시 동작 검토 필요
- [x] [Review][Defer] 인증 redirect 테스트 커버리지 없음 [mobile/test/navigation_shell_test.dart] — deferred, Supabase mock 복잡성으로 현재 스토리 범위 초과; 전용 라우터 테스트 스토리에서 처리

## Change Log

- 2026-07-24: Story 1.4 구현 완료 — `StatefulShellRoute.indexedStack` 4탭 내비게이션, auth stream ChangeNotifier 브릿지로 cold start flash 해결, 4개 플레이스홀더 화면 + `ShellScaffold` 생성, 테스트 27개 전체 통과
