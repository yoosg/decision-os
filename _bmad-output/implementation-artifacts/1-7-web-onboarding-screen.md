# Story 1.7: Web Onboarding Screen

---
baseline_commit: NO_VCS
---

Status: done

<!-- 출처: Story 5.2 라이브 검증 중 발견된 웹 공백 보정 스토리. 웹 signin/signup(1-2)이 `/onboarding`으로 라우팅하나 웹 온보딩 페이지가 어떤 스토리에서도 구현되지 않아 로그인 직후 404 발생(GET /onboarding = 404). Flutter 온보딩(1-5)은 존재하나 웹은 누락. -->

## Story

신규 웹 사용자로서,
로그인 직후 온보딩 화면에서 내 역할·경험·기술 스택·관심 영역·일일 학습 시간을 등록할 수 있기를 원한다,
그래서 개인화된 Daily Brief를 받고 로그인 직후 404를 만나지 않는다.

**범위**: 웹 전용(Flutter 1-5와 패리티). 신규 API 없음 — 기존 `POST /api/v1/onboarding/complete`(Story 1-5 산출물, `api/routers/onboarding.py`) 재사용.

## Acceptance Criteria

**AC-1: 온보딩 라우트 존재 및 도달**
- **Given** `onboarding_completed=false`인 인증 사용자가 로그인/회원가입을 완료하면
- **Then** `signin`/`signup`의 기존 `router.push("/onboarding")`가 **실제 페이지로 연결**되어 404가 발생하지 않는다
- **And** 이 페이지는 4탭 셸(bottom-nav) 밖의 독립 라우트(`web/src/app/onboarding/page.tsx`)로 렌더링된다

**AC-2: 다단계 입력 폼(Flutter 1-5 패리티)**
- **Then** 역할(`role`), 경험 수준(`experience_level`), 기술 스택(`tech_stack[]`), 프로젝트 목표(`project_goal`), 관심 영역(`interests[]`), 일일 학습 시간(`daily_learning_time_min`)을 입력받는다
- **And** enum 값은 API 계약과 정확히 일치: `role ∈ {frontend,backend,ai_engineer,pm,designer,student,other}`, `experience_level ∈ {beginner,intermediate,advanced}`, `project_goal ∈ {ai_side_project,rag_service,agent_architecture,work_automation,ai_adoption,other}`, `daily_learning_time_min ∈ {15,30,60}` (UX 스펙 유효값)

**AC-3: 제출 및 완료 라우팅**
- **When** 완료 CTA를 누르면 `POST /api/v1/onboarding/complete`(Bearer 토큰)로 프로필을 저장하고 서버가 `user_profiles.onboarding_completed=true` + 최초 `projects` 행을 생성한다
- **Then** 성공 시 `router.push("/home")`
- **And** 실패 시 에러 피드백을 노출하고 재시도를 허용한다(무한 로딩 금지)

**AC-4: 재진입/완료자 가드**
- **Given** 이미 `onboarding_completed=true`인 사용자가 `/onboarding`에 직접 접근하면
- **Then** `/home`으로 리다이렉트한다(온보딩 프로필 덮어쓰기 방지 — Flutter 1-5 Review Findings와 동일한 실수 반복 금지)

## Tasks / Subtasks

- [x] Task 1: `web/src/app/onboarding/page.tsx` 신규 (Client Component) (AC: 1,2,3)
  - [x] 1.1 `createClient()`로 세션 확인 — 세션 없으면 `/signin`, `onboarding_completed=true`면 `/home`로 리다이렉트(AC-4)
  - [x] 1.2 다단계(step) 폼 상태 + enum 옵션 정의(위 AC-2 값). `signin/page.tsx`의 입력/버튼 스타일 토큰 재사용
  - [x] 1.3 완료 시 `getSession()` 토큰으로 `POST ${NEXT_PUBLIC_FASTAPI_URL}/api/v1/onboarding/complete` 호출, 성공 → `/home`, 실패 → 에러 표시(`outcome/page.tsx` 토스트/에러 패턴 참고)
  - [x] 1.4 `.timeout` 상당(AbortController)로 무한 로딩 방지
- [x] Task 2: 완료자 재진입 가드 (AC: 4) — 페이지 진입 시 프로필 조회 후 분기(1.1과 통합 가능)
- [x] Task 3: (선택) `web/src/app/page.tsx`/미들웨어에 온보딩 게이트 추가 여부 결정 — 현재 웹은 전역 온보딩 강제 게이트가 없고 signin/signup 경유로만 진입. 최소 구현은 페이지 생성까지, 게이트는 설계 결정으로 분리
- [x] Task 4: 스펙 문서 테스트 `web/src/app/onboarding/__tests__/onboarding.test.tsx`(러너 없음, `@ts-nocheck` 컨벤션) — enum 매핑/완료 라우팅/재진입 가드 검증

### Review Findings (code-review 2026-07-28)

