# Adversarial Review — Decision OS Architecture Spine
Date: 2026-07-22
Reviewer: Adversarial (incompatibility hunter)

---

## Verdict

7 real holes found: the spine's data-ownership and async-flow rules are well-intentioned but leave enough whitespace between them that two independently compliant builders can produce components that cannot be wired together without a renegotiation.

---

## Incompatible Pairs Found

### Gap-1: `context_snapshot` / `result` shape — no schema contract

- **Unit A**: The Insurance Playbook team builds `HospitalReceiptReviewContextBuilder`. It writes `context_snapshot` as a flat JSON object with top-level keys `policy_ids: uuid[]`, `receipt_url: string`, `claim_history: object[]`. It writes `result` as `{ recommendations: [{policy_id, rationale, amount}] }`.
- **Unit B**: The Renewal Review team (next sprint, following the same AD-4 + AD-6 Rule: "새 Review 타입 = 새 ReviewContextBuilder 구현") builds `RenewalReviewContextBuilder`. It writes `context_snapshot` as `{ policies: [{id, coverage, premium}], change_summary: string }` and `result` as `{ verdict: string, changed_items: string[] }` — a completely different shape.
- **Incompatibility**: Any component that reads the `reviews` table and tries to render or process `context_snapshot` or `result` — a dashboard aggregating all reviews, an Outcome page pulling prior Review results as context, a future Memory extractor — cannot assume any stable shape. Two builders both obeyed AD-4 and AD-6, yet produced unreadable outputs for any shared consumer.
- **Missing/weak AD**: AD-4 and AD-6 mandate a `ReviewContextBuilder` per type but never specify (a) the required top-level envelope for `context_snapshot` (e.g., mandatory `review_type`, `version`, `playbook_type` keys), nor (b) the required structure for `result` (e.g., mandatory `summary: string`, `items: [{…}]` wrapper). **Missing AD**: "공통 Review 결과 Envelope — `context_snapshot`과 `result`는 type-tagged versioned envelope(`{ schema_version, review_type, payload }`)을 감싸야 한다; `payload` 내부만 타입별 자유."

---

### Gap-2: Review `status` terminal state — no idempotency rule prevents double-completion

- **Unit A**: The Hospital Receipt Review builder implements the `pending → processing → completed | failed` machine (AD-5 compliant). On LLM success it sets `status = 'completed'` and writes `result`. It never checks whether `status` is already `completed` before writing, because AD-5 only says what the transitions are, not that a terminal state must be immutable.
- **Unit B**: A second engineer adds a "post-processing enrichment" step — also inside a `BackgroundTask`, also AD-5 compliant — that re-reads `completed` reviews to append a `confidence_score` to `result`. It writes `result` back and sets `status = 'completed'` again (no-op on status, but mutates `result`).
- **Incompatibility**: If Unit A's BackgroundTask crashes mid-write and retries (legitimate under AD-5's failure handling intent), and Unit B's enrichment task runs concurrently, both mutate `result` with no ordering guarantee. Result content silently diverges from what the LLM produced. The frontend Realtime notification fires once on each `status` update; with two `completed` writes it fires twice, causing duplicate completion events.
- **Missing/weak AD**: AD-5 states the state machine transitions but does not declare terminal states immutable, does not require idempotency guards on status transitions, and does not prohibit post-hoc `result` mutation after `completed`. **Missing AD**: "Review `completed` 및 `failed`는 불변 터미널 상태다; 해당 상태 진입 후 `result` 또는 `status`를 재기록하는 코드는 불허한다; 후처리가 필요한 경우 별도 테이블 또는 `reviews` 내 별도 컬럼을 사용한다."

---

### Gap-3: Realtime subscription payload — frontend and backend have no agreed event shape

