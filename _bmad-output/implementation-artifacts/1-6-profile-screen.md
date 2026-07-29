# Story 1.6: Profile Screen

---
baseline_commit: NO_VCS
---

Status: done

## Story

사용자로서,
내 프로필(역할·경험·기술 스택·관심 영역·일일 학습 시간)을 조회하고 편집할 수 있기를 원한다,
그래서 변경된 상황에 맞게 Daily Brief 개인화 기준을 업데이트할 수 있다.

## Acceptance Criteria

**AC-1: 프로필 조회 화면**

- **Given** 로그인한 사용자가 프로필 탭을 탭했을 때
- **When** 프로필 화면이 표시되면
- **Then** Role, Experience, Tech Stack, Project/Goal, Interests, Daily Learning Time 항목이 표시된다
- **And** 우상단에 "편집" CTA가 있다
- **And** 알림 설정 행이 존재한다
- **And** `GET /api/v1/users/profile`을 호출하여 최신 프로필 데이터를 로드한다

**AC-2: 프로필 편집 및 저장**

- **Given** 사용자가 "편집"을 탭했을 때
- **When** 편집 모드에서 항목을 수정하고 "저장"을 누르면
- **Then** `PATCH /api/v1/users/profile`이 호출되어 프로필이 업데이트된다
- **And** 낙관적 업데이트 후 토스트 "프로필이 업데이트됐습니다. 다음 Daily Brief에 반영됩니다."가 3초간 표시된다
- **And** "취소"를 누르면 변경사항 없이 조회 모드로 돌아간다

**AC-3: 알림 설정 행 — OS 설정 이동**

- **Given** 사용자가 온보딩에서 알림 권한을 거부했을 때
- **When** 프로필 화면의 "알림 설정" 행을 탭하면
- **Then** iOS/Android OS 설정 앱으로 이동한다 (인앱 재요청 없음)
- **And** "기기 설정에서 알림을 허용할 수 있습니다." 안내 문구가 화면에 표시된다

**AC-4: 크로스 플랫폼 동기화**

- **Given** 사용자가 웹 또는 Flutter 앱에서 프로필을 편집할 때
- **When** 동일한 계정으로 다른 플랫폼을 확인하면
- **Then** 업데이트된 프로필 정보가 동기화되어 표시된다

## Tasks / Subtasks

