# Spine Pair Review — Decision OS
**Reviewer:** Rubric Walker
**Date:** 2026-07-21

---

## Overall verdict

The spine pair is substantively complete for the primary MVP loop (Receipt → OCR → Event → Review → Decision → Outcome → Memory) and achieves unusually high consistency on tokens, component naming, and voice. Three critical gaps exist: the `병원 방문 직접 등록` surface has zero state coverage and no flow steps beyond a list mention; `Contextual Chat` has no behavioral spec and no state patterns; and the OCR disclaimer is positioned *above* the fields in both spines but *below* them in the wireframe — a contradiction that will produce implementation divergence. Resolving those three and seven major gaps is required before a developer can implement the full product correctly.

---

## 1. Flow Coverage — adequate (with gaps on 4 surfaces)

**What was checked:** Every surface in the IA Screen Inventory (19 surfaces) was mapped against Key Flows (2 flows + their failure paths) and State Patterns. Each flow was verified for: named protagonist, numbered steps, [Climax] beat, and failure path.

Both flows have named protagonists, numbered steps, a single [Climax] beat each, and at least one explicit failure path. The core loop (Receipt → Review → Decision → Outcome → Memory) is fully step-covered in Flow 1. Onboarding (Flow 2) covers CODEF → Health Score → Home entry.

### Findings

- **Critical** `병원 방문 직접 등록` (IA row 9): Listed in the IA inventory and referenced in the + Bottom Sheet option list and in the OCR failure path ("routes to 병원 방문 직접 등록 폼 → Step 5"), but has zero numbered flow steps, no state pattern, and no field-list spec. A developer cannot implement this form from these docs. (§ EXPERIENCE.md, Screen Inventory row 9 / Key Flows passim). *Fix:* Add a Flow 1b with numbered steps or a dedicated state/component entry for this form, including minimum fields (병원명, 진료일, 진료비, 진료 유형 minimum — or call out if fields differ from OCR extraction).*

- **Critical** `Contextual Chat` (IA row 19): Present in the IA inventory and navigation rule, but has no Component Pattern section, no State Pattern entry, no flow steps with a protagonist, and no behavioral spec (how it opens, how context is passed, how it closes). (§ EXPERIENCE.md, Screen Inventory row 19). *Fix:* Add a Component Pattern section and at least one State Pattern covering: empty (no prior context), in-conversation, and post-conversation navigation. A flow snippet showing the entry trigger and dismiss path is required.*

- **Major** `Inbox Full List` (IA row 2): Referenced in Inbox Card component spec ("Where: Home (Inbox section) and Inbox Full List screen") but no flow reaches it, no state patterns cover it (e.g., empty, full, paginated), and its "전체 보기" trigger condition "N items" is unresolved. (§ EXPERIENCE.md, Component Patterns → Inbox Card). *Fix:* Specify N, add empty/populated states, and add a flow step or footnote showing the navigation.*

- **Major** `Profile / Integration` (IA row 18): Listed in the IA inventory with purpose "Integration management, notification settings, data/account management" but has no flow, no state pattern, and no component or interaction spec. Notification Patterns references "re-requested on Home after denial" prohibition without specifying what happens in Profile when the user wants to re-enable. (§ EXPERIENCE.md, Screen Inventory row 18). *Fix:* Add at minimum a State Pattern entry covering: connected state, disconnected state, and the re-enable path for notifications.*

- **Major** `수동 보험 입력` (IA row 16): Referenced only in the Flow 2 failure path ("수동 보험 입력 폼 (보험사 / 상품명 / 보험료 / 보장)") as a destination, but has no numbered steps, no state patterns (what happens if the user adds 0 policies? 1 policy?), and no minimum field spec beyond the parenthetical. (§ EXPERIENCE.md, Flow 2 실패 경로). *Fix:* Either add numbered steps to Flow 2 or add a State Pattern row for this screen.*