- **Unit A**: The FastAPI engineer completing a Review fires the Realtime notification implicitly by updating `reviews.status` via `service_role`. The payload Supabase sends to subscribers is the full Postgres row diff. The engineer assumes the frontend will read `new.status === 'completed'` and then separately query the full `result`.
- **Unit B**: The Next.js engineer subscribes to `reviews` on `review_id`. To avoid an extra round-trip, the engineer assumes the Realtime payload includes the full `result` JSONB inline (since Supabase Realtime sends the entire new row by default in `REPLICA IDENTITY FULL` mode). The engineer writes the render logic to directly destructure `payload.new.result.recommendations` without a follow-up fetch.
- **Incompatibility**: If the Postgres table's `REPLICA IDENTITY` is set to `DEFAULT` (which only sends the primary key on UPDATE), the frontend receives `{ id: uuid }` with no `result`. Unit B's code crashes. Conversely, if `REPLICA IDENTITY FULL` is set, the payload includes all columns including potentially large `context_snapshot`, creating unexpected bandwidth consumption that the backend engineer never intended. Neither engineer violated any AD — AD-5 says "Supabase Realtime 또는 폴링으로 완료 감지" without specifying what the Realtime payload must contain or what `REPLICA IDENTITY` must be set to.
- **Missing/weak AD**: AD-5 specifies the async pattern but leaves the Realtime contract entirely open. **Missing AD**: "Supabase Realtime 구독 계약 — `reviews` 테이블은 `REPLICA IDENTITY FULL`로 설정한다; Realtime 이벤트 payload는 `{ id, status, review_type, result }` 필드를 포함한다; 프론트엔드는 Realtime 이벤트 수신 후 추가 조회 없이 상태 전환 여부만 판단하고, 전체 데이터는 별도 Supabase 클라이언트 조회로 가져온다."

---

### Gap-4: RLS policy ownership — two teams writing conflicting or absent policies

- **Unit A**: The Insurance Playbook team creates `insurance_policies`, `insurance_claims`, `insurance_documents` tables and writes RLS policies enforcing `user_id = auth.uid()`. They follow AD-3's rule ("모든 사용자 데이터 테이블에 RLS 필수"). Their policies use `(SELECT user_id FROM projects WHERE id = insurance_policies.project_id) = auth.uid()` via a sub-select join.
- **Unit B**: A second team later creates `career_profiles` (the Career Playbook, which is Deferred but will eventually be built by someone following the same spine). They also comply with AD-3 by adding RLS. But they write a direct `project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())` policy. The sub-select patterns differ: one resolves via `insurance_policies.user_id` (a denormalized column they added to the table), the other via joining `projects`. If Unit A added `user_id` as a denormalized column and Unit B did not, the policies express different join depths and can be inconsistently bypassable when `projects` rows are deleted or re-assigned.
- **Incompatibility**: No AD specifies the RLS pattern — which join path to use, whether `user_id` must be denormalized into every Playbook table, or whether a helper function `fn_user_owns_project(project_id)` must be called. Two compliant teams produce policies with different security semantics. A future audit or row-sharing feature breaks one silently.
- **Missing/weak AD**: AD-3 mandates RLS existence but not the implementation pattern. **Missing AD**: "RLS 구현 패턴 — 모든 Playbook 테이블은 `user_id uuid NOT NULL`을 직접 컬럼으로 보유하고, RLS 정책은 `user_id = auth.uid()`로만 단순화한다; `projects` JOIN을 통한 간접 RLS 불허; Playbook 테이블 생성 시 `user_id`를 `projects.user_id`에서 복사해 비정규화한다."

---

### Gap-5: LLM Provider Interface — return type and error contract undefined

