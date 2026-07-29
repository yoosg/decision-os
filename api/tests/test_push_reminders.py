"""Queue/Outcome 리마인더 Push 단위 테스트 (Story 5.3 Trigger #2/#3).

Supabase / Firebase Mock으로 실행 가능 — 환경변수 불필요.
test_recommender_pipeline.py의 `pipeline.fcm.messaging.send` patch 패턴 답습.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pipeline.fcm import (
    run_outcome_reminder_job,
    run_queue_reminder_job,
    send_outcome_reminder_push,
    send_queue_reminder_push,
)


# ─── Supabase 클라이언트 Fluent Mock ──────────────────────────────────────────

class _FakeTable:
    """모든 쿼리 메서드가 self를 반환하고 execute()가 고정 data를 돌려주는 fluent mock.

    update() 호출은 공유 calls dict에 기록해 검증에 사용.
    """

    def __init__(self, data, calls):
        self._data = data
        self._calls = calls

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def is_(self, *a, **k):
        return self

    def lte(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def range(self, *a, **k):
        return self

    def update(self, payload, *a, **k):
        self._calls.setdefault("update", []).append(payload)
        return self

    def execute(self):
        return SimpleNamespace(data=self._data)


def _make_client(tables, calls):
    client = MagicMock()
    client.table.side_effect = lambda name: tables.get(name, _FakeTable([], calls))
    return client


def _utc_at(run_date: str, hour_utc: int = 3) -> str:
    """run_date + hour_utc(UTC) ISO 문자열. hour_utc=3 → +9h = run_date 12:00 KST."""
    return f"{run_date}T{hour_utc:02d}:00:00+00:00"


# ─── send_queue_reminder_push / send_outcome_reminder_push ────────────────────

def test_queue_push_success():
    with patch("pipeline.fcm.messaging.send", return_value="mid"):
        assert send_queue_reminder_push("u", "tok", "제목", "s1") is True


def test_queue_push_exception_returns_false():
    with patch("pipeline.fcm.messaging.send", side_effect=Exception("boom")):
        assert send_queue_reminder_push("u", "tok", "제목", "s1") is False


def test_queue_push_empty_token_guard():
    with patch("pipeline.fcm.messaging.send") as m:
        assert send_queue_reminder_push("u", "", "제목", "s1") is False
        m.assert_not_called()


def test_queue_push_includes_data_payload():
    captured = {}

    def mock_send(msg):
        captured["data"] = msg.data
        captured["title"] = msg.notification.title
        return "mid"

    with patch("pipeline.fcm.messaging.send", side_effect=mock_send):
        send_queue_reminder_push("u", "tok", "제목", "s1")

    assert captured["data"] == {"type": "queue_reminder", "signal_id": "s1"}
    assert captured["title"] == "오늘 학습하기로 한 Signal이 남아있습니다"


def test_outcome_push_success():
    with patch("pipeline.fcm.messaging.send", return_value="mid"):
        assert send_outcome_reminder_push("u", "tok", "제목", "s1") is True


def test_outcome_push_empty_token_guard():
    with patch("pipeline.fcm.messaging.send") as m:
        assert send_outcome_reminder_push("u", "", "제목", "s1") is False
        m.assert_not_called()


def test_outcome_push_includes_data_payload():
    captured = {}

    def mock_send(msg):
        captured["data"] = msg.data
        captured["title"] = msg.notification.title
        return "mid"

    with patch("pipeline.fcm.messaging.send", side_effect=mock_send):
        send_outcome_reminder_push("u", "tok", "제목", "s1")

    assert captured["data"] == {"type": "outcome_reminder", "signal_id": "s1"}
    assert captured["title"] == "학습 결과를 기록해 주세요"


# ─── run_queue_reminder_job ───────────────────────────────────────────────────

def _queue_tables(decisions, calls, *, devices=None):
    return {
        "decisions": _FakeTable(decisions, calls),
        "reviews": _FakeTable([{"project_id": "p1", "signal_id": "s1"}], calls),
        "projects": _FakeTable([{"user_id": "u1"}], calls),
        "signals": _FakeTable([{"title": "LLM Agents"}], calls),
        "user_devices": _FakeTable(
            devices if devices is not None else [{"fcm_token": "tok1"}], calls
        ),
    }


def test_queue_job_sends_to_today_target():
    run_date = "2026-07-28"
    calls = {}
    decisions = [{"id": "d1", "review_id": "r1", "updated_at": _utc_at(run_date)}]
    client = _make_client(_queue_tables(decisions, calls), calls)

    with patch("pipeline.fcm.messaging.send", return_value="mid") as m:
        sent = run_queue_reminder_job(client, run_date)

    assert sent == 1
    assert m.call_count == 1


def test_queue_job_no_targets_returns_zero():
    run_date = "2026-07-28"
    calls = {}
    client = _make_client(_queue_tables([], calls), calls)

    with patch("pipeline.fcm.messaging.send") as m:
        sent = run_queue_reminder_job(client, run_date)

    assert sent == 0
    m.assert_not_called()


def test_queue_job_excludes_carried_over_item():
    """자정 넘겨 이월된 항목(updated_at 어제 KST)은 제외."""
    run_date = "2026-07-28"
    yesterday = "2026-07-27"
    calls = {}
    decisions = [{"id": "d1", "review_id": "r1", "updated_at": _utc_at(yesterday)}]
    client = _make_client(_queue_tables(decisions, calls), calls)

    with patch("pipeline.fcm.messaging.send") as m:
        sent = run_queue_reminder_job(client, run_date)

    assert sent == 0
    m.assert_not_called()


def test_queue_job_one_push_per_user():
    """한 사용자가 today 항목을 여럿 남겨도 push 1건 (설계 결정 3)."""
    run_date = "2026-07-28"
    calls = {}
    decisions = [
        {"id": "d1", "review_id": "r1", "updated_at": _utc_at(run_date, 2)},
        {"id": "d2", "review_id": "r2", "updated_at": _utc_at(run_date, 4)},
    ]
    client = _make_client(_queue_tables(decisions, calls), calls)

    with patch("pipeline.fcm.messaging.send", return_value="mid") as m:
        sent = run_queue_reminder_job(client, run_date)

    assert sent == 1
    assert m.call_count == 1


# ─── run_outcome_reminder_job ─────────────────────────────────────────────────

def _outcome_tables(decisions, calls, *, outcomes=None, devices=None):
    return {
        "decisions": _FakeTable(decisions, calls),
        "outcomes": _FakeTable(outcomes if outcomes is not None else [], calls),
        "reviews": _FakeTable([{"project_id": "p1", "signal_id": "s1"}], calls),
        "projects": _FakeTable([{"user_id": "u1"}], calls),
        "signals": _FakeTable([{"title": "LLM Agents"}], calls),
        "user_devices": _FakeTable(
            devices if devices is not None else [{"fcm_token": "tok1"}], calls
        ),
    }


def _old_created_at() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()


def test_outcome_job_sends_and_marks_sent():
    """3일 경과·outcome 없음·미발송 → push + outcome_reminder_sent_at UPDATE."""
    calls = {}
    decisions = [{"id": "d1", "review_id": "r1", "created_at": _old_created_at()}]
    client = _make_client(_outcome_tables(decisions, calls), calls)

    with patch("pipeline.fcm.messaging.send", return_value="mid") as m:
        sent = run_outcome_reminder_job(client, "2026-07-28")

    assert sent == 1
    assert m.call_count == 1
    updates = calls.get("update", [])
    assert len(updates) == 1
    assert "outcome_reminder_sent_at" in updates[0]


def test_outcome_job_skips_when_outcome_exists():
    """Outcome 이미 기록된 대상은 skip (push·update 없음)."""
    calls = {}
    decisions = [{"id": "d1", "review_id": "r1", "created_at": _old_created_at()}]
    tables = _outcome_tables(decisions, calls, outcomes=[{"id": "o1"}])
    client = _make_client(tables, calls)

    with patch("pipeline.fcm.messaging.send") as m:
        sent = run_outcome_reminder_job(client, "2026-07-28")

    assert sent == 0
    m.assert_not_called()
    assert calls.get("update", []) == []


def test_outcome_job_no_device_does_not_mark_sent():
    """설계 결정 4: 토큰 0건이면 sent_at 미기록 (다음날 재시도 보존)."""
    calls = {}
    decisions = [{"id": "d1", "review_id": "r1", "created_at": _old_created_at()}]
    tables = _outcome_tables(decisions, calls, devices=[])
    client = _make_client(tables, calls)

    with patch("pipeline.fcm.messaging.send") as m:
        sent = run_outcome_reminder_job(client, "2026-07-28")

    assert sent == 0
    m.assert_not_called()
    assert calls.get("update", []) == []


def test_outcome_job_marks_sent_even_when_send_fails():
    """설계 결정 4: 토큰 ≥1건인데 전송이 예외로 실패해도 outcome_reminder_sent_at을
    기록해 이후 중단('1회'=발송 시도 1회). 매일 재시도 스톰 방지."""
    calls = {}
    decisions = [{"id": "d1", "review_id": "r1", "created_at": _old_created_at()}]
    client = _make_client(_outcome_tables(decisions, calls), calls)

    with patch("pipeline.fcm.messaging.send", side_effect=Exception("boom")) as m:
        sent = run_outcome_reminder_job(client, "2026-07-28")

    assert sent == 0  # 전송 실패
    assert m.call_count == 1  # 시도는 함(토큰 있음)
    updates = calls.get("update", [])
    assert len(updates) == 1  # 실패해도 dedup 기록
    assert "outcome_reminder_sent_at" in updates[0]


def test_outcome_job_no_targets_returns_zero():
    calls = {}
    client = _make_client(_outcome_tables([], calls), calls)

    with patch("pipeline.fcm.messaging.send") as m:
        sent = run_outcome_reminder_job(client, "2026-07-28")

    assert sent == 0
    m.assert_not_called()
