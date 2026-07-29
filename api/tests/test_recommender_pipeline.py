"""Recommender & Daily Brief Batch Pipeline 단위 테스트 (Story 2.3).

Supabase / Firebase Mock으로 실행 가능 — 환경변수 불필요.
"""
from unittest.mock import MagicMock, call, patch

import pytest

from pipeline.fcm import run_daily_brief_push_job, send_daily_brief_push
from pipeline.recommender import (
    _RAG_WEIGHT,
    _embed_signal_list,
    _score_signals,
    compute_relevance_score,
    create_daily_brief_for_user,
    mark_stuck_jobs,
    run_recommender,
)


# ─── compute_relevance_score ──────────────────────────────────────────────────

def test_tech_stack_match_increases_score():
    signal = {"technology_name": "langgraph", "summary": "multi-agent framework"}
    user = {"tech_stack": ["LangGraph", "Python"], "interests": []}
    assert compute_relevance_score(signal, user) > 0.1


def test_interests_match_increases_score():
    signal = {"technology_name": "MCP", "summary": "protocol for agents"}
    user = {"tech_stack": [], "interests": ["Agent", "MCP"]}
    assert compute_relevance_score(signal, user) > 0.1


def test_no_match_returns_base_score():
    signal = {"technology_name": "Kubernetes", "summary": "container orchestration"}
    user = {"tech_stack": ["React"], "interests": ["Frontend"]}
    assert compute_relevance_score(signal, user) == 0.1


def test_score_capped_at_one():
    signal = {"technology_name": "langgraph mcp agent", "summary": "rag agent langgraph mcp"}
    user = {"tech_stack": ["LangGraph", "MCP", "Agent", "RAG"], "interests": ["LangGraph", "MCP", "Agent"]}
    assert compute_relevance_score(signal, user) == 1.0


def test_empty_profile_returns_base_score():
    signal = {"technology_name": "LangGraph", "summary": "multi-agent"}
    user = {}
    assert compute_relevance_score(signal, user) == 0.1


def test_none_fields_treated_as_empty():
    signal = {"technology_name": None, "summary": None}
    user = {"tech_stack": ["LangGraph"], "interests": []}
    assert compute_relevance_score(signal, user) == 0.1


# ─── mark_stuck_jobs ──────────────────────────────────────────────────────────

def test_mark_stuck_jobs_updates_processing_to_failed():
    mock_client = MagicMock()
    # chain: .table().update().eq().lt().execute()
    mock_client.table.return_value.update.return_value.eq.return_value.lt.return_value.execute.return_value.data = [
        {"id": "brief-1"}, {"id": "brief-2"}
    ]
    count = mark_stuck_jobs(mock_client, timeout_minutes=15)
    assert count == 2


def test_mark_stuck_jobs_returns_zero_when_none_stuck():
    mock_client = MagicMock()
    mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.lt.return_value.execute.return_value.data = []
    count = mark_stuck_jobs(mock_client)
    assert count == 0


# ─── Mock 헬퍼 ───────────────────────────────────────────────────────────────

