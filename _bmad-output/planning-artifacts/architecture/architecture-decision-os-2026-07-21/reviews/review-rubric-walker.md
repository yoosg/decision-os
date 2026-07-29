# Rubric Walker Review — Decision OS Architecture Spine
Date: 2026-07-22
Reviewer: Rubric Walker (good-spine checklist)

---

## Verdict

PASS WITH CONCERNS — The spine correctly fixes the central architectural divergence risks (monolith vs. microservices, data access bifurcation, async Review execution, Playbook extension model), but it is silent on the entire observability/logging dimension, leaves error handling strategy unspecified, has no testing strategy, and contains one deferred item (보험증권 이미지 파싱 방식) that is a real divergence risk that belongs in a decision, not a deferral.

---

## Critical Findings (must address before handoff)

**CF-1: No testing strategy decision.**
The spine is completely silent on testing architecture. For a system with async background tasks, LLM provider abstraction, and a split data-access model (Next.js direct reads vs. FastAPI writes), two independent teams could diverge immediately: one could write unit tests for ReviewContextBuilder, another could write integration tests hitting Supabase directly, a third could write E2E-only tests. There is no AD fixing which layer owns which test concerns, nor any rule about how the LLM provider abstraction is tested (mock vs. contract vs. real calls). This is a structural dimension the spine owns and must address.

**CF-2: 보험증권 이미지 파싱 방식 is misclassified as Deferred.**
AD-8 binds "첫 Review 타입: 병원 영수증 → 청구 가능 보험 분석" as an MVP deliverable. FR-1.2 (보험증권 이미지 파싱) is listed as an MVP ASSUMPTION in the PRD. Whether parsing uses OCR (a separate service or library call from FastAPI) vs. LLM-as-OCR (a variant ReviewContextBuilder with a multimodal prompt) is an implementation fork that determines module structure, cost model, and data flow. If one developer treats it as an LLM preprocessing step inside ReviewContextBuilder and another builds it as a separate FastAPI endpoint calling a third-party OCR API, the resulting modules are architecturally incompatible. This must be an AD with a rule, or explicitly moved to out-of-MVP scope with a clear rationale.

**CF-3: No observability/logging decision.**
The spine has no AD covering structured logging, request tracing, or error reporting. In a system with async BackgroundTasks and LLM calls, this is not a nice-to-have. The failure mode (LLM call fails silently, status machine stays in `processing` forever) is already partially addressed by AD-5's state machine, but there is no rule about what gets logged, at what level, with what correlation (review_id? user_id?), or what external tooling (Sentry, Railway logs, Supabase logs) is the system of record for errors. Two developers building separate Playbook modules will make inconsistent choices.

---

## High Findings (should address)

**HF-1: Error handling strategy is absent.**
AD-5 mandates a `pending → processing → completed | failed` state machine and states AI failure must not cause data loss. But the spine says nothing about: what happens when status becomes `failed` (is the user notified? how?), whether retries are in scope, or who is responsible for the retry/notification path (FastAPI? Next.js polling logic? Supabase Realtime trigger?). This is especially acute because the PRD requires Realtime notification on completion (AD-5 diagram shows `DB-->>FE: Realtime 알림`), but the failure path notification is entirely unspecified. Two developers could diverge: one sends a Realtime event on failure, another relies on the user polling and discovering the failed state, another sends an email via Supabase Edge Function. An error handling AD is needed.

**HF-2: API contract between Next.js and FastAPI is not fixed.**
AD-3 establishes what flows through FastAPI (writes + AI) vs. direct Supabase (reads), but the REST API contract itself — URL structure, response envelope shape, versioning strategy, auth header format — is entirely unspecified. For a spine that binds the service boundary, leaving the API contract shape open means the Next.js team and the FastAPI team can produce incompatible interfaces. At minimum, an AD should fix: the auth header convention (Bearer token from Supabase JWT?), the response envelope shape for async 202 responses, and whether API versioning is applied from day one (e.g., `/api/v1/`).

