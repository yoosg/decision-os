# 입문자 프로젝트 카드 상세화면 (웹) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 웹 리뷰 상세화면이 `review_type`에 따라 입문자 프로젝트 카드(7블록) 또는 기존 research(13섹션)를 그리도록 분기한다.

**Architecture:** 생성 파이프라인(트리거·실시간·재시도)은 그대로 공유하고, `ReviewPageContent`의 `completed` 상태에서만 payload 렌더를 분기한다. 카드 렌더는 `research-review-content` ↔ `review-sections` 2분할을 미러링한 `project-card-content` ↔ `project-card-blocks`로 구현한다.

**Tech Stack:** Next.js 16(App Router), React 19, TypeScript. 인라인 스타일 + 유틸 클래스(`text-*`) + CSS 변수. 테스트 러너 없음.

## Global Constraints

- **테스트 러너 없음**: `package.json`에 `test` 스크립트/vitest 없음. 테스트 파일은 기존 `*.test.tsx`와 동일하게 **미실행 스펙 문서**(상단 주석 + `@ts-nocheck` + jest-style API). 실제 게이트는 `npx tsc --noEmit` + Playwright 시각 확인.
- **디자인 시스템**: 인라인 스타일 + 유틸 클래스(`text-screen-title`, `text-section-title`, `text-body`, `text-label`) + CSS 변수(`--text-secondary`, `--surface-raised`, `--surface-card`, `--border-subtle`, `--accent-primary`). 새 색/토큰 도입 금지.
- **범위(화면 먼저)**: ④/⑥ 체크박스는 로컬 상태(새로고침 초기화), ⑦ 결과 버튼은 UI만(클릭 시 토스트). 진도·결과 저장 API, `example_prompt` 개인화는 비범위.
- **폴백**: `review_type`이 없는 과거 리뷰(`undefined`)는 `research`로 렌더.
- **한국어 카피**: 모든 사용자 노출 문구는 한국어, 입문자 친화 말투.
- **작업 경로**: 모든 명령은 `web/`에서 실행. tsc: `cd web && npx tsc --noEmit`.
- **비범위 알림**: history chain 상세(`chain-detail-content.tsx`)는 `ReviewSections`를 직접 쓰므로 카드 미대응 — 이번 작업에서 건드리지 않는다(카드 히스토리는 향후).

---

### Task 1: 카드 블록 컴포넌트 (`project-card-blocks.tsx`)

`ProjectCardPayload` 타입 + 난이도 라벨 맵 + ①~⑥ 블록 렌더(복사 버튼·마일스톤/성공 체크리스트 로컬 상태 포함).

**Files:**
- Create: `web/src/components/home/review/project-card-blocks.tsx`
- Test: `web/src/components/home/review/__tests__/project-card-blocks.test.tsx`

**Interfaces:**
- Produces:
  - `interface ProjectCardPayload` (아래 필드 그대로)
  - `const CARD_DIFFICULTY_LABEL: Record<ProjectCardPayload["difficulty"], string>`
  - `function ProjectCardBlocks({ payload }: { payload: ProjectCardPayload }): JSX.Element` — ①~⑥ 블록만 렌더(헤더·⑦ 제외)

- [ ] **Step 1: 스펙 문서(미실행 테스트) 작성**

Create `web/src/components/home/review/__tests__/project-card-blocks.test.tsx`:

