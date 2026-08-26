-- 입문자 카드 진도/결과 저장 — project_card_progress
--
-- 왜/무엇을:
--   입문자 프로젝트 카드 상세화면의 ④ 진도(마일스톤 체크)·⑥ 성공 체크리스트·⑦ 결과가
--   지금은 로컬 상태라 새로고침 시 유실된다. 이 테이블은 "카드 1장 × 유저 1명 = 1행"의
--   개인 진행상태를 영속화한다. 체크 상태는 카드 payload(milestones/success_checklist)의
--   인덱스 배열로 저장한다(카드 재생성 전까지 순서 안정).
--
--   쓰기 소유권(AD-3): 쓰기는 FastAPI service_role만. RLS는 SELECT만 user_id=auth.uid()
--   허용(engagement_events·memories와 동형). INSERT/UPDATE/DELETE 정책 부재 → service_role만.
--   가산적(additive): 신규 테이블 1개만 추가, 기존 테이블·행·정책 무변경(무회귀).
--   모든 DDL은 IF NOT EXISTS(멱등).

CREATE TABLE IF NOT EXISTS public.project_card_progress (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id          UUID NOT NULL REFERENCES public.reviews(id) ON DELETE CASCADE,
    user_id            UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    milestones_checked INTEGER[] NOT NULL DEFAULT '{}',
    checklist_checked  INTEGER[] NOT NULL DEFAULT '{}',
    result             TEXT CHECK (result IN ('success', 'stuck', 'dropped')),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (review_id, user_id)
);

-- 유저별 진행상태 조회
CREATE INDEX IF NOT EXISTS idx_card_progress_user
    ON public.project_card_progress (user_id);

-- RLS — SELECT only (user_id 직접 컬럼, engagement_events와 동형). 쓰기는 service_role만(AD-3).
ALTER TABLE public.project_card_progress ENABLE ROW LEVEL SECURITY;

CREATE POLICY "project_card_progress_select" ON public.project_card_progress FOR SELECT
    USING (user_id = auth.uid());

-- updated_at 자동 갱신 (기존 public.set_updated_at() 재사용)
CREATE TRIGGER trg_project_card_progress_updated_at
    BEFORE UPDATE ON public.project_card_progress
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
