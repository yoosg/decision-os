"""Learning Path 트리거/파이프라인 단위 테스트 (Story 4.1).

HTTP 엔드포인트 테스트는 라우터 경계에서 `get_supabase`를 모킹한다(기존 `test_reviews_trigger.py` 등과 동일 관례).
파이프라인 단계 테스트는 `_execute_learning_path_pipeline(..., client, llm)`에 client/llm을 직접 주입한다
(모듈 내부를 patch하지 않음) — `pipeline.reviewer.review_signal()` 테스트와 동일한 관례이며, LLM Provider 인터페이스만
모킹한다(AD-11). `run_learning_path_from_pending`(BackgroundTask 진입점) 자체는 `get_supabase`/`OpenAIProvider` 생성
후 위 함수로 위임만 하므로 별도 테스트에서 위임 여부만 검증한다.
"""
import time
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

TEST_SECRET = "test-super-secret-key-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_OTHER_USER_ID = "660e8400-e29b-41d4-a716-446655440001"
TEST_SIGNAL_ID = "sig-abc-123"
TEST_PROJECT_ID = "proj-xyz-456"
TEST_REVIEW_ID = "rev-def-789"
TEST_DECISION_ID = "dec-ghi-012"
TEST_LEARNING_PATH_ID = "lp-jkl-345"


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

def test_trigger_learning_path_requires_auth():
    """Authorization 헤더 없이 호출 시 401 반환."""
    from main import app
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/learning-paths/trigger",
            json={"decision_id": TEST_DECISION_ID},
        )
    assert response.status_code == 401


def test_trigger_learning_path_returns_202_with_learning_path_id(monkeypatch):
    """정상 호출 → 202 + learning_path_id 반환 + BackgroundTask 등록. (6.1)"""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = MagicMock()
    learning_paths_call_count = [0]

    def table_side_effect(table_name):
        c = _chain()
        if table_name == "decisions":
            c.execute.return_value.data = [
                {"id": TEST_DECISION_ID, "review_id": TEST_REVIEW_ID, "choice": "learn_now"}
            ]
        elif table_name == "reviews":
            c.execute.return_value.data = [
                {"id": TEST_REVIEW_ID, "project_id": TEST_PROJECT_ID, "signal_id": TEST_SIGNAL_ID}
            ]
        elif table_name == "projects":
            c.execute.return_value.data = [{"id": TEST_PROJECT_ID}]
        elif table_name == "learning_paths":
            learning_paths_call_count[0] += 1
            if learning_paths_call_count[0] == 1:
                # 멱등성 체크: 기존 learning_path 없음
                c.execute.return_value.data = []
            else:
                # INSERT 응답
                c.execute.return_value.data = [{"id": TEST_LEARNING_PATH_ID}]
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.learning_paths.get_supabase", return_value=mock_client), \
         patch("routers.learning_paths.run_learning_path_from_pending") as mock_run:
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/learning-paths/trigger",
                json={"decision_id": TEST_DECISION_ID},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 202
    body = response.json()
    assert body["data"]["learning_path_id"] == TEST_LEARNING_PATH_ID
    assert body["data"]["status"] == "pending"
    assert body["error"] is None
    mock_run.assert_called_once_with(TEST_LEARNING_PATH_ID, TEST_DECISION_ID, TEST_SIGNAL_ID)


def test_trigger_learning_path_returns_422_when_choice_not_learn_now(monkeypatch):
    """choice != 'learn_now'인 decision_id → 422. (6.2)"""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = MagicMock()

    def table_side_effect(table_name):
        c = _chain()
        if table_name == "decisions":
            c.execute.return_value.data = [
                {"id": TEST_DECISION_ID, "review_id": TEST_REVIEW_ID, "choice": "queue"}
            ]
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.learning_paths.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/learning-paths/trigger",
                json={"decision_id": TEST_DECISION_ID},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 422


def test_trigger_learning_path_returns_404_for_other_users_decision(monkeypatch):
    """다른 사용자의 decision_id → 404. (6.3)"""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = MagicMock()

    def table_side_effect(table_name):
        c = _chain()
        if table_name == "decisions":
            c.execute.return_value.data = [
                {"id": TEST_DECISION_ID, "review_id": TEST_REVIEW_ID, "choice": "learn_now"}
            ]
        elif table_name == "reviews":
            c.execute.return_value.data = [
                {"id": TEST_REVIEW_ID, "project_id": TEST_PROJECT_ID, "signal_id": TEST_SIGNAL_ID}
            ]
        elif table_name == "projects":
            # 다른 사용자 소유 → user_id 필터에 매칭되는 project 없음
            c.execute.return_value.data = []
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.learning_paths.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/learning-paths/trigger",
                json={"decision_id": TEST_DECISION_ID},
                headers={"Authorization": f"Bearer {_make_token(TEST_OTHER_USER_ID)}"},
            )

    assert response.status_code == 404


