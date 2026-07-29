import ssl
from datetime import timedelta
from functools import lru_cache
from typing import Annotated

import certifi
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from core.config import settings

security = HTTPBearer()

# Supabase는 최신 프로젝트에서 비대칭 JWT 서명키(ES256/RS256)를 사용한다.
# 이 경우 HS256 공유 secret으로는 검증이 불가능하므로 JWKS(공개키)로 검증한다.
# 레거시(HS256 공유 secret) 프로젝트도 지원하기 위해 폴백을 유지한다.
_JWKS_URL = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    # PyJWKClient는 JWKS를 캐시한다(키 회전 시 재조회).
    # PyJWKClient는 내부적으로 urllib을 쓰는데, macOS python.org 배포판은 시스템 CA를
    # 참조하지 못해 SSL CERTIFICATE_VERIFY_FAILED가 난다. certifi CA 번들로 컨텍스트를 명시 주입.
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    return PyJWKClient(_JWKS_URL, ssl_context=ssl_context)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> str:
    """Supabase JWT 검증 → user_id(sub) 반환. 실패 시 401.

    - 비대칭 서명(ES256/RS256): JWKS 공개키로 검증(공유 secret 불필요).
    - 대칭 서명(HS256, 레거시): supabase_jwt_secret으로 검증.
    """
    token = credentials.credentials
    try:
        alg = jwt.get_unverified_header(token).get("alg", "")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        if alg.startswith(("ES", "RS", "PS", "Ed")):
            signing_key = _jwks_client().get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                audience="authenticated",
                leeway=timedelta(seconds=10),
            )
        else:
            if not settings.supabase_jwt_secret:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication not configured",
                )
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                leeway=timedelta(seconds=10),
            )
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWKClientError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