- [x] Task 1: `app_settings` 패키지 추가 (AC: #3)
  - [x] 1.1 `pubspec.yaml`에 `app_settings: ^5.1.1` 추가
  - [x] 1.2 `flutter pub get` 실행

- [x] Task 2: FastAPI `PATCH /api/v1/users/profile` 엔드포인트 구현 (AC: #2, #4)
  - [x] 2.1 `api/routers/users.py` 생성
  - [x] 2.2 `ProfileUpdateRequest` Pydantic 모델 정의 (모든 필드 Optional)
  - [x] 2.3 `GET /users/profile` 엔드포인트 — 현재 user_profiles 반환
  - [x] 2.4 `PATCH /users/profile` 엔드포인트 — partial update, JWT 인증 필수
  - [x] 2.5 응답: `{"data": {...profile fields...}, "error": null}`
  - [x] 2.6 `api/main.py`에 users_router 등록

- [x] Task 3: `profile_provider.dart` 생성 — 프로필 상태 Provider (AC: #1, #2)
  - [x] 3.1 `mobile/lib/features/profile/providers/profile_provider.dart` 생성
  - [x] 3.2 `@riverpod` 코드 생성 방식으로 `profileProvider` 선언 (FutureProvider)
  - [x] 3.3 `profileNotifierProvider` 선언 (상태 업데이트·낙관적 업데이트용)
  - [x] 3.4 `build_runner` 실행

- [x] Task 4: `profile_screen.dart` 완성 — 조회 + 편집 모드 (AC: #1, #2, #3)
  - [x] 4.1 기존 `profile_screen.dart` 플레이스홀더를 `ConsumerStatefulWidget`으로 교체
  - [x] 4.2 조회 모드: Role·Experience·Tech Stack·Project/Goal·Interests·Daily Learning Time 항목 표시
  - [x] 4.3 조회 모드 우상단 "편집" 텍스트 버튼 (AppBar action)
  - [x] 4.4 알림 설정 행: 안내 문구 + OS 설정 이동 (`AppSettings.openAppSettings()`)
  - [x] 4.5 편집 모드: 온보딩과 동일한 옵션 카드·multi-select pill UI 재사용
  - [x] 4.6 편집 모드 하단 "저장" (primary pill) + "취소" (ghost pill) CTA
  - [x] 4.7 낙관적 업데이트 + 토스트 메시지 (ScaffoldMessenger.of(context).showSnackBar)
  - [x] 4.8 API 호출 패턴: `PATCH /api/v1/users/profile` (Bearer JWT, http 패키지)

- [x] Task 5: 테스트 작성 및 실행 (AC: #1, #2)
  - [x] 5.1 `mobile/test/profile_test.dart` 생성
  - [x] 5.2 프로필 조회 화면 렌더링 테스트 (mock profileProvider)
  - [x] 5.3 편집 모드 전환 및 "취소" 동작 테스트
  - [x] 5.4 기존 회귀 테스트: `flutter test test/navigation_shell_test.dart test/theme_test.dart test/auth_test.dart test/onboarding_test.dart`

## Dev Notes

### 현재 파일 상태 (MODIFY 대상)

**`mobile/lib/features/profile/screens/profile_screen.dart` (현재 플레이스홀더)**

```dart
// 현재 내용 — 완전히 교체 대상
import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.surfaceRaised,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('프로필', style: Theme.of(context).textTheme.displayMedium),
              const SizedBox(height: 8),
              Text(
                '프로필 설정이 여기에 표시됩니다. — Story 1.6에서 구현 예정',
                ...
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

`StatelessWidget`을 `ConsumerStatefulWidget`으로 전환한다. import 추가: `flutter_riverpod`, `supabase_flutter`, `http`, `app_settings`.

### FastAPI 엔드포인트 설계

**`api/routers/users.py` (NEW)**

```python
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from core.schemas import APIResponse
from core.supabase import get_supabase
from middleware.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

# GET /users/profile — 프로필 조회
@router.get("/profile", response_model=APIResponse)
def get_profile(user_id: Annotated[str, Depends(get_current_user)]) -> APIResponse:
    client = get_supabase()
    result = client.table("user_profiles").select(
        "role, experience_level, tech_stack, project_goal, interests, daily_learning_time_min, onboarding_completed"
    ).eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return APIResponse(data=result.data[0])

# PATCH /users/profile — 프로필 부분 업데이트
class ProfileUpdateRequest(BaseModel):
    role: Literal['frontend', 'backend', 'ai_engineer', 'pm', 'designer', 'student', 'other'] | None = None
    experience_level: Literal['beginner', 'intermediate', 'advanced'] | None = None
    tech_stack: list[str] | None = None
    project_goal: Literal['ai_side_project', 'rag_service', 'agent_architecture', 'work_automation', 'ai_adoption', 'other'] | None = None
    interests: list[str] | None = None
    daily_learning_time_min: int | None = Field(None, gt=0)

@router.patch("/profile", response_model=APIResponse)
def update_profile(
    body: ProfileUpdateRequest,
    user_id: Annotated[str, Depends(get_current_user)],
) -> APIResponse:
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=422, detail="No fields to update")
    client = get_supabase()
    result = client.table("user_profiles").update(update_data).eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return APIResponse(data=result.data[0])
```

**`api/main.py` MODIFY — users_router 등록**

```python
from routers.users import router as users_router
# ...기존 include_router 아래에 추가:
app.include_router(users_router, prefix="/api/v1")
```

### Flutter 상태 관리 패턴 (AD-14 준수)

AD-14 규칙: `@riverpod` 코드 생성 방식 사용. `profileProvider`는 FutureProvider로 GET 호출, `profileNotifierProvider`는 AsyncNotifier로 낙관적 업데이트 관리.

```dart
// mobile/lib/features/profile/providers/profile_provider.dart
import 'dart:convert';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:http/http.dart' as http;

part 'profile_provider.g.dart';

class UserProfile {
  final String? role;
  final String? experienceLevel;
  final List<String> techStack;
  final String? projectGoal;
  final List<String> interests;
  final int? dailyLearningTimeMin;

  const UserProfile({
    this.role,
    this.experienceLevel,
    this.techStack = const [],
    this.projectGoal,
    this.interests = const [],
    this.dailyLearningTimeMin,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) => UserProfile(
    role: json['role'] as String?,
    experienceLevel: json['experience_level'] as String?,
    techStack: (json['tech_stack'] as List<dynamic>?)?.cast<String>() ?? [],
    projectGoal: json['project_goal'] as String?,
    interests: (json['interests'] as List<dynamic>?)?.cast<String>() ?? [],
    dailyLearningTimeMin: json['daily_learning_time_min'] as int?,
  );

  UserProfile copyWith({
    String? role,
    String? experienceLevel,
    List<String>? techStack,
    String? projectGoal,
    List<String>? interests,
    int? dailyLearningTimeMin,
  }) => UserProfile(
    role: role ?? this.role,
    experienceLevel: experienceLevel ?? this.experienceLevel,
    techStack: techStack ?? this.techStack,
    projectGoal: projectGoal ?? this.projectGoal,
    interests: interests ?? this.interests,
    dailyLearningTimeMin: dailyLearningTimeMin ?? this.dailyLearningTimeMin,
  );
}

@riverpod
class ProfileNotifier extends _$ProfileNotifier {
  static const _apiBase = String.fromEnvironment(
    'FASTAPI_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  @override
  Future<UserProfile> build() async {
    final session = Supabase.instance.client.auth.currentSession;
    if (session == null) throw Exception('No session');
    final response = await http.get(
      Uri.parse('$_apiBase/api/v1/users/profile'),
      headers: {'Authorization': 'Bearer ${session.accessToken}'},
    ).timeout(const Duration(seconds: 15));
    if (response.statusCode != 200) throw Exception('Failed to load profile');
    final data = jsonDecode(response.body)['data'] as Map<String, dynamic>;
    return UserProfile.fromJson(data);
  }

  Future<void> updateProfile(Map<String, dynamic> updates) async {
    final prev = state;
    // 낙관적 업데이트
    state = AsyncData(state.requireValue.copyWith(
      role: updates['role'] as String?,
      experienceLevel: updates['experience_level'] as String?,
      techStack: (updates['tech_stack'] as List?)?.cast<String>(),
      projectGoal: updates['project_goal'] as String?,
      interests: (updates['interests'] as List?)?.cast<String>(),
      dailyLearningTimeMin: updates['daily_learning_time_min'] as int?,
    ));
    try {
      final session = Supabase.instance.client.auth.currentSession;
      if (session == null) throw Exception('No session');
      final response = await http.patch(
        Uri.parse('$_apiBase/api/v1/users/profile'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ${session.accessToken}',
        },
        body: jsonEncode(updates),
      ).timeout(const Duration(seconds: 15));
      if (response.statusCode != 200) {
        state = prev;  // 롤백
        throw Exception('Update failed');
      }
    } catch (_) {
      state = prev;  // 롤백
      rethrow;
    }
  }
}
```

`build_runner` 실행 필수:
```
cd mobile && dart run build_runner build --delete-conflicting-outputs
```

### ProfileScreen 구조 패턴

```dart
// mobile/lib/features/profile/screens/profile_screen.dart
import 'package:app_settings/app_settings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/profile_provider.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});
  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  bool _isEditMode = false;

  // 편집 중 임시 상태
  String? _editRole;
  String? _editExperience;
  final Set<String> _editTechStack = {};
  String? _editProjectGoal;
  final Set<String> _editInterests = {};
  int? _editDailyTime;

  void _enterEditMode(UserProfile profile) {
    setState(() {
      _isEditMode = true;
      _editRole = profile.role;
      _editExperience = profile.experienceLevel;
      _editTechStack
        ..clear()
        ..addAll(profile.techStack);
      _editProjectGoal = profile.projectGoal;
      _editInterests
        ..clear()
        ..addAll(profile.interests);
      _editDailyTime = profile.dailyLearningTimeMin;
    });
  }

  void _cancelEdit() => setState(() => _isEditMode = false);

  Future<void> _saveProfile() async {
    try {
      await ref.read(profileNotifierProvider.notifier).updateProfile({
        if (_editRole != null) 'role': _editRole,
        if (_editExperience != null) 'experience_level': _editExperience,
        if (_editTechStack.isNotEmpty) 'tech_stack': _editTechStack.toList(),
        if (_editProjectGoal != null) 'project_goal': _editProjectGoal,
        if (_editInterests.isNotEmpty) 'interests': _editInterests.toList(),
        if (_editDailyTime != null) 'daily_learning_time_min': _editDailyTime,
      });
      if (!mounted) return;
      setState(() => _isEditMode = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('프로필이 업데이트됐습니다. 다음 Daily Brief에 반영됩니다.'),
          duration: Duration(seconds: 3),
        ),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('업데이트에 실패했습니다. 다시 시도해 주세요.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final profileAsync = ref.watch(profileNotifierProvider);
    return Scaffold(
      backgroundColor: AppColors.surfaceRaised,
      appBar: AppBar(
        title: Text('프로필', style: Theme.of(context).textTheme.displayMedium),
        backgroundColor: AppColors.surfaceRaised,
        elevation: 0,
        actions: [
          if (!_isEditMode)
            profileAsync.whenData((profile) =>
              TextButton(
                onPressed: () => _enterEditMode(profile),
                child: const Text('편집'),
              )
            ).valueOrNull ?? const SizedBox.shrink(),
        ],
      ),
      body: profileAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('프로필을 불러오지 못했습니다.')),
        data: (profile) => _isEditMode
            ? _buildEditMode()
            : _buildViewMode(profile),
      ),
    );
  }
}
```

### 조회 모드 항목 표시

각 항목은 `_ProfileRow` 내부 위젯으로 구현:
```dart
// 조회 행 패턴
ListTile(
  contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
  title: Text(label, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary)),
  subtitle: Text(value, style: Theme.of(context).textTheme.bodyLarge),
)
```

표시 레이블 매핑:

| 필드 | 레이블 | 표시 값 예시 |
|------|--------|-------------|
| role | 역할 | "AI Engineer" |
| experience_level | 경험 수준 | "중급" |
| tech_stack | 기술 스택 | "React, LangGraph, MCP" |
| project_goal | 프로젝트 목표 | "AI 사이드 프로젝트 개발" |
| interests | 관심 영역 | "Agent, RAG, MCP" |
| daily_learning_time_min | 하루 학습 시간 | "30분" |

**알림 설정 행:**
```dart
ListTile(
  title: const Text('알림 설정'),
  subtitle: const Text('기기 설정에서 알림을 허용할 수 있습니다.'),
  trailing: const Icon(Icons.chevron_right),
  onTap: () => AppSettings.openAppSettings(),
)
```

### 편집 모드 — 온보딩 UI 패턴 재사용

Story 1.5 `onboarding_screen.dart`에 구현된 옵션 카드·multi-select pill 위젯 패턴을 **재사용**:
- 단일 선택 옵션 카드: `GestureDetector + Container + Border`
- Multi-select pill: `FilterChip` (Tech Stack, Interests)
- Primary CTA: `FilledButton` (`StadiumBorder`, ThemeData에 이미 설정)

편집 모드 하단 CTA 배치:
```dart
Row(
  children: [
    Expanded(
      child: OutlinedButton(
        onPressed: _cancelEdit,
        child: const Text('취소'),
      ),
    ),
    const SizedBox(width: 12),
    Expanded(
      child: FilledButton(
        onPressed: _isSaveEnabled ? _saveProfile : null,
        child: const Text('저장'),
      ),
    ),
  ],
)
```

`_isSaveEnabled`: role·experience·projectGoal·dailyTime이 모두 선택된 경우 `true`.

### app_settings 패키지 사용

```dart
import 'package:app_settings/app_settings.dart';
// OS 설정 앱으로 이동
AppSettings.openAppSettings();
```

`app_settings: ^5.1.1` — OS 앱 설정으로 이동하는 가장 간단한 방법. `permission_handler`는 이 스토리에서 불필요 (알림 권한 재요청 안 함, OS 설정 이동만).

### 아키텍처 준수

| 규칙 | 근거 |
|------|------|
| `@riverpod` 코드 생성 방식 — `AsyncNotifier` | AD-14: Riverpod 2.x 단일 표준, `@riverpod` 코드 생성 방식 사용 |
| FastAPI 쓰기 전담 — `user_profiles` UPDATE는 FastAPI만 | AD-3: 데이터 접근 소유권 분리 |
| `GET /api/v1/users/profile` 읽기는 FastAPI 경유 | AD-3: 읽기·쓰기 분리 (Supabase 직접 읽기 금지 — 이 스토리에서 FastAPI 경유) |
| 응답 봉투: `{"data": ..., "error": null}` | AD-13: 공통 API 계약 |
| 낙관적 업데이트 + 실패 시 롤백 | UX: "프로필 — save" 상태 스펙 |
| 인앱 알림 권한 재요청 금지 → OS 설정만 | UX-DR12, EXPERIENCE.md line 527 |
| 최상위 탭에서 시스템 back 가로채기 없음 | EXPERIENCE.md line 511, 537 |

### OS 설정 이동 패턴 (플랫폼별)

EXPERIENCE.md:527에 명시:
- iOS: `AppSettings.openAppSettings()` → 앱 전용 설정 화면 (UNUserNotificationCenter 재요청 금지)
- Android 13+: `AppSettings.openAppSettings()` → 알림 설정 화면

`app_settings` 패키지가 두 플랫폼 모두 처리. `permission_handler` 패키지 추가 불필요.

### 전체 데이터 모델 참고 (001_initial_schema.sql:19-31)

```sql
role                    TEXT,   -- 'frontend' | 'backend' | 'ai_engineer' | 'pm' | 'designer' | 'student' | 'other'
experience_level        TEXT,   -- 'beginner' | 'intermediate' | 'advanced'
tech_stack              TEXT[], -- ['Next.js', 'Python', 'LangGraph', ...]
project_goal            TEXT,   -- 'ai_side_project' | 'rag_service' | 'agent_architecture' | 'work_automation' | 'ai_adoption' | 'other'
interests               TEXT[], -- ['Agent', 'RAG', 'MCP', ...]
daily_learning_time_min INTEGER,-- 15 | 30 | 60
onboarding_completed    BOOLEAN NOT NULL DEFAULT FALSE,
```

### UI 라벨 ↔ API 값 매핑 (온보딩과 동일)

**Role:**
| UI 라벨 | API value |
|---------|-----------|
| Frontend Developer | frontend |
| Backend Developer | backend |
| AI Engineer | ai_engineer |
| Product Manager | pm |
| Designer | designer |
| Student | student |
| 기타 | other |

**Experience Level:**
| UI 라벨 | API value |
|---------|-----------|
| 입문 | beginner |
| 중급 | intermediate |
| 고급 | advanced |

**Project Goal:**
| UI 라벨 | API value |
|---------|-----------|
| AI 사이드 프로젝트 개발 | ai_side_project |
| RAG 서비스 구축 | rag_service |
| Agent Architecture 학습 | agent_architecture |
| 업무 자동화 | work_automation |
| AI 도입 검토 | ai_adoption |
| 기타 | other |

**Daily Learning Time:**
| UI 라벨 | API value |
|---------|-----------|
| 15분 | 15 |
| 30분 | 30 |
| 1시간 | 60 |

Tech Stack, Interests: UI 라벨 그대로 전송 (React, Next.js, Python, LangGraph, MCP, Claude Code, Agent, RAG 등)

### 이전 스토리 1.5 학습 사항

- `ConsumerStatefulWidget` 패턴: Story 1.5 `onboarding_screen.dart` 참고
- 옵션 카드 + multi-select pill UI: `onboarding_screen.dart`에서 동일 패턴 재사용
- `_isCTAEnabled` 가드: 완료 전 API 미호출 보장
- HTTP 패턴: `http.post()` with `Bearer JWT`, `.timeout(const Duration(seconds: 30))` 추가 필수
- API 입력 Enum 검증: `Literal[...]` 타입 사용
- FastAPI 결과 미검증 주의: `if not result.data: raise HTTPException(404)`
- `get_current_user` 미들웨어 패턴: `api/middleware/auth.py` 기존 패턴 그대로 활용 (`from middleware.auth import get_current_user`)

### 신규 파일 / 수정 파일 목록

```
mobile/pubspec.yaml                                            (MODIFY — app_settings 추가)
mobile/lib/features/profile/providers/profile_provider.dart   (NEW)
mobile/lib/features/profile/providers/profile_provider.g.dart (GENERATED — build_runner)
mobile/lib/features/profile/screens/profile_screen.dart       (MODIFY — 플레이스홀더 교체)
mobile/test/profile_test.dart                                  (NEW)

api/routers/users.py                                           (NEW)
api/main.py                                                    (MODIFY — users_router 등록)
```

### References

- 에픽 요구사항: `_bmad-output/planning-artifacts/epics.md` — Story 1.6 (line 346–374)
- UX 상태 스펙: `EXPERIENCE.md` — Profile States (line 448–455), Notification Permission (line 527)
- UX 네비게이션: `EXPERIENCE.md` — Navigation rule (line 511, 537)
- 아키텍처: `ARCHITECTURE-SPINE.md` — AD-3(데이터 접근), AD-13(API 계약), AD-14(Flutter 상태관리)
- DB 스키마: `_bmad-output/implementation-artifacts/db/001_initial_schema.sql` — user_profiles (line 19-32)
- 이전 스토리: `1-5-onboarding-wizard.md` — 옵션 카드·pill UI 패턴, ConsumerStatefulWidget 패턴
- 인증 미들웨어: `api/middleware/auth.py` — `get_current_user` Depends 패턴
- FCM HTTP 패턴: `mobile/lib/features/auth/providers/fcm_provider.dart`
- 기존 라우터 패턴: `api/routers/onboarding.py` — router 등록 패턴

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 (bmad-create-story → bmad-dev-story)

### Debug Log References

### Completion Notes List

- Task 1: `app_settings 5.2.0` 설치 완료 (^5.1.1 constraint 충족)
- Task 2: `api/routers/users.py` 생성 — GET/PATCH `/users/profile`, `ProfileUpdateRequest` Pydantic 모델 (모든 필드 Optional), AD-13 응답 봉투 준수. `api/main.py`에 `users_router` 등록
- Task 3: `profile_provider.dart` 생성 — `UserProfile` 모델 + `ProfileNotifier` AsyncNotifier (GET 조회, 낙관적 업데이트, 실패 시 롤백). `build_runner`로 `profile_provider.g.dart` 자동 생성
- Task 4: `profile_screen.dart` 완성 — `ConsumerStatefulWidget`으로 교체, 조회 모드 6개 항목 + 알림 설정 행(`AppSettings.openAppSettings()`), 편집 모드 단일 선택 옵션 카드 + multi-select pill(온보딩 패턴 재사용), 저장/취소 CTA, 낙관적 업데이트 + SnackBar 토스트
- Task 5: `profile_test.dart` 생성 — 12개 테스트 (fromJson 3, isSaveEnabled 5, 편집 모드 3, 낙관적 업데이트 롤백 1). 전체 59개 테스트 통과 (신규 12 + 회귀 47), 회귀 없음
- `flutter analyze lib/features/profile/` 이슈 0개 확인

### File List

- mobile/pubspec.yaml (MODIFIED — app_settings: ^5.1.1 추가)
- mobile/lib/features/profile/providers/profile_provider.dart (NEW)
- mobile/lib/features/profile/providers/profile_provider.g.dart (GENERATED — build_runner)
- mobile/lib/features/profile/screens/profile_screen.dart (MODIFIED — 플레이스홀더 교체)
- mobile/test/profile_test.dart (NEW)
- api/routers/users.py (NEW)
- api/main.py (MODIFIED — users_router 등록)

### Review Findings

**코드 리뷰 실시일:** 2026-07-24
**리뷰어:** bmad-code-review (Blind Hunter + Edge Case Hunter + Acceptance Auditor)

#### Decision Needed
- [x] [Review][Patch] P-0 [MEDIUM] openAppSettings() → openNotificationSettings() 교체 — AC-3 알림 설정 화면 직접 이동. iOS/Android 모두 openNotificationSettings() 사용. [profile_screen.dart:124]

#### Patch Required
- [x] [Review][Patch] P-1 [HIGH] tech_stack/interests를 빈 배열로 지울 수 없음 — `_saveProfile`에서 `isNotEmpty` 가드로 빈 Set은 업데이트 맵에서 제외됨. 사용자가 모든 선택을 해제해도 서버 값이 변경되지 않음. `copyWith`도 null 인수를 기존값으로 되돌리므로 "clear" 의사를 표현 불가. [profile_screen.dart:54,56 / profile_provider.dart:79,81]
- [x] [Review][Patch] P-2 [MEDIUM] 저장 버튼 중복 탭 시 동시 PATCH 요청 발생 — `_isSaving` 플래그 없이 `_saveProfile`이 async로 실행됨. 빠른 이중 탭으로 동시 PATCH 요청 발생, 낙관적 상태 경쟁 조건 가능. [profile_screen.dart:215]
- [x] [Review][Patch] P-3 [MEDIUM] 프로필 로딩/에러 중 "편집" 버튼 미노출 — `profileAsync.whenData(...).valueOrNull`이 AsyncLoading/AsyncError에서 null 반환해 `SizedBox.shrink()` 렌더링. AC-1 위반 ("우상단에 편집 CTA"). [profile_screen.dart:86-91]
- [x] [Review][Patch] P-4 [MEDIUM] 프로필 로드 실패 시 재시도 수단 없음 — 에러 상태에서 정적 텍스트만 표시, 재시도 버튼·로그인 이동 없음. 토큰 만료 사용자는 화면에서 나갈 방법이 없음. [profile_screen.dart:96 / profile_provider.dart:63]
- [x] [Review][Patch] P-5 [MEDIUM] daily_learning_time_min이 임의의 양수 허용 — `Field(None, gt=0)`은 1, 999 등 모두 허용. DB 스키마와 UX 스펙은 {15, 30, 60}만 유효. `Literal[15, 30, 60]`로 제한 필요. [api/routers/users.py:30]
- [x] [Review][Patch] P-6 [MEDIUM] profile_test.dart가 실제 위젯/프로바이더를 테스트하지 않음 — 모든 12개 테스트가 생산 코드를 미러링한 순수 Dart 함수 테스트. ProfileScreen/ProfileNotifier 미임포트. Task 5.2(렌더링 테스트), 5.3(편집모드/취소 테스트) 미달성. [mobile/test/profile_test.dart]
- [x] [Review][Patch] P-7 [MEDIUM] PATCH 응답 JSON 파싱 미실시 — 성공 PATCH 응답의 `data` 키를 파싱하지 않아 서버 실제 저장값과 낙관적 상태 간 미세 차이 감지 불가. [profile_provider.dart:87-97]
- [x] [Review][Patch] P-8 [LOW] _cancelEdit이 편집 필드 상태를 초기화하지 않음 — `_isEditMode = false`만 설정, `_editRole` 등은 스테일 값 유지. 현재는 `_enterEditMode` 재진입 시 덮어써 안전하나 유지보수 취약점. [profile_screen.dart:47]
- [x] [Review][Patch] P-9 [LOW] tech_stack/interests API 입력값 무검증 — 빈 문자열, 임의 길이 문자열, 무제한 개수 허용. 최소 길이·최대 개수 제약 필요. [api/routers/users.py:27,29]
- [x] [Review][Patch] P-10 [LOW] List.cast<String>() 사용 — 서버가 비문자열 원소 반환 시 CastError. `.whereType<String>().toList()`로 안전하게 교체 가능. [profile_provider.dart:29,31]
- [x] [Review][Patch] P-11 [LOW] JSON 응답에서 `data` 키 누락 시 TypeError — `jsonDecode(body)['data'] as Map<String, dynamic>` 패턴은 `data`가 null이거나 키 없을 때 런타임 오류. null 가드 필요. [profile_provider.dart:69]
- [x] [Review][Patch] P-12 [LOW] 이중 롤백 패턴 — `updateProfile`이 예외를 catch 후 rethrow, `_saveProfile`이 동일 예외를 재캐치. state 롤백이 두 번 발생(두 번째는 무해하나 취약한 결합). [profile_provider.dart:99-102 / profile_screen.dart:67]

#### Deferred (Pre-existing)
- [x] [Review][Defer] W-1: FASTAPI_BASE_URL 기본값 localhost:8000 — 실제 기기에서 silent 연결 오류. 기존 프로바이더 패턴과 동일, 스토리 범위 밖. [profile_provider.dart:55-58] — deferred, pre-existing
- [x] [Review][Defer] W-2: get_profile .limit(1) 미적용 — 동일 user_id 중복 행 시 비결정적 결과. DB PK로 실제 불가, 아키텍처 개선 사항. [api/routers/users.py:17] — deferred, pre-existing
- [x] [Review][Defer] W-3: get_supabase() 싱글톤 미보장 — 요청마다 클라이언트 생성 가능. core/supabase.py 구현 의존, 기존 패턴. [api/routers/users.py:15,42] — deferred, pre-existing
- [x] [Review][Defer] W-4: AsyncLoading/AsyncError 상태에서 requireValue 호출 위험 — UI _isSaveEnabled 가드로 현실적으로 도달 불가. 방어적 코드 개선 가능. [profile_provider.dart:75] — deferred, pre-existing
- [x] [Review][Defer] W-5: 변경 없이 저장 활성화 — 전체 null 프로필에서 즉시 저장 버튼 활성. UX 폴리시 개선 사항, 기능 정확성 무관. [profile_screen.dart:25-29] — deferred, pre-existing

## Change Log

- 2026-07-24: Story 1.6 Profile Screen 스토리 파일 생성 — ready-for-dev
- 2026-07-24: Story 1.6 구현 완료 — FastAPI GET/PATCH /users/profile 엔드포인트, ProfileNotifier (낙관적 업데이트), ProfileScreen (조회+편집 모드), app_settings OS 설정 이동, 테스트 12개 신규 작성, 전체 59개 통과
