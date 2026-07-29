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
        failures = 0
        for query in self._queries:
            if len(out) >= self._max_total:
                break
            try:
                r = self._client.get(
                    _HN_API,
                    params={"query": query, "tags": "story", "hitsPerPage": self._per_query},
                )
                r.raise_for_status()
                hits = r.json().get("hits", [])
            except Exception:
                # 한 쿼리의 일시 실패(429/500/파싱)가 HN 소스 전체(전 키워드)를 죽이지
                # 않도록 격리 — 나머지 쿼리는 계속 수집한다(AD-5 취지).
                failures += 1
                continue
            for hit in hits:
                if len(out) >= self._max_total:
                    break
                title = (hit.get("title") or "").strip()
                if not title:
                    continue
                url = hit.get("url")
                object_id = hit.get("objectID")
                # 외부 링크도 objectID도 없으면 유효 URL을 만들 수 없어 스킵("item?id=None" 방지).
                if not url and not object_id:
                    continue
                # 외부 링크가 없으면 HN 스레드 URL로 폴백(빈 URL 금지).
                link = url or f"https://news.ycombinator.com/item?id={object_id}"
                out.append(
                    RawArticle(
                        technology_name=derive_tech(title),
                        title=title,
                        url=link,
                        source_type="hn",
                    )
                )
        # 모든 쿼리가 실패하고 하나도 못 모았으면 소스 실패로 표면화 — aggregator가
        # source_failed로 격리·로깅하게 한다(전량 실패가 조용한 0건으로 위장되지 않도록).
        if self._queries and failures == len(self._queries) and not out:
            raise RuntimeError(f"all {failures} HN queries failed")
        return out
