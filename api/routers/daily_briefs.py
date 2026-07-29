from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from core.schemas import APIResponse
from middleware.auth import get_current_user
from pipeline.orchestrator import run_ondemand_brief

router = APIRouter(prefix="/daily-briefs", tags=["daily-briefs"])


@router.post("/trigger", status_code=202, response_model=APIResponse)
def trigger_daily_brief(
    background_tasks: BackgroundTasks,
    user_id: Annotated[str, Depends(get_current_user)],
) -> APIResponse:
    brief_date = datetime.now(timezone.utc).date().isoformat()
    background_tasks.add_task(run_ondemand_brief, user_id, brief_date)
    return APIResponse(data={"queued": True, "brief_date": brief_date})