def _make_brief_mock_client(
    existing_brief=None,
    user_profile=None,
    signal_data=None,
    brief_insert_data=None,
    signals_insert_data=None,
    memory_count=0,
    rpc_similarity=None,
    rpc_error=False,
):
    """create_daily_brief_for_user 테스트용 Mock Supabase 클라이언트.

    Story 5.4: memory_count>0이면 Memory RAG 경로, rpc_similarity/rpc_error로 match_memories 응답 제어.
    """
    mock_client = MagicMock()

    daily_briefs_mock = MagicMock()
    daily_brief_signals_mock = MagicMock()
    user_profiles_mock = MagicMock()
    signals_mock = MagicMock()
    memories_mock = MagicMock()

    # memories.select("id", count="exact").eq().limit().execute()
    mem_exec = MagicMock()
    mem_exec.count = memory_count
    mem_exec.data = [{"id": "mem-1"}] if memory_count else []
    memories_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value = mem_exec

    # client.rpc("match_memories", {...}).execute()
    rpc_chain = MagicMock()
    if rpc_error:
        rpc_chain.execute.side_effect = RuntimeError("rpc boom")
    else:
        rpc_chain.execute.return_value.data = (
            [{"similarity": rpc_similarity}] if rpc_similarity is not None else []
        )
    mock_client.rpc.return_value = rpc_chain

    # daily_briefs.select (중복 체크)
    select_chain = MagicMock()
    select_chain.execute.return_value.data = existing_brief or []
    daily_briefs_mock.select.return_value.eq.return_value.eq.return_value = select_chain

    # daily_briefs.insert
    insert_chain = MagicMock()
    insert_chain.execute.return_value.data = brief_insert_data if brief_insert_data is not None else [{"id": "brief-uuid"}]
    daily_briefs_mock.insert.return_value = insert_chain

    # daily_briefs.update (processing 전이 + completed 전이)
    update_chain = MagicMock()
    update_chain.eq.return_value.execute.return_value.data = [{"id": "brief-uuid"}]
    daily_briefs_mock.update.return_value = update_chain

    # user_profiles.select
    profile_chain = MagicMock()
    profile_chain.execute.return_value.data = [user_profile] if user_profile else [{}]
    user_profiles_mock.select.return_value.eq.return_value = profile_chain

    # signals.select (배치 조회 — .in_().eq().execute())
    signal_chain = MagicMock()
    signal_chain.execute.return_value.data = signal_data if signal_data is not None else [
        {"id": "sig-1", "technology_name": "LangGraph", "title": "LangGraph 업데이트", "summary": "new features"}
    ]
    signals_mock.select.return_value.in_.return_value.eq.return_value = signal_chain

    # daily_brief_signals.insert
    dbs_insert_chain = MagicMock()
    dbs_insert_chain.execute.return_value.data = signals_insert_data if signals_insert_data is not None else [{"id": "dbs-uuid"}]
    daily_brief_signals_mock.insert.return_value = dbs_insert_chain

    def table_side_effect(table_name):
        mapping = {
            "daily_briefs": daily_briefs_mock,
            "daily_brief_signals": daily_brief_signals_mock,
            "user_profiles": user_profiles_mock,
            "signals": signals_mock,
            "memories": memories_mock,
        }
        return mapping.get(table_name, MagicMock())

    mock_client.table.side_effect = table_side_effect
    mock_client._daily_briefs = daily_briefs_mock
    mock_client._daily_brief_signals = daily_brief_signals_mock
    mock_client._user_profiles = user_profiles_mock
    mock_client._signals = signals_mock
    mock_client._memories = memories_mock
    return mock_client


# ─── create_daily_brief_for_user ─────────────────────────────────────────────

def test_creates_brief_and_signals():
    mock_client = _make_brief_mock_client()

    brief_id = create_daily_brief_for_user("user-1", ["sig-1"], mock_client, "2026-07-24")

    assert brief_id == "brief-uuid"
    mock_client._daily_briefs.insert.assert_called_once()
    mock_client._daily_brief_signals.insert.assert_called_once()
    # processing → completed 두 번 update 호출 확인
    assert mock_client._daily_briefs.update.call_count == 2
    # 마지막 update가 completed 상태인지 확인
    last_update_data = mock_client._daily_briefs.update.call_args_list[-1][0][0]
    assert last_update_data["status"] == "completed"


def test_skips_duplicate_brief():
    existing = [{"id": "existing-brief-id"}]
    mock_client = _make_brief_mock_client(existing_brief=existing)

    brief_id = create_daily_brief_for_user("user-1", ["sig-1"], mock_client, "2026-07-24")

    assert brief_id == "existing-brief-id"
    mock_client._daily_briefs.insert.assert_not_called()


def test_returns_none_when_no_processed_signals():
    mock_client = _make_brief_mock_client(signal_data=[])

    result = create_daily_brief_for_user("user-1", ["sig-1"], mock_client, "2026-07-24")

    assert result is None
    mock_client._daily_briefs.insert.assert_not_called()


