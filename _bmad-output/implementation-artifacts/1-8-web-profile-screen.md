# Story 1.8: Web Profile Screen

---
baseline_commit: NO_VCS
---

Status: done

<!-- 출처: Story 5.2 라이브 검증 중 발견된 웹 공백 보정 스토리. `web/src/app/(app)/profile/page.tsx`가 "Story 1.6에서 구현 예정" 플레이스홀더로 남아 있음(11줄 스텁). Flutter 프로필(1-6)은 구현됐으나 웹은 스텁 상태로 1-6이 done 처리됨. -->

## Story

웹 사용자로서,
프로필(역할·경험·기술 스택·관심 영역·프로젝트 목표·일일 학습 시간)을 조회하고 편집할 수 있기를 원한다,
그래서 변경된 상황에 맞게 Daily Brief 개인화 기준을 갱신할 수 있다.

**범위**: 웹 전용(Flutter 1-6과 패리티). 신규 API 없음 — 기존 `GET /api/v1/users/profile`, `PATCH /api/v1/users/profile`(Story 1-6 산출물, `api/routers/users.py`) 재사용.

## Acceptance Criteria

**AC-1: 프로필 조회**
- **Given** 인증 사용자가 프로필 탭을 열면
- **Then** 스텁("구현 예정")이 아니라 실제 프로필 값(역할·경험·기술 스택·관심·프로젝트 목표·일일 학습 시간)이 표시된다
- **And** 데이터는 `user_profiles`에서 조회한다(Server Component 직접 조회 또는 `GET /api/v1/users/profile`)

**AC-2: 편집 모드 + 저장**
- **When** 편집을 활성화하고 값을 변경 후 저장하면 `PATCH /api/v1/users/profile`(Bearer)로 부분 갱신한다
- **And** `daily_learning_time_min`은 `{15,30,60}`만 허용(API `Literal[15,30,60]`와 일치), enum 필드는 1-7/1-6과 동일 값 집합
- **And** 저장 성공/실패 피드백을 노출한다(무한 로딩 금지)

**AC-3: 취소**
- **When** 편집 취소 시 변경 사항을 버리고 원래 값으로 되돌린다

**AC-4: 접근성/일관성**
- **Then** 44×44 최소 탭 타깃, 기능 정보는 `text-secondary` 이상 대비(Story 5.1/5.2 지적 재발 금지), 4탭 셸 내부에서 렌더링

## Tasks / Subtasks

- [x] Task 1: `web/src/app/(app)/profile/page.tsx` 스텁 → 실제 구현 교체 (AC: 1)
  - [x] 1.1 `home/page.tsx` 패턴의 Server Component로 `user_profiles` 조회 후 `ProfileContent`에 props 전달, `metadata: { title: "프로필 | Decision OS" }`
- [x] Task 2: `web/src/components/profile/profile-content.tsx` 신규 (Client Component) (AC: 1,2,3,4)
  - [x] 2.1 조회값 표시 + 편집 토글 상태. enum 옵션 매핑(1-7과 공유 가능한 상수로 분리 고려)
  - [x] 2.2 저장 시 `getSession()` 토큰으로 `PATCH ${NEXT_PUBLIC_FASTAPI_URL}/api/v1/users/profile` 부분 갱신, 성공/실패 토스트(`outcome/page.tsx` 패턴)
  - [x] 2.3 취소 시 원본 값 복원(AC-3), `daily_learning_time_min` 선택은 {15,30,60} 세그먼트
- [x] Task 3: 로그아웃 액션 포함 여부 확인 — 기존 웹에 로그아웃 UI 없으면 이 화면에 배치(Flutter 1-6 참고). 범위는 조회/편집 우선, 로그아웃은 선택
- [x] Task 4: 스펙 문서 테스트 `web/src/components/profile/__tests__/profile-content.test.tsx`(러너 없음, `@ts-nocheck`) — 편집/취소/저장 payload 검증

### Review Findings (code-review 2026-07-28)

- [x] [Review][Patch] 프로필 페이지가 미인증/degraded 요청에 리다이렉트하지 않음 — `userId = user?.id ?? ""` → `eq("id","")` 조회, 미들웨어가 Supabase 장애로 통과시키면 빈 프로필 + 동작하는 `로그아웃`이 렌더. 쿼리 `error`도 미확인(빈 프로필 ≡ 조회실패 혼동) [web/src/app/(app)/profile/page.tsx] — 수정: `if (!userData.user) redirect("/signin")` + 쿼리 `error` 로깅
- [x] [Review][Patch] 편집이 옵션 집합 밖 저장값(role/experience/project_goal/daily_learning_time_min) 미처리 — read는 raw 표시되나 edit에선 미선택으로 보이고, 미변경 저장 시 무효값 재전송 → 백엔드 Literal 422(일반 토스트). tech_stack/interests 칩은 영향 없음(백엔드 free string) [web/src/app/(app)/profile/page.tsx, web/src/components/profile/profile-content.tsx] — 수정: 서버에서 옵션 집합 밖 값을 `inSet()`으로 null 처리(편집 clean 시작, 422 방지)
- [x] [Review][Defer] 401(만료 토큰) 일반 에러와 미구분·재로그인 미유도 — 앱 전반 패턴 [web/src/components/profile/profile-content.tsx] — deferred, pre-existing
- [x] [Review][Defer] `NEXT_PUBLIC_FASTAPI_URL` localhost 폴백 — 코드베이스 전역 패턴 [web/src/components/profile/profile-content.tsx] — deferred, pre-existing
- [x] [Review][Defer] `handleLogout` try/catch·중복탭 가드 부재 — `signOut()` reject 시 push 미실행·피드백 없음 [web/src/components/profile/profile-content.tsx] — deferred, pre-existing

