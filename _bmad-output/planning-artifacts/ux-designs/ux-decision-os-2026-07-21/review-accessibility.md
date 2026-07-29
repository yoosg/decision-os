# Accessibility Review — Decision OS
**Reviewer:** Accessibility Specialist (Mobile, Korean-market consumer apps)
**Date:** 2026-07-21
**Standard:** WCAG 2.2 AA, mobile web (iOS VoiceOver + Android TalkBack)
**Files reviewed:** EXPERIENCE.md, DESIGN.md

---

## Overall Verdict

The spec demonstrates genuine accessibility intent — the 44pt touch target floor, section-heading hierarchy, heading-based screen reader navigation, and Reduce Motion coverage are better than most Korean consumer app specs. However, several of the most-used color combinations fail WCAG 2.2 AA contrast thresholds for body-sized Korean text, the Context Sticky Bar's disabled-state semantics are underspecified for assistive technology users, and the disabled-CTA label text (white on `#D1D1D1`) is unreadable at any size. These are product defects, not polish items: three of the five critical findings directly block task completion for users relying on screen magnification, Dynamic Type, or high-contrast modes.

---

## 1. Context Sticky Bar Accessibility — **Critical**

### Findings

- **[Critical]** No `aria-live` announcement is specified for the disabled → enabled state transition. A VoiceOver/TalkBack user who is sequentially swiping through section content has no way to learn that the CTA has become active unless they happen to re-focus the bar. The bar is the *only* path to the Decision — if a screen reader user misses the activation, they are stuck. *Fix:* Add `aria-live="polite"` to a visually hidden status region that announces "청구 준비 시작 버튼을 사용할 수 있습니다" when the bar transitions to enabled state. Do not use `aria-live="assertive"` (it would interrupt mid-sentence reading).

- **[Critical]** The disabled CTA's `aria-label` is specified as combining recommendation text and CTA state ("비활성화됨" or "채택 가능"), but the spec does not define what label is announced when the button is in the disabled state, nor does it specify `aria-disabled="true"`. Without `aria-disabled="true"`, some screen readers will skip the button entirely during focus traversal — which means the user loses the hint that a CTA even exists. *Fix:* Mark the CTA `aria-disabled="true"` (not `disabled` attribute, which removes focus entirely), and set `aria-label="채택 — 비활성화됨. 추천 근거를 먼저 확인해 주세요"` so the composite state and the reason are announced in one pass.

- **[Major]** The hint text "추천 근거를 먼저 확인해 주세요 ↑" is specified as a visual element below the disabled button. There is no spec that associates this hint with the button via `aria-describedby`. A screen reader user tapping the disabled CTA will hear only the button label — not the remediation instruction. *Fix:* Give the hint text an `id` and add `aria-describedby="[hint-id]"` to the CTA element.

- **[Major]** Section "seen" activation is defined as section-presence in the viewport, but the spec says nothing about how a screen reader user (who is not visually tracking scroll) triggers activation. A TalkBack user reading through sections via swipe gestures does move focus through the DOM — but does focus traversal through a section heading count as "seen"? If the trigger is purely scroll-position/Intersection Observer, a screen reader user who reads but does not scroll (some TalkBack modes navigate the virtual cursor without scrolling) could read all four sections and still have a permanently disabled CTA. *Fix:* Define activation as "each section's heading or first meaningful element has received focus OR entered the viewport" — whichever comes first. Document this in the spec explicitly.

- **[Minor]** The upward arrow glyph in "추천 근거를 먼저 확인해 주세요 ↑" will be read by VoiceOver as "위쪽 화살표" interrupting the sentence flow in Korean. *Fix:* Wrap the arrow in `<span aria-hidden="true">↑</span>` so it is visually present but not read aloud.

---

## 2. Touch Targets — **Major**

### Findings

