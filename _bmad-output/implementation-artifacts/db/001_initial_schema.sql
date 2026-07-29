-- Decision OS — Supabase Initial Schema
-- Playbook: AI Research (MVP)
-- Architecture: AD-2, AD-3, AD-4, AD-7, AD-9, AD-12, AD-15, AD-17
-- Date: 2026-07-23
-- Insurance Playbook 테이블은 archive_insurance_schema.sql 참고

-- ============================================================
-- Extensions
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";   -- pgvector (AD-2)

-- ============================================================
-- User Tables
-- ============================================================

-- 사용자 프로필 + 온보딩 데이터 (auth.users 확장)
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id                      UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name            TEXT,
    -- 온보딩 7단계 데이터 (FR-0.2)
    role                    TEXT,   -- 'frontend' | 'backend' | 'ai_engineer' | 'pm' | 'designer' | 'student' | 'other'
    experience_level        TEXT,   -- 'beginner' | 'intermediate' | 'advanced'
    tech_stack              TEXT[], -- ['Next.js', 'Python', 'LangGraph', ...]
    project_goal            TEXT,   -- 'ai_side_project' | 'rag_service' | 'agent_architecture' | 'work_automation' | 'ai_adoption' | 'other'
    interests               TEXT[], -- ['Agent', 'RAG', 'MCP', ...]
    daily_learning_time_min INTEGER,-- 15 | 30 | 60
    onboarding_completed    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- FCM 디바이스 토큰 (AD-17) — FastAPI만 쓰기
CREATE TABLE IF NOT EXISTS public.user_devices (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    fcm_token  TEXT NOT NULL,
    platform   TEXT NOT NULL CHECK (platform IN ('web', 'ios', 'android')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, fcm_token)
);

-- ============================================================
-- Platform Tables (Playbook 공통)
-- ============================================================

-- 프로젝트 (Playbook 공간, MVP: 사용자당 ai_research 1개 자동 생성)
CREATE TABLE IF NOT EXISTS public.projects (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    playbook_type TEXT NOT NULL CHECK (playbook_type IN ('ai_research')),  -- 향후 확장 시 추가
    name          TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Review (AI 분석 작업 — 비동기, AD-5)
-- context_snapshot / result: JSONB 봉투 {"schema_version", "review_type", "payload"} (AD-4)
CREATE TABLE IF NOT EXISTS public.reviews (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id            UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    signal_id             UUID,       -- FK signals 추가 후 아래 ALTER로 연결
    playbook_type         TEXT NOT NULL,
    review_type           TEXT NOT NULL,  -- AI Research MVP: 'research'
    status                TEXT NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    bar_gate_override     TEXT CHECK (bar_gate_override IN ('force_enable', 'force_disable')),  -- ContextStickyBar 강제 제어
    context_snapshot      JSONB,
    result                JSONB,
    error_message         TEXT,
    processing_started_at TIMESTAMPTZ,   -- stuck 감지용 (AD-12)
    completed_at          TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_context_snapshot_envelope CHECK (
        context_snapshot IS NULL OR (
            context_snapshot ? 'schema_version' AND
            context_snapshot ? 'review_type'    AND
            context_snapshot ? 'payload'
        )
    ),
    CONSTRAINT chk_result_envelope CHECK (
        result IS NULL OR (
            result ? 'schema_version' AND
            result ? 'review_type'    AND
            result ? 'payload'
        )
    )
);

-- Decision (사용자 선택 기록) — 쓰기: FastAPI만 (AD-3)
CREATE TABLE IF NOT EXISTS public.decisions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id    UUID NOT NULL REFERENCES public.reviews(id) ON DELETE CASCADE,
    choice       TEXT NOT NULL CHECK (choice IN ('learn_now', 'queue', 'ignore')),
    queue_timing TEXT CHECK (queue_timing IN ('today', 'this_week', 'later')),  -- choice='queue' 시 필수
    memo         TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_queue_timing CHECK (
        (choice = 'queue' AND queue_timing IS NOT NULL) OR
        (choice != 'queue')
    )
);

