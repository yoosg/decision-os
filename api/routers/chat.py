from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from core.schemas import APIResponse
from core.supabase import get_supabase
from middleware.auth import get_current_user
from pipeline.llm.base import ChatContext, LLMProvider, LLMProviderError
from pipeline.llm.factory import get_llm_provider

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessageRequest(BaseModel):
    signal_id: str
    message: str = Field(..., max_length=2000)

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message must not be empty")
        return v


@lru_cache(maxsize=1)
def _cached_llm_provider() -> LLMProvider:
    return get_llm_provider()


@router.post("/messages", response_model=APIResponse)
def send_chat_message(
    body: ChatMessageRequest,
    user_id: Annotated[str, Depends(get_current_user)],
    llm: LLMProvider = Depends(_cached_llm_provider),
) -> APIResponse:
    client = get_supabase()

    try:
        # 시그널은 전역 공유(project_id 없음). 소유권은 "이 사용자의 프로젝트에 속한
        # 완료된 리뷰"의 존재로 검증한다(리뷰가 곧 사용자×시그널 컨텍스트).
        project_rows = (
            client.table("projects")
            .select("id")
            .eq("user_id", user_id)
            .execute()
            .data
        )
        project_ids = [p["id"] for p in project_rows]
        if not project_ids:
            raise HTTPException(status_code=404, detail="Signal not found")

        review_rows = (
            client.table("reviews")
            .select("result")
            .eq("signal_id", body.signal_id)
            .eq("status", "completed")
            .in_("project_id", project_ids)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if not review_rows:
            raise HTTPException(status_code=404, detail="Signal not found")

        review_payload = None
        result = review_rows[0].get("result")
        if isinstance(result, dict):
            review_payload = result.get("payload", result)

        user_rows = (
            client.table("user_profiles")
            .select("role, tech_stack")
            .eq("id", user_id)
            .execute()
            .data
        )
        user_data = user_rows[0] if user_rows else {}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        ) from e

    context = ChatContext(
        signal_id=body.signal_id,
        user_message=body.message,
        review_payload=review_payload,
        user_role=user_data.get("role"),
        user_tech_stack=user_data.get("tech_stack") or [],
    )

    try:
        response = llm.chat(context)
        return APIResponse(data={"reply": response.content})
    except LLMProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