- **[Major]** The three-button CTA row (채택 / 나중에 검토 / 무시) in the enabled Context Sticky Bar places "나중에 검토" and "무시" as "ghost pills side by side." On a 375px viewport with 20px horizontal padding on each side, the available content width is 335px. Divided between two pills with any gap, each pill is ~157px wide. Height is not specified. The spec states ≥ 44pt targets broadly but does not explicitly confirm these two secondary pills meet the minimum. At typical pill padding of `12px top/bottom`, a 13px label renders the pill at approximately 37–39pt tall — **below the 44pt floor**. *Fix:* Specify `min-height: 44px` (≈ 44pt at 1x) explicitly for the secondary ghost pill CTAs. Use a 12px gap between the two pills, not equal-split, so each pill can use the full available width minus 12px.

- **[Major]** Checklist items in the Decision 확인 + 서류 Checklist screen: the spec defines `checklist-item` border-radius (12px) but specifies no minimum height. Checkbox state (checked/unchecked) is a primary interaction. A checkbox row with 13px label at default padding can easily fall below 44pt. *Fix:* Specify `min-height: 44px` on each checklist item row, with the tap target encompassing the entire row (not just the checkbox element).

- **[Minor]** OCR Field Rows: each field is specified at `13px 16px padding` (top/bottom × left/right). At 16px value text, the rendered height is approximately 42–44px — borderline. If the label (11px) sits inside the same padding box, the effective touch target on a compact field could be 38–40px. *Fix:* Specify `min-height: 44px` on OCR field rows and confirm the label is inside the row tap area, not a separate element that fragments the target.

- **[Minor]** Memory Timeline items: `12×14px padding` card shell with `14px` title text yields an approximately 40px rendered height for simple single-line entries. *Fix:* Specify `min-height: 44px` on tappable timeline cards.

- **[Nice to Have]** Bottom nav items: the 52×52px nav-plus FAB is confirmed compliant. The four nav tab items are not explicitly sized — they are implied to fill the nav bar. Given typical bottom nav bar heights (56–60px), these are likely compliant, but explicit `min-height: 44px` and `min-width: 44px` per tab should be stated.

---

## 3. Korean Text & Dynamic Type — **Critical**

### Findings

