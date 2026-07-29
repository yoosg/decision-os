"""Signal Builder & Reviewer Agent 단위 테스트 (Story 2.2).

Supabase·OpenAI Mock으로 실행 가능 — 환경변수 불필요.
"""
import json
from unittest.mock import MagicMock, patch  # noqa: F401  patch은 openai_provider 테스트에서 사용

import pytest

from pipeline.llm.base import LLMProvider, LLMProviderError, ReviewContext
from pipeline.llm.openai_provider import OpenAIProvider
from pipeline.reviewer import review_all_for_signal, review_signal
from pipeline.signal_builder import build_signals
from tests.mocks import VALID_13_SECTION_RESPONSE, MockLLMProvider


# ─── Mock 헬퍼 ──────────────────────────────────────────────────────────────────

def _make_builder_mock_client(
    signal_data: dict | None = None,
    sources: list | None = None,
    update_data: list | None = None,
):
    """Signal Builder 테스트용 Supabase Client 목.

    반환된 mock_client._signals_mock, _sources_mock 로 해당 테이블 mock에 직접 접근 가능.
    """
    if signal_data is None:
        signal_data = {
            "id": "sig-uuid",
            "technology_name": "LangGraph",
            "title": "임시 제목",
            "status": "raw",
        }
    if sources is None:
        sources = [{"source_type": "official_blog", "url": "https://example.com", "title": "Blog"}]
    if update_data is None:
        update_data = [{"id": "sig-uuid"}]

    signals_t = MagicMock()
    signals_t.select.return_value.eq.return_value.execute.return_value.data = [signal_data]
    signals_t.update.return_value.eq.return_value.execute.return_value.data = update_data

    sources_t = MagicMock()
    sources_t.select.return_value.eq.return_value.execute.return_value.data = sources

    table_map = {
        "signals": signals_t,
        "signal_sources": sources_t,
    }

    mock_client = MagicMock()
    mock_client.table.side_effect = lambda name: table_map.get(name, MagicMock())
    mock_client._signals_mock = signals_t
    mock_client._sources_mock = sources_t
    return mock_client


def _make_reviewer_mock_client(
    review_id: str = "rev-uuid",
    signal_data: dict | None = None,
    sources: list | None = None,
    project_user_id: str = "user-uuid",
    profile: dict | None = None,
    insert_returns_data: bool = True,
):
    """Reviewer 테스트용 Supabase Client 목.

    반환된 mock_client._reviews_mock 으로 reviews 테이블 mock에 직접 접근 가능.
    """
    if signal_data is None:
        signal_data = {
            "id": "sig-uuid",
            "technology_name": "LangGraph",
            "title": "LangGraph 기본",
            "summary": None,
            "signal_date": "2026-07-24",
            "status": "processed",
        }
    if sources is None:
        sources = [{"source_type": "official_blog", "url": "https://example.com", "title": "LangGraph Blog"}]
    if profile is None:
        profile = [{"role": "developer", "tech_stack": ["Python"], "interests": ["AI"], "experience_level": "intermediate"}]

    reviews_t = MagicMock()
    if insert_returns_data:
        reviews_t.insert.return_value.execute.return_value.data = [{"id": review_id}]
    else:
        reviews_t.insert.return_value.execute.return_value.data = []
    reviews_t.update.return_value.eq.return_value.execute.return_value.data = [{"id": review_id}]

    signals_t = MagicMock()
    signals_t.select.return_value.eq.return_value.execute.return_value.data = [signal_data]

    sources_t = MagicMock()
    sources_t.select.return_value.eq.return_value.execute.return_value.data = sources

    projects_t = MagicMock()
    projects_t.select.return_value.eq.return_value.execute.return_value.data = [{"user_id": project_user_id}]

    profiles_t = MagicMock()
    profiles_t.select.return_value.eq.return_value.execute.return_value.data = profile

    table_map = {
        "reviews": reviews_t,
        "signals": signals_t,
        "signal_sources": sources_t,
        "projects": projects_t,
        "user_profiles": profiles_t,
    }

    mock_client = MagicMock()
    mock_client.table.side_effect = lambda name: table_map.get(name, MagicMock())
    mock_client._reviews_mock = reviews_t
    return mock_client


# ─── 5.2 Signal Builder: LLM Mock으로 status='processed' 업데이트 검증 ──────────

