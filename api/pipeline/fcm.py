from __future__ import annotations

import json
import threading
from datetime import date, datetime, timedelta, timezone

import firebase_admin
from firebase_admin import credentials, messaging
from supabase import Client

from pipeline.logger import pipeline_log

_firebase_app: firebase_admin.App | None = None
_firebase_lock = threading.Lock()  # P6: 스레드 안전 초기화

_PAGE_SIZE = 1000
_PUSH_FALLBACK_TITLE = "새 AI 기술 트렌드 브리핑"

# Asia/Seoul 고정 UTC+9 (DST 없음) — 타임존 라이브러리 미도입(5.1/5.2와 동일 판단)
_KST_OFFSET = timedelta(hours=9)


def _parse_utc(ts: str) -> datetime:
    """Supabase TIMESTAMPTZ 문자열을 tz-aware UTC datetime으로 파싱."""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _kst_date(ts: str) -> str:
    """UTC timestamp 문자열 → KST 날짜(ISO) 문자열."""
    return (_parse_utc(ts) + _KST_OFFSET).date().isoformat()


def init_firebase(service_account_json: str) -> bool:
    """Firebase Admin 초기화. 이미 초기화된 경우 스킵. 실패 시 False."""
    global _firebase_app
    if _firebase_app is not None:
        return True
    with _firebase_lock:  # P6: double-checked locking
        if _firebase_app is not None:
            return True
        if not service_account_json:
            return False
        try:
            cred_dict = json.loads(service_account_json)
            cred = credentials.Certificate(cred_dict)
            _firebase_app = firebase_admin.initialize_app(cred)
            return True
        except Exception as e:
            pipeline_log(
                stage="fcm",
                brief_date="",
                user_count=0,
                level="error",
                event="firebase_init_failed",
                error=str(e)[:200],
            )
            return False


def send_daily_brief_push(
    user_id: str,
    fcm_token: str,
    top_signal_title: str,
    brief_date: str,
    signal_id: str,
) -> bool:
    """Daily Brief 준비 알림 FCM Push 전송. 성공 True, 실패 False.

    Story 5.3: data 페이로드(type, signal_id) 추가 — 홈 딥링크·하이라이트 대상 식별용.
    """
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title="오늘의 AI CTO 브리핑이 준비됐습니다",
                body=top_signal_title or _PUSH_FALLBACK_TITLE,  # P11: 빈 문자열 폴백
            ),
            # FCM data 값은 전부 문자열이어야 함 — signal_id는 이미 문자열(UUID)
            data={"type": "daily_brief", "signal_id": signal_id or ""},
            token=fcm_token,
        )
        messaging.send(message)
        pipeline_log(
            stage="fcm",
            brief_date=brief_date,
            user_count=0,
            event="push_sent",
            user_id=user_id,
        )
        return True
    except Exception as e:
        pipeline_log(
            stage="fcm",
            brief_date=brief_date,
            user_count=0,
            level="error",
            event="push_failed",
            user_id=user_id,
            error=str(e)[:200],
        )
        return False


def _fetch_all_completed_briefs(client: Client, brief_date: str) -> list[dict]:
    """completed 상태 Daily Brief 전체 페이지네이션 조회."""
    all_briefs: list[dict] = []
    offset = 0
    today = date.fromisoformat(brief_date)
    while True:
        result = (
            client.table("daily_briefs")
            .select("id,user_id")
            .eq("brief_date", today.isoformat())
            .eq("status", "completed")
            .range(offset, offset + _PAGE_SIZE - 1)
            .execute()
        )
        batch = result.data or []
        all_briefs.extend(batch)
        if len(batch) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE
    return all_briefs


def run_daily_brief_push_job(client: Client, brief_date: str) -> int:
    """오늘 completed Daily Brief 보유 사용자 전체에 FCM Push 전송. 전송 성공 수 반환."""
    briefs = _fetch_all_completed_briefs(client, brief_date)  # P8: 페이지네이션

    if not briefs:
        pipeline_log(
            stage="fcm",
            brief_date=brief_date,
            user_count=0,
            event="no_completed_briefs",
        )
        return 0

    pipeline_log(
        stage="fcm",
        brief_date=brief_date,
        user_count=len(briefs),
        event="push_job_started",
    )

    success_count = 0
    for brief in briefs:
        brief_id = brief["id"]
        user_id = brief["user_id"]
        try:
            # top Signal 제목 조회 (position=1)
            top = (
                client.table("daily_brief_signals")
                .select("signal_id,position")
                .eq("daily_brief_id", brief_id)
                .order("position")
                .limit(1)
                .execute()
            ).data
            if not top:
                continue
            top_signal_id = top[0]["signal_id"]
            signal = (
                client.table("signals")
                .select("title")
                .eq("id", top_signal_id)
                .execute()
            ).data
            # P11: title이 없을 경우 폴백 (send_daily_brief_push에서도 처리됨)
            top_title = (signal[0].get("title") if signal else None) or ""

            # 사용자 FCM 토큰 조회 (여러 기기 지원)
            devices = (
                client.table("user_devices")
                .select("fcm_token")
                .eq("user_id", user_id)
                .execute()
            ).data or []

            for device in devices:
                if send_daily_brief_push(
                    user_id, device["fcm_token"], top_title, brief_date, top_signal_id
                ):
                    success_count += 1

        except Exception as e:
            pipeline_log(
                stage="fcm",
                brief_date=brief_date,
                user_count=len(briefs),
                level="error",
                event="user_push_error",
                user_id=user_id,
                error=str(e)[:200],
            )

    return success_count


