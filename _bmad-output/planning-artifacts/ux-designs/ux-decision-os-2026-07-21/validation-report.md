# Validation Report — Decision OS UX Spines
**Synthesized from:** Reviewer A (Rubric Walker) · Reviewer B (Accessibility) · Reviewer C (Fintech/Insurance Adversary)
**Date:** 2026-07-21
**Workspace:** `_bmad-output/planning-artifacts/ux-designs/ux-decision-os-2026-07-21/`

---

## Summary

| Severity | Reviewer A | Reviewer B | Reviewer C | Unique (after dedup) |
|---|---|---|---|---|
| **Critical** | 4 | 5 | 6 | **12** |
| **Major** | 12 | 16 | 14 | **28** |
| **Minor** | 12 | 11 | 10 | **23** |
| **Nice to Have** | 3 | 5 | 0 | **7** |

Cross-cutting issues (appearing in 2+ reviewers) are marked **[CROSS]** and treated as highest priority within their severity tier.

---

## Critical Issues

### CRIT-01 · Context Sticky Bar: recommendation text visible before evidence is read **[CROSS B+C]**

The bar always shows the recommendation summary ("추천: 실손보험 청구 권장") in both disabled and enabled states. A user who opens the Review screen sees the conclusion before reading a single sentence of evidence. The disabled CTA is the friction mechanism, but the recommendation is already served — making it a guarantee anchor, not a prompt to read. Separately (Reviewer B), the disabled→enabled state transition has no `aria-live` announcement, no `aria-disabled="true"` on the CTA, no `aria-describedby` linking the hint text, and the section-presence activation may never fire for screen reader users who navigate by virtual cursor without scrolling.

**Source:** B (Critical), C (Critical)
**Fix:**
- In the **disabled state**, replace recommendation text with neutral: "분석 내용을 먼저 읽어 주세요." Reveal recommendation text only when CTA activates.
- Add `aria-disabled="true"` on the disabled CTA (not `disabled` attribute, which removes focus).
- Set `aria-label="채택 — 비활성화됨. 추천 근거를 먼저 확인해 주세요"` on disabled CTA.
- Give hint text an `id`; add `aria-describedby="[hint-id]"` to the CTA.
- Add `aria-live="polite"` on a visually hidden status region that announces activation: "청구 준비 시작 버튼을 사용할 수 있습니다."
- Define activation trigger as "section heading or first meaningful element has received focus OR entered the viewport — whichever comes first," so screen reader virtual-cursor traversal counts.
- In the Context Sticky Bar DOM, place focus-order position after the last content section via `tabindex` ordering, even though it is visually fixed. Document this as an implementation requirement.

---

### CRIT-02 · Memory is immutable with no correction or deletion path **[C]**

EXPERIENCE.md states "This chain is immutable once written. The user does not manage or edit the Memory Timeline items directly." OCR errors that the user missed become permanent context for all future AI Reviews on the same Project. Under 개인정보보호법 Article 36, users have the right to correct their personal data. An immutable memory chain may be legally non-compliant in addition to degrading AI Review quality over time.

**Source:** C (Critical)
**Fix:**
- Users can **flag** a Memory Timeline item as "incorrect" — this creates a correction note (not an in-place edit) appended to the chain, visible in the timeline. The correction note feeds the AI context going forward.
- Full **deletion** of individual items must be available under the 개인정보보호법 right to erasure.
- Add state pattern for Memory Timeline: "flagged / correction pending" state with visual indicator.
- Specify this flow in EXPERIENCE.md under Memory States and Memory Timeline Item component.

---

### CRIT-03 · No mandated legal disclaimer text on Review or Checklist screen **[C]**

The spec contains no persistent, mandatory UI element carrying a legal disclaimer. "AI 분析 결과는 참고 정보입니다" appears only in a microcopy preference table as a "Do" example — not as a required component on any screen. Under 보험업법 Article 83, "청구 권장" language from an AI system acting as insurance solicitation is a criminal exposure risk. Under 금융소비자보호법 Article 19, inducing action without adequate disclosure of non-professional status is a fair-treatment violation.

**Source:** C (Critical)
**Fix:**
- Specify a mandatory, non-dismissable disclaimer line as a named component (e.g., `LegalDisclaimerBar`) pinned to the Review 상세 screen and the 서류 Checklist screen.
- Mandatory copy: "본 분석은 참고 정보이며, 보험사의 최종 심사 기준과 다를 수 있습니다. Decision OS는 보험 모집 또는 중개 행위를 하지 않습니다."
- Rename Decision CTA from "채택" to "채택 — 직접 청구" and add a single-sentence header on the Checklist screen: "다음 단계는 보험사 앱 또는 창구에서 직접 진행합니다. Decision OS는 청구 절차에 관여하지 않습니다."
- Add `LegalDisclaimerBar` to DESIGN.md frontmatter components and add its behavioral spec to EXPERIENCE.md Component Patterns.

---

### CRIT-04 · "Conclusion first" Review titles create false certainty anchor **[C]**

