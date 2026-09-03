from core.config import settings
from pipeline.llm.base import LLMProvider
from pipeline.llm.gemini_provider import GeminiProvider
from pipeline.llm.openai_provider import OpenAIProvider


def get_llm_provider() -> LLMProvider:
    """settings.llm_provider 플래그에 따라 LLM 프로바이더를 생성한다(토글 단일 지점)."""
    if settings.llm_provider == "gemini":
        return GeminiProvider(
            gemini_api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            openai_api_key=settings.openai_api_key,
            embedding_model=settings.openai_embedding_model,
            max_retries=settings.gemini_max_retries,
            request_delay_sec=settings.gemini_request_delay_sec,
            timeout_sec=settings.gemini_timeout_sec,
        )
    return OpenAIProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        embedding_model=settings.openai_embedding_model,
    )
