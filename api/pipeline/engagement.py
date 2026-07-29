"""Story 6.5 — engagement 이벤트 로깅 헬퍼(백엔드 공용, best-effort).

engagement_events 테이블은 "측정용 관측 데이터"일 뿐 핵심 플로우가 아니다(AD-5). 따라서
이 모듈의 모든 쓰기는 best-effort다: 어떤 실패(네트워크·FK 위반·권한 등)도 예외로 전파하지
않고 구조화 경고(event="engagement_log_failed", AD-12)만 남긴다. 호출부(recommender의 brief
생성, decisions 라우터, /engagement 엔드포인트)는 이 함수가 절대 예외를 던지지 않는다고 신뢰하고
호출한다 — brief 생성/decision 응답/화면 렌더가 로깅 실패로 막히지 않도록.
"""
from __future__ import annotations

from typing import Any

from supabase import Client

from pipeline.logger import pipeline_log

_VALID_EVENT_TYPES = {"impression", "open", "read_through", "decision"}


def log_engagement(
    client: Client,
    user_id: str,
    signal_id: str,
    event_type: str,
    *,
    daily_brief_id: str | None = None,
    variant: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """engagement_events에 단일 이벤트 insert (best-effort — 실패해도 예외 전파 없음).

    존재하지 않는 signal_id/user_id는 FK 위반으로 insert가 실패하지만, 그 예외도 삼켜서
    호출부 UX를 막지 않는다(조용히 스킵 + 경고 로그).
    """
    row: dict[str, Any] = {
        "user_id": user_id,
        "signal_id": signal_id,
        "event_type": event_type,
    }
    if daily_brief_id is not None:
        row["daily_brief_id"] = daily_brief_id
    if variant is not None:
        row["variant"] = variant
    if metadata is not None:
        row["metadata"] = metadata

    try:
        client.table("engagement_events").insert(row).execute()
    except Exception as e:  # noqa: BLE001 — best-effort: 모든 실패를 삼킨다(AD-5)
        pipeline_log(
            stage="engagement",
            brief_date="",
            user_count=0,
            level="warning",
            event="engagement_log_failed",
            event_type=event_type,
            signal_id=signal_id,
            error=str(e)[:200],
        )


def log_engagement_bulk(client: Client, rows: list[dict[str, Any]]) -> None:
    """engagement_events에 다건 insert (서버 impression 배치용, best-effort).

    한 번의 insert로 여러 행을 기록한다. 빈 리스트는 no-op. 실패는 전체를 삼키고 경고만 남긴다
    (부분 성공/재시도는 하지 않음 — 관측 데이터라 완결성보다 격리가 우선, AD-5).
    """
    if not rows:
        return
    try:
        client.table("engagement_events").insert(rows).execute()
    except Exception as e:  # noqa: BLE001 — best-effort(AD-5)
        pipeline_log(
            stage="engagement",
            brief_date="",
            user_count=0,
            level="warning",
            event="engagement_log_failed",
            event_type="bulk",
            row_count=len(rows),
            error=str(e)[:200],
        )
