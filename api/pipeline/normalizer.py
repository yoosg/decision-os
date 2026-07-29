from datetime import date

from supabase import Client

from pipeline.logger import pipeline_log
from pipeline.models import RawArticle


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
        )

    return signal_ids
