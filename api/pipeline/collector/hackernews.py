"""HackerNews 수집 어댑터 (Story 6.1, AD-16).

HN Algolia `search_by_date` REST API(https, tags=story)로 여러 AI 키워드의 최근
스토리를 수집한다. 쿼리별 상한(hitsPerPage)과 전체 상한(_MAX_HN)을 적용한다.

예외 계약(AD-5): 실패는 삼키지 않고 밖으로 던진다. 격리는 aggregator가 담당한다.
"""
from __future__ import annotations

from collections.abc import Sequence

import httpx

from pipeline.collector.base import BaseCollector
from pipeline.collector.rss import derive_tech
from pipeline.models import RawArticle

# 스파이크는 http:// 사용 → https로 교정(certifi TLS 검증 대상).
_HN_API = "https://hn.algolia.com/api/v1/search_by_date"
_MAX_HN = 10
_PER_QUERY = 3


class HackerNewsCollector(BaseCollector):
    """여러 키워드로 HN 최근 스토리를 수집하는 단일 어댑터."""

    def __init__(
        self,
        queries: Sequence[str],
        client: httpx.Client,
        name: str = "HackerNews",
        max_total: int = _MAX_HN,
        per_query: int = _PER_QUERY,
    ) -> None:
        self.name = name
        self._queries = list(queries)
        self._client = client
        self._max_total = max_total
        self._per_query = per_query

    def collect(self) -> list[RawArticle]:
        out: list[RawArticle] = []
        for query in self._queries:
            if len(out) >= self._max_total:
                break
            r = self._client.get(
                _HN_API,
                params={"query": query, "tags": "story", "hitsPerPage": self._per_query},
            )
            r.raise_for_status()
            for hit in r.json().get("hits", []):
                if len(out) >= self._max_total:
                    break
                title = (hit.get("title") or "").strip()
                if not title:
                    continue
                # 외부 링크가 없으면 HN 스레드 URL로 폴백(빈 URL 금지).
                link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                out.append(
                    RawArticle(
                        technology_name=derive_tech(title),
                        title=title,
                        url=link,
                        source_type="hn",
                    )
                )
        return out