def test_trigger_learning_path_idempotent_returns_existing(monkeypatch):
    """pending/processing 상태 learning_path 이미 존재 시 새 INSERT 없이 기존 learning_path_id 반환. (6.4)"""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = MagicMock()

    def table_side_effect(table_name):
        c = _chain()
        if table_name == "decisions":
            c.execute.return_value.data = [
                {"id": TEST_DECISION_ID, "review_id": TEST_REVIEW_ID, "choice": "learn_now"}
            ]
        elif table_name == "reviews":
            c.execute.return_value.data = [
                {"id": TEST_REVIEW_ID, "project_id": TEST_PROJECT_ID, "signal_id": TEST_SIGNAL_ID}
            ]
        elif table_name == "projects":
            c.execute.return_value.data = [{"id": TEST_PROJECT_ID}]
        elif table_name == "learning_paths":
            c.execute.return_value.data = [{"id": "existing-lp-id", "status": "processing"}]
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.learning_paths.get_supabase", return_value=mock_client), \
         patch("routers.learning_paths.run_learning_path_from_pending") as mock_run:
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/learning-paths/trigger",
                json={"decision_id": TEST_DECISION_ID},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 202
    body = response.json()
    assert body["data"]["learning_path_id"] == "existing-lp-id"
    assert body["data"]["status"] == "processing"
    mock_run.assert_not_called()


def test_trigger_learning_path_insert_race_falls_back_to_existing(monkeypatch):
    """존재 확인 통과 후 INSERT가 유니크 제약(23505) 위반 시, 재조회한 기존 row를 반환한다 (TOCTOU 레이스)."""
    from postgrest.exceptions import APIError

    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = MagicMock()
    learning_paths_call_count = [0]

    def table_side_effect(table_name):
        c = _chain()
        if table_name == "decisions":
            c.execute.return_value.data = [
                {"id": TEST_DECISION_ID, "review_id": TEST_REVIEW_ID, "choice": "learn_now"}
            ]
        elif table_name == "reviews":
            c.execute.return_value.data = [
                {"id": TEST_REVIEW_ID, "project_id": TEST_PROJECT_ID, "signal_id": TEST_SIGNAL_ID}
            ]
        elif table_name == "projects":
            c.execute.return_value.data = [{"id": TEST_PROJECT_ID}]
        elif table_name == "learning_paths":
            def execute_side_effect():
                learning_paths_call_count[0] += 1
                result = MagicMock()
                if learning_paths_call_count[0] == 1:
                    result.data = []  # 최초 존재 확인: 없음
                elif learning_paths_call_count[0] == 2:
                    raise APIError({"message": "duplicate key", "code": "23505"})  # 동시 요청이 먼저 INSERT
                else:
                    result.data = [{"id": "concurrent-lp-id", "status": "pending"}]  # 재조회
                return result
            c.execute.side_effect = execute_side_effect
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.learning_paths.get_supabase", return_value=mock_client), \
         patch("routers.learning_paths.run_learning_path_from_pending") as mock_run:
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/learning-paths/trigger",
                json={"decision_id": TEST_DECISION_ID},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 202
    body = response.json()
    assert body["data"]["learning_path_id"] == "concurrent-lp-id"
    assert body["data"]["status"] == "pending"
    mock_run.assert_not_called()


