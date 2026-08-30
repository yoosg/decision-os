# 입문자 카드 웹 공용화 + 폴리시 (3a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 입문자 프로젝트 카드 웹 화면의 중복을 공용화(먼저)하고, 승인된 방향 C(모노크롬)로 시각을 폴리시(이어서)한다.

**Architecture:** 파트 1은 동작 무변경 리팩터(공용 헬퍼/타입/컴포넌트 추출), 파트 2는 `ProjectCardMeta`/`ProjectCardBlocks`/`ProjectCardContent`의 인라인 스타일 restyle. 두 대상 화면(인터랙티브 카드 = 홈/큐, 읽기전용 카드 = 히스토리 체인)이 같은 컴포넌트를 공유하므로 폴리시는 자동 반영된다.

**Tech Stack:** Next.js(커스텀 빌드, `web/AGENTS.md` 주의), React, TypeScript, Supabase JS. **웹 전용** — 백엔드/스키마/프롬프트 무변경.

## Global Constraints

- **테스트 러너 없음.** 이 저장소 웹은 `next dev/build/start` + typescript만 있고 vitest/jest/playwright 설정이 없다(메모리 `web-test-runner-vitest`). 기존 `*.test.tsx`는 **실행 불가 placeholder** — 새 테스트를 그 형식으로 추가하지 말 것. **검증 = `cd web && npx tsc --noEmit`(타입) + Playwright MCP 라이브 확인.**
- **모노크롬만.** 신규 색 도입 금지. `--accent-primary:#0D0D0D`, `--surface-card/raised`, `--text-secondary` 등 기존 CSS 변수만.
- **인라인 스타일 관례 유지.** 기존 파일이 `className="text-body"` 등 유틸 클래스 + 인라인 `style` 객체를 쓰므로 그 패턴을 따른다(새 CSS 모듈 도입 금지).
- **동작 무변경(파트 1).** 진도 저장(`useCardProgress`) 계약, `progress` 옵셔널 prop, 로컬 폴백, `aria-pressed`/`aria-live`/터치 타깃(≥44px)/label 연결을 보존.
- **커밋:** 태스크마다 1커밋. 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **라이브 검증 환경(메모리 `local-run-setup`):** 백엔드 `:8000` + 웹 `:3000`. `project_card` 리뷰가 있는 시그널이 최소 1개 필요(카드 모드 토글 ON 후 생성, 또는 기존 시드 카드). 로그인: `test-history@decisionos.dev` / `Test1234!`.
- **브랜치:** `feat/card-web-commonization-polish`(main에서 분기).

---

## File Structure

**신규**
- `web/src/lib/api.ts` — `API_BASE_URL` 상수 + `getAccessToken()` 헬퍼 (plain `.ts`, `"use client"` 아님)
- `web/src/components/home/review/review-types.ts` — `ReviewType` 유니온 + `isProjectCard` 가드
- `web/src/components/ui/back-link.tsx` — 공용 뒤로가기 링크

**수정(파트 1 공용화)**
- FASTAPI_URL/토큰 11곳: `home/review/[signalId]/{outcome,chat,learning-path}/page.tsx`, `onboarding/page.tsx`, `components/home/review/{use-card-progress.ts,review-page-content.tsx,context-sticky-bar.tsx}`, `components/home/daily-brief-content.tsx`, `components/profile/profile-content.tsx`, `components/queue/queue-content.tsx`, `lib/engagement.ts`
- `components/history/chain-detail-content.tsx` — 판별 유니온, 캐스트 제거, BackLink
- `components/home/review/review-page-content.tsx` — `ReviewType` 타입, API 헬퍼
- `app/(app)/history/chain/[signalId]/page.tsx` — 판별 유니온 데이터 구성
- `components/home/review/research-review-content.tsx` — BackLink
- `components/home/review/project-card-blocks.tsx` — `CheckableList` 추출 (+ 파트 2 폴리시)