def test_signal_builder_updates_status_to_processed():
    """build_signals()가 raw signal의 status를 'processed'로 업데이트한다."""
    mock_client = _make_builder_mock_client()
    signal_content = json.dumps({"title": "LangGraph 통합", "summary": "요약 내용"})
    llm = MockLLMProvider(signal_content=signal_content)

    result = build_signals(["sig-uuid"], mock_client, llm=llm, brief_date="2026-07-24")

    assert result == ["sig-uuid"]
    assert len(llm.build_signal_calls) == 1
    mock_client._signals_mock.update.assert_called_once()
    update_payload = mock_client._signals_mock.update.call_args[0][0]
    assert update_payload["status"] == "processed"
    assert update_payload["title"] == "LangGraph 통합"
    assert update_payload["summary"] == "요약 내용"


# ─── 5.3 Signal Builder: status='raw' 아닌 signal_id 스킵 검증 ─────────────────

def test_signal_builder_skips_non_raw_signal():
    """build_signals()가 raw 상태가 아닌 signal을 스킵한다."""
    signal_data = {
        "id": "sig-uuid",
        "technology_name": "LangGraph",
        "title": "기존 제목",
        "status": "processed",
    }
    mock_client = _make_builder_mock_client(signal_data=signal_data)
    llm = MockLLMProvider()

    result = build_signals(["sig-uuid"], mock_client, llm=llm, brief_date="2026-07-24")

    assert result == []
    assert len(llm.build_signal_calls) == 0


# ─── 5.4 LLMProvider 인터페이스: 추상 메서드 generate() 존재 검증 ───────────────

def test_llm_provider_is_abstract():
    """LLMProvider는 abstract class로 직접 인스턴스화 불가."""
    with pytest.raises(TypeError):
        LLMProvider()


def test_llm_provider_has_abstract_generate():
    """LLMProvider에 generate() 추상 메서드가 존재한다."""
    assert hasattr(LLMProvider, "generate")
    assert getattr(LLMProvider.generate, "__isabstractmethod__", False)


def test_llm_provider_has_abstract_build_signal_title_summary():
    """LLMProvider에 build_signal_title_summary() 추상 메서드가 존재한다."""
    assert hasattr(LLMProvider, "build_signal_title_summary")
    assert getattr(LLMProvider.build_signal_title_summary, "__isabstractmethod__", False)


# ─── 5.5 OpenAIProvider: client.responses.create() 호출 검증 ───────────────────

def test_openai_provider_calls_responses_create():
    """OpenAIProvider.generate()가 client.responses.create()를 호출한다."""
    fake_response = MagicMock()
    fake_response.output_text = VALID_13_SECTION_RESPONSE

    with patch("pipeline.llm.openai_provider.OpenAI") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        mock_instance.responses.create.return_value = fake_response

        provider = OpenAIProvider(api_key="test-key", model="gpt-4o")
        context = ReviewContext(
            technology_name="LangGraph",
            signal_sources=[{"source_type": "blog", "url": "https://a.com", "title": "Blog"}],
        )
        result = provider.generate(context)

    mock_instance.responses.create.assert_called_once()
    call_kwargs = mock_instance.responses.create.call_args[1]
    assert call_kwargs["model"] == "gpt-4o"
    assert "input" in call_kwargs
    assert "instructions" in call_kwargs
    assert call_kwargs["text"] == {"format": {"type": "json_object"}}
    assert result.model == "gpt-4o"


def test_openai_provider_does_not_use_chat_completions():
    """OpenAIProvider가 chat.completions를 사용하지 않는다."""
    fake_response = MagicMock()
    fake_response.output_text = VALID_13_SECTION_RESPONSE

    with patch("pipeline.llm.openai_provider.OpenAI") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        mock_instance.responses.create.return_value = fake_response

        provider = OpenAIProvider(api_key="test-key")
        context = ReviewContext(technology_name="X", signal_sources=[])
        provider.generate(context)

    mock_instance.chat.completions.create.assert_not_called()


# ─── 5.6 OpenAIProvider: 예외 발생 시 LLMProviderError 래핑 검증 ────────────────

def test_openai_provider_wraps_openai_error():
    """OpenAI 예외가 LLMProviderError로 래핑된다."""
    from openai import OpenAIError

    with patch("pipeline.llm.openai_provider.OpenAI") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        mock_instance.responses.create.side_effect = OpenAIError("API error")

        provider = OpenAIProvider(api_key="test-key")
        context = ReviewContext(technology_name="X", signal_sources=[])

        with pytest.raises(LLMProviderError):
            provider.generate(context)


