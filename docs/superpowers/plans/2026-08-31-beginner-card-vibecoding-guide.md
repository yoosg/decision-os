# 입문자 카드 통합 바이브코딩 가이드 (P3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 입문자 프로젝트 카드 상단에 "Claude Code 설정 + 바이브코딩 흐름 6단계"를 담은 접이식(fold) 정적 가이드를 추가해, 카드 하나만 보고도 바이브코딩을 시작할 수 있게 한다.

**Architecture:** 순수 프론트엔드. 정적 콘텐츠 상수 + `localStorage` 첫 방문 자동 펼침을 가진 client 컴포넌트 `VibeCodingGuide`를 신설하고, 카드가 렌더되는 두 호출처(홈/큐/스탠드얼론, 체인상세) 최상단에 삽입한다. 백엔드·스키마·API 변경 없음.

**Tech Stack:** Next.js 16.2.11, React 19.2.4, TypeScript, 인라인 스타일(주변 카드 컨벤션).

## Global Constraints

- **백엔드/스키마/API 변경 절대 없음.** 콘텐츠는 전부 프론트 정적 상수(LLM 생성 아님).
- **웹 테스트 러너 없음(이 브랜치):** `package.json` scripts = dev/build/start만, vitest 미설치. 검증 = `npx tsc --noEmit`(타입) + Playwright 라이브. 실행형 유닛테스트 없음.
- **Next.js 주의:** `web/AGENTS.md` — 이 저장소 Next.js는 수정본. 코드 작성 전 `node_modules/next/dist/docs/`의 관련 가이드 확인.
- **스코프:** P3만. P1(마일스톤)·P2(체크리스트)는 건드리지 않음. 리서치 리뷰 화면엔 가이드 미노출.
- **톤:** PR #7 모노크롬 폴리시와 일치(담백한 박스, 검정 텍스트/서브텍스트, 인라인 스타일).
- **콘텐츠 문구는 아래 코드에 있는 값을 그대로(verbatim) 사용.**
- **작업 브랜치:** `feat/beginner-card-vibecoding-guide` (이미 체크아웃됨).
- **라이브 검증용 시드:** signal `ccb42703-16ea-479e-9d1d-336ed9f70bf6`에 project_card completed 리뷰 `ac38f504-f212-4e45-afb9-2694e2a3599a`가 심겨 있음. URL `http://localhost:3000/home/review/ccb42703-16ea-479e-9d1d-336ed9f70bf6` (테스트 유저로 로그인된 브라우저). 검증 후 Task 2에서 정리.

---

## File Structure

- **Create** `web/src/components/home/review/vibe-coding-guide.tsx` — `VibeCodingGuide` 컴포넌트 + 정적 콘텐츠 상수(`SETUP_STEPS`, `FLOW_STEPS`). 하나의 책임: 가이드 fold 렌더 + 첫 방문 자동 펼침. `FLOW_STEPS`는 P1 마일스톤 백본으로 재사용될 예정이나 P3에선 이 파일에 둔다(주석 표기).
- **Modify** `web/src/components/home/review/project-card-content.tsx` — h1 다음, `<ProjectCardMeta>` 앞에 `<VibeCodingGuide />` 삽입.
- **Modify** `web/src/components/history/chain-detail-content.tsx` — `project_card` 분기 내 `<ProjectCardMeta>` 앞에 `<VibeCodingGuide />` 삽입.

---

### Task 1: VibeCodingGuide 컴포넌트 (콘텐츠 + fold + 첫 방문 자동 펼침)

**Files:**
- Create: `web/src/components/home/review/vibe-coding-guide.tsx`

**Interfaces:**
- Consumes: 없음(자체 완결).
- Produces: `export function VibeCodingGuide(): JSX.Element` — props 없음. Task 2가 두 호출처에서 `<VibeCodingGuide />`로 사용.

- [ ] **Step 1: Next.js 가이드 확인 (코드 작성 전)**

Run: `ls node_modules/next/dist/docs/ 2>/dev/null && echo '---' && sed -n '1,40p' node_modules/next/dist/docs/*.md 2>/dev/null | head -60`
목적: client 컴포넌트/`"use client"`/`useEffect` 사용 관련 이 버전 특이사항이 있는지 훑기. 특이사항 없으면 진행.

- [ ] **Step 2: 컴포넌트 파일 작성 (전체 코드)**

