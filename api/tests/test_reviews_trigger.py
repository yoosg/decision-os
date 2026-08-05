"""Reviews on-demand trigger 단위/통합 테스트 (Story 3.2).

Supabase Mock으로 실행 가능 — 환경변수 불필요.
"""
import time
from unittest.mock import MagicMock, call, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

TEST_SECRET = "test-super-secret-key-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_SIGNAL_ID = "sig-abc-123"
TEST_PROJECT_ID = "proj-xyz-456"
TEST_REVIEW_ID = "rev-def-789"


def _make_token(user_id: str = TEST_USER_ID) -> str:
    payload = {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")


def _chain() -> MagicMock:
    """자기 자신을 반환하는 체인 가능 MagicMock."""
    c = MagicMock()
    for attr in ("select", "insert", "update", "eq", "in_", "limit", "order"):
        getattr(c, attr).return_value = c
    return c


# ─── HTTP 엔드포인트 테스트 ────────────────────────────────────────────────────

def test_trigger_review_requires_auth():
    """Authorization 헤더 없이 호출 시 401 반환."""
    from main import app
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reviews/trigger",
            json={"signal_id": TEST_SIGNAL_ID},
        )
    assert response.status_code == 401


def test_trigger_review_returns_202_with_review_id(monkeypatch):
    """유효한 JWT + 신규 Review → 202 + review_id 반환 + BackgroundTask 등록."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = MagicMock()
    reviews_call_count = [0]

    def table_side_effect(table_name):
        c = _chain()
        if table_name == "projects":
            c.execute.return_value.data = [{"id": TEST_PROJECT_ID}]
        elif table_name == "reviews":
            reviews_call_count[0] += 1
            if reviews_call_count[0] == 1:
                # 멱등성 체크: 기존 review 없음
                c.execute.return_value.data = []
            else:
                # INSERT 응답
                c.execute.return_value.data = [{"id": TEST_REVIEW_ID}]
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.reviews.get_supabase", return_value=mock_client), \
         patch("routers.reviews.run_review_from_pending") as mock_run:
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/reviews/trigger",
                json={"signal_id": TEST_SIGNAL_ID},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 202
    body = response.json()
    assert body["data"]["review_id"] == TEST_REVIEW_ID
    assert body["data"]["status"] == "pending"
    assert body["error"] is None
    mock_run.assert_called_once_with(TEST_REVIEW_ID, TEST_SIGNAL_ID, TEST_PROJECT_ID)


def test_trigger_review_returns_404_when_no_project(monkeypatch):
    """ai_research 프로젝트 없을 때 404 반환."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = MagicMock()

    def table_side_effect(table_name):
        c = _chain()
        if table_name == "projects":
            c.execute.return_value.data = []
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.reviews.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/reviews/trigger",
                json={"signal_id": TEST_SIGNAL_ID},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 404


def test_trigger_review_idempotent_returns_existing(monkeypatch):
    """pending 상태 Review 이미 존재 시 새 INSERT 없이 기존 review_id 반환."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = MagicMock()

    def table_side_effect(table_name):
        c = _chain()
        if table_name == "projects":
            c.execute.return_value.data = [{"id": TEST_PROJECT_ID}]
        elif table_name == "reviews":
            c.execute.return_value.data = [{"id": "existing-review-id", "status": "pending"}]
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.reviews.get_supabase", return_value=mock_client), \
         patch("routers.reviews.run_review_from_pending") as mock_run:
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/reviews/trigger",
                json={"signal_id": TEST_SIGNAL_ID},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 202
    body = response.json()
    assert body["data"]["review_id"] == "existing-review-id"
    assert body["data"]["status"] == "pending"
    mock_run.assert_not_called()


# ─── run_review_from_pending 단위 테스트 ─────────────────────────────────────

def test_run_review_from_pending_completes():
    """run_review_from_pending 정상 실행 시 reviews 테이블에 completed 상태 업데이트."""
    from tests.test_signal_builder_reviewer import MockLLMProvider

    mock_client = MagicMock()
    reviews_update_statuses: list[str] = []

    def table_side_effect(table_name):
        c = _chain()
        if table_name == "signals":
            c.execute.return_value.data = [{
                "id": TEST_SIGNAL_ID,
                "technology_name": "TestTech",
                "title": "Test Title",
                "summary": "요약",
                "signal_date": "2026-07-25",
            }]
        elif table_name == "signal_sources":
            c.execute.return_value.data = []
        elif table_name == "projects":
            c.execute.return_value.data = [{"user_id": TEST_USER_ID}]
        elif table_name == "user_profiles":
            c.execute.return_value.data = [{
                "role": "backend",
                "tech_stack": ["Python"],
                "interests": ["AI"],
                "experience_level": "intermediate",
            }]
        elif table_name == "reviews":
            # update 호출 시 status 기록
            def update_side_effect(data):
                if "status" in data:
                    reviews_update_statuses.append(data["status"])
                return c
            c.update.side_effect = update_side_effect
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("pipeline.reviewer.get_supabase", return_value=mock_client), \
         patch("pipeline.reviewer.get_llm_provider", return_value=MockLLMProvider()):
        from pipeline.reviewer import run_review_from_pending
        run_review_from_pending(TEST_REVIEW_ID, TEST_SIGNAL_ID, TEST_PROJECT_ID)

    assert "completed" in reviews_update_statuses


def test_run_review_from_pending_sets_failed_on_error():
    """LLM 오류 발생 시 reviews 테이블에 failed 상태 업데이트."""
    from tests.test_signal_builder_reviewer import MockLLMProvider

    mock_client = MagicMock()
    reviews_update_statuses: list[str] = []

    def table_side_effect(table_name):
        c = _chain()
        if table_name == "signals":
            c.execute.return_value.data = [{
                "id": TEST_SIGNAL_ID,
                "technology_name": "TestTech",
                "title": "Test Title",
                "summary": "요약",
                "signal_date": "2026-07-25",
            }]
        elif table_name == "signal_sources":
            c.execute.return_value.data = []
        elif table_name == "projects":
            c.execute.return_value.data = [{"user_id": TEST_USER_ID}]
        elif table_name == "user_profiles":
            c.execute.return_value.data = []
        elif table_name == "reviews":
            def update_side_effect(data):
                if "status" in data:
                    reviews_update_statuses.append(data["status"])
                return c
            c.update.side_effect = update_side_effect
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("pipeline.reviewer.get_supabase", return_value=mock_client), \
         patch("pipeline.reviewer.get_llm_provider", return_value=MockLLMProvider(raise_error=True)):
        from pipeline.reviewer import run_review_from_pending
        run_review_from_pending(TEST_REVIEW_ID, TEST_SIGNAL_ID, TEST_PROJECT_ID)

    assert "failed" in reviews_update_statuses