```tsx
/**
 * project-card-blocks.test.tsx
 *
 * NOTE: 이 프로젝트에는 Jest/Vitest가 설정되어 있지 않습니다.
 * 이 파일은 테스트 스펙 문서 역할을 합니다.
 */

// @ts-nocheck — 테스트 러너 없이 타입 오류 방지
import { render, screen, fireEvent } from "@testing-library/react";
import { ProjectCardBlocks } from "../project-card-blocks";

const payload = {
  skill_label: "웹폼 만들고 데이터 저장하기",
  difficulty: "first_step",
  estimated_minutes: 30,
  deliverable: "간단한 예약 폼 웹페이지",
  success_preview: "폼에 입력하면 목록에 추가돼요",
  prerequisites: "없어요, 바로 시작!",
  how_to_start: "AI 코딩 도구를 열고 아래 프롬프트를 붙여넣으세요.",
  example_prompt: "예약 폼 만들어줘. 날짜·시간·인원 입력받고 목록에 저장해줘.",
  milestones: [
    { action: "폼 화면 만들기", done_signal: "입력칸이 보임" },
    { action: "저장 붙이기", done_signal: "목록에 추가됨" },
  ],
  troubleshooting: [{ symptom: "저장이 안 돼요", fix: "저장 코드를 추가해달라고 다시 요청하세요." }],
  success_checklist: ["폼이 보인다", "입력하면 목록에 남는다"],
};

test("①~⑥ 블록 헤더와 내용이 렌더된다", () => {
  render(<ProjectCardBlocks payload={payload} />);
  expect(screen.getByText("📦 완성하면 이게 나와")).toBeTruthy();
  expect(screen.getByText(payload.deliverable)).toBeTruthy();
  expect(screen.getByText("🧰 시작 전 준비물")).toBeTruthy();
  expect(screen.getByText("🚀 이렇게 시작해")).toBeTruthy();
  expect(screen.getByText("🗺️ 진행 과정")).toBeTruthy();
  expect(screen.getByText("🆘 막히면 이렇게")).toBeTruthy();
  expect(screen.getByText("✅ 다 됐는지 확인")).toBeTruthy();
});

test("④ 마일스톤 체크박스를 켜면 진도 카운트가 오른다", () => {
  render(<ProjectCardBlocks payload={payload} />);
  expect(screen.getByText("0/2")).toBeTruthy();
  const checkboxes = screen.getAllByRole("checkbox");
  fireEvent.click(checkboxes[0]);
  expect(screen.getByText("1/2")).toBeTruthy();
});

test("③ 복사 버튼이 example_prompt를 클립보드에 쓴다", () => {
  const writeText = jest.fn().mockResolvedValue(undefined);
  Object.assign(navigator, { clipboard: { writeText } });
  render(<ProjectCardBlocks payload={payload} />);
  fireEvent.click(screen.getByRole("button", { name: /복사/ }));
  expect(writeText).toHaveBeenCalledWith(payload.example_prompt);
});
```

- [ ] **Step 2: 컴포넌트 구현**

Create `web/src/components/home/review/project-card-blocks.tsx`:

