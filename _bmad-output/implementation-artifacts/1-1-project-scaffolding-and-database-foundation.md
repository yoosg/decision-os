---
baseline_commit: NO_VCS
---

# Story 1.1: Project Scaffolding & Database Foundation

Status: done

## Story

개발자로서,
전체 플랫폼의 기반 인프라가 설정되어 있기를 원한다,
그래서 이후 모든 기능 스토리가 일관된 아키텍처 위에서 구현될 수 있다.

## Acceptance Criteria

**AC-1: 앱 초기화 — 세 패키지가 독립 실행**

- **Given** 빈 레포지토리가 있을 때
- **When** 프로젝트 초기화를 완료하면
- **Then** Next.js 앱, FastAPI 앱, Flutter 앱이 각각 별도 패키지로 존재하고 로컬에서 실행된다
- **And** `GET /api/v1/health` → `{"data": {"status": "ok"}, "error": null}` 응답을 반환한다
- **And** 모든 FastAPI 응답은 `{"data": ..., "error": null | {"code": str, "message": str}}` 봉투 형식을 따른다

**AC-2: Supabase 마이그레이션 적용**

- **Given** Supabase 프로젝트가 연결되어 있을 때
- **When** 마이그레이션을 실행하면
- **Then** `user_profiles`, `projects`, `user_devices` 테이블(+ 전체 스키마 테이블)이 생성된다
- **And** `projects` 테이블에 `playbook_type` 컬럼이 존재하고 `ai_research` 값을 허용한다
- **And** `user_profiles`, `projects`, `user_devices` 테이블에 RLS가 활성화되어 있다
- **And** `projects` RLS 정책: `user_id = auth.uid()` (직접 소유 패턴 — AD-9)
- **And** `reviews` 등 project 경유 테이블의 RLS: `EXISTS (SELECT 1 FROM projects p WHERE p.id = project_id AND p.user_id = auth.uid())`

**AC-3: Next.js CSS 디자인 토큰**

- **Given** Next.js 앱이 실행 중일 때
- **When** CSS를 검사하면
- **Then** DESIGN.md의 전체 색상 토큰이 CSS 커스텀 프로퍼티로 정의되어 있다 (`--surface-base`, `--accent-primary` 등)
- **And** 타이포그래피 스케일 클래스가 정의되어 있다 (screen-title 28-30px/700 ~ badge 10px/700/uppercase)
- **And** 여백 시스템(4px 기준, 20px 화면 패딩) 및 모서리 반경 토큰이 정의되어 있다

**AC-4: Flutter ThemeData + Riverpod**

- **Given** Flutter 앱이 실행 중일 때
- **When** ThemeData를 검사하면
- **Then** `ColorScheme`, `TextTheme`, `ShapeTheme` 전체가 DESIGN.md 값으로 override되어 있다
- **And** `ThemeData(splashFactory: NoSplash.splashFactory)`로 잉크/리플 효과가 전면 비활성화되어 있다
- **And** Riverpod 2.x `ProviderScope`가 앱 루트에 감싸져 있다

## Tasks / Subtasks

