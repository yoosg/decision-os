"""Recommender & Daily Brief Batch Pipeline 단위 테스트 (Story 2.3).

Supabase / Firebase Mock으로 실행 가능 — 환경변수 불필요.
"""
import math
from unittest.mock import MagicMock, call, patch

import pytest

from pipeline.fcm import run_daily_brief_push_job, send_daily_brief_push
from pipeline.recommender import (
    _RAG_WEIGHT,
    _W_RECENCY,
    _W_RELEVANCE,
    _authority_norm,
    _clamp,
    _embed_signal_list,
    _lexical_boost,
    _mmr_rerank,
    _popularity_norm,
    _recency_norm,
    _score_signals,
    _signal_embed_text,
    compute_relevance_score,
    compute_relevance_score_v2,
    create_daily_brief_for_user,
    mark_stuck_jobs,
    run_recommender,
)

# v2 랭킹 피처: metadata 없는 시그널(published_at/popularity/source_authority = None)의
# 중립 결합값 헬퍼 — combined = _W_RELEVANCE*blended + _W_RECENCY*0.5 (pop=0, auth=0).
def _combine_neutral(blended: float) -> float:
    return _W_RELEVANCE * blended + _W_RECENCY * 0.5


# 하이브리드 base = clamp(substring/코사인 base + 렉시컬 가점) — 실제 _score_signals와 동일.
def _base_boosted(sig: dict, profile: dict) -> float:
    return _clamp(compute_relevance_score(sig, profile) + _lexical_boost(sig, profile))


# Story 6.5: _score_signals가 (ordered, variant) 튜플을 반환하도록 확장됐다.
# 순서(ordered)만 검증하는 기존 테스트는 이 래퍼로 ordered만 받는다(variant는 별도 테스트).
def _order(*args, **kwargs):
    ordered, _variant = _score_signals(*args, **kwargs)
    return ordered


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
        patch("pipeline.orchestrator.settings.review_pregeneration_enabled", True),
        patch("pipeline.orchestrator.StubCollector.collect", mock_collect),
        patch("pipeline.orchestrator.normalize", mock_normalize),
        patch("pipeline.orchestrator.build_signals", mock_build),
        patch("pipeline.orchestrator.review_all_for_signal", mock_review),
        patch("pipeline.orchestrator.run_recommender", mock_recommend),
        patch("pipeline.orchestrator.get_supabase", return_value=MagicMock()),
        patch("pipeline.orchestrator.get_llm_provider", return_value=MagicMock()),
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
        patch("pipeline.orchestrator.get_llm_provider", return_value=MagicMock()),
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
    """llm 미주입 → substring 콜드 스타트 폴백(D1) + 랭킹 피처 결합, RPC 미호출 (AC-A2, AC6)."""
    profile = {"tech_stack": ["LangGraph"], "interests": []}
    client = MagicMock()
    scored = _order([_SIG], profile, "u", client, "d", None, None)
    # v2: base=substring 폴백, combined = 0.7*base + 0.15*0.5(중립 recency)
    assert scored[0][1] == pytest.approx(_combine_neutral(_base_boosted(_SIG, profile)))
    client.rpc.assert_not_called()


def test_score_signals_coldstart_when_no_memories():
    """memory 미보유 → 콜드 스타트(RAG 블렌드 없음) + 랭킹 피처, RPC 미호출 (AC-A2)."""
    profile = {"tech_stack": ["LangGraph"], "interests": []}
    client = _rag_score_client(memory_count=0)
    # MagicMock llm은 embed_text 미설정 → 프로필 임베딩 norm 0 → base=substring 폴백(AD-5)
    scored = _order([_SIG], profile, "u", client, "d", MagicMock(), _EMB)
    assert scored[0][1] == pytest.approx(_combine_neutral(_base_boosted(_SIG, profile)))
    client.rpc.assert_not_called()


def test_score_signals_rag_boosts_over_coldstart():
    """memory 보유 → (base + _RAG_WEIGHT*top_sim) 블렌드 후 랭킹 피처 결합 (AC-A1, AC5)."""
    profile = {}  # base = 0.1 (빈 프로필 → substring 0.1)
    client = _rag_score_client(memory_count=2, similarity=0.8)
    scored = _order([_SIG], profile, "u", client, "d", MagicMock(), _EMB)
    blended = 0.1 + _RAG_WEIGHT * 0.8  # 0.5
    assert scored[0][1] == pytest.approx(_combine_neutral(blended))
    client.rpc.assert_called_once()


