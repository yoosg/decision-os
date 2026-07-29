---
name: Decision OS
description: >
  Premium personal operating system for consequential decisions. AI Research is the first Playbook.
  Mobile-first. Monochromatic, calm, financial-grade. One screen, one decision.
colors:
  surface-base: "#FFFFFF"
  surface-raised: "#F9F9F9"
  surface-card: "#F2F2F2"
  surface-card-alt: "#ECECEC"
  surface-overlay: "rgba(0,0,0,0.45)"
  text-primary: "#0D0D0D"
  text-secondary: "#595D6A"
  text-tertiary: "#9CA3AF"
  text-disabled: "#D1D1D1"
  border-subtle: "#E5E5E5"
  border-card: "#DCDCDC"
  accent-primary: "#0D0D0D"
  accent-foreground: "#FFFFFF"
  status-positive: "#16A34A"
  status-positive-bg: "#DCFCE7"
  status-warning: "#B45309"
  status-uncertain: "#6B7280"
  error: "#EF4444"
  error-bg: "#FEF2F2"
  surface-honest-box: "#F5F5F5"
  # [ASSUMPTION] Dark mode tokens not confirmed for MVP. Values below are
  # placeholders only and must not be used until dark mode is explicitly scoped.
  dark-surface-base: "#0D0D0D"
  dark-surface-card: "#1A1A1A"
  dark-text-primary: "#FFFFFF"
  dark-text-secondary: "#9CA3AF"
typography:
  # [ASSUMPTION] A specific named typeface (e.g., Inter, Pretendard) has not been
  # confirmed beyond the system-ui stack. The font stack below is the only
  # confirmed choice.
  font-family: "system-ui, -apple-system, 'Helvetica Neue', sans-serif"
  scale:
    screen-title: { size: "28–30px", weight: 700, tracking: "-0.5px" }
    section-title: { size: "22–24px", weight: 700, tracking: "-0.3px" }
    body-large: { size: "17px", weight: 600, tracking: "-0.2px" }
    body: { size: "15–16px", weight: 500 }
    label: { size: "13px", weight: 600 }
    caption: { size: "11–12px", weight: 500, tracking: "0.4–0.8px" }
    badge: { size: "10px", weight: 700, tracking: "0.5px", transform: "uppercase" }
rounded:
  card: "16px"
  pill: "9999px"
  sheet: "24px 24px 0 0"
  badge: "9999px"
  checklist-item: "12px"
  timeline-card: "12px"
  form-field: "12px"
  option-card: "14px"
  fab-plus: "50%"
spacing:
  base-unit: "4px"
  scale: [4, 8, 12, 16, 20, 24, 32, 48]
  screen-horizontal-padding: "20px"
  card-padding: "16px"
  section-gap: "20px"
  cta-area-vertical: "12px 20px 16px"