# ─── 5.7 Reviewer: review_signal() → reviews INSERT pending 검증 ────────────────

def test_reviewer_inserts_pending_review():
    """review_signal()이 reviews 테이블에 pending 상태로 INSERT한다."""
    mock_client = _make_reviewer_mock_client()
    llm = MockLLMProvider()

    result = review_signal("sig-uuid", "proj-uuid", mock_client, llm, brief_date="2026-07-24")

    assert result == "rev-uuid"
    mock_client._reviews_mock.insert.assert_called_once()
    insert_payload = mock_client._reviews_mock.insert.call_args[0][0]
    assert insert_payload["status"] == "pending"
    assert insert_payload["playbook_type"] == "ai_research"
    assert insert_payload["review_type"] == "research"
    assert insert_payload["signal_id"] == "sig-uuid"
    assert insert_payload["project_id"] == "proj-uuid"


# ─── 5.8 Reviewer: 상태 전이 pending → processing → completed 검증 ──────────────

def test_reviewer_state_transition_to_completed():
    """review_signal()이 pending → processing → completed 상태 전이를 수행한다."""
    update_calls = []

    reviews_t = MagicMock()
    reviews_t.insert.return_value.execute.return_value.data = [{"id": "rev-uuid"}]

    def update_side_effect(data):
        update_calls.append(data)
        m = MagicMock()
        m.eq.return_value.execute.return_value.data = [{"id": "rev-uuid"}]
        return m

    reviews_t.update.side_effect = update_side_effect

    signal_t = MagicMock()
    signal_t.select.return_value.eq.return_value.execute.return_value.data = [{
        "id": "sig-uuid", "technology_name": "LangGraph",
        "title": "제목", "summary": None, "signal_date": "2026-07-24",
    }]
    sources_t = MagicMock()
    sources_t.select.return_value.eq.return_value.execute.return_value.data = []
    projects_t = MagicMock()
    projects_t.select.return_value.eq.return_value.execute.return_value.data = [{"user_id": "user-uuid"}]
    profiles_t = MagicMock()
    profiles_t.select.return_value.eq.return_value.execute.return_value.data = []

    table_map = {
        "reviews": reviews_t, "signals": signal_t,
        "signal_sources": sources_t, "projects": projects_t, "user_profiles": profiles_t,
    }
    mock_client = MagicMock()
    mock_client.table.side_effect = lambda name: table_map.get(name, MagicMock())

    result = review_signal("sig-uuid", "proj-uuid", mock_client, MockLLMProvider(), brief_date="2026-07-24")

    assert result == "rev-uuid"
    statuses = [c.get("status") for c in update_calls if "status" in c]
    assert "processing" in statuses
    assert "completed" in statuses
    assert statuses.index("completed") > statuses.index("processing")


# ─── 5.9 Reviewer: LLM 실패 시 status='failed', error_message 저장 검증 ─────────

def test_reviewer_on_llm_failure_sets_failed_status():
    """LLM 실패 시 status='failed'와 error_message가 저장된다."""
    failed_updates = []

    reviews_t = MagicMock()
    reviews_t.insert.return_value.execute.return_value.data = [{"id": "rev-uuid"}]

    def update_side_effect(data):
        failed_updates.append(data)
        m = MagicMock()
        m.eq.return_value.execute.return_value.data = [{"id": "rev-uuid"}]
        return m

    reviews_t.update.side_effect = update_side_effect

    signal_t = MagicMock()
    signal_t.select.return_value.eq.return_value.execute.return_value.data = [{
        "id": "sig-uuid", "technology_name": "LangGraph",
        "title": "제목", "summary": None, "signal_date": "2026-07-24",
    }]
    sources_t = MagicMock()
    sources_t.select.return_value.eq.return_value.execute.return_value.data = []
    projects_t = MagicMock()
    projects_t.select.return_value.eq.return_value.execute.return_value.data = [{"user_id": "user-uuid"}]
    profiles_t = MagicMock()
    profiles_t.select.return_value.eq.return_value.execute.return_value.data = []

    table_map = {
        "reviews": reviews_t, "signals": signal_t,
        "signal_sources": sources_t, "projects": projects_t, "user_profiles": profiles_t,
    }
    mock_client = MagicMock()
    mock_client.table.side_effect = lambda name: table_map.get(name, MagicMock())

    result = review_signal("sig-uuid", "proj-uuid", mock_client, MockLLMProvider(raise_error=True), brief_date="2026-07-24")

    assert result is None
    failed_update = next((u for u in failed_updates if u.get("status") == "failed"), None)
    assert failed_update is not None
    assert "error_message" in failed_update
    assert "mock LLM error" in failed_update["error_message"]