- **Minor** `카메라 / 영수증 촬영` (IA row 5): Not covered by any state pattern (e.g., permission denied, low-light failure, camera unavailable). The OCR failure path covers what happens after capture, but not camera-access failures. (§ EXPERIENCE.md, State Patterns). *Fix:* Add a state pattern row: "카메라 권한 거부 → 설정으로 이동" fallback.*

- **Minor** `보험 건강도 결과` (IA row 17): Covered by Onboarding States and Flow 2 Step 5, but no state pattern covers subsequent visits (returning user who navigates back via Project tab — is this screen accessible post-onboarding?). (§ EXPERIENCE.md, Onboarding States). *Fix:* Clarify whether this is a one-time onboarding screen or a persistent screen reachable from 프로젝트 탭. The IA suggests it's onboarding-only but the project tab shows HealthScoreCard — the distinction is blurred.*

---

## 2. Token Completeness — strong (one naming mismatch, one gap)

**What was checked:** All 24 named tokens in DESIGN.md frontmatter (excluding [ASSUMPTION]-tagged dark mode tokens). All `{path.to.token}` references in EXPERIENCE.md prose. Every reference was resolved against frontmatter.

All six `{colors.X}` references in EXPERIENCE.md resolve correctly to defined tokens with hex values:
- `{colors.text-disabled}` → `#D1D1D1` ✓
- `{colors.accent-primary}` → `#0D0D0D` ✓
- `{colors.accent-foreground}` → `#FFFFFF` ✓
- `{colors.error}` → `#EF4444` ✓
- `{colors.error-bg}` → `#FEF2F2` ✓
- `{colors.status-positive}` → `#16A34A` ✓

All five `{components.X}` references resolve to frontmatter component names ✓

### Findings

- **Major** `HonestBox` background token gap: DESIGN.md Component section specifies the HonestBox background as `#F5F5F5` — a raw hex value described as "lighter than surface-card" — but this hex is not defined as a named token in the frontmatter. The frontmatter components section repeats this value inline. A developer implementing theming or a dark mode variant has no token to reference. (§ DESIGN.md Components → Honest Box; frontmatter `components.HonestBox`). *Fix:* Add `surface-honest-box: "#F5F5F5"` (or similar) to the colors frontmatter and replace the raw hex in both the component description and prose with `{colors.surface-honest-box}`.*

- **Major** `status-positive-bg` is defined in frontmatter but never referenced by token path anywhere in EXPERIENCE.md. DESIGN.md prose uses it by name ("녹색 badge fill") but EXPERIENCE.md uses it nowhere, leaving the badge-green state underdefined for the behavioral spec. (§ DESIGN.md Colors → Accent & Status; EXPERIENCE.md passim). *Fix:* Add a reference in the Inbox Card or Decision Loop Patterns section for the "채택 완료" / "지급 완료" badge fill.*

- **Minor** `HonestBox` secondary CTAs: DESIGN.md specifies the Context Sticky Bar enabled-state secondary CTAs have `border: 1.5px solid #E0E0E0`. This raw hex `#E0E0E0` is not a defined token (closest: `border-subtle: #E5E5E5` or `border-card: #DCDCDC`). (§ DESIGN.md Components → Context Sticky Bar → Enabled state). *Fix:* Map to nearest token or add `border-secondary-cta: "#E0E0E0"` to frontmatter.*

- **Nice to Have** `status-warning` is defined in frontmatter with usage "갱신 임박" but is referenced nowhere in EXPERIENCE.md flows or state patterns. There is no state spec for a "갱신 임박" warning state on the Project screen or Inbox. *Fix:* Either add a state pattern entry for renewal warning, or note the token as reserved for post-MVP.*

---

## 3. Component Coverage — strong (one directional gap, one naming discrepancy)

**What was checked:** 8 components in DESIGN.md frontmatter vs. Component Patterns sections in EXPERIENCE.md. Both directions (DESIGN → EXPERIENCE, EXPERIENCE → DESIGN).

**DESIGN.md → EXPERIENCE.md mapping:**

