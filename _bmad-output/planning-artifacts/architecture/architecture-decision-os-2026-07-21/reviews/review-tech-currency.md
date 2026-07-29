# Tech Currency Review — Decision OS Architecture Spine
Date: 2026-07-22
Reviewer: Tech Currency (web-verified)

---

## Verdict

The core stack (Next.js 16, FastAPI 0.139, Supabase + pgvector, OpenAI) is current and fits the use case, but two decisions carry meaningful risk: Railway has documented production reliability issues in 2026 that make it a shaky foundation for anything beyond a prototype, and FastAPI BackgroundTasks will hit a hard ceiling as LLM workload concurrency grows — the architecture already defers a message broker upgrade but does not name the trigger clearly enough.

---

## Critical (outdated/wrong tech that affects design)

### 1. OpenAI API: Responses API is now the recommended default — Chat Completions is no longer the "current" approach for new projects

**What the spine says:** "LLM Provider (OpenAI MVP)" — no API surface specified. AD-6 and AD-8 imply a simple request/response pattern without specifying Chat Completions vs. Responses API.

**What was found:** OpenAI officially recommends the Responses API for all new projects as of 2025–2026. Chat Completions remains supported for lightweight stateless flows but future model capabilities (reasoning, multimodal, built-in tool use like file search and web search) will land in Responses API first. The Assistants API is being sunset in 2026, making Responses the long-term path. Internal OpenAI evals show 40–80% cache utilization improvement and measurable cost reduction versus Chat Completions.

**Impact on design:** The spine's LLM Provider Interface abstraction (AD-6) is a good pattern, but the initial OpenAI implementation should target the Responses API, not Chat Completions. The `ReviewContextBuilder` pattern and the RAG flow (file search is a built-in Responses API tool) could simplify significantly if the implementation uses the right API surface from the start. Retrofitting later is low-risk given the provider abstraction, but building against Chat Completions from day one means unnecessary rework.

**Action:** Specify `Responses API` (not Chat Completions) as the target for the OpenAI provider implementation in AD-6. Note Chat Completions as the fallback for simple stateless calls only.

---

### 2. Railway: Documented production reliability issues in 2026 — not suitable as-is for the deployment platform

**What the spine says:** AD-2 binds both Next.js and FastAPI to Railway.

**What was found:** Multiple independent sources in 2026 report: stuck deployments, silent cron job failures, false-positive status pages, and severe edge routing bugs. Railway is explicitly not recommended for production Next.js applications that matter to your business. For FastAPI specifically, Railway is described as a poor default for apps handling long-running work, file processing, or scheduled jobs — which is exactly what Decision OS does (BackgroundTasks for LLM processing, Storage uploads). Railway had two notable outages in 2026. Railway does offer a Next.js + FastAPI full-stack starter template, so the deployment pattern works, but operational risk is elevated.

**Impact on design:** AD-2 locks both services to Railway. The current design makes Railway a single point of failure for the entire system. For an MVP/prototype this is acceptable and fast to ship, but the architecture spine makes no mention of the operational risk or an exit path.

**Action:** Either (a) add a caveat to AD-2 explicitly scoping Railway to MVP/prototype only with a noted upgrade path to Render, Fly.io, or Vercel (for Next.js) + Render/Fly (for FastAPI), or (b) replace Railway with a more reliable default. At minimum, the spine should acknowledge Railway's known reliability profile and tie a deployment platform re-evaluation to the first production milestone.

---

## Verified Current (confirmed via web)

### Next.js 16 (current: 16.2.10 LTS / 16.2.11 latest patch, July 2026)
Confirmed current and actively maintained. Next.js 16.2.6 ships Turbopack as the default bundler, React 19.2, Cache Components, and async params. Next.js 16.3 Preview adds AI-specific tooling. No breaking changes found that would affect the AD-3 data access pattern (direct Supabase client reads on the frontend, REST calls to FastAPI for writes). The App Router pattern assumed by the architecture is the established default. **No changes required.**

### FastAPI 0.139.x (current: 0.139.2 as of July 16, 2026)
Confirmed current. FastAPI remains the standard Python async web framework. Requires Python 3.10+; Python 3.12 or 3.13 is the recommended target for new projects in 2026. Generates OpenAPI 3.1 docs out of the box. The modular monolith pattern (AD-1, internal routers per playbook) is idiomatic FastAPI. **No changes required, but ensure Python 3.12+ is pinned in the project.**

### Supabase: PostgreSQL + Auth + Storage + Realtime — all confirmed current and production-ready
All four Supabase primitives used by the spine are confirmed stable:
- **PostgreSQL + Auth + Storage**: Standard Supabase offering, no changes.
- **Realtime**: Built on Elixir Phoenix, supports millions of concurrent WebSocket connections. Postgres Changes path has ~50–200ms latency via WAL replication — acceptable for the Review completion notification flow in AD-5. Pro plan includes Realtime; >500 concurrent connections requires Team plan. The Realtime subscription pattern in AD-5 (`FE → DB: Realtime 구독 (review_id)`) is correct and idiomatic. **No changes required.**
- **RLS pattern (AD-3)**: Read via anon key + JWT + RLS, write via service_role through FastAPI — this is the canonical Supabase security pattern as of 2026. **Confirmed correct.**