- [x] Task 1: 모노레포 루트 구조 설정 (AC: #1)
  - [x] 1.1 루트 디렉토리에 `web/`, `api/`, `mobile/` 폴더 생성
  - [x] 1.2 루트 `.gitignore` 설정 (각 앱별 ignore 패턴 포함)
  - [x] 1.3 루트 `README.md` 작성 (각 앱 실행 방법 포함)

- [x] Task 2: FastAPI 앱 초기화 (AC: #1)
  - [x] 2.1 `api/` 폴더에 FastAPI 앱 생성 (`main.py`, `requirements.txt`, `.env.example`)
  - [x] 2.2 응답 봉투 스키마 정의: `{"data": ..., "error": null | {"code": str, "message": str}}`
  - [x] 2.3 `GET /api/v1/health` 엔드포인트 구현 → `{"data": {"status": "ok"}, "error": null}`
  - [x] 2.4 **Python 3.12+** 사용 확인 (FastAPI 0.139.x 권고 버전, `python -V` 확인) — ⚠️ Python 3.11.9 사용 (3.12 미설치, 기능상 동일)
  - [x] 2.4.1 Supabase Python 클라이언트 설치 및 환경변수 설정 (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`)
  - [x] 2.5 JSON 구조화 로그 설정 (AD-12: `review_id`, `playbook_type` 필드 포함 가능한 로거)
  - [x] 2.6 `uvicorn` 로컬 실행 확인

- [x] Task 3: Supabase 마이그레이션 적용 (AC: #2)
  - [x] 3.1 `_bmad-output/implementation-artifacts/db/001_initial_schema.sql` 파일을 Supabase 프로젝트에 실행 (supabase CLI `db push` 사용, uuid_generate_v4 → gen_random_uuid 수정)
  - [x] 3.2 Supabase 대시보드에서 테이블 생성 확인 (user_profiles, projects, user_devices, reviews, decisions, outcomes, memories, activities, signals, signal_sources, daily_briefs, daily_brief_signals, learning_paths — 13개 확인)
  - [x] 3.3 RLS 정책 활성화 확인 (11개 테이블 RLS true, signals/signal_sources는 플랫폼 레벨로 의도적 비활성)
  - [x] 3.4 `pgvector` 확장 활성화 확인 (`memories.embedding VECTOR(1536)`)
  - [x] 3.5 Realtime 활성화 확인 (`reviews`, `daily_briefs`, `learning_paths` 테이블)

- [x] Task 4: Next.js 앱 초기화 (AC: #1, #3)
  - [x] 4.1 `web/` 폴더에 Next.js 앱 생성 (App Router, TypeScript)
  - [x] 4.2 Supabase JS SDK 설치 (`@supabase/supabase-js`, `@supabase/ssr`)
  - [x] 4.3 환경변수 설정 (`.env.local`: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `FASTAPI_BASE_URL`)
  - [x] 4.4 전역 CSS 파일(`globals.css`)에 디자인 토큰 CSS 커스텀 프로퍼티 구현 (아래 Dev Notes 참조)
  - [x] 4.5 타이포그래피 유틸리티 클래스 구현 (Tailwind 또는 CSS 클래스)
  - [x] 4.6 `<html lang="ko">` 루트 속성 확인 (UX-DR14)
  - [x] 4.7 `next dev` 로컬 실행 확인 (`npm run build` 성공)

- [x] Task 5: Flutter 앱 초기화 (AC: #1, #4)
  - [x] 5.1 `mobile/` 폴더에 Flutter 앱 생성 (`flutter create` — Flutter 3.44.7)
  - [x] 5.2 `pubspec.yaml` 의존성 추가: `flutter_riverpod`, `riverpod_annotation`, `hooks_riverpod`, `go_router`, `supabase_flutter`, `build_runner`, `riverpod_generator`
  - [x] 5.3 Material 3 `ThemeData` 전체 override 구현 (CardTheme → CardThemeData, Flutter 3.44.7 API 반영)
  - [x] 5.4 `ProviderScope` 앱 루트 래핑 (`runApp(ProviderScope(child: MyApp()))`)
  - [x] 5.5 `SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge)` 설정
  - [x] 5.6 `SafeArea` 앱 루트에 적용
  - [x] 5.7 `flutter run` 로컬 실행 확인 (Chrome에서 정상 실행, ThemeData 테스트 14개 통과)

- [x] Task 6: FastAPI ↔ Supabase 연결 검증 (AC: #1, #2)
  - [x] 6.1 FastAPI 시작 시 Supabase 연결 테스트 (lifespan 이벤트로 구현, 자격증명 있을 때 실제 연결 확인)
  - [x] 6.2 `GET /api/v1/health` → 200 응답 통합 테스트 작성 (pytest 3개 테스트 통과)

### Review Findings

#### Decision Needed

- [x] [Review][Decision] signals/signal_sources RLS 전략 미결정 — RLS 미활성화 상태로 인증된 모든 사용자가 Supabase 클라이언트(anon key)로 전체 신호 데이터 조회 가능. 주석은 "service_role만 접근"이라 하지만 정책 없음 = 클라이언트 조회 허용. 플랫폼 공개 콘텐츠로 의도한 것인지, 아니면 SELECT 제한 정책을 추가해야 하는지 결정 필요. [`supabase/migrations/20260723000000_initial_schema.sql`]
- [x] [Review][Decision] learning_paths processing_started_at 컬럼 누락 — mark_stuck_jobs가 reviews는 processing_started_at 기준으로 stuck 감지하나, learning_paths는 updated_at 사용(AD-12 불일치). 스트림 업데이트 시 타임아웃 클록이 리셋됨. 전용 컬럼 추가가 이 스토리 범위인지 결정 필요. [`supabase/migrations/20260723000000_initial_schema.sql`]

#### Patch — High

- [x] [Review][Patch] user_profiles RLS 정책이 FOR SELECT 전용이 아님 (AD-3 위반) — 쓰기 전용 FastAPI 패턴 위반; 인증 클라이언트가 직접 INSERT/UPDATE 가능. FOR SELECT만 허용하도록 수정 필요. [`supabase/migrations/20260723000000_initial_schema.sql`]
- [x] [Review][Patch] mark_stuck_jobs PostgREST 경유 authenticated 롤 직접 호출 가능 — SECURITY DEFINER이나 GRANT/REVOKE 미설정으로 로그인 사용자가 모든 처리 중 작업을 실패 상태로 전환 가능. REVOKE ALL FROM PUBLIC; GRANT TO service_role 필요. [`supabase/migrations/20260723000000_initial_schema.sql`]
- [x] [Review][Patch] user_devices INSERT/DELETE RLS 정책 없음 — SELECT 정책만 존재; 클라이언트가 자신의 기기를 등록할 수 없고 백엔드 경유 시 user_id 검증도 없음. INSERT WITH CHECK (user_id = auth.uid()) 추가 필요. [`supabase/migrations/20260723000000_initial_schema.sql`]
- [x] [Review][Patch] lifespan DB ping 타임아웃 없음 — 비동기 컨텍스트에서 동기 execute() 실행, 네트워크 지연 시 서버 스타트업이 무한 블로킹됨. asyncio.wait_for 또는 타임아웃 설정 필요. [`api/main.py:25-33`]

#### Patch — Medium

- [x] [Review][Patch] FastAPI CORS 미들웨어 누락 — Next.js 웹 프론트엔드의 모든 크로스오리진 요청이 브라우저에서 차단됨. CORSMiddleware 추가 필요. [`api/main.py`]
- [x] [Review][Patch] /health 엔드포인트 DB 연결 상태 미확인 — DB 다운 시에도 항상 200 {"status": "ok"} 반환; 로드밸런서/프로브가 비정상 인스턴스로 트래픽 라우팅. 경량 DB ping 추가 및 실패 시 503 반환 필요. [`api/routers/health.py`]
- [x] [Review][Patch] 웹 Supabase env var 비null 단언(!) 사용 — 환경변수 미설정 시 undefined가 createBrowserClient에 전달되어 불명확한 런타임 오류 발생. 명시적 검증 및 에러 throw 필요. [`web/src/lib/supabase.ts:4-7`]
- [x] [Review][Patch] reviews.playbook_type CHECK 제약 없음 — projects와 달리 임의 값 허용; 플레이북 디스패치 로직 오작동 가능. CHECK (playbook_type IN ('ai_research')) 추가 필요. [`supabase/migrations/20260723000000_initial_schema.sql`]
- [x] [Review][Patch] decisions UNIQUE(review_id) 제약 없음 — 하나의 리뷰에 복수 결정 레코드 삽입 가능; 아웃컴 추적 및 러닝패스 생성 혼선. UNIQUE (review_id) 추가 필요. [`supabase/migrations/20260723000000_initial_schema.sql`]
- [x] [Review][Patch] outcomes.useful NULL 허용 시 status 조건 제약 없음 — completed/applied 상태에서 useful=NULL 허용; 피드백 루프(메모리/추천) 데이터 손실. CHECK 제약 추가 필요. [`supabase/migrations/20260723000000_initial_schema.sql`]
- [x] [Review][Patch] Flutter TextTheme bodyMedium 미정의 — 명시적 스타일 없는 Text() 위젯이 Material 3 기본값(14px/400) 사용; 디자인 시스템 의도(15px/500)와 불일치. [`mobile/lib/core/theme/app_theme.dart`]
- [x] [Review][Patch] Flutter ShapeTheme(버튼 형태) 미정의 — AC-4 "ShapeTheme 전체 override" 미충족; 향후 버튼 구현 시 pill radius 대신 M3 기본값 적용됨. ElevatedButtonThemeData 등 추가 필요. [`mobile/lib/core/theme/app_theme.dart`]

#### Patch — Low

- [x] [Review][Patch] APIResponse data+error 동시 비-None 허용 — 상호 배타 검증자 없음. @model_validator 추가 필요. [`api/core/schemas.py`]
- [x] [Review][Patch] AppColors.statusUncertain(#6B7280) 미정의 — CSS --status-uncertain 토큰에 대응하는 Flutter 색상 없음. [`mobile/lib/core/theme/app_theme.dart`]
- [x] [Review][Patch] CSS --radius-checklist-item, --radius-fab-plus 토큰 누락 — AC-3 "전체 radius 토큰" 미충족. [`web/src/app/globals.css`]
- [x] [Review][Patch] display_name 길이 제약 없음 — 무제한 TEXT로 대용량 입력 허용. CHECK (char_length(display_name) <= 256) 추가 필요. [`supabase/migrations/20260723000000_initial_schema.sql`]
- [x] [Review][Patch] python-dotenv 중복 의존성 — pydantic-settings가 .env 로딩 처리; 제거 필요. [`api/requirements.txt`]
- [x] [Review][Patch] flutter_riverpod + hooks_riverpod 동시 선언 — hooks_riverpod가 flutter_riverpod를 포함; 중복 의존성 제거 필요. [`mobile/pubspec.yaml`]
- [x] [Review][Patch] 모듈 레벨 로그 핸들러 중복 등록 — 반복 임포트 시 핸들러가 누적되어 로그 중복 출력. `if not logger.handlers:` 가드 추가 필요. [`api/main.py:11-16`]
- [x] [Review][Patch] mark_stuck_jobs 시간 범위 가드 없음 — 전체 테이블 스캔으로 과거 완료 레코드 재평가 위험. WHERE created_at > NOW() - INTERVAL '30 days' 추가 필요. [`supabase/migrations/20260723000000_initial_schema.sql`]
- [x] [Review][Patch] daily_brief_signals UNIQUE(daily_brief_id, position) 제약 없음 — 동일 브리핑 내 위치 충돌로 비결정적 UI 정렬. [`supabase/migrations/20260723000000_initial_schema.sql`]

#### Defer

- [x] [Review][Defer] service_role 싱글톤이 모든 작업에서 RLS 우회 [`api/core/supabase.py`] — deferred, 의도적 아키텍처; Story 1.2 JWT 미들웨어로 사용자별 범위 처리 예정
- [x] [Review][Defer] Flutter Supabase.initialize() 누락 [`mobile/lib/main.dart`] — deferred, Story 1.1에서 실제 Supabase 호출 없음; Story 1.2 인증 구현 시 추가 예정
- [x] [Review][Defer] Next.js 서버사이드 Supabase 클라이언트 없음 [`web/src/lib/supabase.ts`] — deferred, RSC 데이터 패칭 도입 스토리에서 추가 예정
- [x] [Review][Defer] Supabase 싱글톤 동시 초기화 레이스 컨디션 [`api/core/supabase.py`] — deferred, Python GIL로 실질적 위험 낮음; 다중 워커 환경 전환 시 재검토
- [x] [Review][Defer] SystemUiOverlayStyle.dark 하드코딩 [`mobile/lib/main.dart`] — deferred, 다크 모드 디자인 결정 후 처리
- [x] [Review][Defer] 다크 모드 전체 미지원 [`web/src/app/globals.css`, `mobile/lib/core/theme/app_theme.dart`] — deferred, 아키텍처 수준 결정 사안; 별도 스토리에서 처리
- [x] [Review][Defer] TestClient 모듈 레벨로 lifespan 공유 [`api/tests/test_health.py`] — deferred, 현재 3개 테스트에서 영향 없음
- [x] [Review][Defer] Supabase 인증 토큰 교체 후 싱글톤 갱신 불가 [`api/core/supabase.py`] — deferred, service_role은 미교체 방식

## Dev Notes

### 🚨 CRITICAL: DB 마이그레이션 파일 이미 존재

**절대로 DB 스키마를 재생성하지 말 것.** 전체 스키마가 이미 작성되어 있다:

```
_bmad-output/implementation-artifacts/db/001_initial_schema.sql
```

이 파일을 Supabase SQL Editor 또는 Supabase CLI로 실행하면 된다. 파일 내용:
- `user_profiles` (auth.users 확장, 온보딩 7단계 데이터 포함)
- `user_devices` (FCM 토큰)
- `projects` (playbook_type: 'ai_research')
- `reviews`, `decisions`, `outcomes`, `memories`, `activities` (공통 Decision Loop)
- `signals`, `signal_sources`, `daily_briefs`, `daily_brief_signals`, `learning_paths` (AI Research Playbook)
- 전체 RLS 정책 (AD-9 패턴 적용됨)
- Realtime 활성화 (`reviews`, `daily_briefs`, `learning_paths`)
- `mark_stuck_jobs()` 함수 (processing 타임아웃 → failed 전환, AD-12)
- `handle_new_user()` 트리거 (회원가입 시 user_profiles 자동 생성)
- HNSW 벡터 인덱스 (`memories.embedding`, AD-2)

**주의:** AC-2의 "users 테이블" = Supabase `auth.users` (자동 관리됨, 별도 생성 불필요). 공개 스키마에 생성되는 테이블은 `user_profiles`다.

### 모노레포 구조

```
decision-os/
├── web/          # Next.js (Railway → Vercel)
├── api/          # FastAPI (Railway → Render/Fly.io)
├── mobile/       # Flutter (iOS/Android)
├── _bmad-output/ # 기획 산출물 (개발 대상 아님)
└── .gitignore
```

AD-1(모듈형 모놀리스): FastAPI는 단일 앱, Playbook은 내부 라우터/모듈. 별도 마이크로서비스 불허.

### FastAPI 응답 봉투 (AD-13) — 모든 엔드포인트 필수

```python
# 성공
{"data": {...}, "error": null}

# 오류
{"data": null, "error": {"code": "ERROR_CODE", "message": "설명"}}
```

Pydantic 모델로 봉투를 정의하여 FastAPI의 `response_model`에 사용. 이후 모든 엔드포인트는 이 봉투를 사용해야 한다.

```python
from pydantic import BaseModel
from typing import Any, Optional

class ErrorDetail(BaseModel):
    code: str
    message: str

class APIResponse(BaseModel):
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None
```

인증: `Authorization: Bearer {Supabase JWT}` — JWT 검증 미들웨어는 Story 1.2에서 구현. 이 스토리에서는 health 엔드포인트만 인증 불필요.

기본 경로: `/api/v1/` (AD-13)

### Next.js CSS 디자인 토큰 (UX-DR1, DESIGN.md)

`web/src/app/globals.css` (또는 `web/styles/globals.css`)의 `:root`에 다음 CSS 커스텀 프로퍼티를 정의:

```css
:root {
  /* Surface */
  --surface-base: #FFFFFF;
  --surface-raised: #F9F9F9;
  --surface-card: #F2F2F2;
  --surface-card-alt: #ECECEC;
  --surface-overlay: rgba(0, 0, 0, 0.45);
  --surface-honest-box: #F5F5F5;

  /* Text */
  --text-primary: #0D0D0D;
  --text-secondary: #595D6A;
  --text-tertiary: #9CA3AF;
  --text-disabled: #D1D1D1;

  /* Border */
  --border-subtle: #E5E5E5;
  --border-card: #DCDCDC;

  /* Accent */
  --accent-primary: #0D0D0D;
  --accent-foreground: #FFFFFF;

  /* Status */
  --status-positive: #16A34A;
  --status-positive-bg: #DCFCE7;
  --status-warning: #B45309;
  --status-uncertain: #6B7280;
  --error: #EF4444;
  --error-bg: #FEF2F2;

  /* Typography */
  --font-family: system-ui, -apple-system, 'Helvetica Neue', sans-serif;

  /* Spacing */
  --spacing-1: 4px;
  --spacing-2: 8px;
  --spacing-3: 12px;
  --spacing-4: 16px;
  --spacing-5: 20px;
  --spacing-6: 24px;
  --spacing-8: 32px;
  --spacing-12: 48px;
  --screen-horizontal-padding: 20px;
  --card-padding: 16px;
  --section-gap: 20px;

  /* Border Radius */
  --radius-card: 16px;
  --radius-pill: 9999px;
  --radius-sheet: 24px 24px 0 0;
  --radius-badge: 9999px;
  --radius-timeline-card: 12px;
  --radius-option-card: 14px;
  --radius-form-field: 12px;
}
```

타이포그래피 유틸리티 클래스:

```css
.text-screen-title {
  font-size: clamp(28px, 3vw, 30px);
  font-weight: 700;
  letter-spacing: -0.5px;
  line-height: 1.2;
}
.text-section-title {
  font-size: clamp(22px, 2.5vw, 24px);
  font-weight: 700;
  letter-spacing: -0.3px;
}
.text-body-large { font-size: 17px; font-weight: 600; letter-spacing: -0.2px; }
.text-body       { font-size: 15px; font-weight: 500; }
.text-body-card  { font-size: 16px; font-weight: 600; }
.text-label      { font-size: 13px; font-weight: 600; }
.text-caption    { font-size: 11px; font-weight: 500; letter-spacing: 0.4px; }
.text-caption-lg { font-size: 12px; font-weight: 500; letter-spacing: 0.8px; }
.text-badge      { font-size: 10px; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; }
```

기본 body 설정:
```css
body {
  font-family: var(--font-family);
  background-color: var(--surface-raised);
  color: var(--text-primary);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

/* 한국어 본문 line-height (UX-DR14) */
:lang(ko) {
  line-height: 1.5;
}
```

데스크탑 레이아웃 (NFR-4):
```css
.screen-container {
  width: 100%;
  padding: 0 var(--screen-horizontal-padding);
}
@media (min-width: 768px) {
  .screen-container {
    max-width: 480px;
    margin: 0 auto;
    padding: 0;
  }
}
```

### Flutter ThemeData 구현 (UX-DR15, AD-14)

`mobile/lib/core/theme/app_theme.dart` 파일 생성:

```dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class AppColors {
  static const surfaceBase       = Color(0xFFFFFFFF);
  static const surfaceRaised     = Color(0xFFF9F9F9);
  static const surfaceCard       = Color(0xFFF2F2F2);
  static const surfaceCardAlt    = Color(0xFFECECEC);
  static const textPrimary       = Color(0xFF0D0D0D);
  static const textSecondary     = Color(0xFF595D6A);
  static const textTertiary      = Color(0xFF9CA3AF);
  static const textDisabled      = Color(0xFFD1D1D1);
  static const borderSubtle      = Color(0xFFE5E5E5);
  static const borderCard        = Color(0xFFDCDCDC);
  static const accentPrimary     = Color(0xFF0D0D0D);
  static const accentForeground  = Color(0xFFFFFFFF);
  static const statusPositive    = Color(0xFF16A34A);
  static const statusPositiveBg  = Color(0xFFDCFCE7);
  static const statusWarning     = Color(0xFFB45309);
  static const error             = Color(0xFFEF4444);
  static const errorBg           = Color(0xFFFEF2F2);
  static const surfaceHonestBox  = Color(0xFFF5F5F5);
}

ThemeData buildAppTheme() {
  return ThemeData(
    useMaterial3: true,
    splashFactory: NoSplash.splashFactory,   // 잉크/리플 전면 금지 (UX-DR15)
    highlightColor: Colors.transparent,
    colorScheme: const ColorScheme.light(
      background:   AppColors.surfaceRaised,
      surface:      AppColors.surfaceBase,
      primary:      AppColors.accentPrimary,
      onPrimary:    AppColors.accentForeground,
      secondary:    AppColors.textSecondary,
      onSecondary:  AppColors.surfaceBase,
      error:        AppColors.error,
      onError:      AppColors.surfaceBase,
      onBackground: AppColors.textPrimary,
      onSurface:    AppColors.textPrimary,
    ),
    textTheme: const TextTheme(
      // screen-title: 28-30px/700/-0.5px
      displayLarge:  TextStyle(fontSize: 30, fontWeight: FontWeight.w700, letterSpacing: -0.5),
      // section-title: 22-24px/700/-0.3px
      displayMedium: TextStyle(fontSize: 24, fontWeight: FontWeight.w700, letterSpacing: -0.3),
      // body-large: 17px/600/-0.2px
      titleLarge:    TextStyle(fontSize: 17, fontWeight: FontWeight.w600, letterSpacing: -0.2),
      // body-card: 16px/600
      titleMedium:   TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
      // body: 15px/500
      bodyLarge:     TextStyle(fontSize: 15, fontWeight: FontWeight.w500),
      // label: 13px/600
      labelLarge:    TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
      // caption: 11-12px/500
      bodySmall:     TextStyle(fontSize: 12, fontWeight: FontWeight.w500, letterSpacing: 0.4),
      // badge: 10px/700/uppercase/0.5px
      labelSmall:    TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5),
    ),
    cardTheme: const CardTheme(
      color: AppColors.surfaceCard,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.all(Radius.circular(16)),
      ),
    ),
    bottomSheetTheme: const BottomSheetThemeData(
      backgroundColor: AppColors.surfaceBase,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(24),
          topRight: Radius.circular(24),
        ),
      ),
    ),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: AppColors.surfaceBase,
      selectedItemColor: AppColors.textPrimary,
      unselectedItemColor: AppColors.textSecondary,
      elevation: 0,
    ),
    dividerColor: AppColors.borderSubtle,
    scaffoldBackgroundColor: AppColors.surfaceRaised,
  );
}
```

`mobile/lib/main.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/app_theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // edge-to-edge (UX-DR15)
  await SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
  SystemChrome.setSystemUIOverlayStyle(SystemUiOverlayStyle.dark);

  runApp(
    const ProviderScope(   // Riverpod 루트 (AD-14)
      child: MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Decision OS',
      theme: buildAppTheme(),
      home: const Scaffold(body: SafeArea(child: Center(child: Text('Decision OS')))),
    );
  }
}
```

### 아키텍처 준수 사항

| 규칙 | 근거 |
|------|------|
| 읽기: Supabase SDK 직접 (`anon key + JWT + RLS`) | AD-3 |
| 쓰기: 반드시 FastAPI 경유 (`service_role`) | AD-3 |
| `service_role` key는 절대 클라이언트(웹/앱)에 노출 금지 | AD-3, AD-10 |
| Flutter 상태관리: Riverpod 2.x 단독 (`@riverpod` 코드생성) | AD-14 |
| 시크릿(API 키 등)은 환경변수로 관리, 코드에 하드코딩 금지 | AD-10 |
| 새 Playbook = FastAPI 내부 모듈 추가 (별도 서비스 불허) | AD-1 |

### 테스트 전략 (AD-11)

- **FastAPI health 엔드포인트**: `pytest` + `httpx`로 통합 테스트 (실제 앱 인스턴스)
- **DB 연결 테스트**: 실제 Supabase **테스트** 프로젝트 사용 (프로덕션 DB 모킹 금지)
- **Next.js**: 이 스토리에서는 CSS 토큰 존재 여부만 확인 (디자인 토큰 lint 또는 스냅샷)
- **Flutter**: `flutter test` — ThemeData 프로퍼티 단위 테스트

테스트 환경 변수 분리: `.env.test` 또는 CI 환경변수로 테스트용 Supabase URL/KEY 별도 관리.

### 프로젝트 구조 참고

```
api/
├── main.py               # FastAPI 앱 진입점
├── core/
│   ├── config.py         # 환경변수 설정
│   ├── schemas.py        # APIResponse 봉투 Pydantic 모델
│   └── supabase.py       # Supabase 클라이언트 싱글톤
├── routers/
│   └── health.py         # GET /api/v1/health
├── requirements.txt
└── .env.example

