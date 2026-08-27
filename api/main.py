import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger

from core.config import settings
from routers.chat import router as chat_router
from routers.daily_briefs import router as daily_briefs_router
from routers.decisions import router as decisions_router
from routers.devices import router as devices_router
from routers.engagement import router as engagement_router
from routers.health import router as health_router
from routers.learning_paths import router as learning_paths_router
from routers.onboarding import router as onboarding_router
from routers.outcomes import router as outcomes_router
from routers.project_cards import router as project_cards_router
from routers.reviews import router as reviews_router
from routers.users import router as users_router

# JSON 구조화 로그 설정 (AD-12)
logger = logging.getLogger()
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"levelname": "level", "asctime": "timestamp"},
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.supabase_url and settings.supabase_service_role_key:
        try:
            from core.supabase import get_supabase
            client = get_supabase()
            await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: client.table("user_profiles").select("id").limit(1).execute()
                ),
                timeout=5.0,
            )
            logger.info("Supabase connection verified")
        except asyncio.TimeoutError:
            logger.warning("Supabase connection check timed out")
        except Exception as exc:
            logger.warning("Supabase connection check failed", extra={"error": str(exc)})
    else:
        logger.warning("Supabase credentials not configured — skipping connection check")

    # APScheduler 등록 (lifespan 내부 생성으로 테스트 재초기화 문제 방지)
    from pipeline.orchestrator import (
        run_daily_pipeline,
        run_outcome_reminder_job_entry,
        run_push_job,
        run_queue_reminder_job_entry,
    )

    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    scheduler.add_job(
        run_daily_pipeline,
        CronTrigger(hour=6, minute=0, timezone="Asia/Seoul"),
        id="daily_pipeline",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        run_push_job,
        CronTrigger(hour=9, minute=0, timezone="Asia/Seoul"),
        id="daily_push",
        replace_existing=True,
        misfire_grace_time=300,
    )
    # Story 5.3 Trigger #3: Outcome 입력 요청 리마인더 10:00 KST (설계 결정 5)
    scheduler.add_job(
        run_outcome_reminder_job_entry,
        CronTrigger(hour=10, minute=0, timezone="Asia/Seoul"),
        id="outcome_reminder",
        replace_existing=True,
        misfire_grace_time=300,
    )
    # Story 5.3 Trigger #2: Queue Today 리마인더 20:00 KST
    scheduler.add_job(
        run_queue_reminder_job_entry,
        CronTrigger(hour=20, minute=0, timezone="Asia/Seoul"),
        id="queue_reminder",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.start()
    logger.info(
        "APScheduler started",
        extra={
            "jobs": [
                "daily_pipeline@06:00KST",
                "daily_push@09:00KST",
                "outcome_reminder@10:00KST",
                "queue_reminder@20:00KST",
            ]
        },
    )

    yield

    scheduler.shutdown(wait=False)
    logger.info("APScheduler shutdown")


app = FastAPI(title="Decision OS API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(devices_router, prefix="/api/v1")
app.include_router(onboarding_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(daily_briefs_router, prefix="/api/v1")
app.include_router(reviews_router, prefix="/api/v1")
app.include_router(decisions_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(learning_paths_router, prefix="/api/v1")
app.include_router(outcomes_router, prefix="/api/v1")
app.include_router(project_cards_router, prefix="/api/v1")
app.include_router(engagement_router, prefix="/api/v1")
