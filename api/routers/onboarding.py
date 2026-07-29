from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.schemas import APIResponse
from core.supabase import get_supabase
from middleware.auth import get_current_user

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class OnboardingCompleteRequest(BaseModel):
    role: Literal['frontend', 'backend', 'ai_engineer', 'pm', 'designer', 'student', 'other']
    experience_level: Literal['beginner', 'intermediate', 'advanced']
    tech_stack: list[str]
    project_goal: Literal['ai_side_project', 'rag_service', 'agent_architecture', 'work_automation', 'ai_adoption', 'other']
    interests: list[str]
    daily_learning_time_min: int = Field(..., gt=0)


@router.post("/complete", response_model=APIResponse)
def complete_onboarding(
    body: OnboardingCompleteRequest,
    user_id: Annotated[str, Depends(get_current_user)],
) -> APIResponse:
    """온보딩 완료 — user_profiles 업데이트 + ai_research project 생성(idempotent)."""
    client = get_supabase()

    update_result = client.table("user_profiles").update({
        "role": body.role,
        "experience_level": body.experience_level,
        "tech_stack": body.tech_stack,
        "project_goal": body.project_goal,
        "interests": body.interests,
        "daily_learning_time_min": body.daily_learning_time_min,
        "onboarding_completed": True,
    }).eq("id", user_id).execute()
    if not update_result.data:
        raise HTTPException(status_code=404, detail="User profile not found")

    existing = (
        client.table("projects")
        .select("id")
        .eq("user_id", user_id)
        .eq("playbook_type", "ai_research")
        .execute()
    )
    if existing.data:
        project_id = existing.data[0]["id"]
    else:
        try:
            result = client.table("projects").insert({
                "user_id": user_id,
                "playbook_type": "ai_research",
                "name": "내 AI 학습",
            }).execute()
            if not result.data:
                raise HTTPException(status_code=500, detail="Project creation failed")
            project_id = result.data[0]["id"]
        except HTTPException:
            raise
        except Exception:
            fallback = (
                client.table("projects")
                .select("id")
                .eq("user_id", user_id)
                .eq("playbook_type", "ai_research")
                .execute()
            )
            if not fallback.data:
                raise HTTPException(status_code=500, detail="Project creation failed")
            project_id = fallback.data[0]["id"]

    return APIResponse(data={
        "user_id": user_id,
        "project_id": project_id,
        "onboarding_completed": True,
    })
