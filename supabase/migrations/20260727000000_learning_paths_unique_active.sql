-- Story 4.1 코드 리뷰: /learning-paths/trigger TOCTOU 레이스 방지.
-- 존재 확인(SELECT)과 INSERT 사이 레이스로 동일 decision_id에 대해 pending/processing
-- row가 중복 생성될 수 있었다. completed/failed 이력 row는 여러 개 허용해야 하므로
-- (재시도 시 새 row INSERT) 부분 유니크 인덱스로 pending/processing만 제약한다.
CREATE UNIQUE INDEX IF NOT EXISTS uq_learning_paths_active_decision
    ON public.learning_paths(decision_id)
    WHERE status IN ('pending', 'processing');