Create `web/src/components/home/review/vibe-coding-guide.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";

const SEEN_KEY = "vibecoding_guide_seen";

const SETUP_STEPS: { title: string; desc: string }[] = [
  { title: "설치", desc: "터미널에 npm install -g @anthropic-ai/claude-code (또는 데스크톱 앱 설치)" },
  { title: "로그인", desc: "claude 실행 후 화면 안내대로 로그인" },
  { title: "폴더 열기", desc: "프로젝트 폴더를 만들고 그 안에서 claude 실행" },
  { title: "첫 프롬프트", desc: "카드의 '예시 프롬프트'를 그대로 붙여넣기" },
];

// 이 6단계 백본은 후속 P1(마일스톤 프로세스화)에서 재사용 예정 — 그때 공용 상수로 추출.
const FLOW_STEPS: { title: string; desc: string }[] = [
  { title: "브레인스토밍", desc: "\"이 아이디어로 뭘 만들 수 있어?\" Claude에게 옵션 펼쳐달라 하기" },
  { title: "구체화", desc: "그중 하나를 골라 한 문장으로 좁히기" },
  { title: "기획·설계", desc: "필요한 화면·데이터·기능을 목록으로 적기" },
  { title: "개발", desc: "화면부터 만들고, 그다음 기능 붙이기" },
  { title: "테스트", desc: "직접 써보며 안 되는 걸 Claude에게 고쳐달라 하기" },
  { title: "마무리·다음", desc: "정리하고 \"다음엔 뭘 더 해볼까?\" 물어보기" },
];

export function VibeCodingGuide() {
  // SSR/hydration mismatch 회피: 서버·클라 모두 초기엔 접힘(false)으로 렌더 →
  // 마운트 후 useEffect에서 첫 방문이면 펼친다.
  const [open, setOpen] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem(SEEN_KEY)) {
        setOpen(true);
        localStorage.setItem(SEEN_KEY, "1");
      }
    } catch {
      // localStorage 접근 불가(프라이빗 모드 등) → 접힌 기본값 유지
    }
  }, []);

  const listStyle = { margin: "0 0 16px", paddingLeft: "18px", fontSize: "13px", color: "var(--text-secondary)" } as const;
  const headingStyle = { fontSize: "13px", fontWeight: 700, margin: "0 0 8px" } as const;

  return (
    <section
      style={{
        border: "1px solid var(--border-subtle, #E5E5E5)",
        borderRadius: "12px",
        padding: "12px 14px",
        marginBottom: "20px",
        background: "var(--surface-card, #F7F7F7)",
      }}
    >
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        style={{
          width: "100%",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "transparent",
          border: "none",
          padding: 0,
          cursor: "pointer",
          fontSize: "14px",
          fontWeight: 700,
          color: "var(--text-primary, #111)",
        }}
      >
        <span>🧭 바이브코딩 가이드</span>
        <span aria-hidden="true" style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
          {open ? "접기 ▴" : "펼치기 ▾"}
        </span>
      </button>

      {open && (
        <div style={{ marginTop: "12px" }}>
          <h3 style={headingStyle}>🧰 처음이라면: Claude Code 켜기</h3>
          <ol style={listStyle}>
            {SETUP_STEPS.map((s) => (
              <li key={s.title} style={{ marginBottom: "4px" }}>
                <strong style={{ color: "var(--text-primary)" }}>{s.title}</strong> — {s.desc}
              </li>
            ))}
          </ol>

          <h3 style={headingStyle}>🧭 바이브코딩은 이렇게 흘러가요</h3>
          <ol style={{ ...listStyle, marginBottom: 0 }}>
            {FLOW_STEPS.map((s) => (
              <li key={s.title} style={{ marginBottom: "4px" }}>
                <strong style={{ color: "var(--text-primary)" }}>{s.title}</strong> — {s.desc}
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 3: 타입체크**

Run: `cd web && npx tsc --noEmit`
Expected: 에러 0(신규 파일 관련). (기존 무관 에러가 있으면 신규 파일 라인만 클린인지 확인.)

- [ ] **Step 4: 커밋**

```bash
git add web/src/components/home/review/vibe-coding-guide.tsx
git commit -m "feat(cards): 바이브코딩 가이드 fold 컴포넌트(설정+흐름 6단계, 첫방문 자동펼침)"
```

---

### Task 2: 두 호출처에 삽입 + 라이브 검증 + 시드 정리

**Files:**
- Modify: `web/src/components/home/review/project-card-content.tsx` (h1 다음, `<ProjectCardMeta payload={payload} />` 앞)
- Modify: `web/src/components/history/chain-detail-content.tsx` (`project_card` 분기 내 `<ProjectCardMeta payload={review.payload} />` 앞)

**Interfaces:**
- Consumes: Task 1의 `VibeCodingGuide`.
- Produces: 없음(최종 통합).

- [ ] **Step 1: project-card-content.tsx 삽입**

import 추가(기존 import 블록에):
```tsx
import { VibeCodingGuide } from "./vibe-coding-guide";
```
`<h1 ...>{signalTitle}</h1>` 다음 줄, `<ProjectCardMeta payload={payload} />` **앞**에 삽입:
```tsx
      <h1 className="text-screen-title" style={{ marginBottom: "12px" }}>{signalTitle}</h1>
      <VibeCodingGuide />
      <ProjectCardMeta payload={payload} />
