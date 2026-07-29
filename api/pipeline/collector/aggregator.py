"""수집 오케스트레이션 (Story 6.1, AD-5/AD-12).

레지스트리 어댑터를 순회하며:
  1. 각 어댑터 호출을 try/except로 격리 — 한 소스 실패가 배치를 중단시키지 않는다(AD-5).
  2. 소스별 성공/실패·수집 건수를 pipeline_log(stage="collector")로 남긴다(피드 헬스, AD-12).
  3. 전 소스 합산 후 exact 중복 제거(정확 URL + 정규화 제목).

임베딩·클러스터링·LLM은 여기 없음(Story 6.2/6.4 스코프).
"""
from __future__ import annotations

import certifi
import httpx

from core.config import settings
from pipeline.collector.registry import build_collectors
from pipeline.logger import pipeline_log
from pipeline.models import RawArticle

_USER_AGENT = "decision-os/1.0 (+https://github.com/decision-os)"


def run_collectors(brief_date: str = "", timeout: float | None = None) -> list[RawArticle]:
    """활성 소스를 격리 수집하고 exact-dedup된 RawArticle 목록을 반환한다."""
    timeout = settings.collector_timeout_seconds if timeout is None else timeout

    collected: list[RawArticle] = []
    # AC1: certifi CA 번들로 TLS 검증 + 타임아웃. 공유 client를 어댑터에 주입.
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        verify=certifi.where(),
        headers={"User-Agent": _USER_AGENT},
    ) as client:
        for collector in build_collectors(client):
            name = getattr(collector, "name", type(collector).__name__)
            try:
                articles = collector.collect()
            except Exception as e:  # AD-5: 소스 격리 — 실패해도 다음 소스 계속
                pipeline_log(
                    stage="collector",
                    brief_date=brief_date,
                    user_count=0,
                    level="error",
                    event="source_failed",
                    source=name,
                    error=f"{type(e).__name__}: {str(e)[:300]}",
                )
                continue
            collected.extend(articles)
            pipeline_log(
                stage="collector",
                brief_date=brief_date,
                user_count=0,
                event="source_collected",
                source=name,
                article_count=len(articles),
            )

    deduped, removed = _dedup(collected)
    pipeline_log(
        stage="collector",
        brief_date=brief_date,
        user_count=0,
        event="dedup_done",
        removed=removed,
        total=len(deduped),
    )
    return deduped


def _dedup(articles: list[RawArticle]) -> tuple[list[RawArticle], int]:
    """정확 URL 또는 정규화(strip+lower) 제목 기준 exact 중복 제거."""
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    out: list[RawArticle] = []
    removed = 0
    for a in articles:
        url_key = a.url.strip()
        title_key = a.title.strip().lower()
        if url_key in seen_urls or title_key in seen_titles:
            removed += 1
            continue
        seen_urls.add(url_key)
        seen_titles.add(title_key)
        out.append(a)
    return out, removed