**수정(파트 2 폴리시)**
- `components/home/review/project-card-blocks.tsx` — 뱃지 도트/히어로/정보블록/프롬프트/인터랙티브/여백
- `components/home/review/project-card-content.tsx` — 헤더/결과버튼/BackLink

---

# 파트 1 — 공용화 (먼저, 동작 무변경)

## Task 1: API 베이스 URL / 액세스 토큰 헬퍼 (11곳 치환)

**Files:**
- Create: `web/src/lib/api.ts`
- Modify: 위 "FASTAPI_URL/토큰 11곳" 목록 전부

**Interfaces:**
- Produces: `API_BASE_URL: string`, `getAccessToken(): Promise<string | null>`

- [ ] **Step 1: `api.ts` 작성**

```ts
// web/src/lib/api.ts
import { createClient } from "@/lib/supabase";

// NEXT_PUBLIC_* 는 빌드타임 인라인 → 순수 상수라 RSC/클라이언트 어디서든 안전하게 import 가능
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://localhost:8000";

// 브라우저 supabase 세션에서 액세스 토큰 추출(클라이언트 컴포넌트 전용)
export async function getAccessToken(): Promise<string | null> {
  const {
    data: { session },
  } = await createClient().auth.getSession();
  return session?.access_token ?? null;
}
```

- [ ] **Step 2: 11개 파일에서 로컬 `FASTAPI_URL` 정의를 제거하고 `API_BASE_URL` import로 치환**

각 파일에서 다음 형태의 로컬 정의/인라인을 삭제:
```ts
const FASTAPI_URL = process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://localhost:8000";
// 또는 인라인: process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://localhost:8000"
```
상단에 `import { API_BASE_URL } from "@/lib/api";` 추가하고, 사용처의 `FASTAPI_URL`/인라인을 `API_BASE_URL`로 교체. (이미 `fastapiUrl` 지역변수를 쓰던 곳 — review-page-content, daily-brief-content, context-sticky-bar, queue-content, engagement.ts — 은 그 지역변수 선언을 지우고 사용처를 `API_BASE_URL`로 바꾼다.)

- [ ] **Step 3: 토큰 취득 인라인을 `getAccessToken()`으로 치환**

다음 패턴을 쓰는 곳(review-page-content의 `triggerAPI`, use-card-progress의 `getToken`, daily-brief-content, context-sticky-bar, profile-content, queue-content, onboarding, outcome/chat/learning-path page, engagement.ts 중 해당)을:
```ts
const { data: { session } } = await createClient().auth.getSession();
const token = session?.access_token;
```
로 바꾼다:
```ts
import { getAccessToken } from "@/lib/api";
// ...
const token = await getAccessToken();
```
`use-card-progress.ts`의 로컬 `getToken` 함수(21–24행)는 삭제하고 호출부 2곳을 `getAccessToken()`으로 교체. `createClient` import가 그 파일에서 더 이상 안 쓰이면 제거.

- [ ] **Step 4: 타입체크**

Run: `cd web && npx tsc --noEmit`
Expected: PASS (에러 0). 남은 `NEXT_PUBLIC_FASTAPI_URL` 참조가 없어야 함 — 확인: `grep -rn "NEXT_PUBLIC_FASTAPI_URL" src | grep -v "lib/api.ts"` → 결과 없음.

- [ ] **Step 5: 커밋**

```bash
git add web/src/lib/api.ts web/src
git commit -m "refactor(web): API_BASE_URL·getAccessToken 헬퍼로 11곳 공용화

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `ReviewType` 유니온 + 판별 유니온으로 캐스트 제거

**Files:**
- Create: `web/src/components/home/review/review-types.ts`
- Modify: `web/src/components/history/chain-detail-content.tsx`, `web/src/app/(app)/history/chain/[signalId]/page.tsx`, `web/src/components/home/review/review-page-content.tsx`

**Interfaces:**
- Produces: `type ReviewType = "research" | "project_card"`, `isProjectCard(t): t is "project_card"`

- [ ] **Step 1: `review-types.ts` 작성**

```ts
// web/src/components/home/review/review-types.ts
export type ReviewType = "research" | "project_card";