def test_trigger_learning_path_returns_404_for_nonexistent_decision(monkeypatch):
    """존재하지 않는 decision_id → 404. (6.5)"""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = MagicMock()

    def table_side_effect(table_name):
        c = _chain()
        if table_name == "decisions":
            c.execute.return_value.data = []
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.learning_paths.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/learning-paths/trigger",
                json={"decision_id": "nonexistent-id"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 404


# ─── _execute_learning_path_pipeline 단위 테스트 (pipeline.coach) ───────────────

def test_run_learning_path_from_pending_delegates_to_pipeline(monkeypatch):
    """BackgroundTask 진입점은 client/llm을 생성해 파이프라인 함수로 위임한다."""
    from pipeline import coach

    calls = []
    monkeypatch.setattr(coach, "get_supabase", lambda: "the-client")
    monkeypatch.setattr(
        coach, "get_llm_provider", lambda: "the-llm"
    )
    monkeypatch.setattr(
        coach,
        "_execute_learning_path_pipeline",
        lambda *args: calls.append(args),
    )

    coach.run_learning_path_from_pending(TEST_LEARNING_PATH_ID, TEST_DECISION_ID, TEST_SIGNAL_ID)

    assert len(calls) == 1
    lp_id, dec_id, sig_id, client, llm = calls[0]
    assert (lp_id, dec_id, sig_id) == (TEST_LEARNING_PATH_ID, TEST_DECISION_ID, TEST_SIGNAL_ID)
    assert client == "the-client"
    assert llm == "the-llm"


def test_execute_learning_path_pipeline_completes():
    """정상 실행 시 learning_paths 테이블에 completed 상태 + resources 업데이트."""
    from tests.mocks import MockLLMProvider

    mock_client = MagicMock()
    learning_paths_update_statuses: list[str] = []
    learning_paths_update_data: list[dict] = []

    def table_side_effect(table_name):
        c = _chain()
        if table_name == "signals":
            c.execute.return_value.data = [{
                "id": TEST_SIGNAL_ID,
                "technology_name": "LangGraph",
                "summary": "요약",
            }]
        elif table_name == "signal_sources":
            c.execute.return_value.data = []
        elif table_name == "decisions":
            c.execute.return_value.data = [{"review_id": TEST_REVIEW_ID}]
        elif table_name == "reviews":
            c.execute.return_value.data = [{"project_id": TEST_PROJECT_ID}]
        elif table_name == "projects":
            c.execute.return_value.data = [{"user_id": TEST_USER_ID}]
        elif table_name == "user_profiles":
            c.execute.return_value.data = [{
                "role": "backend",
                "tech_stack": ["Python"],
                "project_goal": "ai_side_project",
                "experience_level": "intermediate",
            }]
        elif table_name == "learning_paths":
            def update_side_effect(data):
                learning_paths_update_data.append(data)
                if "status" in data:
                    learning_paths_update_statuses.append(data["status"])
                return c
            c.update.side_effect = update_side_effect
        return c

    mock_client.table.side_effect = table_side_effect

    from pipeline.coach import _execute_learning_path_pipeline
    _execute_learning_path_pipeline(
        TEST_LEARNING_PATH_ID, TEST_DECISION_ID, TEST_SIGNAL_ID, mock_client, MockLLMProvider()
    )

    assert "processing" in learning_paths_update_statuses
    assert "completed" in learning_paths_update_statuses
    completed_update = next(d for d in learning_paths_update_data if d.get("status") == "completed")
    assert len(completed_update["resources"]) == 5


def test_execute_learning_path_pipeline_sets_failed_on_error():
    """LLM 오류 발생 시 learning_paths 테이블에 failed 상태 업데이트."""
    from tests.mocks import MockLLMProvider

    mock_client = MagicMock()
    learning_paths_update_statuses: list[str] = []

    def table_side_effect(table_name):
        c = _chain()
        if table_name == "signals":
            c.execute.return_value.data = [{
                "id": TEST_SIGNAL_ID,
                "technology_name": "LangGraph",
                "summary": "요약",
            }]
        elif table_name == "signal_sources":
            c.execute.return_value.data = []
        elif table_name == "decisions":
            c.execute.return_value.data = [{"review_id": TEST_REVIEW_ID}]
        elif table_name == "reviews":
            c.execute.return_value.data = [{"project_id": TEST_PROJECT_ID}]
        elif table_name == "projects":
            c.execute.return_value.data = [{"user_id": TEST_USER_ID}]
        elif table_name == "user_profiles":
            c.execute.return_value.data = []
        elif table_name == "learning_paths":
            def update_side_effect(data):
                if "status" in data:
                    learning_paths_update_statuses.append(data["status"])
                return c
            c.update.side_effect = update_side_effect
        return c

    mock_client.table.side_effect = table_side_effect

    from pipeline.coach import _execute_learning_path_pipeline
    _execute_learning_path_pipeline(
        TEST_LEARNING_PATH_ID, TEST_DECISION_ID, TEST_SIGNAL_ID,
        mock_client, MockLLMProvider(raise_error=True),
    )

    assert "failed" in learning_paths_update_statuses
