import logging
from typing import Any

_pipeline_logger = logging.getLogger("pipeline")


def pipeline_log(
    stage: str,
    brief_date: str,
    user_count: int = 0,
    level: str = "info",
    **extra: Any,
) -> None:
    """AD-12: brief_date·pipeline_stage·user_count 필드 포함 구조화 로그."""
    _pipeline_logger.log(
        getattr(logging, level.upper(), logging.INFO),
        f"[{stage}] brief_date={brief_date}",
        extra={"pipeline_stage": stage, "brief_date": brief_date, "user_count": user_count, **extra},
    )
