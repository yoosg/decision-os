from openai import OpenAI, OpenAIError

from pipeline.llm.base import (
    ChatContext, LearningPathContext, LLMProvider, LLMProviderError, LLMResponse, MemoryContext,
    ReviewContext,
)
from pipeline.llm import prompts

# Re-export for backward compatibility (pipeline/coach.py, pipeline/memory_manager.py import these)
ALLOWED_MEMORY_TYPES = prompts.ALLOWED_MEMORY_TYPES
LEARNING_PATH_RESOURCE_TYPES = prompts.LEARNING_PATH_RESOURCE_TYPES


class OpenAIProvider(LLMProvider):
    """OpenAI Responses API 구현체 (AD-6: Chat Completions 사용 불가)."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        timeout: float = 30.0,
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        self._client = OpenAI(api_key=api_key, timeout=timeout)
        self._model = model
        self._embedding_model = embedding_model

    def generate(self, context: ReviewContext) -> LLMResponse:
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=prompts.RESEARCH_REVIEW_SYSTEM_PROMPT,
                # json_object 포맷은 input 메시지에 'json' 단어가 있어야 한다(instructions만으론 400).
                input=f"{prompts.build_review_user_content(context)}\n\n반드시 JSON 객체로 응답하세요.",
                text={"format": {"type": "json_object"}},
            )
            raw = response.output_text
            prompts.parse_and_validate_review(raw)
            return LLMResponse(content=raw, model=self._model)
        except LLMProviderError:
            raise
        except OpenAIError as e:
            raise LLMProviderError(str(e)) from e
        except Exception as e:
            raise LLMProviderError(str(e)) from e

    def build_signal_title_summary(self, technology_name: str, signal_sources: list[dict]) -> LLMResponse:
        # OpenAI Responses API의 json_object 포맷은 input 메시지에 'json' 단어가 있어야 한다
        # (instructions만으로는 부족 → 400). 마지막 줄에 JSON 지시를 명시.
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=prompts.SIGNAL_BUILD_PROMPT,
                input=prompts.build_signal_user_input(technology_name, signal_sources),
                text={"format": {"type": "json_object"}},
            )
            return LLMResponse(content=response.output_text, model=self._model)
        except OpenAIError as e:
            raise LLMProviderError(str(e)) from e
        except Exception as e:
            raise LLMProviderError(str(e)) from e

    def chat(self, context: ChatContext) -> LLMResponse:
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=prompts.CONTEXTUAL_CHAT_SYSTEM_PROMPT,
                input=prompts.build_chat_user_input(context),
            )
            return LLMResponse(content=response.output_text or "", model=self._model)
        except OpenAIError as e:
            raise LLMProviderError(str(e)) from e
        except Exception as e:
            raise LLMProviderError(str(e)) from e

    def generate_learning_path(self, context: LearningPathContext) -> LLMResponse:
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=prompts.LEARNING_PATH_SYSTEM_PROMPT,
                # json_object 포맷은 input 메시지에 'json' 단어가 있어야 한다(instructions만으론 400).
                input=f"{prompts.build_learning_path_user_content(context)}\n\n반드시 JSON 객체로 응답하세요.",
                text={"format": {"type": "json_object"}},
            )
            raw = response.output_text
            prompts.parse_and_validate_learning_path(raw)
            return LLMResponse(content=raw, model=self._model)
        except LLMProviderError:
            raise
        except OpenAIError as e:
            raise LLMProviderError(str(e)) from e
        except Exception as e:
            raise LLMProviderError(str(e)) from e

    def extract_memory(self, context: MemoryContext) -> LLMResponse:
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=prompts.MEMORY_EXTRACTION_SYSTEM_PROMPT,
                # json_object 포맷은 input 메시지에 'json' 단어가 있어야 한다(instructions만으론 400).
                input=f"{prompts.build_memory_user_content(context)}\n\n반드시 JSON 객체로 응답하세요.",
                text={"format": {"type": "json_object"}},
            )
            raw = response.output_text
            prompts.parse_and_validate_memory(raw)
            return LLMResponse(content=raw, model=self._model)
        except LLMProviderError:
            raise
        except OpenAIError as e:
            raise LLMProviderError(str(e)) from e
        except Exception as e:
            raise LLMProviderError(str(e)) from e

    def classify_learnability(self, topics: list[dict]) -> LLMResponse:
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=prompts.LEARNABILITY_CLASSIFY_PROMPT,
                input=prompts.build_learnability_user_input(topics),
                text={"format": {"type": "json_object"}},
            )
            raw = response.output_text
            prompts.parse_and_validate_learnability(raw, expected_count=len(topics))
            return LLMResponse(content=raw, model=self._model)
        except LLMProviderError:
            raise
        except OpenAIError as e:
            raise LLMProviderError(str(e)) from e
        except Exception as e:
            raise LLMProviderError(str(e)) from e

    def embed_text(self, text: str) -> list[float]:
        try:
            response = self._client.embeddings.create(model=self._embedding_model, input=text)
            embedding = response.data[0].embedding
        except OpenAIError as e:
            raise LLMProviderError(str(e)) from e
        except Exception as e:
            raise LLMProviderError(str(e)) from e
        if len(embedding) != 1536:
            raise LLMProviderError(f"임베딩 차원이 1536이 아님: {len(embedding)}")
        return embedding