def test_score_signals_clamped_to_one():
    """블렌딩(base+RAG)이 상한 1.0으로 clamp되고 최종 combined도 [0.1,1.0] 유지 (불변식, AC-A3)."""
    sig = {"id": "sig-1", "technology_name": "langgraph mcp agent rag",
           "title": "t", "summary": "langgraph mcp agent rag"}
    profile = {"tech_stack": ["langgraph", "mcp", "agent", "rag"],
               "interests": ["langgraph", "mcp", "agent"]}  # substring base = 1.0
    client = _rag_score_client(memory_count=1, similarity=0.9)
    scored = _order([sig], profile, "u", client, "d", MagicMock(), {"sig-1": [0.01] * 1536})
    # blended = clamp(1.0 + 0.5*0.9) = 1.0 → combined = 0.7*1.0 + 0.075 = 0.775
    assert scored[0][1] == pytest.approx(_combine_neutral(1.0))
    assert 0.1 <= scored[0][1] <= 1.0  # 불변식


def test_score_signals_rpc_error_falls_back_to_base():
    """match_memories RPC 예외 → 해당 Signal base로 폴백 후 랭킹 피처 결합 (AC-A2, AD-5)."""
    client = _rag_score_client(memory_count=1, rpc_error=True)
    scored = _order([_SIG], {}, "u", client, "d", MagicMock(), _EMB)
    assert scored[0][1] == pytest.approx(_combine_neutral(0.1))  # base=0.1 폴백


def test_score_signals_missing_embedding_uses_base():
    """임베딩 누락 Signal(임베딩 실패분) → base 점수, RPC 미호출."""
    client = _rag_score_client(memory_count=1, similarity=0.9)
    scored = _order([_SIG], {}, "u", client, "d", MagicMock(), {})  # 임베딩 없음
    assert scored[0][1] == pytest.approx(_combine_neutral(0.1))
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
    scored = _order(sigs, {}, "u", MagicMock(), "d", None, None)
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
    # v2: RAG 블렌드(0.1 + 0.5*0.8=0.5) 후 랭킹 피처 결합
    assert inserted[0]["relevance_score"] == pytest.approx(_combine_neutral(0.1 + _RAG_WEIGHT * 0.8))


def test_brief_creation_continues_when_rpc_fails():
    """RPC 실패해도 brief 생성이 중단되지 않고 콜드 스타트 점수로 완료 (AC-A2, AD-5)."""
    client = _make_brief_mock_client(memory_count=1, rpc_error=True)
    brief_id = create_daily_brief_for_user(
        "user-1", ["sig-1"], client, "2026-07-24", MagicMock(), {"sig-1": [0.01] * 1536}
    )
    assert brief_id == "brief-uuid"  # 생성 지속
    inserted = client._daily_brief_signals.insert.call_args[0][0]
    assert inserted[0]["relevance_score"] == pytest.approx(_combine_neutral(0.1))  # base 폴백


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


# ══════════════════════════════════════════════════════════════════════════════
# Story 6.4 — Recommender v2: 코사인 콜드 스타트 + 랭킹 피처 + MMR + RAG 대칭
# ══════════════════════════════════════════════════════════════════════════════

def _llm_with_embeddings(mapping, default=None):
    """embed_text(text) -> vector 매핑 llm mock (프로필 텍스트 임베딩 제어용).

    코사인 검증은 실 네트워크 없이 알려진 벡터로 결정적(오프라인 원칙). mapping에 없으면 default,
    default도 None이면 예외(임베딩 실패 경로 검증용).
    """
    llm = MagicMock()

    def _embed(text):
        if text in mapping:
            return mapping[text]
        if default is not None:
            return default
        raise KeyError(f"no embedding for {text!r}")

    llm.embed_text.side_effect = _embed
    return llm


# ── 순수 헬퍼: recency / popularity / authority / cosine / MMR ──

def test_recency_norm_none_is_neutral():
    assert _recency_norm(None, "2026-07-24") == 0.5


