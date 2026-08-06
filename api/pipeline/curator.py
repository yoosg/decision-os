"""학습가치 분류 단계.

clustering 뒤·normalize 앞. cluster_key 단위 토픽으로 묶어 LLM 배치 1회 호출로
keep/drop + 깨끗한 이름을 받아, 뉴스/오피니언 토픽을 드롭하고 keep 토픽의 라벨을 교체한다.

safe-degrade(AD-5): 토글 off / llm 부재 / 호출·파싱·개수불일치 → 입력 전량 통과.
"""
from __future__ import annotations

import json
from dataclasses import replace

from core.config import settings
from pipeline.llm.base import LLMProvider
from pipeline.logger import pipeline_log
from pipeline.models import RawArticle

_STAGE = "curator"


def _group(articles: list[RawArticle]) -> list[tuple[str, list[RawArticle]]]:
    """cluster_key 단위 그룹핑. None 키는 url별 개별 토픽으로. 결정론 정렬."""
    ordered = sorted(articles, key=lambda a: ((a.cluster_key or ""), a.url))
    groups: dict[str, list[RawArticle]] = {}
    order: list[str] = []
    for a in ordered:
        key = a.cluster_key if a.cluster_key is not None else f"__none__:{a.url}"
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(a)
    return [(k, groups[k]) for k in order]


def curate_learnability(
    articles: list[RawArticle], llm: LLMProvider | None, brief_date: str = ""
) -> list[RawArticle]:
    if not articles or not settings.learnability_filter_enabled or llm is None:
        reason = ("empty_input" if not articles
                  else "disabled" if not settings.learnability_filter_enabled
                  else "no_llm")
        pipeline_log(stage=_STAGE, brief_date=brief_date, user_count=0,
                     event="curation_skipped", reason=reason, input=len(articles))
        return list(articles)

    grouped = _group(articles)
    topics = [
        {"id": i, "label": members[0].technology_name, "title": members[0].title}
        for i, (_key, members) in enumerate(grouped)
    ]

    try:
        resp = llm.classify_learnability(topics)
        results = json.loads(resp.content)["results"]
        if len(results) != len(topics):
            raise ValueError(f"results 개수 불일치: {len(results)} != {len(topics)}")
        by_id = {int(r["id"]): r for r in results}
    except Exception as e:
        pipeline_log(stage=_STAGE, brief_date=brief_date, user_count=0, level="warning",
                     event="curation_degraded", error=str(e)[:200], input=len(articles))
        return list(articles)

    out: list[RawArticle] = []
    dropped = 0
    for i, (_key, members) in enumerate(grouped):
        r = by_id.get(i)
        if r is None or not r.get("keep", True):
            dropped += 1
            pipeline_log(stage=_STAGE, brief_date=brief_date, user_count=0,
                         event="topic_dropped",
                         category=(r or {}).get("category"),
                         title=members[0].title, label=members[0].technology_name)
            continue
        name = r["name"]
        out.extend(replace(a, technology_name=name) for a in members)

    pipeline_log(stage=_STAGE, brief_date=brief_date, user_count=0,
                 event="curation_done", input=len(articles),
                 topics=len(topics), dropped=dropped, kept_articles=len(out))
    return out
