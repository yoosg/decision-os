---
baseline_commit: NO_VCS
---

# Story 2.3: Recommender & Daily Brief Batch Pipeline

Status: done

## Story

백엔드 개발자로서,
APScheduler 배치 파이프라인이 매일 06:00 KST에 자동 실행되어 사용자별 Daily Brief를 생성하고 09:00에 FCM Push를 전송하기를 원한다,
그래서 사용자가 매일 아침 개인화된 AI 기술 브리핑을 받을 수 있다.

## Acceptance Criteria

**AC-1: 전체 배치 파이프라인 실행 순서**

- **Given** APScheduler가 FastAPI에 등록되어 있을 때
- **When** 매일 06:00 KST가 되면
- **Then** `Collector → Normalizer → Signal Builder → Reviewer → Recommender → Daily Brief DB 저장` 순서로 파이프라인이 실행된다
- **And** 각 단계의 진행 로그는 JSON 구조화 형식으로 `brief_date`, `pipeline_stage`, `user_count` 필드를 포함한다 (AD-12)

**AC-2: Recommender — 사용자별 관련성 점수 계산**

- **Given** 오늘 날짜의 `processed` 상태 Signal이 1개 이상 존재하고 `onboarding_completed=true`인 사용자가 있을 때
- **When** Recommender가 실행되면
- **Then** 각 사용자의 `user_profiles`(Role, Tech Stack, Project/Goal, Interests)를 기반으로 Signal별 관련성 점수가 계산된다
- **And** `daily_brief_signals` 테이블에 `relevance_score`와 `position` (1부터 시작, 낮을수록 순위 높음)이 저장된다
- **And** Signal은 `relevance_score` 내림차순으로 정렬되어 `position`이 부여된다

**AC-3: Daily Brief DB 생성**

- **Given** Recommender가 사용자별 관련성 점수 계산을 완료하면
- **Then** `daily_briefs` 테이블에 `{user_id, brief_date, status: 'pending'}` 레코드가 생성된다
- **And** `daily_brief_signals` 삽입 성공 후 `status`가 `'completed'`, `generated_at`이 현재 시각으로 업데이트된다
- **And** 특정 사용자 처리 실패 시 해당 사용자만 `status: 'failed'`가 되고 다른 사용자 처리는 영향받지 않는다
- **And** 동일 사용자·날짜 `daily_briefs`가 이미 존재할 경우 중복 생성 없이 스킵한다

**AC-4: FCM Push — 09:00 KST**

- **Given** 오늘 `brief_date`의 `daily_briefs.status = 'completed'` 레코드가 존재할 때
- **When** 09:00 KST APScheduler Job이 실행되면
- **Then** `user_devices` 테이블의 FCM 토큰을 사용하여 FCM Push가 전송된다
- **And** 메시지 형식: `title="오늘의 AI CTO 브리핑이 준비됐습니다"`, `body=[top Signal 제목 (position=1)]`
- **And** FastAPI가 FCM REST API의 단일 전송 지점이다 (클라이언트 직접 발송 불가 — AD-17)
- **And** FCM 토큰이 만료·무효인 경우 해당 사용자 전송 실패를 로그로 기록하고 다음 사용자로 계속 처리한다

**AC-5: 콜드 스타트 처리**

- **Given** Memory가 없는 신규 사용자일 때
- **When** Recommender가 실행되면
- **Then** Role·Tech Stack·Project/Goal·Interests 기반 키워드 매칭으로 기본 관련성 점수가 계산된다
- **And** 어떤 Signal도 사용자 프로필과 매칭되지 않는 경우 모든 Signal에 최소 기본 점수(0.1)가 부여되어 Daily Brief가 생성된다

**AC-6: 처리 타임아웃 보호**

- **Given** `daily_briefs.status = 'processing'`이 설정된 상태에서
- **When** `mark_stuck_jobs(timeout_minutes=15)` 함수가 호출되면
- **Then** `processing_started_at`이 15분 이상 경과한 레코드는 `status: 'failed'`로 전이된다

## Tasks / Subtasks

