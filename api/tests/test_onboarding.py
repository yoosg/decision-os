"""온보딩 완료 시 첫 Daily Brief 자동 생성 트리거 테스트.

신규 유저가 온보딩을 마치면 그 즉시 개인화 브리핑이 생성되도록,
complete_onboarding이 run_ondemand_brief를 BackgroundTask로 등록하는지 검증한다.
Supabase Mock으로 실행 — 환경변수 불필요.
"""
import time
from unittest.mock import MagicMock, patch

import jwt as pyjwt
from fastapi.testclient import TestClient

TEST_SECRET = "test-super-secret-key-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"

_VALID_BODY = {
    "role": "backend",
    "experience_level": "intermediate",
    "tech_stack": ["python"],
    "project_goal": "ai_side_project",
    "interests": ["llm"],
    "daily_learning_time_min": 30,
}


def _make_token(user_id: str = TEST_USER_ID) -> str:
    payload = {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")


def _mock_supabase() -> MagicMock:
    """프로필 업데이트 성공 + 기존 ai_research project 존재(idempotent 경로) Mock."""
    mock = MagicMock()
    chain = mock.table.return_value
    for attr in ("select", "update", "insert", "eq"):
        getattr(chain, attr).return_value = chain
    chain.execute.return_value.data = [{"id": TEST_USER_ID}]
    return mock


def test_complete_onboarding_triggers_first_brief(monkeypatch):
    """온보딩 완료(200) 시 run_ondemand_brief가 해당 user_id로 BackgroundTask 등록."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    with patch("routers.onboarding.get_supabase", return_value=_mock_supabase()), \
         patch("routers.onboarding.run_ondemand_brief") as mock_run:
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/onboarding/complete",
                json=_VALID_BODY,
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 200
    assert response.json()["data"]["onboarding_completed"] is True
    mock_run.assert_called_once()
    assert mock_run.call_args.args[0] == TEST_USER_ID


def test_complete_onboarding_requires_auth():
    """인증 없이 호출 시 401."""
    from main import app
    with TestClient(app) as client:
        response = client.post("/api/v1/onboarding/complete", json=_VALID_BODY)
    assert response.status_code == 401
