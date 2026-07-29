from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from core.schemas import APIResponse
from core.supabase import get_supabase
from middleware.auth import get_current_user
from pipeline.reviewer import run_review_from_pending

router = APIRouter(prefix="/reviews", tags=["reviews"])


class TriggerReviewRequest(BaseModel):
    signal_id: str


@router.post("/trigger", status_code=202, response_model=APIResponse)
def trigger_review(
    body: TriggerReviewRequest,
    background_tasks: BackgroundTasks,
    user_id: Annotated[str, Depends(get_current_user)],
) -> APIResponse:
    client = get_supabase()

    # 1.3: user_id로 ai_research 프로젝트 조회
    project_rows = (
        client.table("projects")
        .select("id")
        .eq("user_id", user_id)
        .eq("playbook_type", "ai_research")
        .execute()
        .data
    )
    if not project_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    project_id = project_rows[0]["id"]

    # signal 존재 확인
    signal_rows = (
        client.table("signals")
        .select("id")
        .eq("id", body.signal_id)
        .execute()
        .data
    )
    if not signal_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found")

    # 1.4: 멱등성 — 이미 pending/processing 중인 Review 있으면 재사용
    existing = (
        client.table("reviews")
        .select("id, status")
        .eq("signal_id", body.signal_id)
        .eq("project_id", project_id)
        .in_("status", ["pending", "processing"])
        .limit(1)
        .execute()
        .data
    )
    if existing:
        review_id = existing[0]["id"]
        return APIResponse(data={"review_id": review_id, "status": existing[0]["status"]})

    # 1.5: pending INSERT
    insert_result = (
        client.table("reviews")
        .insert({
            "project_id": project_id,
            "signal_id": body.signal_id,
            "playbook_type": "ai_research",
            "review_type": "research",
            "status": "pending",
        })
        .execute()
    )
    if not insert_result.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create review")
    review_id = insert_result.data[0]["id"]

    # 1.6: BackgroundTask 등록
    background_tasks.add_task(run_review_from_pending, review_id, body.signal_id, project_id)

    # 1.7: 202 반환
    return APIResponse(data={"review_id": review_id, "status": "pending"})