- **Unit A**: The MVP engineer implements `OpenAIProvider` as the concrete `LLM Provider Interface` implementation (AD-6: "Provider 교체는 Interface 구현체 교체로만 수행"). Since only OpenAI exists in MVP, the engineer defines the interface return type as a raw `str` (the LLM text output), with Python exceptions propagating directly as `OpenAIError` subclasses.
- **Unit B**: Six months later a second engineer implements `AnthropicProvider` following the same AD-6 rule. They return a `dict` with `{ content: str, stop_reason: str, usage: dict }` because the Anthropic SDK returns a structured object and the engineer finds it useful to preserve metadata. They raise `anthropic.APIError` on failure.
- **Incompatibility**: Every `ReviewContextBuilder` that calls the LLM Provider Interface is written against Unit A's `str` return type. When Unit B's `AnthropicProvider` is swapped in, every builder that calls `.split()`, `.strip()`, or passes the result to a JSON parser as a string immediately breaks. The error handling code that catches `OpenAIError` also fails to catch `anthropic.APIError`. Both units obeyed AD-6's only rule: "Provider 교체는 Interface 구현체 교체로만 수행." The interface itself was never specified.
- **Missing/weak AD**: AD-6 names the "LLM Provider Interface" as a concept but provides no method signatures, return types, or error contract. **Missing AD**: "LLM Provider Interface 계약 — `generate(prompt: str, system: str | None) -> LLMResponse` 단일 메서드; `LLMResponse = { content: str, finish_reason: Literal['stop','length','error'], raw: dict | None }`; 모든 Provider 구현체는 provider-specific 예외를 `LLMProviderError(message: str, retryable: bool)`로 래핑한다."

---

### Gap-6: Playbook table naming and FK conventions — two deferred Playbooks built incompatibly

- **Unit A**: The Career Playbook team (building after Insurance MVP per the Deferred table) creates tables: `career_projects` (extending `projects` via `project_id` FK), `career_positions`, `career_goals`. They use `snake_case` singular nouns and prefix every table with `career_`. They store domain-specific dates as `ISO 8601 text` fields because "it's simpler."
- **Unit B**: The Investment Playbook team, building concurrently, creates `investment_portfolios`, `investmentAssets` (camelCase, accidentally), `investment-transactions` (hyphen, SQL-quoted). They store monetary amounts as `numeric(12,2)` and dates as `timestamptz`. They add a `playbook_version int` column that Insurance and Career do not have.
- **Incompatibility**: AD-4 says "새 Playbook = 새 Playbook 테이블 세트 + `project_id` FK + 해당 Playbook의 `ReviewContextBuilder`." This is the entirety of the Playbook table contract. It says nothing about naming conventions, data type choices for common field types (money, dates, IDs), whether a `playbook_version` column is required or prohibited, or whether `user_id` denormalization (see Gap-4) is required. A cross-playbook feature (e.g., a unified dashboard querying all project types, or a migration tool) immediately hits irreconcilable naming and type collisions.
- **Missing/weak AD**: AD-4's Rule covers structural connectivity (FK) but not schema conventions. **Missing AD**: "Playbook 테이블 컨벤션 — 테이블명은 `{playbook_slug}_{entity_plural}` snake_case; 금액 필드는 `numeric(15,4)`; 날짜 필드는 `timestamptz`; 모든 PK는 `uuid` default `gen_random_uuid()`; `user_id uuid NOT NULL`과 `project_id uuid NOT NULL REFERENCES projects(id)` 필수 포함; `playbook_version` 같은 플랫폼 메타 컬럼은 공통 테이블 역할의 `projects`에서만 관리한다."

---

### Gap-7: Next.js write boundary — "forgot" writes slip through via Supabase client mutations

- **Unit A**: The backend engineer implements `POST /reviews/trigger` in FastAPI, which creates the Review row with `status = pending` (AD-3 compliant: "AI가 생성한 Review·Decision·Outcome 변경은 FastAPI만 수행").
- **Unit B**: A frontend engineer building the "cancel pending review" UX feature reads AD-3 carefully. The rule says FastAPI must handle "AI가 생성한 Review·Decision·Outcome 변경" — i.e., AI-generated changes. The engineer reasons that cancelling a review is a *user-initiated* status change, not an AI-generated one, and therefore writes a direct Supabase client call from Next.js: `supabase.from('reviews').update({ status: 'cancelled' }).eq('id', reviewId)`. They add `status: 'cancelled'` as a new terminal state that FastAPI never knows about.
- **Incompatibility**: FastAPI's BackgroundTask is still running when the frontend cancels. The BackgroundTask completes and overwrites `status = 'completed'`, racing with the frontend's `cancelled` write. Neither engineer violated any stated AD — "AI가 생성한" is the stated boundary, and a user-cancel is genuinely not AI-generated. But the Prevents clause ("Next.js의 직접 쓰기") is contradicted by the Rule's narrower wording ("AI가 생성한 Review…변경은 FastAPI만"). The Prevents and the Rule are inconsistent with each other.
- **Missing/weak AD**: The Prevents clause in AD-3 says "Next.js의 직접 쓰기" (all direct writes), but the Rule narrows it to AI-generated content only, creating an exploitable gap for any non-AI mutation. **Fix needed in AD-3**: Rule should read "모든 테이블에 대한 쓰기(INSERT/UPDATE/DELETE)는 AI 생성 여부와 무관하게 FastAPI 경유; Next.js Supabase 클라이언트는 SELECT(읽기)만 허용된다."

