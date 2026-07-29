-- AC-6: daily_briefs stuck job 감지를 위한 processing_started_at 컬럼 추가
ALTER TABLE public.daily_briefs
    ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_daily_briefs_stuck
    ON public.daily_briefs(processing_started_at)
    WHERE status = 'processing' AND processing_started_at IS NOT NULL;
