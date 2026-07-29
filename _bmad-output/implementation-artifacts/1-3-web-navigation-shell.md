---
baseline_commit: NO_VCS
---

# Story 1.3: Web Navigation Shell

Status: done

## Story

웹 사용자로서,
4개 탭(홈/큐/히스토리/프로필)으로 구성된 하단 내비게이션으로 앱을 탐색할 수 있기를 원한다,
그래서 주요 기능 영역에 항상 빠르게 접근할 수 있다.

## Acceptance Criteria

**AC-1: 하단 내비게이션 바 표시**

- **Given** 로그인한 사용자가 앱에 접근할 때
- **When** 어떤 화면에서든 하단 내비게이션을 확인하면
- **Then** 홈·큐·히스토리·프로필 4개 탭이 고정 표시된다
- **And** 탭 바 상단에 `border-top: 1px solid var(--border-subtle)` 구분선이 있다
- **And** 탭 배경은 `surface-base` (#FFFFFF)이다

**AC-2: 언어 마킹 (UX-DR14)**

- **Given** `<html>` 루트 요소를 검사할 때
- **When** 페이지가 로드되면
- **Then** `lang="ko"` 속성이 설정되어 있다
- **And** "Review", "Signal", "Memory", "Learn Now", "Queue", "Ignore", "Daily Brief", "Learning Path", "Outcome", "NEW", "Applied", "Completed", "Dropped" 텍스트는 `<span lang="en">` 처리된다

**AC-3: 탭 내비게이션 & URL 라우팅**

- **Given** 각 탭에 placeholder 화면이 있을 때
- **When** 탭을 선택하면
- **Then** 해당 탭의 화면으로 이동하고 URL이 `/home`, `/queue`, `/history`, `/profile`로 변경된다
- **And** 데스크탑(≥768px)에서는 콘텐츠가 중앙 정렬, 최대 480px 너비로 표시된다

## Tasks / Subtasks

- [x] Task 1: `(app)` 라우트 그룹 레이아웃 생성 (AC: #1, #3)
  - [x] 1.1 `web/src/app/(app)/layout.tsx` 생성 — 서버 컴포넌트; 인증 체크(createServerSupabaseClient) + BottomNav Client Component + 데스크탑 centering wrapper
  - [x] 1.2 `web/src/components/layout/bottom-nav.tsx` 생성 — `'use client'` + `usePathname`으로 active 탭 감지 + 4개 탭 링크 + 디자인 토큰 스타일 적용

- [x] Task 2: 4개 Placeholder 페이지 생성 (AC: #3)
  - [x] 2.1 `web/src/app/(app)/home/page.tsx` — 홈 placeholder (영어 고유명사 `<span lang="en">` 패턴 예시 포함)
  - [x] 2.2 `web/src/app/(app)/queue/page.tsx` — 큐 placeholder
  - [x] 2.3 `web/src/app/(app)/history/page.tsx` — 히스토리 placeholder
  - [x] 2.4 `web/src/app/(app)/profile/page.tsx` — 프로필 placeholder

- [x] Task 3: 언어 마킹 패턴 검증 (AC: #2)
  - [x] 3.1 `web/src/app/layout.tsx`의 `lang="ko"` 확인 (이미 구현됨 — 수정 불필요)
  - [x] 3.2 Placeholder 페이지에 `<span lang="en">` 패턴 데모 — 향후 콘텐츠 개발자를 위한 컨벤션 확립

### Review Findings

- [x] [Review][Patch] AppLayout auth 호출 미보호 — try/catch 없음; Supabase 장애 시 모든 (app)/ 라우트 500 크래시 (middleware.ts는 동일 상황에서 try/catch로 통과 처리; 레이아웃과 일관성 불일치) [`web/src/app/(app)/layout.tsx:8-13`]
- [x] [Review][Patch] BottomNav iOS safe-area-inset-bottom 미처리 — `position: fixed; bottom: 0` 네브가 iPhone X+ 홈 인디케이터 영역 침범, 하단 탭 타겟 가려짐 (모바일 퍼스트 앱 HIGH 결함) [`web/src/components/layout/bottom-nav.tsx:18-26`]
- [x] [Review][Defer] `pb-16` 고정 패딩이 iOS safe-area 수정 후 동적 대응 필요 [`web/src/app/(app)/layout.tsx:17`] — deferred, pre-existing
- [x] [Review][Defer] Placeholder 페이지에 개발 스토리 번호 노출 ("Story X.X에서 구현 예정") — 실제 콘텐츠 구현 시 제거 — deferred, pre-existing
- [x] [Review][Defer] 4개 placeholder 페이지에 페이지별 `metadata` 미설정 (탭 간 브라우저 제목 구분 불가) — 실제 페이지 구현 스토리에서 추가 — deferred, pre-existing

## Dev Notes

### 🚨 CRITICAL: Next.js 16 파일 명명 규칙

**`middleware.ts` 유지** — Next.js 16 공식 문서는 `proxy.ts`로 마이그레이션할 것을 명시하지만,
Story 1.2 코드 리뷰에서 `proxy.ts` → `middleware.ts`로 명시적으로 롤백함 (Review Patch [CRITICAL]).
`web/src/middleware.ts`를 **절대 `proxy.ts`로 이름 변경하지 말 것**. 현재 구현이 정상 동작 중.

### 현재 존재하는 파일 (수정하지 않음)

```
web/src/
├── app/
│   ├── layout.tsx          # lang="ko" 이미 설정됨 — 수정 없음
│   ├── page.tsx            # /home 리디렉션 — 수정 없음  
│   ├── globals.css         # 디자인 토큰, .screen-container 클래스 — 수정 없음
│   ├── (auth)/
│   │   ├── layout.tsx      # auth 레이아웃 — 수정 없음
│   │   ├── signin/page.tsx
│   │   └── signup/page.tsx
│   └── favicon.ico
├── lib/
│   ├── supabase.ts         # 브라우저 클라이언트 — 수정 없음
│   └── supabase-server.ts  # 서버사이드 클라이언트 — 수정 없음
└── middleware.ts            # Auth guard — 수정 없음
```

### (app) 라우트 그룹 구조

`(app)` 폴더는 URL에 영향을 주지 않음. 아래 구조:

```
web/src/app/
├── (auth)/                     # 인증 화면 그룹 (기존)
│   ├── layout.tsx
│   ├── signin/page.tsx
│   └── signup/page.tsx
└── (app)/                      # ← NEW: 인증된 앱 화면 그룹
    ├── layout.tsx              # ← NEW: 앱 레이아웃 (BottomNav 포함)
    ├── home/
    │   └── page.tsx           # ← NEW: URL: /home
    ├── queue/
    │   └── page.tsx           # ← NEW: URL: /queue
    ├── history/
    │   └── page.tsx           # ← NEW: URL: /history
    └── profile/
        └── page.tsx           # ← NEW: URL: /profile

web/src/components/
└── layout/
    └── bottom-nav.tsx          # ← NEW: Client Component (usePathname)
```

### `(app)/layout.tsx` 구현 가이드

```typescript
// web/src/app/(app)/layout.tsx
import { redirect } from "next/navigation";
import { createServerSupabaseClient } from "@/lib/supabase-server";
import { BottomNav } from "@/components/layout/bottom-nav";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // 미들웨어가 이미 보호하지만, 서버사이드 2차 검증 (직접 URL 접근 방어)
  const supabase = await createServerSupabaseClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/signin");

  return (
    <div className="flex flex-col min-h-svh">
      {/* 콘텐츠 영역: 데스크탑 480px centering은 각 페이지의 .screen-container 클래스로 처리 */}
      <main className="flex-1 pb-16">
        {children}
      </main>
      <BottomNav />
    </div>
  );
}
```

**주의:** `pb-16`(64px)은 BottomNav 높이만큼 main 콘텐츠 하단 패딩. BottomNav가 `position: fixed; bottom: 0`이라 콘텐츠가 가려지지 않도록.

### `bottom-nav.tsx` 구현 가이드

```typescript
// web/src/components/layout/bottom-nav.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  { href: "/home",    label: "홈",      icon: "🏠" },
  { href: "/queue",   label: "큐",      icon: "📋" },
  { href: "/history", label: "히스토리", icon: "🕐" },
  { href: "/profile", label: "프로필",  icon: "👤" },
] as const;

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="주요 내비게이션"
      style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        backgroundColor: "var(--surface-base)",
        borderTop: "1px solid var(--border-subtle)",
        zIndex: 50,
      }}
    >
      <div className="screen-container">
        <ul
          role="list"
          style={{
            display: "flex",
            justifyContent: "space-around",
            padding: "8px 0",
            margin: 0,
            listStyle: "none",
          }}
        >
          {tabs.map((tab) => {
            const isActive = pathname === tab.href || pathname.startsWith(tab.href + "/");
            return (
              <li key={tab.href}>
                <Link
                  href={tab.href}
                  aria-current={isActive ? "page" : undefined}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "2px",
                    padding: "4px 12px",
                    minWidth: "44px",      // UX-DR13: 44px 최소 탭 타겟
                    minHeight: "44px",
                    color: isActive ? "var(--accent-primary)" : "var(--text-secondary)",
                    textDecoration: "none",
                    fontSize: "10px",
                    fontWeight: isActive ? 700 : 500,
                  }}
                >
                  <span aria-hidden="true" style={{ fontSize: "20px" }}>{tab.icon}</span>
                  <span>{tab.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </nav>
  );
}
```

**⚠️ 아이콘:** 이 스토리에서는 이모지 placeholder 사용 (SVG 아이콘은 후속 스토리에서 교체).
**⚠️ `min-height: 44px`:** UX-DR13 WCAG 2.2 AA 탭 타겟 요건.
**⚠️ `screen-container` 클래스:** `globals.css`에 이미 정의됨 — 데스크탑(≥768px)에서 max-width 480px, margin: 0 auto.

### Placeholder 페이지 구현 가이드

각 페이지는 최소한의 placeholder. `<span lang="en">` 패턴을 홈 페이지에서 데모:

```typescript
// web/src/app/(app)/home/page.tsx
export default function HomePage() {
  return (
    <div className="screen-container" style={{ paddingTop: "24px" }}>
      <h1 className="text-section-title">홈</h1>
      <p className="text-body" style={{ color: "var(--text-secondary)", marginTop: "8px" }}>
        <span lang="en">Daily Brief</span>가 여기에 표시됩니다.{" "}
        — Story 2.4에서 구현 예정
      </p>
    </div>
  );
}
```

나머지 페이지도 동일 패턴, 한국어 섹션 제목 + 간단한 placeholder 텍스트.

### `<span lang="en">` 패턴 컨벤션 (UX-DR14)

이 스토리에서 확립하는 개발 컨벤션:

```tsx
// 올바른 패턴
<span lang="en">Daily Brief</span>
<span lang="en">Signal</span>
<span lang="en">Queue</span>
<span lang="en">Learn Now</span>
<span lang="en">Review</span>
<span lang="en">Memory</span>
```

**대상 영어 고유명사 전체 목록:** Review, Signal, Memory, Learn Now, Queue, Ignore, Daily Brief, Learning Path, Outcome, NEW, Applied, Completed, Dropped

이 패턴은 스크린리더가 해당 단어를 영어 발음으로 읽도록 돕는다 (한국어 화자 UX 개선).

### 데스크탑 480px 레이아웃

`globals.css`에 이미 정의된 `.screen-container` 클래스를 사용:

```css
/* 이미 구현됨 — 재구현 불필요 */
.screen-container { width: 100%; padding: 0 20px; }
@media (min-width: 768px) {
  .screen-container { max-width: 480px; margin: 0 auto; padding: 0; }
}
```

각 페이지에서 `<div className="screen-container">` 래퍼 사용. BottomNav도 `screen-container`로 감싸 탭 배치가 데스크탑에서 중앙 정렬됨.

### 아키텍처 준수 사항

| 규칙 | 근거 |
|------|------|
| 클라이언트 직접 Supabase 읽기 (anon key + RLS) | AD-3 |
| 이 스토리에서 FastAPI 호출 없음 (순수 내비게이션) | AD-3 (쓰기 없음) |
| lang="ko" 루트 + 영어 고유명사 span 마킹 | NFR-1, UX-DR14 |
| 모바일 우선 + 데스크탑 max-width 480px | NFR-4, UX-DR9 |
| 44px 최소 탭 타겟 | UX-DR13 (WCAG 2.2 AA) |
| middleware.ts 파일명 유지 (proxy.ts로 변경 금지) | Story 1.2 Review Patch [CRITICAL] |

### 이전 스토리에서 인계받은 Deferred 항목

Story 1.2의 아래 Deferred 항목이 **이 스토리(1.3)에서 해결**됨:

- **GoRouter 동기 session 읽기 cold start 깜빡임** (`mobile/lib/core/router/app_router.dart`) — 이 스토리는 Flutter를 건드리지 않음. Flutter 측 수정은 **Story 1.4**에서 `StatefulShellRoute.indexedStack` 교체 시 처리.

이 스토리는 Next.js 웹 앱만 담당. Flutter는 변경 없음.

### 테스트 전략

이 스토리에서 중요한 테스트:

1. **라우팅 테스트 (수동):**
   - 비인증 상태에서 `/home` 직접 접근 → `/signin` 리디렉션 확인
   - 각 탭 클릭 시 URL 변경 확인
   - 데스크탑(768px 이상) 브라우저에서 max-width 480px 확인

2. **언어 마킹 (수동):**
   - 브라우저 DevTools → Elements에서 `<span lang="en">` 확인

3. **접근성 (수동):**
   - 각 탭 `aria-current="page"` 동적 업데이트 확인
   - `nav aria-label="주요 내비게이션"` 확인
   - 키보드 Tab 키로 내비게이션 이동 가능 확인

Note: 컴포넌트 유닛 테스트는 이 placeholder 스토리의 필수 요건이 아님. Story 2.4(홈 화면 실제 구현) 시 컴포넌트 테스트 추가 예정.

### 프로젝트 구조 참고 (이 스토리 완료 후)

```
web/src/
├── app/
│   ├── (auth)/             # 기존 (변경 없음)
│   │   ├── layout.tsx
│   │   ├── signin/page.tsx
│   │   └── signup/page.tsx
│   ├── (app)/              # ← 신규: 인증된 앱 레이아웃 그룹
│   │   ├── layout.tsx      # 앱 레이아웃 (BottomNav 포함)
│   │   ├── home/page.tsx
│   │   ├── queue/page.tsx
│   │   ├── history/page.tsx
│   │   └── profile/page.tsx
│   ├── layout.tsx          # 루트 레이아웃 (변경 없음)
│   ├── page.tsx            # / → /home 리디렉션 (변경 없음)
│   ├── globals.css
│   └── favicon.ico
├── components/
│   └── layout/
│       └── bottom-nav.tsx  # ← 신규: Client Component
├── lib/
│   ├── supabase.ts
│   └── supabase-server.ts
└── middleware.ts
```

### References

- 에픽 정의: `_bmad-output/planning-artifacts/epics.md` — Story 1.3 (line 261–283)
- 디자인 토큰: `web/src/app/globals.css` — CSS 커스텀 프로퍼티 전체
- UX 요구사항: DESIGN.md → UX-DR9 (4탭 내비게이션), UX-DR13 (접근성), UX-DR14 (언어 마킹)
- 아키텍처: ARCHITECTURE-SPINE.md → AD-3 (데이터 접근), AD-13 (API 계약), NFR-1, NFR-4
- 이전 스토리: `_bmad-output/implementation-artifacts/1-2-user-authentication.md` — middleware.ts, supabase-server.ts 패턴
- Deferred: `_bmad-output/implementation-artifacts/deferred-work.md` — GoRouter cold start (Story 1.4 예정)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

없음 — 구현 중 이슈 없음. TypeScript `--noEmit` 통과.

### Completion Notes List

- `(app)` 라우트 그룹 레이아웃 생성: 서버 컴포넌트에서 `createServerSupabaseClient`로 인증 2차 검증 후 `/signin` 리디렉션, `pb-16`으로 BottomNav(fixed) 가림 방지
- `BottomNav` Client Component: `usePathname`으로 active 탭 감지, 4개 탭 링크, 디자인 토큰 적용, WCAG 2.2 AA 44px 최소 탭 타겟, `aria-current="page"` 동적 설정
- 4개 placeholder 페이지 생성: 각 페이지 `screen-container` 클래스로 데스크탑 480px 중앙 정렬
- `<span lang="en">` 패턴: home·queue·history 페이지에서 컨벤션 데모 (Daily Brief, Queue, Memory)
- `lang="ko"` 루트 레이아웃 확인: 이미 설정됨, 수정 불필요
- `middleware.ts` 파일명 유지: proxy.ts 변경 없음

### File List

- `web/src/app/(app)/layout.tsx` (신규)
- `web/src/app/(app)/home/page.tsx` (신규)
- `web/src/app/(app)/queue/page.tsx` (신규)
- `web/src/app/(app)/history/page.tsx` (신규)
- `web/src/app/(app)/profile/page.tsx` (신규)
- `web/src/components/layout/bottom-nav.tsx` (신규)

## Change Log

- 2026-07-24: Story 1.3 구현 완료 — (app) 라우트 그룹 레이아웃, BottomNav Client Component, 4개 placeholder 페이지 생성, `<span lang="en">` 컨벤션 확립
