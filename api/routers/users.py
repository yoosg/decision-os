from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, field_validator

from core.schemas import APIResponse
from core.supabase import get_supabase
from middleware.auth import get_current_user
from pipeline.orchestrator import run_ondemand_brief

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/profile", response_model=APIResponse)
def get_profile(user_id: Annotated[str, Depends(get_current_user)]) -> APIResponse:
    client = get_supabase()
    result = client.table("user_profiles").select(
        "role, experience_level, tech_stack, project_goal, interests, daily_learning_time_min, onboarding_completed"
    ).eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return APIResponse(data=result.data[0])


class ProfileUpdateRequest(BaseModel):
    role: Literal['frontend', 'backend', 'ai_engineer', 'pm', 'designer', 'student', 'other'] | None = None
    experience_level: Literal['beginner', 'intermediate', 'advanced'] | None = None
    tech_stack: list[str] | None = None
    project_goal: Literal['ai_side_project', 'rag_service', 'agent_architecture', 'work_automation', 'ai_adoption', 'other'] | None = None
    interests: list[str] | None = None
    daily_learning_time_min: Literal[15, 30, 60] | None = None

    @field_validator('tech_stack', 'interests', mode='before')
    @classmethod
    def validate_string_list(cls, v: list | None) -> list | None:
        if v is None:
            return v
        if len(v) > 20:
            raise ValueError('최대 20개까지 선택 가능합니다')
        result = [s.strip() for s in v if isinstance(s, str) and s.strip()]
        if any(len(s) > 100 for s in result):
            raise ValueError('항목 길이는 100자 이하여야 합니다')
        return result


@router.patch("/profile", response_model=APIResponse)
def update_profile(
    body: ProfileUpdateRequest,
    background_tasks: BackgroundTasks,
    user_id: Annotated[str, Depends(get_current_user)],
) -> APIResponse:
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=422, detail="No fields to update")
    client = get_supabase()
    result = client.table("user_profiles").update(update_data).eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    background_tasks.add_task(run_ondemand_brief, user_id, datetime.now(timezone.utc).date().isoformat())
    return APIResponse(data=result.data[0])
