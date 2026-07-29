"""Story 6.5 — engagement 수집 엔드포인트 + 로깅 헬퍼 단위 테스트.

오프라인 원칙: 실 네트워크·실 DB 금지. Supabase는 MagicMock.
"""
import time
from unittest.mock import MagicMock, patch

import jwt as pyjwt
from fastapi.testclient import TestClient

from pipeline.engagement import log_engagement, log_engagement_bulk

TEST_SECRET = "test-super-secret-key-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
SIG_OK = "11111111-1111-1111-1111-111111111111"
SIG_BAD = "22222222-2222-2222-2222-222222222222"


def _make_token(user_id: str = TEST_USER_ID) -> str:
    payload = {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")


def _insert_mock_client(fail_signal_ids=()):
    """engagement_events insert를 signal_id별로 성공/실패 제어하는 Mock 클라이언트."""
    client = MagicMock()

    def table(name):
        t = MagicMock()

        def insert(row):
            ins = MagicMock()
            if row.get("signal_id") in fail_signal_ids:
                ins.execute.side_effect = RuntimeError("FK violation: signal not found")
            else:
                ins.execute.return_value.data = [{"id": "ev-1"}]
            return ins

        t.insert.side_effect = insert
        return t

    client.table.side_effect = table
    return client


# ─── POST /api/v1/engagement ────────────────────────────────────────────────

def test_collect_engagement_accepts_valid_events(monkeypatch):
    """유효한 open·read_through 배치 → 200 + accepted 카운트."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    client_mock = _insert_mock_client()
    with patch("routers.engagement.get_supabase", return_value=client_mock):
        from main import app
        with TestClient(app) as client:
            res = client.post(
                "/api/v1/engagement",
                json={"events": [
                    {"signal_id": SIG_OK, "event_type": "open"},
                    {"signal_id": SIG_OK, "event_type": "read_through"},
                ]},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert res.status_code == 200
    body = res.json()
    assert body["data"]["accepted"] == 2
    assert body["error"] is None


def test_collect_engagement_rejects_decision_type_422(monkeypatch):
    """클라이언트발 decision 타입은 서버 정본이라 금지 → 422 (Pydantic Literal)."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    client_mock = _insert_mock_client()
    with patch("routers.engagement.get_supabase", return_value=client_mock):
        from main import app
        with TestClient(app) as client:
            res = client.post(
                "/api/v1/engagement",
                json={"events": [{"signal_id": SIG_OK, "event_type": "decision"}]},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert res.status_code == 422


def test_collect_engagement_skips_unknown_signal_best_effort(monkeypatch):
    """존재하지 않는 signal_id는 insert 실패 → 조용히 스킵(accepted 제외), 전체 요청은 200 유지."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    client_mock = _insert_mock_client(fail_signal_ids={SIG_BAD})
    with patch("routers.engagement.get_supabase", return_value=client_mock):
        from main import app
        with TestClient(app) as client:
            res = client.post(
                "/api/v1/engagement",
                json={"events": [
                    {"signal_id": SIG_OK, "event_type": "open"},
                    {"signal_id": SIG_BAD, "event_type": "open"},
                ]},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert res.status_code == 200
    assert res.json()["data"]["accepted"] == 1  # 실패한 SIG_BAD 제외


def test_collect_engagement_requires_auth(monkeypatch):
    """인증 헤더 없으면 거절(UX와 무관 — 서버 보호)."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    client_mock = _insert_mock_client()
    with patch("routers.engagement.get_supabase", return_value=client_mock):
        from main import app
        with TestClient(app) as client:
            res = client.post(
                "/api/v1/engagement",
                json={"events": [{"signal_id": SIG_OK, "event_type": "open"}]},
            )

    assert res.status_code in (401, 403)


# ─── log_engagement / log_engagement_bulk best-effort ───────────────────────

def test_log_engagement_swallows_insert_exception():
    """insert 예외 시에도 예외를 던지지 않는다(best-effort, AD-5)."""
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.side_effect = RuntimeError("boom")
    # 예외가 전파되면 이 호출에서 실패 → raise 없음이 성공 기준
    log_engagement(client, TEST_USER_ID, SIG_OK, "decision", metadata={"choice": "learn_now"})


def test_log_engagement_bulk_empty_is_noop():
    """빈 리스트는 insert를 호출하지 않는다(no-op)."""
    client = MagicMock()
    log_engagement_bulk(client, [])
    client.table.assert_not_called()


def test_log_engagement_bulk_swallows_exception():
    """bulk insert 예외도 삼킨다(best-effort)."""
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.side_effect = RuntimeError("boom")
    log_engagement_bulk(client, [{"user_id": TEST_USER_ID, "signal_id": SIG_OK, "event_type": "impression"}])


def test_log_engagement_builds_optional_fields():
    """daily_brief_id·variant·metadata가 있을 때만 row에 포함된다."""
    client = MagicMock()
    captured = {}

    def insert(row):
        captured.update(row)
        return MagicMock()

    client.table.return_value.insert.side_effect = insert
    log_engagement(
        client, TEST_USER_ID, SIG_OK, "impression",
        daily_brief_id="brief-1", variant="rag", metadata={"position": 1},
    )
    assert captured["daily_brief_id"] == "brief-1"
    assert captured["variant"] == "rag"
    assert captured["metadata"] == {"position": 1}
    assert captured["event_type"] == "impression"