export function isProjectCard(
  t: ReviewType | string | null,
): t is "project_card" {
  return t === "project_card";
}
```

- [ ] **Step 2: `chain-detail-content.tsx` — `ChainDetailData.review`를 판별 유니온으로**

11행 `review: { reviewType: string | null; payload: ReviewPayload | ProjectCardPayload } | null;` 를 아래로 교체하고 상단에 `import type { ReviewType } from "@/components/home/review/review-types";` 추가(사용 안 하면 생략 가능):

```ts
  review:
    | { reviewType: "project_card"; payload: ProjectCardPayload }
    | { reviewType: "research"; payload: ReviewPayload }
    | null;
```

REVIEW 노드 분기(133–140행)에서 캐스트 제거 — 판별 유니온이 좁혀줌:
```tsx
{review.reviewType === "project_card" ? (
  <>
    <ProjectCardMeta payload={review.payload} />
    <ProjectCardBlocks payload={review.payload} />
  </>
) : (
  <ReviewSections payload={review.payload} />
)}
```

- [ ] **Step 3: `chain/[signalId]/page.tsx` — 데이터 경계에서 한 번 좁혀 구성**

77–86행 영역을 아래로 교체(원시 DB 문자열을 신뢰 경계에서 1회 캐스트, 렌더 컴포넌트는 캐스트-프리):
```ts
  const payload = reviewRow?.result?.payload as
    | ReviewPayload
    | ProjectCardPayload
    | undefined;
  const reviewType =
    reviewRow?.result?.review_type === "project_card" ? "project_card" : "research";
```
그리고 `review` 필드:
```ts
    review: payload
      ? ({ reviewType, payload } as ChainDetailData["review"])
      : null,
```

- [ ] **Step 4: `review-page-content.tsx` — `string | null` → `ReviewType | null`**

상단에 `import type { ReviewType } from "./review-types";` 추가. 14행 `reviewType?: string | null` 과 24행 `reviewType?: string | null` 을 `reviewType?: ReviewType | null` 로 교체. 96행 실시간 갱신 `(data?.result?.review_type as string | null | undefined) ?? null` 을 `((data?.result?.review_type as ReviewType | undefined) ?? null)` 로. 186행 분기 `uiState.reviewType === "project_card"` 는 그대로 동작(옵션: `isProjectCard(uiState.reviewType)` 로 교체 가능).

- [ ] **Step 5: 타입체크**

Run: `cd web && npx tsc --noEmit`
Expected: PASS. `chain-detail-content.tsx`에 `as ProjectCardPayload`/`as ReviewPayload` 캐스트가 없어야 함 — 확인: `grep -n "as ProjectCardPayload\|as ReviewPayload" src/components/history/chain-detail-content.tsx` → 결과 없음.

- [ ] **Step 6: 커밋**

```bash
git add web/src
git commit -m "refactor(web): ReviewType 판별 유니온 도입, 카드 렌더 캐스트 제거

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `BackLink` 공용 컴포넌트

**Files:**
- Create: `web/src/components/ui/back-link.tsx`
- Modify: `web/src/components/home/review/project-card-content.tsx`, `web/src/components/history/chain-detail-content.tsx`, `web/src/components/home/review/research-review-content.tsx`

**Interfaces:**
- Consumes: —
- Produces: `<BackLink href={string}>{label}</BackLink>`

- [ ] **Step 1: `back-link.tsx` 작성**

```tsx
// web/src/components/ui/back-link.tsx
import Link from "next/link";
import type { ReactNode } from "react";

export function BackLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="text-label"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "4px",
        color: "var(--text-secondary)",
        marginBottom: "20px",
      }}
    >
      <svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path
          d="M10 4L6 8l4 4"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {children}
    </Link>
  );
}
```