def test_recency_norm_recent_higher_than_old():
    ref = "2026-07-24"
    recent = _recency_norm("2026-07-24T00:00:00+00:00", ref)
    old = _recency_norm("2026-07-10T00:00:00+00:00", ref)
    assert recent > old
    assert recent == pytest.approx(1.0)  # age 0 → 0.5**0 = 1.0


def test_recency_norm_future_is_capped_to_one():
    """미래 timestamp(age<0) → 1.0 캡 (D5)."""
    assert _recency_norm("2026-08-01T00:00:00Z", "2026-07-24") == 1.0


def test_recency_norm_bad_input_is_neutral():
    """파싱 실패 → 중립 0.5 (D5 방어)."""
    assert _recency_norm("not-a-date", "2026-07-24") == 0.5


def test_recency_norm_naive_datetime_handled():
    """naive datetime 문자열도 UTC로 간주해 파싱(예외 없음)."""
    assert 0.0 <= _recency_norm("2026-07-20T00:00:00", "2026-07-24") <= 1.0


def test_popularity_norm():
    assert _popularity_norm(0, 5.0) == 0.0          # 인기 0
    assert _popularity_norm(100, 0.0) == 0.0        # batch_max 0
    assert _popularity_norm(None, 5.0) == 0.0       # None
    assert _popularity_norm(100, math.log1p(100)) == pytest.approx(1.0)  # 배치 최대


def test_authority_norm():
    assert _authority_norm(None) == 0.0
    assert _authority_norm(4) == 1.0
    assert _authority_norm(2) == 0.5
    assert _authority_norm(8) == 1.0  # 상한 캡


def test_compute_relevance_score_v2_cosine_bounds():
    """동일 벡터 → 1.0, 직교 → clamp 0.1 (AC1)."""
    assert compute_relevance_score_v2([1.0, 0.0], 1.0, [1.0, 0.0], 1.0) == 1.0
    assert compute_relevance_score_v2([1.0, 0.0], 1.0, [0.0, 1.0], 1.0) == 0.1


def test_mmr_rerank_deterministic_tiebreak():
    """동점 mmr → signal_id 오름차순 (AC3 결정론)."""
    items = [("b", 0.5, [1.0, 0.0], 1.0), ("a", 0.5, [1.0, 0.0], 1.0)]
    order = [x[0] for x in _mmr_rerank(items, 0.7)]
    assert order == ["a", "b"]


# ── 콜드 스타트 코사인 순위 + go→google 오매칭 회귀 (AC1) ──

def test_coldstart_cosine_ranks_semantically_near_higher():
    """프로필과 의미 가까운(코사인↑) 시그널이 먼 시그널보다 상위 (AC1)."""
    profile = {"tech_stack": ["go"], "interests": []}  # profile text = "go"
    near = {"id": "near", "technology_name": "Golang", "title": "t", "summary": "s"}
    far = {"id": "far", "technology_name": "Cooking", "title": "t", "summary": "s"}
    embs = {"near": [1.0, 0.0], "far": [0.0, 1.0]}     # near = 프로필 방향, far = 직교
    llm = _llm_with_embeddings({"go": [1.0, 0.0]})
    client = _rag_score_client(memory_count=0)
    scored = _order([far, near], profile, "u", client, "d", llm, embs)
    assert [s[0] for s in scored][0] == "near"


def test_coldstart_no_substring_pullup_go_google():
    """substring이었으면 'go' in 'google' 로 끌어올려졌을 무관 시그널이 코사인에선 안 올라감 (AC1 핵심 회귀)."""
    profile = {"tech_stack": ["go"], "interests": []}
    google = {"id": "google", "technology_name": "Google", "title": "Google announces X", "summary": "cloud"}
    relevant = {"id": "relevant", "technology_name": "Golang", "title": "Go 1.22", "summary": "go release"}
    embs = {"relevant": [1.0, 0.0], "google": [0.0, 1.0]}  # google 무관(직교)
    llm = _llm_with_embeddings({"go": [1.0, 0.0]})
    client = _rag_score_client(memory_count=0)
    scored = dict(_order([google, relevant], profile, "u", client, "d", llm, embs))
    assert scored["relevant"] > scored["google"]
    # 무관 google은 base 코사인 0 → clamp 0.1 → combined = neutral(0.1) (끌어올림 없음)
    assert scored["google"] == pytest.approx(_combine_neutral(0.1))


