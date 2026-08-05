import warnings
import pytest
from pydantic import ValidationError
from core.config import Settings


def test_llm_provider_defaults_to_openai():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        s = Settings(_env_file=None)
    assert s.llm_provider == "openai"
    assert s.openai_model == "gpt-4o-mini"  # 비용 절감: 기본 모델을 mini로
    assert s.gemini_model == "gemini-2.5-flash"
    assert s.gemini_max_retries == 4
    assert s.gemini_request_delay_sec == 0.0


def test_llm_provider_accepts_gemini():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        s = Settings(_env_file=None, llm_provider="gemini")
    assert s.llm_provider == "gemini"


def test_llm_provider_rejects_unknown_value():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, llm_provider="claude")