- [ ] **Step 2: 3곳 교체**

- `project-card-content.tsx` 38–48행 `<Link ...>홈으로</Link>` 블록 → `<BackLink href="/home">홈으로</BackLink>` (상단 `import { BackLink } from "@/components/ui/back-link";`; `Link` 미사용 시 import 제거)
- `chain-detail-content.tsx` 102–117행 `<Link href="/history" ...>히스토리로</Link>` → `<BackLink href="/history">히스토리로</BackLink>` (이 파일은 `Link`를 Decision 노드 등에서 계속 쓰므로 import 유지)
- `research-review-content.tsx` 21–48행 `<Link href="/home" ...>홈으로</Link>` → `<BackLink href="/home">홈으로</BackLink>` (이 파일은 `Link`를 하단 chat 링크에서 계속 씀 → import 유지)

- [ ] **Step 3: 타입체크**

Run: `cd web && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 4: 커밋**

```bash
git add web/src
git commit -m "refactor(web): 뒤로가기 링크를 공용 BackLink로 추출(3곳)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: `CheckableList<T>` 추출 + 파트 1 라이브 스모크

**Files:**
- Modify: `web/src/components/home/review/project-card-blocks.tsx`

**Interfaces:**
- Produces: 파일 내부 `CheckableList<T>` (export 불필요 — 내부 사용)

- [ ] **Step 1: `CheckableList<T>` 추가 + `MilestoneList`/`SuccessChecklist`를 이 위에 재작성**

`project-card-blocks.tsx`의 `MilestoneList`(86–122행)와 `SuccessChecklist`(124–150행)를 아래로 교체:

```tsx
function CheckableList<T>({
  items,
  checked,
  onToggle,
  renderLabel,
  header,
}: {
  items: T[];
  checked: Set<number>;
  onToggle: (i: number) => void;
  renderLabel: (item: T) => React.ReactNode;
  header?: React.ReactNode;
}) {
  return (
    <div>
      {header}
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {items.map((item, i) => (
          <li key={i} style={{ marginBottom: "12px" }}>
            <label style={{ display: "flex", gap: "8px", alignItems: "flex-start", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={checked.has(i)}
                onChange={() => onToggle(i)}
                style={{ marginTop: "3px" }}
              />
              <span>{renderLabel(item)}</span>
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
}

function MilestoneList({
  milestones,
  checked,
  onToggle,
}: {
  milestones: ProjectCardPayload["milestones"];
  checked: Set<number>;
  onToggle: (i: number) => void;
}) {
  return (
    <CheckableList
      items={milestones}
      checked={checked}
      onToggle={onToggle}
      header={
        <p className="text-label" style={{ color: "var(--text-secondary)", marginBottom: "8px" }}>
          {checked.size}/{milestones.length}
        </p>
      }
      renderLabel={(m) => (
        <>
          <span className="text-body" style={{ display: "block" }}>{m.action}</span>
          <span className="text-body" style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
            끝나면: {m.done_signal}
          </span>
        </>
      )}
    />
  );
}

function SuccessChecklist({
  items,
  checked,
  onToggle,
}: {
  items: string[];
  checked: Set<number>;
  onToggle: (i: number) => void;
}) {
  return (
    <CheckableList
      items={items}
      checked={checked}
      onToggle={onToggle}
      renderLabel={(it) => <span className="text-body">{it}</span>}
    />
  );
}
```

주의: `SuccessChecklist`의 기존 `<li>` 마진은 8px였으나 `CheckableList`는 12px로 통일된다(무해한 시각 차이 — 파트 2에서 어차피 인터랙티브 블록을 재작업). `ProjectCardBlocks`의 `MilestoneList`/`SuccessChecklist` 호출부(208–212행, 229–233행)는 prop 시그니처가 동일하므로 무변경.

- [ ] **Step 2: 타입체크**