| DESIGN.md name | EXPERIENCE.md section | Status |
|---|---|---|
| ContextStickyBar | Context Sticky Bar | ✓ |
| InboxCard | Inbox Card | ✓ |
| EventCandidateCard | Event Candidate Card | ✓ |
| HealthScoreCard | Health Score Card | ✓ |
| PlusBottomSheet | + Bottom Sheet | ✓ |
| MemoryTimelineItem | Memory Timeline Item | ✓ |
| OCRFieldRow | OCR Field Row | ✓ |
| HonestBox | Honest Box | ✓ |

All 8 components have behavioral specs in EXPERIENCE.md. All 8 have visual specs in DESIGN.md. ✓

### Findings

- **Major** Component name casing inconsistency: DESIGN.md frontmatter uses `PlusBottomSheet` (PascalCase, no spaces) but EXPERIENCE.md Component Patterns section header uses `+ Bottom Sheet` (display text with special character). EXPERIENCE.md `{components.PlusBottomSheet}` references use the correct PascalCase token path, but the section header mismatch will confuse a developer matching section headers to token references. (§ DESIGN.md frontmatter `PlusBottomSheet`; EXPERIENCE.md § Component Patterns → + Bottom Sheet). *Fix:* Rename the EXPERIENCE.md section header to `### PlusBottomSheet (+ Bottom Sheet)` or add a note that the display name is `+ Bottom Sheet`.*

- **Major** `EventCandidateCard` behavioral gap: The component has a behavioral spec (EXPERIENCE.md § Event Candidate Card) but that spec does not cover the card's appearance when it appears *within the Home Inbox* (as an Inbox item) vs. on the standalone `Event 후보 확인` screen. The distinction matters because on the Inbox, it must have "확인 필요" badge (per State Patterns); on the confirmation screen, it has the event data preview layout. A developer building both screens needs to know whether it's the same component with a different state, or two separate layouts. (§ EXPERIENCE.md Component Patterns → Event Candidate Card; State Patterns → Event 후보 — 사용자 미확인). *Fix:* Add a "where: two contexts" note distinguishing the Inbox variant (badge-only summary) from the confirmation screen variant (full preview).*

- **Minor** `{components.HealthScoreCard}`, `{components.EventCandidateCard}`, `{components.MemoryTimelineItem}` are never referenced by token path in EXPERIENCE.md prose — only by display-name text. The three components referenced by `{components.X}` token path are: ContextStickyBar, HonestBox, InboxCard, OCRFieldRow, PlusBottomSheet. This is inconsistent. (§ EXPERIENCE.md passim). *Fix:* Apply token path references consistently, or accept prose references as sufficient and document this convention.*

---

## 4. State Coverage — adequate (two critical gaps, three major)

**What was checked:** Every surface in the IA inventory was walked for expected states (empty, loading, error, permission-denied, partial-data, etc.). Six critical surfaces were checked explicitly per the audit brief.

**Home:** All three states explicitly covered (Empty Inbox ✓, Loading/Review 생성 중 ✓, Inbox with items ✓). The wireframe (Screen 2) shows an illustration icon (✓ emoji) for the empty state, but EXPERIENCE.md State Patterns specifies "No illustration" — minor contradiction.

**Review 상세:** Both Context Sticky Bar states (disabled ✓, enabled ✓) are fully covered with explicit token references. ✓

**OCR 결과 확인:** OCR failure error state is covered in Flow States. ✓ However, the partial-OCR state (some fields extracted, some blank/unrecognized) is not specced — covered under "Fields extracted in MVP" but no state for a field that returns blank is defined.

**보험 연동:** CODEF connection failure fallback covered in Onboarding States ✓. CODEF loading state covered ✓.

**Contextual Chat:** No state patterns at all (see Flow Coverage § Finding Critical).

**Memory Timeline:** Empty state for new user covered ✓ in Memory States.

### Findings

- **Critical** `병원 방문 직접 등록` has zero state coverage: no empty state, no validation error state, no submit-loading state, no success state. (§ EXPERIENCE.md State Patterns — surface absent). *Fix:* Add state pattern rows for this screen.*

