import json
import logging
from datetime import datetime, timezone

from supabase import Client

from pipeline.llm.base import LearningPathContext, LLMProvider, LLMProviderError
from pipeline.llm.openai_provider import LEARNING_PATH_RESOURCE_TYPES, OpenAIProvider
from pipeline.logger import pipeline_log
from core.config import settings
from core.supabase import get_supabase

_log = logging.getLogger(__name__)


def _fetch_one_or_raise(client: Client, table: str, column: str, value: str, select_cols: str, entity_name: str) -> dict:
    """단일 row 조회. 결과 없으면 RuntimeError(entity_name 명시)를 발생시킨다."""
    rows = client.table(table).select(select_cols).eq(column, value).execute().data
    if not rows:
        raise RuntimeError(f"{entity_name} not found: {column}={value}")
    return rows[0]


def _execute_learning_path_pipeline(
    learning_path_id: str,
    decision_id: str,
    signal_id: str,
    client: Client,
    llm: LLMProvider,
) -> bool:
    """
    Learning Path 파이프라인. 성공 시 True 반환.
    실패 시 learning_paths 테이블을 failed로 전이 후 False 반환.
    """
    try:
        # pending → processing 상태 전이
        client.table("learning_paths").update({
            "status": "processing",
            "processing_started_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", learning_path_id).execute()

        # Signal + sources 조회
        signal_data = _fetch_one_or_raise(client, "signals", "id", signal_id, "*", "signal")

        sources = (
            client.table("signal_sources")
            .select("source_type,url,title")
            .eq("signal_id", signal_id)
            .execute()
            .data or []
        )

        # Decision → Review → Project → user_id → user_profiles 조회
        decision_data = _fetch_one_or_raise(client, "decisions", "id", decision_id, "review_id", "decision")
        review_id = decision_data["review_id"]

        review_data = _fetch_one_or_raise(client, "reviews", "id", review_id, "project_id", "review")
        project_id = review_data["project_id"]

        project_data = _fetch_one_or_raise(client, "projects", "id", project_id, "user_id", "project")
        user_id = project_data["user_id"]

        profile_data = (
            client.table("user_profiles")
            .select("role,tech_stack,project_goal,experience_level")
            .eq("id", user_id)
            .execute()
            .data
        )
        profile = profile_data[0] if profile_data else {}

        # LearningPathContext 구성 + LLM 호출
        context = LearningPathContext(
            technology_name=signal_data["technology_name"],
            signal_summary=signal_data.get("summary") or "",
            signal_sources=sources,
            user_role=profile.get("role"),
            user_tech_stack=profile.get("tech_stack") or [],
            user_project_goal=profile.get("project_goal"),
            user_experience_level=profile.get("experience_level"),
        )
        llm_response = llm.generate_learning_path(context)

        # resources JSONB 검증 (5개 항목, type 값 검증)
        payload = json.loads(llm_response.content)
        resources = payload.get("resources")
        if not isinstance(resources, list) or len(resources) != 5:
            raise ValueError(f"resources 배열이 5개가 아님: {resources}")
        resource_types = [r.get("type") for r in resources]
        if resource_types != LEARNING_PATH_RESOURCE_TYPES:
            raise ValueError(f"resources type 순서/값 불일치: {resource_types}")

        # completed 상태 전이 (불변)
        client.table("learning_paths").update({
            "status": "completed",
            "resources": resources,
        }).eq("id", learning_path_id).execute()

        pipeline_log(stage="coach", brief_date="", user_count=0,
                     event="learning_path_completed", learning_path_id=learning_path_id,
                     decision_id=decision_id, signal_id=signal_id)
        return True

    except Exception as e:
        _log.exception(
            "learning_path pipeline failed learning_path_id=%s decision_id=%s signal_id=%s",
            learning_path_id, decision_id, signal_id,
        )
        try:
            client.table("learning_paths").update({
                "status": "failed",
                "error_message": str(e)[:500],
            }).eq("id", learning_path_id).execute()
        except Exception:
            _log.exception(
                "failed to persist 'failed' status for learning_path_id=%s (row may remain stuck at 'processing')",
                learning_path_id,
            )
        pipeline_log(stage="coach", brief_date="", user_count=0,
                     level="error", event="learning_path_failed",
                     learning_path_id=learning_path_id, decision_id=decision_id,
                     signal_id=signal_id, error=str(e)[:200])
        return False


def run_learning_path_from_pending(learning_path_id: str, decision_id: str, signal_id: str) -> None:
    """
    BackgroundTask 진입점. pending INSERT는 이미 완료된 상태이므로
    processing 전이부터 시작한다.
    """
    client = get_supabase()
    llm = OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)
    _execute_learning_path_pipeline(learning_path_id, decision_id, signal_id, client, llm)
