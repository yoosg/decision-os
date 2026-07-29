import warnings

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_role_key: str = Field(default="", repr=False)
    supabase_jwt_secret: str = Field(default="", repr=False)
    cors_origins: list[str] = ["http://localhost:3000"]
    openai_api_key: str = Field(default="", repr=False)
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    firebase_service_account_json: str = Field(default="", repr=False)
    # Story 6.1: 실 수집기 어댑터 — "real"(외부 소스 수집) | "stub"(하드코딩 5건 폴백)
    collector_mode: str = "real"
    # 외부 HTTP 요청 타임아웃(초). 스파이크에서 확인된 타임아웃 이슈 대응.
    collector_timeout_seconds: float = 10.0

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
                "OPENAI_API_KEY is not set — LLM calls will fail",
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
