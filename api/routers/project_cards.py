"""project_card_progress 엔드포인트 — 입문자 카드 진도/결과 저장."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from core.schemas import APIResponse
from core.supabase import get_supabase
from middleware.auth import get_current_user

router = APIRouter(prefix="/project-cards", tags=["project-cards"])


class ProgressRequest(BaseModel):
    milestones_checked: list[int] = []
    checklist_checked: list[int] = []
    result: Literal["success", "stuck", "dropped"] | None = None


def _load_owned_card(client, review_id: str, user_id: str) -> dict:
    """review_id → 소유권·카드타입 검증 후 review row 반환. 실패 시 404."""
    review_rows = (
        client.table("reviews")
        .select("id, project_id, review_type, result")
        .eq("id", review_id)
        .execute()
        .data
    )
    if not review_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    review = review_rows[0]

    if review.get("review_type") != "project_card":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    project_rows = (
        client.table("projects")
        .select("id")
        .eq("id", review["project_id"])
        .eq("user_id", user_id)
        .execute()
        .data
    )
    if not project_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    return review


def _card_lengths(review: dict) -> tuple[int, int]:
    """카드 payload의 milestones·success_checklist 길이."""
    payload = ((review.get("result") or {}).get("payload")) or {}
    milestones = payload.get("milestones") or []
    checklist = payload.get("success_checklist") or []
    return len(milestones), len(checklist)


def _row_to_data(row: dict | None) -> dict:
    if not row:
        return {"milestones_checked": [], "checklist_checked": [], "result": None}
    return {
        "milestones_checked": row.get("milestones_checked") or [],
        "checklist_checked": row.get("checklist_checked") or [],
        "result": row.get("result"),
    }


@router.get("/{review_id}/progress", response_model=APIResponse)
def get_progress(
    review_id: str,
    user_id: Annotated[str, Depends(get_current_user)],
) -> APIResponse:
    client = get_supabase()
    _load_owned_card(client, review_id, user_id)

    rows = (
        client.table("project_card_progress")
        .select("milestones_checked, checklist_checked, result")
        .eq("review_id", review_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )
    return APIResponse(data=_row_to_data(rows[0] if rows else None))


@router.put("/{review_id}/progress", response_model=APIResponse)
def put_progress(
    review_id: str,
    body: ProgressRequest,
    user_id: Annotated[str, Depends(get_current_user)],
) -> APIResponse:
    client = get_supabase()
    review = _load_owned_card(client, review_id, user_id)

    n_milestones, n_checklist = _card_lengths(review)

    def _validate(indices: list[int], length: int, field: str) -> None:
        for i in indices:
            if i < 0 or i >= length:
                if length == 0:
                    detail = f"{field} index {i} out of range (field is empty, no valid indices)"
                else:
                    detail = f"{field} index {i} out of range (0..{length - 1})"
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=detail,
                )

    _validate(body.milestones_checked, n_milestones, "milestones_checked")
    _validate(body.checklist_checked, n_checklist, "checklist_checked")

    # dedup + 정렬(안정적 저장)
    milestones = sorted(set(body.milestones_checked))
    checklist = sorted(set(body.checklist_checked))

    values = {
        "milestones_checked": milestones,
        "checklist_checked": checklist,
        "result": body.result,
    }

    # UNIQUE(review_id, user_id) 기준 단일 upsert — select→insert/update의 TOCTOU 레이스 제거
    # (동시 PUT이 둘 다 INSERT 시도 → UNIQUE 위반 500 나던 문제).
    written = (
        client.table("project_card_progress")
        .upsert(
            {**values, "review_id": review_id, "user_id": user_id},
            on_conflict="review_id,user_id",
        )
        .execute()
        .data
    )

    row = written[0] if written else {**values}
    return APIResponse(data=_row_to_data(row))
