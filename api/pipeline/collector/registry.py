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
    min_points: int = 0
    tags: tuple[str, ...] = field(default_factory=tuple)
    enabled: bool = True


SOURCES: list[Source] = [
    Source("Hugging Face", "rss", "official_blog", url="https://huggingface.co/blog/feed.xml"),
    Source("Simon Willison", "rss", "official_blog", url="https://simonwillison.net/atom/everything/"),
    Source("Google AI", "rss", "official_blog", url="https://blog.google/technology/ai/rss/"),
    Source("OpenAI Blog", "rss", "official_blog", url="https://openai.com/blog/rss.xml"),
    Source("langgraph releases", "github", "github", url="langchain-ai/langgraph"),
    Source("langchain releases", "github", "github", url="langchain-ai/langchain"),
    Source("llama_index releases", "github", "github", url="run-llama/llama_index"),
    Source("vllm releases", "github", "github", url="vllm-project/vllm"),
    Source("ollama releases", "github", "github", url="ollama/ollama"),
    Source("llama.cpp releases", "github", "github", url="ggml-org/llama.cpp"),
    Source("HackerNews", "hn", "hn", queries=("LLM", "OpenAI", "Anthropic Claude", "RAG"), min_points=50),
    Source("Show HN AI", "hn", "hn", queries=("AI", "LLM"), tags=("show_hn",), min_points=10),
]


def _build_one(source: Source, client: httpx.Client) -> BaseCollector:
    if source.kind == "rss":
        return RssCollector(source.name, source.url, source.source_type, client)
    if source.kind == "github":
        return GitHubReleasesCollector(source.url, client, name=source.name)
    if source.kind == "hn":
        return HackerNewsCollector(
            source.queries, client, name=source.name,
            min_points=source.min_points, tags=source.tags,
        )
    raise ValueError(f"Unknown source kind: {source.kind!r} ({source.name})")


def build_collectors(
    client: httpx.Client, sources: list[Source] | None = None
) -> list[BaseCollector]:
    """활성 소스만 어댑터 인스턴스로 변환. 공유 client를 각 어댑터에 주입."""
    registry = SOURCES if sources is None else sources
    return [_build_one(s, client) for s in registry if s.enabled]
