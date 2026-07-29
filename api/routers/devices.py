from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from core.schemas import APIResponse
from core.supabase import get_supabase
from middleware.auth import get_current_user

router = APIRouter(prefix="/devices", tags=["devices"])


class DeviceRegisterRequest(BaseModel):
    fcm_token: str
    platform: Literal["web", "ios", "android"]


@router.post("/register", response_model=APIResponse)
def register_device(
    body: DeviceRegisterRequest,
    user_id: Annotated[str, Depends(get_current_user)],
) -> APIResponse:
    """FCM 토큰 등록 (UPSERT). 타 사용자의 동일 토큰은 먼저 삭제해 소유권 이전."""
    client = get_supabase()
    # 다른 사용자가 동일 FCM 토큰을 보유한 경우 삭제 (기기 재사용 시 크로스유저 알림 방지)
    client.table("user_devices").delete().eq("fcm_token", body.fcm_token).neq(
        "user_id", user_id
    ).execute()
    result = (
        client.table("user_devices")
        .upsert(
            {
                "user_id": user_id,
                "fcm_token": body.fcm_token,
                "platform": body.platform,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="user_id,fcm_token",
        )
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register device",
        )
    device_id = result.data[0]["id"]
    return APIResponse(data={"device_id": device_id})