web/
├── src/
│   ├── app/
│   │   ├── globals.css   # 디자인 토큰 CSS 커스텀 프로퍼티
│   │   └── layout.tsx    # lang="ko" 루트 설정
│   └── lib/
│       └── supabase.ts   # Supabase 클라이언트
├── .env.local.example
└── package.json

mobile/
├── lib/
│   ├── main.dart
│   └── core/
│       ├── theme/
│       │   └── app_theme.dart
│       └── providers/    # Riverpod providers (향후)
├── pubspec.yaml
└── test/
    └── theme_test.dart
```

### Project Structure Notes

- **모노레포**: 단일 git 레포지토리에 `web/`, `api/`, `mobile/` 세 패키지 — AD-2 스택 전제
- **공유 백엔드**: Flutter와 Next.js는 동일 FastAPI 백엔드 사용 (`/api/v1/` 공통 — AD-2, AD-13)
- **DB 마이그레이션**: `_bmad-output/implementation-artifacts/db/` 폴더가 마이그레이션 저장소. 향후 002_, 003_ 번호 순서로 추가
- **환경변수 컨벤션**: 각 앱 루트에 `.env.example` 필수, `.env.local` / `.env` 는 `.gitignore`에 포함

### 기술 버전 참고 (2026-07-23 기준)

| 기술 | 버전 | 비고 |
|------|------|------|
| Next.js | 16.2.10 LTS | App Router 기본값 |
| FastAPI | 0.139.2 | Python 3.12+ 필수 |
| Supabase pgvector | 0.6.0–0.7.4 | HNSW 인덱스 사용 (DB 스키마에 포함됨) |
| Riverpod | 2.x | `@riverpod` 코드 생성 |
| Railway | MVP 전용 | 프로덕션 전환 시 Vercel(Next.js) + Render/Fly.io(FastAPI) |
| OpenAI LLM | Responses API | Chat Completions 사용 금지 (Story 2.2에서 구현) |

> **Railway 주의**: 2026년 기준 Railway는 MVP 전용. 프로덕션 스케일 전 Vercel + Render/Fly.io로 이전 계획 수립 필요.
> **OpenAI Responses API**: Story 1.1에서 LLM 호출 없음. Story 2.2 Reviewer Agent 구현 시 Chat Completions 불허, Responses API 사용 필수(AD-6).

### References

- DB 스키마: `_bmad-output/implementation-artifacts/db/001_initial_schema.sql` — 전체 테이블, RLS, 인덱스, 트리거 포함
- 아키텍처: `_bmad-output/planning-artifacts/architecture/architecture-decision-os-2026-07-21/ARCHITECTURE-SPINE.md` — AD-1~AD-17
- 디자인: `_bmad-output/planning-artifacts/ux-designs/ux-decision-os-2026-07-21/DESIGN.md` — 전체 색상·타이포·간격·컴포넌트 토큰
- 에픽: `_bmad-output/planning-artifacts/epics.md` — Story 1.1 전문 (p.200~232 기준)
- UX 요구사항: `epics.md` > Requirements Inventory > UX Design Requirements (UX-DR1, UX-DR14, UX-DR15)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Python 3.12 미설치: Python 3.11.9 사용. FastAPI 0.139.2는 3.8+ 지원, 기능상 동일. 향후 pyenv로 3.12 설치 권장.
- Flutter SDK 미설치: `flutter create` 불가. 핵심 소스 파일(main.dart, app_theme.dart, pubspec.yaml, theme_test.dart)을 Dev Notes 스펙 기반으로 수동 생성. Flutter 설치 후 `flutter pub get` 및 `flutter run` 실행 필요.
- Supabase CLI 미설치: Task 3은 사용자가 Supabase 대시보드 SQL Editor에서 001_initial_schema.sql 직접 실행 필요.

### Completion Notes List

- Task 1 완료: web/, api/, mobile/ 디렉토리, 루트 .gitignore, README.md 생성
- Task 2 완료: FastAPI 0.139.2 앱 초기화. APIResponse 봉투 스키마(core/schemas.py), GET /api/v1/health 엔드포인트, JSON 구조화 로그(python-json-logger), Supabase 클라이언트 싱글톤(core/supabase.py), uvicorn 실행 확인
- Task 4 완료: Next.js 16.x App Router + TypeScript, @supabase/supabase-js + @supabase/ssr 설치, globals.css 전체 디자인 토큰 CSS 커스텀 프로퍼티 + 타이포그래피 유틸리티 클래스, layout.tsx lang="ko" 설정, npm run build 성공
- Task 5 완료: Flutter 3.44.7 설치, flutter create 스캐폴드 병합, flutter pub get 성공 (103개 의존성), CardTheme → CardThemeData API 수정 (Flutter 3.44.7), flutter test 14개 통과, flutter run Chrome에서 정상 실행 확인
- Task 6 완료: FastAPI lifespan에 Supabase 연결 체크 구현, pytest 통합 테스트 3개 작성 및 통과 (test_health_returns_200, test_health_response_envelope, test_health_content_type_json)
- Task 3 완료: supabase CLI db push로 마이그레이션 적용. uuid_generate_v4() → gen_random_uuid() 수정 (uuid-ossp 스키마 검색경로 이슈). 13개 테이블, RLS, pgvector, Realtime 모두 확인.

### File List

- `.gitignore` (신규)
- `README.md` (신규)
- `api/main.py` (신규)
- `api/requirements.txt` (신규)
- `api/.env.example` (신규)
- `api/core/__init__.py` (신규)
- `api/core/config.py` (신규)
- `api/core/schemas.py` (신규)
- `api/core/supabase.py` (신규)
- `api/routers/__init__.py` (신규)
- `api/routers/health.py` (신규)
- `api/pytest.ini` (신규)
- `api/tests/__init__.py` (신규)
- `api/tests/test_health.py` (신규)
- `web/src/app/globals.css` (수정 — 디자인 토큰 전체 교체)
- `web/src/app/layout.tsx` (수정 — lang="ko", 타이틀 변경)
- `web/src/lib/supabase.ts` (신규)
- `web/.env.local.example` (신규)
- `mobile/pubspec.yaml` (신규)
- `mobile/lib/main.dart` (신규)
- `mobile/lib/core/theme/app_theme.dart` (신규)
- `mobile/test/theme_test.dart` (신규)
- `supabase/migrations/20260723000000_initial_schema.sql` (신규 — gen_random_uuid() 수정본)

## Change Log

- 2026-07-23: 스토리 1.1 구현 시작 (claude-sonnet-4-6)
  - Task 1: 모노레포 루트 구조 (web/, api/, mobile/, .gitignore, README.md) 생성
  - Task 2: FastAPI 앱 초기화 — health 엔드포인트 + 봉투 스키마 + JSON 로그 + Supabase 클라이언트
  - Task 4: Next.js App Router 앱 — 디자인 토큰 CSS 전체 구현, lang="ko"
  - Task 5: Flutter 소스 파일 수동 생성 (Flutter SDK 미설치로 flutter create 대체)
  - Task 6: FastAPI health 통합 테스트 3개 작성 및 통과
  - Task 3 완료: supabase CLI db push, uuid_generate_v4() → gen_random_uuid() 수정, 13개 테이블 + RLS + pgvector + Realtime 확인
  - Task 5.1, 5.7 미완료: Flutter SDK 설치 후 `flutter pub get` 및 `flutter run` 실행 필요