```tsx
"use client";

import { useState } from "react";

export interface ProjectCardPayload {
  skill_label: string;
  difficulty: "first_step" | "basic" | "challenge";
  estimated_minutes: number;
  deliverable: string;
  success_preview: string;
  prerequisites: string;
  how_to_start: string;
  example_prompt: string;
  milestones: { action: string; done_signal: string }[];
  troubleshooting: { symptom: string; fix: string }[];
  success_checklist: string[];
}

export const CARD_DIFFICULTY_LABEL: Record<ProjectCardPayload["difficulty"], string> = {
  first_step: "첫걸음",
  basic: "기본",
  challenge: "도전",
};

function useCheckedSet() {
  const [checked, setChecked] = useState<Set<number>>(new Set());
  const toggle = (i: number) =>
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  return { checked, toggle };
}

function CopyPromptButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // 클립보드 미지원 환경 — 무시
    }
  };
  return (
    <button
      type="button"
      onClick={handleCopy}
      className="text-label"
      style={{
        border: "1px solid var(--border-subtle, #E5E5E5)",
        borderRadius: "9999px",
        background: "transparent",
        padding: "4px 12px",
        cursor: "pointer",
      }}
    >
      {copied ? "복사됨!" : "📋 복사"}
    </button>
  );
}

function MilestoneList({ milestones }: { milestones: ProjectCardPayload["milestones"] }) {
  const { checked, toggle } = useCheckedSet();
  return (
    <div>
      <p className="text-label" style={{ color: "var(--text-secondary)", marginBottom: "8px" }}>
        {checked.size}/{milestones.length}
      </p>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {milestones.map((m, i) => (
          <li key={i} style={{ marginBottom: "12px" }}>
            <label style={{ display: "flex", gap: "8px", alignItems: "flex-start", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={checked.has(i)}
                onChange={() => toggle(i)}
                style={{ marginTop: "3px" }}
              />
              <span>
                <span className="text-body" style={{ display: "block" }}>{m.action}</span>
                <span className="text-body" style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
                  끝나면: {m.done_signal}
                </span>
              </span>
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SuccessChecklist({ items }: { items: string[] }) {
  const { checked, toggle } = useCheckedSet();
  return (
    <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
      {items.map((it, i) => (
        <li key={i} style={{ marginBottom: "8px" }}>
          <label style={{ display: "flex", gap: "8px", alignItems: "flex-start", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={checked.has(i)}
              onChange={() => toggle(i)}
              style={{ marginTop: "3px" }}
            />
            <span className="text-body">{it}</span>
          </label>
        </li>
      ))}
    </ul>
  );
}

export function ProjectCardBlocks({ payload }: { payload: ProjectCardPayload }) {
  return (
    <>
      {/* ① 완성하면 이게 나와 */}
      <section style={{ marginBottom: "24px" }}>
        <h2 className="text-section-title" style={{ marginBottom: "8px" }}>📦 완성하면 이게 나와</h2>
        <p className="text-body">{payload.deliverable}</p>
        <p className="text-body" style={{ color: "var(--text-secondary)", marginTop: "8px" }}>
          이렇게 보이면 성공 — {payload.success_preview}
        </p>
      </section>

      {/* ② 시작 전 준비물 */}
      <section style={{ marginBottom: "24px" }}>
        <h2 className="text-section-title" style={{ marginBottom: "8px" }}>🧰 시작 전 준비물</h2>
        <p className="text-body">{payload.prerequisites}</p>
      </section>

      {/* ③ 이렇게 시작해 */}
      <section style={{ marginBottom: "24px" }}>
        <h2 className="text-section-title" style={{ marginBottom: "8px" }}>🚀 이렇게 시작해</h2>
        <p className="text-body" style={{ marginBottom: "12px" }}>{payload.how_to_start}</p>
        <div
          style={{
            background: "var(--surface-raised, #F9F9F9)",
            border: "1px solid var(--border-subtle, #E5E5E5)",
            borderRadius: "12px",
            padding: "12px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span className="text-label" style={{ color: "var(--text-secondary)" }}>예시 프롬프트</span>
            <CopyPromptButton text={payload.example_prompt} />
          </div>
          <p className="text-body" style={{ whiteSpace: "pre-wrap" }}>{payload.example_prompt}</p>
        </div>
      </section>

      {/* ④ 진행 과정 */}
      <section style={{ marginBottom: "24px" }}>
        <h2 className="text-section-title" style={{ marginBottom: "8px" }}>🗺️ 진행 과정</h2>
        <MilestoneList milestones={payload.milestones ?? []} />
      </section>

      {/* ⑤ 막히면 이렇게 */}
      <section style={{ marginBottom: "24px" }}>
        <h2 className="text-section-title" style={{ marginBottom: "8px" }}>🆘 막히면 이렇게</h2>
        {(payload.troubleshooting ?? []).map((t, i) => (
          <div key={i} style={{ marginBottom: "12px" }}>
            <p className="text-body" style={{ fontWeight: 600 }}>{t.symptom}</p>
            <p className="text-body" style={{ color: "var(--text-secondary)" }}>{t.fix}</p>
          </div>
        ))}
      </section>

      {/* ⑥ 다 됐는지 확인 */}
      <section style={{ marginBottom: "24px" }}>
        <h2 className="text-section-title" style={{ marginBottom: "8px" }}>✅ 다 됐는지 확인</h2>
        <SuccessChecklist items={payload.success_checklist ?? []} />
      </section>
    </>
  );
}
```

- [ ] **Step 3: 타입체크**

Run: `cd web && npx tsc --noEmit`
Expected: 새 파일 관련 에러 없음(기존 프로젝트 에러가 있다면 이 파일 경로가 새로 등장하지 않는지 확인).

- [ ] **Step 4: 커밋**

```bash
git add web/src/components/home/review/project-card-blocks.tsx web/src/components/home/review/__tests__/project-card-blocks.test.tsx
git commit -m "feat(web/cards): 프로젝트 카드 ①~⑥ 블록 컴포넌트 + 스펙 문서"
```

---

### Task 2: 카드 래퍼 컴포넌트 (`project-card-content.tsx`)

뒤로가기·헤더(제목·난이도 뱃지·시간·skill_label)·블록 오케스트레이션·⑦ 결과 인라인 바(UI만).

