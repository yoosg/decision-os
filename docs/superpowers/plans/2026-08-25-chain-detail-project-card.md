# 입문자 카드 체인 상세 대응 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 체인 상세(`/history/chain/[signalId]`)의 REVIEW 노드가 `review_type`을 읽어 `project_card`면 배지+7블록 카드로, 그 외면 기존 13섹션으로 렌더하도록 분기한다.

**Architecture:** `page.tsx`가 `result` 봉투에서 `review_type`을 함께 꺼내 `ChainDetailContent`로 내려보내고, 컴포넌트는 `reviewType`으로 분기한다. 카드 본문의 배지 부분을 `ProjectCardMeta` 공용 컴포넌트로 추출해 기존 카드 화면과 체인이 공유한다.

**Tech Stack:** Next.js(App Router, 커스텀 빌드 — `web/AGENTS.md` 참고), React 서버/클라이언트 컴포넌트, Supabase, TypeScript.

## Global Constraints

- 이 브랜치엔 유닛 테스트 러너가 없다(vitest/jest 미설치). 검증은 `npx tsc --noEmit` 타입체크 + Playwright/수동 확인으로 한다.
- `web/AGENTS.md`: 이 Next.js는 관례가 다를 수 있으니 API를 쓰기 전 `node_modules/next/dist/docs/`의 해당 가이드를 확인한다.
- 기존 카드 화면(`ProjectCardContent`)은 리팩터 후에도 **픽셀 동일**해야 한다(회귀 기준).
- `review_type` 값: `"project_card"`(입문자 7블록 카드) vs 그 외(`"research"`/undefined → 13섹션).
- 작업 디렉토리 기준: 모든 명령은 `web/`에서 실행. 브랜치: `feat/chain-detail-project-card`.

---

## File Structure

- `web/src/components/home/review/project-card-blocks.tsx` — **수정**: `ProjectCardMeta` 컴포넌트 추가 export.
- `web/src/components/home/review/project-card-content.tsx` — **수정**: 인라인 배지를 `<ProjectCardMeta/>`로 교체.
- `web/src/app/(app)/history/chain/[signalId]/page.tsx` — **수정**: `review_type` 추출 + `ChainDetailData.review`에 전달.
- `web/src/components/history/chain-detail-content.tsx` — **수정**: `ChainDetailData` 타입 확장 + REVIEW 노드 분기 렌더.

---

### Task 1: `ProjectCardMeta` 추출 (회귀 중립 리팩터)

**Files:**
- Modify: `web/src/components/home/review/project-card-blocks.tsx`
- Modify: `web/src/components/home/review/project-card-content.tsx:5`, `:42-54`

**Interfaces:**
- Produces: `ProjectCardMeta({ payload }: { payload: ProjectCardPayload }): JSX.Element` — 배지 두 줄(난이도/시간 배지 + 스킬 줄), export from `project-card-blocks.tsx`.

- [ ] **Step 1: `ProjectCardMeta`를 `project-card-blocks.tsx`에 추가**

`CARD_DIFFICULTY_LABEL` 정의(현재 19-23줄) 바로 아래에 추가한다. 내용은 `project-card-content.tsx`의 기존 배지 마크업(43-54줄)을 그대로 옮긴 것이다:

```tsx
export function ProjectCardMeta({ payload }: { payload: ProjectCardPayload }) {
  return (
    <>
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
    </>
  );
}
```

- [ ] **Step 2: `project-card-content.tsx` import 교체 (5줄)**

`CARD_DIFFICULTY_LABEL`은 추출 후 이 파일에서 더 이상 쓰지 않으므로 제거하고 `ProjectCardMeta`를 추가한다.

변경 전:
```tsx
import { ProjectCardBlocks, CARD_DIFFICULTY_LABEL, type ProjectCardPayload } from "./project-card-blocks";
```
변경 후:
```tsx
import { ProjectCardBlocks, ProjectCardMeta, type ProjectCardPayload } from "./project-card-blocks";
```

- [ ] **Step 3: `project-card-content.tsx` 배지 마크업을 컴포넌트 호출로 교체 (42-54줄)**

`h1` 제목은 그대로 두고, 그 아래 배지 div + 스킬 p(43-54줄)를 `<ProjectCardMeta/>` 한 줄로 바꾼다.

변경 전:
```tsx
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
```
변경 후:
```tsx
      {/* 헤더 */}
      <h1 className="text-screen-title" style={{ marginBottom: "12px" }}>{signalTitle}</h1>
      <ProjectCardMeta payload={payload} />
```

- [ ] **Step 4: 타입체크**

