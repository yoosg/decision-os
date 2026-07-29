"""outcomes 엔드포인트 단위 테스트 (Story 4.2)."""
import time
from unittest.mock import MagicMock, patch

import jwt as pyjwt
from fastapi.testclient import TestClient

TEST_SECRET = "test-super-secret-key-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_REVIEW_ID = "rev-abc-111"
TEST_PROJECT_ID = "proj-xyz-222"
TEST_DECISION_ID = "dec-ghi-333"
TEST_OUTCOME_ID = "out-jkl-444"


def _make_token(user_id: str = TEST_USER_ID) -> str:
    payload = {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")


def _chain() -> MagicMock:
    c = MagicMock()
    for attr in ("select", "insert", "update", "eq", "in_", "limit", "order"):
        getattr(c, attr).return_value = c
    return c


def _base_mock(outcomes_first_call_data: list, outcomes_insert_data: list | None = None) -> MagicMock:
    """P14 패턴: 메서드 기반 mock — SELECT/INSERT를 호출 순서가 아닌 메서드로 구분."""
    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        c = MagicMock()
        if table_name == "decisions":
            ch = _chain()
            ch.execute.return_value.data = [{"id": TEST_DECISION_ID, "review_id": TEST_REVIEW_ID}]
            c.select.return_value = ch
        elif table_name == "reviews":
            ch = _chain()
            ch.execute.return_value.data = [{"id": TEST_REVIEW_ID, "project_id": TEST_PROJECT_ID}]
            c.select.return_value = ch
        elif table_name == "projects":
            ch = _chain()
            ch.execute.return_value.data = [{"id": TEST_PROJECT_ID}]
            c.select.return_value = ch
        elif table_name == "outcomes":
            select_ch = _chain()
            select_ch.execute.return_value.data = outcomes_first_call_data
            insert_ch = _chain()
            insert_ch.execute.return_value.data = outcomes_insert_data or [{"id": TEST_OUTCOME_ID}]
            c.select.return_value = select_ch
            c.insert.return_value = insert_ch
        return c

    mock_client.table.side_effect = table_side_effect
    return mock_client


# ─── 3.2: completed + useful=true → 201 ─────────────────────────────────────

def test_completed_with_useful_returns_201(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = _base_mock(outcomes_first_call_data=[], outcomes_insert_data=[{"id": TEST_OUTCOME_ID}])

    with patch("routers.outcomes.get_supabase", return_value=mock_client), \
         patch("routers.outcomes.run_memory_manager_from_outcome") as mock_run:
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/outcomes",
                json={"decision_id": TEST_DECISION_ID, "status": "completed", "useful": True},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["outcome_id"] == TEST_OUTCOME_ID
    assert body["error"] is None
    mock_run.assert_called_once_with(TEST_OUTCOME_ID, TEST_DECISION_ID)


# ─── 3.3: applied + useful=true + applied_project_note → 201 ───────────────

def test_applied_with_project_note_returns_201(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = _base_mock(outcomes_first_call_data=[], outcomes_insert_data=[{"id": TEST_OUTCOME_ID}])

    with patch("routers.outcomes.get_supabase", return_value=mock_client), \
         patch("routers.outcomes.run_memory_manager_from_outcome"):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/outcomes",
                json={
                    "decision_id": TEST_DECISION_ID,
                    "status": "applied",
                    "useful": True,
                    "applied_project_note": "사내 대시보드 프로젝트에 적용",
                },
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["outcome_id"] == TEST_OUTCOME_ID


# ─── 3.4: dropped (useful 없음) → 201 ───────────────────────────────────────

def test_dropped_without_useful_returns_201(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = _base_mock(outcomes_first_call_data=[], outcomes_insert_data=[{"id": TEST_OUTCOME_ID}])

    with patch("routers.outcomes.get_supabase", return_value=mock_client), \
         patch("routers.outcomes.run_memory_manager_from_outcome"):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/outcomes",
                json={"decision_id": TEST_DECISION_ID, "status": "dropped"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["outcome_id"] == TEST_OUTCOME_ID


# ─── 3.5: not_useful (useful 없음) → 201 ────────────────────────────────────

def test_not_useful_without_useful_returns_201(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = _base_mock(outcomes_first_call_data=[], outcomes_insert_data=[{"id": TEST_OUTCOME_ID}])

    with patch("routers.outcomes.get_supabase", return_value=mock_client), \
         patch("routers.outcomes.run_memory_manager_from_outcome"):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/outcomes",
                json={"decision_id": TEST_DECISION_ID, "status": "not_useful"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["outcome_id"] == TEST_OUTCOME_ID


# ─── 3.6: completed + useful 없음 → 422 ─────────────────────────────────────

def test_completed_without_useful_returns_422(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = _base_mock(outcomes_first_call_data=[])

    with patch("routers.outcomes.get_supabase", return_value=mock_client), \
         patch("routers.outcomes.run_memory_manager_from_outcome"):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/outcomes",
                json={"decision_id": TEST_DECISION_ID, "status": "completed"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 422


# ─── 3.7: 다른 사용자 소유의 decision_id → 404 ───────────────────────────────

def test_outcome_for_other_users_decision_returns_404(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        c = _chain()
        if table_name == "decisions":
            c.execute.return_value.data = [{"id": TEST_DECISION_ID, "review_id": TEST_REVIEW_ID}]
        elif table_name == "reviews":
            c.execute.return_value.data = [{"id": TEST_REVIEW_ID, "project_id": "other-project"}]
        elif table_name == "projects":
            c.execute.return_value.data = []
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.outcomes.get_supabase", return_value=mock_client), \
         patch("routers.outcomes.run_memory_manager_from_outcome"):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/outcomes",
                json={"decision_id": TEST_DECISION_ID, "status": "completed", "useful": True},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 404


# ─── 3.8: 동일 decision_id 중복 요청 → 기존 outcome_id 반환 + INSERT 미호출 ───

def test_duplicate_decision_id_returns_existing_outcome_id(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    existing_outcome_id = "existing-outcome-id"
    insert_called = False
    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        nonlocal insert_called
        c = _chain()
        if table_name == "decisions":
            c.execute.return_value.data = [{"id": TEST_DECISION_ID, "review_id": TEST_REVIEW_ID}]
        elif table_name == "reviews":
            c.execute.return_value.data = [{"id": TEST_REVIEW_ID, "project_id": TEST_PROJECT_ID}]
        elif table_name == "projects":
            c.execute.return_value.data = [{"id": TEST_PROJECT_ID}]
        elif table_name == "outcomes":
            c.execute.return_value.data = [{"id": existing_outcome_id}]
            original_insert = c.insert

            def tracked_insert(data: dict) -> MagicMock:
                nonlocal insert_called
                insert_called = True
                return original_insert(data)

            c.insert = tracked_insert
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.outcomes.get_supabase", return_value=mock_client), \
         patch("routers.outcomes.run_memory_manager_from_outcome") as mock_run:
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/outcomes",
                json={"decision_id": TEST_DECISION_ID, "status": "completed", "useful": True},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["outcome_id"] == existing_outcome_id
    assert not insert_called, "멱등성 경로에서 INSERT가 호출되면 안 됨"
    mock_run.assert_not_called()


# ─── Review: actual_learning_time_min 음수 → 422 ────────────────────────────

def test_negative_learning_time_returns_422(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = _base_mock(outcomes_first_call_data=[])

    with patch("routers.outcomes.get_supabase", return_value=mock_client), \
         patch("routers.outcomes.run_memory_manager_from_outcome"):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/outcomes",
                json={
                    "decision_id": TEST_DECISION_ID,
                    "status": "dropped",
                    "actual_learning_time_min": -5,
                },
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 422


# ─── Review: blank memo/applied_project_note → None으로 변환되어 INSERT ────

def test_blank_memo_and_note_coerced_to_none(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    captured: dict = {}
    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        c = _chain()
        if table_name == "decisions":
            c.execute.return_value.data = [{"id": TEST_DECISION_ID, "review_id": TEST_REVIEW_ID}]
        elif table_name == "reviews":
            c.execute.return_value.data = [{"id": TEST_REVIEW_ID, "project_id": TEST_PROJECT_ID}]
        elif table_name == "projects":
            c.execute.return_value.data = [{"id": TEST_PROJECT_ID}]
        elif table_name == "outcomes":
            select_ch = _chain()
            select_ch.execute.return_value.data = []
            c.select.return_value = select_ch

            def tracked_insert(data: dict) -> MagicMock:
                captured.update(data)
                insert_ch = _chain()
                insert_ch.execute.return_value.data = [{"id": TEST_OUTCOME_ID}]
                return insert_ch

            c.insert = tracked_insert
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.outcomes.get_supabase", return_value=mock_client), \
         patch("routers.outcomes.run_memory_manager_from_outcome"):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/outcomes",
                json={
                    "decision_id": TEST_DECISION_ID,
                    "status": "completed",
                    "useful": True,
                    "memo": "   ",
                    "applied_project_note": "",
                },
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 201
    assert captured["memo"] is None
    assert captured["applied_project_note"] is None


# ─── Review: INSERT 예외 발생 시 재조회로 기존 outcome_id 반환 (race fallback) ─

def test_insert_exception_falls_back_to_existing_outcome(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    existing_outcome_id = "race-existing-outcome-id"
    call_count = {"select": 0}
    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        c = _chain()
        if table_name == "decisions":
            c.execute.return_value.data = [{"id": TEST_DECISION_ID, "review_id": TEST_REVIEW_ID}]
        elif table_name == "reviews":
            c.execute.return_value.data = [{"id": TEST_REVIEW_ID, "project_id": TEST_PROJECT_ID}]
        elif table_name == "projects":
            c.execute.return_value.data = [{"id": TEST_PROJECT_ID}]
        elif table_name == "outcomes":
            def select_side_effect(*_args: object, **_kwargs: object) -> MagicMock:
                call_count["select"] += 1
                sel = _chain()
                if call_count["select"] == 1:
                    sel.execute.return_value.data = []
                else:
                    sel.execute.return_value.data = [{"id": existing_outcome_id}]
                return sel

            c.select.side_effect = select_side_effect

            def raising_insert(_data: dict) -> MagicMock:
                raise RuntimeError("simulated concurrent insert conflict")

            c.insert = raising_insert
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.outcomes.get_supabase", return_value=mock_client), \
         patch("routers.outcomes.run_memory_manager_from_outcome") as mock_run:
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/outcomes",
                json={"decision_id": TEST_DECISION_ID, "status": "completed", "useful": True},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["outcome_id"] == existing_outcome_id
    mock_run.assert_not_called()
