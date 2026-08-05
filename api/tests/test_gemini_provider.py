# api/tests/test_gemini_provider.py
import json
from unittest.mock import MagicMock
import pytest

from pipeline.llm.base import (
    ChatContext, LearningPathContext, LLMProviderError, MemoryContext, ReviewContext,
)
from pipeline.llm.gemini_provider import GeminiProvider
from tests.mocks import VALID_13_SECTION_RESPONSE


def _client_returning(*texts):
    """models.generate_content가 순서대로 text를 반환하는 fake genai client."""
    client = MagicMock()
    responses = [MagicMock(text=t) for t in texts]
    client.models.generate_content.side_effect = responses
    return client


def _provider(client, embedder=None):
    return GeminiProvider(
        gemini_api_key="k", model="gemini-2.5-flash",
        openai_api_key="ok", embedding_model="text-embedding-3-small",
        max_retries=4, request_delay_sec=0.0, client=client, embedder=embedder,
    )


def test_build_signal_title_summary_returns_content():
    client = _client_returning('{"title": "제목", "summary": "요약"}')
    resp = _provider(client).build_signal_title_summary("LangGraph", [])
    assert json.loads(resp.content)["title"] == "제목"
    # JSON 모드로 호출됐는지 확인
    kwargs = client.models.generate_content.call_args.kwargs
    assert kwargs["config"].response_mime_type == "application/json"


def test_generate_validates_13_sections():
    client = _client_returning(VALID_13_SECTION_RESPONSE)
    ctx = ReviewContext(technology_name="LangGraph", signal_sources=[])
    resp = _provider(client).generate(ctx)
    assert "one_line_definition" in resp.content


def test_generate_raises_on_missing_section():
    client = _client_returning('{"one_line_definition": "x"}')
    ctx = ReviewContext(technology_name="LangGraph", signal_sources=[])
    with pytest.raises(LLMProviderError):
        _provider(client).generate(ctx)


def test_chat_returns_plain_text_without_json_mode():
    client = _client_returning("안녕하세요, 답변입니다.")
    ctx = ChatContext(signal_id="s1", user_message="질문")
    resp = _provider(client).chat(ctx)
    assert resp.content == "안녕하세요, 답변입니다."
    kwargs = client.models.generate_content.call_args.kwargs
    assert kwargs["config"].response_mime_type is None


def test_embed_text_delegates_to_openai_embedder():
    embedder = MagicMock()
    embedder.embed_text.return_value = [0.0] * 1536
    out = _provider(_client_returning(), embedder=embedder).embed_text("hi")
    assert len(out) == 1536
    embedder.embed_text.assert_called_once_with("hi")


def test_retry_on_rate_limit_then_succeeds(monkeypatch):
    import pipeline.llm.gemini_provider as gp
    monkeypatch.setattr(gp.time, "sleep", lambda *_: None)
    client = MagicMock()
    client.models.generate_content.side_effect = [
        Exception("429 RESOURCE_EXHAUSTED: quota"),
        MagicMock(text='{"title": "t", "summary": "s"}'),
    ]
    resp = _provider(client).build_signal_title_summary("X", [])
    assert json.loads(resp.content)["title"] == "t"
    assert client.models.generate_content.call_count == 2


def test_retry_exhausted_raises_llm_error(monkeypatch):
    import pipeline.llm.gemini_provider as gp
    monkeypatch.setattr(gp.time, "sleep", lambda *_: None)
    client = MagicMock()
    client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED")
    with pytest.raises(LLMProviderError):
        _provider(client).build_signal_title_summary("X", [])