-- Outcome (학습 결과 추적) — 쓰기: FastAPI만 (AD-3)
CREATE TABLE IF NOT EXISTS public.outcomes (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id             UUID NOT NULL REFERENCES public.decisions(id) ON DELETE CASCADE,
    status                  TEXT NOT NULL
                                CHECK (status IN ('completed', 'applied', 'dropped', 'not_useful')),
    useful                  BOOLEAN,
    actual_learning_time_min INTEGER,
    applied_project_note    TEXT,   -- Applied 선택 시 프로젝트 메모
    memo                    TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Memory (의사결정 장기 학습 자산) — 쓰기: FastAPI만, Outcome 후 AI 추출 (AD-3, AD-7)
CREATE TABLE IF NOT EXISTS public.memories (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    memory_type        TEXT NOT NULL
                           CHECK (memory_type IN (
                               'preference',        -- 사용자 학습 선호 패턴
                               'skill',             -- 보유 기술 및 수준
                               'project',           -- 현재 프로젝트 맥락
                               'decision_history',  -- 과거 결정 패턴
                               'outcome_history'    -- 학습 결과 패턴
                           )),
    summary            TEXT NOT NULL,   -- AI가 자연어로 정리한 기억 요약
    embedding          VECTOR(1536),    -- summary 임베딩 (Recommender RAG용, AD-7)
    source_decision_id UUID REFERENCES public.decisions(id) ON DELETE SET NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Activity (UI 타임라인용 감사 로그) — 쓰기: FastAPI만 (AD-3)
CREATE TABLE IF NOT EXISTS public.activities (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id    UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    activity_type TEXT NOT NULL,
    payload       JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- AI Research Playbook Tables (AD-4, AD-15, AD-16)
-- ============================================================

-- Signal (기술 단위 큐레이션 이벤트 — 플랫폼 레벨, 사용자 무관)
CREATE TABLE IF NOT EXISTS public.signals (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    technology_name  TEXT NOT NULL,
    title            TEXT NOT NULL,
    summary          TEXT,
    signal_date      DATE NOT NULL,
    status           TEXT NOT NULL DEFAULT 'raw'
                         CHECK (status IN ('raw', 'processed', 'archived')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Signal 출처 (Official Blog, GitHub, Reddit, HN, YouTube 등)
CREATE TABLE IF NOT EXISTS public.signal_sources (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id   UUID NOT NULL REFERENCES public.signals(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL CHECK (source_type IN ('official_blog', 'github', 'reddit', 'hn', 'youtube', 'other')),
    url         TEXT NOT NULL,
    title       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Daily Brief (사용자별 일일 브리핑 — 사용자 레벨)
CREATE TABLE IF NOT EXISTS public.daily_briefs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    brief_date   DATE NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    generated_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, brief_date)
);

-- Daily Brief ↔ Signal 연결 (관련성 점수 포함)
CREATE TABLE IF NOT EXISTS public.daily_brief_signals (
    daily_brief_id  UUID NOT NULL REFERENCES public.daily_briefs(id) ON DELETE CASCADE,
    signal_id       UUID NOT NULL REFERENCES public.signals(id) ON DELETE CASCADE,
    relevance_score FLOAT NOT NULL,
    position        INTEGER NOT NULL,
    PRIMARY KEY (daily_brief_id, signal_id)
);

-- Learning Path (Learn Now 결정 후 AI 생성 — 사용자 레벨, AD-5)
-- resources JSONB: {"schema_version": 1, "items": [{type, title, url, descriptor}, ...]}
CREATE TABLE IF NOT EXISTS public.learning_paths (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id UUID NOT NULL REFERENCES public.decisions(id) ON DELETE CASCADE,
    signal_id   UUID NOT NULL REFERENCES public.signals(id)   ON DELETE CASCADE,
    resources   JSONB,
    status      TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- reviews.signal_id FK 연결 (signals 테이블 생성 후)
ALTER TABLE public.reviews
    ADD CONSTRAINT fk_reviews_signal
    FOREIGN KEY (signal_id) REFERENCES public.signals(id) ON DELETE SET NULL;

-- ============================================================
-- Indexes
-- ============================================================

-- User
CREATE INDEX IF NOT EXISTS idx_user_devices_user_id    ON public.user_devices(user_id);

-- Projects
CREATE INDEX IF NOT EXISTS idx_projects_user_id        ON public.projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_playbook_type  ON public.projects(user_id, playbook_type);

-- Reviews
CREATE INDEX IF NOT EXISTS idx_reviews_project_id      ON public.reviews(project_id);
CREATE INDEX IF NOT EXISTS idx_reviews_signal_id       ON public.reviews(signal_id);
CREATE INDEX IF NOT EXISTS idx_reviews_status          ON public.reviews(status);
CREATE INDEX IF NOT EXISTS idx_reviews_stuck           ON public.reviews(processing_started_at)
    WHERE status = 'processing';

-- Decisions / Outcomes
CREATE INDEX IF NOT EXISTS idx_decisions_review_id     ON public.decisions(review_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_decision_id    ON public.outcomes(decision_id);

-- Memories
CREATE INDEX IF NOT EXISTS idx_memories_user_id        ON public.memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_type           ON public.memories(user_id, memory_type);

-- Activities
CREATE INDEX IF NOT EXISTS idx_activities_project_id   ON public.activities(project_id, created_at DESC);

-- Signals
CREATE INDEX IF NOT EXISTS idx_signals_date            ON public.signals(signal_date DESC);
CREATE INDEX IF NOT EXISTS idx_signals_status          ON public.signals(status);
CREATE INDEX IF NOT EXISTS idx_signal_sources_signal   ON public.signal_sources(signal_id);

-- Daily Briefs
CREATE INDEX IF NOT EXISTS idx_daily_briefs_user_date  ON public.daily_briefs(user_id, brief_date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_brief_signals_brief ON public.daily_brief_signals(daily_brief_id, position);

-- Learning Paths
CREATE INDEX IF NOT EXISTS idx_learning_paths_decision ON public.learning_paths(decision_id);
CREATE INDEX IF NOT EXISTS idx_learning_paths_status   ON public.learning_paths(status);

-- HNSW 벡터 인덱스 — memories (Recommender RAG, AD-2)
CREATE INDEX IF NOT EXISTS idx_memories_embedding
    ON public.memories
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================================
-- Row Level Security — AD-9 표준 패턴
-- ============================================================

ALTER TABLE public.user_profiles     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_devices      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reviews           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.decisions         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.outcomes          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memories          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.activities        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_briefs      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_brief_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learning_paths    ENABLE ROW LEVEL SECURITY;
-- signals / signal_sources: 플랫폼 레벨 (RLS 불필요, FastAPI service_role만 접근)

-- user_profiles
CREATE POLICY "user_profiles_own" ON public.user_profiles
    USING (id = auth.uid()) WITH CHECK (id = auth.uid());

-- user_devices — SELECT only (쓰기: FastAPI, AD-3)
CREATE POLICY "user_devices_select" ON public.user_devices FOR SELECT
    USING (user_id = auth.uid());

-- projects
CREATE POLICY "projects_own" ON public.projects
    USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

-- reviews — SELECT only (쓰기: FastAPI service_role, AD-3)
CREATE POLICY "reviews_select" ON public.reviews FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.projects p
        WHERE p.id = project_id AND p.user_id = auth.uid()
    ));

-- decisions — SELECT only (AD-9: project_id 경유 서브쿼리)
CREATE POLICY "decisions_select" ON public.decisions FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.reviews r
        JOIN public.projects p ON p.id = r.project_id
        WHERE r.id = review_id AND p.user_id = auth.uid()
    ));

-- outcomes — SELECT only
CREATE POLICY "outcomes_select" ON public.outcomes FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.decisions d
        JOIN public.reviews r ON r.id = d.review_id
        JOIN public.projects p ON p.id = r.project_id
        WHERE d.id = decision_id AND p.user_id = auth.uid()
    ));

-- memories — SELECT only, user_id 직접 컬럼 (AD-9: user_id 직접 테이블 단순 정책)
CREATE POLICY "memories_select" ON public.memories FOR SELECT
    USING (user_id = auth.uid());

-- activities — SELECT only
CREATE POLICY "activities_select" ON public.activities FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.projects p
        WHERE p.id = project_id AND p.user_id = auth.uid()
    ));