- **Critical** `Contextual Chat` has zero state coverage. (§ EXPERIENCE.md State Patterns — surface absent). *Fix:* See Flow Coverage Critical finding.*

- **Major** `Decision 확인 + 서류 Checklist` partial-completion state: Flow States covers "결과 대기 중" (all docs unchecked) and the Outcome 입력 대기 trigger, but the intermediate state (some items checked, user closes app and returns) is not spec'd. Does the checklist persist state? Is there a badge change? (§ EXPERIENCE.md State Patterns → Flow States → Decision 채택 → 결과 대기; Decision Loop Patterns → Post-Decision → 채택 path). *Fix:* Add: "Checklist — partially checked: state persists across sessions; no badge change until all items checked or Outcome submitted."*

- **Major** `Insurance Project 상세` has no state patterns at all: no empty state (user with 0 linked policies), no loading state while Health Score recomputes, no stale-data state. The wireframe shows a populated state (Screen 10) but no state table row covers this surface. (§ EXPERIENCE.md State Patterns — surface absent). *Fix:* Add state rows for: (a) empty/no policies linked, (b) score loading, (c) score stale.*

- **Major** `분석 중 상태` (dedicated screen, IA row 8): The dedicated screen is described in Flow States and in Flow 1 Step 6, but the "분석 completed while user is still on screen" transition is not specced. What happens if the Review appears while the user is still viewing the 분석 중 screen — does the screen auto-navigate to Home, or does it require a tap on "홈으로 돌아가기"? (§ EXPERIENCE.md State Patterns → Flow States → Review 생성 중). *Fix:* Add a sub-state: "Analysis completes while screen is open → CTA changes to '새 Review 확인하기' and navigates to Home/Review." Or specify the screen is one-way.*

- **Minor** OCR partial-extraction state: No state for a field returning blank (e.g., 병원명 could not be parsed). The minimum-four-field MVP spec says fields are extracted, but does not cover when fewer are extracted. (§ EXPERIENCE.md Component Patterns → OCR Field Row → Fields extracted). *Fix:* Add a "blank/unparsed field" state to OCR Field Row: shows field label + empty value + edit icon, auto-focuses.*

- **Minor** Home empty state illustration contradiction: State Patterns says "No illustration" for empty inbox, but wireframe Screen 2 shows a `✓` emoji as an empty icon with an `empty-icon` CSS class (which is explicitly illustrated). (§ EXPERIENCE.md State Patterns → Home States → Empty Inbox; wireframes Screen 2). *Fix:* Either remove the icon from the wireframe or change State Patterns to permit a minimal icon. Clarify intent.*

---

## 5. Visual Reference Coverage — minor gaps

**What was checked:** Files in `.working/` directory. Links from both spines to each artifact.

`.working/` contains two files:
1. `wireframes-key-screens-2026-07-21.html`
2. `ia-2026-07-21.excalidraw`

### Findings

- **Major** `ia-2026-07-21.excalidraw` is an orphaned artifact: it exists in `.working/` but is not linked from either DESIGN.md or EXPERIENCE.md. Neither spine references it by path or by name. (§ `.working/ia-2026-07-21.excalidraw`). *Fix:* Either link from EXPERIENCE.md § Information Architecture ("See also: `.working/ia-2026-07-21.excalidraw` for visual IA map") or delete if it duplicates the IA inventory table.*

- **Minor** Wireframe link in both spines is by filename only in `sources:` frontmatter, not by relative path (`./working/wireframes-key-screens-2026-07-21.html`). A consumer parsing sources: cannot locate the file without knowing the directory convention. (§ DESIGN.md frontmatter sources; EXPERIENCE.md frontmatter sources). *Fix:* Change to `.working/wireframes-key-screens-2026-07-21.html` in both frontmatters.*