def test_v2_invariant_and_deterministic_tiebreak():
    """모든 combined ∈ [0.1,1.0]; 동점 입력 → signal_id 오름차순 (AC1/AC3)."""
    sigs = [
        {"id": "sig-b", "technology_name": "X", "title": "t", "summary": "s"},
        {"id": "sig-a", "technology_name": "X", "title": "t", "summary": "s"},
    ]
    embs = {"sig-a": [1.0, 0.0], "sig-b": [1.0, 0.0]}  # 동일 → 동점
    llm = _llm_with_embeddings({}, default=[1.0, 0.0])
    client = _rag_score_client(memory_count=0)
    scored = _order(sigs, {"tech_stack": ["z"]}, "u", client, "d", llm, embs)
    for _sid, sc in scored:
        assert 0.1 <= sc <= 1.0
    assert [s[0] for s in scored] == ["sig-a", "sig-b"]


# ── 랭킹 피처: 최신성 · 인기 · 권위 (AC2) ──

def test_ranking_recency_boosts_recent_signal():
    """동일 base에서 최신(published_at 최근) 시그널이 상위, 오래된 것은 하위 (AC2)."""
    recent = {"id": "recent", "technology_name": "X", "title": "t", "summary": "s",
              "published_at": "2026-07-24T00:00:00+00:00"}
    old = {"id": "old", "technology_name": "X", "title": "t", "summary": "s",
           "published_at": "2026-06-24T00:00:00+00:00"}
    embs = {"recent": [1.0, 0.0], "old": [1.0, 0.0]}
    llm = _llm_with_embeddings({}, default=[1.0, 0.0])
    client = _rag_score_client(memory_count=0)
    scored = dict(_order([old, recent], {"tech_stack": ["z"]}, "u", client, "2026-07-24", llm, embs))
    assert scored["recent"] > scored["old"]


def test_ranking_popularity_and_authority_boost():
    """동일 base·최신성에서 고인기·고권위 시그널이 상위, metadata 없는 건 중립 (AC2)."""
    pop = {"id": "pop", "technology_name": "X", "title": "t", "summary": "s", "popularity": 1000}
    auth = {"id": "auth", "technology_name": "X", "title": "t", "summary": "s", "source_authority": 4}
    plain = {"id": "plain", "technology_name": "X", "title": "t", "summary": "s"}  # metadata 없음 → 중립
    embs = {"pop": [1.0, 0.0], "auth": [1.0, 0.0], "plain": [1.0, 0.0]}
    llm = _llm_with_embeddings({}, default=[1.0, 0.0])
    client = _rag_score_client(memory_count=0)
    scored = dict(_order([plain, pop, auth], {"tech_stack": ["z"]}, "u", client, "d", llm, embs))
    assert scored["pop"] > scored["plain"]
    assert scored["auth"] > scored["plain"]


def test_published_at_none_is_neutral_not_penalized():
    """published_at NULL 시그널은 최신성 페널티 없이 중립(recency 0.5) 처리 (AC2, AD-5)."""
    no_date = {"id": "no_date", "technology_name": "X", "title": "t", "summary": "s"}  # published_at 없음
    embs = {"no_date": [1.0, 0.0]}
    llm = _llm_with_embeddings({}, default=[1.0, 0.0])
    client = _rag_score_client(memory_count=0)
    scored = dict(_order([no_date], {"tech_stack": ["z"]}, "u", client, "d", llm, embs))
    # base 코사인 1.0 → combined = 0.7*1.0 + 0.15*0.5(중립) = 0.775
    assert scored["no_date"] == pytest.approx(_combine_neutral(1.0))


# ── MMR 다양성 (AC3) ──

