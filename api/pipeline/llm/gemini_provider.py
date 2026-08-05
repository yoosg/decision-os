import time

from google import genai
from google.genai import types

from pipeline.llm import prompts
from pipeline.llm.base import (
    ChatContext, LearningPathContext, LLMProvider, LLMProviderError, LLMResponse,
    MemoryContext, ReviewContext,
)
from pipeline.llm.openai_provider import OpenAIProvider

_RATE_LIMIT_MARKERS = ("429", "RESOURCE_EXHAUSTED", "rate limit", "quota")


class GeminiProvider(LLMProvider):
    """Gemini 텍스트 생성 구현체. 임베딩은 OpenAI에 위임(설계 결정 1)."""

    def __init__(
        self,
        gemini_api_key: str,
        model: str = "gemini-2.5-flash",
        openai_api_key: str = "",
        embedding_model: str = "text-embedding-3-small",
        max_retries: int = 4,
        request_delay_sec: float = 0.0,
        client=None,
        embedder=None,
    ) -> None:
        self._client = client or genai.Client(api_key=gemini_api_key)
        self._model = model
        self._max_retries = max_retries
        self._request_delay_sec = request_delay_sec
        # 임베딩은 항상 OpenAI. 테스트 주입 가능(embedder).
        self._embedder = embedder or OpenAIProvider(
            api_key=openai_api_key, embedding_model=embedding_model
        )

    @staticmethod
    def _is_rate_limit(exc: Exception) -> bool:
        code = getattr(exc, "code", None)
        if code in (429, 503):
            return True
        text = str(exc)
        return any(m in text for m in _RATE_LIMIT_MARKERS)

    def _generate(self, system_instruction: str, contents: str, as_json: bool) -> str:
        """generate_content 호출 + 프리티어 429 백오프 재시도. 실패 시 LLMProviderError."""
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json" if as_json else None,
        )
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                if self._request_delay_sec:
                    time.sleep(self._request_delay_sec)
                response = self._client.models.generate_content(
                    model=self._model, contents=contents, config=config,
                )
                return response.text or ""
            except Exception as e:  # noqa: BLE001 — 재시도 분류 후 표준화
                last_exc = e
                if self._is_rate_limit(e) and attempt < self._max_retries - 1:
                    time.sleep(2 ** (attempt + 1))  # 2s, 4s, 8s...
                    continue
                raise LLMProviderError(str(e)) from e
        raise LLMProviderError(str(last_exc))

    def generate(self, context: ReviewContext) -> LLMResponse:
        raw = self._generate(
            prompts.RESEARCH_REVIEW_SYSTEM_PROMPT,
            prompts.build_review_user_content(context), as_json=True,
        )
        prompts.parse_and_validate_review(raw)
        return LLMResponse(content=raw, model=self._model)

    def build_signal_title_summary(self, technology_name: str, signal_sources: list[dict]) -> LLMResponse:
        raw = self._generate(
            prompts.SIGNAL_BUILD_PROMPT,
            prompts.build_signal_user_input(technology_name, signal_sources), as_json=True,
        )
        return LLMResponse(content=raw, model=self._model)

    def chat(self, context: ChatContext) -> LLMResponse:
        raw = self._generate(
            prompts.CONTEXTUAL_CHAT_SYSTEM_PROMPT,
            prompts.build_chat_user_input(context), as_json=False,
        )
        return LLMResponse(content=raw, model=self._model)

    def generate_learning_path(self, context: LearningPathContext) -> LLMResponse:
        raw = self._generate(
            prompts.LEARNING_PATH_SYSTEM_PROMPT,
            prompts.build_learning_path_user_content(context), as_json=True,
        )
        prompts.parse_and_validate_learning_path(raw)
        return LLMResponse(content=raw, model=self._model)

    def extract_memory(self, context: MemoryContext) -> LLMResponse:
        raw = self._generate(
            prompts.MEMORY_EXTRACTION_SYSTEM_PROMPT,
            prompts.build_memory_user_content(context), as_json=True,
        )
        prompts.parse_and_validate_memory(raw)
        return LLMResponse(content=raw, model=self._model)

    def embed_text(self, text: str) -> list[float]:
        return self._embedder.embed_text(text)