# ─── 소유권 조인 헬퍼 (decision → review → project.user_id, review.signal_id → signals.title) ──
# 리마인더 job은 service_role로 실행(RLS 우회) — 명시적 순차 조회로 소유자·기기 식별 (AD-3)


def _fetch_review(client: Client, review_id: str) -> dict | None:
    rows = (
        client.table("reviews")
        .select("project_id,signal_id")
        .eq("id", review_id)
        .limit(1)
        .execute()
    ).data
    return rows[0] if rows else None


def _fetch_project_user(client: Client, project_id: str) -> str | None:
    rows = (
        client.table("projects")
        .select("user_id")
        .eq("id", project_id)
        .limit(1)
        .execute()
    ).data
    return rows[0]["user_id"] if rows else None


def _fetch_signal_title(client: Client, signal_id: str | None) -> str:
    if not signal_id:
        return ""
    rows = (
        client.table("signals")
        .select("title")
        .eq("id", signal_id)
        .limit(1)
        .execute()
    ).data
    return (rows[0].get("title") if rows else None) or ""


def _fetch_user_tokens(client: Client, user_id: str) -> list[str]:
    devices = (
        client.table("user_devices")
        .select("fcm_token")
        .eq("user_id", user_id)
        .execute()
    ).data or []
    return [d["fcm_token"] for d in devices if d.get("fcm_token")]


# ─── Trigger #2: Queue Today 리마인더 ─────────────────────────────────────────


def send_queue_reminder_push(
    user_id: str,
    fcm_token: str,
    signal_title: str,
    signal_id: str,
) -> bool:
    """Queue Today 리마인더 FCM Push 전송. 성공 True, 실패 False."""
    if not fcm_token:  # 빈/None 토큰 사전 가드 (deferred-work.md:180)
        return False
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title="오늘 학습하기로 한 Signal이 남아있습니다",
                body=signal_title or _PUSH_FALLBACK_TITLE,
            ),
            data={"type": "queue_reminder", "signal_id": signal_id or ""},
            token=fcm_token,
        )
        messaging.send(message)
        pipeline_log(
            stage="fcm_queue_reminder",
            brief_date="",
            user_count=0,
            event="push_sent",
            user_id=user_id,
        )
        return True
    except Exception as e:
        pipeline_log(
            stage="fcm_queue_reminder",
            brief_date="",
            user_count=0,
            level="error",
            event="push_failed",
            user_id=user_id,
            error=str(e)[:200],
        )
        return False


def run_queue_reminder_job(client: Client, run_date: str) -> int:
    """20:00 KST: 오늘 queue_timing='today'로 남아있는 Queue 결정 보유 사용자에게 리마인더 전송.

    대상 판정: choice='queue' AND queue_timing='today' AND updated_at의 KST 날짜 == run_date
    (설계 결정 2 — 오늘 today로 설정된 항목만; 이월된 항목은 재알림하지 않음).
    사용자당 1건(가장 최근 updated_at 항목 제목) — 설계 결정 3. 전송 성공 수 반환.
    """
    # 1. today queue 결정 페이지네이션 조회
    decisions: list[dict] = []
    offset = 0
    while True:
        batch = (
            client.table("decisions")
            .select("id,review_id,updated_at")
            .eq("choice", "queue")
            .eq("queue_timing", "today")
            .range(offset, offset + _PAGE_SIZE - 1)
            .execute()
        ).data or []
        decisions.extend(batch)
        if len(batch) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE

    # 2. updated_at KST 날짜 == run_date 필터 (자정 넘겨 이월된 항목 제외)
    todays = [
        d for d in decisions
        if d.get("updated_at") and _kst_date(d["updated_at"]) == run_date
    ]
    if not todays:
        pipeline_log(
            stage="fcm_queue_reminder", brief_date=run_date, user_count=0, event="no_targets"
        )
        return 0

    # 3. 사용자별 그룹 — 가장 최근 updated_at 1건 (설계 결정 3: 사용자당 1 push)
    by_user: dict[str, dict] = {}
    for d in todays:
        review = _fetch_review(client, d["review_id"])
        if not review:
            continue
        user_id = _fetch_project_user(client, review["project_id"])
        if not user_id:
            continue
        cur = by_user.get(user_id)
        # 가장 최근 updated_at 비교는 tz-aware datetime으로 (ISO 문자열 사전식 비교는
        # 소수초/오프셋 표기 변동 시 오정렬 위험 — 같은 파일 _parse_utc 재사용)
        if cur is None or _parse_utc(d["updated_at"]) > _parse_utc(cur["updated_at"]):
            by_user[user_id] = {
                "updated_at": d["updated_at"],
                "signal_id": review.get("signal_id"),
            }

    if not by_user:
        pipeline_log(
            stage="fcm_queue_reminder", brief_date=run_date, user_count=0, event="no_targets"
        )
        return 0

    pipeline_log(
        stage="fcm_queue_reminder",
        brief_date=run_date,
        user_count=len(by_user),
        event="push_job_started",
    )

    success_count = 0
    for user_id, info in by_user.items():
        title = _fetch_signal_title(client, info["signal_id"])
        for token in _fetch_user_tokens(client, user_id):
            if send_queue_reminder_push(user_id, token, title, info["signal_id"] or ""):
                success_count += 1

    return success_count


