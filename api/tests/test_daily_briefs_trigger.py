"""Daily Brief on-demand trigger 단위/통합 테스트 (Story 2.5).

Supabase Mock으로 실행 가능 — 환경변수 불필요.
"""
import time
from unittest.mock import ANY, MagicMock, call, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from pipeline.orchestrator import run_ondemand_brief

TEST_SECRET = "test-super-secret-key-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_BRIEF_DATE = "2026-07-25"


def _make_token(user_id: str = TEST_USER_ID) -> str:
    payload = {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")


# ─── HTTP 엔드포인트 테스트 ────────────────────────────────────────────────────

def test_trigger_requires_auth():
    """Authorization 헤더 없이 호출 시 401 반환 (HTTPBearer 동작)."""
    from main import app
    with TestClient(app) as client:
        response = client.post("/api/v1/daily-briefs/trigger")
    assert response.status_code == 401


def test_trigger_returns_202(monkeypatch):
    """유효한 JWT로 호출 시 202 + queued:true 반환 + background task 등록 검증."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    with patch("routers.daily_briefs.run_ondemand_brief") as mock_run:
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/daily-briefs/trigger",
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 202
    body = response.json()
    assert body["data"]["queued"] is True
    assert "brief_date" in body["data"]
    assert body["error"] is None
    mock_run.assert_called_once_with(TEST_USER_ID, body["data"]["brief_date"])


def test_update_profile_triggers_ondemand_brief(monkeypatch):
    """PATCH /users/profile 성공 시 run_ondemand_brief가 BackgroundTask로 등록됨 (AC-2)."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_supabase = MagicMock()
    chain = mock_supabase.table.return_value
    chain.update.return_value = chain
    chain.eq.return_value = chain
    chain.execute.return_value.data = [{"id": TEST_USER_ID, "role": "backend"}]

    with patch("routers.users.get_supabase", return_value=mock_supabase), \
         patch("routers.users.run_ondemand_brief") as mock_run:
        from main import app
        with TestClient(app) as client:
            response = client.patch(
                "/api/v1/users/profile",
                json={"role": "backend"},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 200
    mock_run.assert_called_once()
    call_args = mock_run.call_args
    assert call_args.args[0] == TEST_USER_ID


# ─── run_ondemand_brief 단위 테스트 ───────────────────────────────────────────

def _make_mock_client():
    """체인 가능한 Supabase MagicMock 반환."""
    mock_client = MagicMock()
    # 체인 메서드들이 자기 자신을 반환하도록 설정
    chain = mock_client.table.return_value
    for attr in ("select", "delete", "update", "eq", "neq", "lt", "in_"):
        getattr(chain, attr).return_value = chain
    chain.execute.return_value.data = []
    return mock_client


def test_run_ondemand_brief_skips_if_processing():
    """processing 상태 Brief가 있으면 DELETE를 호출하지 않고 반환."""
    mock_client = _make_mock_client()

    # processing 체크: .table().select().eq().eq().eq().execute() → 데이터 있음
    processing_chain = MagicMock()
    processing_chain.select.return_value = processing_chain
    processing_chain.eq.return_value = processing_chain
    processing_chain.execute.return_value.data = [{"id": "existing-brief"}]

    delete_chain = MagicMock()
    delete_chain.delete.return_value = delete_chain
    delete_chain.eq.return_value = delete_chain
    delete_chain.neq.return_value = delete_chain
    delete_chain.execute.return_value.data = []

    def table_side_effect(name):
        if name == "daily_briefs":
            return processing_chain
        return MagicMock()

    mock_client.table.side_effect = table_side_effect

    with patch("pipeline.orchestrator.get_supabase", return_value=mock_client):
        run_ondemand_brief(TEST_USER_ID, TEST_BRIEF_DATE)

    # delete가 호출되지 않아야 함
    processing_chain.delete.assert_not_called()


def test_run_ondemand_brief_deletes_failed_brief():
    """failed 상태 Brief 삭제 후 재생성 흐름 검증."""
    mock_client = MagicMock()

    call_count = [0]

    def table_side_effect(name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.delete.return_value = chain
        chain.eq.return_value = chain
        chain.neq.return_value = chain
        chain.in_.return_value = chain

        if name == "daily_briefs":
            call_count[0] += 1
            if call_count[0] == 1:
                # 첫 번째 호출: processing 체크 → 없음
                chain.execute.return_value.data = []
            else:
                # 두 번째 이후 호출 (delete, create 등)
                chain.execute.return_value.data = []
        elif name == "signals":
            chain.execute.return_value.data = [{"id": "sig-1"}, {"id": "sig-2"}]
        else:
            chain.execute.return_value.data = []

        return chain

    mock_client.table.side_effect = table_side_effect

    with patch("pipeline.orchestrator.get_supabase", return_value=mock_client), \
         patch("pipeline.orchestrator.create_daily_brief_for_user") as mock_create:
        run_ondemand_brief(TEST_USER_ID, TEST_BRIEF_DATE)

    # Story 5.4: llm 인자(Memory RAG용)가 5번째 위치로 추가됨 (키 미설정 시 None)
    mock_create.assert_called_once_with(
        TEST_USER_ID, ["sig-1", "sig-2"], mock_client, TEST_BRIEF_DATE, ANY
    )


def test_run_ondemand_brief_deletes_completed_brief():
    """completed 상태 Brief(프로필 변경 케이스) 삭제 후 재생성 검증."""
    mock_client = MagicMock()
    call_count = [0]

    def table_side_effect(name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.delete.return_value = chain
        chain.eq.return_value = chain
        chain.neq.return_value = chain
        chain.in_.return_value = chain

        if name == "daily_briefs":
            call_count[0] += 1
            # 첫 번째 호출(processing 체크): completed는 processing 아님 → 없음
            chain.execute.return_value.data = []
        elif name == "signals":
            chain.execute.return_value.data = [{"id": "sig-3"}]
        else:
            chain.execute.return_value.data = []

        return chain

    mock_client.table.side_effect = table_side_effect

    with patch("pipeline.orchestrator.get_supabase", return_value=mock_client), \
         patch("pipeline.orchestrator.create_daily_brief_for_user") as mock_create:
        run_ondemand_brief(TEST_USER_ID, TEST_BRIEF_DATE)

    mock_create.assert_called_once_with(
        TEST_USER_ID, ["sig-3"], mock_client, TEST_BRIEF_DATE, ANY
    )


def test_run_ondemand_brief_no_signals_today():
    """오늘 날짜 processed Signal이 없어도 graceful하게 처리 (None 반환)."""
    mock_client = MagicMock()
    call_count = [0]

    def table_side_effect(name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.delete.return_value = chain
        chain.eq.return_value = chain
        chain.neq.return_value = chain
        chain.in_.return_value = chain
        chain.execute.return_value.data = []  # Signal 없음
        return chain

    mock_client.table.side_effect = table_side_effect

    with patch("pipeline.orchestrator.get_supabase", return_value=mock_client), \
         patch("pipeline.orchestrator.create_daily_brief_for_user") as mock_create:
        mock_create.return_value = None
        run_ondemand_brief(TEST_USER_ID, TEST_BRIEF_DATE)

    # signal_ids=[]로 create 호출됨 (Story 5.4: llm 인자 추가)
    mock_create.assert_called_once_with(TEST_USER_ID, [], mock_client, TEST_BRIEF_DATE, ANY)