- **Minor** `OCR disclaimer position contradiction`: DESIGN.md and EXPERIENCE.md both specify disclaimer "above the field list." The wireframe (Screen 5, `note-text` div) renders the disclaimer *below* the last field row and *above* the CTA area — i.e., after the fields, not before. This will cause disagreement between design intent and wireframe reference during implementation. (§ DESIGN.md Components → OCR Field Row; EXPERIENCE.md Component Patterns → OCR Field Row → Disclaimer placement; wireframes-key-screens-2026-07-21.html Screen 5 lines 1495–1497). *Fix:* Move disclaimer div in wireframe to above the first form-field div, or update the spec to say "below fields, above CTA." Choose one and make both spines + wireframe consistent.*

---

## 6. Bloat & Overspecification — minor

**What was checked:** Both spines for PRD restatement, pixel specs where tokens exist, decorative narrative, and misplaced content.

### Findings

- **Minor** EXPERIENCE.md § Decision Loop Patterns → Review Before Action: "Users who have a Review in their Inbox may read it, defer it (보류), or dismiss it (무시), but they cannot proceed to claim filing from the product without having opened the Review." This is a PRD/product requirement restatement, not a UX design decision. It belongs in the PRD or architecture docs, not the experience spec. (§ EXPERIENCE.md Decision Loop Patterns → Review Before Action). *Fix:* Replace with the UX constraint: "The Review 상세 screen has no 'skip' CTA. The only forward paths are ContextStickyBar (채택/보류/무시) and back navigation."*

- **Minor** DESIGN.md § Shapes table: "Phone frame (wireframe artifact) | 44px (not a product token)" is explicitly flagged as a non-product token. Its presence in the Shapes section risks a developer copying it. (§ DESIGN.md Shapes). *Fix:* Move this note to a comment or footnote rather than a table row alongside real product tokens.*

- **Minor** EXPERIENCE.md § Inspiration & Anti-patterns → "What Decision OS is NOT": The subsection "Not a ChatGPT-style AI assistant" is 80+ words of narrative explaining the product philosophy. This is PRD/PRFAQ content. The banned-patterns table below it is the actionable UX artifact. (§ EXPERIENCE.md Inspiration & Anti-patterns → What Decision OS is NOT). *Fix:* Trim the prose paragraphs; keep only the Rejected patterns table.*

- **Nice to Have** DESIGN.md § Colors → "Color Usage Principles" paragraph on `status-uncertain`: "Maps to text-secondary; uncertainty is expressed through tone, not a separate color" is a sound design decision but is stated in three places (frontmatter comment, color table, and principles). One instance suffices.*

---

## 7. Inheritance Discipline — strong (one path issue, two consistency gaps)

**What was checked:** `sources:` frontmatter entries, glossary term consistency across both files, component name consistency, and `{path.to.token}` resolution.

### Findings

- **Major** `sources:` entries are descriptive labels, not resolvable paths. Both spines list `.memlog.md`, `prd.md`, `prfaq-decision-os-distillate.md`, `architecture/overview.md` — but these are relative paths without an anchor directory. A reader or automated tool cannot locate these files without knowing the repo root. `wireframes-key-screens-2026-07-21.html` is similarly missing its `.working/` prefix. (§ DESIGN.md frontmatter sources; EXPERIENCE.md frontmatter sources). *Fix:* Use absolute or repo-root-relative paths (e.g., `_bmad-output/planning-artifacts/...`) or explicitly state the convention.*

- **Minor** Glossary term `Review` used inconsistently in one instance: EXPERIENCE.md § Notification Patterns → Non-Triggers says "AI analysis complete (not visible to user as a standalone event; the Review appearing in Inbox is the signal)" — but elsewhere Review is treated as the output of analysis, not a synonym for "analysis result." This is consistent in 98% of usage; the one instance above could mislead. *Fix:* Reword to "not sent as a standalone push; the push for the completed Review serves as the signal."*