**Files:**
- Create: `web/src/components/home/review/project-card-content.tsx`
- Test: `web/src/components/home/review/__tests__/project-card-content.test.tsx`

**Interfaces:**
- Consumes: `ProjectCardBlocks`, `CARD_DIFFICULTY_LABEL`, `type ProjectCardPayload` (Task 1)
- Produces: `function ProjectCardContent({ signalId, signalTitle, payload }: { signalId: string; signalTitle: string; payload: ProjectCardPayload }): JSX.Element`

- [ ] **Step 1: 스펙 문서(미실행 테스트) 작성**

Create `web/src/components/home/review/__tests__/project-card-content.test.tsx`:

```tsx
/**
 * project-card-content.test.tsx
 *
 * NOTE: 이 프로젝트에는 Jest/Vitest가 설정되어 있지 않습니다.
 * 이 파일은 테스트 스펙 문서 역할을 합니다.
 */

// @ts-nocheck — 테스트 러너 없이 타입 오류 방지
import { render, screen, fireEvent } from "@testing-library/react";
import { ProjectCardContent } from "../project-card-content";

const payload = {
  skill_label: "웹폼 만들고 데이터 저장하기",
  difficulty: "first_step",
  estimated_minutes: 30,
  deliverable: "간단한 예약 폼 웹페이지",
  success_preview: "폼에 입력하면 목록에 추가돼요",
  prerequisites: "없어요, 바로 시작!",
  how_to_start: "AI 코딩 도구를 열고 붙여넣으세요.",
  example_prompt: "예약 폼 만들어줘.",
  milestones: [{ action: "폼 만들기", done_signal: "입력칸 보임" }],
  troubleshooting: [{ symptom: "저장 안 됨", fix: "다시 요청" }],
  success_checklist: ["폼이 보인다"],
};

test("헤더에 제목·난이도 뱃지·시간·스킬라벨이 나온다", () => {
  render(<ProjectCardContent signalId="s1" signalTitle="예약 폼 만들기" payload={payload} />);
  expect(screen.getByText("예약 폼 만들기")).toBeTruthy();
  expect(screen.getByText(/첫걸음/)).toBeTruthy();       // first_step → 첫걸음
  expect(screen.getByText(/30분/)).toBeTruthy();
  expect(screen.getByText(/웹폼 만들고 데이터 저장하기/)).toBeTruthy();
});

test("⑦ 결과 버튼 클릭 시 '곧 지원' 토스트가 뜬다", () => {
  render(<ProjectCardContent signalId="s1" signalTitle="t" payload={payload} />);
  fireEvent.click(screen.getByRole("button", { name: /성공/ }));
  expect(screen.getByText(/곧 지원/)).toBeTruthy();
});
```

- [ ] **Step 2: 컴포넌트 구현**