Run: `cd web && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 3: 커밋**

```bash
git add web/src
git commit -m "refactor(web): 체크박스 리스트를 공용 CheckableList로 추출

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 4: 파트 1 라이브 스모크(Playwright MCP)**

웹(:3000)+백엔드(:8000) 기동, `test-history@decisionos.dev`/`Test1234!` 로그인. 다음을 브라우저로 확인(동작 무변경 회귀 체크):
  1. 인터랙티브 카드(홈): 렌더 · 예시 프롬프트 복사 · 마일스톤/체크리스트 토글 → 새로고침 후 상태 복원(진도 저장 회귀 없음).
  2. 체인 상세(히스토리): 카드형/리서치형 둘 다 정상 렌더(캐스트 제거 회귀 없음).
  3. 온보딩·프로필·큐·데일리브리프 happy-path(API_BASE_URL/getAccessToken 치환 회귀 없음).
Expected: 모두 기존과 동일. 이상 시 해당 태스크로 되돌아가 수정.

---

# 파트 2 — 폴리시 (이어서, 방향 C · 모노크롬)

> 승인 목업: `.superpowers/brainstorm/*/content/fullcard.html`(after). 각 태스크 검증은 `npx tsc --noEmit` + (Task 10에서) 라이브 before/after.

## Task 5: 난이도 뱃지 도트 + 헤더 압축 (`ProjectCardMeta`)

**Files:**
- Modify: `web/src/components/home/review/project-card-blocks.tsx`

- [ ] **Step 1: 난이도 도트 상수 추가**

`CARD_DIFFICULTY_LABEL`(20–24행) 아래에 추가:
```ts
export const CARD_DIFFICULTY_DOTS: Record<ProjectCardPayload["difficulty"], string> = {
  first_step: "●○○",
  basic: "●●○",
  challenge: "●●●",
};
```

- [ ] **Step 2: `ProjectCardMeta` 재작성(도트 뱃지 + 시간·스킬 한 줄)**

26–43행 `ProjectCardMeta`를 교체:
```tsx
export function ProjectCardMeta({ payload }: { payload: ProjectCardPayload }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center", marginBottom: "20px" }}>
      <span
        className="text-label"
        style={{ display: "inline-flex", alignItems: "center", gap: "4px", background: "var(--surface-card, #F2F2F2)", borderRadius: "9999px", padding: "4px 12px" }}
      >
        {CARD_DIFFICULTY_LABEL[payload.difficulty]}
        <span aria-hidden="true" style={{ letterSpacing: "1px", fontSize: "11px" }}>
          {CARD_DIFFICULTY_DOTS[payload.difficulty]}
        </span>
      </span>
      <span className="text-label" style={{ color: "var(--text-secondary)" }}>
        ⏱ {payload.estimated_minutes}분 · 🎓 {payload.skill_label}
      </span>
    </div>
  );
}
```

- [ ] **Step 2b: 타입체크 → 커밋**

Run: `cd web && npx tsc --noEmit` → PASS
```bash
git add web/src
git commit -m "feat(cards): 난이도 도트 뱃지 + 헤더 한 줄 압축

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 6: 완성물 히어로 블록 (①)

**Files:**
- Modify: `web/src/components/home/review/project-card-blocks.tsx`

- [ ] **Step 1: ① 섹션(171–177행)을 검정 히어로로 교체**

```tsx
{/* ① 완성하면 이게 나와 — 히어로 */}
<section
  style={{
    marginBottom: "20px",
    background: "var(--accent-primary, #0D0D0D)",
    color: "#fff",
    borderRadius: "14px",
    padding: "16px",
  }}
>
  <p className="text-label" style={{ opacity: 0.65, marginBottom: "6px" }}>📦 완성하면 이게 나와</p>
  <p className="text-body-large" style={{ marginBottom: "6px" }}>{payload.deliverable}</p>
  <p className="text-body" style={{ opacity: 0.8 }}>✓ {payload.success_preview}</p>
