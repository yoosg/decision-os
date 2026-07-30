"""decisions 엔드포인트 단위 테스트 (Story 3.3)."""
import time
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

TEST_SECRET = "test-super-secret-key-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_OTHER_USER_ID = "660e8400-e29b-41d4-a716-446655440001"
TEST_REVIEW_ID = "rev-abc-111"
TEST_PROJECT_ID = "proj-xyz-222"
TEST_DECISION_ID = "dec-ghi-333"
TEST_SIGNAL_ID = "sig-jkl-444"


def _make_token(user_id: str = TEST_USER_ID) -> str:
    payload = {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")


def _chain() -> MagicMock:
    c = MagicMock()
    for attr in ("select", "insert", "update", "eq", "in_", "limit", "order"):
        getattr(c, attr).return_value = c
    return c


def _base_mock(decisions_first_call_data: list, decisions_insert_data: list | None = None) -> MagicMock:
    """P14: 메서드 기반 mock — SELECT/INSERT를 호출 순서가 아닌 메서드로 구분."""
    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        c = MagicMock()
        if table_name == "reviews":
            ch = _chain()
            ch.execute.return_value.data = [{"id": TEST_REVIEW_ID, "project_id": TEST_PROJECT_ID}]
            c.select.return_value = ch
        elif table_name == "projects":
            ch = _chain()
            ch.execute.return_value.data = [{"id": TEST_PROJECT_ID}]
            c.select.return_value = ch
        elif table_name == "decisions":
            select_ch = _chain()
            select_ch.execute.return_value.data = decisions_first_call_data
            insert_ch = _chain()
            insert_ch.execute.return_value.data = decisions_insert_data or [{"id": TEST_DECISION_ID}]
            c.select.return_value = select_ch
            c.insert.return_value = insert_ch
        return c

    mock_client.table.side_effect = table_side_effect
    return mock_client


# ─── 3.1: learn_now decision 저장 성공 ─────────────────────────────────────

def test_create_learn_now_decision_returns_201(monkeypatch):
    """learn_now decision 저장 성공 → 201 + decision_id 반환."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = _base_mock(decisions_first_call_data=[], decisions_insert_data=[{"id": TEST_DECISION_ID}])

    with patch("routers.decisions.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/decisions",
                json={"review_id": TEST_REVIEW_ID, "choice": "learn_now"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["decision_id"] == TEST_DECISION_ID  # P19
    assert body["error"] is None  # P19


# ─── 3.2: queue decision + queue_timing 저장 성공 ───────────────────────────

def test_create_queue_decision_with_timing_returns_201(monkeypatch):
    """queue + queue_timing 저장 성공."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = _base_mock(decisions_first_call_data=[], decisions_insert_data=[{"id": TEST_DECISION_ID}])

    with patch("routers.decisions.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/decisions",
                json={"review_id": TEST_REVIEW_ID, "choice": "queue", "queue_timing": "this_week"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["decision_id"] == TEST_DECISION_ID  # P19
    assert body["error"] is None  # P19


# ─── 3.3: ignore decision 저장 성공 ────────────────────────────────────────

def test_create_ignore_decision_returns_201(monkeypatch):
    """ignore decision 저장 성공."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = _base_mock(decisions_first_call_data=[], decisions_insert_data=[{"id": TEST_DECISION_ID}])

    with patch("routers.decisions.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/decisions",
                json={"review_id": TEST_REVIEW_ID, "choice": "ignore"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["decision_id"] == TEST_DECISION_ID  # P19
    assert body["error"] is None  # P19


# ─── 3.4: queue decision 시 queue_timing 없으면 422 ─────────────────────────

def test_queue_decision_without_timing_returns_422(monkeypatch):
    """queue 선택 + queue_timing 없음 → 422."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = MagicMock()
    mock_client.table.return_value = _chain()

    with patch("routers.decisions.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/decisions",
                json={"review_id": TEST_REVIEW_ID, "choice": "queue"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 422


# ─── 3.5: 다른 사용자의 review_id로 요청 시 404 ─────────────────────────────

def test_decision_for_other_users_review_returns_404(monkeypatch):
    """다른 사용자 소유의 review → 404."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        c = _chain()
        if table_name == "reviews":
            c.execute.return_value.data = [{"id": TEST_REVIEW_ID, "project_id": "other-project"}]
        elif table_name == "projects":
            c.execute.return_value.data = []
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.decisions.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/decisions",
                json={"review_id": TEST_REVIEW_ID, "choice": "learn_now"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 404


# ─── 3.6: 동일 review_id 중복 요청 시 기존 decision_id 반환 ──────────────────

def test_duplicate_decision_returns_existing_decision_id(monkeypatch):
    """동일 review_id에 대한 중복 요청 시 기존 decision_id 반환 (멱등성). P20: INSERT 미호출 검증."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    existing_decision_id = "existing-decision-id"
    insert_called = False
    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        nonlocal insert_called
        c = _chain()
        if table_name == "reviews":
            c.execute.return_value.data = [{"id": TEST_REVIEW_ID, "project_id": TEST_PROJECT_ID}]
        elif table_name == "projects":
            c.execute.return_value.data = [{"id": TEST_PROJECT_ID}]
        elif table_name == "decisions":
            # 멱등성 SELECT: 동일 choice(learn_now)의 기존 decision 존재 → early return
            c.execute.return_value.data = [{"id": existing_decision_id, "choice": "learn_now"}]
            # P20: INSERT가 실제로 호출되는지 추적
            original_insert = c.insert
            def tracked_insert(data: dict) -> MagicMock:
                nonlocal insert_called
                insert_called = True
                return original_insert(data)
            c.insert = tracked_insert
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.decisions.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/decisions",
                json={"review_id": TEST_REVIEW_ID, "choice": "learn_now"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["decision_id"] == existing_decision_id
    assert not insert_called, "멱등성 경로에서 INSERT가 호출되면 안 됨"  # P20


# ─── Task 2: PATCH /api/v1/decisions/:id ───────────────────────────────────

# 2.1: 성공 — choice='queue'인 decision → queue_timing 업데이트 → 200
def test_patch_queue_decision_updates_timing_returns_200(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        c = MagicMock()
        if table_name == "decisions":
            select_ch = _chain()
            select_ch.execute.return_value.data = [
                {"id": TEST_DECISION_ID, "review_id": TEST_REVIEW_ID, "choice": "queue"}
            ]
            update_ch = _chain()
            update_ch.execute.return_value.data = [{"id": TEST_DECISION_ID}]
            c.select.return_value = select_ch
            c.update.return_value = update_ch
        elif table_name == "reviews":
            ch = _chain()
            ch.execute.return_value.data = [{"id": TEST_REVIEW_ID, "project_id": TEST_PROJECT_ID}]
            c.select.return_value = ch
        elif table_name == "projects":
            ch = _chain()
            ch.execute.return_value.data = [{"id": TEST_PROJECT_ID}]
            c.select.return_value = ch
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.decisions.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/decisions/{TEST_DECISION_ID}",
                json={"queue_timing": "later"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["decision_id"] == TEST_DECISION_ID
    assert body["data"]["queue_timing"] == "later"
    assert body["error"] is None


# 2.2: choice='learn_now' decision에 PATCH 시도 → 422
def test_patch_non_queue_decision_returns_422(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        c = MagicMock()
        if table_name == "decisions":
            select_ch = _chain()
            select_ch.execute.return_value.data = [
                {"id": TEST_DECISION_ID, "review_id": TEST_REVIEW_ID, "choice": "learn_now"}
            ]
            c.select.return_value = select_ch
        elif table_name == "reviews":
            ch = _chain()
            ch.execute.return_value.data = [{"id": TEST_REVIEW_ID, "project_id": TEST_PROJECT_ID}]
            c.select.return_value = ch
        elif table_name == "projects":
            ch = _chain()
            ch.execute.return_value.data = [{"id": TEST_PROJECT_ID}]
            c.select.return_value = ch
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.decisions.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/decisions/{TEST_DECISION_ID}",
                json={"queue_timing": "later"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 422


# 2.3: 존재하지 않는 decision_id → 404
def test_patch_nonexistent_decision_returns_404(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        c = MagicMock()
        if table_name == "decisions":
            select_ch = _chain()
            select_ch.execute.return_value.data = []
            c.select.return_value = select_ch
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.decisions.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            response = client.patch(
                "/api/v1/decisions/nonexistent-id",
                json={"queue_timing": "later"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 404


# 2.4: 다른 사용자 소유 decision(project.user_id 불일치) → 404
def test_patch_other_users_decision_returns_404(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        c = MagicMock()
        if table_name == "decisions":
            select_ch = _chain()
            select_ch.execute.return_value.data = [
                {"id": TEST_DECISION_ID, "review_id": TEST_REVIEW_ID, "choice": "queue"}
            ]
            c.select.return_value = select_ch
        elif table_name == "reviews":
            ch = _chain()
            ch.execute.return_value.data = [{"id": TEST_REVIEW_ID, "project_id": "other-project"}]
            c.select.return_value = ch
        elif table_name == "projects":
            ch = _chain()
            ch.execute.return_value.data = []  # 소유권 없음
            c.select.return_value = ch
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.decisions.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/decisions/{TEST_DECISION_ID}",
                json={"queue_timing": "later"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 404


# 2.5: 잘못된 queue_timing 값 → 422 (Pydantic Literal 검증)
def test_patch_invalid_queue_timing_value_returns_422(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = MagicMock()
    mock_client.table.return_value = _chain()

    with patch("routers.decisions.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/decisions/{TEST_DECISION_ID}",
                json={"queue_timing": "tomorrow"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# Story 6.5 — decision engagement 이벤트 서버 로깅 (신규 insert 시 1회, 멱등 0회, 실패 무영향)
# ══════════════════════════════════════════════════════════════════════════════

def _mock_with_signal(decisions_first_call_data, decisions_insert_data=None):
    """reviews SELECT가 signal_id를 포함하는 decisions 라우터용 Mock(6.5 engagement 로깅 경로)."""
    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        c = MagicMock()
        if table_name == "reviews":
            ch = _chain()
            ch.execute.return_value.data = [
                {"id": TEST_REVIEW_ID, "project_id": TEST_PROJECT_ID, "signal_id": TEST_SIGNAL_ID}
            ]
            c.select.return_value = ch
        elif table_name == "projects":
            ch = _chain()
            ch.execute.return_value.data = [{"id": TEST_PROJECT_ID}]
            c.select.return_value = ch
        elif table_name == "decisions":
            select_ch = _chain()
            select_ch.execute.return_value.data = decisions_first_call_data
            insert_ch = _chain()
            insert_ch.execute.return_value.data = decisions_insert_data or [{"id": TEST_DECISION_ID}]
            c.select.return_value = select_ch
            c.insert.return_value = insert_ch
        return c

    mock_client.table.side_effect = table_side_effect
    return mock_client


def test_new_decision_logs_engagement_event_once(monkeypatch):
    """신규 decision insert 성공 → decision engagement 1회 로깅(signal_id·choice 포함)."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = _mock_with_signal(decisions_first_call_data=[])
    with patch("routers.decisions.get_supabase", return_value=mock_client), \
         patch("routers.decisions.log_engagement") as mock_log:
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/decisions",
                json={"review_id": TEST_REVIEW_ID, "choice": "learn_now"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 201
    mock_log.assert_called_once()
    args, kwargs = mock_log.call_args
    # log_engagement(client, user_id, signal_id, "decision", metadata=...)
    assert args[2] == TEST_SIGNAL_ID
    assert args[3] == "decision"
    assert kwargs["metadata"]["choice"] == "learn_now"


def test_idempotent_decision_does_not_log_engagement(monkeypatch):
    """멱등 재요청(기존 decision 반환) → engagement 로깅 0회(중복 카운트 방지)."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = _mock_with_signal(decisions_first_call_data=[{"id": "existing-decision", "choice": "learn_now"}])
    with patch("routers.decisions.get_supabase", return_value=mock_client), \
         patch("routers.decisions.log_engagement") as mock_log:
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/decisions",
                json={"review_id": TEST_REVIEW_ID, "choice": "learn_now"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 201  # 라우터 데코레이터가 201 고정(멱등도 기존 decision 반환)
    mock_log.assert_not_called()


def test_create_decision_transitions_queue_to_learn_now(monkeypatch):
    """보관함(queue) 결정을 learn_now로 재요청 시 choice 전환(UPDATE)·queue_timing 초기화. INSERT 미호출.

    버그: queue로 담은 항목은 나중에 '학습하기'를 눌러도 learn_now로 전환되지 않아
    학습경로(choice=learn_now 필요)가 영영 생성되지 않았다.
    """
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    update_payload: dict = {}
    insert_called = False
    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        nonlocal insert_called
        c = MagicMock()
        if table_name == "reviews":
            ch = _chain()
            ch.execute.return_value.data = [
                {"id": TEST_REVIEW_ID, "project_id": TEST_PROJECT_ID, "signal_id": TEST_SIGNAL_ID}
            ]
            c.select.return_value = ch
        elif table_name == "projects":
            ch = _chain()
            ch.execute.return_value.data = [{"id": TEST_PROJECT_ID}]
            c.select.return_value = ch
        elif table_name == "decisions":
            select_ch = _chain()
            select_ch.execute.return_value.data = [
                {"id": TEST_DECISION_ID, "choice": "queue", "queue_timing": "this_week"}
            ]
            c.select.return_value = select_ch

            def tracked_update(data: dict) -> MagicMock:
                update_payload.update(data)
                uch = _chain()
                uch.execute.return_value.data = [{"id": TEST_DECISION_ID}]
                return uch

            c.update.side_effect = tracked_update

            def tracked_insert(data: dict) -> MagicMock:
                nonlocal insert_called
                insert_called = True
                ich = _chain()
                ich.execute.return_value.data = [{"id": TEST_DECISION_ID}]
                return ich

            c.insert.side_effect = tracked_insert
        return c

    mock_client.table.side_effect = table_side_effect

    with patch("routers.decisions.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/decisions",
                json={"review_id": TEST_REVIEW_ID, "choice": "learn_now"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 201
    assert response.json()["data"]["decision_id"] == TEST_DECISION_ID
    assert update_payload.get("choice") == "learn_now", "queue→learn_now 전환 UPDATE 필요"
    assert update_payload.get("queue_timing") is None, "learn_now 전환 시 queue_timing 초기화"
    assert not insert_called, "전환은 UPDATE로 처리 — INSERT 미호출"


def test_decision_engagement_log_failure_does_not_block_201(monkeypatch):
    """engagement 로깅이 예외를 던져도 decision 응답(201)은 막히지 않는다(AD-5)."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_client = _mock_with_signal(decisions_first_call_data=[])
    with patch("routers.decisions.get_supabase", return_value=mock_client), \
         patch("routers.decisions.log_engagement", side_effect=RuntimeError("log boom")):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/decisions",
                json={"review_id": TEST_REVIEW_ID, "choice": "learn_now"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 201