### Supabase pgvector — confirmed production-ready, HNSW index required
pgvector is confirmed stable and production-ready for the use case. Current versions in production: pgvector 0.6.0–0.7.4. HNSW is the 2026 recommended index (not IVFFlat), keeping query latency under 10ms at p99 for up to ~5 million vectors on a Supabase Pro instance. For the insurance policy RAG use case (policy documents per user, small corpus), a single Supabase Pro instance with pgvector is sufficient and cost-effective. The spine's rule ("RAG는 pgvector(Supabase)가 담당; 외부 벡터 DB 불허") is sound for this scale. **No changes required, but implementation must use HNSW index, not IVFFlat.**

### FastAPI BackgroundTasks — correct for MVP, but the scale ceiling is well-documented
BackgroundTasks is confirmed appropriate for fire-and-forget, single-process async tasks. For LLM API calls (async HTTP I/O), it works well at low concurrency because the tasks are awaiting network I/O. The spine already defers message broker adoption (Deferred table: "BackgroundTasks 처리 용량 한계 도달 시"). **This deferral is correct.** However, the trigger criterion is vague.

---

## Concerns / Watch Items

### A. BackgroundTasks scale ceiling: trigger criterion needs a concrete threshold

The spine defers Redis/Celery until "처리 용량 한계 도달 시" (when capacity limit is reached). Current 2026 benchmarks show:
- BackgroundTasks: fine for < ~20–30 concurrent LLM requests in a single process
- ARQ (Redis-backed async queue): handles 50+ concurrent LLM calls with far better observability and retry logic
- Celery: still lacks native async/await in 2025–2026, making it the wrong choice for async LLM workloads; ARQ is the 2026 community recommendation for FastAPI + async LLM

The Deferred table should specify ARQ (not Celery) as the preferred upgrade path, and set a concrete trigger (e.g., "concurrent review processing exceeds 20 simultaneous jobs, or any BackgroundTask failure rate > 1% with no retry visibility").

### B. Railway free/hobby tier limits are tight for the full stack

Railway Hobby plan is $5/month with usage billed on top. Running two services (Next.js + FastAPI) plus any Redis or Postgres instance (if not using Supabase exclusively) will exceed the credit ceiling quickly. Since the spine uses Supabase for all data (no Railway-hosted Postgres), this is manageable — but Railway's network egress charges can surprise teams. Worth tracking from the first deployment.

### C. Supabase pgvector index maintenance window

The most common production incident with Supabase pgvector is ignoring index maintenance (VACUUM / REINDEX), which causes cascading query timeouts and memory exhaustion. For the insurance RAG use case, policy document embeddings will be relatively static once ingested, so this risk is low — but the team should plan a scheduled REINDEX during low-traffic windows before the corpus exceeds ~100K vectors.

### D. Supabase Realtime at scale: concurrent connection limits

For MVP (single-user or small beta), the Free/Pro plan Realtime limits are non-issues. However, Postgres Changes latency (~50–200ms) means that for near-real-time feedback during LLM processing, the UI should show a progress/spinner state and not assume instant delivery. The architecture already handles this correctly (polling as fallback in AD-5), so no change needed — just confirm the polling interval is set as a true fallback, not just a comment.

### E. OpenAI model selection not specified

The spine names "OpenAI" and "LLM Provider Interface" but does not specify which model tier. As of July 2026, GPT-4o is the cost-effective workhorse for structured JSON extraction and RAG-augmented generation; o3/GPT-5 reasoning models are expensive and overkill for claim analysis with well-structured context. The Provider Interface (AD-6) should document the initial model selection rationale so it doesn't drift to expensive models under "just try it" pressure.

---

## Summary Table

| Technology | Status | Version Verified | Action Required |
|---|---|---|---|
| Next.js | Current | 16.2.10 LTS (July 2026) | None |
| FastAPI | Current | 0.139.2 (July 2026) | Pin Python 3.12+ |
| Supabase Auth + Storage | Current | — | None |
| Supabase Realtime | Current | — | None |
| Supabase pgvector | Production-ready | 0.6.0–0.7.4 | Use HNSW index explicitly |
| Railway | Viable for MVP only | — | Add reliability caveat + exit path to spine |
| OpenAI API (Chat Completions assumed) | Outdated default | Responses API is now recommended | Specify Responses API in AD-6 |
| FastAPI BackgroundTasks | Correct for MVP | — | Specify ARQ (not Celery) in Deferred table; add concrete trigger threshold |