-- daily_briefs — SELECT only (user_id 직접 컬럼)
CREATE POLICY "daily_briefs_select" ON public.daily_briefs FOR SELECT
    USING (user_id = auth.uid());

-- daily_brief_signals — SELECT only (daily_brief_id 경유)
CREATE POLICY "daily_brief_signals_select" ON public.daily_brief_signals FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.daily_briefs db
        WHERE db.id = daily_brief_id AND db.user_id = auth.uid()
    ));

-- learning_paths — SELECT only (decision_id → review_id → project_id 경유)
CREATE POLICY "learning_paths_select" ON public.learning_paths FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.decisions d
        JOIN public.reviews r ON r.id = d.review_id
        JOIN public.projects p ON p.id = r.project_id
        WHERE d.id = decision_id AND p.user_id = auth.uid()
    ));

-- ============================================================
-- Realtime (AD-5: 프론트가 완료 감지)
-- ============================================================

ALTER PUBLICATION supabase_realtime ADD TABLE public.reviews;
ALTER PUBLICATION supabase_realtime ADD TABLE public.daily_briefs;
ALTER PUBLICATION supabase_realtime ADD TABLE public.learning_paths;

-- ============================================================
-- updated_at 자동 갱신 트리거
-- ============================================================

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_user_profiles_updated_at
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_user_devices_updated_at
    BEFORE UPDATE ON public.user_devices
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_projects_updated_at
    BEFORE UPDATE ON public.projects
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_reviews_updated_at
    BEFORE UPDATE ON public.reviews
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_decisions_updated_at
    BEFORE UPDATE ON public.decisions
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_outcomes_updated_at
    BEFORE UPDATE ON public.outcomes
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_signals_updated_at
    BEFORE UPDATE ON public.signals
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_daily_briefs_updated_at
    BEFORE UPDATE ON public.daily_briefs
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_learning_paths_updated_at
    BEFORE UPDATE ON public.learning_paths
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============================================================
-- 신규 가입 시 user_profiles 자동 생성
-- ============================================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    INSERT INTO public.user_profiles (id, display_name)
    VALUES (NEW.id, NEW.raw_user_meta_data->>'display_name')
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================
-- Stuck Review / Learning Path 자동 처리 (AD-12)
-- 사용법: SELECT public.mark_stuck_jobs(15);
-- ============================================================

CREATE OR REPLACE FUNCTION public.mark_stuck_jobs(timeout_minutes INTEGER DEFAULT 15)
RETURNS INTEGER LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    cnt INTEGER := 0;
    tmp INTEGER;
BEGIN
    -- Stuck reviews
    UPDATE public.reviews
    SET
        status        = 'failed',
        error_message = 'processing timeout: exceeded ' || timeout_minutes || ' minutes',
        completed_at  = NOW()
    WHERE status = 'processing'
      AND processing_started_at < NOW() - (timeout_minutes || ' minutes')::INTERVAL;
    GET DIAGNOSTICS tmp = ROW_COUNT;
    cnt := cnt + tmp;

    -- Stuck learning paths (updated_at 기준)
    UPDATE public.learning_paths
    SET
        status        = 'failed',
        error_message = 'processing timeout: exceeded ' || timeout_minutes || ' minutes',
        updated_at    = NOW()
    WHERE status = 'processing'
      AND updated_at < NOW() - (timeout_minutes || ' minutes')::INTERVAL;
    GET DIAGNOSTICS tmp = ROW_COUNT;
    cnt := cnt + tmp;

    RETURN cnt;
END;
$$;