- **[Critical]** `text-secondary` (#6B7280) on `surface-card` (#F2F2F2) produces a contrast ratio of approximately **3.5:1**. WCAG 2.2 AA requires 4.5:1 for normal text (under 18pt/24px or 14pt/~18.67px bold). This combination appears in: Inbox Card subtitle row (13px), OCR Field Row label (11px), Memory Timeline type label (10px/uppercase), and Bottom Sheet sub-label (13px). Every one of these is below the 18pt large-text threshold. This is the single most pervasive contrast failure in the system. *Fix:* Darken `text-secondary` to approximately `#5A5F6B` or shift `surface-card` lighter. Alternatively, use `text-primary` (#0D0D0D) for any secondary text smaller than 18pt that sits on `surface-card`, and reserve `text-secondary` only for text on `surface-base` (#FFFFFF) where the ratio clears 4.5:1.

- **[Critical]** `text-secondary` (#6B7280) on `#F5F5F5` (Honest Box background) produces approximately **4.0:1** — still below 4.5:1 for the 13px body text and 11px uppercase label. The Honest Box is the AI uncertainty disclosure: a user with low vision may be precisely the person who needs to read this most carefully. *Fix:* Use `#595D6A` or darker for Honest Box body text, or shift the background to `#FFFFFF` (which clears 4.6:1).

- **[Critical]** White text on the disabled CTA background (`#D1D1D1`) produces approximately **1.5:1** — which fails even the most minimal threshold. While WCAG 2.2 SC 1.4.3 exempts "inactive UI components" from contrast requirements, this exemption applies only when the component's state is communicated through other means (aria-disabled, alt text). As noted in Section 1, the spec does not currently guarantee those other means are in place. Until `aria-disabled` and an accessible label are confirmed, this label text must meet contrast. *Fix:* Change the disabled CTA label text color to `text-primary` (#0D0D0D) on the `#D1D1D1` background, which gives ~8.5:1, and simultaneously implement the `aria-disabled` semantic so the exemption can properly apply.

- **[Major]** The Context Sticky Bar uses `min-height: unspecified` for the bar itself. The spec correctly states it must be "padding-driven so that when the user increases system font size, the bar expands." But the recommendation text uses the `label` scale (13px) and the hint text uses `caption` scale (11px). At iOS Dynamic Type "AX5" (the largest accessibility size), system fonts can render at 2.5–3x the base size. On a typical 375px viewport with a bar already containing 4 stacked elements (context label, recommendation text, primary CTA, secondary CTAs + hint text), the bar can occupy more than 60% of the viewport height at max Dynamic Type, leaving less than 40% for Review content above. The spec does not address this. *Fix:* Cap the bar at `max-height: 40vh` at minimum, or specify that at Dynamic Type ≥ 150% the recommendation text truncates to one line with a "..." disclosure, and the hint text collapses. Any truncation must remain accessible (full text accessible via `aria-label` on the button).

- **[Major]** `text-tertiary` (#9CA3AF) is used for timestamps, placeholders, and timeline dates on both `surface-card` (#F2F2F2) and `surface-base` (#FFFFFF). Contrast ratios are approximately **2.4:1** and **2.9:1** respectively — both fail AA. While timestamps at 11–12px could theoretically be considered decorative, they carry meaningful information (dates, times) required to understand the Memory Timeline. *Fix:* Use `text-secondary` (#6B7280) on `surface-base` (4.6:1) for dates in the Memory Timeline, or provide the date as part of the card's composite accessible label so the visual contrast failure has no functional impact.

- **[Major]** `status-warning` (#D97706) on `surface-base` (#FFFFFF) produces approximately **3.0:1** — fails AA for normal text. The warning token is used for "갱신 임박" indicators. *Fix:* Darken to `#B45309` (~4.7:1 on white) or ensure warning state is never conveyed through text alone (icon + badge text instead).

- **[Minor]** `error` (#EF4444) on `error-bg` (#FEF2F2) for the 11px error hint text below OCR fields: approximately **3.9:1** — passes large text (3:1) but fails for 11px text. *Fix:* Darken error hint text to `#DC2626` (~4.7:1 on `#FEF2F2`), or render the hint text in `text-primary` (#0D0D0D) to guarantee contrast independent of the error color.

- **[Minor]** `status-positive` (#16A34A) on `status-positive-bg` (#DCFCE7): approximately **3.1:1**. Used for the "지급 완료" badge. This passes large text threshold but not normal text. The badge font is 10px — far below large text. *Fix:* Use `text-primary` (#0D0D0D) for badge label text and retain the green background as the color signal only; the text itself stays high-contrast.

- **[Minor]** Korean line-height: DESIGN.md specifies "line-height for Korean body text: 1.5–1.6" — this is correct. However, the Honest Box body is specified as `13px / line-height 1.5`, and OCR field rows use `16px / weight 600` value text. No spec exists for line-height on field values or card titles. Korean characters (한글 syllable blocks) have a higher cap height and descender ratio than Latin; at `line-height: 1.3` or below, ascenders and descenders can clip. *Fix:* Add a global rule: all Korean body text smaller than 16px must use `line-height: 1.5` minimum; card title text at 16px+ may use `line-height: 1.4`. Add this as an explicit rule in DESIGN.md Typography Principles.

- **[Nice to Have]** The spec uses `system-ui` font stack without naming a Korean typeface. On Android, `system-ui` may resolve to Noto Sans KR or NanumSquare depending on device OEM skin — these have meaningfully different metrics. Consider specifying `'Apple SD Gothic Neo', 'Noto Sans KR', system-ui, sans-serif` for consistent Korean rendering across devices.

---

## 4. Screen Reader Decision Flow — **Major**

### Findings (박지은 flow, screen reader only)

- **[Major]** Home → Inbox Card (Step 7): The spec states the InboxCard announces "title + badge label + timestamp as composite accessible label." However, the NEW badge uses `accent-primary` background — this background/foreground relationship is visual only. If the card's composite accessible label is implemented as the card title alone (a common implementation shortcut), the "NEW" badge state is silently skipped. The spec mandates the composite label but does not show the label string. *Fix:* Provide an explicit example composite `aria-label` string, e.g., `"보험금 청구 가능성 — 청구 가능 보험 2건 확인됨, NEW, 2026년 7월 21일"`. This prevents implementation teams from guessing.

- **[Major]** Review 상세 section headings (Step 8): EXPERIENCE.md states sections must use `h2` or `aria-level`. The section sequence (Summary, Recommendation, Evidence, Risk/Uncertainty, Honest Box) is critical — the activation trigger depends on the user having "seen" all four sections. But the spec does not define heading levels below `h2`. If all five sections are `h2`, VoiceOver heading navigation jumps between them correctly. If sub-sections inside Evidence or Risk/Uncertainty use headings, the hierarchy must be stated. *Fix:* Specify: Review 상세 screen heading hierarchy = `h1` for Review title, `h2` for Summary/Recommendation/Evidence/Risk/Uncertainty/Honest Box section headings, `h3` for any sub-section within Evidence or Risk. This must be documented as an implementation requirement.

- **[Major]** Context Sticky Bar (Step 8 → CTA): The spec states the recommendation text and CTA state are announced as a single `aria-label` on the CTA button. This is correct intent, but the implementation note is missing: because the bar is `position: fixed`, it may be reached via VoiceOver "last in DOM" traversal rather than at the natural point in the reading flow after the last section. A screen reader user reading top-to-bottom may encounter the bar CTA before reading all four sections, encounter a disabled CTA, and not know they need to continue reading. *Fix:* In the DOM, place the Context Sticky Bar's focus-order position after the last content section using `tabindex` ordering or DOM placement, even though it is visually fixed. Document this explicitly.

- **[Minor]** Decision CTAs — all three options (채택 / 나중에 검토 / 무시) are reachable when enabled — this is correctly specified. However, the semantic roles are not stated. "나중에 검토" and "무시" are ghost pills — if implemented as `<div>` or `<a>` rather than `<button>`, they will not announce as interactive elements in TalkBack's default mode. *Fix:* Specify that all three Decision CTAs must use `<button>` element (not `<a>` or `<div>`).

- **[Minor]** Decision 확인 checklist (Step 9): Spec says `aria-checked` state should be announced ("체크됨" / "체크 안 됨"). This is correct. But the spec does not state whether checklist items use `role="checkbox"` in a `role="group"` with a group label. Without the group label, a screen reader user hears "진단서, 체크 안 됨" without knowing this is "청구 서류 체크리스트" context. *Fix:* Wrap checklist items in a `<fieldset>` with a `<legend>` of "청구 서류 체크리스트" or equivalent ARIA group.

- **[Minor]** Outcome 입력 option cards (3 cards: 지급 완료 / 거절됨 / 추가 서류 요청): The spec does not define the semantic role of the option cards. If they are implemented as `<div>` cards with tap handlers, VoiceOver/TalkBack will not announce them as selectable or announce selected state. *Fix:* Implement Outcome cards as `role="radio"` within a `role="radiogroup"` labelled "보험금 지급 결과", or as `<input type="radio">` with styled labels. Announce selected state via `aria-checked="true/false"`.

---

## 5. Color Independence — **Major**

### Findings

- **[Major]** OCR Field Row "Confirmed state" uses `status-positive` (#16A34A) checkmark as the sole visual differentiator from the default state. The spec states "No information is conveyed by color alone. Status states (positive, error, uncertain) are always accompanied by a text label or icon in addition to color" — and the checkmark icon is that accompaniment. However, a checkmark *icon* is itself a color-bearing visual. For a user with deuteranopia (red-green color blindness, ~8% of Korean males), a gray checkmark versus green checkmark on a gray card surface may not be distinguishable. *Fix:* Ensure the confirmed field also changes its label text to include a non-color indicator — e.g., the field label changes from "진료비" to "진료비 ✓" in text (with aria-label "진료비 — 확인됨"), or a border/outline appears on confirmed fields. The spec currently specifies "transparent border + status-positive checkmark" — the border return-to-transparent actually removes the one non-color shape cue.

- **[Major]** Memory Timeline Outcome dots: positive outcome uses `status-positive` fill, pending uses `text-tertiary` fill, and the spec references "Outcome neutral / pending: text-tertiary fill." For a color-blind user, a green 12×12px dot versus a gray 12×12px dot is the only differentiator for "paid" vs "pending" outcomes on the timeline. No text label, no icon, no shape change is specified. *Fix:* Add a type label or icon inside or beside the Outcome dot — e.g., "₩" glyph for paid outcomes, "?" for pending, "✕" for rejected — so the outcome state is not color-only.

- **[Minor]** The disabled CTA uses `text-disabled` (#D1D1D1) as background — only a color change signals the disabled state. The spec also states `cursor: not-allowed`, but cursor state is irrelevant on mobile touch. The spec does reference `aria-disabled` intent (Section 1 of this review), but without `aria-disabled` implemented, the non-color cue is missing. *Fix:* As stated in Section 1, implement `aria-disabled="true"` and specify the button also carries a visual shape distinction in disabled state (e.g., dashed border instead of solid, or a lock icon at the left of the label).

- **[Nice to Have]** InboxCard NEW badge: `accent-primary` (#0D0D0D) background + `accent-foreground` (#FFFFFF) text — 21:1 contrast, clear. The "보류" badge (implied replacement when deferred) is not fully defined. If it uses a light background with `text-secondary` text, confirm the contrast. The spec should define all badge variants (NEW / 보류 / 확인 필요 / 보험 청구 진행 중) with explicit color tokens.

---

## 6. Motion & Animation — **Minor**

### Findings

- **[Minor]** The Reduce Motion spec only explicitly covers: (1) Context Sticky Bar activation fade/slide, (2) loading dot pulse, (3) card entrance animations. The Bottom Sheet open/close animation (slide-up from bottom) is not mentioned. On iOS, a sheet that slides up can trigger vestibular discomfort for users with motion sensitivity — this is the most common motion-triggered complaint in Korean consumer apps with bottom sheets. *Fix:* Add to the Reduce Motion spec: "Bottom Sheet open/close: replace slide-up animation with an instant appear/disappear (no translate transform) when `prefers-reduced-motion` is set."

- **[Minor]** The "분석 중" full-screen loading state specifies "three-dot pulse or similar" animation and the Reduce Motion spec covers substituting it with a static three-dot indicator. However, the full-screen loading state for CODEF integration ("약 30초 소요됩니다") also has an "animated indicator" — this is not covered by the Reduce Motion spec. *Fix:* Extend the Reduce Motion rule to all loading indicators globally: "All animated loading indicators replace their animation with a static indicator when `prefers-reduced-motion` is set."

- **[Nice to Have]** The Health Score Card arc ring visual (partial border technique) — if animated on load (arc drawing in), this should be covered by Reduce Motion. The spec does not define whether the arc ring has an entrance animation. *Fix:* Clarify whether the arc ring animates on entry; if so, add it to the Reduce Motion inventory.

---

## 7. Korean-specific Considerations — **Major**

### Findings

- **[Major]** Decision option labels "채택", "나중에 검토", "무시" — as CTA button labels read in isolation by a screen reader, these are ambiguous without context. "무시" in particular has a very blunt connotation in Korean; without the screen context, a VoiceOver user swiping to the button hears only "무시 버튼" — no indication that "무시" means "이 Review를 무시" vs. "이 앱을 무시". *Fix:* Provide more descriptive `aria-label` attributes: `aria-label="채택 — 보험금 청구 진행"`, `aria-label="나중에 검토 — 이 Review를 보류"`, `aria-label="무시 — 이 Review를 아카이브"`. The visible button label remains the short form (correct per UX principle), but screen readers receive full context.

- **[Major]** Currency formatting: the spec references "₩72,000원" in the 박지은 Outcome flow. Korean screen readers (iOS VoiceOver in Korean) handle the ₩ prefix and 원 suffix inconsistently — some pronounce it "원72,000원" (double unit), others skip the ₩ symbol. *Fix:* Specify that monetary amounts in the product use `aria-label` to provide an unambiguous reading: e.g., `<span aria-label="칠만 이천 원">₩72,000</span>`. For amounts in the Health Score Card ("월 163,000원"), the same pattern applies.

- **[Major]** The spec's `lang="ko"` on the HTML root is correct and confirmed. However, EXPERIENCE.md states: "System strings and legal notices may include Korean/English dual display where required." No inline `lang` attribute policy is defined for English text within a Korean page. Korean screen readers will mispronounce English strings (e.g., "CODEF", "ID", "Review") using Korean phoneme rules unless `lang="en"` is applied inline. "Review" (spelled in English) appears extensively in the product copy. *Fix:* Specify a global rule: any English word or phrase rendered within Korean body copy must carry `lang="en"` on its inline element. At minimum, define the exhaustive list of English-origin proper nouns in the product (CODEF, Review, ID, PW, NEW badge label, Memory, OS) and confirm their language attribution policy.

- **[Minor]** Number formatting in Korean: the spec does not address how large numbers are read. Health Score Card shows "월 163,000원" — TalkBack reads this as "일육삼쉼표영영영 원" (digit-by-digit with comma) rather than "십육만삼천 원." While this is a TalkBack/OS behavior rather than a product responsibility, an `aria-label` override as described above for currency also resolves this. *Fix:* Covered by the currency formatting fix above.

- **[Minor]** The "AI" abbreviation appears throughout the product (AI Review, AI 분석 결과, AI가 확인하지 못한 정보). Korean VoiceOver reads "AI" as "에이아이" which is correct and acceptable, but should be confirmed as the intended pronunciation. If the product ever uses "인공지능" in any context, ensure consistency. *Fix:* Confirm "AI" is always rendered in Latin script (not Hangul transliteration) and that the English pronunciation via VoiceOver Korean is acceptable to the product team.

- **[Nice to Have]** The Korean screen reader ecosystem includes Samsung TalkBack (with Bixby Voice integration) in addition to standard Android TalkBack. Samsung TalkBack has a custom touch exploration mode that can behave differently with `position: fixed` elements (such as the Context Sticky Bar) on Samsung devices (a dominant market segment in Korea). *Fix:* Include Samsung Galaxy (Android 14+, One UI 6+) with Samsung TalkBack as an explicit test target in the accessibility testing plan.

---

## Summary Counts

| Severity | Count |
|----------|-------|
| **Critical** | 5 |
| **Major** | 16 |
| **Minor** | 11 |
| **Nice to Have** | 5 |
| **Total** | 37 |

---

## Top 3 Priority Fixes

### 1. Context Sticky Bar — Screen Reader Activation (Critical)
The disabled → enabled CTA transition has no `aria-live` announcement, the disabled button has no confirmed `aria-disabled="true"`, the hint text is not linked via `aria-describedby`, and the activation trigger may never fire for screen reader users who navigate without scrolling. The Context Sticky Bar is the only path to the Decision — a screen reader user who cannot reach or understand the CTA cannot complete any consequential action in the product. Fix all four issues in a single implementation pass: (a) `aria-disabled="true"` on disabled CTA, (b) composite `aria-label` including state and reason, (c) `aria-describedby` on hint text, (d) `aria-live="polite"` status region for activation announcement, (e) define activation trigger to fire on section focus traversal in addition to scroll intersection.

### 2. `text-secondary` Contrast on Non-White Surfaces (Critical)
`#6B7280` on `#F2F2F2` (surface-card, ~3.5:1) and on `#F5F5F5` (Honest Box, ~4.0:1) fail WCAG 2.2 AA for all text below 18pt. This affects Inbox Card subtitles, OCR Field Row labels (11px), Memory Timeline type labels (10px), Bottom Sheet sub-labels, and the entire Honest Box body — which is the AI uncertainty disclosure. Darken `text-secondary` to ~`#595D6A` (approximately 4.6:1 on surface-card) or define a separate `text-on-card` token at sufficient contrast. This single token change resolves the majority of contrast failures in the product without requiring redesign.

### 3. Decision CTA `aria-label` Strings — Context for Screen Reader Users (Major)
"채택", "나중에 검토", and "무시" are ambiguous in isolation. Provide explicit `aria-label` attributes on all three CTAs that include the action's consequence (e.g., "채택 — 보험금 청구 진행", "무시 — 이 Review를 아카이브"). Additionally, specify `aria-label` patterns for all monetary amounts (₩N,NNN 원 format) and for the InboxCard composite label. These are copy decisions that must be made by the product team, not left to engineering interpretation — codify them in EXPERIENCE.md's Screen Reader section before implementation begins.