def test_mmr_disperses_similar_and_keeps_no_embedding_signal():
    """유사 임베딩이 상위에 몰리지 않고 분산; 임베딩 없는 시그널은 탈락하지 않고 순서만 뒤로 (AC3, AD-5)."""
    # profile [1,1] 기준 a,b,c(=[1,0])와 d(=[0,1])는 관련도 동일하나 서로 직교(주제 다름)
    a = {"id": "a", "technology_name": "X", "title": "t", "summary": "s"}
    b = {"id": "b", "technology_name": "X", "title": "t", "summary": "s"}
    c = {"id": "c", "technology_name": "X", "title": "t", "summary": "s"}
    d = {"id": "d", "technology_name": "Y", "title": "t", "summary": "s"}
    e = {"id": "e", "technology_name": "NoEmb", "title": "t", "summary": "s"}  # 임베딩 없음
    embs = {"a": [1.0, 0.0], "b": [1.0, 0.0], "c": [1.0, 0.0], "d": [0.0, 1.0]}  # e 없음
    llm = _llm_with_embeddings({}, default=[1.0, 1.0])  # profile 벡터 [1,1]
    client = _rag_score_client(memory_count=0)
    scored = _order([a, b, c, d, e], {"tech_stack": ["z"]}, "u", client, "d", llm, embs)
    order = [s[0] for s in scored]
    # MMR: a 선택 후 b,c는 중복 페널티 → 직교인 d가 위로 분산 (2번째 안에 진입)
    assert order.index("d") < order.index("c")
    # 임베딩 없는 e도 탈락하지 않음
    assert "e" in order
    assert len(order) == 5


# ── RAG 대칭화: _signal_embed_text summary 중심 (AC4) ──

def test_signal_embed_text_is_summary_centric():
    """AC4: summary 중심(memory 문서 임베딩과 대칭), 없으면 title 폴백, 둘 다 없으면 빈 문자열."""
    assert _signal_embed_text({"technology_name": "X", "title": "T", "summary": "S"}) == "S"
    assert _signal_embed_text({"technology_name": "X", "title": "T", "summary": None}) == "T"
    assert _signal_embed_text({"technology_name": "X", "title": None, "summary": None}) == ""


# ── AD-5: 프로필 임베딩 실패 → substring 폴백 (AC6) ──

def test_profile_embed_failure_falls_back_to_substring():
    """프로필 임베딩 실패 → 예외 없이 substring base 폴백 후 랭킹 피처 결합 (AC6, AD-5)."""
    profile = {"tech_stack": ["LangGraph"]}
    llm = MagicMock()
    llm.embed_text.side_effect = RuntimeError("profile embed boom")
    client = _rag_score_client(memory_count=0)
    scored = _order([_SIG], profile, "u", client, "d", llm, _EMB)
    assert scored[0][1] == pytest.approx(_combine_neutral(_base_boosted(_SIG, profile)))


def test_rag_symmetry_uses_summary_query_and_single_embedding():
    """AC4: memory 보유 경로에서도 시그널 임베딩(summary 기반)을 콜드 스타트·RAG query가 공유(1회 임베딩)."""
    sig = {"id": "sig-1", "technology_name": "X", "title": "T", "summary": "vector db tuning"}
    llm = MagicMock()
    llm.embed_text.return_value = [1.0, 0.0]
    # signal_embeddings=None → _score_signals가 _embed_signal_list로 1회 임베딩
    client = _rag_score_client(memory_count=1, similarity=0.5)
    _score_signals([sig], {}, "u", client, "d", llm, None)
    # 시그널 임베딩 텍스트가 summary("vector db tuning")로 호출됨 (title/tech 아님)
    embed_texts = [c.args[0] for c in llm.embed_text.call_args_list]
    assert "vector db tuning" in embed_texts


# ══════════════════════════════════════════════════════════════════════════════
# Story 6.5 — variant 반환 + 서버 impression 로깅 정본
# ══════════════════════════════════════════════════════════════════════════════

def test_score_signals_variant_coldstart_when_no_llm():
    """llm 미주입 → variant='coldstart' (memory 분기 미실행)."""
    _ordered, variant = _score_signals([_SIG], {"tech_stack": ["z"]}, "u", MagicMock(), "d", None, None)
    assert variant == "coldstart"


def test_score_signals_variant_coldstart_when_no_memory():
    """memory 미보유 → variant='coldstart' (memory_rag_coldstart 경로)."""
    client = _rag_score_client(memory_count=0)
    _ordered, variant = _score_signals([_SIG], {}, "u", client, "d", MagicMock(), _EMB)
    assert variant == "coldstart"


