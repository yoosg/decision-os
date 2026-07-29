from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from core.schemas import APIResponse
from core.supabase import get_supabase
from middleware.auth import get_current_user
from pipeline.memory_manager import run_memory_manager_from_outcome

router = APIRouter(prefix="/outcomes", tags=["outcomes"])


class OutcomeRequest(BaseModel):
    decision_id: str
    status: Literal["completed", "applied", "dropped", "not_useful"]
    useful: bool | None = None
    actual_learning_time_min: int | None = None
    applied_project_note: str | None = Field(default=None, max_length=500)
    memo: str | None = Field(default=None, max_length=2000)

    @field_validator("memo", "applied_project_note", mode="before")
    @classmethod
    def blank_memo_to_none(cls, v: object) -> object:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("actual_learning_time_min")
    @classmethod
    def reject_out_of_range_learning_time(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("actual_learning_time_min must not be negative")
        if v is not None and v > 100_000:
            raise ValueError("actual_learning_time_min must not exceed 100000")
        return v


@router.post("", status_code=201, response_model=APIResponse)
def create_outcome(
    body: OutcomeRequest,
    user_id: Annotated[str, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
) -> APIResponse:
    # 1.4: DB chk_useful_required와 동일 규칙을 API 레이어에서 선제 검증
    if body.status in ("completed", "applied") and body.useful is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="useful is required when status is 'completed' or 'applied'",
        )

    client = get_supabase()

    # 1.5: decision_id → decisions.review_id → reviews.project_id → projects 소유권 검증
    decision_rows = (
        client.table("decisions")
        .select("id, review_id")
        .eq("id", body.decision_id)
        .execute()
        .data
    )
    if not decision_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")

    review_id = decision_rows[0]["review_id"]

    review_rows = (
        client.table("reviews")
        .select("id, project_id")
        .eq("id", review_id)
        .execute()
        .data
    )
    if not review_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")

    project_id = review_rows[0]["project_id"]

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

    # 1.6: 멱등성 — 이미 outcome 존재 시 기존 outcome_id 반환
    existing = (
        client.table("outcomes")
        .select("id")
        .eq("decision_id", body.decision_id)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        return APIResponse(data={"outcome_id": existing[0]["id"]})

    # 1.7: INSERT + race-condition 폴백
    try:
        insert_result = (
            client.table("outcomes")
            .insert({
                "decision_id": body.decision_id,
                "status": body.status,
                "useful": body.useful,
                "actual_learning_time_min": body.actual_learning_time_min,
                "applied_project_note": body.applied_project_note,
                "memo": body.memo,
            })
            .execute()
        )
    except Exception as exc:
        retry = (
            client.table("outcomes")
            .select("id")
            .eq("decision_id", body.decision_id)
            .limit(1)
            .execute()
            .data
        )
        if retry:
            return APIResponse(data={"outcome_id": retry[0]["id"]})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create outcome",
        ) from exc

    if not insert_result.data:
        # 1.8: RLS 또는 DB 제약 거부
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Outcome creation was denied",
        )
    outcome_id = insert_result.data[0]["id"]

    # 4.3: 신규 INSERT 성공 경로에서만 Memory 추출 BackgroundTask 트리거
    background_tasks.add_task(run_memory_manager_from_outcome, outcome_id, body.decision_id)

    # 1.9: 201 반환
    return APIResponse(data={"outcome_id": outcome_id})
