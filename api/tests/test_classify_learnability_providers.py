"""Offline provider-level tests for classify_learnability.
Uses MagicMock to avoid real API calls — one test per provider.
"""
import json
from unittest.mock import MagicMock

from pipeline.llm.openai_provider import OpenAIProvider
from pipeline.llm.gemini_provider import GeminiProvider

_TOPICS = [{"id": 0, "label": "LangGraph", "title": "LangGraph 0.3 릴리스"}]
_VALID_RAW = json.dumps({"results": [{"id": 0, "keep": True, "category": "tool_update", "name": "LangGraph 0.3"}]})


def test_openai_provider_classify_learnability_returns_llm_response():
    """OpenAIProvider.classify_learnability returns LLMResponse with validated JSON content."""
    provider = OpenAIProvider(api_key="dummy-key")

    # Replace the internal OpenAI client with a MagicMock
    mock_client = MagicMock()
    mock_client.responses.create.return_value = MagicMock(output_text=_VALID_RAW)
    provider._client = mock_client

    resp = provider.classify_learnability(_TOPICS)

    assert resp.content == _VALID_RAW
    parsed = json.loads(resp.content)
    assert parsed["results"][0]["id"] == 0
    assert parsed["results"][0]["keep"] is True
    assert parsed["results"][0]["name"] == "LangGraph 0.3"


def test_gemini_provider_classify_learnability_returns_llm_response():
    """GeminiProvider.classify_learnability returns LLMResponse with validated JSON content."""
    # Inject a MagicMock client whose models.generate_content(...).text returns valid JSON
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(text=_VALID_RAW)

    # Use injectable embedder to avoid real OpenAI init
    mock_embedder = MagicMock()

    provider = GeminiProvider(
        gemini_api_key="dummy-key",
        model="gemini-2.5-flash",
        openai_api_key="dummy-ok",
        client=mock_client,
        embedder=mock_embedder,
    )

    resp = provider.classify_learnability(_TOPICS)

    assert resp.content == _VALID_RAW
    parsed = json.loads(resp.content)
    assert parsed["results"][0]["id"] == 0
    assert parsed["results"][0]["keep"] is True
    assert parsed["results"][0]["name"] == "LangGraph 0.3"
