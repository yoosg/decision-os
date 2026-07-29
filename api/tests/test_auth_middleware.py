"""FastAPI JWT 미들웨어 단위 테스트 — LLM 생성 Mock JWT 사용."""
import time

import jwt as pyjwt
import pytest
from fastapi import FastAPI
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from middleware.auth import get_current_user

TEST_SECRET = "test-super-secret-key-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"


def _make_token(user_id: str = TEST_USER_ID, expired: bool = False, secret: str = TEST_SECRET) -> str:
    exp = int(time.time()) + (-10 if expired else 3600)
    payload = {"sub": user_id, "aud": "authenticated", "exp": exp}
    return pyjwt.encode(payload, secret, algorithm="HS256")


# --- 단위 테스트: get_current_user dependency 직접 호출 ---

def _call_dependency(token: str, secret: str = TEST_SECRET) -> str:
    import importlib
    import unittest.mock as mock

    with mock.patch("middleware.auth.settings") as mock_settings:
        mock_settings.supabase_jwt_secret = secret
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        return get_current_user(creds)


def test_valid_jwt_returns_user_id():
    token = _make_token()
    result = _call_dependency(token)
    assert result == TEST_USER_ID


def test_expired_jwt_raises_401():
    from fastapi import HTTPException
    token = _make_token(expired=True)
    with pytest.raises(HTTPException) as exc_info:
        _call_dependency(token)
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


def test_invalid_signature_raises_401():
    from fastapi import HTTPException
    token = _make_token(secret="wrong-secret-key-that-is-32-bytes-lo")
    with pytest.raises(HTTPException) as exc_info:
        _call_dependency(token)
    assert exc_info.value.status_code == 401
    assert "invalid" in exc_info.value.detail.lower()


# --- 통합 테스트: FastAPI TestClient로 Authorization 헤더 없음 → 401 ---

from fastapi import Depends as _Depends  # noqa: E402

app = FastAPI()


@app.get("/protected")
def protected_route(user_id: str = _Depends(get_current_user)):
    return {"user_id": user_id}


@pytest.fixture
def client(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)
    with TestClient(app) as c:
        yield c


def test_no_auth_header_returns_401(client):
    resp = client.get("/protected")
    assert resp.status_code == 401


def test_valid_bearer_token_returns_200(client):
    token = _make_token()
    resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["user_id"] == TEST_USER_ID
