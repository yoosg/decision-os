"""Memory Manager 파이프라인/OpenAIProvider 단위 테스트 (Story 4.3).

파이프라인 단계 테스트는 `_execute_memory_extraction(..., client, llm)`에 client/llm을 직접 주입한다
(`test_execute_learning_path_pipeline_completes`와 동일한 관례, AD-11 완전 모킹 컨벤션은
스토리 Dev Notes "스펙 갈등" 섹션 참조).
"""
import json
from unittest.mock import MagicMock, patch

from openai import OpenAIError

TEST_OUTCOME_ID = "out-jkl-444"
TEST_DECISION_ID = "dec-ghi-333"
TEST_REVIEW_ID = "rev-abc-111"
TEST_PROJECT_ID = "proj-xyz-222"
TEST_SIGNAL_ID = "sig-abc-123"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"


def _chain() -> MagicMock:
    c = MagicMock()
    for attr in ("select", "insert", "update", "eq", "in_", "limit", "order"):
        getattr(c, attr).return_value = c
    return c


def _base_table_side_effect(*, signal_id: str | None = TEST_SIGNAL_ID, insert_capture: dict | None = None):
    def table_side_effect(table_name: str) -> MagicMock:
        c = _chain()
        if table_name == "outcomes":
            c.execute.return_value.data = [{
                "status": "completed",
                "useful": True,
                "actual_learning_time_min": 90,
                "applied_project_note": "적용 노트",
                "memo": "outcome 메모",
            }]
        elif table_name == "decisions":
            c.execute.return_value.data = [{
                "choice": "learn_now", "memo": "decision 메모", "review_id": TEST_REVIEW_ID,
            }]
        elif table_name == "reviews":
            c.execute.return_value.data = [{
                "project_id": TEST_PROJECT_ID,
                "signal_id": signal_id,
                "result": {"one_line_definition": "한 줄 정의"},
            }]
        elif table_name == "projects":
            c.execute.return_value.data = [{"user_id": TEST_USER_ID}]
        elif table_name == "signals":
            c.execute.return_value.data = [{"technology_name": "LangGraph"}]
        elif table_name == "memories":
            if insert_capture is not None:
                def tracked_insert(data: dict) -> MagicMock:
                    insert_capture.update(data)
                    return c
                c.insert = tracked_insert
        return c
    return table_side_effect


# ─── 7.2: 정상 흐름 → memories.insert 호출 + True 반환 ──────────────────────

def test_execute_memory_extraction_inserts_memory_and_returns_true():
    from tests.mocks import MockLLMProvider
    from pipeline.memory_manager import _execute_memory_extraction

    captured: dict = {}
    mock_client = MagicMock()
    mock_client.table.side_effect = _base_table_side_effect(insert_capture=captured)

    result = _execute_memory_extraction(TEST_OUTCOME_ID, TEST_DECISION_ID, mock_client, MockLLMProvider())

    assert result is True
    assert captured["user_id"] == TEST_USER_ID
    assert captured["memory_type"] == "outcome_history"
    assert captured["summary"]
    assert isinstance(captured["embedding"], list) and len(captured["embedding"]) == 1536
    assert captured["source_decision_id"] == TEST_DECISION_ID


# ─── 7.3: LLM 에러 → 예외 미전파 + False 반환 + INSERT 미호출 ────────────────

def test_execute_memory_extraction_returns_false_on_llm_error():
    from tests.mocks import MockLLMProvider
    from pipeline.memory_manager import _execute_memory_extraction

    insert_called = False
    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        nonlocal insert_called
        c = _base_table_side_effect()(table_name)
        if table_name == "memories":
            def tracked_insert(_data: dict) -> MagicMock:
                nonlocal insert_called
                insert_called = True
                return c
            c.insert = tracked_insert
        return c

    mock_client.table.side_effect = table_side_effect

    result = _execute_memory_extraction(
        TEST_OUTCOME_ID, TEST_DECISION_ID, mock_client, MockLLMProvider(raise_error=True),
    )

    assert result is False
    assert not insert_called


# ─── 7.4: 잘못된 memory_type / JSON 파싱 실패 → False 반환 + INSERT 미호출 ───

def test_execute_memory_extraction_returns_false_on_invalid_memory_type():
    from pipeline.llm.base import LLMResponse
    from pipeline.memory_manager import _execute_memory_extraction

    class BadMemoryTypeProvider:
        def extract_memory(self, context):
            return LLMResponse(content=json.dumps({"memory_type": "invalid_type", "summary": "요약"}), model="mock")

        def embed_text(self, text):
            raise AssertionError("embed_text가 호출되면 안 됨")

    insert_called = False
    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        nonlocal insert_called
        c = _base_table_side_effect()(table_name)
        if table_name == "memories":
            def tracked_insert(_data: dict) -> MagicMock:
                nonlocal insert_called
                insert_called = True
                return c
            c.insert = tracked_insert
        return c

    mock_client.table.side_effect = table_side_effect

    result = _execute_memory_extraction(TEST_OUTCOME_ID, TEST_DECISION_ID, mock_client, BadMemoryTypeProvider())

    assert result is False
    assert not insert_called


