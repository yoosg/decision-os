"""소스 레지스트리 (Story 6.1).

활성 외부 소스 목록을 **코드 상수**로 정의한다. DB 소스 테이블이 아님 — 스키마 확장은
Story 6.3 스코프. 새 소스 추가 = SOURCES에 항목 하나 + (필요 시) 새 어댑터, 하위
파이프라인 무수정(AD-16).

`build_collectors(client)`는 활성 항목만 필터해 공유 httpx.Client가 주입된 어댑터
인스턴스 목록을 만든다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from pipeline.collector.base import BaseCollector
from pipeline.collector.github import GitHubReleasesCollector
from pipeline.collector.hackernews import HackerNewsCollector
from pipeline.collector.rss import RssCollector
from pipeline.models import SourceType


@dataclass(frozen=True)
class Source:
    """레지스트리 항목.

    kind:
      - "rss":    RSS/Atom 피드 — `url` 사용
      - "github": GitHub releases.atom — `url`에 "owner/repo"
      - "hn":     HackerNews Algolia — `queries` 사용
    """

    name: str
    kind: str
    source_type: SourceType
    url: str = ""
    queries: tuple[str, ...] = field(default_factory=tuple)
    enabled: bool = True


# 스파이크 검증 시드: RSS 5개 + HN 키워드 + GitHub Releases 1개.
# enabled=False로 개별 토글 가능(피드 헬스에 따라 끄기).
SOURCES: list[Source] = [
    Source("Hugging Face", "rss", "official_blog", url="https://huggingface.co/blog/feed.xml"),
    Source("Simon Willison", "rss", "official_blog", url="https://simonwillison.net/atom/everything/"),
    Source("Google AI", "rss", "official_blog", url="https://blog.google/technology/ai/rss/"),
    Source("The Verge AI", "rss", "other", url="https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    Source("LangChain", "rss", "official_blog", url="https://blog.langchain.dev/rss/"),
    Source("HackerNews", "hn", "hn", queries=("LLM", "OpenAI", "Anthropic Claude", "RAG")),
    Source("langgraph releases", "github", "github", url="langchain-ai/langgraph"),
]


def _build_one(source: Source, client: httpx.Client) -> BaseCollector:
    if source.kind == "rss":
        return RssCollector(source.name, source.url, source.source_type, client)
    if source.kind == "github":
        return GitHubReleasesCollector(source.url, client, name=source.name)
    if source.kind == "hn":
        return HackerNewsCollector(source.queries, client, name=source.name)
    raise ValueError(f"Unknown source kind: {source.kind!r} ({source.name})")


def build_collectors(
    client: httpx.Client, sources: list[Source] | None = None
) -> list[BaseCollector]:
    """활성 소스만 어댑터 인스턴스로 변환. 공유 client를 각 어댑터에 주입."""
    registry = SOURCES if sources is None else sources
    return [_build_one(s, client) for s in registry if s.enabled]