def test_returns_none_when_brief_insert_fails():
    mock_client = _make_brief_mock_client(brief_insert_data=[])

    result = create_daily_brief_for_user("user-1", ["sig-1"], mock_client, "2026-07-24")

    assert result is None


def test_returns_none_and_sets_failed_when_signals_insert_fails():
    """P2: daily_brief_signals INSERT 실패 시 brief가 failed 상태로 전이되고 None 반환."""
    mock_client = _make_brief_mock_client(signals_insert_data=[])

    result = create_daily_brief_for_user("user-1", ["sig-1"], mock_client, "2026-07-24")

    assert result is None
    # failed 전이 확인
    update_calls = mock_client._daily_briefs.update.call_args_list
    failed_call = any(
        call[0][0].get("status") == "failed"
        for call in update_calls
    )
    assert failed_call, "brief_signals INSERT 실패 시 daily_briefs.status='failed' 전이 없음"


def test_sets_processing_status_before_signals_insert():
    """AC-6: INSERT 후 processing 상태로 전이 확인."""
    mock_client = _make_brief_mock_client()

    create_daily_brief_for_user("user-1", ["sig-1"], mock_client, "2026-07-24")

    update_calls = mock_client._daily_briefs.update.call_args_list
    statuses = [c[0][0].get("status") for c in update_calls]
    assert "processing" in statuses, "processing 상태 전이 없음"
    processing_idx = statuses.index("processing")
    completed_idx = statuses.index("completed")
    assert processing_idx < completed_idx, "processing이 completed보다 먼저 설정되어야 함"


# ─── run_recommender ──────────────────────────────────────────────────────────

def test_user_failure_isolation():
    """두 번째 사용자 실패 → 다른 사용자 처리 계속, success_count 정확."""
    mock_client = MagicMock()
    call_order = []

    def create_brief_side_effect(user_id, signal_ids, client, brief_date, llm=None, signal_embeddings=None):
        call_order.append(user_id)
        if user_id == "user-2":
            raise RuntimeError("DB error")
        return f"brief-{user_id}"

    # _fetch_all_users mock: range 쿼리 패턴
    users_page = MagicMock()
    users_page.data = [{"id": "user-1"}, {"id": "user-2"}, {"id": "user-3"}]
    mock_client.table.return_value.select.return_value.eq.return_value.range.return_value.execute.return_value = users_page

    with patch("pipeline.recommender.create_daily_brief_for_user", side_effect=create_brief_side_effect):
        with patch("pipeline.recommender.mark_stuck_jobs"):
            success = run_recommender(["sig-1"], mock_client, "2026-07-24")

    assert success == 2
    assert call_order == ["user-1", "user-2", "user-3"]


def test_skips_non_onboarded_users():
    """onboarding_completed=false(쿼리에서 제외) 사용자 → brief 생성 없음."""
    mock_client = MagicMock()

    users_page = MagicMock()
    users_page.data = []
    mock_client.table.return_value.select.return_value.eq.return_value.range.return_value.execute.return_value = users_page

    with patch("pipeline.recommender.create_daily_brief_for_user") as mock_create:
        with patch("pipeline.recommender.mark_stuck_jobs"):
            success = run_recommender(["sig-1"], mock_client, "2026-07-24")

    assert success == 0
    mock_create.assert_not_called()


def test_failure_sets_brief_status_failed():
    """P3: 사용자 예외 발생 시 pending/processing brief → failed 전이."""
    mock_client = MagicMock()

    users_page = MagicMock()
    users_page.data = [{"id": "user-1"}]
    mock_client.table.return_value.select.return_value.eq.return_value.range.return_value.execute.return_value = users_page

    with patch("pipeline.recommender.create_daily_brief_for_user", side_effect=RuntimeError("fail")):
        with patch("pipeline.recommender.mark_stuck_jobs"):
            run_recommender(["sig-1"], mock_client, "2026-07-24")

    # update("status"="failed") 호출 확인
    update_calls = mock_client.table.return_value.update.call_args_list
    failed_update = any(
        call[0][0].get("status") == "failed"
        for call in update_calls
    )
    assert failed_update, "예외 시 daily_briefs.status='failed' 전이 없음"


