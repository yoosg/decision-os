import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.config import settings
from core.schemas import APIResponse, ErrorDetail

router = APIRouter()


@router.get("/health", response_model=APIResponse)
async def health_check():
    if settings.supabase_url and settings.supabase_service_role_key:
        try:
            from core.supabase import get_supabase
            client = get_supabase()
            await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: client.table("user_profiles").select("id").limit(1).execute()
                ),
                timeout=3.0,
            )
        except Exception:
            return JSONResponse(
                status_code=503,
                content=APIResponse(
                    error=ErrorDetail(code="DB_UNAVAILABLE", message="Database connection failed")
                ).model_dump(),
            )
    return APIResponse(data={"status": "ok"})
