"""devices 엔드포인트 테스트.

단위 테스트: Supabase 클라이언트 Mock으로 실행 가능.
통합 테스트: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY 환경변수 설정 시 실행.
"""
import time
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

TEST_SECRET = "test-super-secret-key-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_FCM_TOKEN = "fcm-test-token-abc123"
TEST_DEVICE_ID = "device-uuid-001"


def _make_token(user_id: str = TEST_USER_ID) -> str:
    payload = {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")


@pytest.fixture
def client_with_mocks(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_result = MagicMock()
    mock_result.data = [{"id": TEST_DEVICE_ID}]
    mock_table = MagicMock()
    mock_table.upsert.return_value.execute.return_value = mock_result
    mock_supabase = MagicMock()
    mock_supabase.table.return_value = mock_table

    with patch("routers.devices.get_supabase", return_value=mock_supabase):
        from main import app
        with TestClient(app) as c:
            yield c, mock_table


def test_register_device_success(client_with_mocks):
    client, mock_table = client_with_mocks
    token = _make_token()
    resp = client.post(
        "/api/v1/devices/register",
        json={"fcm_token": TEST_FCM_TOKEN, "platform": "ios"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["device_id"] == TEST_DEVICE_ID
    assert body["error"] is None

    mock_table.upsert.assert_called_once()
    call_args = mock_table.upsert.call_args
    upserted = call_args[0][0]
    assert upserted["user_id"] == TEST_USER_ID
    assert upserted["fcm_token"] == TEST_FCM_TOKEN
    assert upserted["platform"] == "ios"


def test_register_device_android(client_with_mocks):
    client, _ = client_with_mocks
    token = _make_token()
    resp = client.post(
        "/api/v1/devices/register",
        json={"fcm_token": "android-token", "platform": "android"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def test_register_device_invalid_platform(client_with_mocks):
    client, _ = client_with_mocks
    token = _make_token()
    resp = client.post(
        "/api/v1/devices/register",
        json={"fcm_token": TEST_FCM_TOKEN, "platform": "windows"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


def test_register_device_no_auth(client_with_mocks):
    client, _ = client_with_mocks
    resp = client.post(
        "/api/v1/devices/register",
        json={"fcm_token": TEST_FCM_TOKEN, "platform": "ios"},
    )
    assert resp.status_code == 401


def test_register_device_upsert_conflict(client_with_mocks):
    """동일 user_id+fcm_token 재등록 시 updated_at만 갱신 (UPSERT)."""
    client, mock_table = client_with_mocks
    token = _make_token()
    for _ in range(2):
        resp = client.post(
            "/api/v1/devices/register",
            json={"fcm_token": TEST_FCM_TOKEN, "platform": "ios"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    assert mock_table.upsert.call_count == 2
    for call in mock_table.upsert.call_args_list:
        assert call[1].get("on_conflict") == "user_id,fcm_token"