Voice principle "Conclusion first" produces Review titles like "보험금 청구가 가능합니다" — a declarative assertion the AI is not legally or factually authorized to make. This is the first thing users read. Any subsequent disclaimer is fighting against a cognitive anchor formed in the first 300ms of screen load. Under 금융소비자보호법 Article 19, the distinction between "informing of possibility" and "inducing to act" is context- and prominence-dependent.

**Source:** C (Critical)
**Fix:**
- Change the voice constraint from "Conclusion first" to "Possibility first": require AI-generated Review titles to use possibility framing ("청구 가능성이 있습니다", "해당될 수 있습니다", "2건 검토됨") rather than declarative completion ("가능합니다", "해당됩니다").
- Add this as a hard constraint in the AI title generation spec — not a preference, a gate.
- Update the microcopy table in EXPERIENCE.md Voice and Tone to reflect this rule.

---

### CRIT-05 · Denied claim outcome has no UX treatment **[C]**

The Outcome input screen records "거절" as a valid result, but no copy or screen is specified for the user's next moment: "AI가 가능하다고 했는데 왜 거절됐나요?" A user who acted on "청구 가능합니다" and received a denial experiences AI-caused financial disappointment with no explanation, no context, and no repair path. In Korean fintech, one poorly handled rejection on the first claim becomes the app review that poisons market entry.

**Source:** C (Critical)
**Fix:**
- Add a **거절 Outcome screen variant** with contextual copy: "이번 청구가 거절됐습니다. AI 분析은 참고 정보이며, 보험사의 심사 기준에 따라 결과가 다를 수 있습니다. 거절 사유를 기록하면 다음 분析에 반영됩니다."
- Add a "거절 사유 입력" field — optional but prominent — that feeds Memory context.
- Add state pattern entry in EXPERIENCE.md: Outcome — 거절 path.

---

### CRIT-06 · 병원 방문 직접 등록: zero flow coverage and zero state coverage **[A]**

This surface is listed in the IA inventory (row 9), referenced in the + Bottom Sheet option list, and named as the OCR failure path destination ("routes to 병원 방문 직접 등록 폼"). It has zero numbered flow steps, no state pattern, and no field-list spec. A developer cannot implement this form from the current docs.

**Source:** A (Critical × 2 — Flow Coverage + State Coverage)
**Fix:**
- Add a Flow 1b with numbered steps for the direct registration path (minimum: 병원명, 진료일, 진료비, 진료 유형 fields), or add a dedicated state/component entry.
- Add state patterns: empty form (focus on first field), validation error, submit-loading, success.
- Specify whether the field set differs from OCR extraction, or uses the same schema.

---

### CRIT-07 · Contextual Chat: zero behavioral spec, zero state coverage **[A]**

Present in the IA inventory (row 19) and the navigation rule ("context-aware entry from Review/Project/Event screens only") but has no Component Pattern section, no State Pattern entry, no protagonist flow, and no behavioral spec (how it opens, how context is passed, how it closes, how it handles empty conversation history).

**Source:** A (Critical × 2 — Flow Coverage + State Coverage)
**Fix:**
- Add a Component Pattern section specifying entry trigger, context-passing mechanism, and dismiss path.
- Add State Patterns: empty (no prior context), in-conversation, post-conversation navigation.
- Add a flow snippet with a protagonist showing at minimum one entry → exchange → dismiss sequence.

---

### CRIT-08 · `text-secondary` (#6B7280) contrast fails WCAG AA on card surfaces **[B]**

