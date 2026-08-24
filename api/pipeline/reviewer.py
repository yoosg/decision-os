import json
import logging
from datetime import datetime, timezone

from supabase import Client

from pipeline.llm.base import LLMProvider, LLMProviderError, ReviewContext, REQUIRED_SECTIONS
from pipeline.llm.prompts import parse_and_validate_card
from pipeline.logger import pipeline_log
from core.config import settings
from core.supabase import get_supabase

_log = logging.getLogger(__name__)


def _execute_review_pipeline(
    review_id: str,
    signal_id: str,
    project_id: str,
    client: Client,
    llm: LLMProvider,
    brief_date: str = "",
) -> bool:
    """
    Review 파이프라인 step 2–7. 성공 시 True 반환.
    실패 시 reviews 테이블을 failed로 전이 후 False 반환.
    """
    try:
        # 2) processing 상태 전이
        client.table("reviews").update({
            "status": "processing",
            "processing_started_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", review_id).execute()

        # 3) Signal + sources + user profile 조회
        signal_data = client.table("signals").select("*").eq("id", signal_id).execute().data
        if not signal_data:
            raise RuntimeError(f"signal {signal_id} not found")
        signal_data = signal_data[0]

        sources = (
            client.table("signal_sources")
            .select("source_type,url,title")
            .eq("signal_id", signal_id)
            .execute()
            .data or []
        )

        project_data = client.table("projects").select("user_id").eq("id", project_id).execute().data
        if not project_data:
            raise RuntimeError(f"project {project_id} not found")
        user_id = project_data[0]["user_id"]

        profile_data = (
            client.table("user_profiles")
            .select("role,tech_stack,interests,experience_level")
            .eq("id", user_id)
            .execute()
            .data
        )
        profile = profile_data[0] if profile_data else {}

        # 4) context_snapshot 저장
        review_type_value = "project_card" if settings.beginner_card_mode_enabled else "research"
        context_snapshot = {
            "schema_version": 1,
            "review_type": review_type_value,
            "payload": {
                "signal": {
                    "id": signal_id,
                    "technology_name": signal_data["technology_name"],
                    "title": signal_data["title"],
                    "summary": signal_data.get("summary"),
                    "signal_date": str(signal_data["signal_date"]),
                },
                "sources": sources,
                "user_profile": {
                    "role": profile.get("role"),
                    "tech_stack": profile.get("tech_stack", []),
                    "interests": profile.get("interests", []),
                    "experience_level": profile.get("experience_level"),
                },
            },
        }
        client.table("reviews").update({
            "context_snapshot": context_snapshot,
        }).eq("id", review_id).execute()

        # 5) ReviewContext 빌드 + LLM 호출
        context = ReviewContext(
            technology_name=signal_data["technology_name"],
            signal_sources=sources,
            user_role=profile.get("role"),
            user_tech_stack=profile.get("tech_stack") or [],
            user_interests=profile.get("interests") or [],
            user_experience_level=profile.get("experience_level"),
        )

        # 6) 생성 + 검증 (토글에 따라 카드 / 13섹션)
        if settings.beginner_card_mode_enabled:
            llm_response = llm.generate_card(context)
            parse_and_validate_card(llm_response.content)
            payload = json.loads(llm_response.content)
        else:
            llm_response = llm.generate(context)
            payload = json.loads(llm_response.content)
            missing = [k for k in REQUIRED_SECTIONS if k not in payload]
            if missing:
                raise ValueError(f"LLM 응답에 필수 섹션 누락: {missing}")

            ltd = payload.get("learning_time_difficulty")
            if not isinstance(ltd, dict) or "estimated_hours" not in ltd or "difficulty" not in ltd:
                raise ValueError(f"learning_time_difficulty 하위 필드 누락 또는 형식 오류: {ltd}")

            honest_box = payload.get("honest_box")
            if not isinstance(honest_box, dict):
                payload["honest_box"] = {"content": str(honest_box) if honest_box is not None else "", "severity": "standard"}
            elif honest_box.get("severity") not in ("standard", "high"):
                payload["honest_box"]["severity"] = "standard"

        result = {
            "schema_version": 1,
            "review_type": review_type_value,
            "payload": payload,
        }

        # 7) completed 상태 전이 (불변)
        client.table("reviews").update({
            "status": "completed",
            "review_type": review_type_value,
            "result": result,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", review_id).execute()

        pipeline_log(stage="reviewer", brief_date=brief_date, user_count=0,
                     event="review_completed", review_id=review_id, playbook_type="ai_research",
                     signal_id=signal_id)
        return True

    except Exception as e:
        try:
            client.table("reviews").update({
                "status": "failed",
                "error_message": str(e)[:500],
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", review_id).execute()
        except Exception:
            pass
        pipeline_log(stage="reviewer", brief_date=brief_date, user_count=0,
                     level="error", event="review_failed",
                     review_id=review_id, playbook_type="ai_research",
                     signal_id=signal_id, error=str(e)[:200])
        return False


def review_signal(
    signal_id: str,
    project_id: str,
    client: Client,
    llm: LLMProvider,
    brief_date: str = "",
) -> str | None:
    """
    Signal 하나에 대한 Research Review 생성.
    상태 머신: pending → processing → completed | failed (불변)
    반환: review_id (성공) 또는 None (실패)
    """
    review_id: str | None = None
    try:
        # 1) Review 레코드 생성 (pending)
        insert_result = client.table("reviews").insert({
            "project_id": project_id,
            "signal_id": signal_id,
            "playbook_type": "ai_research",
            "review_type": "research",
            "status": "pending",
        }).execute()
        if not insert_result.data:
            pipeline_log(stage="reviewer", brief_date=brief_date, user_count=0,
                         level="error", event="review_insert_failed",
                         signal_id=signal_id, playbook_type="ai_research")
            return None
        review_id = insert_result.data[0]["id"]
    except Exception as e:
        pipeline_log(stage="reviewer", brief_date=brief_date, user_count=0,
                     level="error", event="review_failed",
                     review_id=None, playbook_type="ai_research",
                     signal_id=signal_id, error=str(e)[:200])
        return None

    success = _execute_review_pipeline(review_id, signal_id, project_id, client, llm, brief_date)
    return review_id if success else None


def run_review_from_pending(review_id: str, signal_id: str, project_id: str) -> None:
    """
    BackgroundTask 진입점. pending INSERT는 이미 완료된 상태이므로
    step 2(processing 전이)부터 시작한다.
    """
    from pipeline.llm.factory import get_llm_provider  # lazy import: Gemini 의존성 분리
    client = get_supabase()
    llm = get_llm_provider()
    _execute_review_pipeline(review_id, signal_id, project_id, client, llm)


def review_all_for_signal(
    signal_id: str,
    client: Client,
    llm: LLMProvider,
    brief_date: str = "",
) -> list[str]:
    """processed Signal에 대해 모든 ai_research 프로젝트의 Review 생성."""
    projects = (
        client.table("projects")
        .select("id")
        .eq("playbook_type", "ai_research")
        .execute()
        .data or []
    )
    review_ids: list[str] = []
    for project in projects:
        rid = review_signal(signal_id, project["id"], client, llm, brief_date)
        if rid:
            review_ids.append(rid)
    return review_ids
