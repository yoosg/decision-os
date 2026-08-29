## Task 2 Report: ReviewType 유니온 + 판별 유니온으로 캐스트 제거

### Status: DONE

### What Changed

**Files created:**
- `web/src/components/home/review/review-types.ts` — `ReviewType = "research" | "project_card"` union + `isProjectCard()` type guard

**Files modified:**
1. `web/src/components/history/chain-detail-content.tsx`
   - `ChainDetailData.review` changed from `{ reviewType: string | null; payload: ReviewPayload | ProjectCardPayload }` to discriminated union: `{ reviewType: "project_card"; payload: ProjectCardPayload } | { reviewType: "research"; payload: ReviewPayload } | null`
   - Render branch casts `as ProjectCardPayload` and `as ReviewPayload` removed — TypeScript now narrows via the discriminant

2. `web/src/app/(app)/history/chain/[signalId]/page.tsx`
   - `reviewType` now computed as literal `"project_card" | "research"` (ternary, no raw string passthrough)
   - One boundary cast `{ reviewType, payload } as ChainDetailData["review"]` retained (raw DB row origin)

3. `web/src/components/home/review/review-page-content.tsx`
   - Imported `ReviewType` from `./review-types`
   - `ReviewUIState.reviewType` changed from `string | null` to `ReviewType | null`
   - `InitialReview.reviewType` changed from `string | null` to `ReviewType | null`
   - Line ~97 realtime cast updated: `as string | null | undefined` → `as ReviewType | undefined`

4. `web/src/app/(app)/home/review/[signalId]/page.tsx` (discovered during tsc — not in brief)
   - Own local `InitialReview` type updated: `reviewType?: string | null` → `reviewType?: ReviewType | null`
   - DB boundary cast updated to `as ReviewType | undefined`

5. `web/src/app/(app)/queue/review/[signalId]/page.tsx` (discovered during tsc — not in brief)
   - Same changes as home review page (parallel structure)

### tsc Result

`cd web && npx tsc --noEmit` → **PASS (exit 0, 0 errors)**

### Grep Verification

`grep -n "as ProjectCardPayload\|as ReviewPayload" web/src/components/history/chain-detail-content.tsx` → **no output (casts gone)**

### Files Changed

| File | Action |
|------|--------|
| `web/src/components/home/review/review-types.ts` | Created |
| `web/src/components/history/chain-detail-content.tsx` | Modified (discriminated union, casts removed) |
| `web/src/app/(app)/history/chain/[signalId]/page.tsx` | Modified (boundary cast pattern) |
| `web/src/components/home/review/review-page-content.tsx` | Modified (ReviewType import + type updates) |
| `web/src/app/(app)/home/review/[signalId]/page.tsx` | Modified (ReviewType boundary) |
| `web/src/app/(app)/queue/review/[signalId]/page.tsx` | Modified (ReviewType boundary) |

### Commit

SHA: `1658dd1`
Subject: `refactor(web): ReviewType 판별 유니온 도입, 카드 렌더 캐스트 제거`

### Self-Review

- Render-layer casts removed: YES (`chain-detail-content.tsx` is cast-free, compiler narrows via discriminant)
- Boundary casts: `chain/[signalId]/page.tsx` has one `as ChainDetailData["review"]`; `home/review/[signalId]/page.tsx` and `queue/review/[signalId]/page.tsx` each have `as ReviewType | undefined` — all DB boundary files (correct pattern)
- Behavior change: NONE — discriminated union is compile-time only; runtime values unchanged
- Union exhaustive: `ReviewType = "research" | "project_card"` covers both branches

### Concerns

Two additional page files (`home/review/[signalId]/page.tsx` and `queue/review/[signalId]/page.tsx`) required updating beyond the brief's listed files. These were necessary because they define their own `InitialReview` types that feed into `ReviewPageContent`'s now-stricter prop type. Changes are consistent with the brief's intent — DB boundary casts remain in DB boundary files only.

## Fix: boundary normalization

### What Changed

1. **`web/src/components/home/review/review-types.ts`** — Added `toReviewType(v: string | null | undefined): ReviewType | null` normalizer that performs real runtime narrowing (checks `=== "project_card"` or `=== "research"`, returns `null` for all unknown/null values).

2. **`web/src/app/(app)/home/review/[signalId]/page.tsx`** — Replaced bare cast `(reviewRow.result?.review_type as ReviewType | undefined) ?? null` with `toReviewType(reviewRow.result?.review_type)`. Added `toReviewType` import.

3. **`web/src/app/(app)/queue/review/[signalId]/page.tsx`** — Same replacement as home page (parallel structure). Added `toReviewType` import.

4. **`web/src/components/home/review/review-page-content.tsx`** — Replaced bare cast `(data?.result?.review_type as ReviewType | undefined) ?? null` at realtime subscription handler (~line 99) with `toReviewType(data?.result?.review_type)`. Added `toReviewType` import.

`chain/[signalId]/page.tsx` was NOT touched (already reviewed and correct per brief).

### tsc Result

`cd web && npx tsc --noEmit` → **PASS (exit 0, 0 errors)**

### Grep Verification

`grep -rn "as ReviewType" web/src` → **no output (all three bare casts gone)**