# ─── send_daily_brief_push ────────────────────────────────────────────────────

def test_push_success():
    with patch("pipeline.fcm.messaging.send", return_value="message_id"):
        result = send_daily_brief_push("uid", "token", "LangGraph 업데이트", "2026-07-24", "sig-1")
    assert result is True


def test_push_exception_returns_false():
    with patch("pipeline.fcm.messaging.send", side_effect=Exception("FCM error")):
        result = send_daily_brief_push("uid", "token", "LangGraph 업데이트", "2026-07-24", "sig-1")
    assert result is False


def test_push_uses_fallback_title_when_empty():
    """P11: top_signal_title이 빈 문자열일 때 폴백 제목 사용."""
    from pipeline.fcm import _PUSH_FALLBACK_TITLE
    captured = []

    def mock_send(msg):
        captured.append(msg.notification.body)
        return "msg_id"

    with patch("pipeline.fcm.messaging.send", side_effect=mock_send):
        send_daily_brief_push("uid", "token", "", "2026-07-24", "sig-1")

    assert captured[0] == _PUSH_FALLBACK_TITLE


def test_push_includes_data_payload():
    """Story 5.3: data 페이로드(type, signal_id)가 메시지에 포함된다."""
    captured = {}

    def mock_send(msg):
        captured["data"] = msg.data
        return "msg_id"

    with patch("pipeline.fcm.messaging.send", side_effect=mock_send):
        send_daily_brief_push("uid", "token", "LangGraph 업데이트", "2026-07-24", "sig-1")

    assert captured["data"] == {"type": "daily_brief", "signal_id": "sig-1"}


# ─── run_daily_brief_push_job ─────────────────────────────────────────────────

def test_no_briefs_returns_zero():
    mock_client = MagicMock()
    briefs_result = MagicMock()
    briefs_result.data = []
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.range.return_value.execute.return_value = briefs_result

    result = run_daily_brief_push_job(mock_client, "2026-07-24")

    assert result == 0


def test_push_job_sends_to_all_devices():
    """completed brief 보유 사용자의 모든 기기에 Push 전송."""
    mock_client = MagicMock()

    briefs_mock = MagicMock()
    briefs_mock.select.return_value.eq.return_value.eq.return_value.range.return_value.execute.return_value.data = [
        {"id": "brief-1", "user_id": "user-1"}
    ]

    dbs_mock = MagicMock()
    dbs_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"signal_id": "sig-1", "position": 1}
    ]

    signals_mock = MagicMock()
    signals_mock.select.return_value.eq.return_value.execute.return_value.data = [
        {"title": "LangGraph 업데이트"}
    ]

    devices_mock = MagicMock()
    devices_mock.select.return_value.eq.return_value.execute.return_value.data = [
        {"fcm_token": "token-a"},
        {"fcm_token": "token-b"},
    ]

    def table_side_effect(table_name):
        mapping = {
            "daily_briefs": briefs_mock,
            "daily_brief_signals": dbs_mock,
            "signals": signals_mock,
            "user_devices": devices_mock,
        }
        return mapping.get(table_name, MagicMock())

    mock_client.table.side_effect = table_side_effect

    with patch("pipeline.fcm.send_daily_brief_push", return_value=True) as mock_send:
        result = run_daily_brief_push_job(mock_client, "2026-07-24")

    assert result == 2
    assert mock_send.call_count == 2


# ─── run_daily_pipeline 오케스트레이터 ─────────────────────────────────────────