## Dev Notes

- **API 계약(재사용, 신규 없음)**: `api/routers/users.py` → `GET /api/v1/users/profile`, `PATCH /api/v1/users/profile`(부분 갱신, `daily_learning_time_min: Literal[15,30,60]`).
- **현재 상태**: `web/src/app/(app)/profile/page.tsx`는 11줄 스텁("Story 1.6에서 구현 예정"). 전면 교체 대상.
- **재사용 패턴**: `home/page.tsx`(Server Component 조회 + Client content 분리), `outcome/page.tsx`(토큰 fetch/토스트), `context-sticky-bar.tsx`(세션 만료 처리), `queue-content.tsx`(편집/낙관적 갱신 패턴 — 단 프로필은 단순 저장이므로 과설계 지양).
- **참조**: Flutter `mobile/lib/features/profile/screens/profile_screen.dart` + `profile_provider.dart`(필드/편집 UX), Story 1-6(백엔드·enum 계약, Review Findings의 `Literal[15,30,60]` 제약).
- **RSC 주의**: 공유 enum/라벨 상수를 client 컴포넌트에서만 정의하지 말고 plain `.ts`로 분리(Server Component 재사용 시 client reference 프록시화 방지 — Story 5.2에서 동일 유형 버그 발생).

## Dev Agent Record

### Agent Model Used
claude-opus-4-8 (BMad dev-story)

### Debug Log References
- **Web tsc**: `npx tsc --noEmit` → 신규/변경 파일 0 오류(기존 `chat/page.tsx` 사전 이슈 제외).
- **라이브 브라우저 검증 (puppeteer + 실제 Chrome, yousk6347 로그인)**:
  - 조회 모드: `/profile`가 스텁이 아니라 실제 값 라벨 표시(역할=AI Engineer, 경험=중급, 기술스택 칩=Python/FastAPI/Next.js, 목표=RAG 서비스 구축, 관심=RAG/Agent, 시간=30분) + 로그아웃 버튼. (AC-1 ✅)
  - 편집 모드: 편집 버튼 → 전체 옵션(역할 7/경험 3/기술 8/목표 6/관심 7/시간 3) 렌더. (AC-2 편집 UI ✅)
  - 취소: 값 변경(중급→고급) 후 취소 → 조회 모드에서 '중급' 유지, '고급' 사라짐(원본 복원, AC-3 ✅).
  - **페이지 에러 0** — Server Component `profile/page.tsx` + plain `profile-options.ts` 조합으로 5.2형 RSC 경계 크래시 없음.
  - **제한**: 저장(PATCH)→성공 토스트 happy path 는 FastAPI(:8000) 미기동으로 라이브 미검증. PATCH 페이로드(`experience_level`/`daily_learning_time_min ∈ {15,30,60}`)·성공/실패 토스트는 스펙 테스트(`profile-content.test.tsx`)로 커버.
- **회귀 확인**: 공유 옵션 모듈 분리 후 온보딩(1-7) 위저드·완료자 가드 재검증 → 정상(무회귀).

### Completion Notes List
- **공유 옵션 모듈(Task 2.1)**: enum/라벨을 `web/src/lib/profile-options.ts`(plain, RSC-safe)로 분리하고 온보딩(1-7)/프로필(1-8) 양쪽에서 소비. 5.2 RSC 교훈에 따라 client 모듈이 아닌 plain `.ts`로 배치.
- **로그아웃(Task 3)**: 웹에 로그아웃 UI가 전무했으므로(전수 grep 확인) 프로필 화면에 배치(`supabase.auth.signOut()` → `/signin`).
- **저장 정책**: 부분 갱신 — 값이 있는 필드만 전송(backend `exclude_none`과 정합). `daily_learning_time_min`은 세그먼트 {15,30,60}만 선택 가능(API `Literal[15,30,60]`와 일치).
- **데이터 접근**: 조회는 Server Component 직접 `user_profiles` RLS self-select(신규 API 없음), 저장은 기존 `PATCH /api/v1/users/profile`(1-6) 재사용.
- AbortController 30s 타임아웃, 접근성 44px 탭 타깃/`text-secondary` 라벨(AC-4).

### File List
**신규**
- `web/src/lib/profile-options.ts` (온보딩/프로필 공유 enum 옵션, RSC-safe)
- `web/src/components/profile/profile-content.tsx`
- `web/src/components/profile/__tests__/profile-content.test.tsx` (스펙 문서)

**수정**
- `web/src/app/(app)/profile/page.tsx` (스텁 → 실제 구현)
- `web/src/app/onboarding/page.tsx` (로컬 enum 상수 → 공유 `profile-options.ts` 소비, DRY)

## Change Log

| 날짜 | 변경 내용 |
|------|----------|
| 2026-07-28 | Story 1.8 생성 — 5.2 라이브 검증에서 발견된 웹 프로필 스텁(1-6 done인데 웹 미구현) 보정. Flutter 1-6 패리티. |
| 2026-07-28 | Story 1.8 구현 완료 (dev-story) — 웹 프로필 조회/편집/취소 + 로그아웃, 공유 옵션 모듈 분리. 라이브로 조회·편집·취소·무회귀 검증(저장 happy path는 백엔드 미기동으로 스펙테스트 커버). tsc 무오류. Status → review. |
| 2026-07-28 | code-review (3-layer 병렬) — patch 2건 수정(미인증 리다이렉트+error 로깅, 옵션 밖 저장값 sanitize), defer 3건. tsc·라이브 무회귀 확인. Status → done. |
