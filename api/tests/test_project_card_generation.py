import pytest

from pipeline.llm.base import LLMProviderError, ReviewContext
from pipeline.llm.prompts import parse_and_validate_card
from tests.mocks import VALID_CARD_RESPONSE, MockLLMProvider


def test_mock_generate_card_returns_valid_card():
    llm = MockLLMProvider()
    ctx = ReviewContext(technology_name="간단한 챗봇", signal_sources=[])
    resp = llm.generate_card(ctx)
    parse_and_validate_card(resp.content)  # 예외 없이 통과
    assert resp.model == "mock"


def test_valid_card_response_constant_passes_validation():
    parse_and_validate_card(VALID_CARD_RESPONSE)


def test_mock_generate_card_raises_when_configured():
    llm = MockLLMProvider(raise_error=True)
    ctx = ReviewContext(technology_name="x", signal_sources=[])
    with pytest.raises(LLMProviderError):
        llm.generate_card(ctx)
