# ⚠️ THROWAWAY SPIKE (2026-07-29) — Story 6.1 레퍼런스용. 프로덕션 아님.
# 실행하려면 api/로 복사 후 (feedparser 설치 필요). httpx+feedparser+HN Algolia 패턴 참고.
"""SPIKE (throwaway) — 실 RSS/HN 데이터가 기존 파이프라인에 흐르는지 검증용.

정식 아님. 목적: (1) 실데이터 수집 가능성 확인, (2) 데이터 모양/볼륨/중복/technology_name
휴리스틱의 한계를 눈으로 보고 → 정식 스토리(수집 & Recommender v2) 스코핑 근거 확보.

실행: python3 spike_rss.py            # 수집 + 그룹핑 미리보기(비용 0, DB 미기록)
      python3 spike_rss.py --build   # + 상위 N개를 실제 LLM 시그널 생성(소액 비용)
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

import feedparser
import httpx

from pipeline.collector.base import BaseCollector
from pipeline.models import RawArticle

# RSS 피드 (title, url, source_type)
_FEEDS = [
    ("Hugging Face", "https://huggingface.co/blog/feed.xml", "official_blog"),
    ("Simon Willison", "https://simonwillison.net/atom/everything/", "official_blog"),
    ("Google AI", "https://blog.google/technology/ai/rss/", "official_blog"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "other"),
    ("LangChain", "https://blog.langchain.dev/rss/", "official_blog"),
]
# HackerNews (Algolia) — AI 키워드 최근 스토리
_HN_QUERIES = ["LLM", "OpenAI", "Anthropic Claude", "RAG"]

# technology_name 휴리스틱 — 일부러 단순(첫 매치). 실제로는 클러스터링/LLM이 해야 함.
_TECH_KEYWORDS = [
    "GPT-5", "GPT-4", "ChatGPT", "OpenAI", "Claude", "Anthropic", "Gemini", "DeepMind",
    "Llama", "Mistral", "DeepSeek", "Qwen", "LangGraph", "LangChain", "LlamaIndex",
    "MCP", "RAG", "Agent", "Diffusion", "Sora", "Whisper", "Hugging Face", "PyTorch",
    "Cursor", "Copilot", "vLLM", "Ollama", "embedding", "fine-tun", "o1", "o3",
]

_MAX_PER_FEED = 5
_MAX_HN = 10


def _derive_tech(title: str) -> str:
    low = title.lower()
    for kw in _TECH_KEYWORDS:
        if kw.lower() in low:
            return kw
    return "General AI"


class RssSpikeCollector(BaseCollector):
    def collect(self) -> list[RawArticle]:
        out: list[RawArticle] = []
        seen_urls: set[str] = set()

        with httpx.Client(timeout=10.0, follow_redirects=True,
                          headers={"User-Agent": "decision-os-spike/0.1"}) as client:
            # RSS
            for src, url, stype in _FEEDS:
                try:
                    r = client.get(url)
                    r.raise_for_status()
                    feed = feedparser.parse(r.content)
                    for e in feed.entries[:_MAX_PER_FEED]:
                        link = getattr(e, "link", "")
                        title = getattr(e, "title", "").strip()
                        if not title or not link or link in seen_urls:
                            continue
                        seen_urls.add(link)
                        out.append(RawArticle(
                            technology_name=_derive_tech(title),
                            title=title, url=link, source_type=stype,
                        ))
                    print(f"  [rss] {src}: {min(len(feed.entries), _MAX_PER_FEED)} entries")
                except Exception as ex:
                    print(f"  [rss] {src}: FAIL {type(ex).__name__}: {str(ex)[:60]}")

            # HackerNews (Algolia)
            hn_count = 0
            for q in _HN_QUERIES:
                if hn_count >= _MAX_HN:
                    break
                try:
                    r = client.get("http://hn.algolia.com/api/v1/search_by_date",
                                   params={"query": q, "tags": "story", "hitsPerPage": 3})
                    for hit in r.json().get("hits", []):
                        link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                        title = (hit.get("title") or "").strip()
                        if not title or link in seen_urls or hn_count >= _MAX_HN:
                            continue
                        seen_urls.add(link)
                        hn_count += 1
                        out.append(RawArticle(
                            technology_name=_derive_tech(title),
                            title=title, url=link, source_type="hn",
                        ))
                except Exception as ex:
                    print(f"  [hn] {q}: FAIL {type(ex).__name__}: {str(ex)[:60]}")
            print(f"  [hn] {hn_count} stories")
        return out


def _preview(articles: list[RawArticle]) -> None:
    print(f"\n=== 수집 결과: {len(articles)}건 ===")
    by_src: dict[str, int] = {}
    for a in articles:
        by_src[a.source_type] = by_src.get(a.source_type, 0) + 1
    print("소스별:", dict(by_src))

    # normalize가 하는 것처럼 technology_name으로 그룹핑 미리보기(= 생성될 시그널)
    groups: dict[str, list[RawArticle]] = {}
    for a in articles:
        groups.setdefault(a.technology_name, []).append(a)
    print(f"\n=== technology_name 그룹 = 생성될 시그널 {len(groups)}개 (현재 normalize는 그룹당 1시그널·첫 제목만 사용) ===")
    for tech, arts in sorted(groups.items(), key=lambda x: -len(x[1])):
        print(f"\n▸ {tech}  ({len(arts)}건)")
        for a in arts:
            print(f"    - [{a.source_type}] {a.title[:70]}")


if __name__ == "__main__":
    print("수집 시작…")
    arts = RssSpikeCollector().collect()
    _preview(arts)
    if "--build" in sys.argv:
        print("\n(--build) 상위 3개 그룹을 실제 LLM 시그널로 생성해 봅니다…")
        from core.config import settings
        from pipeline.llm.openai_provider import OpenAIProvider
        llm = OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model,
                             embedding_model=settings.openai_embedding_model)
        groups: dict[str, list[RawArticle]] = {}
        for a in arts:
            groups.setdefault(a.technology_name, []).append(a)
        top = sorted(groups.items(), key=lambda x: -len(x[1]))[:3]
        for tech, g in top:
            sources = [{"source_type": a.source_type, "url": a.url, "title": a.title} for a in g]
            try:
                import json
                res = llm.build_signal_title_summary(tech, sources)
                p = json.loads(res.content)
                print(f"\n▸ {tech}: {p.get('title')}\n    {str(p.get('summary'))[:160]}")
            except Exception as ex:
                print(f"\n▸ {tech}: BUILD FAIL {type(ex).__name__}: {str(ex)[:80]}")
