from unittest.mock import patch
from pipeline.llm.factory import get_llm_provider
from pipeline.llm.openai_provider import OpenAIProvider
from pipeline.llm.gemini_provider import GeminiProvider


def test_factory_returns_openai_by_default():
    with patch("pipeline.llm.factory.settings") as s:
        s.llm_provider = "openai"
        s.openai_api_key = "k"; s.openai_model = "gpt-4o"
        s.openai_embedding_model = "text-embedding-3-small"
        assert isinstance(get_llm_provider(), OpenAIProvider)


def test_factory_returns_gemini_when_flagged():
    with patch("pipeline.llm.factory.settings") as s:
        s.llm_provider = "gemini"
        s.gemini_api_key = "gk"; s.gemini_model = "gemini-2.5-flash"
        s.gemini_max_retries = 4; s.gemini_request_delay_sec = 0.0
        s.openai_api_key = "ok"; s.openai_embedding_model = "text-embedding-3-small"
        # genai.Client가 실제 생성되지 않도록 주입 경로를 우회: client 패치
        with patch("pipeline.llm.gemini_provider.genai.Client"):
            assert isinstance(get_llm_provider(), GeminiProvider)