- **Minor** DESIGN.md § Components → Context Sticky Bar cross-references "See EXPERIENCE.md — Component Patterns → Context Sticky Bar" for activation trigger. This is a valid cross-reference, but it is the only outbound cross-reference from DESIGN.md to EXPERIENCE.md. The activation trigger is a behavioral spec — its presence in DESIGN.md is correct (it's referenced in the disabled-state spec), but the pointer is informal. If section headers change, this reference breaks. *Fix:* Low priority — acceptable as is, but a section anchor would be more robust.*

---

## 8. Shape Fit — strong

**What was checked:** DESIGN.md section order against canonical order. EXPERIENCE.md required sections. Inspiration & Anti-patterns presence. Invented section justification.

**DESIGN.md section order:**
1. Brand & Style ✓
2. Colors ✓
3. Typography ✓
4. Layout & Spacing ✓
5. Elevation & Depth ✓
6. Shapes ✓
7. Components ✓
8. Do's and Don'ts ✓

Canonical order: correct. ✓

**EXPERIENCE.md required sections:**
- Foundation ✓
- IA ✓
- Voice and Tone ✓
- Component Patterns ✓
- State Patterns ✓
- Interaction Primitives ✓
- Accessibility Floor ✓
- Key Flows ✓

All 8 required defaults present. ✓

**Inspiration & Anti-patterns:** Present and well-formed. Cal AI / Linear / Apple Health / Copilot Money all referenced with lifted patterns named. Rejected patterns table is actionable. ✓

**Invented sections:**

- `Notification Patterns`: Earns its place. Push notification timing, stale policy, deep link behavior, and Inbox-as-notification-center are all implementation-bearing decisions not covered by the 8 required sections. ✓

- `Decision Loop Patterns`: Earns its place. The three-state model, confirmation philosophy, Outcome loop closure, and Memory write spec are core to the product and span multiple screens. Without this section, a developer could not implement the post-채택 flow correctly. ✓

### Findings

- **Minor** EXPERIENCE.md § Interaction Primitives → Bottom Sheet Dismissal is duplicated: the spec appears under both § Interaction Primitives → Bottom Sheet Dismissal AND under § Component Patterns → + Bottom Sheet → Dismiss methods. The two descriptions are consistent but redundant. (§ EXPERIENCE.md Interaction Primitives → Bottom Sheet Dismissal; Component Patterns → + Bottom Sheet). *Fix:* Collapse one to a cross-reference.*

- **Nice to Have** DESIGN.md § Layout & Spacing spacing table has two rows that conflict with frontmatter: the table says "Section gap (header to first card): 10px" but frontmatter `section-gap: "20px"`. The table appears to distinguish "header to first card" (10px) from "section-to-section gap" (20px) — which is a legitimate split — but the frontmatter only defines one `section-gap` token. (§ DESIGN.md frontmatter spacing; Layout & Spacing table). *Fix:* Add `section-gap-inner: "10px"` to frontmatter or rename the table rows to clarify both exist.*

---

## Special Focus — Review → Decision → Outcome → Memory Loop

**Can a developer implement the full loop from these docs alone?**

**Verdict: yes with three caveats.**

The loop is fully specced for the primary path: Flow 1 Steps 7–12 cover Review → Decision (채택) → Checklist → Outcome entry → Memory write. Decision Loop Patterns covers all three decision states and Outcome loop closure. Memory Write section defines the four objects stored and their immutability.

**Caveats:**
1. The `보류` path returns Review to Inbox but does not specify the badge change timeline: does "보류" replace "NEW" immediately on tap, or on next Inbox load? The State Patterns table says "badge changes to '보류'" but the trigger is ambiguous.
2. The `무시` path specifies "accessible from Memory Timeline under the associated Event chain" but Memory Timeline Item only shows Event/Review/Decision/Outcome dot types. A `무시`-labeled Decision item has no dot color spec (it cannot be `status-positive` for a dismissed decision). 
3. The Outcome 입력 screen CTA text is "기록하기" in the wireframe (Screen 9) and implied by "확인" in Flow 1 Step 12. No microcopy table entry for the Outcome confirmation CTA exists.

---

## Summary counts

- **Critical:** 4
- **Major:** 12
- **Minor:** 12
- **Nice to Have:** 3

**Output file:** `/Users/sgyoo/Desktop/claude-playground/decision-os/_bmad-output/planning-artifacts/ux-designs/ux-decision-os-2026-07-21/review-rubric.md`
