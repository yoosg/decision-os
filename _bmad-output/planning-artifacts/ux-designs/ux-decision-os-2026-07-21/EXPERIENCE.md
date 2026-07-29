---
title: Decision OS — AI Research Playbook EXPERIENCE.md
status: final
created: 2026-07-21
updated: 2026-07-22
version: "2.1.0"
design-ref: DESIGN.md
sources:
  - _bmad-output/planning-artifacts/ux-designs/ux-decision-os-2026-07-21/.memlog.md (canonical decisions log)
  - _bmad-output/planning-artifacts/prds/prd-decision-os-2026-07-21/prd.md
  - docs/ai-research-playbook-prd-guide.md
  - docs/decision-os-manifesto.md
---

# Decision OS — AI Research Playbook Experience Specification

## Foundation

**Platforms:**
- **Web (Next.js):** Mobile-first web application. Primary viewport: 375–430px. Desktop (≥ 768px): centered single-column, max 480px content width.
- **Native app (Flutter):** iOS 14+ and Android 8.0+ (API 26+). Flutter 3.x, released alongside the web product. Feature parity with web at MVP. Behavioral delta between platforms documented in the Platform Patterns section.

**Design system:** Material 3 with full ThemeData token override. All `ColorScheme`, `TextTheme`, and `ShapeTheme` defaults are replaced with DESIGN.md values — no Material 3 defaults are visible to the user. Rationale over custom-from-scratch Flutter widgets: Material 3 provides correct safe-area handling, platform gesture behavior, and screen reader semantics out of the box; full token override makes the output visually identical to the DESIGN.md spec.

**Paradigm:** Inbox-first, event-driven. The product surfaces what requires attention — users do not come to ask questions. The central interface metaphor is an operating system inbox, not a news feed, a chat, a dashboard, or a learning management system. Within the AI Research Playbook, the primary vehicle for surfacing attention is the Daily Brief: a curated, personalized briefing generated each morning by the AI Research OS.

**Core concept:** 매일 아침 AI CTO가 오늘 배워야 할 기술을 브리핑해주는 Daily Learning Loop. The product does not show fifty AI articles. It recommends one technology to understand today, and guides the user through understanding → decision → learning → application.

**Core loop (all interactions flow through this):**
```
Signal (Event)
  ↓
Research Review
  ↓
Decision (Learn Now / Queue / Ignore)
  ↓
Learning Path → Outcome
  ↓
Memory → Next Daily Brief (improved personalization)
```

**UX principles:**
1. **One Screen, One Decision.** Each screen presents exactly one primary action. Supporting actions defer or dismiss.
2. **Review before Action.** No consequential action (Learn Now, queue scheduling, etc.) is taken without a preceding Research Review.
3. **Chat is not primary.** Contextual Chat is a secondary capability available only within Research Review 상세. It never appears on Home, Queue, History, or Profile.
4. **Minimize information overwhelm.** AI Research produces enormous daily volume. The product's job is to reduce the decision surface to exactly what matters for this user today. No feed, no infinite scroll, no "50 articles about AI."
5. **Honest AI.** AI uncertainty is always surfaced, never hidden. The {components.HonestBox} is a feature, not a disclaimer. Experimental tech, missing official docs, and compatibility unknowns must be disclosed.


## Information Architecture

**Navigation model:** 4-tab bottom navigation, persistent across all top-level screens.

| Tab | Label | Icon | Entry point |
|-----|-------|------|-------------|
| 1 | 홈 | Home icon | Home (Daily Brief) |
| 2 | 큐 | Queue icon | Queue (Scheduled learning items) |
| 3 | 히스토리 | Clock/timeline icon | History / Memory Timeline |
| 4 | 프로필 | Person icon | Profile / Learning preferences |

There is no + tab in MVP. The + action (user-submitted analysis candidates) is explicitly deferred to V2.

### Screen Inventory

| Surface | Reached from | Purpose |
|---------|-------------|---------|
| **Home (Daily Brief)** | App open / push notification tap | Daily Brief heading + SignalCard list; today's recommended technologies |
| **Research Review 상세** | Home SignalCard tap; Queue item tap | Full 13-section Research Review + {components.ContextStickyBar} |
| **Learning Path** | Research Review → Learn Now CTA | Ordered learning resources for the chosen technology |
| **Outcome 입력** | Push notification; Learning Path completion prompt | Record learning result (Completed / Applied / Dropped / Not Useful) |
| **Queue** | 큐 탭 | Today / This Week / Later grouped learning items; reschedule actions |
| **History / Memory Timeline** | 히스토리 탭 | Chronological Signal → Review → Decision → Outcome linked entries |
| **Memory Chain 상세** | History Timeline item tap | Full immutable chain for a single Decision event |
| **Profile** | 프로필 탭 | Learning preferences, notification settings, onboarding data management |
| **Profile Edit** | Profile → 편집 | Edit Role, Experience, Tech Stack, Project/Goal, Interests, Daily Learning Time |
| **Onboarding Welcome** | First app launch | Product value proposition + start |
| **Onboarding — Role** | Welcome → 시작하기 | Role selection step |
| **Onboarding — Experience** | Role complete | Experience level selection |
| **Onboarding — Tech Stack** | Experience complete | Multi-select tech stack |
| **Onboarding — Project/Goal** | Tech Stack complete | Current project or learning goal |
| **Onboarding — Interests** | Project/Goal complete | Technology interest areas |
| **Onboarding — Daily Learning Time** | Interests complete | Available daily learning time |
| **Onboarding — First Brief Generating** | Profile complete | Full-screen loading: "Daily Brief 생성 중" |
| **Contextual Chat** | Button within Research Review 상세 only | Context-grounded supplementary conversation |

**Navigation rule:** Chat entry is only possible from within Research Review 상세. There is no Chat entry from Home, Queue, History, or Profile. No floating chat FAB exists anywhere in the product. The Queue tab contains only items the user has previously scheduled — it is not an editorial feed.

### Flutter Routing

**Router:** GoRouter with `StatefulShellRoute.indexedStack`. Each tab has its own `GlobalKey<NavigatorState>` so tab history is independent and persists across tab switches.

| Tab index | GoRouter branch | Root path |
|-----------|-----------------|-----------|
| 0 | Home branch | `/home` |
| 1 | Queue branch | `/queue` |
| 2 | History branch | `/history` |
| 3 | Profile branch | `/profile` |

**Screen navigation within tabs:**
- Home → Research Review 상세: push `/home/review/:signalId` within the Home branch
- Research Review 상세 → Learning Path: push `/home/review/:signalId/learning-path`
- Learning Path → Outcome 입력: push `/home/review/:signalId/outcome`
- Queue → Research Review 상세: push `/queue/review/:signalId` within the Queue branch (independent stack from Home branch)
- Contextual Chat: push `/home/review/:signalId/chat` within the same branch stack

**Onboarding flow:** Separate `GoRoute` outside the `StatefulShellRoute`. Path: `/onboarding`. Sub-steps are in-place widget swaps within the Onboarding screen (not pushed routes). Back navigation between onboarding steps is allowed via back chevron. Back navigation on the First Brief Generating screen is suppressed via `PopScope(canPop: false)`.

**Deep link routing (push notification tap):**
GoRouter redirects the notification deep link to `/home`. The Home screen then highlights the relevant SignalCard. Direct navigation to `/home/review/:signalId` bypassing Home is prohibited — Home is the notification center.

**Initial route logic:** On app launch, check onboarding completion state from local storage. Route to `/onboarding` if incomplete; `/home` if complete.


## Voice and Tone

### Principles

- **Calm and factual.** Technology decisions are consequential. Anxiety-inducing or urgency-first language makes users feel behind. Every piece of copy defaults to the neutral register of a trusted technical advisor.
- **Possibility first.** Review titles and notification copy lead with the actionable possibility or relevance framing, not a declarative conclusion. "MCP 통합이 현재 프로젝트에 적용 가능합니다" — not "MCP를 지금 배워야 합니다" (imperative) and not "MCP에 대한 분석 결과를 안내드립니다" (process). AI Review titles must use relevance framing ("관련성이 있습니다", "적용 가능성이 확인됐습니다", "학습 권장 기술로 확인됐습니다") rather than declarative imperatives. This is a hard constraint on AI title generation — not a stylistic preference.
- **AI = reference, not authority.** All AI-generated content is framed as a recommendation or possibility, never as a directive. The user is the decision-maker.
- **Honest Box tone: direct, not apologetic.** "AI가 확인하지 못한 정보" is stated neutrally. It is not a warning and does not imply the Review is unreliable — it means the AI is being transparent about the limits of its knowledge for this specific technology.
- **Action labels are verbs with intent.** "<span lang='en'>Learn Now</span>" not "확인". "<span lang='en'>Queue</span>: <span lang='en'>This Week</span>" not "나중에". "분석 중입니다. 앱을 닫아도 됩니다." not "잠시만 기다려 주세요...".

### Microcopy Reference Table

| Do | Don't |
|----|-------|
| "오늘 배울 기술로 추천합니다" | "지금 배우지 않으면 뒤처집니다" |
| "현재 프로젝트에 적용 가능성이 확인됐습니다" | "반드시 배워야 합니다!" |
| "<span lang='en'>AI</span>가 확인하지 못한 정보" | "경고: 불확실한 정보가 있습니다" |
| "분석 중입니다. 앱을 닫아도 됩니다." | "잠시만 기다려 주세요..." |
| "<span lang='en'>Learn Now</span>" | "승인" / "확인" / "시작" |
| "<span lang='en'>Queue</span>: <span lang='en'>This Week</span>" | "나중에 보기" / "건너뛰기" |
| "<span lang='en'>Ignore</span>" | "취소" / "삭제" |
| "<span lang='en'>AI</span> 분析 결과는 참고 정보입니다" | "100% 정확한 분析 결과입니다" |
| "학습 결과를 기록해 주세요" | "결과를 빠르게 입력해 주세요!" |
| "기록하기" (<span lang='en'>Outcome</span> 확인 primary CTA) | "저장" / "확인" / "제출" |
| "<span lang='en'>Daily Brief</span>를 받아보실 수 있습니다" | "알림을 반드시 허용해 주세요" |

