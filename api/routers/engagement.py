"""Story 6.5 — POST /api/v1/engagement: 웹 클라이언트발 engagement 이벤트 수집.

수집 대상은 open·read_through·impression뿐이다. decision은 서버 정본(decisions 라우터가 로깅)이라
클라이언트발을 금지한다(Pydantic Literal에서 제외 → 잘못된 타입은 422). variant도 클라이언트가 못
정한다(impression variant 정본은 recommender/서버, D2/D5) — 요청 스키마에 variant 필드 없음.

AD-13(API 계약): Bearer JWT(get_current_user 재사용)·/api/v1/·{data,error} 봉투.
AD-5(safe degradation): 각 이벤트는 best-effort insert — 존재하지 않는 signal_id는 FK 위반으로
조용히 스킵(accepted 카운트에서 제외)되고, 어떤 실패도 UX를 막지 않는다.
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.schemas import APIResponse
from core.supabase import get_supabase
from middleware.auth import get_current_user
from pipeline.logger import pipeline_log

router = APIRouter(prefix="/engagement", tags=["engagement"])


class EngagementEvent(BaseModel):
    signal_id: str
    # 클라이언트발 허용 타입 — decision 제외(서버 정본). 잘못된 타입은 Pydantic이 422로 거절.
    event_type: Literal["impression", "open", "read_through"]
    daily_brief_id: str | None = None
    metadata: dict | None = None


class EngagementBatch(BaseModel):
    events: list[EngagementEvent]


@router.post("", response_model=APIResponse)
def collect_engagement(
    body: EngagementBatch,
    user_id: Annotated[str, Depends(get_current_user)],
) -> APIResponse:
    """배치 engagement 이벤트를 best-effort로 수집. accepted 카운트 반환(개별 실패는 전체를 막지 않음)."""
    client = get_supabase()

    accepted = 0
    for event in body.events:
        row = {
            "user_id": user_id,
            "signal_id": event.signal_id,
            "event_type": event.event_type,
        }
        if event.daily_brief_id:
            row["daily_brief_id"] = event.daily_brief_id
        if event.metadata is not None:
            row["metadata"] = event.metadata
        try:
            client.table("engagement_events").insert(row).execute()
            accepted += 1
        except Exception as e:  # noqa: BLE001 — best-effort: 개별 실패 스킵, UX 무영향(AD-5)
            # 예: 존재하지 않는 signal_id → FK 위반. accepted 증가 없이 경고만(AD-12).
            pipeline_log(
                stage="engagement",
                brief_date="",
                user_count=0,
                level="warning",
                event="engagement_log_failed",
                event_type=event.event_type,
                signal_id=event.signal_id,
                error=str(e)[:200],
            )

    return APIResponse(data={"accepted": accepted})
