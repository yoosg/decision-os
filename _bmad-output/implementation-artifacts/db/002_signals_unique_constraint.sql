-- Story 2.1 Code Review (P-1): signals(technology_name, signal_date) UNIQUE 제약 추가
-- normalizer가 ON CONFLICT DO NOTHING upsert를 사용할 수 있도록 DB 레이어에서 중복 방지.
ALTER TABLE public.signals
    ADD CONSTRAINT signals_technology_name_signal_date_key
    UNIQUE (technology_name, signal_date);
