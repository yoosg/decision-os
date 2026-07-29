from __future__ import annotations

from datetime import date

from core.config import settings
from core.supabase import get_supabase
from pipeline.collector.aggregator import run_collectors
from pipeline.collector.stub import StubCollector
from pipeline.fcm import (
    init_firebase,
    run_daily_brief_push_job,
    run_outcome_reminder_job,
    run_queue_reminder_job,
)
from pipeline.llm.openai_provider import OpenAIProvider
from pipeline.logger import pipeline_log
from pipeline.normalizer import normalize
from pipeline.recommender import create_daily_brief_for_user, run_recommender
from pipeline.reviewer import review_all_for_signal
from pipeline.signal_builder import build_signals


def run_daily_pipeline(brief_date: str | None = None) -> dict:
    """06:00 KST 배치 파이프라인 전체 실행.

    반환: {"brief_date": str, "signals": int, "briefs": int, "error": str | None}
    """
    # P9: brief_date에서 today 파생 — 백필 시 date.today()와 불일치 방지
    brief_date = brief_date or date.today().isoformat()
    today = date.fromisoformat(brief_date)

    pipeline_log(
        stage="orchestrator",
        brief_date=brief_date,
        user_count=0,
        event="pipeline_started",
    )

    client = get_supabase()
    llm = OpenAIProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        embedding_model=settings.openai_embedding_model,
    )

    try:
        # 1. Collect — Story 6.1: collector_mode에 따라 실 수집기 / stub 폴백 분기
        if settings.collector_mode == "stub":
            articles = StubCollector().collect()
        else:
            articles = run_collectors(brief_date=brief_date)
        pipeline_log(stage="orchestrator", brief_date=brief_date, user_count=0,
                     event="collect_done", article_count=len(articles))

        # 2. Normalize
        signal_ids = normalize(articles, today, client, brief_date=brief_date)
        pipeline_log(stage="orchestrator", brief_date=brief_date, user_count=0,
                     event="normalize_done", new_signal_count=len(signal_ids))

        # 3. Signal Builder — P1: llm 인스턴스 전달 (기존 코드는 api_key/model 문자열 전달로 TypeError)
        processed_ids = build_signals(signal_ids, client, llm, brief_date=brief_date)
        pipeline_log(stage="orchestrator", brief_date=brief_date, user_count=0,
                     event="signal_build_done", processed_count=len(processed_ids))

        # 4. Reviewer (signal_id마다 모든 ai_research 프로젝트)
        total_reviews = 0
        for signal_id in processed_ids:
            review_ids = review_all_for_signal(signal_id, client, llm, brief_date=brief_date)
            total_reviews += len(review_ids)
        pipeline_log(stage="orchestrator", brief_date=brief_date, user_count=0,
                     event="review_done", review_count=total_reviews)

        # 5. Recommender + Daily Brief 생성 (Story 5.4: Memory RAG 개인화 — llm 주입)
        brief_count = run_recommender(processed_ids, client, brief_date, llm)
        pipeline_log(stage="orchestrator", brief_date=brief_date, user_count=0,
                     event="pipeline_completed",
                     signal_count=len(processed_ids),
                     brief_count=brief_count)

        return {
            "brief_date": brief_date,
            "signals": len(processed_ids),
            "briefs": brief_count,
            "error": None,
        }

    except Exception as e:
        pipeline_log(
            stage="orchestrator",
            brief_date=brief_date,
            user_count=0,
            level="error",
            event="pipeline_failed",
            error=str(e)[:500],
        )
        return {
            "brief_date": brief_date,
            "signals": 0,
            "briefs": 0,
            "error": str(e)[:500],
        }