def test_run_daily_pipeline_calls_stages_in_order():
    """각 단계 함수가 순서대로 호출되는지 검증."""
    import pipeline.orchestrator  # patch 전에 모듈 로드 필요
    call_order = []

    def mock_collect(self):
        call_order.append("collect")
        from pipeline.models import RawArticle
        return [RawArticle("LangGraph", "Title", "https://a.com", "official_blog")]

    def mock_normalize(articles, signal_date, client, brief_date):
        call_order.append("normalize")
        return ["sig-1"]

    def mock_build(signal_ids, client, llm, brief_date):
        call_order.append("build")
        return ["sig-1"]

    def mock_review(signal_id, client, llm, brief_date):
        call_order.append("review")
        return ["rev-1"]

    def mock_recommend(signal_ids, client, brief_date, llm=None):
        call_order.append("recommend")
        return 1

    with (
        # Story 6.1: stub 모드로 고정 — StubCollector.collect 경로 검증(오프라인)
        patch("pipeline.orchestrator.settings.collector_mode", "stub"),
        patch("pipeline.orchestrator.StubCollector.collect", mock_collect),
        patch("pipeline.orchestrator.normalize", mock_normalize),
        patch("pipeline.orchestrator.build_signals", mock_build),
        patch("pipeline.orchestrator.review_all_for_signal", mock_review),
        patch("pipeline.orchestrator.run_recommender", mock_recommend),
        patch("pipeline.orchestrator.get_supabase", return_value=MagicMock()),
        patch("pipeline.orchestrator.OpenAIProvider", return_value=MagicMock()),
    ):
        result = pipeline.orchestrator.run_daily_pipeline("2026-07-24")

    assert call_order == ["collect", "normalize", "build", "review", "recommend"]
    assert result["error"] is None
    assert result["briefs"] == 1


def test_run_daily_pipeline_brief_date_derives_today():
    """P9: brief_date 파라미터 전달 시 today를 date.today()가 아닌 brief_date에서 파생."""
    import pipeline.orchestrator  # patch 전에 모듈 로드 필요
    captured_dates = {}

    def mock_normalize(articles, signal_date, client, brief_date):
        captured_dates["signal_date"] = signal_date.isoformat()
        captured_dates["brief_date"] = brief_date
        return []

    with (
        # Story 6.1: stub 모드로 고정 — 오프라인(네트워크 미접속) 보장
        patch("pipeline.orchestrator.settings.collector_mode", "stub"),
        patch("pipeline.orchestrator.StubCollector.collect", return_value=[]),
        patch("pipeline.orchestrator.normalize", mock_normalize),
        patch("pipeline.orchestrator.build_signals", return_value=[]),
        patch("pipeline.orchestrator.run_recommender", return_value=0),
        patch("pipeline.orchestrator.get_supabase", return_value=MagicMock()),
        patch("pipeline.orchestrator.OpenAIProvider", return_value=MagicMock()),
    ):
        pipeline.orchestrator.run_daily_pipeline("2026-01-01")

    assert captured_dates["signal_date"] == "2026-01-01"
    assert captured_dates["brief_date"] == "2026-01-01"


# ─── Memory RAG (Story 5.4) ───────────────────────────────────────────────────

def _rag_score_client(memory_count=1, similarity=0.8, rpc_error=False):
    """_score_signals 단위 테스트용 최소 Mock 클라이언트 (memories 체크 + match_memories RPC)."""
    client = MagicMock()

    mem_exec = MagicMock()
    mem_exec.count = memory_count
    mem_exec.data = [{"id": "mem-1"}] if memory_count else []
    memories_mock = MagicMock()
    memories_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value = mem_exec

    rpc_chain = MagicMock()
    if rpc_error:
        rpc_chain.execute.side_effect = RuntimeError("rpc boom")
    else:
        rpc_chain.execute.return_value.data = [{"similarity": similarity}]
    client.rpc.return_value = rpc_chain

    def table_side_effect(name):
        return memories_mock if name == "memories" else MagicMock()

    client.table.side_effect = table_side_effect
    return client


_SIG = {"id": "sig-1", "technology_name": "LangGraph", "title": "t", "summary": "s"}
_EMB = {"sig-1": [0.01] * 1536}


# ── _embed_signal_list: 배치당 1회 임베딩, 실패 격리 (설계 A-2, AD-5) ──

