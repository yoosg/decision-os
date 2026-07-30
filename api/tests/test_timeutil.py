"""core.timeutil — KST(UTC+9) 달력일 계산 단위 테스트.

브리핑/리마인더의 '하루' 경계를 한국 기준(Asia/Seoul)으로 통일한다.
DST 없는 고정 오프셋이라 tz 라이브러리 없이 검증 가능(fcm.py와 동일 판단).
"""

from datetime import datetime, timezone

from core.timeutil import KST, to_kst_date, today_kst


def test_to_kst_date_before_utc_midnight_is_next_kst_day():
    # UTC 2026-07-29 23:30 == KST 2026-07-30 08:30 → KST 날짜는 07-30
    dt = datetime(2026, 7, 29, 23, 30, tzinfo=timezone.utc)
    assert to_kst_date(dt) == "2026-07-30"


def test_to_kst_date_at_kst_day_boundary():
    # UTC 15:00 == KST 00:00(다음날) → 경계에서 날짜가 넘어감
    assert to_kst_date(datetime(2026, 7, 29, 15, 0, tzinfo=timezone.utc)) == "2026-07-30"
    # UTC 14:59 == KST 23:59(같은날) → 아직 안 넘어감
    assert to_kst_date(datetime(2026, 7, 29, 14, 59, tzinfo=timezone.utc)) == "2026-07-29"


def test_to_kst_date_accepts_naive_as_utc():
    # naive datetime은 UTC로 간주 (저장 타임스탬프가 UTC이므로 안전한 기본값)
    assert to_kst_date(datetime(2026, 7, 29, 15, 0)) == "2026-07-30"


def test_today_kst_matches_manual_conversion():
    # today_kst()는 '지금'을 KST 날짜로 준다 — 현재 UTC로 직접 변환한 값과 일치해야 함
    assert today_kst() == to_kst_date(datetime.now(timezone.utc))


def test_kst_is_utc_plus_9():
    assert KST.utcoffset(None).total_seconds() == 9 * 3600
