-- Story 5.3 Trigger #3: Outcome 입력 리마인더 1회 발송 추적 컬럼.
-- Learn Now 후 3일 경과 + Outcome 미기록 + 미발송(NULL) 조건으로 1회만 push 후 기록.
ALTER TABLE public.decisions
    ADD COLUMN IF NOT EXISTS outcome_reminder_sent_at TIMESTAMPTZ;