Create `web/src/components/home/review/project-card-content.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ProjectCardBlocks, CARD_DIFFICULTY_LABEL, type ProjectCardPayload } from "./project-card-blocks";

interface Props {
  signalId: string;
  signalTitle: string;
  payload: ProjectCardPayload;
}

const OUTCOMES = [
  { key: "success", label: "🎉 성공" },
  { key: "stuck", label: "😵 막힘" },
  { key: "give_up", label: "🏳️ 포기" },
];

export function ProjectCardContent({ signalTitle, payload }: Props) {
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  return (
    <div className="screen-container" style={{ paddingTop: "24px", paddingBottom: "96px" }}>
      <Link
        href="/home"
        className="text-label"
        style={{ display: "inline-flex", alignItems: "center", gap: "4px", color: "var(--text-secondary)", marginBottom: "20px" }}
      >
        <svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M10 4L6 8l4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        홈으로
      </Link>

      {/* 헤더 */}
      <h1 className="text-screen-title" style={{ marginBottom: "12px" }}>{signalTitle}</h1>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center", marginBottom: "8px" }}>
        <span
          className="text-label"
          style={{ background: "var(--surface-card, #F2F2F2)", borderRadius: "9999px", padding: "4px 12px" }}
        >
          🏷️ {CARD_DIFFICULTY_LABEL[payload.difficulty]}
        </span>
        <span className="text-label" style={{ color: "var(--text-secondary)" }}>⏱ {payload.estimated_minutes}분</span>
      </div>
      <p className="text-body" style={{ color: "var(--text-secondary)", marginBottom: "24px" }}>
        🎓 {payload.skill_label}
      </p>

      <ProjectCardBlocks payload={payload} />

      {/* ⑦ 결과 남기기 (인라인, UI만 — 저장 API는 다음 슬라이스) */}
      <section style={{ marginTop: "8px" }}>
        <h2 className="text-section-title" style={{ marginBottom: "8px" }}>결과 남기기</h2>
        <div style={{ display: "flex", gap: "8px" }}>
          {OUTCOMES.map((o) => (
            <button
              key={o.key}
              type="button"
              onClick={() => setToast("결과 기록은 곧 지원돼요")}
              style={{
                flex: 1,
                minHeight: "44px",
                borderRadius: "9999px",
                border: "1px solid var(--border-subtle, #E5E5E5)",
                background: "transparent",
                cursor: "pointer",
                fontSize: "14px",
                fontWeight: 500,
              }}
            >
              {o.label}
            </button>
          ))}
        </div>
      </section>

      {toast && (
        <div
          role="status"
          aria-live="polite"
          style={{
            position: "fixed",
            bottom: "calc(80px + env(safe-area-inset-bottom))",
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            zIndex: 60,
            pointerEvents: "none",
          }}
        >
          <div style={{ background: "rgba(0,0,0,0.75)", color: "#fff", padding: "10px 20px", borderRadius: "9999px", fontSize: "14px" }}>
            {toast}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: 타입체크**

Run: `cd web && npx tsc --noEmit`
Expected: 새 파일 관련 에러 없음.

- [ ] **Step 4: 커밋**

```bash
git add web/src/components/home/review/project-card-content.tsx web/src/components/home/review/__tests__/project-card-content.test.tsx
git commit -m "feat(web/cards): 프로젝트 카드 래퍼(헤더·⑦ 결과 인라인) 컴포넌트"
```

---

### Task 3: `review_type` 분기 배선 (page + ReviewPageContent)

`page.tsx`가 `review_type`을 전달하고, `ReviewPageContent`가 완성 상태에서 카드/리서치를 분기한다. queue 리뷰 페이지도 같은 `ReviewPageContent`를 쓰므로 자동 적용된다.

**Files:**
- Modify: `web/src/app/(app)/home/review/[signalId]/page.tsx`
- Modify: `web/src/components/home/review/review-page-content.tsx`
- Test: `web/src/components/home/review/__tests__/review-page-content.test.tsx`

**Interfaces:**
- Consumes: `ProjectCardContent` (Task 2), `type ProjectCardPayload` (Task 1), 기존 `ResearchReviewContent`/`ReviewPayload`
- Produces: 분기된 `ReviewPageContent`(완성 시 `reviewType==="project_card"` → 카드, 그 외 → 리서치)

- [ ] **Step 1: 분기 스펙 문서(미실행 테스트) 작성**

Create `web/src/components/home/review/__tests__/review-page-content.test.tsx`:

```tsx
/**
 * review-page-content.test.tsx
 *
 * NOTE: 이 프로젝트에는 Jest/Vitest가 설정되어 있지 않습니다.
 * 이 파일은 테스트 스펙 문서 역할을 합니다.
 */

// @ts-nocheck — 테스트 러너 없이 타입 오류 방지
import { render, screen } from "@testing-library/react";
import { ReviewPageContent } from "../review-page-content";

jest.mock("@/lib/engagement", () => ({ trackEngagement: jest.fn() }));
jest.mock("@/lib/supabase", () => ({ createClient: () => ({ auth: { getSession: async () => ({ data: { session: null } }) } }) }));

const cardPayload = {
  skill_label: "웹폼 만들기", difficulty: "first_step", estimated_minutes: 30,
  deliverable: "예약 폼", success_preview: "목록에 추가됨", prerequisites: "없음",
  how_to_start: "붙여넣기", example_prompt: "만들어줘",
  milestones: [{ action: "a", done_signal: "b" }],
  troubleshooting: [{ symptom: "s", fix: "f" }], success_checklist: ["c"],
};

test("review_type=project_card 면 카드 헤더 블록을 렌더한다", () => {
  render(
    <ReviewPageContent
      signalId="s1"
      signalTitle="카드 제목"
      initialReview={{ id: "r1", status: "completed", signalTitle: "카드 제목", payload: cardPayload, reviewType: "project_card" }}
    />
  );
  expect(screen.getByText("📦 완성하면 이게 나와")).toBeTruthy();
});