Run: `npx tsc --noEmit`
Expected: 에러 없음(exit 0). 특히 `project-card-content.tsx`에서 `CARD_DIFFICULTY_LABEL` 미사용 경고/에러가 없어야 한다.

- [ ] **Step 5: 회귀 확인 (기존 카드 화면 픽셀 동일)**

`next dev` 실행 후 기존 `project_card` 리뷰 화면(`/home/review/[signalId]`)을 열어 헤더가 이전과 동일한지 확인한다. (러너 없음 — 시각 확인.) 대상 signalId를 모르면 Supabase에서 조회:
```sql
select signal_id from reviews
where status='completed' and result->>'review_type'='project_card'
order by created_at desc limit 1;
```
Expected: 제목 → 🏷️난이도·⏱분 배지 → 🎓스킬 순서/여백이 리팩터 전과 동일.

- [ ] **Step 6: Commit**

```bash
git add web/src/components/home/review/project-card-blocks.tsx web/src/components/home/review/project-card-content.tsx
git commit -m "refactor(cards): 카드 헤더 배지를 ProjectCardMeta 공용 컴포넌트로 추출

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: 데이터 흐름 — `review_type` 전달

**Files:**
- Modify: `web/src/components/history/chain-detail-content.tsx:8-20` (`ChainDetailData` 타입)
- Modify: `web/src/app/(app)/history/chain/[signalId]/page.tsx:5`, `:37-40`, `:76`, `:84`

**Interfaces:**
- Consumes: `ProjectCardPayload`, `ReviewPayload` 타입.
- Produces: `ChainDetailData.review` 형태가 `{ reviewType: string | null; payload: ReviewPayload | ProjectCardPayload } | null`. Task 3이 이 필드를 소비한다.

- [ ] **Step 1: `ChainDetailData.review` 타입 확장 (chain-detail-content.tsx 8-20줄)**

파일 상단 import에 `ProjectCardPayload`를 추가하고(2줄 근처), `review` 필드를 확장한다.

import 추가 (2줄 `ReviewSections` import 아래에):
```tsx
import { type ProjectCardPayload } from "@/components/home/review/project-card-blocks";
```
`review` 필드 변경 (10줄):
```tsx
  review: { reviewType: string | null; payload: ReviewPayload | ProjectCardPayload } | null;
```

- [ ] **Step 2: `page.tsx`에서 `ProjectCardPayload` import (5줄 근처)**

기존 `ReviewPayload` import 아래에 추가:
```tsx
import type { ProjectCardPayload } from "@/components/home/review/project-card-blocks";
```

- [ ] **Step 3: `page.tsx` reviewRow 타입에 `review_type` 추가 (37-40줄)**

변경 전:
```tsx
  const reviewRow = reviewData as unknown as {
    id: string;
    result: { payload?: ReviewPayload } | null;
  } | null;
```
변경 후:
```tsx
  const reviewRow = reviewData as unknown as {
    id: string;
    result: { review_type?: string | null; payload?: ReviewPayload | ProjectCardPayload } | null;
  } | null;
```

- [ ] **Step 4: `page.tsx` payload 추출 + review 조립 (76줄, 84줄)**

76줄 변경 전:
```tsx
  const payload = reviewRow?.result?.payload as ReviewPayload | undefined;
```
76줄 변경 후:
```tsx
  const payload = reviewRow?.result?.payload as ReviewPayload | ProjectCardPayload | undefined;
  const reviewType = reviewRow?.result?.review_type ?? null;
```
84줄 변경 전:
```tsx
    review: payload ? { payload } : null,
```
84줄 변경 후:
```tsx
    review: payload ? { reviewType, payload } : null,
```

- [ ] **Step 5: 타입체크**

Run: `npx tsc --noEmit`
Expected: 에러 없음(exit 0). Task 3 이전이라 `chain-detail-content.tsx`는 아직 `review.payload`만 쓰고 `reviewType`은 미소비 상태 — 객체 필드라 미사용 에러는 없다.

- [ ] **Step 6: Commit**

```bash
git add web/src/app/\(app\)/history/chain/\[signalId\]/page.tsx web/src/components/history/chain-detail-content.tsx
git commit -m "feat(chain): 체인 상세에 review_type 데이터 전달 플러밍

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: REVIEW 노드 분기 렌더 + 검증

**Files:**
- Modify: `web/src/components/history/chain-detail-content.tsx:2` (import), `:130-134` (REVIEW 노드)

**Interfaces:**
- Consumes: Task 2의 `ChainDetailData.review = { reviewType, payload }`; Task 1의 `ProjectCardMeta`; 기존 `ProjectCardBlocks`, `ReviewSections`.

