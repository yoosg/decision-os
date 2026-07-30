"""KST(Asia/Seoul) 달력일 헬퍼.

브리핑/리마인더의 '하루' 경계를 한국 기준으로 통일하기 위한 유틸.
Asia/Seoul은 DST가 없어 UTC+9 고정 오프셋으로 안전하게 계산한다
(tz 라이브러리 미도입 — pipeline/fcm.py와 동일 판단).

주의: 여기서 다루는 것은 '달력상 며칠'(brief_date 등)뿐이다.
processing_started_at·generated_at 같은 '순간(timestamp)'은 UTC 저장이 정본이므로
이 모듈을 쓰지 않는다.
"""

from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


def to_kst_date(dt: datetime) -> str:
    """주어진 datetime을 KST 기준 날짜(YYYY-MM-DD)로 변환.

    tz-naive datetime은 UTC로 간주한다(저장 타임스탬프가 UTC이므로 안전한 기본값).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST).date().isoformat()


def today_kst() -> str:
    """KST(UTC+9) 기준 오늘 날짜 YYYY-MM-DD."""
    return to_kst_date(datetime.now(timezone.utc))