**HF-3: Security posture for sensitive financial data is not addressed.**
The PRD calls out in NFR that insurance and claims data is sensitive personal financial information (민감 금융 데이터). AD-3 establishes RLS at the database level, but the spine has no AD covering: input validation strategy (who validates user-submitted insurance data before it hits the DB?), file upload security (what validates the receipt image before it's stored in Supabase Storage?), LLM prompt injection risk (user-supplied memo or claim data goes into LLM context — is sanitization required?), or secrets management (how are LLM API keys and Supabase service_role key handled across Railway deployments?). The Korean market context (한국 시장 전용) may also imply PIPA (개인정보보호법) considerations that are entirely unaddressed.

**HF-4: Deployment model is underspecified for practical dev/staging/prod separation.**
The spine names Railway as the deployment platform (AD-2) but says nothing about environment topology. There is no decision fixing whether there is a staging environment, whether Supabase has a separate project per environment, or how environment-specific secrets are handled. For a two-person team this may seem trivial, but for a review to validate the spine is complete, this is a missing dimension the spine must either decide or explicitly defer with a stated re-evaluation condition. Currently it is simply absent.

**HF-5: Spec coverage — FR-5 (Dashboard) has no architectural grounding.**
FR-5 requires a dashboard showing current insurance status, in-progress reviews, and a timeline of past decisions and outcomes. This is a read-heavy, potentially aggregated view. AD-3 says reads go directly from Next.js to Supabase via RLS. But the spine does not address whether aggregate queries (e.g., "show me all outcomes grouped by decision type across all reviews") are safe to run directly from the client via RLS, or whether they require a FastAPI endpoint. The rule in AD-3 says "읽기 로직이 복잡해질 경우 해당 조회만 FastAPI로 이동" — but this is a conditional with no decision about the dashboard specifically, leaving the dashboard implementation team without guidance on which of their queries cross the complexity threshold.

---

## Medium / Low Findings

**ML-1 (Medium): `activities` table in the ER diagram is undeclared.**
AD-4's ER diagram lists `activities` as a common table (`공통 테이블: projects, reviews, decisions, outcomes, activities`), but it does not appear in the entity definitions, has no attributes defined, and no AD explains what it stores or who writes to it. If two developers independently decide what `activities` means (audit log? user action feed? system events?), the table will be incoherent. Either define it in AD-4 or remove it from the diagram.

**ML-2 (Medium): `reviews.playbook_type` is redundant and the redundancy is not justified.**
AD-4 ER shows both `projects.playbook_type` (the domain fork gate) and `reviews.playbook_type`. A review belongs to a project, so its playbook_type is derivable. Carrying it as a denormalized field creates a consistency risk (can a review's playbook_type differ from its project's?). The AD should either justify the denormalization explicitly (e.g., "for query performance without joins") or remove the redundant field.

**ML-3 (Medium): Playbook activation assumption from PRD is unaddressed.**
PRD section 6 states `[ASSUMPTION] Playbook은 설정 기반으로 활성화/비활성화 가능하다`. AD-1 defines how new Playbooks are added (new module in FastAPI), but says nothing about how they are activated or disabled at runtime. This is relevant for the expansion path and should at minimum be called out as deferred with a re-evaluation condition.

**ML-4 (Low): Technology currency flags.**
The spine names Next.js, FastAPI, Supabase, pgvector, Railway, and OpenAI. All appear current as of the spine date (2026-07-21), but no versions are pinned. In particular, Supabase's pgvector support and Railway's pricing/plan availability should be verified by the technology currency reviewer (flagging per checklist item 4, not making a determination here).

**ML-5 (Low): BackgroundTasks concurrency limit is implicitly deferred but not named.**
AD-5 mandates all Reviews run as FastAPI BackgroundTasks. The Deferred table correctly calls out Redis/Celery as a future path when BackgroundTasks hits capacity limits. However, there is no guidance on what the current concurrency limit is or what monitoring signal triggers the re-evaluation. "처리 용량 한계 도달 시" is not a measurable condition. The deferral is structurally safe but operationally vague.

**ML-6 (Low): LLM Provider Interface contract is not defined.**
AD-6 mandates a `LLM Provider Interface` and says "Provider 교체는 Interface 구현체 교체로만 수행." The interface itself — method signatures, input/output types, streaming vs. non-streaming — is not specified anywhere in the spine. If this is left to implementing developers, the OpenAI implementation may make assumptions (e.g., synchronous non-streaming) that make swapping to Anthropic's streaming API non-trivial. This is a medium divergence risk that could be addressed with a brief interface shape note in AD-6.

---

## Per-Criterion Notes

### 1. Divergence Coverage
Partially passes. The spine correctly prevents the most dangerous divergence: microservice sprawl (AD-1), competing data infrastructure (AD-2), write-path confusion (AD-3), Playbook schema pollution of common tables (AD-4), and synchronous LLM-in-HTTP-response anti-pattern (AD-5). The uncovered divergence risks are in testing strategy (CF-1), error handling (HF-1), API contract shape (HF-2), and dashboard query routing (HF-5). Two teams building separate Playbooks would not diverge on the major structural choices, but they would diverge on observability, error reporting, and API conventions.

### 2. Enforceable Rules
Mixed. Most rules are enforceable via code review: "새 Playbook = FastAPI 내부에 모듈 추가" (AD-1), "모든 사용자 데이터 테이블에 RLS 필수" (AD-3), "Review 상태 머신: pending → processing → completed | failed" (AD-5). However, AD-3's rule "읽기 로직이 복잡해질 경우 해당 조회만 FastAPI로 이동" is not enforceable — "복잡해질 경우" is a subjective judgment call with no measurable criterion. This rule should be replaced with a concrete heuristic (e.g., "any query requiring a JOIN across more than two tables, or any aggregation, must be served from FastAPI").

### 3. Deferred Safety
One misclassification found (CF-2): 보험증권 이미지 파싱 방식 is deferred but the feature it supports (FR-1.2) is an MVP ASSUMPTION in the PRD, and the parsing approach determines module structure. All other deferred items are genuinely post-MVP or post-validation decisions that cannot create incompatible divergence during MVP development: Memory 테이블 스키마 (explicitly excluded from MVP by AD-7), Redis/Celery (triggered by a capacity condition), Career/Investment/Home schemas (post-MVP Playbooks). The other deferrals are safe.

### 4. Technology Currency
Flagged for secondary review. Next.js, FastAPI, Supabase (with pgvector), Railway, and OpenAI API are all viable as of 2026-07-21. No specific versions are pinned, which is a risk for Railway's service offering and Supabase's pgvector feature availability. No determination made here; flagged per checklist instruction.

### 5. Spec Coverage
Partial. The spine covers FR-0 (auth via Supabase, AD-2/AD-3), FR-1 partial (data model in AD-4, but FR-1.2 image parsing is unresolved — CF-2), FR-2 (Review engine in AD-5/AD-6), FR-3 (Decision in AD-4 data model), FR-4 (Outcome in AD-4 data model, Outcome → Review context loop in AD-7). FR-5 (Dashboard) is partially covered by AD-3's read pattern but the complex query boundary is unresolved (HF-5). NFR on data privacy is partially covered by AD-3 RLS, but PIPA compliance, input validation, and file security are absent (HF-3). The PRD's platform extensibility requirement (section 6) is covered by AD-1 and AD-4.

### 6. Operational/Environmental Envelope
Fails. Deployment platform (Railway) is named in AD-2, but the environment model (dev/staging/prod), secrets management strategy, Supabase project-per-environment pattern, and operational monitoring are absent. The spine is silent on the entire ops dimension beyond "Railway hosts both services." This is not catastrophic for a two-person MVP team, but it is a gap the rubric requires to be either decided or explicitly deferred with conditions.

### 7. No Inherited Spine Contradictions
Skipped per instructions (no parent spine).

### 8. Altitude Sweep

| Dimension | Coverage |
|---|---|
| State mutation | Covered (AD-3: all writes via FastAPI; AD-5: Review state machine) |
| Data ownership | Covered (AD-3: RLS + access split; AD-4: common vs. Playbook tables) |
| Service boundaries | Covered (AD-1: monolith; AD-3: Next.js vs. FastAPI responsibility) |
| API contracts | Not covered — shape, versioning, auth header unspecified (HF-2) |
| Auth/authz | Partially covered — Supabase Auth chosen (AD-2), RLS mandated (AD-3), but service-to-service auth and API key management absent (HF-3) |
| Observability | Not covered — no logging, tracing, or error reporting AD (CF-3) |
| Error handling | Not covered — failure path for async Reviews unspecified beyond state machine (HF-1) |
| Security posture | Partially covered — RLS in place, but input validation, file upload security, prompt injection, secrets management absent (HF-3) |
| Deployment model | Not covered — environment topology absent (HF-4) |
| Testing strategy | Not covered — no AD (CF-1) |

The spine covers 3 of 10 altitude dimensions fully, 2 partially, and 5 not at all.

### 9. Seed vs. Invariant Discipline
The spine is appropriately thin on the seed side — it does not over-specify table column types, UI component choices, or internal FastAPI module naming. The invariants it does fix are genuine divergence risks. The primary failure is being too thin on the invariant side: observability, error handling, API contract shape, and testing strategy are real divergence risks at this altitude that are missing entirely, not deliberately deferred. The Memory deferral (AD-7) is a well-reasoned invariant: it actively prevents premature schema fixation while still fixing the interim approach. That is a good pattern the spine should apply to the missing dimensions as well (either decide or explicitly defer with a condition).