```

- [ ] **Step 2: chain-detail-content.tsx 삽입**

import 추가(기존 import 블록에):
```tsx
import { VibeCodingGuide } from "@/components/home/review/vibe-coding-guide";
```
`project_card` 분기의 `<ProjectCardMeta payload={review.payload} />` **앞**에 삽입:
```tsx
            <>
              <VibeCodingGuide />
              <ProjectCardMeta payload={review.payload} />
              <ProjectCardBlocks payload={review.payload} />
            </>
```

- [ ] **Step 3: 타입체크**

Run: `cd web && npx tsc --noEmit`
Expected: 신규 삽입 관련 에러 0.

- [ ] **Step 4: 라이브 검증 — 첫 방문 자동 펼침**

브라우저(테스트 유저 로그인 상태)에서 Playwright로:
1. localStorage 비우기: `localStorage.removeItem('vibecoding_guide_seen')`
2. `http://localhost:3000/home/review/ccb42703-16ea-479e-9d1d-336ed9f70bf6` 로드
3. 확인: `🧭 바이브코딩 가이드`가 **펼쳐진 상태**, "🧰 처음이라면: Claude Code 켜기"와 6단계 흐름이 보임(브레인스토밍…마무리·다음).
Expected: 펼침 + 두 섹션·6단계 모두 표시.

- [ ] **Step 5: 라이브 검증 — 재방문 접힘 + 토글**

1. 같은 페이지 새로고침(플래그 이미 세팅됨)
2. 확인: 가이드가 **접힘**(헤더만, "펼치기 ▾").
3. 헤더 클릭 → 펼쳐지고 `aria-expanded=true`.
Expected: 재방문 접힘, 클릭 시 펼침.

- [ ] **Step 6: 라이브 검증 — 리서치 리뷰엔 미노출**

리서치 리뷰 시그널(예: 히스토리/홈에서 카드 아닌 리뷰) 상세를 열어 `🧭 바이브코딩 가이드`가 **없음** 확인.
Expected: 카드가 아닌 화면엔 가이드 미표시.

- [ ] **Step 7: 커밋**

```bash
git add web/src/components/home/review/project-card-content.tsx web/src/components/history/chain-detail-content.tsx
git commit -m "feat(cards): 카드 상단에 바이브코딩 가이드 노출(홈/큐/스탠드얼론/체인상세)"
```

- [ ] **Step 8: 라이브 검증 시드 정리**

검증이 끝났으므로 심어둔 시드 카드와 임시 스크립트를 정리:
```bash
# 임시 스크립트 삭제
rm -f api/_show_card_oneoff.py
```
시드 리뷰 행 삭제(Supabase MCP 또는 SQL):
```sql
delete from reviews where id = 'ac38f504-f212-4e45-afb9-2694e2a3599a';
```
Expected: 임시 파일 제거, 시드 카드 행 삭제(해당 시그널은 다시 리서치 리뷰로 표시됨).

---

## Self-Review

**Spec coverage:**
- 카드 상단 단일 fold → Task 1 컴포넌트 + Task 2 삽입 ✓
- 정적 콘텐츠 A(4스텝)+B(6단계) → Task 1 `SETUP_STEPS`/`FLOW_STEPS` ✓
- 첫 방문 자동 펼침(localStorage 전역) → Task 1 `useEffect` ✓
- 전 화면(홈/큐/스탠드얼론=project-card-content, 체인상세=chain-detail-content) → Task 2 Step 1–2 ✓
- 리서치 리뷰 미노출 → 두 호출처 모두 project_card 경로에만 삽입(리서치 경로 무변경) + Task 2 Step 6 검증 ✓
- 백엔드 무변경 → 파일 변경 목록에 api/ 없음 ✓
- 6단계 백본 P1 재사용 표기 → Task 1 주석 ✓
- 검증=tsc+Playwright(러너 없음) → 각 Task 검증 스텝 ✓
- 시드/임시파일 정리 → Task 2 Step 8 ✓

**Placeholder scan:** 전체 코드·명령·기대값 명시. TBD/TODO 없음. (설치 명령 재검증은 Step 1의 docs 확인과 별개로, 문구 자체는 스펙 확정값 사용.)

**Type consistency:** `VibeCodingGuide`(무props) 이름·시그니처가 Task 1 정의 = Task 2 사용처 일치. `SEEN_KEY="vibecoding_guide_seen"`가 컴포넌트와 Task 2 Step 4/8 검증에서 동일.

---

## Execution Handoff

계획 완료. 실행 방식은 문서 저장 후 선택.