</section>
```

- [ ] **Step 2: 타입체크 → 커밋**

Run: `cd web && npx tsc --noEmit` → PASS
```bash
git add web/src
git commit -m "feat(cards): 완성물 블록을 히어로(검정 박스)로 강조

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 7: 정보 블록 담백화 (② 준비물, ⑤ 막히면)

**Files:**
- Modify: `web/src/components/home/review/project-card-blocks.tsx`

- [ ] **Step 1: ② 준비물(179–183행) 본문을 secondary로**

`<p className="text-body">{payload.prerequisites}</p>` → `<p className="text-body" style={{ color: "var(--text-secondary)" }}>{payload.prerequisites}</p>`

- [ ] **Step 2: ⑤ 막히면(215–224행) 처방에 `→` 프리픽스**

troubleshooting map 내부 fix 줄:
```tsx
<p className="text-body" style={{ color: "var(--text-secondary)" }}>→ {t.fix}</p>
```

- [ ] **Step 3: 타입체크 → 커밋**

Run: `cd web && npx tsc --noEmit` → PASS
```bash
git add web/src
git commit -m "feat(cards): 정보 블록 담백화(준비물·막히면)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 8: 프롬프트 복사 피드백 (③)

**Files:**
- Modify: `web/src/components/home/review/project-card-blocks.tsx`

- [ ] **Step 1: `CopyPromptButton`(57–84행) done 상태를 검정 fill로**

버튼 라벨/스타일 교체:
```tsx
  return (
    <button
      type="button"
      onClick={handleCopy}
      className="text-label"
      style={{
        border: copied ? "1px solid var(--accent-primary, #0D0D0D)" : "1px solid var(--border-subtle, #E5E5E5)",
        borderRadius: "9999px",
        background: copied ? "var(--accent-primary, #0D0D0D)" : "transparent",
        color: copied ? "#fff" : "inherit",
        padding: "4px 12px",
        cursor: "pointer",
      }}
    >
      {copied ? "✓ 복사됨" : "📋 복사"}
    </button>
  );
```
(타이머 로직 무변경 — 2초 후 원복)

- [ ] **Step 2: 타입체크 → 커밋**

Run: `cd web && npx tsc --noEmit` → PASS
```bash
git add web/src
git commit -m "feat(cards): 프롬프트 복사 피드백(✓ 복사됨 검정 fill)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 9: 인터랙티브 블록 좌측 액센트 (④ 진행, ⑥ 확인)

**Files:**
- Modify: `web/src/components/home/review/project-card-blocks.tsx`

- [ ] **Step 1: 인터랙티브 래퍼 스타일 상수 추가(파일 상단, 컴포넌트 밖)**

```ts
const INTERACTIVE_BLOCK_STYLE: React.CSSProperties = {
  background: "var(--surface-card, #F7F7F7)",
  borderLeft: "3px solid var(--accent-primary, #0D0D0D)",
  borderRadius: "0 12px 12px 0",
  padding: "14px",
  marginBottom: "20px",
};
```

- [ ] **Step 2: ④ 진행 과정 섹션(205–213행)을 래퍼로 감싸고 헤더+카운트 정렬**

```tsx
{/* ④ 진행 과정 */}
<section style={INTERACTIVE_BLOCK_STYLE}>
  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
    <h2 className="text-section-title" style={{ margin: 0 }}>🗺️ 진행 과정</h2>
  </div>
  <MilestoneList
    milestones={payload.milestones ?? []}
    checked={milestoneChecked}
    onToggle={milestoneToggle}
  />
</section>
```
(카운트는 `MilestoneList` header가 이미 `0/2`를 렌더하므로 유지)

- [ ] **Step 3: ⑥ 다 됐는지(226–234행)를 동일 래퍼로**

