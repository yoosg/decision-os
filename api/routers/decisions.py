from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from core.schemas import APIResponse
from core.supabase import get_supabase
from middleware.auth import get_current_user

router = APIRouter(prefix="/decisions", tags=["decisions"])


class DecisionRequest(BaseModel):
    review_id: str
    choice: Literal["learn_now", "queue", "ignore"]
    queue_timing: Literal["today", "this_week", "later"] | None = None
    memo: str | None = None

    @field_validator("memo", mode="before")
    @classmethod
    def blank_memo_to_none(cls, v: object) -> object:
        if isinstance(v, str) and not v.strip():
            return None
        return v


@router.post("", status_code=201, response_model=APIResponse)
def create_decision(
    body: DecisionRequest,
    user_id: Annotated[str, Depends(get_current_user)],
) -> APIResponse:
    # P14: queue_timing은 queue choice 전용
    if body.queue_timing is not None and body.choice != "queue":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="queue_timing is only valid when choice is 'queue'",
        )
    # 1.4: queue 선택 시 queue_timing 필수
    if body.choice == "queue" and body.queue_timing is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="queue_timing is required when choice is 'queue'",
        )

    client = get_supabase()

    # 1.3: review_id → project_id → user_id 검증
    review_rows = (
        client.table("reviews")
        .select("id, project_id")
        .eq("id", body.review_id)
        .execute()
        .data
    )
    if not review_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    # 1.5: 멱등성 — 이미 decision 존재 시 기존 decision_id 반환
    existing = (
        client.table("decisions")
        .select("id")
        .eq("review_id", body.review_id)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        return APIResponse(data={"decision_id": existing[0]["id"]})

    # 1.6: INSERT (P4: race condition 완화 — concurrent INSERT 시 재조회로 멱등성 보장)
    try:
        insert_result = (
            client.table("decisions")
            .insert({
                "review_id": body.review_id,
                "choice": body.choice,
                "queue_timing": body.queue_timing,
                "memo": body.memo,
            })
            .execute()
        )
    except Exception as exc:  # P1: 예외 컨텍스트 보존 (bare except → exc)
        # 동시 요청으로 INSERT 실패 시 기존 decision 반환
        retry = (
            client.table("decisions")
            .select("id")
            .eq("review_id", body.review_id)
            .limit(1)
            .execute()
            .data
        )
        if retry:
            return APIResponse(data={"decision_id": retry[0]["id"]})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create decision",
        ) from exc  # P1: 원본 예외를 cause로 연결하여 traceback 보존

    if not insert_result.data:
        # P12: RLS 정책 차단 또는 DB 제약 위반 (exception 없이 empty data 반환)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Decision creation was denied",
        )
    decision_id = insert_result.data[0]["id"]

    # 1.7: 201 반환
    return APIResponse(data={"decision_id": decision_id})


class DecisionUpdateRequest(BaseModel):
    queue_timing: Literal["today", "this_week", "later"]


@router.patch("/{decision_id}", response_model=APIResponse)
def update_decision(
    decision_id: str,
    body: DecisionUpdateRequest,
    user_id: Annotated[str, Depends(get_current_user)],
) -> APIResponse:
    client = get_supabase()

    # 1.3.1: decision_id → review_id, choice 조회
    decision_rows = (
        client.table("decisions")
        .select("id, review_id, choice")
        .eq("id", decision_id)
        .execute()
        .data
    )
    if not decision_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")

    review_id = decision_rows[0]["review_id"]
    choice = decision_rows[0]["choice"]

    # 1.3.2: review_id → project_id 조회
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

    # 1.3.3: project_id + user_id 소유권 확인
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

    # 1.3.4: 소유권 확인 이후에만 choice 검증
    if choice != "queue":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="queue_timing can only be updated for queue decisions",
        )

    # 1.4: queue_timing 갱신 — trg_decisions_updated_at 트리거가 updated_at 자동 갱신
    update_result = (
        client.table("decisions")
        .update({"queue_timing": body.queue_timing})
        .eq("id", decision_id)
        .execute()
    )

    if not update_result.data:
        # 1.5: service_role은 RLS를 우회하므로 실무에서는 거의 발생하지 않지만 컨벤션 일치를 위해 유지
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Decision update was denied",
        )

    # 1.6
    return APIResponse(data={"decision_id": decision_id, "queue_timing": body.queue_timing})