# ─── 5.10 Reviewer: result JSONB 봉투 구조 검증 ────────────────────────────────

def test_reviewer_result_jsonb_envelope():
    """result JSONB가 schema_version, review_type, payload 봉투를 갖는다."""
    saved_result = {}

    reviews_t = MagicMock()
    reviews_t.insert.return_value.execute.return_value.data = [{"id": "rev-uuid"}]

    def update_side_effect(data):
        if "result" in data:
            saved_result.update(data["result"])
        m = MagicMock()
        m.eq.return_value.execute.return_value.data = [{"id": "rev-uuid"}]
        return m

    reviews_t.update.side_effect = update_side_effect

    signal_t, sources_t, projects_t, profiles_t = (
        MagicMock(), MagicMock(), MagicMock(), MagicMock()
    )
    signal_t.select.return_value.eq.return_value.execute.return_value.data = [{
        "id": "sig-uuid", "technology_name": "LangGraph",
        "title": "제목", "summary": None, "signal_date": "2026-07-24",
    }]
    sources_t.select.return_value.eq.return_value.execute.return_value.data = []
    projects_t.select.return_value.eq.return_value.execute.return_value.data = [{"user_id": "user-uuid"}]
    profiles_t.select.return_value.eq.return_value.execute.return_value.data = []

    table_map = {
        "reviews": reviews_t, "signals": signal_t,
        "signal_sources": sources_t, "projects": projects_t, "user_profiles": profiles_t,
    }
    mock_client = MagicMock()
    mock_client.table.side_effect = lambda name: table_map.get(name, MagicMock())

    review_signal("sig-uuid", "proj-uuid", mock_client, MockLLMProvider(), brief_date="2026-07-24")

    assert "schema_version" in saved_result
    assert "review_type" in saved_result
    assert "payload" in saved_result
    assert saved_result["schema_version"] == 1
    assert saved_result["review_type"] == "research"


# ─── 5.11 Reviewer: payload 13섹션 키 존재 검증 ──────────────────────────────────

def test_reviewer_result_payload_has_13_sections():
    """result.payload에 13섹션 키가 모두 존재한다."""
    saved_payload = {}

    reviews_t = MagicMock()
    reviews_t.insert.return_value.execute.return_value.data = [{"id": "rev-uuid"}]

    def update_side_effect(data):
        if "result" in data:
            saved_payload.update(data["result"].get("payload", {}))
        m = MagicMock()
        m.eq.return_value.execute.return_value.data = [{"id": "rev-uuid"}]
        return m

    reviews_t.update.side_effect = update_side_effect

    signal_t, sources_t, projects_t, profiles_t = (
        MagicMock(), MagicMock(), MagicMock(), MagicMock()
    )
    signal_t.select.return_value.eq.return_value.execute.return_value.data = [{
        "id": "sig-uuid", "technology_name": "LangGraph",
        "title": "제목", "summary": None, "signal_date": "2026-07-24",
    }]
    sources_t.select.return_value.eq.return_value.execute.return_value.data = []
    projects_t.select.return_value.eq.return_value.execute.return_value.data = [{"user_id": "user-uuid"}]
    profiles_t.select.return_value.eq.return_value.execute.return_value.data = []

    table_map = {
        "reviews": reviews_t, "signals": signal_t,
        "signal_sources": sources_t, "projects": projects_t, "user_profiles": profiles_t,
    }
    mock_client = MagicMock()
    mock_client.table.side_effect = lambda name: table_map.get(name, MagicMock())

    review_signal("sig-uuid", "proj-uuid", mock_client, MockLLMProvider(), brief_date="2026-07-24")

    required = [
        "one_line_definition", "key_concepts", "problems_solved", "why_it_matters",
        "vs_existing_tech", "user_relevance", "learning_goals", "learning_time_difficulty",
        "practical_applicability", "risks", "recommendation_reason",
        "reference_sources", "honest_box",
    ]
    for section in required:
        assert section in saved_payload, f"payload에 '{section}' 키 누락"


