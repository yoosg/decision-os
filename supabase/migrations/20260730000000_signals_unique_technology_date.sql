-- 로컬 실행 검증(2026-07-28)에서 발견: normalizer가
-- upsert(on_conflict="technology_name,signal_date")로 "하루 1기술 1시그널"을 보장하는데,
-- 대응하는 UNIQUE 제약이 initial_schema 및 이후 어떤 마이그레이션에도 정의되지 않았다.
-- 그 결과 upsert가 "ON CONFLICT 대상 제약 없음" 예외를 던지고 normalizer의 try/except가
-- 이를 삼켜, 파이프라인이 시그널을 0건 생성하는(무증상) 버그가 있었다.
CREATE UNIQUE INDEX IF NOT EXISTS uq_signals_technology_date
    ON public.signals (technology_name, signal_date);