test("review_type 이 research/undefined 면 기존 13섹션(핵심 한 줄 요약)을 렌더한다", () => {
  const researchPayload = {
    one_line_definition: "정의", key_concepts: "", problems_solved: "", why_it_matters: "",
    vs_existing_tech: "", user_relevance: "", learning_goals: "",
    learning_time_difficulty: { estimated_hours: 1, difficulty: "beginner" },
    practical_applicability: "", risks: "", recommendation_reason: "", reference_sources: [],
    honest_box: { content: "", severity: "standard" },
  };
  render(
    <ReviewPageContent
      signalId="s2"
      signalTitle="리서치 제목"
      initialReview={{ id: "r2", status: "completed", signalTitle: "리서치 제목", payload: researchPayload }}
    />
  );
  expect(screen.getByText("핵심 한 줄 요약")).toBeTruthy();
});
```

- [ ] **Step 2: `ReviewPageContent`에 분기 추가**

Modify `web/src/components/home/review/review-page-content.tsx`.

2a. import 추가 (파일 상단 import 블록, `ResearchReviewContent` import 아래):

```tsx
import { ProjectCardContent } from "./project-card-content";
import type { ProjectCardPayload } from "./project-card-blocks";
```

2b. `ReviewUIState`의 completed 변형에 `reviewType`과 payload 유니온 반영:

```tsx
type ReviewUIState =
  | { type: "completed"; reviewId: string; payload: ReviewPayload | ProjectCardPayload; signalTitle: string; barGateOverride?: string | null; reviewType?: string | null }
  | { type: "generating" }
  | { type: "failed" };
```

2c. `InitialReview` 타입에 `reviewType` 추가:

```tsx
type InitialReview = {
  id: string;
  status: string;
  signalTitle: string;
  payload?: ReviewPayload;
  barGateOverride?: string | null;
  reviewType?: string | null;
} | null;
```

2d. 초기 completed 상태에 `reviewType` 전달 (useState 초기화 블록):

```tsx
    if (initialReview?.status === "completed" && initialReview.payload) {
      return {
        type: "completed",
        reviewId: initialReview.id,
        payload: initialReview.payload,
        signalTitle: initialReview.signalTitle,
        barGateOverride: initialReview.barGateOverride,
        reviewType: initialReview.reviewType,
      };
    }
```

2e. 실시간 재조회 콜백에서 `review_type`도 함께 읽어 반영. `triggerAndSubscribe` 안의 재조회 블록을 아래로 교체:

```tsx
            const { data } = await supabase
              .from("reviews")
              .select("result, bar_gate_override")
              .eq("id", reviewId)
              .single();
            const fetched = data?.result?.payload as ReviewPayload | ProjectCardPayload | undefined;
            if (fetched) {
              setUIState({
                type: "completed",
                reviewId: reviewIdRef.current ?? reviewId,
                payload: fetched,
                signalTitle,
                barGateOverride: data?.bar_gate_override as string | null,
                reviewType: (data?.result?.review_type as string | null | undefined) ?? null,
              });
            } else {
              setUIState({ type: "failed" });
            }
```

2f. 렌더 분기 — 기존 `if (uiState.type === "completed")` 블록을 아래로 교체:

```tsx
  if (uiState.type === "completed") {
    if (uiState.reviewType === "project_card") {
      return (
        <ProjectCardContent
          signalId={signalId}
          signalTitle={uiState.signalTitle}
          payload={uiState.payload as ProjectCardPayload}
        />
      );
    }
    return (
      <ResearchReviewContent
        signalId={signalId}
        signalTitle={uiState.signalTitle}
        payload={uiState.payload as ReviewPayload}
        reviewId={uiState.reviewId}
        barGateOverride={uiState.barGateOverride}
      />
    );
  }