# ─── 5.12 Reviewer: HonestBox severity 값 검증 ───────────────────────────────────

def _make_severity_mock(review_content: str):
    """severity 검증용 공통 mock 빌더."""
    saved_payload = {}

    reviews_t = MagicMock()
    reviews_t.insert.return_value.execute.return_value.data = [{"id": "rev-uuid"}]

    def update_side_effect(data):
        if "result" in data:
            saved_payload.update(data["result"].get("payload", {}))
        m = MagicMock()
        m.eq.return_value.execute.return_value.data = [{"id": "rev-uuid"}]
        return m

    reviews_t.update.side_effect = update_side_effect

    signal_t, sources_t, projects_t, profiles_t = (
        MagicMock(), MagicMock(), MagicMock(), MagicMock()
    )
    signal_t.select.return_value.eq.return_value.execute.return_value.data = [{
        "id": "sig-uuid", "technology_name": "LangGraph",
        "title": "제목", "summary": None, "signal_date": "2026-07-24",
    }]
    sources_t.select.return_value.eq.return_value.execute.return_value.data = []
    projects_t.select.return_value.eq.return_value.execute.return_value.data = [{"user_id": "user-uuid"}]
    profiles_t.select.return_value.eq.return_value.execute.return_value.data = []

    table_map = {
        "reviews": reviews_t, "signals": signal_t,
        "signal_sources": sources_t, "projects": projects_t, "user_profiles": profiles_t,
    }
    mock_client = MagicMock()
    mock_client.table.side_effect = lambda name: table_map.get(name, MagicMock())
    return mock_client, MockLLMProvider(content=review_content), saved_payload


def test_reviewer_honest_box_invalid_severity_defaults_to_standard():
    """honest_box.severity가 유효하지 않으면 'standard'로 기본값이 적용된다."""
    invalid = json.loads(VALID_13_SECTION_RESPONSE)
    invalid["honest_box"]["severity"] = "invalid_value"

    mock_client, llm, saved_payload = _make_severity_mock(json.dumps(invalid))
    review_signal("sig-uuid", "proj-uuid", mock_client, llm, brief_date="2026-07-24")

    severity = saved_payload.get("honest_box", {}).get("severity")
    assert severity == "standard", f"유효하지 않은 severity가 'standard'로 기본값 처리되지 않음: {severity}"


def test_reviewer_honest_box_severity_high_preserved():
    """honest_box.severity가 'high'이면 그대로 유지된다."""
    high = json.loads(VALID_13_SECTION_RESPONSE)
    high["honest_box"]["severity"] = "high"

    mock_client, llm, saved_payload = _make_severity_mock(json.dumps(high))
    review_signal("sig-uuid", "proj-uuid", mock_client, llm, brief_date="2026-07-24")

    assert saved_payload.get("honest_box", {}).get("severity") == "high"


# ─── 5.13 Reviewer: completed/failed 진입 후 상태 변경 없음 검증 ─────────────────

def _make_status_tracking_mock(llm: LLMProvider):
    """상태 전이 추적용 공통 mock 빌더."""
    update_calls_data: list[dict] = []

    reviews_t = MagicMock()
    reviews_t.insert.return_value.execute.return_value.data = [{"id": "rev-uuid"}]

    def update_side_effect(data):
        update_calls_data.append(dict(data))
        m = MagicMock()
        m.eq.return_value.execute.return_value.data = [{"id": "rev-uuid"}]
        return m

    reviews_t.update.side_effect = update_side_effect

    signal_t, sources_t, projects_t, profiles_t = (
        MagicMock(), MagicMock(), MagicMock(), MagicMock()
    )
    signal_t.select.return_value.eq.return_value.execute.return_value.data = [{
        "id": "sig-uuid", "technology_name": "LangGraph",
        "title": "제목", "summary": None, "signal_date": "2026-07-24",
    }]
    sources_t.select.return_value.eq.return_value.execute.return_value.data = []
    projects_t.select.return_value.eq.return_value.execute.return_value.data = [{"user_id": "user-uuid"}]
    profiles_t.select.return_value.eq.return_value.execute.return_value.data = []

    table_map = {
        "reviews": reviews_t, "signals": signal_t,
        "signal_sources": sources_t, "projects": projects_t, "user_profiles": profiles_t,
    }
    mock_client = MagicMock()
    mock_client.table.side_effect = lambda name: table_map.get(name, MagicMock())
    return mock_client, update_calls_data