### Language

`lang="ko"` on the `<html>` root element. Ensures correct Korean text rendering, hyphenation, and screen reader pronunciation.

**English-origin proper nouns** used within Korean body copy must carry `lang="en"` on their inline element so Korean screen readers apply correct phoneme rules. Exhaustive list for this product: `Review`, `Signal`, `Memory`, `Learn Now`, `Queue`, `Ignore`, `Daily Brief`, `Learning Path`, `Outcome`, `NEW` (badge), `OS`, `Applied`, `Completed`, `Dropped`. The product uses `<span lang="en">AI</span>` throughout for the AI abbreviation. Technology proper nouns (LangGraph, MCP, Claude Code, GitHub, Reddit, HN, YouTube, FastAPI) also carry `lang="en"` inline treatment.


## Component Patterns

Behavioral specifications for all components referenced in DESIGN.md. Visual specs (surface colors, border-radius, typography scale) are in DESIGN.md — this section defines behavior, activation logic, and interaction constraints.

---

### Context Sticky Bar

**Where:** Research Review 상세 screen only. Fixed to the bottom edge, above the bottom navigation.

**Content:**
- **Disabled state:** Shows a neutral engagement prompt above the CTA row: "리뷰 내용을 먼저 읽어 주세요." The recommendation is deliberately withheld. Displaying it before evidence is read creates a false certainty anchor that undermines every subsequent calibration mechanism.
- **Enabled state:** Reveals the Review's primary recommendation summary above the CTA row (e.g., "지금 배울 것을 권장합니다"). Context label "추천" (11px / `text-secondary`) appears above the recommendation text.

