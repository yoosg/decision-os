import json

from pipeline.llm.base import LLMProvider, LLMProviderError
from pipeline.logger import pipeline_log


def build_signals(
    signal_ids: list[str],
    client,          # supabase.Client
    llm: LLMProvider,
    brief_date: str = "",
) -> list[str]:
    """raw 상태 Signal → LLM 제목/요약 생성 + status='processed'. 처리된 signal_id 목록 반환."""
    if not signal_ids:
        return []

    processed_ids: list[str] = []

    for signal_id in signal_ids:
        try:
            signal_result = client.table("signals").select("*").eq("id", signal_id).execute()
            if not signal_result.data:
                continue
            signal_data = signal_result.data[0]

            if signal_data["status"] != "raw":
                pipeline_log(stage="signal_builder", brief_date=brief_date, user_count=0,
                             event="signal_already_processed", signal_id=signal_id)
                continue

            sources_result = (
                client.table("signal_sources")
                .select("source_type,url,title")
                .eq("signal_id", signal_id)
                .execute()
            )
            sources = sources_result.data or []

            llm_response = llm.build_signal_title_summary(signal_data["technology_name"], sources)
            parsed = json.loads(llm_response.content)
            title = parsed.get("title") or signal_data["title"]
            summary = parsed.get("summary") or ""

            update_result = client.table("signals").update({
                "title": title,
                "summary": summary,
                "status": "processed",
            }).eq("id", signal_id).execute()

            if not update_result.data:
                pipeline_log(stage="signal_builder", brief_date=brief_date, user_count=0,
                             level="error", event="signal_update_failed", signal_id=signal_id)
                continue

            processed_ids.append(signal_id)
            pipeline_log(stage="signal_builder", brief_date=brief_date, user_count=0,
                         event="signal_built", signal_id=signal_id,
                         technology_name=signal_data["technology_name"])

        except LLMProviderError as e:
            pipeline_log(stage="signal_builder", brief_date=brief_date, user_count=0,
                         level="error", event="llm_call_failed", signal_id=signal_id, error=str(e))
            continue
        except Exception as e:
            pipeline_log(stage="signal_builder", brief_date=brief_date, user_count=0,
                         level="error", event="signal_build_failed", signal_id=signal_id, error=str(e))
            continue

    return processed_ids
