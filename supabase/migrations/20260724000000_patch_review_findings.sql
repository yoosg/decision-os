-- Decision OS — Patch Migration
-- Story 1.1 코드 리뷰 지적 사항 중 초기 DB 푸시 시 누락된 항목 적용
-- Date: 2026-07-24

-- ============================================================
-- 1. decisions: UNIQUE(review_id) — 한 리뷰당 결정 1개 보장
-- ============================================================
ALTER TABLE public.decisions
    ADD CONSTRAINT decisions_review_id_key UNIQUE (review_id);

-- ============================================================
-- 2. outcomes: chk_useful_required — completed/applied 시 useful 필수
-- ============================================================
ALTER TABLE public.outcomes
    ADD CONSTRAINT chk_useful_required
    CHECK (status NOT IN ('completed', 'applied') OR useful IS NOT NULL);

-- ============================================================
-- 3. reviews: playbook_type 값 제한
-- ============================================================
ALTER TABLE public.reviews
    ADD CONSTRAINT chk_reviews_playbook_type
    CHECK (playbook_type IN ('ai_research'));

-- ============================================================
-- 4. learning_paths: processing_started_at 컬럼 + Stuck 인덱스 (AD-12)
-- ============================================================
ALTER TABLE public.learning_paths
    ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_learning_paths_stuck
    ON public.learning_paths(processing_started_at)
    WHERE status = 'processing';

-- ============================================================
-- 5. user_profiles: display_name 길이 제약
-- ============================================================
ALTER TABLE public.user_profiles
    ADD CONSTRAINT chk_display_name_length
    CHECK (display_name IS NULL OR char_length(display_name) <= 256);

-- ============================================================
-- 6. daily_brief_signals: UNIQUE(daily_brief_id, position) — 위치 충돌 방지
-- ============================================================
ALTER TABLE public.daily_brief_signals
    ADD CONSTRAINT daily_brief_signals_brief_position_key
    UNIQUE (daily_brief_id, position);

-- ============================================================
-- 7. signals / signal_sources: RLS 활성화 + 인증 사용자 SELECT 정책
-- ============================================================
ALTER TABLE public.signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.signal_sources ENABLE ROW LEVEL SECURITY;

CREATE POLICY "signals_select" ON public.signals FOR SELECT
    USING (auth.uid() IS NOT NULL);

CREATE POLICY "signal_sources_select" ON public.signal_sources FOR SELECT
    USING (auth.uid() IS NOT NULL);

-- ============================================================
-- 8. set_updated_at: search_path 고정 (보안 경고 해소)
-- ============================================================
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- ============================================================
-- 9. handle_new_user: search_path 고정 + anon/authenticated EXECUTE 제거
-- ============================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO public.user_profiles (id, display_name)
    VALUES (NEW.id, NEW.raw_user_meta_data->>'display_name')
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM anon;
REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM authenticated;

-- ============================================================
-- 10. mark_stuck_jobs: search_path 고정 + 30일 가드 + 권한 정리
-- ============================================================
CREATE OR REPLACE FUNCTION public.mark_stuck_jobs(timeout_minutes INTEGER DEFAULT 15)
RETURNS INTEGER LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    cnt INTEGER := 0;
    tmp INTEGER;
BEGIN
    -- Stuck reviews (30일 이내 레코드만 — 전체 테이블 스캔 방지)
    UPDATE public.reviews
    SET
        status        = 'failed',
        error_message = 'processing timeout: exceeded ' || timeout_minutes || ' minutes',
        completed_at  = NOW()
    WHERE status = 'processing'
      AND processing_started_at < NOW() - (timeout_minutes || ' minutes')::INTERVAL
      AND created_at > NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS tmp = ROW_COUNT;
    cnt := cnt + tmp;

    -- Stuck learning paths
    UPDATE public.learning_paths
    SET
        status        = 'failed',
        error_message = 'processing timeout: exceeded ' || timeout_minutes || ' minutes',
        updated_at    = NOW()
    WHERE status = 'processing'
      AND processing_started_at < NOW() - (timeout_minutes || ' minutes')::INTERVAL
      AND created_at > NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS tmp = ROW_COUNT;
    cnt := cnt + tmp;

    RETURN cnt;
END;
$$;

REVOKE ALL ON FUNCTION public.mark_stuck_jobs(INTEGER) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.mark_stuck_jobs(INTEGER) FROM anon;
REVOKE EXECUTE ON FUNCTION public.mark_stuck_jobs(INTEGER) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.mark_stuck_jobs(INTEGER) TO service_role;