def test_embed_signal_list_embeds_each_signal_once():
    llm = MagicMock()
    llm.embed_text.return_value = [0.1] * 1536
    signals = [
        {"id": "a", "technology_name": "X", "title": "t1", "summary": "s1"},
        {"id": "b", "technology_name": "Y", "title": "t2", "summary": "s2"},
    ]
    emb = _embed_signal_list(signals, llm, "2026-07-29")
    assert set(emb.keys()) == {"a", "b"}
    assert llm.embed_text.call_count == 2


def test_embed_signal_list_skips_failed_embeddings():
    llm = MagicMock()
    llm.embed_text.side_effect = [[0.1] * 1536, RuntimeError("embed fail")]
    signals = [
        {"id": "a", "technology_name": "X", "title": "t1", "summary": "s1"},
        {"id": "b", "technology_name": "Y", "title": "t2", "summary": "s2"},
    ]
    emb = _embed_signal_list(signals, llm, "2026-07-29")
    assert "a" in emb and "b" not in emb  # 실패한 Signal만 누락 → 콜드 스타트 폴백


def test_embed_signal_list_skips_empty_text():
    llm = MagicMock()
    llm.embed_text.return_value = [0.1] * 1536
    signals = [{"id": "a", "technology_name": None, "title": None, "summary": None}]
    emb = _embed_signal_list(signals, llm, "2026-07-29")
    assert emb == {}
    llm.embed_text.assert_not_called()


# ── _score_signals: RAG 경로 / 콜드 스타트 폴백 / 예외 폴백 / user_id 격리 ──

def test_score_signals_no_llm_is_coldstart():
    """llm 미주입 → 콜드 스타트, RPC 미호출 (AC-A2)."""
    profile = {"tech_stack": ["LangGraph"], "interests": []}
    client = MagicMock()
    scored = _score_signals([_SIG], profile, "u", client, "d", None, None)
    assert scored[0][1] == compute_relevance_score(_SIG, profile)
    client.rpc.assert_not_called()


def test_score_signals_coldstart_when_no_memories():
    """memory 미보유 사용자 → 콜드 스타트 폴백, RPC 미호출 (AC-A2)."""
    profile = {"tech_stack": ["LangGraph"], "interests": []}
    client = _rag_score_client(memory_count=0)
    scored = _score_signals([_SIG], profile, "u", client, "d", MagicMock(), _EMB)
    assert scored[0][1] == compute_relevance_score(_SIG, profile)
    client.rpc.assert_not_called()


def test_score_signals_rag_boosts_over_coldstart():
    """memory 보유 → base + _RAG_WEIGHT*top_similarity (AC-A1)."""
    profile = {}  # base = 0.1
    client = _rag_score_client(memory_count=2, similarity=0.8)
    scored = _score_signals([_SIG], profile, "u", client, "d", MagicMock(), _EMB)
    assert scored[0][1] == pytest.approx(0.1 + _RAG_WEIGHT * 0.8)
    client.rpc.assert_called_once()


def test_score_signals_clamped_to_one():
    """블렌딩 결과가 상한 1.0을 넘지 않음 (relevance_score 불변식, AC-A3)."""
    sig = {"id": "sig-1", "technology_name": "langgraph mcp agent rag",
           "title": "t", "summary": "langgraph mcp agent rag"}
    profile = {"tech_stack": ["langgraph", "mcp", "agent", "rag"],
               "interests": ["langgraph", "mcp", "agent"]}  # base = 1.0
    client = _rag_score_client(memory_count=1, similarity=0.9)
    scored = _score_signals([sig], profile, "u", client, "d", MagicMock(), {"sig-1": [0.01] * 1536})
    assert scored[0][1] == 1.0


def test_score_signals_rpc_error_falls_back_to_base():
    """match_memories RPC 예외 → 해당 Signal 콜드 스타트 점수로 폴백 (AC-A2, AD-5)."""
    client = _rag_score_client(memory_count=1, rpc_error=True)
    scored = _score_signals([_SIG], {}, "u", client, "d", MagicMock(), _EMB)
    assert scored[0][1] == 0.1  # base


