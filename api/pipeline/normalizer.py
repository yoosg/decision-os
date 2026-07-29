from datetime import date, timezone

from supabase import Client

from pipeline.logger import pipeline_log
from pipeline.models import RawArticle

# Story 6.3: source_type → 출처 권위 등급(0~4). 클러스터 내 "최고 등급"을 signals에 저장해
# 6.4 랭킹이 토픽 신뢰도 대표값으로 쓴다(설계결정 D3). 등급값·매핑은 후속 튜닝 대상.
_SOURCE_AUTHORITY = {
    "official_blog": 4,
    "github": 3,
    "hn": 2,
    "reddit": 1,
    "youtube": 1,
    "other": 0,
}


def _aggregate_metadata(group: list[RawArticle]) -> dict:
    """클러스터(그룹) 멤버 집계로 signals 랭킹 메타데이터 산출(Story 6.3, AC2).

    - published_at: 멤버 중 최신(max). 모두 None이면 None.
    - popularity:   멤버 합.
    - source_authority: 멤버 source_type 등급의 최댓값.
    - cluster_key:  클러스터 내 동일하므로 첫 멤버 값(None 가능).
    값 없는 멤버는 건너뛰고 계속 — 한 멤버 때문에 저장이 실패하지 않는다(safe degrade, AD-5).
    """
    # 수집기는 항상 UTC-aware를 주지만, RawArticle 타입은 naive도 허용한다. naive/aware가
    # 섞이면 max()가 TypeError로 배치 전체를 중단(이 함수는 upsert try 밖에서 호출)하므로,
    # naive는 UTC로 간주해 정규화한 뒤 비교한다(방어적 safe-degrade).
    published_dts = [
        d if d.tzinfo is not None else d.replace(tzinfo=timezone.utc)
        for a in group
        if (d := a.published_at) is not None
    ]
    latest = max(published_dts) if published_dts else None
    return {
        "published_at": latest.isoformat() if latest is not None else None,
        "popularity": sum(a.popularity or 0 for a in group),
        "source_authority": max(
            (_SOURCE_AUTHORITY.get(a.source_type, 0) for a in group), default=0
        ),
        "cluster_key": group[0].cluster_key if group else None,
    }


def normalize(
    articles: list[RawArticle],
    signal_date: date,
    client: Client,
    brief_date: str = "",
) -> list[str]:
    """RawArticle 목록 → signals + signal_sources 저장. 신규 signal_id 목록 반환."""
    groups: dict[str, list[RawArticle]] = {}
    for a in articles:
        groups.setdefault(a.technology_name, []).append(a)

    signal_ids: list[str] = []

    for tech_name, group_articles in groups.items():
        if not tech_name or not tech_name.strip():
            pipeline_log(
                stage="normalizer",
                brief_date=brief_date,
                user_count=0,
                level="warning",
                event="empty_technology_name_skipped",
            )
            continue

        meta = _aggregate_metadata(group_articles)

        try:
            first = group_articles[0]
            result = (
                client.table("signals")
                .upsert(
                    {
                        "technology_name": tech_name,
                        "title": first.title,
                        "signal_date": signal_date.isoformat(),
                        "status": "raw",
                        # Story 6.3 랭킹 메타데이터. ignore_duplicates=True라 conflict 시
                        # no-op(최초 insert 시에만 기록) — MVP 허용(D4).
                        "published_at": meta["published_at"],
                        "popularity": meta["popularity"],
                        "source_authority": meta["source_authority"],
                        "cluster_key": meta["cluster_key"],
                    },
                    on_conflict="technology_name,signal_date",
                    ignore_duplicates=True,
                )
                .execute()
            )
        except Exception:
            pipeline_log(
                stage="normalizer",
                brief_date=brief_date,
                user_count=0,
                level="error",
                event="signal_upsert_failed",
                technology_name=tech_name,
            )
            continue

        if not result.data:
            pipeline_log(
                stage="normalizer",
                brief_date=brief_date,
                user_count=0,
                event="signal_exists_skipped",
                technology_name=tech_name,
                signal_date=signal_date.isoformat(),
            )
            continue

        signal_id = result.data[0]["id"]

        try:
            sources = [
                {
                    "signal_id": signal_id,
                    "source_type": a.source_type,
                    "url": a.url,
                    "title": a.title,
                }
                for a in group_articles
            ]
            sources_result = client.table("signal_sources").insert(sources).execute()
            if not sources_result.data:
                raise RuntimeError("signal_sources insert returned no data")
        except Exception:
            pipeline_log(
                stage="normalizer",
                brief_date=brief_date,
                user_count=0,
                level="error",
                event="signal_sources_insert_failed",
                signal_id=signal_id,
                technology_name=tech_name,
            )
            continue

        signal_ids.append(signal_id)
        pipeline_log(
            stage="normalizer",
            brief_date=brief_date,
            user_count=0,
            event="signal_created",
            signal_id=signal_id,
            technology_name=tech_name,
            source_count=len(group_articles),
            published_at=meta["published_at"],
            popularity=meta["popularity"],
            source_authority=meta["source_authority"],
        )

    return signal_ids