- [ ] **Step 1: import 추가 (chain-detail-content.tsx 상단)**

Task 2에서 이미 `ProjectCardPayload`(type)를 import했다. 여기에 값 컴포넌트 두 개를 추가한다. 2줄의 `ReviewSections` import은 유지하고, 아래에:
```tsx
import { ProjectCardBlocks, ProjectCardMeta } from "@/components/home/review/project-card-blocks";
```
(Task 2에서 추가한 `import { type ProjectCardPayload } from ...` 줄과 합쳐 `import { ProjectCardBlocks, ProjectCardMeta, type ProjectCardPayload } from "@/components/home/review/project-card-blocks";` 한 줄로 정리해도 된다.)

- [ ] **Step 2: REVIEW 노드 분기 (130-134줄)**

변경 전:
```tsx
      {review && (
        <ChainNode color="var(--text-secondary)" glyph={null} typeLabel="REVIEW">
          <ReviewSections payload={review.payload} />
        </ChainNode>
      )}
```
변경 후:
```tsx
      {review && (
        <ChainNode color="var(--text-secondary)" glyph={null} typeLabel="REVIEW">
          {review.reviewType === "project_card" ? (
            <>
              <ProjectCardMeta payload={review.payload as ProjectCardPayload} />
              <ProjectCardBlocks payload={review.payload as ProjectCardPayload} />
            </>
          ) : (
            <ReviewSections payload={review.payload as ReviewPayload} />
          )}
        </ChainNode>
      )}
```

- [ ] **Step 3: 타입체크**

Run: `npx tsc --noEmit`
Expected: 에러 없음(exit 0).

- [ ] **Step 4: 검증 — research 체인 회귀 (Playwright/수동)**

`next dev` 실행 후 기존 research 리뷰가 있는 체인을 연다. 대상 조회:
```sql
select s.id from signals s
join reviews r on r.signal_id = s.id
where r.status='completed' and coalesce(r.result->>'review_type','research') <> 'project_card'
order by r.created_at desc limit 1;
```
`/history/chain/<id>` 접속.
Expected: REVIEW 칸이 기존 13섹션 그대로. 변화 없음.

- [ ] **Step 5: 검증 — project_card 체인 (Playwright/수동)**

`project_card` 리뷰가 달린 signal의 체인을 연다. 대상 조회:
```sql
select signal_id from reviews
where status='completed' and result->>'review_type'='project_card'
order by created_at desc limit 1;
```
`/history/chain/<signal_id>` 접속.
Expected:
- REVIEW 칸에 🏷️난이도·⏱분 배지 + 🎓스킬 + 7블록이 렌더된다.
- REVIEW 칸에 "결과 남기기" 버튼/토스트가 **없다**(OUTCOME 칸이 담당).
- "홈으로"/제목 h1 중복이 **없다**(체인의 "히스토리로"·SIGNAL 칸만).
- DECISION/OUTCOME 칸은 기존대로 렌더.

> 대상 데이터가 없으면: `test-history@decisionos.dev` 유저 신호 중 하나의 최신 완료 review `result`를 `project_card` 샘플 payload로 갱신해 케이스를 만든다(Supabase MCP `execute_sql`). 검증 후 원복하거나 그대로 두어도 무방.

- [ ] **Step 6: Commit**

```bash
git add web/src/components/history/chain-detail-content.tsx
git commit -m "feat(chain): REVIEW 노드를 review_type으로 분기(카드/리서치)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- 결정 1(배지 포함) → Task 3 Step 2(`ProjectCardMeta` + `ProjectCardBlocks`). ✓
- 결정 2(공용 컴포넌트) → Task 1(`ProjectCardMeta` 추출). ✓
- 데이터 흐름(review_type 전달) → Task 2. ✓
- 분기 렌더 + "결과 남기기"/뒤로가기/제목 제외 → Task 3 Step 2 + Step 5 검증. ✓
- 회귀(기존 카드 화면 동일) → Task 1 Step 5. ✓
- 검증 두 시나리오 → Task 3 Step 4·5. ✓

**Placeholder scan:** 모든 코드 스텝에 실제 코드/명령/기대값 포함. SQL의 런타임 ID는 조회 쿼리로 대체(플레이스홀더 아님). ✓

**Type consistency:** `ChainDetailData.review = { reviewType: string \| null; payload: ReviewPayload \| ProjectCardPayload }` — Task 2 정의와 Task 3 소비(`review.reviewType`, `review.payload as ...`) 일치. `ProjectCardMeta`/`ProjectCardBlocks` props(`{ payload: ProjectCardPayload }`) — Task 1 정의와 Task 3 사용 일치. ✓