def test_reviewer_no_status_change_after_completed():
    """completed 상태 이후 추가 status 업데이트가 없다."""
    mock_client, update_calls_data = _make_status_tracking_mock(MockLLMProvider())

    review_signal("sig-uuid", "proj-uuid", mock_client, MockLLMProvider(), brief_date="2026-07-24")

    statuses = [d.get("status") for d in update_calls_data if "status" in d]
    completed_idx = next((i for i, s in enumerate(statuses) if s == "completed"), None)
    assert completed_idx is not None, "completed 상태 전이가 없음"
    assert statuses[completed_idx + 1:] == [], f"completed 이후 추가 상태 변경: {statuses[completed_idx + 1:]}"


def test_reviewer_no_status_change_after_failed():
    """failed 상태 이후 추가 status 업데이트가 없다."""
    mock_client, update_calls_data = _make_status_tracking_mock(MockLLMProvider(raise_error=True))

    review_signal("sig-uuid", "proj-uuid", mock_client, MockLLMProvider(raise_error=True), brief_date="2026-07-24")

    statuses = [d.get("status") for d in update_calls_data if "status" in d]
    failed_idx = next((i for i, s in enumerate(statuses) if s == "failed"), None)
    assert failed_idx is not None, "failed 상태 전이가 없음"
    assert statuses[failed_idx + 1:] == [], f"failed 이후 추가 상태 변경: {statuses[failed_idx + 1:]}"


# ─── 추가: review_all_for_signal 검증 ────────────────────────────────────────────

def test_review_all_for_signal_calls_per_project():
    """review_all_for_signal()이 각 ai_research 프로젝트마다 review를 생성한다."""
    rev_counter = {"n": 0}

    reviews_t = MagicMock()

    def insert_side_effect(data):
        rev_counter["n"] += 1
        m = MagicMock()
        m.execute.return_value.data = [{"id": f"rev-{rev_counter['n']}"}]
        return m

    reviews_t.insert.side_effect = insert_side_effect
    reviews_t.update.return_value.eq.return_value.execute.return_value.data = [{"id": "rev"}]

    # projects 테이블: 쿼리 종류에 따라 다른 값 반환
    projects_t = MagicMock()

    def projects_select_side_effect(fields):
        m = MagicMock()
        if fields == "id":
            # review_all_for_signal 내부 — ai_research 프로젝트 목록
            m.eq.return_value.execute.return_value.data = [{"id": "proj-1"}, {"id": "proj-2"}]
        else:
            # review_signal 내부 — user_id 조회
            m.eq.return_value.execute.return_value.data = [{"user_id": "user-uuid"}]
        return m

    projects_t.select.side_effect = projects_select_side_effect

    signal_t, sources_t, profiles_t = MagicMock(), MagicMock(), MagicMock()
    signal_t.select.return_value.eq.return_value.execute.return_value.data = [{
        "id": "sig-uuid", "technology_name": "LangGraph",
        "title": "제목", "summary": None, "signal_date": "2026-07-24",
    }]
    sources_t.select.return_value.eq.return_value.execute.return_value.data = []
    profiles_t.select.return_value.eq.return_value.execute.return_value.data = []

    table_map = {
        "reviews": reviews_t, "signals": signal_t,
        "signal_sources": sources_t, "projects": projects_t, "user_profiles": profiles_t,
    }
    mock_client = MagicMock()
    mock_client.table.side_effect = lambda name: table_map.get(name, MagicMock())

    review_ids = review_all_for_signal("sig-uuid", mock_client, MockLLMProvider(), brief_date="2026-07-24")

    assert len(review_ids) == 2
    assert "rev-1" in review_ids
    assert "rev-2" in review_ids


# ─── 추가: 빈 입력 경계 케이스 ───────────────────────────────────────────────────

def test_build_signals_empty_list_returns_empty():
    """build_signals([])는 빈 리스트를 반환하고 Supabase를 호출하지 않는다."""
    mock_client = MagicMock()
    llm = MockLLMProvider()
    result = build_signals([], mock_client, llm=llm)
    assert result == []
    mock_client.table.assert_not_called()
