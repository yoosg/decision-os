"""RSS/Atom 수집 어댑터 (Story 6.1, AD-16).

feedparser로 피드를 파싱해 RawArticle 목록을 반환한다. 네트워크 요청은
주입받은 공유 httpx.Client가 담당하므로(어댑터가 client를 만들지 않음) 테스트는
client를 mock으로 대체해 오프라인으로 실행할 수 있다.

예외 계약(AD-5): 어댑터는 실패를 삼키지 않고 밖으로 던진다. 소스 격리는
aggregator가 담당한다.
"""
from __future__ import annotations

import feedparser
import httpx

from pipeline.collector.base import BaseCollector
from pipeline.models import RawArticle, SourceType

# technology_name 휴리스틱 — 임시 스톱갭(6.2 의미 클러스터링이 대체). 첫 매치 사용.
_TECH_KEYWORDS = [
    "GPT-5", "GPT-4", "ChatGPT", "OpenAI", "Claude", "Anthropic", "Gemini", "DeepMind",
    "Llama", "Mistral", "DeepSeek", "Qwen", "LangGraph", "LangChain", "LlamaIndex",
    "MCP", "RAG", "Agent", "Diffusion", "Sora", "Whisper", "Hugging Face", "PyTorch",
    "Cursor", "Copilot", "vLLM", "Ollama", "embedding", "fine-tun", "o1", "o3",
]

_GENERAL = "General AI"
_MAX_PER_FEED = 5


def derive_tech(text: str) -> str:
    """제목 등에서 technology_name을 추정. 매치 없으면 "General AI"(빈 값 절대 금지)."""
    low = (text or "").lower()
    for kw in _TECH_KEYWORDS:
        if kw.lower() in low:
            return kw
    return _GENERAL


class RssCollector(BaseCollector):
    """RSS/Atom 피드 한 개를 수집하는 어댑터."""

    def __init__(
        self,
        name: str,
        url: str,
        source_type: SourceType,
        client: httpx.Client,
        max_items: int = _MAX_PER_FEED,
    ) -> None:
        self.name = name
        self._url = url
        self._source_type: SourceType = source_type
        self._client = client
        self._max_items = max_items

    def collect(self) -> list[RawArticle]:
        r = self._client.get(self._url)
        r.raise_for_status()
        feed = feedparser.parse(r.content)

        out: list[RawArticle] = []
        for entry in feed.entries[: self._max_items]:
            title = (getattr(entry, "title", "") or "").strip()
            link = (getattr(entry, "link", "") or "").strip()
            if not title or not link:
                continue
            out.append(
                RawArticle(
                    technology_name=self._technology_name(title, feed),
                    title=title,
                    url=link,
                    source_type=self._source_type,
                )
            )
        return out

    def _technology_name(self, title: str, feed) -> str:
        """서브클래스가 파생 로직을 바꿀 수 있도록 분리(예: GitHub은 repo 문맥 사용)."""
        return derive_tech(title)
