from abc import ABC, abstractmethod
from dataclasses import dataclass, field


REQUIRED_SECTIONS = [
    "one_line_definition", "key_concepts", "problems_solved", "why_it_matters",
    "vs_existing_tech", "user_relevance", "learning_goals", "learning_time_difficulty",
    "practical_applicability", "risks", "recommendation_reason",
    "reference_sources", "honest_box",
]


class LLMProviderError(Exception):
    """LLM 공급자 에러 표준화 (AD-6)."""
    pass


@dataclass
class ReviewContext:
    """Research Review 생성 컨텍스트."""
    technology_name: str
    signal_sources: list[dict]          # [{source_type, url, title}, ...]
    user_role: str | None = None
    user_tech_stack: list[str] = field(default_factory=list)
    user_interests: list[str] = field(default_factory=list)
    user_experience_level: str | None = None


@dataclass
class LearningPathContext:
    """Learning Path 생성 컨텍스트."""
    technology_name: str
    signal_summary: str
    signal_sources: list[dict]       # [{source_type, url, title}]
    user_role: str | None = None
    user_tech_stack: list[str] = field(default_factory=list)
    user_project_goal: str | None = None   # user_profiles.project_goal
    user_experience_level: str | None = None


@dataclass
class MemoryContext:
    """Memory 추출 컨텍스트 (Decision Loop 체인: Signal + Review + Decision + Outcome)."""
    technology_name: str | None
    decision_choice: str
    decision_memo: str | None
    outcome_status: str
    outcome_useful: bool | None
    outcome_actual_learning_time_min: int | None
    outcome_memo: str | None
    outcome_applied_project_note: str | None
    review_one_line_definition: str | None = None


@dataclass
class ChatContext:
    """Contextual Chat 컨텍스트."""
    signal_id: str
    user_message: str
    review_payload: dict | None = None
    user_role: str | None = None
    user_tech_stack: list[str] = field(default_factory=list)


@dataclass
class LLMResponse:
    """LLM 공급자 응답 표준화."""
    content: str    # JSON 문자열 (13섹션 payload 또는 기타 형식)
    model: str = ""


class LLMProvider(ABC):
    """LLM 공급자 추상 인터페이스 (AD-6)."""

    @abstractmethod
    def generate(self, context: ReviewContext) -> LLMResponse:
        ...

    @abstractmethod
    def build_signal_title_summary(self, technology_name: str, signal_sources: list[dict]) -> LLMResponse:
        """Signal 기술명·출처로 AI 제목·요약 생성. {"title": "...", "summary": "..."} JSON 반환."""
        ...

    @abstractmethod
    def chat(self, context: ChatContext) -> LLMResponse:
        """Contextual Chat — Review 컨텍스트 기반 질답."""
        ...

    @abstractmethod
    def generate_learning_path(self, context: LearningPathContext) -> LLMResponse:
        """5가지 고정 리소스 타입의 Learning Path JSON 생성."""
        ...

    @abstractmethod
    def extract_memory(self, context: MemoryContext) -> LLMResponse:
        """Decision Loop 체인에서 Memory(memory_type + summary)를 추출. JSON {"memory_type","summary"} 반환."""
        ...

    @abstractmethod
    def classify_learnability(self, topics: list[dict]) -> LLMResponse:
        """토픽 배치를 학습가치로 분류. content = JSON {"results":[{"id","keep","category","name"}]}."""
        ...

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """텍스트를 임베딩 벡터(1536차원)로 변환 (AD-7)"""
        ...
