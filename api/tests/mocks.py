"""테스트 전용 공유 Mock — 여러 테스트 파일에서 재사용 (LLM Provider 인터페이스 모킹, AD-11)."""
import json

from pipeline.llm.base import LLMProvider, LLMProviderError, LLMResponse, ReviewContext

VALID_13_SECTION_RESPONSE = json.dumps({
    "one_line_definition": "정의",
    "key_concepts": "개념",
    "problems_solved": "문제",
    "why_it_matters": "중요성",
    "vs_existing_tech": "차이",
    "user_relevance": "관련성",
    "learning_goals": "목표",
    "learning_time_difficulty": {"estimated_hours": 5, "difficulty": "intermediate"},
    "practical_applicability": "적용",
    "risks": "위험",
    "recommendation_reason": "추천",
    "reference_sources": ["https://example.com"],
    "honest_box": {"content": "솔직한 평가", "severity": "standard"},
})

VALID_SIGNAL_RESPONSE = json.dumps({"title": "LangGraph 통합", "summary": "요약 내용"})

VALID_LEARNING_PATH_RESPONSE = json.dumps({
    "resources": [
        {"type": "official_docs", "title": "공식 문서", "url": "https://example.com/docs", "descriptor": "설명"},
        {"type": "core_material", "title": "핵심 자료", "url": "https://example.com/core", "descriptor": "설명"},
        {"type": "github", "title": "GitHub", "url": "https://github.com/example", "descriptor": "설명"},
        {"type": "practice_example", "title": "실습 예제", "url": "https://example.com/practice", "descriptor": "설명"},
        {"type": "applied_idea", "title": "적용 아이디어", "url": "", "descriptor": "개인화된 적용 아이디어"},
    ],
})

VALID_MEMORY_RESPONSE = json.dumps({"memory_type": "outcome_history", "summary": "요약 내용"})


class MockLLMProvider(LLMProvider):
    def __init__(
        self,
        content: str = VALID_13_SECTION_RESPONSE,
        raise_error: bool = False,
        signal_content: str | None = None,
        learning_path_content: str | None = None,
    ):
        self._content = content
        self._raise_error = raise_error
        self._signal_content = signal_content or VALID_SIGNAL_RESPONSE
        self._learning_path_content = learning_path_content or VALID_LEARNING_PATH_RESPONSE
        self.build_signal_calls: list[tuple] = []

    def generate(self, context: ReviewContext) -> LLMResponse:
        if self._raise_error:
            raise LLMProviderError("mock LLM error")
        return LLMResponse(content=self._content, model="mock")

    def build_signal_title_summary(self, technology_name: str, signal_sources: list[dict]) -> LLMResponse:
        self.build_signal_calls.append((technology_name, signal_sources))
        if self._raise_error:
            raise LLMProviderError("mock LLM error")
        return LLMResponse(content=self._signal_content, model="mock")

    def chat(self, context):
        raise NotImplementedError

    def generate_learning_path(self, context):
        if self._raise_error:
            raise LLMProviderError("mock LLM error")
        return LLMResponse(content=self._learning_path_content, model="mock")

    def extract_memory(self, context):
        if self._raise_error:
            raise LLMProviderError("mock LLM error")
        return LLMResponse(content=VALID_MEMORY_RESPONSE, model="mock")

    def embed_text(self, text):
        if self._raise_error:
            raise LLMProviderError("mock LLM error")
        return [0.001] * 1536
