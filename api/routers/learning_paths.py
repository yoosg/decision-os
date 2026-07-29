from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from postgrest.exceptions import APIError
from pydantic import BaseModel

from core.schemas import APIResponse
from core.supabase import get_supabase
from middleware.auth import get_current_user
from pipeline.coach import run_learning_path_from_pending

router = APIRouter(prefix="/learning-paths", tags=["learning-paths"])


class TriggerLearningPathRequest(BaseModel):
    decision_id: str


@router.post("/trigger", status_code=202, response_model=APIResponse)
def trigger_learning_path(
    body: TriggerLearningPathRequest,
    background_tasks: BackgroundTasks,
    user_id: Annotated[str, Depends(get_current_user)],
) -> APIResponse:
    client = get_supabase()

    # decision_id로 decisions 조회 → review_id, choice 검증
    decision_rows = (
        client.table("decisions")
        .select("id, review_id, choice")
        .eq("id", body.decision_id)
        .execute()
        .data
    )
    if not decision_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")

    decision = decision_rows[0]
    if decision["choice"] != "learn_now":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="decision.choice must be 'learn_now'",
        )

    # review_id → project_id, signal_id 조회
    review_rows = (
        client.table("reviews")
        .select("id, project_id, signal_id")
        .eq("id", decision["review_id"])
        .execute()
        .data
    )
    if not review_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    review = review_rows[0]
    project_id = review["project_id"]
    signal_id = review["signal_id"]

    # project_id → user_id 권한 검증
    project_rows = (
        client.table("projects")
        .select("id")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
        .data
    )
    if not project_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")

    # 멱등성: 이미 pending/processing 중인 learning_path 있으면 재사용
    existing = (
        client.table("learning_paths")
        .select("id, status")
        .eq("decision_id", body.decision_id)
        .in_("status", ["pending", "processing"])
        .limit(1)
        .execute()
        .data
    )
    if existing:
        return APIResponse(data={"learning_path_id": existing[0]["id"], "status": existing[0]["status"]})

    # pending INSERT — decision_id당 pending/processing 1개 제약(uq_learning_paths_active_decision)으로
    # 동시 요청 시 존재 확인과 INSERT 사이의 레이스를 DB 레벨에서 최종적으로 차단한다.
    try:
        insert_result = (
            client.table("learning_paths")
            .insert({
                "decision_id": body.decision_id,
                "signal_id": signal_id,
                "status": "pending",
            })
            .execute()
        )
    except APIError as e:
        if e.code == "23505":
            concurrent = (
                client.table("learning_paths")
                .select("id, status")
                .eq("decision_id", body.decision_id)
                .in_("status", ["pending", "processing"])
                .limit(1)
                .execute()
                .data
            )
            if concurrent:
                return APIResponse(data={"learning_path_id": concurrent[0]["id"], "status": concurrent[0]["status"]})
        raise
    if not insert_result.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create learning path")
    learning_path_id = insert_result.data[0]["id"]

    # BackgroundTask 등록
    background_tasks.add_task(run_learning_path_from_pending, learning_path_id, body.decision_id, signal_id)

    # 202 반환
    return APIResponse(data={"learning_path_id": learning_path_id, "status": "pending"})