def test_score_signals_variant_rag_when_memory_applied():
    """memory 보유 + RAG 적용 → variant='rag' (memory_rag_applied 경로와 동일 분기)."""
    client = _rag_score_client(memory_count=2, similarity=0.8)
    _ordered, variant = _score_signals([_SIG], {}, "u", client, "d", MagicMock(), _EMB)
    assert variant == "rag"


def test_score_signals_variant_rag_even_if_per_signal_rpc_fails():
    """per-signal RPC 실패(continue 폴백)여도 memory 보유 코호트이므로 variant='rag'.

    pipeline_log가 이 경로에서 memory_rag_applied를 남기므로(스토리 규칙: variant는 로그와 일치),
    variant도 rag로 유지된다. 개별 시그널 점수는 base로 폴백되지만 코호트 라벨은 rag.
    """
    client = _rag_score_client(memory_count=1, rpc_error=True)
    _ordered, variant = _score_signals([_SIG], {}, "u", client, "d", MagicMock(), _EMB)
    assert variant == "rag"


def test_score_signals_variant_coldstart_when_memory_check_raises():
    """memory 존재 확인 쿼리 자체가 실패(outer except) → memory_rag_coldstart → variant='coldstart'."""
    client = MagicMock()
    # memories.select(...).eq(...).limit(...).execute() 가 예외 → outer except 진입
    client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = (
        RuntimeError("memories check boom")
    )
    _ordered, variant = _score_signals([_SIG], {}, "u", client, "d", MagicMock(), _EMB)
    assert variant == "coldstart"


def test_brief_logs_server_impressions_with_variant():
    """create_daily_brief_for_user가 brief 시그널마다 impression 이벤트를 variant/position/score와 로깅."""
    client = _make_brief_mock_client(memory_count=1, rpc_similarity=0.8)
    with patch("pipeline.recommender.log_engagement_bulk") as mock_bulk:
        brief_id = create_daily_brief_for_user(
            "user-1", ["sig-1"], client, "2026-07-24", MagicMock(), {"sig-1": [0.01] * 1536}
        )
    assert brief_id == "brief-uuid"
    mock_bulk.assert_called_once()
    rows = mock_bulk.call_args[0][1]
    assert rows[0]["event_type"] == "impression"
    assert rows[0]["variant"] == "rag"  # memory 보유 → rag 코호트
    assert rows[0]["signal_id"] == "sig-1"
    assert rows[0]["daily_brief_id"] == "brief-uuid"
    assert rows[0]["metadata"]["position"] == 1
    assert "relevance_score" in rows[0]["metadata"]


def test_brief_impressions_coldstart_variant_when_no_memory():
    """memory 미보유 brief → impression variant='coldstart'."""
    client = _make_brief_mock_client(memory_count=0)
    with patch("pipeline.recommender.log_engagement_bulk") as mock_bulk:
        create_daily_brief_for_user(
            "user-1", ["sig-1"], client, "2026-07-24", MagicMock(), {"sig-1": [0.01] * 1536}
        )
    rows = mock_bulk.call_args[0][1]
    assert rows[0]["variant"] == "coldstart"


def test_brief_completes_when_impression_logging_raises():
    """impression 로깅이 예외를 던져도 brief는 completed로 진행(best-effort 이중 보증, AD-5)."""
    client = _make_brief_mock_client()
    with patch("pipeline.recommender.log_engagement_bulk", side_effect=RuntimeError("log boom")):
        brief_id = create_daily_brief_for_user("user-1", ["sig-1"], client, "2026-07-24")
    assert brief_id == "brief-uuid"  # 로깅 실패에도 생성 완료
    last_update = client._daily_briefs.update.call_args_list[-1][0][0]
    assert last_update["status"] == "completed"