- [x] [Review][Defer] 웹 전역 온보딩 완료 게이트 부재 — `onboarding_completed=false`(또는 프로필 행 없음) 사용자가 `/home`·`/profile`에 직접 URL 접근 시 온보딩 스킵 가능. — deferred: 진입점(signin/signup) 라우팅이 정상 유저 흐름을 커버하고, 미들웨어 전역 체크는 요청마다 DB 조회 비용 발생 → 저빈도 엣지케이스로 수용(1-7 설계 결정과 일치). 필요 시 별도 개선.
- [x] [Review][Patch] 온보딩 마운트 가드 try/catch 부재 — `getUser()`/`user_profiles` 쿼리 throw(네트워크/Supabase 장애) 시 `setReady(true)` 미도달로 영구 blank 화면(`return null`) [web/src/app/onboarding/page.tsx] — 수정: try/catch 추가, catch 시 fail-open으로 `setReady(true)`
- [x] [Review][Patch] `다음` 버튼 rapid 더블클릭 시 스텝 스킵 — `setStep(s=>s+1)`가 리렌더 전 2회 발화 → 필수 스텝(예: 경험) 건너뜀 → null 제출 → 백엔드 422(graceful하나 혼란) [web/src/app/onboarding/page.tsx] — 수정: `goNext`/`이전`을 closure 캡처 `step` 기반(`setStep(step±1)`)으로 idempotent화
- [x] [Review][Defer] 401(만료됐지만 존재하는 토큰) 일반 에러와 미구분·재로그인 미유도 — 앱 전반 패턴(outcome/context-sticky-bar 동일) [web/src/app/onboarding/page.tsx] — deferred, pre-existing
- [x] [Review][Defer] `NEXT_PUBLIC_FASTAPI_URL` localhost 폴백 — 미설정 prod 빌드에서 client가 localhost 타깃, 코드베이스 전역 패턴 [web/src/app/onboarding/page.tsx] — deferred, pre-existing

## Dev Notes

- **API 계약(재사용, 신규 없음)**: `api/routers/onboarding.py` → `POST /api/v1/onboarding/complete`, body `{role, experience_level, tech_stack, project_goal, interests, daily_learning_time_min}`. 서버가 `user_profiles` 갱신 + `projects` upsert 수행(1-5 Review에서 TOCTOU/미검증 패치 반영됨).
- **미들웨어**: `web/src/middleware.ts`는 이미 `/onboarding`을 `isAuthRoute`로 취급 → 미인증만 `/signin`으로 보냄. 인증된 미온보딩 사용자는 통과.
- **재사용 패턴**: `signin/page.tsx`(폼/입력/CTA 스타일, 라우팅), `outcome/page.tsx`(토큰 fetch + 토스트/에러), `createClient()`(`@/lib/supabase`).
- **알려진 갭(1-5)**: 완료자 `/onboarding` 재진입 시 프로필 덮어쓰기 위험 → AC-4 가드 필수.
- **참조**: Flutter `mobile/lib/features/onboarding/screens/onboarding_screen.dart`(입력 항목/순서/enum), Story 1-5, 1-2(웹 인증 라우팅 origin).

## Dev Agent Record

### Agent Model Used
claude-opus-4-8 (BMad dev-story)

### Debug Log References
- **Web tsc**: `npx tsc --noEmit` → 신규 파일 0 오류(기존 `chat/page.tsx` 사전 이슈 제외).
- **라이브 브라우저 검증 (puppeteer + 실제 Chrome, dev 서버 실행 중)**:
  - Part A — 미온보딩 유저(`test-history`, `onboarding_completed=false`) 로그인 → **`/onboarding` 위저드 렌더(원래 404였던 경로, 이제 404 아님)**. 6스텝(역할→경험→기술스택→목표→관심→학습시간) 전부 진행 확인. 완료 클릭 시 FastAPI(:8000) 미기동으로 **graceful 에러("저장 중 오류가 발생했습니다") 표시 + /home 이동 안 함**(AC-3 실패 경로). 페이지 에러 0.
  - Part B — 완료 유저(`yousk6347`, `onboarding_completed=true`)가 `/onboarding` 직접 진입 → **`/home`으로 리다이렉트**(AC-4 가드). ✅
  - **제한**: submit 성공→`/home` happy path 는 FastAPI 백엔드 미기동(서비스롤 키·`.env` 부재)으로 라이브 미검증. fetch 페이로드/enum 매핑/성공 라우팅은 스펙 테스트(`onboarding.test.tsx`)로 커버. 백엔드 기동 시 동작 예상.

### Completion Notes List
- 라우트 위치: `web/src/app/onboarding/page.tsx` — `(app)` 셸(bottom-nav) 밖 최상위 라우트로 배치(온보딩 중 탭바 미노출).
- **설계 결정(Task 3)**: 전역 온보딩 게이트(미들웨어/root)는 추가하지 않음. signin/signup 이 이미 미온보딩 사용자를 `/onboarding` 으로 push 하고, 페이지 자체 가드(세션 없음→`/signin`, 완료됨→`/home`)만 수행. 전역 강제 게이트는 모든 라우트 동작을 바꾸는 큰 변경이라 별도 판단으로 분리(Flutter는 GoRouter redirect로 강제하나 웹은 진입점 기반).
- enum 값 집합을 API 계약(`Literal[...]`)과 정확히 일치시킴. `daily_learning_time_min ∈ {15,30,60}`.
- AbortController 30s 타임아웃으로 무한 로딩 방지.

### File List
**신규**
- `web/src/app/onboarding/page.tsx`
- `web/src/app/onboarding/__tests__/onboarding.test.tsx` (스펙 문서)

## Change Log

| 날짜 | 변경 내용 |
|------|----------|
| 2026-07-28 | Story 1.7 생성 — 5.2 라이브 검증에서 발견된 웹 온보딩 공백(로그인 후 /onboarding 404) 보정. Flutter 1-5 패리티. |
| 2026-07-28 | Story 1.7 구현 완료 (dev-story) — 웹 온보딩 위저드 신규(`onboarding/page.tsx`) + 완료자 가드. 라이브 브라우저로 404 제거·위저드·가드 검증(submit happy path는 백엔드 미기동으로 스펙테스트 커버). tsc 무오류. Status → review. |
| 2026-07-28 | code-review (3-layer 병렬) — patch 2건 수정(마운트 가드 try/catch, 다음 더블클릭 스텝스킵 방지), decision 1건 defer(전역 온보딩 게이트), defer 2건. tsc·라이브 무회귀 확인. Status → done. |