def run_ondemand_brief(user_id: str, brief_date: str) -> None:
    """On-demand Daily Brief 생성 (Recommender 이후 단계만 실행).

    processing 중인 Brief가 있으면 건너뜀.
    non-processing 기존 Brief 삭제 후 오늘 날짜 processed Signal로 재생성.
    """
    client = get_supabase()
    # Story 5.4: 온디맨드 brief도 Memory RAG 개인화 적용 (embedding_model 일치 필수).
    # Provider 구성 실패(예: API 키 미설정) 시 llm=None → 콜드 스타트 폴백으로 안전 저하(AD-5).
    try:
        llm = OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            embedding_model=settings.openai_embedding_model,
        )
    except Exception:
        llm = None
    _deleted_existing = False

    try:
        # processing 상태 Brief 존재 시 조기 반환 (중복 실행 방지)
        processing_check = (
            client.table("daily_briefs")
            .select("id")
            .eq("user_id", user_id)
            .eq("brief_date", brief_date)
            .eq("status", "processing")
            .execute()
        )
        if processing_check.data:
            pipeline_log(
                stage="ondemand",
                brief_date=brief_date,
                user_count=1,
                event="skipped_already_processing",
                user_id=user_id,
            )
            return

        # 기존 non-processing Brief 삭제 (daily_brief_signals는 CASCADE DELETE)
        client.table("daily_briefs").delete().eq("user_id", user_id).eq(
            "brief_date", brief_date
        ).neq("status", "processing").execute()
        _deleted_existing = True

        # 오늘 날짜 processed Signal 조회
        sig_result = (
            client.table("signals")
            .select("id")
            .eq("status", "processed")
            .eq("signal_date", brief_date)
            .execute()
        )
        signal_ids = [r["id"] for r in (sig_result.data or [])]

        create_daily_brief_for_user(user_id, signal_ids, client, brief_date, llm)

        pipeline_log(
            stage="ondemand",
            brief_date=brief_date,
            user_count=1,
            event="ondemand_brief_completed",
            user_id=user_id,
        )

    except Exception as e:
        if _deleted_existing:
            pipeline_log(
                stage="ondemand",
                brief_date=brief_date,
                user_count=1,
                level="error",
                event="brief_lost",
                user_id=user_id,
                error=str(e)[:500],
            )
        pipeline_log(
            stage="ondemand",
            brief_date=brief_date,
            user_count=1,
            level="error",
            event="ondemand_brief_failed",
            user_id=user_id,
            error=str(e)[:500],
        )


def run_push_job(brief_date: str | None = None) -> dict:
    """09:00 KST FCM Push Job.

    반환: {"brief_date": str, "sent": int, "error": str | None}
    """
    brief_date = brief_date or date.today().isoformat()

    if not init_firebase(settings.firebase_service_account_json):
        pipeline_log(
            stage="fcm",
            brief_date=brief_date,
            user_count=0,
            level="warning",
            event="firebase_not_initialized_skip_push",
        )
        return {"brief_date": brief_date, "sent": 0, "error": "firebase not initialized"}

    client = get_supabase()
    try:
        sent = run_daily_brief_push_job(client, brief_date)
        return {"brief_date": brief_date, "sent": sent, "error": None}
    except Exception as e:
        # P10: 예외 시 pipeline_log 기록
        pipeline_log(
            stage="fcm",
            brief_date=brief_date,
            user_count=0,
            level="error",
            event="push_job_failed",
            error=str(e)[:500],
        )
        return {"brief_date": brief_date, "sent": 0, "error": str(e)[:500]}


def run_queue_reminder_job_entry(run_date: str | None = None) -> dict:
    """20:00 KST Queue Today 리마인더 Job (Story 5.3 Trigger #2).

    반환: {"run_date": str, "sent": int, "error": str | None}
    """
    run_date = run_date or date.today().isoformat()

    if not init_firebase(settings.firebase_service_account_json):
        pipeline_log(
            stage="fcm_queue_reminder",
            brief_date=run_date,
            user_count=0,
            level="warning",
            event="firebase_not_initialized_skip_push",
        )
        return {"run_date": run_date, "sent": 0, "error": "firebase not initialized"}

    client = get_supabase()
    try:
        sent = run_queue_reminder_job(client, run_date)
        return {"run_date": run_date, "sent": sent, "error": None}
    except Exception as e:
        pipeline_log(
            stage="fcm_queue_reminder",
            brief_date=run_date,
            user_count=0,
            level="error",
            event="push_job_failed",
            error=str(e)[:500],
        )
        return {"run_date": run_date, "sent": 0, "error": str(e)[:500]}


def run_outcome_reminder_job_entry(run_date: str | None = None) -> dict:
    """10:00 KST Outcome 입력 요청 리마인더 Job (Story 5.3 Trigger #3).

    반환: {"run_date": str, "sent": int, "error": str | None}
    """
    run_date = run_date or date.today().isoformat()

    if not init_firebase(settings.firebase_service_account_json):
        pipeline_log(
            stage="fcm_outcome_reminder",
            brief_date=run_date,
            user_count=0,
            level="warning",
            event="firebase_not_initialized_skip_push",
        )
        return {"run_date": run_date, "sent": 0, "error": "firebase not initialized"}

    client = get_supabase()
    try:
        sent = run_outcome_reminder_job(client, run_date)
        return {"run_date": run_date, "sent": sent, "error": None}
    except Exception as e:
        pipeline_log(
            stage="fcm_outcome_reminder",
            brief_date=run_date,
            user_count=0,
            level="error",
            event="push_job_failed",
            error=str(e)[:500],
        )
        return {"run_date": run_date, "sent": 0, "error": str(e)[:500]}