def test_score_signals_missing_embedding_uses_base():
    """임베딩 누락 Signal(임베딩 실패분) → base 점수, RPC 미호출."""
    client = _rag_score_client(memory_count=1, similarity=0.9)
    scored = _score_signals([_SIG], {}, "u", client, "d", MagicMock(), {})  # 임베딩 없음
    assert scored[0][1] == 0.1
    client.rpc.assert_not_called()


def test_score_signals_scopes_rpc_to_user_id():
    """match_memories가 반드시 해당 user_id로 스코프 호출됨 (AC-A3 격리)."""
    client = _rag_score_client(memory_count=1, similarity=0.5)
    _score_signals([_SIG], {}, "user-XYZ", client, "d", MagicMock(), _EMB)
    name, params = client.rpc.call_args[0]
    assert name == "match_memories"
    assert params["match_user_id"] == "user-XYZ"


def test_score_signals_deterministic_order():
    """동점 시 signal_id로 결정론적 정렬 (설계 A-1 ③)."""
    sigs = [
        {"id": "sig-b", "technology_name": "X", "title": "t", "summary": "s"},
        {"id": "sig-a", "technology_name": "X", "title": "t", "summary": "s"},
    ]
    scored = _score_signals(sigs, {}, "u", MagicMock(), "d", None, None)
    assert [s[0] for s in scored] == ["sig-a", "sig-b"]  # 동점 0.1 → id 오름차순


# ── create_daily_brief_for_user 통합: RAG 반영 + 실패 시 생성 지속 ──

def test_brief_uses_rag_score_when_memories_exist():
    """memory 보유 시 daily_brief_signals.relevance_score에 RAG 블렌딩 점수가 반영됨."""
    client = _make_brief_mock_client(memory_count=1, rpc_similarity=0.8)
    brief_id = create_daily_brief_for_user(
        "user-1", ["sig-1"], client, "2026-07-24", MagicMock(), {"sig-1": [0.01] * 1536}
    )
    assert brief_id == "brief-uuid"
    inserted = client._daily_brief_signals.insert.call_args[0][0]
    assert inserted[0]["relevance_score"] == pytest.approx(0.1 + _RAG_WEIGHT * 0.8)


def test_brief_creation_continues_when_rpc_fails():
    """RPC 실패해도 brief 생성이 중단되지 않고 콜드 스타트 점수로 완료 (AC-A2, AD-5)."""
    client = _make_brief_mock_client(memory_count=1, rpc_error=True)
    brief_id = create_daily_brief_for_user(
        "user-1", ["sig-1"], client, "2026-07-24", MagicMock(), {"sig-1": [0.01] * 1536}
    )
    assert brief_id == "brief-uuid"  # 생성 지속
    inserted = client._daily_brief_signals.insert.call_args[0][0]
    assert inserted[0]["relevance_score"] == 0.1  # base 폴백


def test_run_recommender_embeds_signals_once_for_batch():
    """배치 경로: llm 주입 시 후보 Signal을 배치당 1회만 임베딩하여 전 사용자 재사용 (설계 A-2)."""
    mock_client = MagicMock()

    users_page = MagicMock()
    users_page.data = [{"id": "user-1"}, {"id": "user-2"}]
    mock_client.table.return_value.select.return_value.eq.return_value.range.return_value.execute.return_value = users_page

    llm = MagicMock()
    with patch("pipeline.recommender.mark_stuck_jobs"), \
         patch("pipeline.recommender.create_daily_brief_for_user", return_value="brief") as mock_create, \
         patch("pipeline.recommender._build_signal_embeddings", return_value={"sig-1": [0.01] * 1536}) as mock_embed:
        run_recommender(["sig-1"], mock_client, "2026-07-24", llm)

    # 배치 임베딩은 사용자 수와 무관하게 1회
    mock_embed.assert_called_once()
    # 각 사용자 create 호출에 동일 signal_embeddings dict 재사용
    for c in mock_create.call_args_list:
        assert c[0][5] == {"sig-1": [0.01] * 1536}