`#6B7280` on `surface-card` (#F2F2F2) = ~3.5:1. `#6B7280` on Honest Box background (#F5F5F5) = ~4.0:1. Both fail AA (4.5:1 required) for text below 18pt. Affected elements: Inbox Card subtitle (13px), OCR Field Row label (11px), Memory Timeline type label (10px), Bottom Sheet sub-label (13px), and the entire Honest Box body — which is the AI uncertainty disclosure, where low-vision users most need to read.

**Source:** B (Critical)
**Fix:**
- Darken `text-secondary` to `#595D6A` (~4.6:1 on surface-card) or add a separate `text-on-card` token at that value.
- Update the `text-secondary` hex in DESIGN.md frontmatter and propagate to all prose references.
- This single token change resolves the majority of contrast failures in the product.

---

### CRIT-09 · `text-tertiary` (#9CA3AF) contrast fails AA on all surfaces **[B]**

~2.4:1 on `surface-card` (#F2F2F2), ~2.9:1 on `surface-base` (#FFFFFF). Both fail AA. Used for timestamps, placeholders, and timeline dates — information that carries meaning (dates in Memory Timeline are required to understand the sequence of events).

**Source:** B (Critical)
**Fix:**
- Use `text-secondary` (#6B7280, or the corrected `#595D6A` per CRIT-08) on `surface-base` (≥4.5:1) for all date/timestamp text.
- Alternatively, provide dates as part of the card's composite `aria-label` so that even if visual contrast is low, the information is accessible to screen readers.

---

### CRIT-10 · White text on disabled CTA (`#D1D1D1` bg) = ~1.5:1 **[B]**

The WCAG inactive UI exemption from contrast requirements (SC 1.4.3) applies only when the disabled state is communicated through other means (`aria-disabled`, accessible label). Until CRIT-01 aria fixes are confirmed in place, white-on-#D1D1D1 has no exemption and fails at any text size.

**Source:** B (Critical)
**Fix:**
- Change disabled CTA label text color to `text-primary` (#0D0D0D) on `#D1D1D1` background: ~8.5:1, clearly readable.
- After CRIT-01 aria fixes are confirmed, the exemption becomes valid — but using `text-primary` is safer and costs nothing visually.
- Also add a non-color disabled signal: a lock icon at label-left, or dashed instead of solid border.

---

### CRIT-11 · Context Sticky Bar at max Dynamic Type crowds the viewport **[B]**

At iOS Dynamic Type "AX5" (max accessibility size), system fonts render at ~2.5–3× base. The bar contains 4 stacked elements (context label, recommendation/neutral text, primary CTA, secondary pills + hint text). At max Dynamic Type on a 375px viewport, the bar can occupy >60% of the viewport, leaving <40% for Review content — the content the user is supposed to read before the CTA enables.

**Source:** B (Critical)
**Fix:**
- Cap bar at `max-height: 40vh`, or specify: at Dynamic Type ≥ 150%, recommendation/neutral text truncates to one line with "…" and the hint text collapses.
- Truncated text must still be accessible: full text available via `aria-label` on the button.
- Add this as an explicit rule in the ContextStickyBar component spec in EXPERIENCE.md.

---

### CRIT-12 · Short Review exception: no content-type gate, bypasses Review Before Action **[C]**

"If the Review content fits in a single viewport without scrolling, the bar is enabled from the moment the screen loads" (EXPERIENCE.md). No prohibition on consequential claim Reviews being classified as "short." The AI backend controls this gate. A terse Review ("청구 가능 — 실손 해당, 서류 2건 필요") that fits one viewport allows the user to tap 채택 in under 3 seconds — bypassing the entire Review before Action principle architecturally.

**Source:** C (Major in Section 5, top-5 must-fix)
**Fix:**
- Short Review exception is permitted only if: (a) the Review contains **no HonestBox entry** AND (b) the claim amount is **below a defined threshold** (propose 50,000원 as starting point).
- For all other Reviews, section-scroll activation is required regardless of Review length.
- Add this gate constraint to the Short Review Exception spec in EXPERIENCE.md.

---

## Major Issues

### MAJ-01 · Honest Box: no graduated severity between low- and high-consequence uncertainty **[C]**

All HonestBox entries carry equal visual weight ("direct, not apologetic"). A policy-clause gap (where the AI cannot verify the specific clause governing the claim) and an unconfirmed hospital name are treated identically. Users will habituate to HonestBox as boilerplate.

**Source:** C (Major)
**Fix:** Add a visual weight differentiator: high-consequence entries (policy-clause gaps, coverage-amount uncertainty) use `status-warning` token for the HonestBox border or icon; standard entries use the current neutral treatment.

---

### MAJ-02 · Honest Box positioned last — uncertainty trails conclusion and evidence **[C]**

HonestBox is always the last section before the data timestamp. Users who scroll to the scroll-activation threshold may tap 채택 with no meaningful engagement with the HonestBox. Uncertainty should qualify the recommendation, not trail it.

**Source:** C (Major)
**Fix:** Move HonestBox to immediately after the Recommendation section, before Evidence. Update section order in EXPERIENCE.md Key Flows and State Patterns, and update the section-presence activation trigger list to match the new order.

---

### MAJ-03 · No Korean insurance anxiety treatment: premium retaliation fear **[C]**

"청구하면 다음 갱신 때 보험료가 오르나요?" is the primary source of claim anxiety for Korean users. The spec prohibits urgency language and states "Minimize anxiety," but this specific fear — which causes real false negatives (users not claiming what they're owed) — is completely unaddressed.

**Source:** C (Major)
**Fix:** The Review 상세 spec must include a mandatory field for premium impact: either a factual AI statement ("이 상품의 청구 이력은 갱신 보험료에 영향을 주지 않습니다" or "영향을 줄 수 있습니다") or an HonestBox entry acknowledging the AI cannot determine this. Silence on this question amplifies anxiety.

---

### MAJ-04 · Document checklist: no guidance for missing documents, no escape route **[C]**

If a user realizes on the checklist screen that a required document is unavailable (hospital closed, record retention period passed), there is no guidance path. The checklist sits in a "결과 대기" state with no exit other than abandoning the flow.

**Source:** C (Major)
**Fix:**
- Each checklist item must have an expandable "이 서류를 구하기 어렵다면" help row specifying alternatives or consequence of omission.
- Add a secondary CTA on the Checklist screen: "서류 준비가 어려워요" → routes to Contextual Chat on this screen. This is a valid contextual Chat entry point (per the no-floating-FAB rule).

---

### MAJ-05 · Analysis timeout and failure state not defined **[C]**

The spec defines no maximum analysis window, no failure state for background job failures, and no error notification when analysis never completes after the user closes the app. A user who confirmed an Event, closed the app, and returns an hour later finds no Review card and no error — no mental model for what happened.

**Source:** C (Major)
**Fix:**
- Define a maximum analysis window (e.g., 5 minutes).
- If exceeded: push notification "분析을 완료하지 못했습니다. 앱에서 확인해 주세요" + Inbox error card with "다시 분析하기" CTA.
- Add to State Patterns table: Review 생성 실패 (timeout/error state) with Inbox treatment and recovery path.

---

### MAJ-06 · CODEF partial success: analysis completeness not disclosed **[C]**

CODEF returning data for 3 of a user's 5 policies produces an AI Health Score and initial Review based on incomplete coverage data, with no indication to the user. A user with an uncaptured critical illness rider may decide not to claim because "AI said no coverage" — when the AI simply didn't have access to that policy.

**Source:** C (Major)
**Fix:**
- Integration result screen must display "N건 연동됨 / 예상 M건" count.
- HonestBox in the initial Review must contain a mandatory entry: "연동된 보험 정보에 기반한 분析입니다. 미연동 보험이 있는 경우 해당 보장은 포함되지 않습니다."
- Add to the CODEF onboarding State Patterns: partial-success state.

---

### MAJ-07 · CODEF stale data: no last-updated timestamp, no staleness warning **[C]**

No specified refresh cadence, no "데이터 마지막 업데이트" timestamp visible on the Insurance Project screen. If a cancelled policy still appears as active in 내보험다보여, the AI may generate a "청구 가능합니다" Review for coverage that no longer exists.

**Source:** C (Major)
**Fix:**
- Insurance Project 상세 must show "보험 정보 마지막 업데이트" timestamp with a manual "다시 가져오기" action.
- If data is older than 30 days, show a warning badge on the Health Score Card.
- Add these as state rows in Insurance Project 상세 State Patterns.

---

### MAJ-08 · OCR per-field plausibility validation missing **[C]**

A smudged receipt digit (840,000원 instead of 84,000원) is OCR-extracted and the "confirmed" checkmark rewards confirmation without verifying plausibility. The AI Review is then generated against a 10× inflated medical expense.

**Source:** C (Major)
**Fix:** Add per-field inline warning when value exceeds a plausibility threshold (e.g., 진료비 > 500,000원 for an outpatient receipt): "진료비가 일반적인 외래 진료비보다 높습니다. 금액을 다시 확인해 주세요." Do not block submission — warn only. Add to OCR Field Row component spec.

---

### MAJ-09 · Manual insurance entry: no visual distinction from CODEF-verified data **[C]**

A user who manually entered incorrect policy details months ago receives AI Reviews based on that wrong data. The Memory is immutable (per CRIT-02), so errors compound. No visual tag distinguishes manually-entered from CODEF-verified policies in the Insurance Project screen or in Reviews.

**Source:** C (Major)
**Fix:**
- Insurance Project 상세 must show policy-level tags: "직접 입력" vs "연동 확인".
- Reviews based on manually-entered data must include a mandatory HonestBox entry: "보장 정보는 직접 입력된 내용으로, 검증되지 않았습니다."

---

### MAJ-10 · 보류 decision: no time-stamped indicator, claim window awareness absent **[C]**

A user who hits 보류 on a claim Review may forget it indefinitely. Claim submission windows are 3 years, but hospital record availability and diagnostic certificate windows are much shorter. The spec prohibits re-engagement push beyond one follow-up but has no time-stamped reminder on the Inbox card.

**Source:** C (Major)
**Fix:**
- Inbox card for 보류 Reviews: show "보류한 날로부터 N일째" time indicator.
- After 90 days: one-time informational push (not urgency) "보류 중인 보험 청구 Review가 있습니다."

---

### MAJ-11 · 무시 decision: no post-tap signal that action is reversible **[C]**

"무시" archives the Review and removes it from the Inbox with no confirmation dialog and no visible recovery path. Users who intended 보류 but tapped 무시 (two adjacent ghost pills) have no on-screen indication the action is not destructive. Additionally, the two secondary CTAs are equivalent-weight ghost pills despite having very different consequences.

**Source:** C (Major)
**Fix:**
- After 무시 tap: single-line non-blocking toast (3 seconds): "이 Review는 메모리에서 다시 볼 수 있습니다."
- "무시" should be lower visual prominence than "나중에 검토": text-only (no pill border) to reduce accidental selection.

---

### MAJ-12 · Health Score: no plain-language interpretation of score **[C]**

The Health Score (0–100 AI integer) is presented without explaining what the number means for the user's actual insurance situation. A score of 82 could mean "well-covered," "overpaying," or "major coverage gaps" — the user cannot tell which. If users anchor on "82 is pretty good" and a subsequent Review reveals major gaps, the score's prior reassurance damages trust.

**Source:** C (Major)
**Fix:**
- The 보험 건강도 결과 screen must include a 2–3 line AI-generated plain-language interpretation below the Health Score Card (not a static template).
- Health Score disclaimer must include: "보험업법상 인가된 평가 지표가 아닙니다."
- Score methodology accessible on demand via an info icon.

---

### MAJ-13 · Inbox Full List: no flow, no state, N items threshold unresolved **[A]**

Referenced in the InboxCard component spec ("Where: Home Inbox section and Inbox Full List screen") but no flow reaches it, no state patterns cover it (empty, full, paginated), and the "전체 보기" trigger threshold N is undefined.

**Source:** A (Major)
**Fix:** Specify N; add empty/populated/paginated state patterns; add a flow step showing the 전체 보기 → Inbox Full List navigation.

---

### MAJ-14 · Profile / Integration screen: no flow, no state **[A]**

IA inventory lists purpose ("Integration management, notification settings, data/account management") but no flow, no state pattern, and no component spec. Notification Patterns references "re-requested on Home after denial" but does not specify what happens in Profile for the re-enable path.

**Source:** A (Major)
**Fix:** Add state pattern rows: connected, disconnected, re-enable notification path.

---

### MAJ-15 · 수동 보험 입력 screen: no steps, no states **[A]**

Referenced as a Flow 2 failure-path destination ("수동 보험 입력 폼 (보험사 / 상품명 / 보험료 / 보장)") with no numbered steps, no state patterns (0 policies added, 1+ policies), and minimum field spec only as a parenthetical.

**Source:** A (Major)
**Fix:** Add numbered steps to Flow 2 failure path, or add a State Pattern row for this screen covering: empty, partially filled, submitted states.

---

### MAJ-16 · HonestBox background (#F5F5F5) not a named token **[A]**

Raw hex specified in both DESIGN.md frontmatter component and prose. Theming and dark mode cannot reference an unnamed hex.

**Source:** A (Major)
**Fix:** Add `surface-honest-box: "#F5F5F5"` to DESIGN.md colors frontmatter; replace raw hex in component spec and prose with `{colors.surface-honest-box}`.

---

### MAJ-17 · `status-positive-bg` defined but never referenced in EXPERIENCE.md **[A]**

The "채택 완료" / "지급 완료" badge fill is underdefined behaviorally.

**Source:** A (Major)
**Fix:** Add a token reference in the InboxCard or Decision Loop Patterns section specifying badge fill for positive completion states.

---

### MAJ-18 · PlusBottomSheet vs "+ Bottom Sheet" naming mismatch **[A]**

DESIGN.md frontmatter uses `PlusBottomSheet` (PascalCase); EXPERIENCE.md section header uses `+ Bottom Sheet`. Confuses developers matching section headers to token references.

**Source:** A (Major)
**Fix:** Rename EXPERIENCE.md section header to `### PlusBottomSheet (+ Bottom Sheet)` or add a note that the display name is "+ Bottom Sheet."

---

### MAJ-19 · EventCandidateCard: Inbox variant vs confirmation screen variant not distinguished **[A]**

The component behavioral spec does not cover its two contexts: (1) Inbox appearance with "확인 필요" badge, and (2) standalone Event 후보 확인 screen with full event data preview. A developer building both screens cannot tell if it's one component with two states or two separate layouts.

**Source:** A (Major)
**Fix:** Add a "where: two contexts" note to the EventCandidateCard component spec distinguishing Inbox variant (badge-only summary) from confirmation screen variant (full preview).

---

### MAJ-20 · Decision + Checklist: partial-completion state not specced **[A]**

If a user partially checks items and closes the app, does the checklist persist state? Is there a badge change? No intermediate state is defined.

**Source:** A (Major)
**Fix:** Add: "Checklist — partially checked: state persists across sessions; no badge change until all items checked or Outcome submitted."

---

### MAJ-21 · Insurance Project 상세: no state patterns at all **[A]**

Wireframe shows a populated state (Screen 10) but no state table row exists for this surface: no empty/no policies state, no Health Score loading state, no stale data state.

**Source:** A (Major — also overlaps MAJ-07 for staleness)
**Fix:** Add state rows: (a) empty / no policies linked, (b) Health Score loading, (c) Health Score stale (connects to MAJ-07 staleness fix).

---

### MAJ-22 · 분析 중 screen: completion transition not specced **[A]**

When the Review appears while the user is still viewing the 분析 중 screen — does it auto-navigate to Home, or require a tap? No transition state specified.

**Source:** A (Major)
**Fix:** Add sub-state: "Analysis completes while screen is open → CTA changes to '새 Review 확인하기', navigates to Home." Or specify the screen is one-way (navigate only on tap or dismissal). Pick one.

---

### MAJ-23 · ia-2026-07-21.excalidraw not linked from either spine **[A]**

Exists in `.working/` but is not referenced in DESIGN.md or EXPERIENCE.md.

**Source:** A (Major)
**Fix:** Add link in EXPERIENCE.md § Information Architecture: "See also: `.working/ia-2026-07-21.excalidraw` for visual IA map."

---

### MAJ-24 · `sources:` entries are descriptive labels, not resolvable paths **[A]**

Both spines list `.memlog.md`, `prd.md`, `wireframes-key-screens-2026-07-21.html` without directory anchors. A reader or automated tool cannot locate these without knowing repo root conventions.

**Source:** A (Major)
**Fix:** Use repo-root-relative paths: `_bmad-output/planning-artifacts/ux-designs/ux-decision-os-2026-07-21/.working/wireframes-key-screens-2026-07-21.html`; `_bmad-output/planning-artifacts/ux-designs/ux-decision-os-2026-07-21/.memlog.md`; etc.

---

### MAJ-25 · Ghost pill CTAs (나중에 검토 / 무시) may fall below 44pt height **[B]**

At typical pill padding (12px top/bottom) with 13px label, the pill renders ~37–39pt — below the 44pt minimum. The spec states ≥ 44pt broadly but does not explicitly confirm these secondary pills.

**Source:** B (Major)
**Fix:** Specify `min-height: 44px` on secondary ghost pill CTAs. Confirm 12px gap between the two pills.

---

### MAJ-26 · Checklist items: no min-height specified **[B]**

A checkbox row with 13px label at default padding can fall below 44pt. Checkbox state is a primary interaction.

**Source:** B (Major)
**Fix:** Specify `min-height: 44px` on each checklist item row; tap target encompasses the entire row (not just the checkbox element).

---

### MAJ-27 · `status-warning` (#D97706) on white = ~3.0:1, fails AA **[B]**

Used for "갱신 임박" indicators. Fails AA for normal text.

**Source:** B (Major)
**Fix:** Darken to `#B45309` (~4.7:1 on white), or ensure warning state is never conveyed by text color alone (icon + badge text).

---

### MAJ-28 · OCR Field Row confirmed state: checkmark is color-only differentiator **[B]**

A green checkmark vs. gray checkmark on a gray card surface may not be distinguishable for deuteranopia users (~8% of Korean males). The spec states "no information conveyed by color alone" but the "transparent border + status-positive checkmark" removes the one non-color shape cue.

**Source:** B (Major)
**Fix:** Confirmed field label changes from "진료비" to "진료비 ✓" in visible text (with `aria-label` "진료비 — 확인됨"), or a border/outline appears on confirmed fields.

---

## Minor Issues

### MIN-01 · 카메라 / 영수증 촬영: no permission-denied or camera-unavailable state **[A]**

OCR failure path covers post-capture failures but not camera-access failures.

**Fix:** Add state pattern row: "카메라 권한 거부 → 설정으로 이동" fallback.

---

### MIN-02 · 보험 건강도 결과 screen: post-onboarding accessibility unclear **[A]**

IA suggests onboarding-only, but Project tab shows HealthScoreCard — whether this screen is accessible post-onboarding is ambiguous.

**Fix:** Clarify: one-time onboarding screen, OR persistent screen reachable from 프로젝트 탭. Update IA inventory accordingly.

---

### MIN-03 · OCR partial-extraction: no state for a field returning blank **[A]**

Spec says "fields extracted in MVP" but no state for a field the OCR cannot parse.

**Fix:** Add "blank/unparsed field" state to OCR Field Row: shows field label + empty value + edit icon, auto-focuses.

---

### MIN-04 · Home empty state illustration contradiction **[A]**

State Patterns says "No illustration" for empty inbox; wireframe Screen 2 shows a `✓` emoji with `empty-icon` CSS class.

**Fix:** Either remove the icon from the wireframe or change State Patterns to permit a minimal icon. Clarify intent; make spine and wireframe consistent.

---

### MIN-05 · Bottom Sheet open/close animation not covered by Reduce Motion spec **[B]**

Reduce Motion covers card entrance and dot pulse but not the Bottom Sheet slide-up — the most common motion-triggered complaint in Korean consumer apps.

**Fix:** Add to Reduce Motion spec: "Bottom Sheet open/close: replace slide-up with instant appear/disappear when `prefers-reduced-motion` is set."

---

### MIN-06 · CODEF loading animation not covered by Reduce Motion spec **[B]**

The "약 30초 소요됩니다" loading state has an animated indicator not covered by the Reduce Motion spec.

**Fix:** Extend Reduce Motion rule globally: "All animated loading indicators replace their animation with a static indicator when `prefers-reduced-motion` is set."

---

### MIN-07 · `error` (#EF4444) on `error-bg` (#FEF2F2) at 11px: 3.9:1, fails AA for small text **[B]**

**Fix:** Darken error hint text to `#DC2626` (~4.7:1 on `#FEF2F2`), or use `text-primary` (#0D0D0D) for hint text color.

---

### MIN-08 · Status-positive badge text on status-positive-bg: 3.1:1, fails AA for 10px badge **[B]**

**Fix:** Use `text-primary` (#0D0D0D) for badge label text; retain green background as color signal only.

---

### MIN-09 · No global line-height rule for Korean text below 16px **[B]**

Korean characters can clip at line-height < 1.3. Some field values and card titles have no line-height spec.

**Fix:** Add global rule to DESIGN.md Typography: "all Korean body text < 16px: `line-height: 1.5` minimum; card title text ≥ 16px: `line-height: 1.4` minimum."

---

### MIN-10 · Decision CTAs must be `<button>` elements — semantic role not specified **[B]**

If secondary CTAs ("나중에 검토", "무시") are implemented as `<div>` or `<a>`, they will not announce as interactive in TalkBack's default mode.

**Fix:** Specify all three Decision CTAs must use `<button>` element.

---

### MIN-11 · Outcome input cards: semantic role not defined **[B]**

Option cards (지급 완료 / 거절됨 / 추가 서류 요청) have no role specified. If implemented as `<div>` tap targets, VoiceOver/TalkBack will not announce selected state.

**Fix:** Implement as `role="radio"` in a `role="radiogroup"` labelled "보험금 지급 결과", or as `<input type="radio">` with styled labels.

---

### MIN-12 · Memory Timeline Outcome dots: color-only differentiator **[B]**

Positive outcome = status-positive fill, pending = text-tertiary fill. No text label or shape change distinguishes them for color-blind users.

**Fix:** Add type label or icon beside the Outcome dot (e.g., "₩" for paid, "?" for pending, "✕" for rejected).

---

### MIN-13 · Upward arrow glyph in hint text read as "위쪽 화살표" by VoiceOver **[B]**

Interrupts sentence flow in Korean.

**Fix:** Wrap: `<span aria-hidden="true">↑</span>`.

---

### MIN-14 · Currency formatting: ₩N,NNN read inconsistently by Korean VoiceOver **[B]**

Some readers pronounce it "원72,000원" (double unit); others skip ₩.

**Fix:** Specify `aria-label` pattern for all monetary amounts: e.g., `<span aria-label="칠만 이천 원">₩72,000</span>`. List this in EXPERIENCE.md Accessibility Floor.

---

### MIN-15 · No `lang="en"` policy for English words in Korean body copy **[B]**

"Review," "CODEF," "ID," "Memory," "NEW," "OS" appear in Korean body copy. Korean screen readers mispronounce these using Korean phoneme rules without `lang="en"` inline.

**Fix:** Specify global rule: any English word rendered within Korean body copy carries `lang="en"` on its inline element. List the exhaustive set of English-origin proper nouns used in the product.

---

### MIN-16 · `보류` badge change timing ambiguous **[A]**

State Patterns says "badge changes to '보류'" but does not specify trigger: immediately on tap, or on next Inbox load?

**Fix:** Specify: badge changes optimistically on tap (immediate UI update).

---

### MIN-17 · `무시` Decision dot color not specified **[A]**

Memory Timeline Item shows Event/Review/Decision/Outcome dot types; a "무시" Decision item has no dot color spec (cannot be status-positive).

**Fix:** Assign `text-secondary` (#6B7280 / corrected per CRIT-08) as the dot fill for 무시 Decisions and document in DESIGN.md Components → MemoryTimelineItem.

---

### MIN-18 · Outcome confirmation CTA microcopy undefined **[A]**

Wireframe (Screen 9) shows "기록하기"; Flow 1 Step 12 implies "확인." No microcopy table entry for this CTA.

**Fix:** Add to the microcopy table: Outcome 확인 primary CTA = "기록하기". Align wireframe and spine.

---

### MIN-19 · OCR disclaimer position contradiction **[A]**

DESIGN.md and EXPERIENCE.md both specify disclaimer "above the field list." Wireframe Screen 5 renders it below the last field row and above the CTA. Contradiction will cause implementation divergence.

**Fix:** Move disclaimer div in wireframe to above the first form-field div, or update both spines to say "below fields, above CTA." Make spine + wireframe consistent.

---

### MIN-20 · Health Score: mandatory score methodology disclosure not specified **[C]**

If users share their score, it creates consumer expectations around a standardized metric that does not exist.

**Fix:** Score methodology must be disclosed on demand via info icon (already included in MAJ-12 fix).

---

### MIN-21 · Onboarding welcome heading implies deficiency **[C]**

"내 보험, 지금 제대로 알고 있나요?" presupposes ignorance, conflicting with "Minimize anxiety" principle.

**Fix:** Rephrase to "내 보험을 한눈에 정리해 드립니다."

---

### MIN-22 · "자동으로 가져오기" option does not explain what it actually does **[C]**

Users discover mid-flow that they are asked to input government portal credentials into a third-party app — a trust shock for security-conscious Korean users.

**Fix:** Add sub-label to the "자동으로 가져오기" option: "내보험다보여 계정으로 보험 목록을 조회합니다." Show before the user taps the option.

---

### MIN-23 · PRD content in EXPERIENCE.md prose (two instances) **[A]**

"Users who have a Review in their Inbox may read it, defer it, or dismiss it, but they cannot proceed to claim filing from the product without having opened the Review" (Decision Loop Patterns → Review Before Action) is a product requirement, not a UX design decision. Also: "What Decision OS is NOT" prose paragraphs are PRD/PRFAQ content.

**Fix:** Replace requirement statement with the UX constraint: "The Review 상세 screen has no 'skip' CTA. The only forward paths are ContextStickyBar and back navigation." Trim PRD paragraphs in Inspiration & Anti-patterns; keep only the Rejected patterns table.

---

## Nice to Have

### NTH-01 · Wireframe source paths lack `.working/` prefix **[A]**

`sources:` frontmatter lists filename only, not relative path.

**Fix:** Change to `.working/wireframes-key-screens-2026-07-21.html` in both frontmatters.

---

### NTH-02 · Bottom Sheet dismissal spec duplicated **[A]**

Appears in both Interaction Primitives → Bottom Sheet Dismissal and Component Patterns → + Bottom Sheet → Dismiss methods.

**Fix:** Collapse one to a cross-reference.

---

### NTH-03 · `section-gap-inner` not in frontmatter **[A]**

Layout & Spacing table distinguishes "header to first card: 10px" from "section-to-section: 20px," but frontmatter has only one `section-gap: "20px"` token.

**Fix:** Add `section-gap-inner: "10px"` or rename table rows to clarify both exist.

---

### NTH-04 · `status-warning` defined but never referenced in EXPERIENCE.md **[A]**

Token usage "갱신 임박" has no state pattern entry.

**Fix:** Either add a state pattern entry for renewal warning, or note the token as reserved for post-MVP.

---

### NTH-05 · Korean typeface stack not specified beyond system-ui **[B]**

On Android, `system-ui` may resolve to Noto Sans KR or NanumSquare depending on OEM skin, with meaningfully different metrics.

**Fix:** Consider specifying `'Apple SD Gothic Neo', 'Noto Sans KR', system-ui, sans-serif` for consistent Korean rendering.

---

### NTH-06 · Samsung TalkBack not named as explicit test target **[B]**

Samsung TalkBack has a custom touch exploration mode that can behave differently with `position: fixed` elements (the Context Sticky Bar). Samsung Galaxy is a dominant market segment in Korea.

**Fix:** Add Samsung Galaxy (Android 14+, One UI 6+) + Samsung TalkBack to the accessibility testing plan.

---

### NTH-07 · `status-uncertain` is stated three times; one instance suffices **[A]**

Defined in frontmatter comment, color table, and Color Usage Principles paragraph.

**Fix:** Keep color table definition; consolidate or remove the other two.

---

## Recommended Remediation Order

### Sprint 0 — Before any user-facing beta (regulatory and trust-critical)

| ID | Issue | Effort |
|---|---|---|
| CRIT-03 | Legal disclaimer component on every Review + Checklist screen | Low (new component + copy) |
| CRIT-04 | Review title voice: possibility-framing, not declarative | Low (copy constraint) |
| CRIT-01 | Context Sticky Bar: neutral disabled text + full aria package | Medium |
| CRIT-02 | Memory: correction flag + deletion path specified | Medium |
| CRIT-05 | Denied claim Outcome screen variant | Low (new screen + copy) |
| CRIT-12 | Short Review exception: content-type gate | Low (spec addition) |
| MAJ-02 | Honest Box moved before Evidence | Low (section reorder) |

### Sprint 1 — Before general availability (safety + contract coverage)

| ID | Issue | Effort |
|---|---|---|
| CRIT-06 | 병원 방문 직접 등록: full flow + state coverage | Medium |
| CRIT-07 | Contextual Chat: behavioral spec + state coverage | Medium |
| CRIT-08 | Darken text-secondary token to #595D6A | Low (token change) |
| CRIT-10 | Disabled CTA: text-primary label + non-color signal | Low |
| CRIT-09 | text-tertiary: use text-secondary on all meaningful text | Low |
| MAJ-01 | HonestBox graduated severity | Low |
| MAJ-03 | Premium retaliation anxiety field in Review spec | Low (copy addition) |
| MAJ-05 | Analysis timeout + failure state + Inbox error card | Medium |
| MAJ-06 | CODEF partial success disclosure | Low (spec + copy) |
| MAJ-07 | CODEF staleness: timestamp + staleness badge | Medium |
| MAJ-08 | OCR per-field plausibility warning | Medium |
| MAJ-28 | OCR confirmed state: non-color differentiator | Low |

### Sprint 2 — Accessibility and completeness

| ID | Issue | Effort |
|---|---|---|
| CRIT-11 | Context Sticky Bar max-height + Dynamic Type truncation | Medium |
| MAJ-04 | Checklist missing-document guidance + Chat escape route | Low |
| MAJ-09 | Manual insurance data tag vs CODEF-verified tag | Low |
| MAJ-10 | 보류 time-stamped indicator | Low |
| MAJ-11 | 무시 toast + reduced visual weight | Low |
| MAJ-12 | Health Score plain-language interpretation | Low (copy spec) |
| MAJ-13–15 | Inbox Full List, Profile, 수동 보험 입력 state coverage | Medium |
| MAJ-16 | surface-honest-box token added to frontmatter | Low |
| MAJ-25–27 | Touch target min-heights; status-warning contrast | Low |
| MIN-05–06 | Reduce Motion: Bottom Sheet + all loading indicators | Low |
| MIN-10–12 | Semantic roles: button, radiogroup, Outcome dots | Low |
| MIN-14–15 | Currency aria-label; lang="en" policy | Low |

---

*This report consolidates findings from three parallel reviewers. Cross-cutting issues ([CROSS]) reflect the intersection of regulatory risk, accessibility, and implementation contract gaps — they should be treated as a single coordinated fix rather than three separate items.*
