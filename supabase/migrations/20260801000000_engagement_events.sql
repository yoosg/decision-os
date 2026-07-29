-- Story 6.5: engagement_events — 측정 하네스용 engagement 이벤트 로그.
--
-- 왜/무엇을:
--   6.1~6.4의 "랭킹 고도화(RAG 재랭킹 vs 콜드스타트)"가 실제로 추천 품질을 올렸는지
--   held-out 지표(Learn Now율·read-through율 등)로 판단하려면, 사용자 반응을 기록할
--   append-only 이벤트 스트림이 필요하다. 이 테이블이 그 스트림이다.
--
--   이벤트 4종(event_type):
--     - impression : brief에 시그널 노출(서버 정본 — recommender가 brief 생성 시 로깅)
--     - open       : Research Review 상세 열람(웹 클라이언트 계측)
--     - read_through: ContextStickyBar 활성화 = 필수 섹션 전부 열람(웹 클라이언트 계측)
--     - decision   : Learn Now / Queue / Ignore(decisions 라우터가 신규 insert 시 로깅)
--
--   variant(rag | coldstart | NULL): held-out 비교의 코호트 라벨. impression에만 서버가
--   정본으로 기록한다(recommender의 memory 분기 결과). decision은 NULL이며 평가 스크립트가
--   (user_id, signal_id)로 impression과 조인해 variant를 attach한다(설계 D5).
--
--   AD-3(쓰기 소유권): 쓰기는 FastAPI service_role만. RLS는 SELECT만 user_id=auth.uid()
--   허용(AD-9 user_id 직접 컬럼 케이스 — daily_briefs·memories와 동형). INSERT/UPDATE/DELETE
--   정책 부재 → service_role만 쓰기 가능(기존 테이블과 동일 패턴).
--   AD-5(safe degradation): 모든 로깅은 best-effort. 이 테이블 쓰기 실패는 핵심 플로우
--   (brief 생성·decision 생성·화면 렌더)를 절대 막지 않는다(코드 레벨 try/except).
--
--   가산적(additive): 신규 테이블 1개만 추가하며 기존 테이블·행·정책은 무변경(무회귀).
--   append-only이므로 updated_at 컬럼/트리거 없음. 모든 DDL은 IF NOT EXISTS(멱등).

CREATE TABLE IF NOT EXISTS public.engagement_events (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    signal_id      UUID NOT NULL REFERENCES public.signals(id) ON DELETE CASCADE,
    daily_brief_id UUID REFERENCES public.daily_briefs(id) ON DELETE SET NULL,
    event_type     TEXT NOT NULL
                       CHECK (event_type IN ('impression', 'open', 'read_through', 'decision')),
    variant        TEXT CHECK (variant IN ('rag', 'coldstart')),
    metadata       JSONB,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Indexes (held-out 평가 집계 + 사용자 타임라인 조회)
-- ============================================================

-- 사용자별 시계열 조회
CREATE INDEX IF NOT EXISTS idx_engagement_user_created
    ON public.engagement_events (user_id, created_at);
-- 시그널 단위 이벤트 타입별 집계(open/read_through 매칭)
CREATE INDEX IF NOT EXISTS idx_engagement_signal_type
    ON public.engagement_events (signal_id, event_type);
-- brief 단위 조회(impression lineage)
CREATE INDEX IF NOT EXISTS idx_engagement_brief
    ON public.engagement_events (daily_brief_id);
-- variant × event_type 집계(평가 하네스 핵심 쿼리)
CREATE INDEX IF NOT EXISTS idx_engagement_variant
    ON public.engagement_events (event_type, variant);

-- ============================================================
-- Row Level Security — AD-9(user_id 직접 컬럼 단순 정책), AD-3(쓰기 service_role만)
-- ============================================================

ALTER TABLE public.engagement_events ENABLE ROW LEVEL SECURITY;

-- engagement_events — SELECT only (user_id 직접 컬럼, daily_briefs·memories와 동형)
-- INSERT/UPDATE/DELETE 정책 부재 → service_role만 쓰기(AD-3)
CREATE POLICY "engagement_events_select" ON public.engagement_events FOR SELECT
    USING (user_id = auth.uid());