def test_run_daily_pipeline_skips_review_when_pregeneration_off():
    """review_pregeneration_enabled=False면 배치가 step5(review_all_for_signal)를 건너뛴다."""
    import pipeline.orchestrator
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
        patch("pipeline.orchestrator.settings.collector_mode", "stub"),
        patch("pipeline.orchestrator.settings.review_pregeneration_enabled", False),
        patch("pipeline.orchestrator.StubCollector.collect", mock_collect),
        patch("pipeline.orchestrator.normalize", mock_normalize),
        patch("pipeline.orchestrator.build_signals", mock_build),
        patch("pipeline.orchestrator.review_all_for_signal", mock_review),
        patch("pipeline.orchestrator.run_recommender", mock_recommend),
        patch("pipeline.orchestrator.get_supabase", return_value=MagicMock()),
        patch("pipeline.orchestrator.get_llm_provider", return_value=MagicMock()),
    ):
        result = pipeline.orchestrator.run_daily_pipeline("2026-07-24")

    assert "review" not in call_order
    assert call_order == ["collect", "normalize", "build", "recommend"]
    assert result["error"] is None
    assert result["briefs"] == 1


# ─── _lexical_boost (하이브리드 관련도 가점) ──────────────────────────────────────

def test_lexical_boost_stack_match_beats_no_match():
    from pipeline.recommender import _lexical_boost
    sig_match = {"technology_name": "LangGraph 1.2", "title": "", "summary": "release"}
    sig_none = {"technology_name": "Mermaid editor", "title": "", "summary": "diagrams"}
    user = {"tech_stack": ["LangGraph"], "interests": []}
    assert _lexical_boost(sig_match, user) > _lexical_boost(sig_none, user)
    assert _lexical_boost(sig_none, user) == 0.0


def test_lexical_boost_go_does_not_match_google():
    from pipeline.recommender import _lexical_boost
    sig = {"technology_name": "Google AI", "title": "", "summary": "google blog"}
    user = {"tech_stack": ["Go"], "interests": []}
    assert _lexical_boost(sig, user) == 0.0


def test_lexical_boost_interest_match():
    from pipeline.recommender import _lexical_boost, _INTEREST_BOOST
    sig = {"technology_name": "RAG pipeline", "title": "", "summary": "retrieval"}
    user = {"tech_stack": [], "interests": ["RAG"]}
    assert _lexical_boost(sig, user) == _INTEREST_BOOST


def test_lexical_boost_multitoken_requires_all_tokens():
    from pipeline.recommender import _lexical_boost
    sig_partial = {"technology_name": "llama release", "title": "", "summary": ""}
    sig_full = {"technology_name": "llama index update", "title": "", "summary": ""}
    user = {"tech_stack": ["llama index"], "interests": []}
    assert _lexical_boost(sig_partial, user) == 0.0
    assert _lexical_boost(sig_full, user) > 0.0


def test_lexical_boost_capped():
    from pipeline.recommender import _lexical_boost, _LEXICAL_BOOST_CAP
    sig = {"technology_name": "python fastapi nextjs rag agent", "title": "", "summary": ""}
    user = {"tech_stack": ["python", "fastapi", "nextjs"], "interests": ["rag", "agent"]}
    # 3*0.3 + 2*0.2 = 1.3 → cap 0.6
    assert _lexical_boost(sig, user) == _LEXICAL_BOOST_CAP


def test_lexical_boost_empty_profile():
    from pipeline.recommender import _lexical_boost
    sig = {"technology_name": "LangGraph", "title": "", "summary": ""}
    assert _lexical_boost(sig, {"tech_stack": [], "interests": []}) == 0.0


def test_score_signals_applies_lexical_boost(monkeypatch):
    """base를 평탄화(0.1)해도 스택 매칭 시그널이 lexical_boost로 1위가 된다.
    match 시그널 id를 정렬상 뒤(sig-b)로 둬, 가점 없으면 tie-break(signal_id 오름차순)로
    non-match(sig-a)가 1위가 되도록 → RED가 확실히 실패하게 설계."""
    import pipeline.recommender as rec
    monkeypatch.setattr(rec, "compute_relevance_score", lambda sig, prof: 0.1)
    signals = [
        {"id": "sig-a", "technology_name": "Mermaid editor", "title": "", "summary": "diagrams",
         "popularity": 0, "source_authority": 0, "published_at": None},
        {"id": "sig-b", "technology_name": "LangGraph release", "title": "", "summary": "x",
         "popularity": 0, "source_authority": 0, "published_at": None},
    ]
    user = {"tech_stack": ["LangGraph"], "interests": []}
    ordered, _variant = rec._score_signals(
        signals, user, "u1", MagicMock(), "2026-08-19", llm=None, signal_embeddings=None
    )
    assert ordered[0][0] == "sig-b"