```tsx
{/* ⑥ 다 됐는지 확인 */}
<section style={INTERACTIVE_BLOCK_STYLE}>
  <h2 className="text-section-title" style={{ marginBottom: "10px" }}>✅ 다 됐는지 확인</h2>
  <SuccessChecklist
    items={payload.success_checklist ?? []}
    checked={checklistChecked}
    onToggle={checklistToggle}
  />
</section>
```

- [ ] **Step 4: 마일스톤 보조문구 `끝나면: ` → `끝나면 · `**

Task 4에서 만든 `MilestoneList`의 `renderLabel` 내 `끝나면: {m.done_signal}` → `끝나면 · {m.done_signal}`.

- [ ] **Step 5: 타입체크 → 커밋**

Run: `cd web && npx tsc --noEmit` → PASS
```bash
git add web/src
git commit -m "feat(cards): 인터랙티브 블록 좌측 액센트(진행·확인)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 10: 여백 리듬 + 결과 버튼 + 라이브 before/after 검증

**Files:**
- Modify: `web/src/components/home/review/project-card-blocks.tsx`, `web/src/components/home/review/project-card-content.tsx`

- [ ] **Step 1: 히어로 전/인터랙티브 그룹 앞에 얇은 구분선**

`ProjectCardBlocks` return에서 ③ 프롬프트 섹션과 ④ 진행 섹션 사이, ⑤ 막히면과 ⑥ 확인 사이에 구분선 삽입:
```tsx
<div style={{ height: "1px", background: "#F0F0F0", margin: "0 0 20px" }} />
```

- [ ] **Step 2: 결과 버튼 섹션에도 상단 구분선(`project-card-content.tsx` ⑦ 앞)**

56행 `<section style={{ marginTop: "8px" }}>` 앞에 동일 구분선 추가(marginTop은 0으로 조정):
```tsx
<div style={{ height: "1px", background: "#F0F0F0", margin: "0 0 20px" }} />
<section>
```
(결과 버튼의 active=검정 테두리+회색 fill 스타일은 이미 모노크롬 — 무변경)

- [ ] **Step 3: 타입체크**

Run: `cd web && npx tsc --noEmit` → PASS

- [ ] **Step 4: 커밋**

```bash
git add web/src
git commit -m "feat(cards): 블록 구분선으로 여백 리듬 정리

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 5: 라이브 before/after 검증(Playwright MCP)**

웹(:3000)+백엔드(:8000), 로그인 후 `project_card` 시그널 열기:
  1. 인터랙티브 카드(홈): 히어로/도트 뱃지/인터랙티브 액센트/`✓ 복사됨`/구분선 리듬 확인. 스크린샷.
  2. 체크박스 토글 → 새로고침 복원(진도 저장 회귀 없음).
  3. 체인 상세(읽기전용): 동일 폴리시가 회귀 없이 렌더(progress 없이). 스크린샷.
  4. before(git stash 또는 이전 스크린샷)와 대비해 목업 방향과 일치하는지 확인.
Expected: 목업 after와 일치, 저장/읽기전용 동작 무변경.

---

## Self-Review 결과(작성자 체크)

- **스펙 커버리지:** 1.1→T1, 1.2→T2, 1.3→T3, 1.4→T4, 1.5(토스트 유지)→작업 없음(의도), 2.1→T5, 2.2→T6, 2.3→T7, 2.4→T8, 2.5→T9, 2.6→T10. 검증(tsc+Playwright)→T4/T10. 갭 없음.
- **Placeholder:** 없음(모든 코드 스텝에 실제 코드/명령).
- **타입 일관성:** `API_BASE_URL`/`getAccessToken`(T1) · `ReviewType`/`isProjectCard`(T2) · `BackLink`(T3) · `CheckableList`/`MilestoneList`/`SuccessChecklist`(T4) · `CARD_DIFFICULTY_DOTS`/`INTERACTIVE_BLOCK_STYLE`(T5/T9) 이름이 사용처와 일치. T9는 T4가 만든 `MilestoneList.renderLabel`을 수정하므로 순서 의존(파트 1 → 파트 2 보장).