components:
  ContextStickyBar: >
    Fixed bottom bar on Research Review 상세 screen only. Two states: disabled (primary CTA uses
    text-disabled bg, neutral engagement prompt shown — recommendation withheld) and enabled
    (accent-primary CTA, recommendation text revealed, secondary ghost CTAs). Recommendation
    is withheld in disabled state to prevent pre-evidence anchoring.
  SignalCard: >
    Home Daily Brief section item. surface-card background, border-radius card (16px), 16px padding.
    NEW badge (accent-primary bg, accent-foreground text, 10px/700/uppercase) on unseen Signals.
    Structure: title row (16px/600) + relevance tag row (12px/text-secondary) + meta row (11px/text-tertiary).
  QueueItem: >
    Queue tab item. Timing badge (TODAY/THIS WEEK/LATER): surface-card-alt bg, text-secondary text,
    10px/700/uppercase. Signal title (15px/600) + estimated time (12px/text-secondary) +
    reschedule text link + chevron. min-height: 44px.
  OutcomeCard: >
    Outcome 입력 option card. border-radius option-card (14px). Selected state: accent-primary border
    (1.5px, not fill). Unselected: border-card (1px). Four states: Completed / Applied / Dropped / Not Useful.
    min-height: 52px.
  LearningPathCard: >
    Learning Path resource item. surface-card bg, border-radius card (16px), 16px padding.
    Resource type label (10px/uppercase/700/text-secondary) + title (15px/600/text-primary) +
    descriptor (13px/text-secondary) + chevron-external icon (text-tertiary). Five fixed types.
  MemoryTimelineItem: >
    Vertical timeline. Left spine: 2px border-subtle line. Dots: 12px circles.
    Signal dot = text-secondary, Review/Decision dot = text-primary.
    Outcome: Completed = status-positive + ✓; Applied = status-positive + →;
    Dropped = text-primary + ✕; Not Useful = text-secondary + −. Glyphs required (color-independent).
    Timeline card: surface-card bg, border-radius timeline-card (12px), 12px×14px padding.
  HonestBox: >
    Distinct section container within Research Review 상세. Background: surface-honest-box (#F5F5F5).
    border-radius timeline-card (12px). Label: 11px / uppercase / weight 700 / text-secondary.
    Body: 13px / text-secondary / line-height 1.5. Never omitted from Review when uncertainty exists.
    High-severity entries carry status-warning left-border accent (3px); standard entries carry no border.
status: final
created: 2026-07-21
updated: 2026-07-22
version: "1.2.0"
sources:
  - _bmad-output/planning-artifacts/ux-designs/ux-decision-os-2026-07-21/.memlog.md (canonical decisions log)
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/prfaq-decision-os-distillate.md
  - _bmad-output/planning-artifacts/ux-designs/ux-decision-os-2026-07-21/mockups/wireframes-key-screens-2026-07-21.html
  - architecture/overview.md
---

# Decision OS Design System

## Brand & Style

Decision OS presents as a **premium personal operating system** — not an insurance app, not an AI chatbot. The overriding impression is:

- **금융 서비스 신뢰감**: The authority and composure of Korean financial-grade products.
- **생산성 도구 명료함**: The directness of tools like Linear — every element earns its place.
- **헬스케어 상태 가시성**: Clear status indicators like Apple Health, never ambiguous.

The aesthetic is monochromatic and calm. White space is structural, not decorative. Large, bold headings carry the hierarchy. The single primary color is near-black (#0D0D0D) — used for text, for the primary CTA, and for the Health Score Card inversion. There are no gradients, no glow effects, no AI-blue accents.


## Colors

### Surface Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `surface-base` | `#FFFFFF` | App chrome: status bar, nav bar, bottom nav, sticky bars |
| `surface-raised` | `#F9F9F9` | Screen background (the "room" all content sits in) |
| `surface-card` | `#F2F2F2` | Cards, list items, form fields (default state) |
| `surface-card-alt` | `#ECECEC` | Nested content within cards; subtle depth step |
| `surface-overlay` | `rgba(0,0,0,0.45)` | Bottom sheet scrim |

### Text

| Token | Hex | Usage |
|-------|-----|-------|
| `text-primary` | `#0D0D0D` | Headings, titles, body copy, primary actions |
| `text-secondary` | `#595D6A` | Subtitles, metadata, section headers, Honest Box body, timeline dates, timestamps (~4.6:1 on surface-card) |
| `text-tertiary` | `#9CA3AF` | Purely decorative placeholders only (e.g., form input ghost text). **Never use for dates, timestamps, or any text that conveys functional information** — contrast is insufficient for meaningful content. |
| `text-disabled` | `#D1D1D1` | Disabled CTA background (Context Sticky Bar disabled state) |

### Borders

| Token | Hex | Usage |
|-------|-----|-------|
| `border-subtle` | `#E5E5E5` | Bottom nav top border, sticky bar top border, timeline spine |
| `border-card` | `#DCDCDC` | Unchecked checkbox border; option-card unselected |

### Accent & Status

| Token | Hex | Usage |
|-------|-----|-------|
| `accent-primary` | `#0D0D0D` | Primary CTA background, nav-plus button, selected state borders, dark Health Score card bg, NEW badge bg |
| `accent-foreground` | `#FFFFFF` | Text on accent-primary surfaces |
| `status-positive` | `#16A34A` | Outcome positive dot, confirmed field checkmark icon. Use sparingly. |
| `status-positive-bg` | `#DCFCE7` | "녹색" badge fill (e.g., "지급 완료" badge) |
| `status-warning` | `#B45309` | Warning state indicators (e.g., 갱신 임박). (~4.7:1 on surface-base) |
| `status-uncertain` | `#6B7280` | Maps to `text-secondary`; uncertainty is expressed through tone, not a separate color |
| `error` | `#EF4444` | OCR field error border, error hint text |
| `error-bg` | `#FEF2F2` | OCR field error fill |

### Color Usage Principles

- The palette is intentionally near-monochromatic. Resist adding color for visual interest.
- `status-positive` (#16A34A) is the only saturated accent in the system. It appears only for confirmed-positive states (paid outcome, confirmed field). Never use it for general success toasts or encouragement.
- `status-warning` and `status-uncertain` communicate state, never urgency.


## Typography

**Font family:** `system-ui, -apple-system, 'Helvetica Neue', sans-serif`

> [ASSUMPTION] No named typeface (e.g., Pretendard, Inter) has been confirmed for MVP beyond the system-ui stack. If a specific Korean typeface is adopted, update this section and the frontmatter `typography.font-family` token accordingly.

### Type Scale

| Role | Size | Weight | Tracking | Notes |
|------|------|--------|----------|-------|
| Screen Title | 28–30px | 700 | -0.5px | Home greeting, onboarding wizard headings |
| Section Title | 22–24px | 700 | -0.3px | Within-screen section breaks |
| Body Large | 17px | 600 | -0.2px | Navigation bar title (centered), list primary labels |
| Body | 15–16px | 500–600 | 0 | Card titles (16px/600), standard body (15px/500) |
| Label | 13px | 600 | 0 | Card subtitles, Context Sticky Bar recommendation text |
| Caption | 11–12px | 500–600 | 0.4–0.8px | Timestamps, field labels, section header uppercase labels |
| Badge | 10px | 700 | 0.5px | NEW / STATUS / TYPE uppercase badges |

### Typography Principles

- Headlines are large and left-aligned. The type itself carries the layout.
- Never center body text. Centered text is reserved for Bottom Sheet titles and progress indicators only.
- Korean lang attribute (`lang="ko"`) must be set at the HTML root. Line-height for Korean body text: 1.5–1.6.
- Letter-spacing on uppercase caption/badge labels must be explicitly set (0.5–1.2px) to maintain legibility at small sizes.


## Layout & Spacing

### Grid

Mobile-first. Content width: 100% with 20px horizontal padding on each side. No breakpoint-driven column grids on mobile. On desktop (≥ 768px), content is centered with a maximum width of 480px.

### Spacing Scale

`4 · 8 · 12 · 16 · 20 · 24 · 32 · 48px`

| Use | Value |
|-----|-------|
| Gap between inline elements (badge + text) | 4–6px |
| Gap between stacked cards | 8–10px |
| Card internal padding | 16px |
| Screen horizontal padding | 20px |
| Section gap (header to first card) | 10px |
| Section-to-section gap | 20px |
| CTA area vertical padding | 12px top / 16px bottom |
| Page top padding | 12–14px below status bar |
| Bottom nav safe area | 20px below nav icons (home indicator clearance) |

### One Screen, One Decision

Each screen surfaces exactly one primary CTA. Secondary and ghost CTAs exist to defer or dismiss — never to present competing primary paths. The visual weight hierarchy must be: Primary CTA > Secondary (outlined pill) > Ghost (text-only pill). The three Decision options (채택 / 보류 / 무시) are the one case where three actions are simultaneously visible — they remain visually distinct by weight, not color.


## Elevation & Depth

Decision OS uses **surface color steps**, not drop shadows, to express depth.

| Layer | Surface | Shadow |
|-------|---------|--------|
| Page background | `surface-raised` (#F9F9F9) | None |
| Cards | `surface-card` (#F2F2F2) | None |
| App chrome (nav, sticky bars) | `surface-base` (#FFFFFF) | `border-top: 1px solid border-subtle` only |
| Bottom Sheet | `surface-base` (#FFFFFF) + `surface-overlay` scrim | None on sheet itself |
| Nav-plus FAB (+ button) | `accent-primary` | `box-shadow: 0 4px 16px rgba(0,0,0,0.25)` — the single elevation exception |

The nav-plus shadow is the only box-shadow used in the entire system. Its purpose is to float the + button above the nav bar visually, indicating it is an action, not navigation.


## Shapes

| Element | Radius |
|---------|--------|
| Card (SignalCard, QueueItem, LearningPathCard, list items) | 16px |
| Primary CTA button (pill) | 9999px |
| Secondary CTA button (pill) | 9999px |
| Bottom Sheet top corners | 24px (bottom corners flush) |
| Badge | 9999px |
| Timeline card, Honest Box | 12px |
| Option card (Outcome selection) | 14px |
| Phone frame (wireframe artifact) | 44px (not a product token) |

Shape is not used for brand expression. Consistent corner radii reduce visual noise — the system reads as calm because shapes are predictable.


## Components

Key-screen mockups: [mockups/wireframes-key-screens-2026-07-21.html](mockups/wireframes-key-screens-2026-07-21.html) (open in any browser). Spines win on any conflict with the mockups.

### Context Sticky Bar

Fixed to the bottom of the Research Review 상세 screen only. Sits above the bottom navigation.

**Structure (top to bottom):**
1. Context/engagement row (11px / text-secondary): "분析" label (disabled) or "추천" label (enabled)
2. Primary text row (13px / weight 600):
   - **Disabled:** "리뷰 내용을 먼저 읽어 주세요" — `text-secondary`. Recommendation withheld.
   - **Enabled:** Current Review recommendation summary (e.g., "지금 배울 것을 권장합니다") — `text-primary`
3. Primary CTA row: full-width pill button
4. Secondary CTA row (enabled state only): two ghost pills side by side — "Queue" and "Ignore"

**Disabled state:**
- Primary CTA: `text-disabled` (#D1D1D1) background, `text-primary` (#0D0D0D) label text, `cursor: not-allowed`; a lock icon (SVG, 14px) at label-left serves as a non-color disabled signal
- Primary CTA label copy: "Learn Now"
- Hint text below button (`id="ctx-hint"`): "추천 근거를 먼저 확인해 주세요 <span aria-hidden>↑</span>" (11px / text-secondary / centered)
- Secondary CTAs: hidden
- Recommendation text: withheld (replaced by neutral engagement prompt above)

**Enabled state:**
- Primary CTA: `accent-primary` background, `accent-foreground` text; label "Learn Now"
- Secondary CTAs visible: border `1.5px solid #E0E0E0`, text-secondary text; `min-height: 44px` each
- Recommendation text: revealed as primary text row

**Dynamic Type:** The bar uses no fixed pixel height. All vertical sizing is padding-driven. At Dynamic Type ≥ 150% (iOS/Android), the engagement/recommendation text row truncates to one line with "…"; full text remains accessible via `aria-label` on the CTA button. If bar height would exceed `40vh`, the secondary ghost pills collapse into a single "더보기" overflow.

**Activation trigger:** See EXPERIENCE.md — Component Patterns → Context Sticky Bar

---

### Signal Card

Home Daily Brief section item. Represents a single curated Signal — one technology or change bundled from multiple sources.

Surface: `surface-card`. Radius: 16px. Padding: 16px. Bottom margin between cards: 10px.

**Structure:**
- Title row: Signal title (16px / weight 600) + NEW badge (`accent-primary` bg, `accent-foreground` text, 10px/700/uppercase, on unseen Signals) + chevron icon (`text-tertiary`)
- Relevance tag row: AI-generated one-line relevance statement (12px / `text-secondary`) — always present, never empty
- Meta row: source count + estimated review time (11px / `text-tertiary`)

**NEW badge:** Displayed on Signals the user has not yet opened. Removed on first open.

---

### Queue Item

Queue tab item representing a Signal the user has scheduled for future learning.

**Structure:**
- Timing badge (top-left): "TODAY" / "THIS WEEK" / "LATER" (10px / uppercase / weight 700 / letter-spacing 0.5px). Badge background: `surface-card-alt` (#ECECEC); text: `text-secondary`.
- Signal title (15px / weight 600 / `text-primary`)
- Estimated review + learning time (12px / `text-secondary`)
- Reschedule text link (12px / `text-secondary` / underline): "일정 변경"
- Chevron icon (`text-tertiary`)

**Overdue state:** "미완료" badge (`status-warning` text / no background fill — text-only).

**Min-height:** 44px for the full item tap target.

---

### Outcome Card

Outcome 입력 screen option card. One of four cards in a radio group.

**States:**
- Unselected: `surface-card` bg, `border-card` (#DCDCDC) 1px border, `text-primary` label
- Selected: `surface-card` bg, `accent-primary` (#0D0D0D) 1.5px border, `text-primary` label

**Dimensions:** `border-radius: 14px`. Padding: 16px. `min-height: 52px`.

**Four cards (fixed order):**
1. Completed — "학습을 완료했습니다"
2. Applied — "실제 프로젝트에 적용했습니다"
3. Dropped — "학습을 중단했습니다"
4. Not Useful — "현재 상황에 맞지 않았습니다"

Selected state is indicated by border only, not fill — to avoid conflating selection with status.

---

### Learning Path Card

Learning Path screen resource item. Tappable — opens external URL.

Surface: `surface-card`. Radius: 16px. Padding: 16px. Bottom margin: 8px.

**Structure:**
- Resource type label (10px / uppercase / weight 700 / `text-secondary` / letter-spacing 0.5px)
- Resource title (15px / weight 600 / `text-primary`)
- Descriptor (13px / `text-secondary`)
- External link indicator: chevron-external icon (`text-tertiary`), pinned right

**Five resource types (fixed order):** 공식 문서 · 핵심 자료 · GitHub · 실습 예제 · 적용 아이디어

---

### Memory Timeline Item

Vertical timeline list. Left edge has a persistent 2px / `border-subtle` vertical spine.

**Dot sizes:** 12×12px circles, 2px `surface-raised` ring (creates separation from spine).
- Signal: `text-secondary` fill
- Review / Decision: `text-primary` (dark) fill
- Outcome: color + glyph (both required — glyph ensures color-independent readability):
  - Completed: `status-positive` fill + "✓" glyph (7px, white, centered)
  - Applied: `status-positive` fill + "→" glyph (7px, white, centered)
  - Dropped: `text-primary` fill + "✕" glyph (7px, white, centered)
  - Not Useful: `text-secondary` fill + "−" glyph (7px, white, centered)

**Card shell:** `surface-card` bg / radius 12px / padding 12×14px.
- Type label: 10px / uppercase / weight 700 / text-secondary / letter-spacing 0.6px
- Title: 14px / weight 600 / text-primary
- Date: 12px / text-secondary (dates are functional information — text-tertiary contrast is insufficient)

Items are tappable — tap navigates to the source screen for that entry.

**Month dividers:** horizontal rule with centered month label (11px / text-secondary).

---

### Honest Box

Distinct container within Research Review 상세. Not a card — a section.

**Background:** `surface-honest-box` (#F5F5F5) — lighter step between `surface-card` and `surface-base`, intentionally lower contrast than cards to signal supplementary status.

**Radius:** 12px. **Padding:** 14px 16px. **Bottom margin:** 12px.

**Label:** "AI가 확인하지 못한 정보" — 11px / uppercase / weight 700 / text-secondary / letter-spacing 0.5px / 6px bottom margin.

**Body:** 13px / text-secondary / line-height 1.5.

Tone: honest and direct, not apologetic. The box is a feature, not an admission of failure.

Never omitted from a Review when there is uncertainty, even if the uncertainty is minor.

**Position within Research Review 상세:** Section 13 — after 참고 출처. Uncertainty types disclosed inline within section 10 (위험 요소); HonestBox consolidates residual unconfirmed information.

**Graduated severity:** High-consequence entries (experimental API with breaking-change history; no official docs for a production-critical feature) carry `status-warning` (#D97706) as a left border accent (3px). Standard entries carry no border accent. The AI backend determines severity tier and passes it as a flag.


## Do's and Don'ts

### Colors

| Do | Don't |
|----|-------|
| Use `accent-primary` (#0D0D0D) as the single primary action color | Add a second accent color (blue, brand color) for CTAs |
| Express `status-uncertain` through `text-secondary` text tone | Create a yellow or orange "uncertain" state background color |
| Use `status-positive` for confirmed-positive outcomes only | Use `status-positive` for loading success toasts or "saved" confirmations |
| Keep the surface palette monochromatic; let content carry meaning | Add color fills to cards to differentiate content categories |

### Typography

| Do | Don't |
|----|-------|
| Use large, bold screen titles (28–30px / 700) | Use 20px-or-below headings as the primary screen identifier |
| Left-align all body and card text | Center body copy outside of Bottom Sheet titles |
| Set `letter-spacing` explicitly on all uppercase caption/badge labels | Leave uppercase text at default tracking (it will look cramped) |
| Use weight contrast (700 vs 500) to establish hierarchy within the same size | Use color contrast to carry typographic hierarchy |

### Components

| Do | Don't |
|----|-------|
| Keep exactly one `btn-primary` per screen | Place two `btn-primary` elements on the same scrollable view |
| Show `ContextStickyBar` in disabled state (gray CTA, neutral engagement text) until key sections confirmed | Show the recommendation text in the disabled state — it anchors a conclusion before evidence is read |
| Show `HonestBox` in every Review that contains uncertainty | Omit HonestBox from a Review to appear more confident — uncertainty disclosure is a feature, not a disclaimer |
| Keep Bottom Sheet to a single layer | Stack a second Bottom Sheet on top of the first |

### Visual Language

| Do | Don't |
|----|-------|
| Use generous whitespace as the primary design signal of "premium" | Fill empty space with illustrative elements or secondary content |
| Express AI involvement through calm, factual copy | Decorate AI sections with gradient glows, pulsing borders, or neon accents |
| Reference Cal AI's typography rhythm and Linear's information hierarchy | Mimic information-dense dashboard layout (dense tables, small text, category tabs, cluttered navigation) |

### Anti-patterns (hard prohibitions)

- **No AI neon / gradients / glow effects.** AI involvement is invisible in the visual layer. The brand is the calm it creates, not the AI powering it.
- **No ChatGPT-style chat UI.** No centered chat bubble layout, no persistent AI input bar on any screen, no floating chat FAB.
- **No 정보 과부하 홈페이지 style.** No dense information grids, no small-print disclaimer tables embedded in UI cards, no sidebar/category navigation.
- **No complex admin dashboard layout.** Multiple simultaneous metric charts, data-dense tables, and sidebar navigation are all prohibited.
- **No gamification.** No streaks, achievement badges, progress percentages for engagement, or celebratory animations on routine saves.
- **No auto-confirmation of Decisions.** The product may never select Learn Now, Queue, or Ignore on the user's behalf. Decision agency belongs exclusively to the user.
