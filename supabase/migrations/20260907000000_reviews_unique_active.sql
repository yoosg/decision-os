-- /reviews/trigger TOCTOU 레이스 방지.
-- 존재 확인(SELECT)과 INSERT 사이 레이스로 동일 signal_id+project_id에 대해 pending/processing
-- row가 중복 생성됐다. 관측: 클릭 1회에 리뷰 2행이 149ms 간격 생성 → 카드가 두 장 만들어져
-- LLM 호출·비용이 2배. completed/failed 이력 row는 여러 개 허용해야 하므로(재시도 시 새 row
-- INSERT) 부분 유니크 인덱스로 pending/processing만 제약한다.
--
-- 20260727000000_learning_paths_unique_active.sql과 같은 패턴 — /learning-paths/trigger에서
-- 먼저 발견된 동일한 버그가 /reviews/trigger에는 반영되지 않은 채 남아 있었다.
CREATE UNIQUE INDEX IF NOT EXISTS uq_reviews_active_signal_project
    ON public.reviews(signal_id, project_id)
    WHERE status IN ('pending', 'processing');