```

- [ ] **Step 3: `page.tsx`가 `reviewType` 전달**

Modify `web/src/app/(app)/home/review/[signalId]/page.tsx`.

3a. `InitialReview` 타입에 `reviewType` 추가:

```tsx
export type InitialReview = {
  id: string;
  status: string;
  signalTitle: string;
  payload?: ReviewPayload;
  barGateOverride?: string | null;
  reviewType?: string | null;
} | null;
```

3b. `initialReview` 생성 블록에서 `review_type` 읽어 전달:

```tsx
  let initialReview: InitialReview = null;
  if (reviewRow) {
    const payload = reviewRow.result?.payload as ReviewPayload | undefined;
    initialReview = {
      id: reviewRow.id as string,
      status: reviewRow.status as string,
      signalTitle,
      payload,
      barGateOverride: reviewRow.bar_gate_override as string | null | undefined,
      reviewType: (reviewRow.result?.review_type as string | null | undefined) ?? null,
    };
  }
```

- [ ] **Step 4: 타입체크**

Run: `cd web && npx tsc --noEmit`
Expected: 에러 없음. (payload 유니온 캐스팅으로 타입 통과)

- [ ] **Step 5: 커밋**

```bash
git add web/src/app/\(app\)/home/review/\[signalId\]/page.tsx web/src/components/home/review/review-page-content.tsx web/src/components/home/review/__tests__/review-page-content.test.tsx
git commit -m "feat(web/cards): review_type 분기 — project_card면 카드, 아니면 13섹션"
```

---

### Task 4: 시각 검증 (Playwright) + 최종 타입체크

카드 상세화면을 실제 브라우저에서 렌더해 7블록·인터랙션을 확인한다.

**Files:** (코드 변경 없음 — 검증만. 필요 시 스크린샷 저장)

- [ ] **Step 1: 백엔드 카드 모드 확인 / 시드**

카드를 실제로 보려면 `review_type="project_card"`인 completed 리뷰가 있어야 한다. 둘 중 하나:
- (a) 백엔드 `beginner_card_mode_enabled=true`로 새 리뷰를 트리거해 카드 생성, 또는
- (b) Supabase에서 기존 completed 리뷰 한 건의 `result`를 카드 payload(11키)+`review_type:"project_card"`로 임시 세팅.

로컬 실행은 [[local-run-setup]] 참고(backend :8000, web :3000). 로그인 계정: `test-history@decisionos.dev / Test1234!`([[seed-test-user-supabase]]).

- [ ] **Step 2: Playwright로 카드 상세화면 확인**

웹 실행 후 해당 signal의 `/home/review/<signalId>` 접속 → 다음 확인:
- 헤더: 제목 · 🏷️난이도 뱃지 · ⏱분 · 🎓skill_label
- ①~⑥ 블록 헤더/내용, ③ 예시 프롬프트 박스 + 📋복사(클릭 시 "복사됨!")
- ④ 체크박스 토글 시 진도 카운트 변화
- ⑦ 결과 버튼 클릭 시 "결과 기록은 곧 지원돼요" 토스트
- 같은 화면에서 `review_type="research"` 리뷰는 기존 13섹션이 그대로 나오는지(회귀 확인)

스크린샷을 남겨 결과 첨부.

- [ ] **Step 3: 최종 타입체크**

Run: `cd web && npx tsc --noEmit`
Expected: 에러 없음.

- [ ] **Step 4: (변경이 있었다면) 커밋**

```bash
git add -A && git commit -m "chore(web/cards): 카드 상세화면 시각 검증"
```

---

## Self-Review

- **Spec coverage**: 분기(Task 3) · 7블록 렌더(Task 1: ①~⑥, Task 2: 헤더+⑦) · ④/⑥ 로컬 체크박스(Task 1) · ③ 복사(Task 1) · ⑦ UI-only 토스트(Task 2) · 폴백 undefined→research(Task 3 2f/3b) · 검증방식(Task 4) 모두 커버.
- **Type consistency**: `ProjectCardPayload`/`CARD_DIFFICULTY_LABEL`/`ProjectCardBlocks`(Task 1) → `ProjectCardContent`(Task 2) → `ReviewPageContent` 분기(Task 3)로 이름·시그니처 일관. payload 유니온은 `as` 캐스팅으로 렌더 직전 좁힘.
- **Placeholder scan**: 모든 코드 스텝에 실제 코드 포함. TODO/TBD 없음. ⑦ 저장 미구현은 의도된 범위(주석으로 명시).
- **비범위 확인**: history chain(`ReviewSections` 직접 사용)은 카드 미대응 — Global Constraints에 명시.
