---
baseline_commit: NO_VCS
---

# Story 1.2: User Authentication

Status: done

## Story

사용자로서,
이메일과 비밀번호로 계정을 만들고 로그인할 수 있기를 원한다,
그래서 내 학습 이력과 결정 기록이 내 계정에 안전하게 귀속된다.

## Acceptance Criteria

**AC-1: 신규 사용자 회원가입**

- **Given** 신규 사용자가 회원가입 화면에 있을 때
- **When** 이메일·비밀번호를 입력하고 가입 버튼을 누르면
- **Then** Supabase Auth를 통해 계정이 생성되고 세션이 시작된다
- **And** 온보딩 wizard 화면으로 이동한다
- **And** Next.js와 Flutter 모두 동일한 Supabase Auth를 사용한다

**AC-2: 기존 사용자 로그인**

- **Given** 기존 사용자가 로그인 화면에 있을 때
- **When** 등록된 이메일·비밀번호를 입력하면
- **Then** 세션이 복원되고 홈 화면(또는 미완료 온보딩)으로 이동한다
- **And** FastAPI 미들웨어가 `Authorization: Bearer {Supabase JWT}` 헤더를 검증한다

**AC-3: Flutter FCM 토큰 등록**

- **Given** 사용자가 로그인한 상태일 때
- **When** Flutter 앱 로그인·오픈 시
- **Then** FCM 토큰이 `POST /api/v1/devices/register`로 FastAPI에 등록되고 `user_devices` 테이블에 저장된다
- **And** FCM 토큰이 클라이언트 코드에 노출되지 않는다 (FastAPI 경유 전송)

**AC-4: 에러 처리**

- **Given** 잘못된 이메일/비밀번호가 입력되었을 때
- **When** 로그인을 시도하면
- **Then** 에러 메시지가 화면에 표시되고 앱 크래시 없이 계속 사용 가능하다

## Tasks / Subtasks