**Disabled state (initial):**
- Primary CTA: {colors.text-disabled} (#D1D1D1) background, {colors.text-primary} (#0D0D0D) label text, `aria-disabled="true"`, `aria-label="Learn Now — 비활성화됨. 리뷰 내용을 먼저 읽어 주세요"`, `aria-describedby="ctx-hint"`, non-interactive; lock icon (SVG, 14px) at label-left as non-color disabled signal
- Hint text (`id="ctx-hint"`): "추천 근거를 먼저 확인해 주세요 <span aria-hidden='true'>↑</span>" (11px / `text-secondary` / centered)
- Secondary CTAs (<span lang="en">Queue</span> / <span lang="en">Ignore</span>): hidden
- `aria-live="polite"` status region (visually hidden, always in DOM): empty in disabled state; populated with "<span lang='en'>Learn Now</span> 버튼을 사용할 수 있습니다" on transition to enabled

**Activation trigger:** The bar transitions to enabled state when the user has engaged with sections 1–6 (한 줄 정의 → 핵심 개념 → 해결하는 문제 → 왜 지금 중요한가 → 기존 기술 차이 → 사용자 관련성) AND sections 10 (위험 요소) AND 11 (추천 이유). Each section is marked "seen" when its heading or first meaningful element **enters the viewport OR receives keyboard/screen reader focus** — whichever comes first. This ensures VoiceOver and TalkBack users who navigate without scrolling also trigger activation.

**Short Review exception:** If the Review content fits in a single viewport without scrolling, the bar may be enabled from load — but **only if both conditions are met**: (a) the Review contains no HonestBox entry, AND (b) the technology has no experimental or compatibility risk flags. Reviews with any uncertainty disclosure or active risk flags must require section-engagement activation regardless of content length. The AI backend enforces this gate and passes a flag to the frontend; the frontend enables the bar based on that flag, not on viewport detection alone.

**Enabled state:**
- Primary CTA: {colors.accent-primary} background, {colors.accent-foreground} text; label "<span lang='en'>Learn Now</span>"
- Secondary CTAs visible: "<span lang='en'>Queue</span>" (`aria-label="Queue — 이 Signal을 큐에 저장"`) and "<span lang='en'>Ignore</span>" (`aria-label="Ignore — 이 Signal을 무시"`) as ghost pills; `min-height: 44px` each. All three CTAs must be `<button>` elements.
- When the user taps Queue, a sub-selection bottom sheet opens (Today / This Week / Later) before the decision is committed.
- Recommendation text revealed above CTA row

**DOM position for screen readers:** The {components.ContextStickyBar} element is placed after the last content section (section 13 — HonestBox) in the DOM, even though it is visually fixed via CSS `position: fixed`. This ensures VoiceOver and TalkBack users encounter the CTA after reading all sections in natural focus order, not before.

**Dynamic Type:** No fixed pixel heights; all vertical sizing is padding-driven. At Dynamic Type ≥ 150%, engagement/recommendation text truncates to one line with "…"; full text accessible via `aria-label`. If bar height would exceed `40vh`, secondary ghost pills collapse into a single "더보기" overflow.

**Forced scroll prohibition:** The disabled state is informational, not a gate. If a user attempts to tap the disabled CTA, the hint text is the only feedback — no shake animation, no error toast.

**Reduce Motion:** Skip the activation transition animation (fade / slide) when the system `prefers-reduced-motion` flag is set.

---

### Signal Card

**Where:** Home (Daily Brief section).

**What it represents:** A single Signal — one technology or change bundled from multiple sources (Official Blog, GitHub, Reddit, HN, YouTube). A Signal is not a link to one article; it is a curated Decision Event about a technology.

**Structure:**
- Top row: Signal title (16px / weight 600) + <span lang="en">NEW</span> badge ({colors.accent-primary} bg, {colors.accent-foreground} text, 10px/700/uppercase) for unseen items + chevron icon ({colors.text-tertiary})
- Personalized relevance tag row: 12px / `text-secondary` — AI-generated one-line relevance statement for this user's profile (e.g., "현재 LangGraph 프로젝트에 직접 적용 가능"). Tag is always present, never empty.
- Meta row: 11px / `text-tertiary` — source count ("출처 5개"), estimated review time ("읽기 약 5분")

**NEW badge:** Displayed on Signal cards the user has not yet opened. Badge text: "<span lang='en'>NEW</span>". Removed on first open.

**Tap behavior:** Tapping the card navigates to Research Review 상세.

**Priority order (top of list = highest priority):**
1. NEW Signals (unseen) — ordered by personalized relevance score
2. Previously queued Signals that surface in today's brief
3. Returned Signals (previously Queued → Today, now appearing on Home)

**Empty state:** See State Patterns — Home / Daily Brief states.

**Composite aria-label:** `aria-label="[Signal 제목], NEW, 출처 [N]개, 읽기 약 [N]분"` — do not rely on DOM concatenation; provide the composite label explicitly.

---

### Research Review Sections

**Where:** Research Review 상세 screen. This is the primary content screen of the AI Research Playbook.

**Structure:** 13 required sections displayed in the following order. Each section has its own heading. The heading hierarchy governs screen reader navigation.

| Order | Section key | Heading level | Notes |
|-------|-------------|---------------|-------|
| 1 | 한 줄 정의 | `h2` | One-sentence definition of the technology. No jargon. |
| 2 | 핵심 개념 설명 | `h2` | Core concepts explained so a user can understand them without prior knowledge. |
| 3 | 해결하는 문제 | `h2` | The concrete problem this technology solves. |
| 4 | 왜 지금 중요한가 | `h2` | Why this technology matters now (timing context). |
| 5 | 기존 기술과의 차이 | `h2` | Comparison to existing/alternative approaches. `h3` per technology compared. |
| 6 | 사용자 관련성 | `h2` | Personalized relevance statement generated from the user's Role + Tech Stack + Project. This section is never generic. Label: "현재 프로필 기준" (11px / text-secondary). |
| 7 | 학습 목표 | `h2` | What the user will be able to do after learning this technology. Bulleted list. |
| 8 | 예상 학습 시간 + 난이도 | `h2` | Estimated time to basic competency; difficulty level (입문 / 중급 / 고급). |
| 9 | 실무 적용 가능성 | `h2` | How the technology can be applied in the user's actual work or project context. |
| 10 | 위험 요소 | `h2` | Risks, caveats, known limitations. Experimental status, missing docs, compatibility issues. Required for bar activation. |
| 11 | 추천 이유 | `h2` | Personalized recommendation reason. Required for bar activation. Context label "추천" (11px / text-secondary) in the ContextStickyBar mirrors this section's conclusion. |
| 12 | 참고 출처 | `h2` | All sources bundled in this Signal: Official Blog, GitHub, Reddit, HN, YouTube links as tappable items. |
| 13 | HonestBox | — | "AI가 확인하지 못한 정보" — see HonestBox spec. Always present when any uncertainty exists. |

**Screen heading hierarchy:**
- `h1` = Signal / Review title (screen-level)
- `h2` = each of the 13 section headings (in order above)
- `h3` = sub-items within sections (e.g., individual technology comparisons within section 5; individual learning steps within section 7)

**Section-engagement tracking for bar activation:**
Each section heading element carries a `data-section-key` attribute. The frontend observes IntersectionObserver on each heading. When a heading enters the viewport (threshold: 0.1) or receives focus, the section is marked "seen" in an in-memory set. The ContextStickyBar checks whether the required set (sections 1–6, 10, 11) is complete before enabling. The backend passes a `bar_gate_override` flag that can force-enable or force-disable the bar regardless of client-side engagement; the client checks this flag first.

**HonestBox position:** Section 13, after section 12 (참고 출처). This is an exception to the original insurance product HonestBox placement (which appeared after Recommendation, before Evidence). In the AI Research Review, the 13-section structure is designed so that uncertainty and risks are disclosed within section 10 inline, and the HonestBox at the end consolidates any residual unconfirmed information. The bar activation requires section 10 engagement, ensuring users encounter risk disclosures before committing.

**ContextualChat entry:** Below section 13 (HonestBox), a text-link CTA: "<span lang='en'>AI</span>에게 질문하기" (13px / `text-secondary` / underline). This is the only entry point to Contextual Chat. It is low-prominence — it must not compete visually with the primary Decision CTA in the ContextStickyBar.

---

### Learning Path Card

**Where:** Learning Path screen. Reached after "Learn Now" decision is committed.

**What it represents:** An AI-generated, ordered set of learning resources for the chosen technology, tailored to the user's current profile (Tech Stack + Project/Goal + Experience level).

**Structure (ordered top to bottom, always in this sequence):**
1. 공식 문서 — link to official documentation with a short descriptor
2. 핵심 자료 — curated essential reading (blog post, guide, or article)
3. GitHub — repository or example codebase with description
4. 실습 예제 — hands-on tutorial or code exercise
5. 적용 아이디어 — personalized application idea for the user's current project or goal (e.g., "기존 LangGraph 워크플로우에 MCP 서버 연결해보기")

Each resource is a tappable item that opens the external URL. Each item shows:
- Resource type label (10px / uppercase / `text-secondary` / letter-spacing): 공식 문서 / 핵심 자료 / GitHub / 실습 예제 / 적용 아이디어
- Resource title (15px / weight 600 / `text-primary`)
- Short descriptor (13px / `text-secondary`)
- External link indicator (chevron-external icon, `text-tertiary`)

**Generating state:** Before the Learning Path is ready, the screen shows "학습 경로를 생성하는 중입니다." with a three-dot pulse animation. Copy does not say "잠시만 기다려 주세요."

**Post-learning Outcome prompt:** After the user has visited external resources and returns to the app, the Learning Path screen shows a persistent but non-blocking prompt at the bottom: "학습을 완료했나요? 결과를 기록해 주세요." with a CTA: "결과 기록하기" (routes to Outcome 입력 screen). This prompt appears only after the user has returned from at least one external resource tap. It is not a bottom sheet and does not block the Learning Path content.

---

### Queue Item

**Where:** Queue tab, grouped under Today / This Week / Later headings.

**What it represents:** A Signal that the user has scheduled for future learning.

**Structure:**
- Timing badge (top-left): "TODAY" / "THIS WEEK" / "LATER" (10px / uppercase / weight 700 / letter-spacing 0.5px). Badge background: {colors.surface-card-alt} (#ECECEC); text: {colors.text-secondary}.
- Signal title (15px / weight 600 / `text-primary`)
- Estimated review + learning time (12px / `text-secondary`)
- Reschedule action (text link, 12px / `text-secondary` / underline): "일정 변경" — tapping opens a sub-selection sheet (Today / This Week / Later)
- Chevron icon indicating tap navigates to Research Review 상세

**Overdue items:** Queue items scheduled as "Today" that are still present after midnight show an "미완료" badge ({colors.status-warning} text, no background fill — text-only, to avoid alarming the user). The badge is informational, not alarming.

**Tap behavior:** Tapping any Queue Item navigates to the Research Review 상세 for that Signal. If the user has previously read the Review, the ContextStickyBar may activate earlier (see Short Review exception above). The prior-read state is passed as a backend flag.

**Reschedule bottom sheet:** Three pill options — Today / This Week / Later — with selected state indicated by {colors.accent-primary} border (not fill). Selecting a new timing updates the badge immediately (optimistic update) and persists asynchronously.

---

### Outcome Card

**Where:** Outcome 입력 screen. Reached from push notification, Learning Path post-completion prompt, or History timeline.

**What it represents:** The user's recorded result after a Learn Now decision.

**Structure:**
- Screen heading: "학습 결과를 기록해 주세요" (28px / weight 700)
- Signal title reference (13px / `text-secondary`): which Signal this Outcome closes
- Outcome state selection (radio group — see Accessibility Floor for aria spec): four options displayed as option cards ({rounded.option-card} = 14px)
  - Completed — "학습을 완료했습니다"
  - Applied — "실제 프로젝트에 적용했습니다"
  - Dropped — "학습을 중단했습니다"
  - Not Useful — "현재 상황에 맞지 않았습니다"
- Optional feedback fields (below radio group, always visible but not required):
  - 유용했는가 (toggle: 예 / 아니오)
  - 실제 학습 시간 (text input: 숫자 + 분 unit)
  - 메모 (multiline text input, placeholder: "적용 방식, 막힌 부분, 다음 단계 등을 남겨두세요")
- Primary CTA: "기록하기" (full-width pill, {colors.accent-primary})

**Applied path (additional prompt):** When "Applied" is selected, an additional prompt appears below the selection card: "어떤 프로젝트에 적용했나요? (선택)" — single-line text field. Not required; contributes to Memory personalization.

**Outcome written to Memory:** On "기록하기" tap, the full Decision chain (Signal + Review + Decision + Outcome) is written to Memory as an immutable record. A non-blocking toast (3 seconds): "결과가 기록됐습니다. 다음 Daily Brief에 반영됩니다." appears. The user is routed to Home.

---

### Honest Box

**Where:** Research Review 상세 — section 13. Always present when the Review contains any uncertainty.

**Omission prohibition:** The {components.HonestBox} is never omitted from a Review that contains uncertainty, even if the uncertainty is minor. An AI Review that omits uncertainty to appear more confident violates the core product principle.

**Content authored by:** AI Review generation backend. The UX layer surfaces it as-is without summarizing or softening.

**Section heading copy:** "AI가 확인하지 못한 정보" — not "주의사항", not "경고", not "면책".

**AI Research-specific uncertainty types:** The backend may disclose any of the following categories (not exhaustive — the AI determines what to disclose):
- 실험적 기술 상태: "이 기능은 아직 실험적(experimental) 단계이며, API가 변경될 수 있습니다."
- 공식 문서 부재: "현재 공식 문서가 완전하지 않아 일부 정보는 커뮤니티 자료에서 수집했습니다."
- 호환성 불명확: "특정 버전 또는 환경에서의 호환성이 확인되지 않았습니다."
- 정보 최신성: "이 분析은 [날짜] 기준이며, 이후 업데이트가 있을 수 있습니다."

**Graduated severity:** The AI backend passes a `severity` flag ("standard" | "high") per HonestBox entry. High-severity entries (e.g., experimental API with breaking-change history; no official docs for a production-critical feature) render with a `status-warning` left-border accent (3px, {colors.status-warning}). Standard entries (e.g., unconfirmed community-reported compatibility) render with no border accent. The frontend does not determine severity — it only renders what the backend flags. This prevents users from treating all HonestBox content as uniform boilerplate.

---

### Contextual Chat

**Where:** Available only from within Research Review 상세. Not available from Home, Queue, History, Profile, or any other screen. No floating chat FAB exists anywhere in the product.

**Entry trigger:** A secondary text-link CTA within Research Review 상세 — "<span lang='en'>AI</span>에게 질문하기" (13px / `text-secondary` / underline) placed below the HonestBox (section 13). This is not a pill button; it is a low-prominence affordance so as not to compete with the primary Decision CTA in the ContextStickyBar.

**Context passing:** The system automatically passes the current Research Review's context object as the conversation seed (Signal ID → Research Review content + user profile). The first AI message acknowledges the context: e.g., "이 Review에 대해 궁금한 점을 물어보세요."

**Close:** Back navigation (tap back or Android back gesture) returns to Research Review 상세 at the same scroll position. The Chat screen pushes onto the navigation stack; it does not open as a modal or bottom sheet.

**Session persistence (v1):** Conversation is not persisted across sessions or app closes. Each entry to Contextual Chat from a given Research Review starts fresh. This prevents stale context from corrupting future conversations.

**Relationship to Decision:** Chat answers questions but cannot execute Decisions. The only path to a Decision is the {components.ContextStickyBar} on Research Review 상세. Chat does not have a "Learn Now" or "Queue" CTA within it.

---

### Memory Timeline Item

**Where:** History / Memory Timeline screen (히스토리 탭).

**Adapted for AI Research:** The four-node chain maps as follows:
- **Signal** (Event node) — the technology or change that triggered the Decision Loop
- **Research Review** (Review node) — AI Research Review generated for this Signal
- **Decision** (Decision node) — Learn Now / Queue / Ignore + timestamp
- **Outcome** (Outcome node) — Completed / Applied / Dropped / Not Useful + optional memo

**Sequence within a chain:** Signal (circle dot) → Research Review (rectangle card with dark dot) → Decision (rectangle card with dark dot, user annotation) → Outcome (circle dot, colored and glyph-differentiated by result).

**Outcome dot glyphs (non-color differentiators):**
- Completed (positive completion): {colors.status-positive} fill + "✓" glyph centered (7px, white)
- Applied (applied to project): {colors.status-positive} fill + "→" glyph centered (7px, white)
- Dropped (abandoned): {colors.text-primary} fill + "✕" glyph centered (7px, white)
- Not Useful (negative assessment): {colors.text-secondary} fill + "−" glyph centered (7px, white)

**Linkable items:** Each item is tappable and navigates to the source screen. If the source screen content is archived (i.e., the Signal has aged out of the Daily Brief cycle), a read-only view renders the complete Research Review content with a "보관된 Review" banner — full content is preserved, not summarized.

**Empty state:** See State Patterns — History / Memory states.


## State Patterns

### Home / Daily Brief States

| State | Trigger | Display |
|-------|---------|---------|
| **Daily Brief — 준비됨** | Daily Brief generation complete; user opens app or taps notification | Section heading: "오늘의 AI CTO 브리핑" (22px / weight 700) + date + one or more SignalCards. Default primary operating state. |
| **Daily Brief — 생성 중** | Brief generation in progress (e.g., after profile complete; or morning regeneration running) | "오늘의 Daily Brief를 생성하는 중입니다." with three-dot pulse animation. Copy does not say "잠시만 기다려 주세요." Primary CTA: none — the screen is informational only. Push notification sent when Brief is ready. |
| **Daily Brief — 생성 실패** | AI analysis does not complete or returns a job error | Error state copy: "오늘의 Daily Brief를 생성하지 못했습니다." Primary CTA: "다시 시도하기". If user closed the app: push notification "Daily Brief를 생성하지 못했습니다. 앱에서 확인해 주세요." |
| **Daily Brief — 오늘 신규 Signal 없음** | Daily Brief generation completes but no new high-relevance Signals found for the user today | Message: "오늘은 새로운 Signal이 없습니다. 어제 Queue에 저장한 항목을 이어서 학습할 수 있습니다." CTA: "큐 보기" (routes to Queue tab). No empty illustration. Calm, not apologetic. |
| **Cold start — 첫 Daily Brief 대기** | Onboarding complete, first Brief generating | See Onboarding States — First Brief Generating. |
| **All Signals seen** | User has opened all today's Signals | Below SignalCard list (cards now without NEW badge): "오늘 브리핑을 모두 확인했습니다." Caption. Calm, not celebratory. Queue CTA appears if user has queued items. |

### Research Review States

| State | Trigger | Display |
|-------|---------|---------|
| **Research Review — ContextStickyBar disabled** | User opens Research Review; has not yet engaged with required sections | Bar in disabled state (gray primary CTA, lock icon, hint text). Neutral engagement text: "리뷰 내용을 먼저 읽어 주세요." Section 6 (사용자 관련성) shows a personalized label: "현재 프로필 기준" above the generated text. |
| **Research Review — ContextStickyBar enabled** | User has engaged with sections 1–6, 10, and 11 | Bar transitions to enabled. Recommendation text revealed. Learn Now / Queue / Ignore CTAs active. `aria-live` status region announces transition. |
| **Research Review — 생성 중** | Signal selected but Review generation still in progress | Full-screen loading state. Copy: "Research Review를 생성하는 중입니다. 앱을 닫아도 됩니다." CTA: "홈으로 돌아가기." Push notification sent when Review is ready. |
| **Queue sub-selection** | User taps Queue CTA in enabled ContextStickyBar | Bottom sheet opens over Research Review with three pill options: Today / This Week / Later. Title: "언제 학습할까요?" Sheet closes on selection; Decision committed immediately. |
| **Learn Now → Learning Path** | User taps Learn Now | Navigate to Learning Path screen. Research Review remains accessible via back navigation. |
| **Ignore committed** | User taps Ignore | Research Review archived. Removed from Home and Queue. Non-blocking toast (3 seconds): "이 Signal은 히스토리에서 다시 볼 수 있습니다." Memory records Signal + Ignore decision. |

### Queue States

| State | Trigger | Display |
|-------|---------|---------|
| **Queue — empty** | User has no queued items | Copy: "큐에 저장된 학습 항목이 없습니다. Signal을 읽고 Queue를 선택하면 여기에 저장됩니다." No illustration. |
| **Queue — populated (Today group)** | User has one or more Today items | "Today" section heading (22px / weight 700) at top. QueueItems listed below. |
| **Queue — populated (This Week group)** | User has This Week items | "This Week" section heading below Today group (or at top if no Today items). QueueItems listed. |
| **Queue — populated (Later group)** | User has Later items | "Later" section heading below This Week group. QueueItems listed. |
| **Queue — overdue item** | Today item remains at midnight without action | QueueItem shows "미완료" badge ({colors.status-warning} text, no fill). No push re-notification within 3 days of initial scheduling. |
| **Queue — rescheduling** | User taps "일정 변경" on a QueueItem | Bottom sheet opens with Today / This Week / Later pill selection. Selection updates item badge immediately (optimistic). |

### Learning Path States

| State | Trigger | Display |
|-------|---------|---------|
| **Learning Path — 생성 중** | Learn Now committed; path not yet ready | "학습 경로를 생성하는 중입니다." three-dot pulse animation. |
| **Learning Path — 준비됨** | Path generation complete | Five ordered resource items. Outcome prompt not yet shown. |
| **Learning Path — Outcome 요청 (post-return)** | User has returned to app after tapping at least one external resource | Non-blocking prompt at bottom of screen: "학습을 완료했나요? 결과를 기록해 주세요." CTA: "결과 기록하기". |
| **Learning Path — 생성 실패** | Path generation fails | Error copy: "학습 경로를 생성하지 못했습니다." CTA: "다시 시도하기". Secondary: "홈으로 돌아가기". |

### Onboarding States

| State | Trigger | Display |
|-------|---------|---------|
| **Welcome** | First app launch | Heading: "오늘 배워야 할 AI, 매일 브리핑해드립니다" (28px / weight 700). Sub-copy: "AI 기술의 변화 속에서 오늘 배울 것을 추천받으세요." Primary CTA: "시작하기". |
| **Step 2 — Role** | Welcome CTA tapped | Step heading: "어떤 역할을 맡고 계신가요?" Option cards (6+1): Frontend Developer / Backend Developer / AI Engineer / Product Manager / Designer / Student / 기타. Select one. Primary CTA: "다음" (enabled on selection). |
| **Step 3 — Experience** | Role selected | Step heading: "AI 기술 경험 수준을 선택해 주세요." Three option cards: 입문 (Beginner) / 중급 (Intermediate) / 고급 (Advanced). Select one. Primary CTA: "다음". |
| **Step 4 — Tech Stack** | Experience selected | Step heading: "주로 사용하는 기술 스택을 선택해 주세요." Multi-select pill options: React, Next.js, Python, FastAPI, LangGraph, MCP, Claude Code, 기타. Select one or more. Primary CTA: "다음" (enabled on ≥ 1 selection). |
| **Step 5 — Project/Goal** | Tech Stack selected | Step heading: "현재 무엇을 만들거나 배우고 계신가요?" Option cards: AI 사이드 프로젝트 개발 / RAG 서비스 구축 / Agent Architecture 학습 / 업무 자동화 / AI 도입 검토 / 기타. Select one. Primary CTA: "다음". |
| **Step 6 — Interests** | Project/Goal selected | Step heading: "관심 있는 기술 영역을 선택해 주세요." Multi-select pill options: Agent / RAG / MCP / Coding Agent / Local LLM / AI UX / 기타. Select one or more. Primary CTA: "다음" (enabled on ≥ 1 selection). |
| **Step 7 — Daily Learning Time** | Interests selected | Step heading: "하루에 AI 학습에 투자할 수 있는 시간은?" Three option cards: 15분 / 30분 / 1시간. Select one. Primary CTA: "완료". |
| **Profile complete → First Brief Generating** | Step 7 CTA tapped | Full-screen loading. Copy: "오늘의 Daily Brief를 생성 중입니다." Three-dot pulse animation. Body: "프로필을 기반으로 가장 관련성 높은 AI 기술을 찾고 있습니다." No back navigation available during generation. |
| **First Brief Ready → Notification Permission** | Brief generation complete | Brief is ready but not yet shown. Notification permission request screen appears first. Heading: "매일 AI CTO 브리핑을 받아보시겠어요?" Copy: "매일 09:00에 오늘 배울 기술 브리핑을 보내드립니다." Two CTAs: "허용" (primary) / "나중에" (ghost pill). This is the first and only notification permission request. After either selection, user is routed to Home with first Daily Brief visible. |
| **Notification permission denied → Home** | "나중에" tapped | Routes directly to Home. Brief visible. Profile screen later shows "알림 설정" row for future enable. |

### History / Memory States

| State | Trigger | Display |
|-------|---------|---------|
| **History — 첫 사용자 empty state** | User opens History tab with no completed Decision Loops | Copy: "아직 기록된 학습 결정이 없습니다. Signal을 읽고 Learn Now를 선택하면 이곳에 기록이 시작됩니다." No illustration. |
| **History — populated** | One or more completed or in-progress Decision Loops exist | Memory Timeline with month dividers. Items listed reverse-chronologically. Each item shows the Decision node's label (Learn Now / Queue / Ignore) and Outcome state if recorded. |
| **History — chain 상세** | User taps a Timeline item | Full chain detail: Signal → Research Review → Decision → Outcome. All nodes tappable to source content. "보관된 Review" banner if source Review has aged out of active feed. |
| **History — in-progress chain** | Learn Now committed, Outcome not yet recorded | Chain shows Signal + Review + Decision nodes. Outcome node shows "미완료" state (text-secondary, "?" glyph dot). |

### Profile States

| State | Trigger | Display |
|-------|---------|---------|
| **Profile — view** | 프로필 탭 tapped | Shows current Role, Experience, Tech Stack, Project/Goal, Interests, Daily Learning Time. "편집" CTA at top-right. Notification settings row. Data management section (account, data export). |
| **Profile — edit mode** | "편집" tapped | Same layout, fields become interactive. Each section has individual edit affordance. Primary CTA at bottom: "저장". Secondary: "취소". |
| **Profile — save** | "저장" tapped | Optimistic update. Toast: "프로필이 업데이트됐습니다. 다음 Daily Brief에 반영됩니다." Returns to Profile view. |
| **Notification re-enable** | User denied permission at onboarding and now wants to enable | "알림 설정" row in Profile. Tapping routes to OS Settings app (no in-app re-request — in-app re-request after denial is prohibited by platform guidelines). Copy: "기기 설정에서 알림을 허용할 수 있습니다." |

### Contextual Chat States

| State | Trigger | Display |
|-------|---------|---------|
| **Empty (no prior message)** | User enters Chat from Research Review 상세 | Screen shows context label (e.g., "Research Review — [Signal 제목]") at top. Body empty. Placeholder: "이 Review에 대해 궁금한 점을 물어보세요." Input bar focused. |
| **In-conversation** | User has sent at least one message | Standard message thread. AI messages left-aligned (`surface-card` bg). User messages right-aligned (`accent-primary` bg, `accent-foreground` text). Each AI message carries a timestamp. |
| **Post-conversation — return to origin** | User taps back | Returns to Research Review 상세 at prior scroll position. No conversation summary shown on the originating screen. |
| **Error — AI unavailable** | Chat response fails or times out | Inline error below last AI message: "응답을 받지 못했습니다. 잠시 후 다시 시도해 주세요." Retry CTA. |


## Interaction Primitives

### Tap

The primary interaction mode. All consequential actions are activated by single tap. There are no long-press actions for primary functions anywhere in the product.

### Bottom Sheet Dismissal

- Drag handle area downward (drag gesture anywhere on the sheet also works)
- Tap on the `surface-overlay` scrim outside the sheet
- Back gesture (Android): closes the sheet, does not navigate back

### Queue Sub-Selection Sheet

The Queue timing selection sheet (Today / This Week / Later) opens when the user taps the Queue CTA in the enabled ContextStickyBar. It is a standard bottom sheet (same dismiss rules as above). Selecting a timing option commits the decision and closes the sheet in one tap — no secondary confirm.

### Context Sticky Bar

The bar is a persistent display element during Research Review scroll. The activation state change (disabled → enabled) does not require or respond to a tap. The primary CTA within the bar is a standard tap target.

### Scroll

Vertical scroll within `screen-content` containers. No horizontal scroll. No carousels. No scroll-triggered animations on content cards.

### Deferred swipe gesture (V2 only — not MVP)

Swipe left on Queue or History items: defer/reschedule action. This interaction is planned for V2 and is explicitly not implemented in MVP.

### Banned interactions (web + Flutter)

- Floating AI chat FAB anywhere in the product
- "Ask AI anything" input bar on Home or any non-Review screen
- Carousels or horizontal scroll of content cards or Signal items
- Auto-confirmation of Signals or Decisions (the system may never select Learn Now, Queue, or Ignore on the user's behalf)
- Drag-to-reorder in Queue (V1)
- Modal stacks deeper than 1 level (one bottom sheet or one modal at a time)
- Long-press for primary actions
- The + tab or + bottom sheet action pattern (deferred to V2; V2 will introduce user-submitted analysis candidates — GitHub repos, URLs, YouTube channels, RSS feeds)
- Progress bars, streaks, or completion percentages for learning engagement
- "50 articles about AI today" feed pattern — the product surfaces one curated Daily Brief, not a feed

**Flutter-specific prohibitions:**
- No ink/ripple splash on SignalCard, QueueItem, or any tappable card — use state-based visual feedback only (`splashFactory: NoSplash.splashFactory`)
- No `showDialog` or `AlertDialog` for Queue timing sub-selection — use `showModalBottomSheet`
- No system back interception on top-level tabs (Home / Queue / History / Profile) — Android back from a top-level tab exits the app
- No fixed-height containers on any text-bearing row — all heights are intrinsic + padding to support Dynamic Type / large-font-scale users


## Platform Patterns

### iOS

**Swipe-to-go-back:** Standard left-edge swipe gesture is preserved for all pushed screens. Research Review 상세 → Home (or Queue). Learning Path → Research Review 상세 at same scroll position. Contextual Chat → Research Review 상세. No screen disables this gesture.

**No hardware back button:** Back affordance is the `<` chevron in the navigation bar title area. Navigation bar title uses `body-large` spec (17px / weight 600 / centered), matching the current EXPERIENCE.md nav bar pattern.

**Safe areas:** `SafeArea` wraps all screen bodies. ContextStickyBar bottom padding extends into the Home Indicator area (≈ 34pt on iPhone X+) with `surface-base` background so the Home Indicator blends with the bar visually.

**Dynamic Type:** iOS system font size scaling maps to Flutter's `textScalerOf(context)`. All ContextStickyBar rows, card rows, and inline labels use intrinsic height + padding (never fixed `height:`). At scale ≥ 1.5×, engagement/recommendation text truncates to one line with "…"; full text accessible via screen reader label.

**Notification permission (iOS):** `UNUserNotificationCenter.requestAuthorization` is triggered at the same moment as web — after first Daily Brief generation completes during onboarding, before Home is shown. The native iOS system dialog replaces the web's in-app permission screen. If denied, the Profile screen shows an "알림 설정" row that routes to `AppSettings.openAppSettings()` (no in-app re-request after iOS denial).

---

### Android

**System back behavior:**

| Location | System back result |
|----------|--------------------|
| Home / Queue / History / Profile (top-level) | Exit app (standard Android behavior — do not intercept) |
| Research Review 상세 | Pop to previous tab screen (Home or Queue depending on entry point) |
| Learning Path | Pop to Research Review 상세 |
| Outcome 입력 | Pop to Learning Path |
| Contextual Chat | Pop to Research Review 상세 at prior scroll position |
| Queue sub-selection sheet | Dismiss sheet (standard `showModalBottomSheet` behavior) |
| Onboarding — First Brief Generating | **Suppressed** via `PopScope(canPop: false)` |

**Edge-to-edge display:** `SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge)` enabled globally. Bottom navigation bar uses `MediaQuery.viewPadding.bottom` for gesture navigation bar inset.

**Ink splash:** Suppressed globally via `ThemeData(splashFactory: NoSplash.splashFactory)`. Tappable card feedback is visual-state-only (no ripple).

**Notification permission (Android 13+):** `POST_NOTIFICATIONS` runtime permission requested via `permission_handler` at the same onboarding trigger as iOS. Android 12 and below do not require explicit permission — FCM works without the dialog.

**FCM (Firebase Cloud Messaging):** Push delivery for Android (and iOS via APNs bridge).
- App in foreground: `onMessage` stream — show in-app indicator on the relevant Home SignalCard only. No OS notification shown when app is foregrounded.
- App in background: `onMessageOpenedApp` fires on notification tap → GoRouter redirects to `/home`.
- App terminated (cold start): `FirebaseMessaging.instance.getInitialMessage()` checked on `main()` init → same redirect to `/home`.

---

### Cross-platform

**Haptic feedback:** `HapticFeedback.mediumImpact()` on: Learn Now tap (Decision committed), Outcome "기록하기" tap (loop closed), Queue timing option selected. No haptic on passive navigation taps (card open, tab switch).

**Bottom sheets:** All bottom sheets use `showModalBottomSheet` with:
```dart
shape: RoundedRectangleBorder(
  borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
)
isDismissible: true
enableDrag: true
```
Drag handle rendered manually (36×4px / #DDD / centered) — do not use Material's `DragHandle` widget (does not match spec). `isScrollControlled: true` for sheets whose content may exceed 50% screen height (Queue sub-selection is short; Onboarding sub-steps may not need it).

**Loading dot-pulse animation:** Three `Container` dots cycled via `AnimatedOpacity` at 300ms / 600ms / 900ms stagger. When `MediaQuery.disableAnimations` is `true`, render dots as static (no animation) — Flutter equivalent of `prefers-reduced-motion`.

**Status bar:** `SystemChrome.setSystemUIOverlayStyle(SystemUiOverlayStyle.dark)` (dark icons on light background) on all screens. `surface-raised` (#F9F9F9) screen background makes light-mode status bar icons legible throughout.

**User scenario: Push notification cold start (신규 플로우)**

박지은이 앱을 완전히 종료한 상태에서 09:00 Daily Brief 알림을 받는다.

1. **알림 수신 → 탭** → 앱이 cold start로 실행됨
2. `main()` → `FirebaseMessaging.instance.getInitialMessage()` → 알림 payload 감지
3. GoRouter 초기 라우트 결정: 온보딩 완료 상태 확인 → `/home`
4. **Home 화면 진입** — SignalCard가 push payload의 signalId에 해당하는 카드를 상단에 표시. 해당 카드에 brief animation (border highlight 300ms, Reduce Motion 시 생략)
5. 박지은이 카드를 탭 → Research Review 상세로 정상 진입
6. 이후 플로우는 Flow 1 (박지은의 Daily Learning Loop)과 동일

**User scenario: 앱 백그라운드 알림 (신규 플로우)**

1. 박지은이 앱을 백그라운드 상태로 두고 다른 앱 사용 중
2. 09:00 OS 알림 수신 → 탭
3. `onMessageOpenedApp` 콜백 → GoRouter: `/home` redirect
4. Home 화면 foregrounded → 해당 SignalCard 상단 강조 표시
5. 이후 동일

## Accessibility Floor

**Standard:** WCAG 2.2 AA (mobile web).

### Tap Targets

All interactive elements: minimum 44×44pt touch target. This applies to: all SignalCard rows (min-height: 44px, tap target encompasses full row), QueueItem rows (min-height: 44px), Research Review section headings tappable rows (min-height: 44px), Memory Timeline tappable cards (min-height: 44px), secondary ghost pill CTAs (min-height: 44px), all CTA buttons, Outcome option cards (min-height: 52px to accommodate label text).

### Context Sticky Bar — Responsive Text

The Context Sticky Bar must not use fixed pixel heights on any row. All vertical sizing is padding-driven so that when the user increases system font size, the bar expands to contain the larger text without clipping. At Dynamic Type ≥ 150% (iOS), engagement/recommendation text truncates to one line with "…"; full text remains accessible via `aria-label` on the CTA button. If bar height would exceed `40vh`, secondary ghost pills collapse into a "더보기" overflow.

### Screen Reader

**Heading hierarchy — Research Review 상세:**
`h1` = Signal / Review title. `h2` = each of the 13 section headings in display order. `h3` for sub-sections within sections (individual technology comparisons in section 5; individual learning steps in section 7). Each heading is announced before body content. Do not flatten all sections to `h2` if sub-sections exist.

**{components.ContextStickyBar} — full aria package:**
- Disabled primary CTA: `aria-disabled="true"` (not the `disabled` attribute, which removes focus), `aria-label="Learn Now — 비활성화됨. 리뷰 내용을 먼저 읽어 주세요"`, `aria-describedby="ctx-hint"`.
- Enabled primary CTA: `aria-label="Learn Now"`.
- Secondary CTAs: `aria-label="Queue — 이 Signal을 큐에 저장"`, `aria-label="Ignore — 이 Signal을 무시"`. All must be `<button>` elements.
- `aria-live="polite"` status region (visually hidden, always present in DOM): announces "<span lang='en'>Learn Now</span> 버튼을 사용할 수 있습니다" exactly once on transition from disabled to enabled.
- Hint text (`id="ctx-hint"`): the upward arrow character is wrapped in `<span aria-hidden="true">↑</span>` to suppress VoiceOver pronunciation.
- DOM position: the bar element is placed after section 13 (HonestBox) in DOM order regardless of visual position, so screen reader linear navigation reaches it last.

**{components.SignalCard}:** card tap target announces title + badge label + relevance tag + source count as a single composite `aria-label`. Example: `"Claude Code 1.0: MCP 통합 업데이트, NEW, 현재 LangGraph 프로젝트에 직접 적용 가능, 출처 5개"`. Do not rely on DOM concatenation — provide the composite label explicitly.

**{components.OutcomeCard} — Outcome radio group:**
- The four Outcome options (Completed / Applied / Dropped / Not Useful) must be implemented as `<input type="radio">` within a `<fieldset>` + `<legend>`, or as elements with `role="radio"` within a `role="radiogroup"`. The group label: "학습 결과를 선택해 주세요". Selected state announced via `aria-checked="true"`. Each option carries an `aria-label` combining the English state label and the Korean descriptor: `aria-label="Completed — 학습을 완료했습니다"`.

**{components.QueueItem}:** item announces timing badge + Signal title + estimated time. Example: `aria-label="Today 예약됨, Claude Code MCP 통합, 약 30분"`. Reschedule link announces `aria-label="일정 변경 — Claude Code MCP 통합"`.

**{components.MemoryTimelineItem}:** each tappable item announces node type + title + date. Example: `aria-label="Learn Now 결정, Claude Code MCP 통합, 2026년 7월 22일"`.

**Outcome dot glyphs in Memory Timeline:** the glyph inside the dot is wrapped in `<span aria-hidden="true">` and the dot element carries an `aria-label` describing the Outcome state in words: `aria-label="Applied 결과 — LangGraph 프로젝트에 적용됨"`.

### Reduce Motion

`@media (prefers-reduced-motion: reduce)`:
- Context Sticky Bar activation transition: remove fade/slide animation; switch instantly.
- **All animated loading indicators** (Daily Brief 생성 중 dot pulse, Research Review 생성 중, Learning Path 생성 중, 모든 로딩 화면): substitute with a static indicator. This rule applies globally — any future loading animation must also respect this override.
- Bottom sheet open/close: replace slide-up/slide-down translate animation with instant appear/disappear (opacity toggle only, no transform).
- All card entrance animations: disabled.
- Queue sub-selection sheet: same instant appear/disappear rule.

### Language

한국어 primary. `lang="ko"` on the `<html>` root element. All in-product copy is Korean.

**English-origin proper nouns** used within Korean body copy must carry `lang="en"` on their inline element so Korean screen readers apply correct phoneme rules. Exhaustive list for this product: `Review`, `Signal`, `Memory`, `Learn Now`, `Queue`, `Ignore`, `Daily Brief`, `Learning Path`, `Outcome`, `NEW` (badge), `OS`, `Applied`, `Completed`, `Dropped`. Technology proper nouns (LangGraph, MCP, Claude Code, GitHub, Reddit, HN, YouTube, FastAPI, RAG, Agent) also carry `lang="en"` inline treatment when embedded in Korean body copy.

### Flutter Semantics

**SignalCard — composite label:**
```dart
Semantics(
  label: '[Signal 제목], NEW, 출처 [N]개, 읽기 약 [N]분',
  button: true,
  child: ExcludeSemantics(child: cardContent),
)
```
Do not rely on widget tree concatenation — provide the composite `label` string explicitly, identical to the web `aria-label` spec.

**ContextStickyBar — disabled CTA:**
```dart
Semantics(
  label: 'Learn Now — 비활성화됨. 리뷰 내용을 먼저 읽어 주세요',
  button: true,
  enabled: false,
  // Do NOT set excludeSemantics: true — screen reader must be able to focus and hear this
)
```

**ContextStickyBar — activation announcement:**
```dart
SemanticsService.announce(
  'Learn Now 버튼을 사용할 수 있습니다',
  TextDirection.ltr,
);
```
Called at the moment the bar transitions to enabled state. Flutter equivalent of `aria-live="polite"`.

**Outcome radio group:**
```dart
Semantics(
  label: '학습 결과를 선택해 주세요',
  child: Column(children: [
    Semantics(
      label: 'Completed — 학습을 완료했습니다',
      inMutuallyExclusiveGroup: true,
      checked: isSelected,
      child: outcomeCard,
    ),
    // ...remaining three options
  ]),
)
```

**Memory Timeline dots:** The glyph character inside the dot is wrapped in `ExcludeSemantics`. The dot `Container` carries a `Semantics(label: 'Applied 결과 — [Signal 제목]')`.

**QueueItem:**
```dart
Semantics(
  label: 'Today 예약됨, [Signal 제목], 약 [N]분',
  button: true,
  child: ExcludeSemantics(child: queueItemContent),
)
```
Reschedule link: `Semantics(label: '일정 변경 — [Signal 제목]')`.

**English proper noun pronunciation:** Flutter does not support per-span `lang` attributes. Korean TTS on iOS/Android generally handles English loanwords embedded in Korean correctly. If testing reveals mispronunciation on specific terms (Learn Now, Queue, Signal), use alternate `semanticsLabel` only on the specific `Text` widget — do not create shadow DOM-style invisible labels diverging from visible text.

### Color Independence

No information is conveyed by color alone. Status states (overdue Queue item, Outcome type, HonestBox severity) are always accompanied by a text label or icon glyph in addition to color. The Memory Timeline Outcome dots use both color and a glyph (✓ / → / ✕ / −) so color-blind users can distinguish Outcome types.


## Notification Patterns

### Push Notification Triggers

| Trigger | Condition | Copy pattern | Timing |
|---------|-----------|-------------|--------|
| Daily Brief 준비됨 | Daily Brief generation complete | "오늘의 AI CTO 브리핑이 준비됐습니다 — [Signal 제목 예시]" | 09:00 매일 |
| Queue Today 리마인더 | User has Today items with no action taken; evening reminder | "오늘 학습하기로 한 [Signal 제목]이 남아있습니다" | 저녁 (20:00) — only sent if Today item exists |
| Outcome 입력 요청 | N days after Learn Now with no Outcome recorded | "학습 결과를 기록해 주세요 — [Signal 제목]" | N일 후 (default: 3일) |

### Non-Triggers (push NOT sent)

- Research Review generation complete (the Daily Brief arriving is the signal, not the underlying Review generation)
- Marketing or re-engagement pushes
- Repeated reminders for the same item within the stale notification policy window
- Any event that does not require user action
- Daily Brief generation failure alone (only triggers push if user has the app open and sees the error; background failure triggers a one-time push)

### Stale Notification Policy

If an item requiring user action (Queue Today, Outcome 입력 요청) remains unacknowledged for 3 calendar days, the system sends one follow-up push notification. No further pushes for that item are sent after the follow-up. The item remains in the Queue or Home until the user acts.

### Deep Link Behavior

Push tap → App opens to **Home (Daily Brief)** → relevant SignalCard or action prompt is highlighted briefly. Direct deep-link to a Research Review 상세 (bypassing Home) is prohibited. The Home screen is the notification center; there is no separate notification history screen.

### Permission Request Timing

Notification permission is requested exactly once during onboarding, immediately after the first Daily Brief is generated and before the Home screen is shown for the first time. This is the first moment the user has experienced concrete value from the product (profile → brief generation completes → permission request). Permission is not requested at app launch, not gated behind a paywall, not re-requested on Home after denial.

### Mobile Push (Flutter)

**Delivery stack:** FCM for Android native push; FCM → APNs bridge for iOS. `firebase_messaging` Flutter package handles all states.

| App state | Handler | Behavior |
|-----------|---------|----------|
| Foreground | `onMessage` stream | No OS notification shown. In-app: brief card highlight on Home only if currently on Home tab. |
| Background | `onMessageOpenedApp` | GoRouter redirects to `/home` on notification tap. |
| Terminated | `getInitialMessage()` | Checked in `main()`. Same redirect to `/home` if payload detected. |

No state shows a direct deep link to Research Review 상세 — Home is always the landing point.

### Inbox as Notification Center

The Home (Daily Brief) screen is the source of truth for all pending items. A push notification is a delivery mechanism for Home items, not a separate system. All items from any push exist on the Home screen before the push is sent.


## Decision Loop Patterns

### Review Before Action

No consequential action — committing to Learn Now, scheduling in Queue, or Ignoring — is taken without the user having engaged with the required sections of the Research Review. The Research Review 상세 screen has no "skip" CTA. The only forward paths are {components.ContextStickyBar} (Learn Now / Queue / Ignore) after activation, and back navigation. The product does not expose any shortcut from Home directly to a Learning Path without passing through Research Review.

### Three-State Decision Model

Every Research Review resolves to exactly one of three states:

| Decision | Label | Resulting state |
|----------|-------|-----------------|
| Learn Now | <span lang="en">Learn Now</span> | Navigate to Learning Path; Outcome loop opens |
| Queue | <span lang="en">Queue</span> → Today / This Week / Later | Signal saved to Queue tab with selected timing badge |
| Ignore | <span lang="en">Ignore</span> | Signal archived; removed from Home; visible in History |

These labels are fixed. Do not substitute synonyms (채택, 확인, 거절, 취소) in UI copy. The three-state model is intentional — it separates "I want to learn this, now" (Learn Now) from "I want to learn this, but not today" (Queue) from "I've considered this and it doesn't apply to me" (Ignore).

### Queue Sub-Decision

When the user selects Queue, the decision is not complete until a timing sub-option is chosen:
- **Today** — item appears at the top of the Queue tab with a "TODAY" badge; a Queue Today evening reminder may be sent
- **This Week** — item appears in the "This Week" Queue group; no immediate notification
- **Later** — item appears in the "Later" Queue group with no scheduled date; user returns on their own initiative

Queue is reversible before Outcome is recorded. A user may tap into a Queued item's Research Review and select Learn Now or Ignore to transition states.

### Decision Confirmation

One tap from the {components.ContextStickyBar} primary CTA (Learn Now) or secondary CTA (Ignore) executes the Decision. Queue requires one additional tap (timing sub-selection), but there is no "Are you sure?" confirmation dialog. The friction is already in the progressive activation of the bar (requiring section engagement). Adding a second confirmation would degrade trust by implying the system doubts the user's choice.

### Post-Decision States

**Learn Now path:**
1. Navigate to Learning Path screen (AI-generated, ordered resource set)
2. User accesses external resources (official docs, GitHub, tutorials)
3. Returns to app; Outcome prompt appears
4. Records Outcome (Completed / Applied / Dropped / Not Useful)
5. Decision Loop closed; full chain written to Memory

**Queue path:**
- Signal saved to Queue tab with timing badge
- No automatic re-escalation; user revisits according to their chosen schedule
- Today items receive one evening reminder; This Week and Later items do not receive automatic reminders

**Ignore path:**
- Signal archived; removed from Home
- Accessible from History timeline under the associated Signal chain
- Non-blocking toast (3 seconds): "이 Signal은 히스토리에서 다시 볼 수 있습니다."
- No undo prompt; accessible via History if the user changes their mind

### Outcome Loop Closure

After Learn Now, the Outcome 입력 screen is triggered by the Learning Path post-return prompt or by push notification (N days after Learn Now with no Outcome). The user records one of:
- Completed (with optional memo)
- Applied (with optional project memo)
- Dropped (with optional reason)
- Not Useful (with optional feedback)

Recording an Outcome closes the Decision Loop. The full chain (Signal + Research Review + Decision + Outcome) is written to Memory Timeline and becomes context for future Daily Brief personalization.

### Memory Write

Every completed or in-progress Decision Loop automatically links and stores:
- The originating Signal (technology name, date, source bundle)
- The Research Review (AI analysis snapshot and recommendation at time of generation)
- The Decision (Learn Now / Queue / Ignore, timestamp, Queue timing if applicable)
- The Outcome (Completed / Applied / Dropped / Not Useful, optional memo, date) — when provided

This chain is immutable once written. The user does not manage or edit Memory Timeline items directly; they are records, not a to-do list. Future Daily Brief personalization is driven by the accumulated Memory, not by user-managed preferences alone.


## Key Flows

### Flow 1 — 박지은의 Daily Learning Loop (핵심 MVP 플로우)

**Protagonist:** 박지은, Frontend Developer, AI 사이드 프로젝트 개발 중. LangGraph를 사용 중이며 MCP에 관심 있음. 매일 바쁘지만 AI 기술 동향은 놓치고 싶지 않다.

**Starting state:** 온보딩 완료. 09:00 Daily Brief 알림 수신.

1. **09:00 알림 수신 → 앱 오픈 → Home: Daily Brief 화면**
   알림을 탭하면 Home이 열린다. 화면 상단: "오늘의 AI CTO 브리핑" 섹션 헤딩 + 날짜. SignalCard가 하나 표시된다: "Claude Code 1.0: MCP 통합 업데이트" + NEW 배지 + 관련성 태그: "현재 Claude Code를 사용 중인 AI 사이드 프로젝트에 직접 적용 가능" + 출처 5개.

2. **SignalCard 탭 → Research Review 상세 열기**
   Research Review 상세 화면이 열린다. `h1`: "Claude Code 1.0: MCP 통합 업데이트". ContextStickyBar가 하단에 고정 표시됨 — disabled 상태. 힌트: "추천 근거를 먼저 확인해 주세요 ↑". 박지은은 위에서 아래로 읽기 시작한다.

3. **섹션 1–5 읽기: 한 줄 정의 → 핵심 개념 → 해결하는 문제 → 왜 지금 중요한가 → 기존 기술 차이**
   각 섹션을 스크롤하며 읽는다. 각 `h2` 섹션 헤딩이 뷰포트에 진입할 때 engagement tracking이 기록된다. ContextStickyBar는 여전히 disabled.

4. **섹션 6 — 사용자 관련성**
   "현재 프로필 기준" 레이블 아래: "현재 Claude Code를 사용 중인 AI 사이드 프로젝트에 MCP 통합 워크플로우를 바로 적용할 수 있습니다. 기존 LangGraph 코드베이스와 연동 가능합니다." — 박지은의 프로필 기반으로 생성된 개인화 콘텐츠. 섹션 6 engaged.

5. **섹션 7–9 스크롤: 학습 목표 → 예상 시간 + 난이도 → 실무 적용 가능성**
   계속 읽는다. 예상 학습 시간: 30분. 난이도: 중급.

6. **섹션 10 — 위험 요소**
   "일부 MCP 서버는 아직 실험적(experimental) 상태입니다. 프로덕션 적용 전 로컬 테스트를 권장합니다. MCP 프로토콜 버전 간 호환성을 확인하세요." 섹션 10 engaged.

7. **섹션 11 — 추천 이유**
   "현재 Claude Code를 업무에 사용 중이며 LangGraph 프로젝트를 개발 중입니다. MCP 통합은 두 도구를 연결하는 직접적인 경로입니다. 지금 배울 것을 권장합니다." 섹션 11 engaged.

8. **[Climax] ContextStickyBar 활성화**
   섹션 11이 뷰포트에 진입하는 순간 ContextStickyBar가 enabled 상태로 전환된다. 추천 텍스트 공개: "지금 배울 것을 권장합니다." Primary CTA: "Learn Now" ({colors.accent-primary} 배경). Secondary CTAs: "Queue" / "Ignore" ghost pills 표시. `aria-live` 영역: "Learn Now 버튼을 사용할 수 있습니다" 발화.

9. **"Learn Now" 탭 → Learning Path 화면**
   Decision 커밋됨. Learning Path 화면으로 이동. 생성 중 상태 → 준비됨.

10. **Learning Path 확인**
    순서대로 표시:
    1. 공식 문서: "Claude Code MCP 공식 가이드" (docs.anthropic.com)
    2. 핵심 자료: "MCP 통합 개요 — Anthropic Blog"
    3. GitHub: "anthropics/claude-code-mcp-example"
    4. 실습 예제: "MCP 서버 로컬 설정 튜토리얼"
    5. 적용 아이디어: "기존 LangGraph 워크플로우에 MCP 서버 연결해보기 — 현재 프로젝트 기준"

11. **외부 링크 방문 → 20분 학습 → 앱 복귀**
    박지은이 공식 문서와 GitHub 예제를 방문한다. 앱으로 복귀하면 Learning Path 화면 하단에 비차단 프롬프트 등장: "학습을 완료했나요? 결과를 기록해 주세요." CTA: "결과 기록하기".

12. **Outcome 입력: "Applied" 선택 → 메모 입력 → "기록하기"**
    Outcome 화면: "Applied — 실제 프로젝트에 적용했습니다" 선택. 메모 입력: "LangGraph 프로젝트에 MCP 서버 통합 완료. 로컬 테스트 성공." "기록하기" 탭.

13. **Memory 업데이트 → Home 복귀**
    토스트: "결과가 기록됐습니다. 다음 Daily Brief에 반영됩니다." Memory에 Signal + Review + Learn Now + Applied 체인 기록. 다음 Daily Brief에서 Claude Code 관련 심화 Signal이 우선 추천될 가능성이 높아진다.

**실패 경로 (바쁜 날):** 박지은이 Review를 읽다가 "지금은 시간이 없다" → Queue CTA 탭 → Queue 타이밍 시트 오픈 → "This Week" 선택 → Queue 탭에 저장됨. 주말에 Queue 탭 접근 → "This Week" 그룹에서 항목 확인 → 탭하면 Research Review로 이동 → 이미 섹션을 읽었으므로 빠른 재확인 → ContextStickyBar 활성화 → "Learn Now" → Learning Path → 학습 → Outcome 기록.

---

### Flow 1b — 박지은의 Queue 관리 (바쁜 날 패턴)

**Protagonist:** 박지은 (동일). 오늘 회의가 많아 Daily Brief를 볼 시간이 충분하지 않다.

**Starting state:** Daily Brief 알림 수신. 오늘 회의 일정이 꽉 참.

1. **알림 탭 → Home 오픈 → SignalCard 확인**
   알림을 탭해 Home을 연다. SignalCard: "LangGraph 0.3: 새로운 Streaming API" + NEW 배지. 관련성 태그: "현재 LangGraph 프로젝트에 관련된 중요 업데이트입니다."

2. **SignalCard 탭 → Research Review 상세 열기 → 빠른 스크롤**
   박지은은 처음 몇 섹션만 훑어본다. 섹션 1–4 스크롤. 충분히 관심이 생겼지만 지금 당장 배울 수 없다.

3. **Queue CTA 활성화를 위해 섹션 1–6, 10, 11까지 빠르게 읽기**
   스크롤을 계속해 required sections를 지나친다. ContextStickyBar 활성화.

4. **"Queue" 탭 → 타이밍 시트: "This Week" 선택**
   Queue CTA를 탭하면 타이밍 선택 시트 오픈. "This Week" 선택 → 시트 닫힘 → Decision 커밋됨. 비차단 토스트: "이번 주 학습 예정으로 저장됐습니다."

5. **주말 → Queue 탭 열기**
   Queue 탭. "This Week" 그룹에 "LangGraph 0.3: 새로운 Streaming API" 항목 표시. 탭하면 Research Review 상세로 이동.

6. **Research Review 상세 — 이미 읽은 상태**
   이전에 required sections를 모두 지나쳤으므로 backend `prior_read` 플래그가 설정됨. ContextStickyBar 즉시 활성화.

7. **"Learn Now" → Learning Path → 학습 → Outcome 기록**
   Flow 1과 동일하게 진행. Outcome: "Completed — 학습을 완료했습니다."

---

### Flow 2 — 이준서의 온보딩 (첫 설치)

**Protagonist:** 이준서, 28세, AI Engineer 준비생. Python을 주로 사용하며 Agent Architecture를 공부 중. AI 핵심 기술 학습 경로를 파악하는 것이 목표.

**Starting state:** 앱 처음 설치. 계정 없음, 데이터 없음.

1. **앱 설치 → Onboarding Welcome 화면**
   화면 헤딩: "오늘 배워야 할 AI, 매일 브리핑해드립니다" (28px / weight 700). 서브카피: "AI 기술의 변화 속에서 오늘 배울 것을 추천받으세요." Primary CTA: "시작하기".

2. **Step 2 — Role 선택**
   헤딩: "어떤 역할을 맡고 계신가요?" 이준서는 "AI Engineer" (준비생)를 선택한다. "다음" CTA 활성화.

3. **Step 3 — Experience 선택**
   헤딩: "AI 기술 경험 수준을 선택해 주세요." 이준서는 "입문 (Beginner)"을 선택한다. "다음".

4. **Step 4 — Tech Stack 선택**
   헤딩: "주로 사용하는 기술 스택을 선택해 주세요." 이준서는 Python, LangGraph를 선택한다 (multi-select). "다음" (≥ 1 선택으로 활성화).

5. **Step 5 — Project/Goal 선택**
   헤딩: "현재 무엇을 만들거나 배우고 계신가요?" 이준서는 "Agent Architecture 학습"을 선택한다. "다음".

6. **Step 6 — Interests 선택**
   헤딩: "관심 있는 기술 영역을 선택해 주세요." 이준서는 Agent, RAG, MCP를 선택한다. "다음".

7. **Step 7 — Daily Learning Time 선택**
   헤딩: "하루에 AI 학습에 투자할 수 있는 시간은?" 이준서는 "30분"을 선택한다. "완료" CTA.

8. **[Climax] 온보딩 완료 → First Daily Brief 생성 중**
   "완료" 탭 → 전체 화면 로딩 전환. 헤딩: "오늘의 Daily Brief를 생성 중입니다." 바디: "프로필을 기반으로 가장 관련성 높은 AI 기술을 찾고 있습니다." 세 점 pulse 애니메이션. 뒤로 가기 불가.

9. **Daily Brief 생성 완료 → 알림 권한 요청**
   전체 화면 알림 권한 요청. 헤딩: "매일 AI CTO 브리핑을 받아보시겠어요?" 카피: "매일 09:00에 오늘 배울 기술 브리핑을 보내드립니다." CTA: "허용" (primary pill) / "나중에" (ghost pill). 이준서는 "허용"을 탭한다.

10. **Home 진입 → 첫 Daily Brief 표시**
    Home. "오늘의 AI CTO 브리핑" 헤딩. SignalCard: "LangGraph 핵심 개념 — Agent 구조 설계 입문" + NEW 배지. 관련성 태그: "Agent Architecture 학습 목표에 직접 연결되는 입문 가이드입니다."

11. **이준서가 첫 Research Review 열기**
    Research Review 상세. `h1`: "LangGraph 핵심 개념 — Agent 구조 설계 입문". ContextStickyBar disabled. 이준서는 섹션 1 — 한 줄 정의부터 읽기 시작한다. 이것이 첫 Decision Loop의 시작이다.

**실패 경로 (온보딩 실패 없음 — 온보딩은 네트워크 없이도 진행 가능):** Daily Brief 생성 실패 시 → "오늘의 Daily Brief를 생성하지 못했습니다." 화면 → "다시 시도하기" CTA → 재시도. 알림 권한 요청은 실패와 무관하게 표시되며, Daily Brief가 준비되면 Home으로 이동.


## Inspiration & Anti-patterns

### Lifted from References

**Cal AI (전체 디자인 언어, 타이포, 여백, 온보딩 wizard 패턴)**
- Single-purpose screens with one large heading and one primary action
- Black pill CTA as the only high-contrast element
- Generous, structural whitespace — negative space carries as much weight as content
- Onboarding as a stepped wizard with minimal fields per step and clear progress

**Linear (Inbox, 우선순위, 상태 관리)**
- Home = "what needs my attention right now" — not a dashboard, not a feed
- Priority ordering of items by relevance type, not by time
- Status badges communicate state without requiring the user to enter the item
- The interface recedes when there is nothing to do; it does not create artificial busyness

**Apple Health (상태 요약, 건강도 시각화)**
- A single status signal gives the user an orientation anchor before diving into details
- The product "monitors" in the background and surfaces what matters
- Status is expressed through calm, factual indicators — not alerts and warnings

**Copilot Money (데이터 카드 디자인)**
- Clean card treatment: title, type, date — no decoration
- Financial-data-style clarity applied to learning information
- Data presented factually, not with progress bars or gamified visuals

### What Decision OS is NOT

**Not a news feed / content aggregator**
Showing 50 AI articles is the opposite of what Decision OS does. The Daily Brief contains exactly the Signal(s) that are most relevant for this user today. "More content" is never an improvement. The signal-to-noise ratio is the product.

**Not a learning management system**
No course catalog, no progress bars tracking completion percentages, no certificates, no gamified streaks. The product is a Decision OS, not an LMS. The Learning Path is generated per-decision, not curated in advance for the user to browse.

**Not a ChatGPT-style AI assistant**
Chat is a secondary, context-grounded tool available only within Research Review 상세. The primary interface never starts with an empty text input asking "What do you want to know?". Decision OS surfaces what you need to know, without being asked.

**Not a 기술 블로그 or AI 뉴스레터**
Long editorial articles, listicles ("Top 10 AI tools this week"), or opinion pieces are not what Decision OS produces. The Research Review is structured, personalized, and action-oriented — it exists to enable a Decision, not to inform generally.

### Rejected Patterns (explicit prohibitions)

| Pattern | Reason |
|---------|--------|
| Floating AI chat FAB | Defines the product as a chatbot; contradicts Inbox/Brief paradigm |
| "50 articles about AI" feed | Information overload is the problem being solved, not a feature |
| Course catalog / LMS pattern | Wrong product category; contradicts Decision OS paradigm |
| AI neon / gradient accents | Visual noise that undermines focused, calm decision-making |
| Auto-confirmation of Decisions | Removes user agency from the core loop |
| Carousels for Signal cards | Hides information; low mobile tap accuracy; contradicts linear Daily Brief |
| Multi-level modal stacks | Disorienting on mobile; violates One Screen, One Decision |
| Streaks / engagement nudges | Wrong reward signal; creates anxiety instead of reducing it |
| Urgency copy ("지금 배우지 않으면 뒤처집니다") | Contradicts Minimize Information Overwhelm principle |
| "관리자 Dashboard" layout | Wrong complexity tier for a personal tool |
| V2 + button in MVP | User-submitted analysis candidates (GitHub repos, URLs, YouTube, RSS) deferred to V2 |
| Progress bars for reading sections | The section-engagement gate should be invisible; a visible progress bar gamifies what is meant to be a reading experience |