def test_execute_memory_extraction_returns_false_on_json_parse_failure():
    from pipeline.llm.base import LLMResponse
    from pipeline.memory_manager import _execute_memory_extraction

    class InvalidJSONProvider:
        def extract_memory(self, context):
            return LLMResponse(content="not-json", model="mock")

        def embed_text(self, text):
            raise AssertionError("embed_text가 호출되면 안 됨")

    insert_called = False
    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        nonlocal insert_called
        c = _base_table_side_effect()(table_name)
        if table_name == "memories":
            def tracked_insert(_data: dict) -> MagicMock:
                nonlocal insert_called
                insert_called = True
                return c
            c.insert = tracked_insert
        return c

    mock_client.table.side_effect = table_side_effect

    result = _execute_memory_extraction(TEST_OUTCOME_ID, TEST_DECISION_ID, mock_client, InvalidJSONProvider())

    assert result is False
    assert not insert_called


# ─── 7.5: review.signal_id가 None → signal 조회 스킵, technology_name=None ──

def test_execute_memory_extraction_skips_signal_lookup_when_signal_id_none():
    from tests.mocks import MockLLMProvider
    from pipeline.memory_manager import _execute_memory_extraction

    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        if table_name == "signals":
            raise AssertionError("signal_id가 None이면 signals 테이블을 조회하면 안 됨")
        return _base_table_side_effect(signal_id=None)(table_name)

    mock_client.table.side_effect = table_side_effect

    result = _execute_memory_extraction(TEST_OUTCOME_ID, TEST_DECISION_ID, mock_client, MockLLMProvider())

    assert result is True


# ─── 7.6: run_memory_manager_from_outcome 위임 테스트 ────────────────────────

def test_run_memory_manager_from_outcome_delegates_to_pipeline(monkeypatch):
    from pipeline import memory_manager

    calls = []
    monkeypatch.setattr(memory_manager, "get_supabase", lambda: "the-client")
    monkeypatch.setattr(
        memory_manager, "get_llm_provider", lambda: "the-llm",
    )
    monkeypatch.setattr(
        memory_manager, "_execute_memory_extraction", lambda *args: calls.append(args),
    )

    memory_manager.run_memory_manager_from_outcome(TEST_OUTCOME_ID, TEST_DECISION_ID)

    assert len(calls) == 1
    outcome_id, decision_id, client, llm = calls[0]
    assert (outcome_id, decision_id) == (TEST_OUTCOME_ID, TEST_DECISION_ID)
    assert client == "the-client"
    assert llm == "the-llm"


# ─── 7.7: OpenAIProvider.extract_memory() ────────────────────────────────────

def test_openai_provider_extract_memory_parses_valid_json():
    from pipeline.llm.base import MemoryContext
    from pipeline.llm.openai_provider import OpenAIProvider

    with patch("pipeline.llm.openai_provider.OpenAI") as mock_openai_cls:
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.responses.create.return_value.output_text = json.dumps({
            "memory_type": "outcome_history", "summary": "요약 내용",
        })

        provider = OpenAIProvider(api_key="sk-test")
        context = MemoryContext(
            technology_name="LangGraph",
            decision_choice="learn_now",
            decision_memo=None,
            outcome_status="completed",
            outcome_useful=True,
            outcome_actual_learning_time_min=60,
            outcome_memo=None,
            outcome_applied_project_note=None,
        )
        response = provider.extract_memory(context)

    assert json.loads(response.content) == {"memory_type": "outcome_history", "summary": "요약 내용"}


def test_openai_provider_extract_memory_raises_on_invalid_memory_type():
    from pipeline.llm.base import LLMProviderError, MemoryContext
    from pipeline.llm.openai_provider import OpenAIProvider

    with patch("pipeline.llm.openai_provider.OpenAI") as mock_openai_cls:
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.responses.create.return_value.output_text = json.dumps({
            "memory_type": "not_a_real_type", "summary": "요약 내용",
        })

        provider = OpenAIProvider(api_key="sk-test")
        context = MemoryContext(
            technology_name="LangGraph",
            decision_choice="learn_now",
            decision_memo=None,
            outcome_status="completed",
            outcome_useful=True,
            outcome_actual_learning_time_min=60,
            outcome_memo=None,
            outcome_applied_project_note=None,
        )
        try:
            provider.extract_memory(context)
            assert False, "LLMProviderError가 발생해야 함"
        except LLMProviderError:
            pass


# ─── 7.8: OpenAIProvider.embed_text() ────────────────────────────────────────

def test_openai_provider_embed_text_returns_vector():
    from pipeline.llm.openai_provider import OpenAIProvider

    with patch("pipeline.llm.openai_provider.OpenAI") as mock_openai_cls:
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.embeddings.create.return_value.data = [MagicMock(embedding=[0.1] * 1536)]

        provider = OpenAIProvider(api_key="sk-test")
        embedding = provider.embed_text("텍스트")

    assert len(embedding) == 1536


def test_openai_provider_embed_text_raises_on_dimension_mismatch():
    from pipeline.llm.base import LLMProviderError
    from pipeline.llm.openai_provider import OpenAIProvider

    with patch("pipeline.llm.openai_provider.OpenAI") as mock_openai_cls:
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.embeddings.create.return_value.data = [MagicMock(embedding=[0.1] * 10)]

        provider = OpenAIProvider(api_key="sk-test")
        try:
            provider.embed_text("텍스트")
            assert False, "LLMProviderError가 발생해야 함"
        except LLMProviderError:
            pass


def test_openai_provider_embed_text_wraps_openai_error():
    from pipeline.llm.base import LLMProviderError
    from pipeline.llm.openai_provider import OpenAIProvider

    with patch("pipeline.llm.openai_provider.OpenAI") as mock_openai_cls:
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.embeddings.create.side_effect = OpenAIError("boom")

        provider = OpenAIProvider(api_key="sk-test")
        try:
            provider.embed_text("텍스트")
            assert False, "LLMProviderError가 발생해야 함"
        except LLMProviderError:
            pass
