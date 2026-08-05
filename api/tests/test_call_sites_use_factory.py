"""프로바이더 생성이 팩토리로 일원화됐는지 보증(회귀 방지).
production 코드에서 OpenAIProvider(...) 직접 생성이 없어야 한다
(팩토리 모듈과 openai_provider 정의 파일은 예외)."""
import pathlib
import re

API = pathlib.Path(__file__).resolve().parent.parent
ALLOWED = {"pipeline/llm/factory.py", "pipeline/llm/openai_provider.py",
           "pipeline/llm/gemini_provider.py"}
TARGET_FILES = [
    "routers/chat.py", "pipeline/coach.py", "pipeline/reviewer.py",
    "pipeline/orchestrator.py", "pipeline/memory_manager.py",
]


def test_no_direct_openai_provider_construction_in_call_sites():
    pattern = re.compile(r"OpenAIProvider\s*\(")
    for rel in TARGET_FILES:
        src = (API / rel).read_text(encoding="utf-8")
        assert not pattern.search(src), f"{rel} still constructs OpenAIProvider directly"


def test_call_sites_import_factory():
    for rel in TARGET_FILES:
        src = (API / rel).read_text(encoding="utf-8")
        assert "get_llm_provider" in src, f"{rel} does not use get_llm_provider"
