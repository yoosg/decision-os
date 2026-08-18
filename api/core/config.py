import warnings
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_role_key: str = Field(default="", repr=False)
    supabase_jwt_secret: str = Field(default="", repr=False)
    cors_origins: list[str] = ["http://localhost:3000"]
    openai_api_key: str = Field(default="", repr=False)
    openai_model: str = "gpt-4o-mini"  # 비용 절감: 기본 모델을 mini로
    openai_embedding_model: str = "text-embedding-3-small"
    # LLM 프로바이더 토글 — "openai"(기본) | "gemini"(테스트/프리티어)
    # Literal로 강제: 오타가 조용히 잘못된 경로로 빠지지 않게 로드 시 검증.
    llm_provider: Literal["openai", "gemini"] = "openai"
    gemini_api_key: str = Field(default="", repr=False)
    gemini_model: str = "gemini-flash-latest"  # 2.5-flash는 신규 사용자 차단(404) → latest alias
    # 프리티어 rate-limit 방어: 429 시 지수 백오프 재시도 횟수 + 호출 간 최소 간격(초)
    gemini_max_retries: int = 4
    gemini_request_delay_sec: float = 0.0
    firebase_service_account_json: str = Field(default="", repr=False)
    # Story 6.1: 실 수집기 어댑터 — "real"(외부 소스 수집) | "stub"(하드코딩 5건 폴백)
    # Literal로 강제 — 오타(예: "Stub")가 조용히 real 실네트워크 경로로 빠지지 않게 로드 시 검증.
    collector_mode: Literal["real", "stub"] = "real"
    # 외부 HTTP 요청 타임아웃(초). 스파이크에서 확인된 타임아웃 이슈 대응.
    collector_timeout_seconds: float = 10.0
    # Story 6.2: 의미 클러스터링 & 관련성/세이프티 필터
    # clustering_enabled: 안전 롤아웃/긴급 차단 토글(끄면 6.1 그대로 pass-through)
    clustering_enabled: bool = True
    # learnability_filter_enabled: 학습가치 필터 on/off (긴급 차단 토글). 끄면 전량 통과.
    learnability_filter_enabled: bool = True
    # 학습 경로 링크 검증: 생성 시점에 리소스 URL 생존 확인 → 죽은 링크(404/410/네트워크 실패)는 검색 링크로 교체.
    # 긴급 차단 토글(끄면 원본 링크 그대로 저장).
    link_verification_enabled: bool = True
    link_verification_timeout_seconds: float = 5.0
    # review_pregeneration_enabled: 배치(06:00)의 리뷰 사전생성 on/off.
    # 기본 False = 온디맨드(유저가 시그널 상세를 열 때만 생성). 긴급 시 True로 사전생성 복귀.
    review_pregeneration_enabled: bool = False
    # cluster_similarity_threshold: 코사인 유사도 클러스터 병합 임계치(초기값, 튜닝 대상)
    cluster_similarity_threshold: float = 0.82
    # relevance_min_similarity: 도메인 앵커 유사도 하한(미만이면 off_domain으로 제외)
    relevance_min_similarity: float = 0.20

    @field_validator("cluster_similarity_threshold", "relevance_min_similarity")
    @classmethod
    def _check_similarity_bounds(cls, v: float, info) -> float:
        # 코사인 유사도는 [-1, 1] 범위. 오설정(예: 82 → 8200%)이 조용히 통과하지 않도록 검증.
        if not -1.0 <= v <= 1.0:
            raise ValueError(
                f"{info.field_name} must be within [-1, 1] (cosine similarity range), got {v}"
            )
        return v

    @model_validator(mode="after")
    def check_required_settings(self) -> "Settings":
        if not self.supabase_url:
            warnings.warn(
                "SUPABASE_URL is not set — Supabase calls will fail",
                RuntimeWarning,
                stacklevel=2,
            )
        if not self.supabase_service_role_key:
            warnings.warn(
                "SUPABASE_SERVICE_ROLE_KEY is not set — database operations will fail",
                RuntimeWarning,
                stacklevel=2,
            )
        if not self.supabase_jwt_secret:
            warnings.warn(
                "SUPABASE_JWT_SECRET is not set — all authenticated endpoints will reject requests",
                RuntimeWarning,
                stacklevel=2,
            )
        if not self.openai_api_key:
            warnings.warn(
                "OPENAI_API_KEY is not set — OpenAI LLM/embedding calls will fail",
                RuntimeWarning,
                stacklevel=2,
            )
        if self.llm_provider == "gemini" and not self.gemini_api_key:
            warnings.warn(
                "LLM_PROVIDER=gemini but GEMINI_API_KEY is not set — Gemini calls will fail",
                RuntimeWarning,
                stacklevel=2,
            )
        if not self.firebase_service_account_json:
            warnings.warn(
                "FIREBASE_SERVICE_ACCOUNT_JSON is not set — FCM Push will be skipped",
                RuntimeWarning,
                stacklevel=2,
            )
        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
