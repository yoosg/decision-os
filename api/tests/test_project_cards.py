"""project_card_progress 엔드포인트 단위 테스트."""
import time
from unittest.mock import MagicMock, patch

import jwt as pyjwt
from fastapi.testclient import TestClient

TEST_SECRET = "test-super-secret-key-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_REVIEW_ID = "rev-abc-111"
TEST_PROJECT_ID = "proj-xyz-222"
TEST_PROGRESS_ID = "prog-def-555"


def _make_token(user_id: str = TEST_USER_ID) -> str:
    payload = {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")


def _chain() -> MagicMock:
    c = MagicMock()
    for attr in ("select", "insert", "update", "eq", "in_", "limit", "order"):
        getattr(c, attr).return_value = c
    return c


def _base_mock(
    *,
    review_row: dict | None,
    progress_first: list,
    progress_write: list | None = None,
) -> MagicMock:
    """메서드 기반 mock — reviews 소유권 조회 + project_card_progress select/write."""
    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        c = MagicMock()
        if table_name == "reviews":
            ch = _chain()
            ch.execute.return_value.data = [review_row] if review_row else []
            c.select.return_value = ch
        elif table_name == "projects":
            ch = _chain()
            ch.execute.return_value.data = [{"id": TEST_PROJECT_ID}]
            c.select.return_value = ch
        elif table_name == "project_card_progress":
            select_ch = _chain()
            select_ch.execute.return_value.data = progress_first
            write_ch = _chain()
            write_ch.execute.return_value.data = progress_write or [{"id": TEST_PROGRESS_ID}]
            c.select.return_value = select_ch
            c.insert.return_value = write_ch
            c.update.return_value = write_ch
        return c

    mock_client.table.side_effect = table_side_effect
    return mock_client


_CARD_REVIEW = {
    "id": TEST_REVIEW_ID,
    "project_id": TEST_PROJECT_ID,
    "review_type": "project_card",
    "result": {"payload": {"milestones": [{}, {}, {}], "success_checklist": ["a", "b"]}},
}


def _client(mock_client):
    with patch("routers.project_cards.get_supabase", return_value=mock_client):
        from main import app
        return TestClient(app)


def test_get_empty_progress_returns_defaults(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)
    mock_client = _base_mock(review_row=_CARD_REVIEW, progress_first=[])
    with patch("routers.project_cards.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            res = client.get(
                f"/api/v1/project-cards/{TEST_REVIEW_ID}/progress",
                headers={"Authorization": f"Bearer {_make_token()}"},
            )
    assert res.status_code == 200
    assert res.json()["data"] == {"milestones_checked": [], "checklist_checked": [], "result": None}


def test_put_inserts_new_progress(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)
    written = [{"id": TEST_PROGRESS_ID, "milestones_checked": [0, 2],
               "checklist_checked": [1], "result": "success"}]
    mock_client = _base_mock(review_row=_CARD_REVIEW, progress_first=[], progress_write=written)
    with patch("routers.project_cards.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            res = client.put(
                f"/api/v1/project-cards/{TEST_REVIEW_ID}/progress",
                headers={"Authorization": f"Bearer {_make_token()}"},
                json={"milestones_checked": [0, 2], "checklist_checked": [1], "result": "success"},
            )
    assert res.status_code == 200
    assert res.json()["data"]["result"] == "success"
    assert res.json()["data"]["milestones_checked"] == [0, 2]


def test_put_out_of_range_index_returns_422(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)
    mock_client = _base_mock(review_row=_CARD_REVIEW, progress_first=[])
    with patch("routers.project_cards.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            res = client.put(
                f"/api/v1/project-cards/{TEST_REVIEW_ID}/progress",
                headers={"Authorization": f"Bearer {_make_token()}"},
                json={"milestones_checked": [3], "checklist_checked": [], "result": None},
            )
    assert res.status_code == 422


def test_put_bad_result_enum_returns_422(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)
    mock_client = _base_mock(review_row=_CARD_REVIEW, progress_first=[])
    with patch("routers.project_cards.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            res = client.put(
                f"/api/v1/project-cards/{TEST_REVIEW_ID}/progress",
                headers={"Authorization": f"Bearer {_make_token()}"},
                json={"milestones_checked": [], "checklist_checked": [], "result": "give_up"},
            )
    assert res.status_code == 422


def test_unowned_review_returns_404(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)
    # projects 소유권 조회가 빈 결과 → 404
    mock_client = _base_mock(review_row=_CARD_REVIEW, progress_first=[])

    def table_side_effect(table_name: str) -> MagicMock:
        c = MagicMock()
        if table_name == "reviews":
            ch = _chain(); ch.execute.return_value.data = [_CARD_REVIEW]; c.select.return_value = ch
        elif table_name == "projects":
            ch = _chain(); ch.execute.return_value.data = []; c.select.return_value = ch  # 소유권 없음
        return c
    mock_client.table.side_effect = table_side_effect

    with patch("routers.project_cards.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            res = client.get(
                f"/api/v1/project-cards/{TEST_REVIEW_ID}/progress",
                headers={"Authorization": f"Bearer {_make_token()}"},
            )
    assert res.status_code == 404


def test_non_card_review_returns_404(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)
    research_review = {**_CARD_REVIEW, "review_type": "research"}
    mock_client = _base_mock(review_row=research_review, progress_first=[])
    with patch("routers.project_cards.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            res = client.get(
                f"/api/v1/project-cards/{TEST_REVIEW_ID}/progress",
                headers={"Authorization": f"Bearer {_make_token()}"},
            )
    assert res.status_code == 404


def test_put_updates_existing_progress(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)
    written = [{"id": TEST_PROGRESS_ID, "milestones_checked": [1],
               "checklist_checked": [0], "result": "stuck"}]
    # progress_first 비어있지 않으므로 UPDATE 브랜치 진입
    mock_client = _base_mock(
        review_row=_CARD_REVIEW,
        progress_first=[{"id": TEST_PROGRESS_ID}],
        progress_write=written,
    )
    with patch("routers.project_cards.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            res = client.put(
                f"/api/v1/project-cards/{TEST_REVIEW_ID}/progress",
                headers={"Authorization": f"Bearer {_make_token()}"},
                json={"milestones_checked": [1], "checklist_checked": [0], "result": "stuck"},
            )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["milestones_checked"] == [1]
    assert data["checklist_checked"] == [0]
    assert data["result"] == "stuck"
    # update()가 호출된 table mock을 확인 (insert가 아님)
    # _base_mock에서 project_card_progress table의 update().eq().execute() 체인이 wire됨
    table_calls = [c.args[0] for c in mock_client.table.call_args_list]
    assert "project_card_progress" in table_calls


def test_missing_auth_returns_401():
    mock_client = _base_mock(review_row=_CARD_REVIEW, progress_first=[])
    with patch("routers.project_cards.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            res = client.get(f"/api/v1/project-cards/{TEST_REVIEW_ID}/progress")
    assert res.status_code == 401
