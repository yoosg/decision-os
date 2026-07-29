-- Story 6.3: Signal 스키마 v2 — 랭킹 메타데이터 확장.
--
-- 왜/무엇을:
--   6.2가 인프로세스로 만든 클러스터(다출처 토픽)를 signals 테이블에 "랭킹 메타데이터"와
--   함께 영속화한다. 다음 스토리(6.4 Recommender v2)가 최신성(published_at)·인기(popularity)
--   ·출처 권위(source_authority)를 실제 데이터로 랭킹에 쓰기 위한 저장 단계다.
--   이 스토리는 "저장까지"만 담당하고, 랭킹 점수식 사용은 6.4 스코프다.
--
--   추가 컬럼(모두 가산적 additive — 기존 행은 DEFAULT로 안전 백필, 무회귀):
--     - published_at    : 클러스터 내 원문 최신 발행 시각(UTC). nullable.
--     - popularity      : 인기 신호 집계(예: HN points 합). NOT NULL DEFAULT 0.
--     - source_authority: 클러스터 내 최고 출처 권위 등급(0~4). NOT NULL DEFAULT 0.
--     - cluster_key     : 6.2 클러스터 식별키(다출처 토픽 lineage). nullable.
--
--   uq_signals_technology_date(20260730) 유지 이유:
--     normalizer의 upsert dedup 키는 여전히 (technology_name, signal_date)다(설계결정 D2).
--     cluster_key는 pass-through(임베딩 실패) 기사에서 NULL이라 upsert 충돌 키로 쓰기엔
--     NULL 다중행 처리가 지저분하다. 따라서 cluster_key는 dedup "전환"이 아니라 "보완"으로,
--     아래 부분 UNIQUE 인덱스(cluster_key IS NOT NULL)로 클러스터 dedup을 보강만 한다.
--
--   모든 DDL은 IF NOT EXISTS — 재적용 안전(멱등).

ALTER TABLE public.signals ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;
ALTER TABLE public.signals ADD COLUMN IF NOT EXISTS popularity INTEGER NOT NULL DEFAULT 0;
ALTER TABLE public.signals ADD COLUMN IF NOT EXISTS source_authority SMALLINT NOT NULL DEFAULT 0;
ALTER TABLE public.signals ADD COLUMN IF NOT EXISTS cluster_key TEXT;

-- 최신성 랭킹용 인덱스(6.4가 published_at DESC로 정렬). NULL은 마지막.
CREATE INDEX IF NOT EXISTS idx_signals_published_at
    ON public.signals (published_at DESC NULLS LAST);

-- 클러스터 기반 dedup 보완: 같은 클러스터(cluster_key)가 같은 날 중복 저장되지 않도록.
-- cluster_key가 NULL인 pass-through 기사는 이 제약에서 제외(부분 UNIQUE).
CREATE UNIQUE INDEX IF NOT EXISTS uq_signals_cluster_date
    ON public.signals (cluster_key, signal_date)
    WHERE cluster_key IS NOT NULL;