- [x] Task 1: FastAPI JWT 미들웨어 구현 (AC: #2)
  - [x] 1.1 `api/requirements.txt`에 `PyJWT[crypto]` 추가 (PyJWT는 supabase SDK 의존성으로 이미 설치됨 — 명시적 선언 추가)
  - [x] 1.2 `api/core/config.py`에 `supabase_jwt_secret: str = ""` 추가 (Supabase Settings → API → JWT Settings에서 획득)
  - [x] 1.3 `api/middleware/__init__.py` 생성
  - [x] 1.4 `api/middleware/auth.py` 생성 — `get_current_user` FastAPI Dependency (아래 Dev Notes 참조)
  - [x] 1.5 `api/tests/test_auth_middleware.py` 작성 — 유효 JWT / 만료 JWT / 없는 헤더 테스트 (단 LLM 생성 Mock JWT 허용)

- [x] Task 2: `POST /api/v1/devices/register` 엔드포인트 (AC: #3)
  - [x] 2.1 `api/routers/devices.py` 생성
  - [x] 2.2 요청 스키마: `{ fcm_token: str, platform: "web" | "ios" | "android" }` Pydantic 모델
  - [x] 2.3 `user_devices` UPSERT (UNIQUE(user_id, fcm_token) — 중복 토큰 방지, ON CONFLICT DO UPDATE SET updated_at)
  - [x] 2.4 응답: `{"data": {"device_id": "<uuid>"}, "error": null}` (APIResponse 봉투)
  - [x] 2.5 `api/main.py`에 devices router 등록 (`prefix="/api/v1"`)
  - [x] 2.6 통합 테스트 작성 (실제 Supabase 테스트 DB 필요)

- [x] Task 3: Next.js 서버사이드 Supabase 클라이언트 + 미들웨어 (AC: #1, #2)
  - [x] 3.1 `web/src/lib/supabase-server.ts` 생성 — SSR/RSC용 `createServerClient` (아래 Dev Notes 참조)
  - [x] 3.2 `web/src/proxy.ts` 생성 — 세션 쿠키 갱신 + 미인증 경로 `/signin` 리디렉션 (Next.js 16: middleware.ts → proxy.ts)
  - [x] 3.3 `web/src/app/(auth)/layout.tsx` 생성 — auth 레이아웃 (인증 상태 체크, 로그인 상태면 `/home` 리디렉션)
  - [x] 3.4 `web/src/app/(auth)/signup/page.tsx` 생성 — 회원가입 폼 (아래 UX 스펙 참조)
  - [x] 3.5 `web/src/app/(auth)/signin/page.tsx` 생성 — 로그인 폼
  - [x] 3.6 `web/src/app/page.tsx` 수정 — 루트(`/`)는 인증 상태 확인 후 `/home` 또는 `/signin` 리디렉션

- [x] Task 4: Flutter Supabase.initialize() + GoRouter + Auth 화면 (AC: #1, #2, #3, #4)
  - [x] 4.1 `mobile/pubspec.yaml`에 Firebase 패키지 추가: `firebase_core: ^3.6.0`, `firebase_messaging: ^15.1.3`
  - [x] 4.2 Firebase 프로젝트 설정 (user action): `google-services.json` (Android), `GoogleService-Info.plist` (iOS) — 플레이스홀더 firebase_options.dart 생성, 실제 설정은 flutterfire configure로 교체 필요
  - [x] 4.3 `mobile/lib/main.dart` 수정 — `Supabase.initialize()` + `Firebase.initializeApp()` 추가
  - [x] 4.4 `mobile/lib/core/router/app_router.dart` 생성 — GoRouter 설정 (Auth Guard + /signin, /signup, /onboarding, /home 경로)
  - [x] 4.5 `mobile/lib/features/auth/providers/auth_provider.dart` 생성 — `@riverpod` 세션 상태 StreamProvider
  - [x] 4.6 `mobile/lib/features/auth/screens/signin_screen.dart` 생성
  - [x] 4.7 `mobile/lib/features/auth/screens/signup_screen.dart` 생성
  - [x] 4.8 `mobile/lib/features/auth/providers/fcm_provider.dart` 생성 — FCM 토큰 획득 및 FastAPI 등록
  - [x] 4.9 로그인 성공 후 + 앱 resume 시 FCM 토큰 등록 호출 (best-effort, 로그인/signup 화면에서 호출)
  - [x] 4.10 `mobile/lib/main.dart`에 GoRouter + auth redirect 연결 (ConsumerWidget + appRouterProvider)

## Dev Notes

### 🚨 CRITICAL: Story 1.1에서 이월된 필수 구현

다음 항목들은 Story 1.1 코드리뷰에서 "이 스토리에서 구현 예정"으로 표시된 **Deferred 항목**이다.
이번 스토리의 최우선 구현 사항:

1. **`Flutter Supabase.initialize()` 누락** (`mobile/lib/main.dart`) — Story 1.2에서 필수 추가
2. **JWT 미들웨어 없음** — Story 1.2에서 FastAPI에 추가 (현재 health 엔드포인트 제외 모든 엔드포인트 미보호)
3. **Next.js 서버사이드 Supabase 클라이언트 없음** — Story 1.2에서 `createServerClient` 추가 필요

### 현재 존재하는 파일 (절대 재생성 금지)

```
api/
├── main.py               ← UPDATE: devices router 등록 추가
├── core/
│   ├── config.py         ← UPDATE: supabase_jwt_secret 필드 추가
│   ├── schemas.py        # 그대로 사용 (APIResponse 봉투 재사용)
│   └── supabase.py       # 그대로 사용 (service_role 클라이언트)
├── routers/
│   └── health.py         # 변경 없음

web/src/
├── app/
│   ├── layout.tsx        # 변경 없음
│   ├── page.tsx          ← UPDATE: /signin 또는 /home 리디렉션으로 교체
│   └── globals.css       # 변경 없음 (디자인 토큰 이미 정의됨)
├── lib/
│   └── supabase.ts       # 변경 없음 (브라우저 클라이언트 — 그대로 사용)

mobile/
├── lib/
│   ├── main.dart         ← UPDATE: Supabase.initialize(), Firebase.initializeApp(), GoRouter
│   └── core/theme/app_theme.dart  # 변경 없음
├── pubspec.yaml          ← UPDATE: firebase_core, firebase_messaging 추가
```

### FastAPI JWT 미들웨어 구현 (`api/middleware/auth.py`)

Supabase JWT는 `HS256`으로 서명됨. `SUPABASE_JWT_SECRET`으로 로컬 검증 (네트워크 호출 불필요, 빠름).

```python
# api/middleware/auth.py
from typing import Annotated
import jwt  # PyJWT — supabase SDK 의존성으로 이미 설치됨
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import settings

security = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> str:
    """Supabase JWT 검증 → user_id(sub) 반환. 실패 시 401."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
```

**`api/core/config.py` 수정:**
```python
class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""  # 추가: Supabase Settings → API → JWT Settings
    cors_origins: list[str] = ["http://localhost:3000"]
    ...
```

**`.env.example` 업데이트:**
```
SUPABASE_JWT_SECRET=your-jwt-secret-here
```

JWT Secret 위치: Supabase 대시보드 → Settings → API → JWT Settings → `JWT Secret`

### FastAPI 디바이스 등록 엔드포인트 (`api/routers/devices.py`)

```python
# api/routers/devices.py
from typing import Annotated, Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.schemas import APIResponse
from core.supabase import get_supabase
from middleware.auth import get_current_user

router = APIRouter(prefix="/devices", tags=["devices"])


class DeviceRegisterRequest(BaseModel):
    fcm_token: str
    platform: Literal["web", "ios", "android"]


@router.post("/register", response_model=APIResponse)
def register_device(
    body: DeviceRegisterRequest,
    user_id: Annotated[str, Depends(get_current_user)],
) -> APIResponse:
    """FCM 토큰 등록 (UPSERT). user_devices 테이블에 저장."""
    client = get_supabase()
    result = (
        client.table("user_devices")
        .upsert(
            {
                "user_id": user_id,
                "fcm_token": body.fcm_token,
                "platform": body.platform,
                "updated_at": "now()",
            },
            on_conflict="user_id,fcm_token",
        )
        .execute()
    )
    device_id = result.data[0]["id"] if result.data else None
    return APIResponse(data={"device_id": device_id})
```

**`api/main.py`에 router 등록 추가:**
```python
from routers.devices import router as devices_router
app.include_router(devices_router, prefix="/api/v1")
```

### Next.js 서버사이드 Supabase 클라이언트 (`web/src/lib/supabase-server.ts`)

Story 1.1 Deferred: "RSC 데이터 패칭 도입 스토리에서 추가 예정" → Story 1.2에서 구현.

```typescript
// web/src/lib/supabase-server.ts
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export function createServerSupabaseClient() {
  const cookieStore = cookies();
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url) throw new Error("Missing NEXT_PUBLIC_SUPABASE_URL");
  if (!key) throw new Error("Missing NEXT_PUBLIC_SUPABASE_ANON_KEY");
  return createServerClient(url, key, {
    cookies: {
      getAll() { return cookieStore.getAll(); },
      setAll(cookiesToSet) {
        try {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          );
        } catch {}  // Server Components에서 쿠키 쓰기 무시
      },
    },
  });
}
```

### Next.js 미들웨어 (`web/src/middleware.ts`)

세션 쿠키 갱신 + 미인증 보호 경로 리디렉션.

```typescript
// web/src/middleware.ts
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

  const supabase = createServerClient(url, key, {
    cookies: {
      getAll() { return request.cookies.getAll(); },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        supabaseResponse = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) =>
          supabaseResponse.cookies.set(name, value, options)
        );
      },
    },
  });

  const { data: { user } } = await supabase.auth.getUser();

  const isAuthRoute = request.nextUrl.pathname.startsWith("/(auth)") ||
    request.nextUrl.pathname === "/signin" ||
    request.nextUrl.pathname === "/signup";

  if (!user && !isAuthRoute) {
    const url = request.nextUrl.clone();
    url.pathname = "/signin";
    return NextResponse.redirect(url);
  }

  return supabaseResponse;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|ico|css|js)$).*)"],
};
```

### Next.js 인증 화면 UX 스펙

**공통:**
- 배경: `var(--surface-raised)` (#F9F9F9)
- 콘텐츠 컨테이너: 중앙 정렬, max-width 480px, 수직 padding 48px
- 이메일·비밀번호 입력 필드: border `var(--border-card)` 1px, radius `var(--radius-form-field)` (12px), padding 12px 16px
- CTA 버튼 (가입/로그인): `var(--accent-primary)` (#0D0D0D) bg, `var(--accent-foreground)` (#FFFFFF) text, height 52px, radius 9999px, width 100%, `text-body-large` (17px/600)
- 에러 메시지: `var(--error)` (#EF4444) 텍스트, 13px/500
- 하단 전환 링크: "이미 계정이 있으신가요? [로그인]" / "계정이 없으신가요? [회원가입]", 13px/text-secondary

**회원가입 화면 (`/signup`):**
- 헤딩: "계정 만들기" (screen-title: 28px/700)
- 서브텍스트: "오늘의 AI 기술 브리핑을 받아보세요" (14px/text-secondary)
- 이메일 입력: type="email", autocomplete="email", placeholder="이메일", 한국어 label
- 비밀번호 입력: type="password", autocomplete="new-password", placeholder="비밀번호 (8자 이상)"
- CTA: "시작하기"
- 비밀번호 최소 8자 검증 (클라이언트사이드)

**로그인 화면 (`/signin`):**
- 헤딩: "다시 오셨군요" (screen-title: 28px/700)
- 이메일 입력: type="email", autocomplete="email"
- 비밀번호 입력: type="password", autocomplete="current-password"
- CTA: "로그인"

**라우팅 로직 (`/`):**
```typescript
// web/src/app/page.tsx
import { redirect } from "next/navigation";
import { createServerSupabaseClient } from "@/lib/supabase-server";

export default async function RootPage() {
  const supabase = createServerSupabaseClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (user) redirect("/home");
  else redirect("/signin");
}
```

**온보딩 리디렉션 로직:** 회원가입 성공 후 onboarding_completed 체크 불필요.
Supabase `handle_new_user()` 트리거가 자동으로 `user_profiles` 생성 (`onboarding_completed: false`).
신규 사용자는 무조건 `/onboarding`으로 이동.
로그인 후 `user_profiles.onboarding_completed` 체크 → false면 `/onboarding`, true면 `/home`.

### Flutter main.dart 업데이트 (Task 4.3)

```dart
// mobile/lib/main.dart
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'core/theme/app_theme.dart';
import 'core/router/app_router.dart';
import 'firebase_options.dart';  // FlutterFire CLI로 자동 생성

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
  SystemChrome.setSystemUIOverlayStyle(SystemUiOverlayStyle.dark);

  // Firebase 초기화 (FCM용 — firebase_options.dart는 FlutterFire CLI로 생성)
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  // Supabase 초기화 (Story 1.1 Deferred → 이번 스토리 구현 필수)
  await Supabase.initialize(
    url: const String.fromEnvironment('SUPABASE_URL'),
    anonKey: const String.fromEnvironment('SUPABASE_ANON_KEY'),
  );

  runApp(
    const ProviderScope(
      child: MyApp(),
    ),
  );
}

class MyApp extends ConsumerWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(appRouterProvider);
    return MaterialApp.router(
      title: 'Decision OS',
      theme: buildAppTheme(),
      routerConfig: router,
    );
  }
}
```

**⚠️ Supabase URL/anonKey 전달 방식:** `const String.fromEnvironment` 또는 `dotenv` 패키지.
개발 시 `--dart-define=SUPABASE_URL=...` 플래그 사용.
**절대 하드코딩 금지 (AD-10).**

### Flutter GoRouter 설정 (`mobile/lib/core/router/app_router.dart`)

```dart
import 'package:go_router/go_router.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../../features/auth/screens/signin_screen.dart';
import '../../features/auth/screens/signup_screen.dart';

part 'app_router.g.dart';

@riverpod
GoRouter appRouter(AppRouterRef ref) {
  return GoRouter(
    initialLocation: '/signin',
    redirect: (context, state) {
      final session = Supabase.instance.client.auth.currentSession;
      final isAuthRoute = state.matchedLocation == '/signin' ||
          state.matchedLocation == '/signup';

      if (session == null && !isAuthRoute) return '/signin';
      if (session != null && isAuthRoute) return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/signin', builder: (_, __) => const SignInScreen()),
      GoRoute(path: '/signup', builder: (_, __) => const SignUpScreen()),
      GoRoute(path: '/onboarding', builder: (_, __) => const Scaffold(body: Center(child: Text('Onboarding — Story 1.5')))),
      GoRoute(path: '/home', builder: (_, __) => const Scaffold(body: Center(child: Text('Home — Story 1.3')))),
    ],
  );
}
```

**⚠️ 주의:** GoRouter redirect는 Story 1.3/1.4 Web/Flutter Navigation Shell 구현 후
`StatefulShellRoute.indexedStack` 방식으로 업데이트 예정.
이번 스토리에서는 단순 `/home` placeholder 라우트로 연결.

**코드 생성 실행:** `flutter pub run build_runner build --delete-conflicting-outputs`

### Flutter Auth Provider (`mobile/lib/features/auth/providers/auth_provider.dart`)

```dart
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

part 'auth_provider.g.dart';

@riverpod
Stream<AuthState> authState(AuthStateRef ref) {
  return Supabase.instance.client.auth.onAuthStateChange;
}

@riverpod
User? currentUser(CurrentUserRef ref) {
  return Supabase.instance.client.auth.currentUser;
}
```

### Flutter FCM 토큰 등록 (`mobile/lib/features/auth/providers/fcm_provider.dart`)

```dart
import 'dart:io';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

part 'fcm_provider.g.dart';

@riverpod
Future<void> registerFcmToken(RegisterFcmTokenRef ref) async {
  final session = Supabase.instance.client.auth.currentSession;
  if (session == null) return;

  final token = await FirebaseMessaging.instance.getToken();
  if (token == null) return;

  final platform = Platform.isIOS ? 'ios' : 'android';
  final apiBase = const String.fromEnvironment('FASTAPI_BASE_URL', defaultValue: 'http://localhost:8000');

  await http.post(
    Uri.parse('$apiBase/api/v1/devices/register'),
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ${session.accessToken}',
    },
    body: jsonEncode({'fcm_token': token, 'platform': platform}),
  );
  // 실패 시 무시 — 다음 로그인/오픈 시 재시도
}
```

**⚠️ `http` 패키지:** `pubspec.yaml`에 `http: ^1.2.0` 추가 필요 (또는 Dio 사용 가능).
FCM 토큰 등록은 best-effort: 실패 시 로그만 남기고 앱 플로우 차단 금지.

**FCM 토큰 갱신 감지:**
```dart
// main.dart 또는 auth screen에서 추가
FirebaseMessaging.instance.onTokenRefresh.listen((newToken) {
  ref.read(registerFcmTokenProvider);  // 토큰 갱신 시 재등록
});
```

### Firebase 설정 (User Action 필요 — 개발자 실행)

1. Firebase Console에서 프로젝트 생성
2. Flutter 앱 등록 (iOS: `com.example.decisionOs`, Android: `com.example.decision_os`)
3. FlutterFire CLI 설치 및 실행:
   ```bash
   dart pub global activate flutterfire_cli
   flutterfire configure --project=<firebase-project-id>
   ```
   → `mobile/lib/firebase_options.dart` 자동 생성
4. Android: `mobile/android/app/google-services.json` 자동 추가
5. iOS: `mobile/ios/Runner/GoogleService-Info.plist` 자동 추가
6. Android `build.gradle` 플러그인 설정 (FlutterFire CLI가 자동 처리):
   ```gradle
   // android/build.gradle
   classpath 'com.google.gms:google-services:4.4.1'
   // android/app/build.gradle  
   apply plugin: 'com.google.gms.google-services'
   ```

**iOS 추가 설정 (`ios/Runner/Info.plist`):**
```xml
<key>FirebaseAppDelegateProxyEnabled</key><false/>
```

### Flutter 로그인/회원가입 화면 패턴

```dart
// mobile/lib/features/auth/screens/signin_screen.dart

class SignInScreen extends ConsumerStatefulWidget {
  const SignInScreen({super.key});
  @override ConsumerState<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends ConsumerState<SignInScreen> {
  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _isLoading = false;
  String? _error;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.surfaceRaised,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 48),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('다시 오셨군요', style: Theme.of(context).textTheme.displayLarge),
              const SizedBox(height: 32),
              // 이메일/비밀번호 TextField (AD-10: 최소 입력 수집)
              if (_error != null) Text(_error!, style: const TextStyle(color: AppColors.error, fontSize: 13)),
              ElevatedButton(
                onPressed: _isLoading ? null : _signIn,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.accentPrimary,
                  foregroundColor: AppColors.accentForeground,
                  minimumSize: const Size(double.infinity, 52),
                  shape: const StadiumBorder(),
                ),
                child: _isLoading ? const CircularProgressIndicator(color: Colors.white) : const Text('로그인'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _signIn() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      await Supabase.instance.client.auth.signInWithPassword(
        email: _emailCtrl.text.trim(),
        password: _passwordCtrl.text,
      );
      // GoRouter redirect가 자동으로 /home 또는 /onboarding으로 이동
      // 로그인 성공 후 FCM 토큰 등록
      await ref.read(registerFcmTokenProvider.future);
    } on AuthException catch (e) {
      setState(() => _error = _mapAuthError(e.message));
    } finally {
      setState(() => _isLoading = false);
    }
  }

  String _mapAuthError(String msg) {
    if (msg.contains('Invalid login credentials')) return '이메일 또는 비밀번호가 올바르지 않습니다.';
    if (msg.contains('Email not confirmed')) return '이메일 확인이 필요합니다.';
    return '로그인 중 오류가 발생했습니다. 다시 시도해 주세요.';
  }
}
```

**회원가입 후 온보딩 리디렉션 판단:**
```dart
// 회원가입 성공 후
final user = Supabase.instance.client.auth.currentUser;
// user_profiles.onboarding_completed는 handle_new_user() 트리거가 DEFAULT FALSE로 생성
// GoRouter redirect: 세션 있고 /signup → /onboarding (Story 1.5 구현 전까지 placeholder)
```

### 아키텍처 준수 사항

| 규칙 | 근거 |
|------|------|
| JWT 검증: FastAPI dependency로 구현 (미들웨어 아님) | AD-3, AD-13 |
| `user_devices` 쓰기: FastAPI service_role만 | AD-3 |
| Supabase Auth 세션: 읽기는 클라이언트 직접 (RLS + anon key) | AD-3 |
| FCM 토큰: 클라이언트 → FastAPI 경유 등록 (클라이언트→FCM 직접 불가) | AD-17 |
| Flutter 상태관리: Riverpod `@riverpod` 코드 생성 | AD-14 |
| GoRouter redirect로 Auth Guard (Supabase 세션 기반) | AD-14 |
| SUPABASE_JWT_SECRET은 FastAPI 환경변수로만 관리 | AD-10 |
| 클라이언트에 service_role key 절대 노출 금지 | AD-3, AD-10 |

### 테스트 전략 (AD-11)

**FastAPI:**
- `api/tests/test_auth_middleware.py` — Mock JWT로 단위 테스트:
  - 유효한 JWT → user_id 반환
  - 만료된 JWT → 401
  - Authorization 헤더 없음 → 401 (자동: HTTPBearer)
- `api/tests/test_devices.py` — 실제 Supabase 테스트 DB 연결:
  - 디바이스 등록 성공
  - 중복 토큰 UPSERT (같은 user_id+fcm_token → updated_at 갱신)
  - 인증 없이 접근 → 401

**Next.js:**
- 미들웨어 세션 처리 테스트 — 인증/미인증 경로 리디렉션 동작

**Flutter:**
- Unit test for error message mapping (`_mapAuthError`)
- GoRouter redirect logic test (세션 있음/없음)

**FCM 관련 테스트:** Firebase SDK Mock 사용 가능, 실제 FCM 토큰은 실기기 테스트 필요.

### 프로젝트 구조 참고 (이번 스토리 후)

```
api/
├── main.py               # devices router 추가됨
├── middleware/
│   ├── __init__.py
│   └── auth.py           # get_current_user dependency
├── core/
│   ├── config.py         # supabase_jwt_secret 추가됨
│   ├── schemas.py
│   └── supabase.py
├── routers/
│   ├── health.py
│   └── devices.py        # POST /api/v1/devices/register
├── tests/
│   ├── test_health.py
│   ├── test_auth_middleware.py
│   └── test_devices.py

web/src/
├── app/
│   ├── layout.tsx
│   ├── page.tsx           # /signin 또는 /home 리디렉션
│   ├── globals.css
│   └── (auth)/
│       ├── layout.tsx     # auth 레이아웃 (인증 상태 체크)
│       ├── signin/page.tsx
│       └── signup/page.tsx
├── lib/
│   ├── supabase.ts        # 브라우저 클라이언트 (기존)
│   └── supabase-server.ts # 서버사이드 클라이언트 (신규)
└── middleware.ts

mobile/lib/
├── main.dart              # Supabase.initialize() + Firebase.initializeApp()
├── firebase_options.dart  # FlutterFire CLI 생성
├── core/
│   ├── theme/app_theme.dart
│   └── router/
│       └── app_router.dart  # GoRouter + auth guard
└── features/
    └── auth/
        ├── providers/
        │   ├── auth_provider.dart
        │   └── fcm_provider.dart
        └── screens/
            ├── signin_screen.dart
            └── signup_screen.dart
```

### References

- DB 스키마: `_bmad-output/implementation-artifacts/db/001_initial_schema.sql` — `user_profiles`(handle_new_user 트리거), `user_devices`(UNIQUE user_id+fcm_token) 참조
- 아키텍처: ARCHITECTURE-SPINE.md — AD-3(데이터 접근), AD-10(보안), AD-13(API 계약), AD-14(Flutter), AD-17(FCM)
- Story 1.1 Dev Notes: `1-1-project-scaffolding-and-database-foundation.md` — 기존 파일 목록, 패턴, Deferred 항목
- Deferred Work: `_bmad-output/implementation-artifacts/deferred-work.md` — 이번 스토리에서 구현해야 할 항목 확인

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Next.js 16에서 `middleware.ts` → `proxy.ts` 변경 (함수명도 `middleware` → `proxy`). 스토리 Dev Notes는 `middleware.ts`로 명시되어 있었으나 Next.js 16 공식 문서에 따라 `proxy.ts`로 구현.
- `cookies()` in Next.js 16은 async: `await cookies()` 필요. `supabase-server.ts` 함수도 `async`로 변경.
- Riverpod 2.6.1에서 제네릭 `Ref` 미지원: `AppRouterRef`, `AuthStateRef` 등 특정 Ref 타입 사용.
- `supabase_flutter` 최신 버전: `anonKey` deprecated → `publishableKey` 사용.
- `HTTPBearer` FastAPI 0.139.2에서 인증 헤더 없을 시 403 아닌 401 반환 — 테스트 수정.
- `flutter_riverpod` 명시적 dependency 추가 필요 (`hooks_riverpod`만으로는 분석 경고 발생).

### Completion Notes List

- **Task 1 완료**: FastAPI JWT 미들웨어 구현. PyJWT HS256 로컬 검증, `get_current_user` Dependency. 5개 테스트 모두 통과.
- **Task 2 완료**: `POST /api/v1/devices/register` 구현. Pydantic 모델 + UPSERT + APIResponse 봉투. 5개 테스트 통과. main.py에 devices router 등록.
- **Task 3 완료**: Next.js 서버사이드 Supabase 클라이언트 구현. `proxy.ts` (Next.js 16 규칙), `(auth)/layout.tsx`, signup/signin 페이지. TypeScript 오류 0개.
- **Task 4 완료**: Flutter Firebase + Supabase 초기화, GoRouter auth guard, AuthProvider, FCM 토큰 등록. 25개 테스트 모두 통과. `firebase_options.dart` 플레이스홀더 생성 — 실제 배포 전 `flutterfire configure`로 교체 필요.
- 전체 테스트: FastAPI 13/13, Flutter 25/25 통과.

### File List

api/requirements.txt
api/core/config.py
api/middleware/__init__.py
api/middleware/auth.py
api/routers/devices.py
api/main.py
api/tests/test_auth_middleware.py
api/tests/test_devices.py
web/src/lib/supabase-server.ts
web/src/proxy.ts
web/src/app/(auth)/layout.tsx
web/src/app/(auth)/signup/page.tsx
web/src/app/(auth)/signin/page.tsx
web/src/app/page.tsx
mobile/pubspec.yaml
mobile/lib/main.dart
mobile/lib/firebase_options.dart
mobile/lib/core/router/app_router.dart
mobile/lib/core/router/app_router.g.dart
mobile/lib/features/auth/providers/auth_provider.dart
mobile/lib/features/auth/providers/auth_provider.g.dart
mobile/lib/features/auth/providers/fcm_provider.dart
mobile/lib/features/auth/providers/fcm_provider.g.dart
mobile/lib/features/auth/screens/signin_screen.dart
mobile/lib/features/auth/screens/signup_screen.dart
mobile/test/auth_test.dart
mobile/test/widget_test.dart

## Change Log

- 2026-07-23: Story 1.2 구현 완료. FastAPI JWT 미들웨어, devices 엔드포인트, Next.js auth 화면(proxy.ts), Flutter GoRouter + auth 화면 + FCM 토큰 등록 구현. FastAPI 13개 테스트, Flutter 25개 테스트 통과.

## Review Findings

> Code review 2026-07-23 — 1 decision-needed, 10 patch, 6 deferred, 11 dismissed

### Decision Needed

- [x] [Review][Decision] Flutter 로그인 후 onboarding_completed 라우팅 방식 → 옵션 B 적용: 로그인/회원가입 화면에서 직접 context.go() 호출

### Patches

- [x] [Review][Patch] [CRITICAL] proxy.ts → middleware.ts 파일명/함수명 오류 — web/src/middleware.ts 생성, 함수명 middleware로 변경, /onboarding을 isAuthRoute에 추가, getUser() try/catch 추가 [web/src/proxy.ts]
- [x] [Review][Patch] [CRITICAL] Empty JWT secret 시작 검증 없음 — model_validator로 RuntimeWarning 발생 추가 [api/core/config.py]
- [x] [Review][Patch] [HIGH] updated_at "now()" 문자열 리터럴 전송 — datetime.now(timezone.utc).isoformat()으로 수정 [api/routers/devices.py:30]
- [x] [Review][Patch] [HIGH] Flutter signup 후 GoRouter가 /home으로 이동 — signup_screen에서 context.go('/onboarding') 직접 호출 [mobile/lib/features/auth/screens/signup_screen.dart]
- [x] [Review][Patch] [HIGH] profile fetch 오류 무시 → 온보딩 완료 사용자가 항상 /onboarding으로 이동 — profileError 체크 추가, 실패 시 /onboarding으로 safe default [web/src/app/(auth)/signin/page.tsx]
- [x] [Review][Patch] [HIGH] iOS에서 FCM 권한 요청 없음 → getToken() null 반환 — requestPermission() 추가 [mobile/lib/main.dart]
- [x] [Review][Patch] [MEDIUM] isLoading 성공 경로에서 reset 안 됨 — try/finally로 setIsLoading(false) 보장 [web/src/app/(auth)/signup/page.tsx, signin/page.tsx]
- [x] [Review][Patch] [MEDIUM] AuthException만 catch — catch (e) 블록 추가로 네트워크 오류 처리 [mobile/lib/features/auth/screens/signin_screen.dart, signup_screen.dart]
- [x] [Review][Patch] [MEDIUM] onTokenRefresh 리스너가 no-op — registerFcmTokenWithToken() 헬퍼 함수 추출, onTokenRefresh에서 호출 [mobile/lib/main.dart, fcm_provider.dart]
- [x] [Review][Patch] [LOW] 웹 signup에서 이메일 trim 없음 — email.trim() 추가 [web/src/app/(auth)/signup/page.tsx]

### Deferred

- [x] [Review][Defer] FASTAPI_BASE_URL 컴파일 타임 결정 — dart-define으로 빌드 시 설정 필요; 문서화됨, CI/CD 설정 시 처리 [mobile/lib/features/auth/providers/fcm_provider.dart:20] — deferred, pre-existing
- [x] [Review][Defer] GoRouter 동기 session 읽기 → cold start 깜빡임 — Story 1.3/1.4 StatefulShellRoute 교체 예정 [mobile/lib/core/router/app_router.dart] — deferred, pre-existing
- [x] [Review][Defer] cors_origins 기본값 localhost:3000 — 배포 환경 설정 이슈; 운영 환경에서 CORS_ORIGINS env var 필수 [api/core/config.py] — deferred, pre-existing
- [x] [Review][Defer] /devices/register 속도 제한 없음 — 인증된 사용자의 남용 가능; 미래 작업 [api/routers/devices.py] — deferred, pre-existing
- [x] [Review][Defer] Flutter platform enum 'web' 없음 — 웹 FCM 지원 범위 정의 후 처리 [mobile/lib/features/auth/providers/fcm_provider.dart:19] — deferred, pre-existing
- [x] [Review][Defer] WWW-Authenticate 헤더 없음 — RFC 6750 준수 이슈, 현재 클라이언트에 영향 없음 [api/middleware/auth.py] — deferred, pre-existing

### Review Findings — Round 2 (2026-07-24)

> Code review 2026-07-24 — 2 decision-needed, 10 patch, 6 deferred, 7 dismissed

#### Decision Needed

- [x] [Review][Decision] FCM 토큰 크로스유저 등록 — 동일 기기를 다른 사용자가 재사용할 때 같은 FCM 토큰이 여러 user_id에 등록되어 타 사용자 알림이 현재 기기에 노출될 수 있음. → 옵션 2 적용: upsert 전 타 사용자의 동일 fcm_token 행 삭제 [api/routers/devices.py]
- [x] [Review][Decision] 이메일 확인 비활성화 여부 — Supabase 이메일 인증 확인이 활성화된 경우 signUp() 후 session=null에서 무한 루프 발생. → 옵션 2 적용: session null 시 이메일 확인 안내 메시지 표시 [mobile/lib/features/auth/screens/signup_screen.dart, web/src/app/(auth)/signup/page.tsx]

#### Patches

- [x] [Review][Patch] [HIGH] JWT secret 미설정 시 서버 기동 허용 — model_validator에서 RuntimeWarning 대신 ValueError 발생으로 startup fail, get_current_user도 빈 secret 시 즉시 401 반환하도록 수정 [api/core/config.py:14-22, api/middleware/auth.py:17-22]
- [x] [Review][Patch] [MEDIUM] SUPABASE_URL/SERVICE_ROLE_KEY 빈값 startup 검증 없음 — supabase_url, supabase_service_role_key에도 빈값 validator 추가 [api/core/config.py:8-10]
- [x] [Review][Patch] [MEDIUM] proxy.ts 데드 코드 삭제 — middleware.ts와 isAuthRoute 불일치(/onboarding 누락)로 향후 혼란 야기 [web/src/proxy.ts]
- [x] [Review][Patch] [MEDIUM] middleware.ts catch{}가 Supabase 장애를 미인증으로 처리 — 전체 사용자 /signin 강제 리디렉션(DoS 유사 효과), 네트워크/인증 오류 구분 또는 503 반환으로 수정 [web/src/middleware.ts:26-30]
- [x] [Review][Patch] [MEDIUM] devices.py UPSERT RLS 거부 시 200 OK + null device_id 반환 — result.data 빈값 체크 및 적절한 HTTP 오류 반환 [api/routers/devices.py:39]
- [x] [Review][Patch] [MEDIUM] JWT 클락 스큐 허용 없음 — jwt.decode()에 leeway=timedelta(seconds=10) 추가, 서버 시계 1초 차이도 즉시 401 유발 [api/middleware/auth.py:17]
- [x] [Review][Patch] [MEDIUM] Flutter SUPABASE_URL 빈값 런타임 감지 없음 — Supabase.initialize() 직후 assert 또는 early exit 추가, 빌드 시 --dart-define 누락 시 앱이 불명확하게 실패 [mobile/lib/main.dart:30-31]
- [x] [Review][Patch] [LOW] JWT secret/service_role_key 평문 str 저장 — repr/로그 노출 방지를 위해 pydantic SecretStr 사용 [api/core/config.py:9-10]
- [x] [Review][Patch] [LOW] pytest.importorskip() default arg 잘못 사용 — Depends(get_current_user) 직접 사용으로 수정 [api/tests/test_auth_middleware.py:64]
- [x] [Review][Patch] [LOW] 로그인 페이지 이메일 trim 없음 — email.trim() 추가 [web/src/app/(auth)/signin/page.tsx:22]

#### Deferred

- [x] [Review][Defer] GoRouter 동기 currentSession, authState 스트림 미연동 — Story 1.3/1.4 StatefulShellRoute 교체 예정 [mobile/lib/core/router/app_router.dart] — deferred, pre-existing
- [x] [Review][Defer] FCM onTokenRefresh 만료 토큰으로 등록 시도 — best-effort 설계, 다음 로그인 시 재시도 [mobile/lib/main.dart:35-37] — deferred, pre-existing
- [x] [Review][Defer] /devices/register 속도 제한 없음 — Round 1에서 이미 Defer됨 [api/routers/devices.py] — deferred, pre-existing
- [x] [Review][Defer] pytest-asyncio asyncio_mode 미설정 — 현재 async 테스트 없음, 추가 시 처리 [api/requirements.txt] — deferred, pre-existing
- [x] [Review][Defer] middleware.ts 온보딩 완료 여부 미검증 — 스펙상 클라이언트사이드 체크만 요구, 미들웨어 범위 벗어남 [web/src/middleware.ts] — deferred, pre-existing
- [x] [Review][Defer] 회원가입 후 이메일 확인 시 FCM 등록 누락 — Decision D2와 연계, 이메일 확인 정책 확정 후 처리 — deferred, pre-existing