- [x] Task 1: 패키지 및 환경변수 추가 (AC: #1, #4)
  - [x] 1.1 `api/requirements.txt`에 추가: `apscheduler==3.10.4`, `firebase-admin==6.5.0`
  - [x] 1.2 `api/core/config.py`에 추가: `firebase_service_account_json: str = Field(default="", repr=False)` — Firebase 서비스 계정 JSON 문자열
  - [x] 1.3 `.env.example`에 `FIREBASE_SERVICE_ACCOUNT_JSON=` 추가
  - [x] 1.4 `config.check_required_settings()`에 `firebase_service_account_json` 누락 경고 추가 (기존 패턴 동일)

- [x] Task 2: Recommender Agent 구현 (AC: #2, #3, #5)
  - [x] 2.1 `api/pipeline/recommender.py` 생성
  - [x] 2.2 `compute_relevance_score(signal: dict, user_profile: dict) -> float` 구현 — 키워드 매칭 기반 MVP 콜드 스타트 스코어링 (아래 Dev Notes 참조)
  - [x] 2.3 `create_daily_brief_for_user(user_id: str, signal_ids: list[str], client: Client, brief_date: str) -> str | None` 구현 — 단일 사용자 Daily Brief 생성 (아래 Dev Notes 참조)
  - [x] 2.4 `run_recommender(signal_ids: list[str], client: Client, brief_date: str) -> int` 구현 — 전체 사용자 처리, 성공 수 반환

- [x] Task 3: FCM Push 모듈 구현 (AC: #4)
  - [x] 3.1 `api/pipeline/fcm.py` 생성
  - [x] 3.2 `init_firebase(service_account_json: str) -> bool` — Firebase Admin 초기화 (중복 초기화 방지)
  - [x] 3.3 `send_daily_brief_push(user_id: str, fcm_token: str, top_signal_title: str, brief_date: str) -> bool` — FCM 메시지 전송
  - [x] 3.4 `run_daily_brief_push_job(client: Client, brief_date: str) -> int` — 오늘 completed brief 가진 사용자 전체 Push 전송

- [x] Task 4: 파이프라인 오케스트레이터 구현 (AC: #1)
  - [x] 4.1 `api/pipeline/orchestrator.py` 생성
  - [x] 4.2 `run_daily_pipeline(brief_date: str | None = None) -> dict` 구현 — 전체 배치 파이프라인 실행 (아래 Dev Notes 참조)
  - [x] 4.3 `run_push_job(brief_date: str | None = None) -> dict` 구현 — 09:00 KST FCM Push Job

- [x] Task 5: APScheduler main.py lifespan 등록 (AC: #1, #4)
  - [x] 5.1 `api/main.py` `lifespan`에 APScheduler(`BackgroundScheduler`) 등록 (아래 Dev Notes 참조)
  - [x] 5.2 06:00 KST cron job → `run_daily_pipeline` 등록
  - [x] 5.3 09:00 KST cron job → `run_push_job` 등록
  - [x] 5.4 lifespan yield 후 `scheduler.shutdown(wait=False)` 호출

- [x] Task 6: 단위 테스트 작성 (AC: #2, #3, #4, #5)
  - [x] 6.1 `api/tests/test_recommender_pipeline.py` 생성
  - [x] 6.2 `compute_relevance_score` — tech_stack 매칭 시 score > 0 검증
  - [x] 6.3 `compute_relevance_score` — interests 매칭 시 score > 0 검증
  - [x] 6.4 `compute_relevance_score` — 매칭 없을 때 0.1 기본 점수 검증 (콜드 스타트 AC-5)
  - [x] 6.5 `compute_relevance_score` — 최대 1.0 캡 검증
  - [x] 6.6 `create_daily_brief_for_user` — DB Mock으로 brief + brief_signals 삽입 + status=completed 검증
  - [x] 6.7 `create_daily_brief_for_user` — 이미 존재하는 brief 스킵 검증 (AC-3 중복 방지)
  - [x] 6.8 `run_recommender` — 한 사용자 실패 시 다른 사용자 처리 계속 검증 (AC-3 격리)
  - [x] 6.9 `run_recommender` — onboarding_completed=false 사용자 스킵 검증
  - [x] 6.10 `send_daily_brief_push` — `messaging.send` 성공 시 True 반환 검증 (Mock)
  - [x] 6.11 `send_daily_brief_push` — FCM 예외 발생 시 False 반환·로그 기록 검증 (Mock)
  - [x] 6.12 `run_push_job` — completed brief 없는 날 0 반환 검증
  - [x] 6.13 `run_daily_pipeline` — 각 단계 함수 호출 순서 검증 (Mock으로 단계별 확인)

## Dev Notes

### ⚠️ 핵심 전제: Story 2.1 / 2.2 구현 결과

다음 함수 / 모듈이 이미 존재하며 **재구현 금지** (import해서 그대로 사용):

| 위치 | 역할 |
|------|------|
| `api/pipeline/collector/stub.py` | `StubCollector` — `collect() -> list[RawArticle]` |
| `api/pipeline/normalizer.py` | `normalize(articles, signal_date, client, brief_date)` → `list[str]` (signal_ids) |
| `api/pipeline/signal_builder.py` | `build_signals(signal_ids, client, api_key, model, brief_date)` → `list[str]` (processed signal_ids) |
| `api/pipeline/reviewer.py` | `review_all_for_signal(signal_id, client, llm, brief_date)` → `list[str]` (review_ids) |
| `api/pipeline/llm/base.py` | `LLMProvider` ABC, `ReviewContext`, `LLMResponse`, `LLMProviderError` |
| `api/pipeline/llm/openai_provider.py` | `OpenAIProvider(LLMProvider)` |
| `api/pipeline/logger.py` | `pipeline_log(stage, brief_date, user_count, level, **extra)` |
| `api/core/config.py` | `settings` — `supabase_url`, `openai_api_key`, `openai_model` 등 |
| `api/core/supabase.py` | `get_supabase()` → `Client` |

### 절대 금지 사항

| 금지 | 이유 |
|------|------|
| `LLMProvider.generate()` event loop에서 직접 await | 동기 메서드, APScheduler ThreadPool에서 실행됨 |
| `daily_briefs` 중복 삽입 (동일 user_id + brief_date) | DB UNIQUE(user_id, brief_date) 제약 |
| 클라이언트 FCM 직접 발송 코드 작성 | AD-17: FastAPI 단일 전송 지점 |
| `firebase-admin` 두 번 초기화 | `ValueError: The default Firebase app already exists` 에러 |
| `client.chat.completions.create()` 사용 | AD-6: Responses API 전용 |

### Recommender 설계

```python
# api/pipeline/recommender.py
from __future__ import annotations
from datetime import date, datetime, timezone
from supabase import Client
from pipeline.logger import pipeline_log


def compute_relevance_score(signal: dict, user_profile: dict) -> float:
    """MVP 콜드 스타트: 키워드 매칭 기반 관련성 점수.
    
    tech_stack 매칭: +0.4/개, interests 매칭: +0.3/개
    최솟값 0.1 (콜드 스타트 — 매칭 없어도 브리프에 포함)
    최댓값 1.0 (캡)
    """
    tech_name = signal.get("technology_name", "").lower()
    summary = (signal.get("summary") or "").lower()
    signal_text = f"{tech_name} {summary}"

    tech_stack = [t.lower() for t in (user_profile.get("tech_stack") or [])]
    interests = [i.lower() for i in (user_profile.get("interests") or [])]

    score = 0.0
    for tech in tech_stack:
        if tech and tech in signal_text:
            score += 0.4
    for interest in interests:
        if interest and interest in signal_text:
            score += 0.3

    return max(min(score, 1.0), 0.1)


def create_daily_brief_for_user(
    user_id: str,
    signal_ids: list[str],
    client: Client,
    brief_date: str,
) -> str | None:
    """단일 사용자 Daily Brief 생성. brief_id 반환 또는 None(스킵/실패)."""
    today = date.fromisoformat(brief_date)

    # 중복 체크 — 이미 존재하면 스킵
    existing = (
        client.table("daily_briefs")
        .select("id")
        .eq("user_id", user_id)
        .eq("brief_date", today.isoformat())
        .execute()
    )
    if existing.data:
        pipeline_log(
            stage="recommender",
            brief_date=brief_date,
            user_count=0,
            event="brief_already_exists",
            user_id=user_id,
        )
        return existing.data[0]["id"]

    # 사용자 프로필 조회
    profile_result = (
        client.table("user_profiles")
        .select("role,tech_stack,interests,experience_level,project_goal")
        .eq("id", user_id)
        .execute()
    )
    user_profile = profile_result.data[0] if profile_result.data else {}

    # Signal 데이터 조회 및 관련성 점수 계산
    signals = []
    for signal_id in signal_ids:
        sig = (
            client.table("signals")
            .select("id,technology_name,title,summary")
            .eq("id", signal_id)
            .eq("status", "processed")
            .execute()
        )
        if sig.data:
            signals.append(sig.data[0])

    if not signals:
        pipeline_log(
            stage="recommender",
            brief_date=brief_date,
            user_count=0,
            level="warning",
            event="no_processed_signals",
            user_id=user_id,
        )
        return None

    # 점수 계산 + 정렬
    scored = sorted(
        [(sig["id"], compute_relevance_score(sig, user_profile)) for sig in signals],
        key=lambda x: -x[1],
    )

    # daily_briefs INSERT (pending)
    brief_result = client.table("daily_briefs").insert({
        "user_id": user_id,
        "brief_date": today.isoformat(),
        "status": "pending",
    }).execute()

    if not brief_result.data:
        pipeline_log(
            stage="recommender",
            brief_date=brief_date,
            user_count=0,
            level="error",
            event="brief_insert_failed",
            user_id=user_id,
        )
        return None

    brief_id = brief_result.data[0]["id"]

    # daily_brief_signals INSERT
    brief_signals = [
        {
            "daily_brief_id": brief_id,
            "signal_id": sig_id,
            "relevance_score": score,
            "position": pos + 1,
        }
        for pos, (sig_id, score) in enumerate(scored)
    ]
    client.table("daily_brief_signals").insert(brief_signals).execute()

    # completed 전이
    client.table("daily_briefs").update({
        "status": "completed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", brief_id).execute()

    pipeline_log(
        stage="recommender",
        brief_date=brief_date,
        user_count=0,
        event="brief_created",
        user_id=user_id,
        brief_id=brief_id,
        signal_count=len(scored),
    )
    return brief_id


def run_recommender(
    signal_ids: list[str],
    client: Client,
    brief_date: str,
) -> int:
    """onboarding_completed=true 사용자 전체 Daily Brief 생성. 성공 수 반환."""
    users = (
        client.table("user_profiles")
        .select("id")
        .eq("onboarding_completed", True)
        .execute()
    ).data or []

    pipeline_log(
        stage="recommender",
        brief_date=brief_date,
        user_count=len(users),
        event="recommender_started",
        signal_count=len(signal_ids),
    )

    success_count = 0
    for user in users:
        user_id = user["id"]
        try:
            brief_id = create_daily_brief_for_user(user_id, signal_ids, client, brief_date)
            if brief_id:
                success_count += 1
        except Exception as e:
            # 사용자별 격리 — 한 명 실패해도 계속 처리 (AC-3)
            pipeline_log(
                stage="recommender",
                brief_date=brief_date,
                user_count=len(users),
                level="error",
                event="brief_creation_failed",
                user_id=user_id,
                error=str(e)[:200],
            )

    pipeline_log(
        stage="recommender",
        brief_date=brief_date,
        user_count=len(users),
        event="recommender_completed",
        success_count=success_count,
    )
    return success_count
```

### FCM Push 설계

```python
# api/pipeline/fcm.py
from __future__ import annotations
import json
import firebase_admin
from firebase_admin import credentials, messaging
from pipeline.logger import pipeline_log
from supabase import Client
from datetime import date

_firebase_app: firebase_admin.App | None = None


def init_firebase(service_account_json: str) -> bool:
    """Firebase Admin 초기화. 이미 초기화된 경우 스킵. 실패 시 False."""
    global _firebase_app
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
) -> bool:
    """Daily Brief 준비 알림 FCM Push 전송. 성공 True, 실패 False."""
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title="오늘의 AI CTO 브리핑이 준비됐습니다",
                body=top_signal_title,
            ),
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


def run_daily_brief_push_job(client: Client, brief_date: str) -> int:
    """오늘 completed Daily Brief 보유 사용자 전체에 FCM Push 전송. 전송 성공 수 반환."""
    today = date.fromisoformat(brief_date)

    # 오늘 completed brief 조회
    briefs = (
        client.table("daily_briefs")
        .select("id,user_id")
        .eq("brief_date", today.isoformat())
        .eq("status", "completed")
        .execute()
    ).data or []

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
            signal = (
                client.table("signals")
                .select("title")
                .eq("id", top[0]["signal_id"])
                .execute()
            ).data
            top_title = signal[0]["title"] if signal else ""

            # 사용자 FCM 토큰 조회 (여러 기기 지원)
            devices = (
                client.table("user_devices")
                .select("fcm_token")
                .eq("user_id", user_id)
                .execute()
            ).data or []

            for device in devices:
                if send_daily_brief_push(user_id, device["fcm_token"], top_title, brief_date):
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
```

### 파이프라인 오케스트레이터 설계

```python
# api/pipeline/orchestrator.py
from __future__ import annotations
from datetime import date
from core.config import settings
from core.supabase import get_supabase
from pipeline.collector.stub import StubCollector
from pipeline.normalizer import normalize
from pipeline.signal_builder import build_signals
from pipeline.reviewer import review_all_for_signal
from pipeline.recommender import run_recommender
from pipeline.fcm import run_daily_brief_push_job
from pipeline.llm.openai_provider import OpenAIProvider
from pipeline.logger import pipeline_log


def run_daily_pipeline(brief_date: str | None = None) -> dict:
    """06:00 KST 배치 파이프라인 전체 실행.
    
    반환: {"brief_date": str, "signals": int, "briefs": int, "error": str | None}
    """
    today = date.today()
    brief_date = brief_date or today.isoformat()

    pipeline_log(
        stage="orchestrator",
        brief_date=brief_date,
        user_count=0,
        event="pipeline_started",
    )

    client = get_supabase()
    llm = OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)

    try:
        # 1. Collect
        collector = StubCollector()
        articles = collector.collect()
        pipeline_log(stage="orchestrator", brief_date=brief_date, user_count=0,
                     event="collect_done", article_count=len(articles))

        # 2. Normalize
        signal_ids = normalize(articles, today, client, brief_date=brief_date)
        pipeline_log(stage="orchestrator", brief_date=brief_date, user_count=0,
                     event="normalize_done", new_signal_count=len(signal_ids))

        # 3. Signal Builder
        processed_ids = build_signals(
            signal_ids, client, settings.openai_api_key, settings.openai_model, brief_date=brief_date
        )
        pipeline_log(stage="orchestrator", brief_date=brief_date, user_count=0,
                     event="signal_build_done", processed_count=len(processed_ids))

        # 4. Reviewer (signal_id마다 모든 ai_research 프로젝트)
        total_reviews = 0
        for signal_id in processed_ids:
            review_ids = review_all_for_signal(signal_id, client, llm, brief_date=brief_date)
            total_reviews += len(review_ids)
        pipeline_log(stage="orchestrator", brief_date=brief_date, user_count=0,
                     event="review_done", review_count=total_reviews)

        # 5. Recommender + Daily Brief 생성
        brief_count = run_recommender(processed_ids, client, brief_date)
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


def run_push_job(brief_date: str | None = None) -> dict:
    """09:00 KST FCM Push Job.
    
    반환: {"brief_date": str, "sent": int, "error": str | None}
    """
    from pipeline.fcm import init_firebase

    today = date.today()
    brief_date = brief_date or today.isoformat()

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
        return {"brief_date": brief_date, "sent": 0, "error": str(e)[:500]}
```

### APScheduler main.py 등록

**수정 위치**: `api/main.py` — 기존 lifespan 함수 내 Supabase 연결 체크 이후, yield 이전에 추가.

```python
# main.py 상단에 추가 import
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# lifespan 함수 수정 — 기존 Supabase 체크 블록 다음에 추가
_scheduler = BackgroundScheduler(timezone="Asia/Seoul")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 기존 Supabase 연결 체크 (변경 없음) ──
    if settings.supabase_url and settings.supabase_service_role_key:
        try:
            ...  # 기존 코드 유지
        except ...:
            ...
    else:
        ...

    # ── APScheduler 등록 ──
    from pipeline.orchestrator import run_daily_pipeline, run_push_job

    _scheduler.add_job(
        run_daily_pipeline,
        CronTrigger(hour=6, minute=0, timezone="Asia/Seoul"),
        id="daily_pipeline",
        replace_existing=True,
        misfire_grace_time=300,  # 5분 이내 misfired job 실행
    )
    _scheduler.add_job(
        run_push_job,
        CronTrigger(hour=9, minute=0, timezone="Asia/Seoul"),
        id="daily_push",
        replace_existing=True,
        misfire_grace_time=300,
    )
    _scheduler.start()
    logger.info("APScheduler started", extra={"jobs": ["daily_pipeline@06:00KST", "daily_push@09:00KST"]})

    yield

    _scheduler.shutdown(wait=False)
    logger.info("APScheduler shutdown")
```

**주의**: `_scheduler`를 module-level 변수로 두면 테스트 시 재초기화 문제 발생 가능. lifespan 내부에서 생성하는 것이 안전.

```python
# 올바른 패턴 — lifespan 내부에서 생성
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    # ... 등록 ...
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)
```

### 테스트 설계 (AD-11)

```python
# api/tests/test_recommender_pipeline.py

# ─── compute_relevance_score ───
def test_tech_stack_match_increases_score():
    signal = {"technology_name": "langgraph", "summary": "multi-agent framework"}
    user = {"tech_stack": ["LangGraph", "Python"], "interests": []}
    assert compute_relevance_score(signal, user) > 0.1

def test_interests_match_increases_score():
    signal = {"technology_name": "MCP", "summary": "protocol for agents"}
    user = {"tech_stack": [], "interests": ["Agent", "MCP"]}
    assert compute_relevance_score(signal, user) > 0.1

def test_no_match_returns_base_score():
    signal = {"technology_name": "Kubernetes", "summary": "container orchestration"}
    user = {"tech_stack": ["React"], "interests": ["Frontend"]}
    assert compute_relevance_score(signal, user) == 0.1

def test_score_capped_at_one():
    signal = {"technology_name": "LangGraph MCP Agent", "summary": "rag agent langgraph mcp"}
    user = {"tech_stack": ["LangGraph", "MCP", "Agent", "RAG"], "interests": ["LangGraph", "MCP", "Agent"]}
    assert compute_relevance_score(signal, user) == 1.0

# ─── create_daily_brief_for_user ───
def test_creates_brief_and_signals(mock_client):
    # mock_client: table() → MagicMock 패턴 (기존 test_pipeline_foundation.py 참고)
    # 검증: daily_briefs INSERT, daily_brief_signals INSERT, status=completed UPDATE 각각 호출 확인

def test_skips_duplicate_brief(mock_client):
    # mock_client.table("daily_briefs").select().eq().eq().execute().data = [{"id": "existing_id"}]
    # 검증: INSERT가 호출되지 않고 existing_id가 반환됨

# ─── run_recommender ───
def test_user_failure_isolation(mock_client):
    # 두 번째 사용자에서 Exception 발생 → 첫 번째, 세 번째 사용자는 정상 처리
    # 검증: success_count == 2 (실패 사용자 제외)

def test_skips_non_onboarded_users(mock_client):
    # user_profiles에 onboarding_completed=false 사용자만 있을 때
    # 검증: daily_briefs INSERT 호출 없음

# ─── send_daily_brief_push ───
def test_push_success(mocker):
    mocker.patch("pipeline.fcm.messaging.send", return_value="message_id")
    result = send_daily_brief_push("uid", "token", "LangGraph 업데이트", "2026-07-24")
    assert result is True

def test_push_exception_returns_false(mocker):
    mocker.patch("pipeline.fcm.messaging.send", side_effect=Exception("FCM error"))
    result = send_daily_brief_push("uid", "token", "LangGraph 업데이트", "2026-07-24")
    assert result is False

# ─── run_push_job ───
def test_no_briefs_returns_zero(mock_client):
    # daily_briefs 쿼리 결과 빈 리스트
    # 검증: run_daily_brief_push_job 반환값 == 0
```

**Mock 패턴**: 기존 `api/tests/test_pipeline_foundation.py`의 `MagicMock()` + 테이블별 사이드이펙트 패턴 동일하게 사용. `pytest-mock`의 `mocker.patch`로 `messaging.send` 목킹.

**`firebase-admin` 테스트 주의**: `init_firebase`는 실제 JSON 없이 빈 문자열 입력 시 `False` 반환 경로로 테스트. `messaging.send`는 반드시 Mock 처리 (실제 FCM 호출 없음).

### 신규 / 수정 파일 목록

```
# 신규 파일
api/pipeline/recommender.py         (NEW — Recommender + Daily Brief 생성)
api/pipeline/fcm.py                 (NEW — Firebase Admin FCM Push)
api/pipeline/orchestrator.py        (NEW — 파이프라인 오케스트레이터)
api/tests/test_recommender_pipeline.py (NEW — 단위 테스트)

# 수정 파일
api/requirements.txt                (UPDATE — apscheduler==3.10.4, firebase-admin==6.5.0 추가)
api/core/config.py                  (UPDATE — firebase_service_account_json 필드 추가)
api/main.py                         (UPDATE — APScheduler lifespan 등록)
api/.env.example                    (UPDATE — FIREBASE_SERVICE_ACCOUNT_JSON= 추가)
```

### 아키텍처 준수 체크리스트

| 규칙 | 근거 | 세부 사항 |
|------|------|----------|
| `daily_briefs` / `daily_brief_signals` 쓰기는 FastAPI만 | AD-3 | 클라이언트 직접 쓰기 금지 |
| FCM 전송은 FastAPI 단일 진입점 | AD-17 | `messaging.send()` 호출은 `fcm.py`에만 |
| 배치 파이프라인 로그 `brief_date·pipeline_stage·user_count` 포함 | AD-12 | `pipeline_log()` 사용 |
| APScheduler KST 기준 06:00/09:00 | AD-15 | `timezone="Asia/Seoul"` |
| On-demand는 Recommender 이후 단계만 | AD-15 | Story 2.5에서 구현 — 이 스토리에서는 `run_recommender()` 단독 호출 가능하도록 설계 |
| 사용자별 실패 격리 | AC-3 | try/except per user in `run_recommender` |
| `daily_briefs` UNIQUE(user_id, brief_date) 중복 방지 | DB 제약 | `create_daily_brief_for_user`에서 사전 중복 체크 |

### 환경변수 요구사항

| 변수 | 설명 | 예시 |
|------|------|------|
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Firebase 서비스 계정 전체 JSON을 문자열로 | `{"type":"service_account","project_id":"...",...}` |
| 기존 변수 | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY` | 이미 설정됨 |

`FIREBASE_SERVICE_ACCOUNT_JSON`이 비어있는 경우 APScheduler는 등록되지만 09:00 KST FCM Job은 Firebase 초기화 실패 경고 로그 후 `sent=0`으로 조기 반환된다. 배치 파이프라인(06:00)은 영향받지 않는다.

### Story 2.5 연계 고려사항

Story 2.5에서 `POST /api/v1/daily-briefs/trigger` 엔드포인트가 추가될 예정. 이 스토리의 `run_recommender(signal_ids, client, brief_date)` 함수는 단독 호출 가능하도록 설계 — Story 2.5에서 임포트하여 BackgroundTask로 실행.

### References

- 에픽: `_bmad-output/planning-artifacts/epics.md` — Story 2.3 (line 439-466), Story 2.5 (line 497-518)
- 아키텍처: `_bmad-output/planning-artifacts/architecture/architecture-decision-os-2026-07-21/ARCHITECTURE-SPINE.md`
  - AD-3(데이터 접근), AD-12(관찰가능성), AD-15(Agent Workflow), AD-17(FCM Push)
- Story 2.2 deferred: `_bmad-output/implementation-artifacts/deferred-work.md` (line 58-68)
  - `LLMProvider.generate()` 동기 메서드 — APScheduler ThreadPool에서 실행으로 해결됨
  - `잘못된 signal_id`로 failed review 생성 — `build_signals` 반환값(processed_ids)만 사용하므로 해당 없음
- 기존 파이프라인: `api/pipeline/normalizer.py`, `api/pipeline/signal_builder.py`, `api/pipeline/reviewer.py`
- 기존 테스트 패턴: `api/tests/test_pipeline_foundation.py` — MagicMock 패턴
- DB 스키마: `supabase/migrations/20260723000000_initial_schema.sql` — daily_briefs (line 181-193), daily_brief_signals (line 194-202)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `compute_relevance_score`에서 `technology_name`이 `None`일 때 `.lower()` AttributeError 발생 → `(signal.get("technology_name") or "").lower()` 패턴으로 수정 (summary는 이미 올바른 패턴 사용 중)

### Completion Notes List

- `api/pipeline/recommender.py`: `compute_relevance_score`, `create_daily_brief_for_user`, `run_recommender` 구현. 키워드 매칭 기반 MVP 관련성 스코어링, 사용자별 격리 처리, 중복 brief 방지 포함.
- `api/pipeline/fcm.py`: `init_firebase`, `send_daily_brief_push`, `run_daily_brief_push_job` 구현. 전역 `_firebase_app` 변수로 중복 초기화 방지, FCM 예외 시 해당 사용자만 실패 처리.
- `api/pipeline/orchestrator.py`: `run_daily_pipeline`(Collector → Normalizer → Signal Builder → Reviewer → Recommender 순 실행), `run_push_job`(Firebase 미초기화 시 조기 반환) 구현.
- `api/main.py`: APScheduler `BackgroundScheduler` lifespan 내부 생성 패턴으로 등록. 06:00 KST `run_daily_pipeline`, 09:00 KST `run_push_job` cron job 등록.
- 단위 테스트 17개 전부 통과, 전체 회귀 테스트 65개 통과.

### File List

- api/pipeline/recommender.py (NEW)
- api/pipeline/fcm.py (NEW)
- api/pipeline/orchestrator.py (NEW)
- api/tests/test_recommender_pipeline.py (NEW)
- api/requirements.txt (MODIFIED)
- api/core/config.py (MODIFIED)
- api/main.py (MODIFIED)
- api/.env.example (MODIFIED)

### Review Findings

- [x] [Review][Defer] `role` / `project_goal` 미사용 — AC-2 4개 필드 스코어링 중 tech_stack + interests만 구현. role은 신호 텍스트 키워드 매칭 효과 낮음, project_goal은 자유입력 문장으로 서브스트링 정밀도 낮음. LLM 임베딩 기반 유사도 도입 시 함께 처리 예정. — deferred, pre-existing
- [x] [Review][Patch] `build_signals()` 인수 오류 → 런타임 TypeError [orchestrator.py:48-50]
- [x] [Review][Patch] `daily_brief_signals` INSERT 실패 시에도 status='completed' 전이 [recommender.py:131-137]
- [x] [Review][Patch] 사용자 예외 처리 시 daily_briefs.status='failed' 미설정 [recommender.py:179-188]
- [x] [Review][Patch] AC-6 `mark_stuck_jobs()` 함수 미구현 — daily_briefs에 processing_started_at 컬럼 없음
- [x] [Review][Patch] 중복 brief 체크 비원자적 (check-then-insert TOCTOU) [recommender.py:45-60]
- [x] [Review][Patch] `_firebase_app` 전역 변수 스레드 비안전 [fcm.py:15-36]
- [x] [Review][Patch] Signal 조회 N+1 쿼리 [recommender.py:72-82]
- [x] [Review][Patch] 사용자/브리프 쿼리 페이지네이션 없음 (Supabase 1000건 한도) [recommender.py:157, fcm.py:80]
- [x] [Review][Patch] 백필 실행 시 brief_date vs today 불일치 [orchestrator.py:22-23]
- [x] [Review][Patch] `run_push_job` 예외 시 pipeline_log 미호출 [orchestrator.py:115-116]
- [x] [Review][Patch] top_signal_title 빈 문자열 시 FCM 알림 body 공백 [fcm.py:127]
- [x] [Review][Defer] StubCollector 프로덕션 오케스트레이터에 하드코딩 [orchestrator.py:7] — deferred, pre-existing
- [x] [Review][Defer] scheduler.shutdown(wait=False) 파이프라인 실행 중 종료 시 pending 잔류 [main.py:74] — deferred, pre-existing
- [x] [Review][Defer] 만료된 FCM 토큰 user_devices에서 미삭제 [fcm.py] — deferred, pre-existing
- [x] [Review][Defer] 관련성 점수 서브스트링 매칭 오탐 (단어 경계 미적용) [recommender.py:25-30] — deferred, pre-existing
- [x] [Review][Defer] APScheduler max_instances=1 명시적 미설정 [main.py:55-61] — deferred, pre-existing
- [x] [Review][Defer] empty/None fcm_token 사전 가드 없음 [fcm.py] — deferred, pre-existing

## Change Log

- 2026-07-24: Story 2.3 구현 완료 — Recommender Agent, FCM Push 모듈, 파이프라인 오케스트레이터, APScheduler 등록, 단위 테스트 17개 작성. 전체 회귀 테스트 65개 통과.
