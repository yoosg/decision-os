import json
import logging

from supabase import Client

from pipeline.llm.base import LLMProvider, MemoryContext
from pipeline.llm.openai_provider import ALLOWED_MEMORY_TYPES, OpenAIProvider
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


def _execute_memory_extraction(outcome_id: str, decision_id: str, client: Client, llm: LLMProvider) -> bool:
    """
    Decision Loop 체인(Signal+Review+Decision+Outcome) 기반 Memory 추출 파이프라인.
    성공 시 memories 테이블에 INSERT 후 True 반환.
    실패 시 예외를 전파하지 않고 로그만 남긴 뒤 False 반환한다 (memories에는 상태 컬럼이 없음).
    """
    try:
        outcome_data = _fetch_one_or_raise(
            client, "outcomes", "id", outcome_id,
            "status,useful,actual_learning_time_min,applied_project_note,memo", "outcome",
        )
        decision_data = _fetch_one_or_raise(
            client, "decisions", "id", decision_id, "choice,memo,review_id", "decision",
        )
        review_data = _fetch_one_or_raise(
            client, "reviews", "id", decision_data["review_id"], "project_id,signal_id,result", "review",
        )
        project_data = _fetch_one_or_raise(
            client, "projects", "id", review_data["project_id"], "user_id", "project",
        )

        signal_id = review_data.get("signal_id")
        if signal_id:
            signal_data = _fetch_one_or_raise(client, "signals", "id", signal_id, "technology_name", "signal")
            technology_name = signal_data["technology_name"]
        else:
            technology_name = None

        result = review_data.get("result")
        one_line_definition = result.get("one_line_definition") if result else None

        context = MemoryContext(
            technology_name=technology_name,
            decision_choice=decision_data["choice"],
            decision_memo=decision_data.get("memo"),
            outcome_status=outcome_data["status"],
            outcome_useful=outcome_data.get("useful"),
            outcome_actual_learning_time_min=outcome_data.get("actual_learning_time_min"),
            outcome_memo=outcome_data.get("memo"),
            outcome_applied_project_note=outcome_data.get("applied_project_note"),
            review_one_line_definition=one_line_definition,
        )

        llm_response = llm.extract_memory(context)
        parsed = json.loads(llm_response.content)
        memory_type = parsed.get("memory_type")
        summary = parsed.get("summary")
        if memory_type not in ALLOWED_MEMORY_TYPES or not isinstance(summary, str) or not summary.strip():
            raise ValueError(f"extract_memory 응답이 유효하지 않음: {parsed}")

        embedding = llm.embed_text(summary)

        client.table("memories").insert({
            "user_id": project_data["user_id"],
            "memory_type": memory_type,
            "summary": summary,
            "embedding": embedding,
            "source_decision_id": decision_id,
        }).execute()

        pipeline_log(stage="memory_manager", brief_date="", user_count=0,
                     event="memory_created", outcome_id=outcome_id, decision_id=decision_id,
                     memory_type=memory_type)
        return True

    except Exception as e:
        _log.exception(
            "memory extraction failed outcome_id=%s decision_id=%s", outcome_id, decision_id,
        )
        pipeline_log(stage="memory_manager", brief_date="", user_count=0,
                     level="error", event="memory_extraction_failed",
                     outcome_id=outcome_id, decision_id=decision_id, error=str(e)[:200])
        return False


def run_memory_manager_from_outcome(outcome_id: str, decision_id: str) -> None:
    """BackgroundTask 진입점. Outcome INSERT 성공 직후 트리거된다."""
    client = get_supabase()
    llm = OpenAIProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        embedding_model=settings.openai_embedding_model,
    )
    _execute_memory_extraction(outcome_id, decision_id, client, llm)