# ─── Trigger #3: Outcome 입력 요청 리마인더 ────────────────────────────────────


def send_outcome_reminder_push(
    user_id: str,
    fcm_token: str,
    signal_title: str,
    signal_id: str,
) -> bool:
    """Outcome 입력 요청 FCM Push 전송. 성공 True, 실패 False."""
    if not fcm_token:  # 빈/None 토큰 사전 가드
        return False
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title="학습 결과를 기록해 주세요",
                body=signal_title or _PUSH_FALLBACK_TITLE,
            ),
            data={"type": "outcome_reminder", "signal_id": signal_id or ""},
            token=fcm_token,
        )
        messaging.send(message)
        pipeline_log(
            stage="fcm_outcome_reminder",
            brief_date="",
            user_count=0,
            event="push_sent",
            user_id=user_id,
        )
        return True
    except Exception as e:
        pipeline_log(
            stage="fcm_outcome_reminder",
            brief_date="",
            user_count=0,
            level="error",
            event="push_failed",
            user_id=user_id,
            error=str(e)[:200],
        )
        return False


def run_outcome_reminder_job(client: Client, run_date: str) -> int:
    """10:00 KST: learn_now 후 3일 경과 + Outcome 미기록 + 미발송 대상에게 1회 리마인더 전송.

    대상 판정: choice='learn_now' AND outcome_reminder_sent_at IS NULL
    AND created_at <= (now - 3일) AND 연결된 outcomes row 없음 (AC-3).
    전송 후 outcome_reminder_sent_at 기록해 1회 후 중단. 전송 성공 수 반환.
    """
    cutoff_iso = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()

    # 1. 대상 후보 페이지네이션 조회 (서버측 필터: learn_now / 미발송 / 3일 경과)
    decisions: list[dict] = []
    offset = 0
    while True:
        batch = (
            client.table("decisions")
            .select("id,review_id,created_at")
            .eq("choice", "learn_now")
            .is_("outcome_reminder_sent_at", "null")
            .lte("created_at", cutoff_iso)
            .range(offset, offset + _PAGE_SIZE - 1)
            .execute()
        ).data or []
        decisions.extend(batch)
        if len(batch) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE

    if not decisions:
        pipeline_log(
            stage="fcm_outcome_reminder", brief_date=run_date, user_count=0, event="no_targets"
        )
        return 0

    pipeline_log(
        stage="fcm_outcome_reminder",
        brief_date=run_date,
        user_count=len(decisions),
        event="push_job_started",
    )

    success_count = 0
    for d in decisions:
        decision_id = d["id"]
        try:
            # Outcome 존재 시 skip (아직 기록 안 된 대상만)
            outcome = (
                client.table("outcomes")
                .select("id")
                .eq("decision_id", decision_id)
                .limit(1)
                .execute()
            ).data
            if outcome:
                continue

            review = _fetch_review(client, d["review_id"])
            if not review:
                continue
            user_id = _fetch_project_user(client, review["project_id"])
            if not user_id:
                continue

            signal_id = review.get("signal_id")
            tokens = _fetch_user_tokens(client, user_id)
            # 설계 결정 4: 토큰 0건이면 sent_at 미기록 → 기기 등록 후 첫 스캔에서 1회 발송 보존
            if not tokens:
                continue

            title = _fetch_signal_title(client, signal_id)
            for token in tokens:
                if send_outcome_reminder_push(user_id, token, title, signal_id or ""):
                    success_count += 1

            # 토큰 ≥1건: 전송 성공/실패 무관하게 기록해 이후 중단 (1회 = 발송 시도 1회)
            (
                client.table("decisions")
                .update({"outcome_reminder_sent_at": datetime.now(timezone.utc).isoformat()})
                .eq("id", decision_id)
                .execute()
            )
        except Exception as e:
            pipeline_log(
                stage="fcm_outcome_reminder",
                brief_date=run_date,
                user_count=len(decisions),
                level="error",
                event="user_push_error",
                user_id="",
                error=str(e)[:200],
            )

    return success_count