---

## Attacks That Failed (spine held)

**1. Multiple `projects` owners (AD-3 + AD-1):** Tried to construct a path where Next.js creates a `project` row directly. The Prevents clause in AD-3 ("Next.js의 직접 쓰기") plus the AD-1 Rule (FastAPI is the single app for business logic) together correctly block this — except for the loophole identified in Gap-7 above (which is a rule-wording inconsistency, not a Next.js can create projects scenario).

**2. External vector DB for RAG (AD-2 + AD-6):** Tried to justify an external Pinecone index for a new Playbook's specialized RAG. AD-2 ("외부 벡터 DB 불허") and AD-6 ("RAG는 외부 벡터 DB 불허") state this twice, redundantly. Two redundant statements make evasion harder. This attack fails.

**3. Second Insurance Project in MVP (AD-8):** Tried to justify a builder creating multi-project support since AD-4 allows multiple `projects` rows per user. AD-8 explicitly blocks this: "사용자당 Insurance Project 1개 자동 생성" and "Prevents: MVP 내 다중 Insurance Project." The spine holds here.

**4. Memory table introduction (AD-7):** Tried to construct a path where a builder adds a `memories` table to speed up context assembly. AD-7 explicitly prevents premature Memory schema introduction and requires real-usage evidence first. The condition gate is clearly stated. This attack fails.

**5. Separate microservice for Career Playbook (AD-1):** AD-1's Rule is unambiguous: "새 Playbook 추가 = FastAPI 내부에 모듈 추가; 별도 서비스 배포 불허." A builder cannot create a separate service without violating the Rule directly. Spine holds.

**6. State machine skipping `processing` (AD-5):** Tried to build a fast-path that goes `pending → completed` directly (for cached results). AD-5's state machine is stated as `pending → processing → completed | failed` — the `processing` state is required. However, AD-5 does not explicitly say "no state may be skipped" — it draws the machine but does not add a rule prohibiting gaps. This is a minor latent risk but not a builder-level incompatibility since no current feature creates a second builder with a reason to skip.

---

## Summary Table

| Gap | Attack Vector | Severity | AD to Add |
|-----|---------------|----------|-----------|
| Gap-1 | `context_snapshot`/`result` JSONB shape free-for-all | High — breaks all cross-review consumers | New AD: Review Result Envelope |
| Gap-2 | Terminal state mutability + double-write | High — silent data corruption + duplicate Realtime events | Amend AD-5: terminal states immutable |
| Gap-3 | Realtime payload contract undefined | Medium — breaks frontend without coordination | Amend AD-5: specify payload + REPLICA IDENTITY |
| Gap-4 | RLS implementation pattern diverges | High — security semantics differ per Playbook | Amend AD-3: mandate denormalized `user_id` + pattern |
| Gap-5 | LLM Provider Interface has no method signature | High — provider swap breaks all callers | Amend AD-6: define `generate()` signature + error type |
| Gap-6 | Playbook table naming/type conventions absent | Medium — cross-playbook features and migrations break | Amend AD-4: add schema conventions rule |
| Gap-7 | "AI-generated" write boundary exploitable by user-initiated mutations | High — race condition + undeclared state | Amend AD-3: all writes via FastAPI, not just AI-generated |
