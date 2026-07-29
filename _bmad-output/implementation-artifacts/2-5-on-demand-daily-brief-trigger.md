---
baseline_commit: NO_VCS
---

# Story 2.5: On-demand Daily Brief Trigger

Status: review

## Story

사용자로서,
신규 가입·프로필 변경·Brief 실패 시 Daily Brief를 즉시 요청할 수 있기를 원한다,
그래서 배치 주기를 기다리지 않고도 최신 Daily Brief를 받을 수 있다.

## Acceptance Criteria

**AC-1: POST /api/v1/daily-briefs/trigger — 202 즉시 응답 + BackgroundTask**

- **Given** 인증된 사용자가 `POST /api/v1/daily-briefs/trigger`를 호출하면
- **Then** 202 Accepted가 즉시 반환된다 (`{"data": {"queued": true, "brief_date": "YYYY-MM-DD"}, "error": null}`)
- **And** BackgroundTask로 Recommender 이후 단계만 실행된다 (Signal은 `signals` 테이블의 오늘 날짜 `processed` 상태 Signal 사용; Collector/Normalizer/Reviewer 재실행 없음)
- **And** 인증 없이 호출 시 401 반환된다

**AC-2: 프로필 변경 후 자동 on-demand 트리거**

- **Given** 사용자가 프로필을 수정했을 때
- **When** `PATCH /api/v1/users/profile` 완료 후
- **Then** On-demand Brief 트리거가 BackgroundTask로 자동 실행되어 새 프로필 기반 Brief가 생성된다
- **And** `PATCH` 응답 자체는 202가 아닌 200으로 즉시 반환된다 (기존 동작 유지)

**AC-3: Daily Brief 완료 시 홈 화면 자동 반영**

- **Given** 홈 화면이 Supabase Realtime으로 `daily_briefs` 테이블을 구독 중일 때
- **When** BackgroundTask가 Brief를 `completed`로 전환하면
- **Then** 수동 새로고침 없이 자동으로 SignalCard 목록이 표시된다
- **Note** 이 기능은 **Story 2.4에서 이미 구현 완료**됨 — 이 스토리에서 프론트엔드 코드 변경 없음

## Tasks / Subtasks

### [BACKEND] FastAPI On-demand 트리거 구현

- [x] Task 1: `api/pipeline/orchestrator.py`에 `run_ondemand_brief(user_id, brief_date)` 추가 (AC: #1, #2)
  - [x] 1.1 함수 시그니처: `def run_ondemand_brief(user_id: str, brief_date: str) -> None`
  - [x] 1.2 `processing` 상태 Brief가 이미 존재하면 조기 반환 (중복 실행 방지)
  - [x] 1.3 기존 `non-processing` Brief 삭제: `.neq("status", "processing")` 필터로 DELETE
        - `daily_brief_signals`는 CASCADE DELETE이므로 별도 삭제 불필요 (DB 스키마 확인됨)
  - [x] 1.4 오늘 날짜 `processed` 상태 Signal 조회:
        ```python
        sig_result = client.table("signals").select("id").eq("status", "processed").eq("signal_date", brief_date).execute()
        signal_ids = [r["id"] for r in (sig_result.data or [])]
        ```
  - [x] 1.5 `create_daily_brief_for_user(user_id, signal_ids, client, brief_date)` 호출
  - [x] 1.6 `pipeline_log(stage="ondemand", brief_date=brief_date, user_count=1, ...)` 로그 기록 (AD-12)
  - [x] 1.7 예외 처리: except Exception → `pipeline_log(level="error", ...)` 기록 후 re-raise 않음

- [x] Task 2: `api/routers/daily_briefs.py` 생성 — `POST /daily-briefs/trigger` (AC: #1)
  - [x] 2.1 `router = APIRouter(prefix="/daily-briefs", tags=["daily-briefs"])`
  - [x] 2.2 엔드포인트 시그니처:
        ```python
        @router.post("/trigger", status_code=202, response_model=APIResponse)
        def trigger_daily_brief(
            background_tasks: BackgroundTasks,
            user_id: Annotated[str, Depends(get_current_user)],
        ) -> APIResponse:
        ```
  - [x] 2.3 `brief_date = date.today().isoformat()` 사용
  - [x] 2.4 `background_tasks.add_task(run_ondemand_brief, user_id, brief_date)`
  - [x] 2.5 `return APIResponse(data={"queued": True, "brief_date": brief_date})`

- [x] Task 3: `api/main.py` — `daily_briefs_router` 등록 (AC: #1)
  - [x] 3.1 `from routers.daily_briefs import router as daily_briefs_router` 추가
  - [x] 3.2 `app.include_router(daily_briefs_router, prefix="/api/v1")` 추가 (기존 라우터 등록 패턴 준수)

- [x] Task 4: `api/routers/users.py` — 프로필 업데이트 후 on-demand 트리거 (AC: #2)
  - [x] 4.1 `update_profile` 함수에 `background_tasks: BackgroundTasks` 파라미터 추가
  - [x] 4.2 `from pipeline.orchestrator import run_ondemand_brief` 임포트 추가
  - [x] 4.3 `from datetime import date` 임포트 추가
  - [x] 4.4 DB 업데이트 성공 후: `background_tasks.add_task(run_ondemand_brief, user_id, date.today().isoformat())`
  - [x] 4.5 함수 시그니처 업데이트:
        ```python
        def update_profile(
            body: ProfileUpdateRequest,
            background_tasks: BackgroundTasks,
            user_id: Annotated[str, Depends(get_current_user)],
        ) -> APIResponse:
        ```

- [x] Task 5: `api/tests/test_daily_briefs_trigger.py` 생성 (AC: #1, #2)
  - [x] 5.1 `test_trigger_requires_auth()` — 인증 없이 401
  - [x] 5.2 `test_trigger_returns_202()` — JWT Mock → 202 + `{"data": {"queued": true, ...}}`
  - [x] 5.3 `test_run_ondemand_brief_skips_if_processing()` — `processing` Brief 존재 시 DELETE 미호출
  - [x] 5.4 `test_run_ondemand_brief_deletes_failed_brief()` — `failed` Brief 삭제 후 재생성
  - [x] 5.5 `test_run_ondemand_brief_deletes_completed_brief()` — `completed` Brief 삭제 후 재생성 (프로필 변경 케이스)
  - [x] 5.6 `test_run_ondemand_brief_no_signals_today()` — Signal 없을 때 graceful 처리
  - [x] 5.7 기존 Mock 패턴: `unittest.mock.MagicMock()` 사용 (AD-11: 비즈니스 로직 테스트 — Mock 허용)

## Dev Notes

### 핵심 설계 원칙

**AD-15 — On-demand는 Recommender 이후만 실행:**
- Signal 수집·정규화·Reviewer는 배치에서 이미 실행됨
- On-demand는 오늘 날짜 `signals.status = 'processed'` Signal만 사용
- StubCollector 재실행 없음 — 단순히 기존 Signal로 Recommender 재실행

**AD-5 — 202 즉시 응답:**
- 엔드포인트는 BackgroundTask를 등록하고 즉시 반환
- 완료 감지는 Supabase Realtime (프론트엔드 Story 2.4에서 이미 구현됨)

**AD-3 — daily_briefs 쓰기는 FastAPI만:**
- DELETE도 FastAPI 경유 (service_role)
- 프론트엔드는 Supabase Realtime으로 결과만 구독

### 기존 코드 재사용 — 반드시 확인

**`api/pipeline/recommender.py`의 `create_daily_brief_for_user()`:**
```python
def create_daily_brief_for_user(
    user_id: str,
    signal_ids: list[str],
    client: Client,
    brief_date: str,
) -> str | None:
```
- 중복 체크 로직이 내장되어 있으나 기존 Brief가 있으면 그냥 반환함
- **따라서 `run_ondemand_brief`에서 먼저 DELETE한 후 호출해야 함**
- 이 함수가 전체 Brief 생성 플로우(`pending → processing → completed`)를 동기로 처리함
- `signal_ids=[]`이면 `None`을 반환하고 Brief를 생성하지 않음 (Signal 없음 상태로 남음)

**`api/pipeline/orchestrator.py`의 기존 구조:**
```python
# 기존 함수들
def run_daily_pipeline(brief_date: str | None = None) -> dict: ...
def run_push_job(brief_date: str | None = None) -> dict: ...
```
- `run_ondemand_brief`는 이 파일의 동일한 패턴으로 추가

**`api/pipeline/logger.py`의 `pipeline_log()`:**
```python
pipeline_log(stage="ondemand", brief_date=brief_date, user_count=1, event="...", ...)
```
- `stage="ondemand"` 사용 (배치와 구분)
- AD-12: `brief_date`, `pipeline_stage`, `user_count` 필드 필수

### daily_briefs 테이블 UNIQUE 제약

```sql
UNIQUE (user_id, brief_date)
```
- 사용자당 날짜별 1개의 Brief만 허용
- **따라서 기존 Brief를 DELETE하지 않으면 INSERT가 UNIQUE 충돌로 실패함**
- `create_daily_brief_for_user`의 중복 체크가 이를 우회하여 기존 레코드를 반환하므로, 반드시 먼저 DELETE해야 함

### daily_brief_signals CASCADE DELETE 확인됨

```sql
daily_brief_signals.daily_brief_id REFERENCES public.daily_briefs(id) ON DELETE CASCADE
```
- `daily_briefs` 삭제 시 연결된 `daily_brief_signals` 자동 삭제
- 별도 DELETE 불필요

### processing 상태 Brief 처리

`run_ondemand_brief`에서 `processing` 상태 Brief가 있으면:
- 이미 Brief 생성 중 → 삭제하면 데이터 무결성 문제 발생
- **건너뛰고 반환** (중복 실행 방지)
- 이 경우 Realtime이 자연스럽게 완료를 전달

### Signal 없음 엣지케이스

오늘 날짜 `processed` Signal이 없는 경우:
- `create_daily_brief_for_user(user_id, [], client, brief_date)` 호출
- 함수 내부에서 `if not signals: return None` → Brief가 생성되지 않음
- Realtime 이벤트 없음 → 홈 화면에서 이전 삭제된 Brief가 없으므로 "generating" 상태 유지
- 이는 배치가 아직 오늘 Signal을 생성하지 않은 경우 발생 — 의도된 동작

### 프론트엔드: 변경 없음

Story 2.4에서 이미 구현된 항목 (변경 필요 없음):

**Web (`web/src/components/home/daily-brief-content.tsx`):**
- `handleRetry()` (line 161): 이미 `POST /api/v1/daily-briefs/trigger` 호출
- Realtime 구독 (line 118): 이미 `daily_briefs` 테이블 변경 감지 후 자동 업데이트

**Flutter (`mobile/lib/features/home/screens/home_screen.dart`):**
- `_handleRetry()` (line 26): 이미 `POST /api/v1/daily-briefs/trigger` 호출
- `dailyBriefStreamProvider` (daily_brief_provider.dart): 이미 Realtime 스트림 구독

### 패턴 주의사항

**BackgroundTasks 파라미터 순서:**
FastAPI에서 `BackgroundTasks`는 일반 파라미터로 선언 (Depends 불필요):
```python
def trigger_daily_brief(
    background_tasks: BackgroundTasks,  # 먼저
    user_id: Annotated[str, Depends(get_current_user)],  # Depends 다음
) -> APIResponse:
```

**Supabase `.neq()` 필터:**
```python
client.table("daily_briefs").delete().eq("user_id", user_id).eq("brief_date", brief_date).neq("status", "processing").execute()
```

**APIResponse with 202:**
```python
from fastapi import status
from fastapi.responses import JSONResponse

# 또는 response_model=APIResponse + status_code=202 데코레이터 사용
@router.post("/trigger", status_code=202, response_model=APIResponse)
def trigger_daily_brief(...) -> APIResponse:
    return APIResponse(data={"queued": True, "brief_date": brief_date})
```

### 테스트 패턴 (기존 코드 준수)

`api/tests/test_recommender_pipeline.py` 패턴:
```python
from unittest.mock import MagicMock, patch

def test_run_ondemand_brief_skips_if_processing():
    mock_client = MagicMock()
    # chain 설정: .table().select().eq().eq().eq().execute() → .data = [{"id": "x"}]
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{"id": "existing"}]
    # DELETE가 호출되지 않음을 assert
    run_ondemand_brief("user-1", "2026-07-25")
    mock_client.table.return_value.delete.assert_not_called()
```

`api/tests/test_health.py` 패턴 (TestClient):
```python
from fastapi.testclient import TestClient
from main import app
client = TestClient(app)

def test_trigger_requires_auth():
    response = client.post("/api/v1/daily-briefs/trigger")
    assert response.status_code == 403  # HTTPBearer 인증 없으면 403 반환
```
참고: `HTTPBearer`는 Authorization 헤더 없으면 403 반환 (auth.py:10)

### 기존 라우터 등록 패턴 준수

`api/main.py` 현재 패턴:
```python
from routers.devices import router as devices_router
from routers.health import router as health_router
from routers.onboarding import router as onboarding_router
from routers.users import router as users_router

app.include_router(health_router, prefix="/api/v1")
app.include_router(devices_router, prefix="/api/v1")
app.include_router(onboarding_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
```
→ `daily_briefs_router`를 동일 패턴으로 추가

### 절대 금지사항

| 금지 | 이유 |
|------|------|
| Collector/Normalizer/Reviewer 재실행 | AD-15: On-demand는 Recommender 이후만 |
| 전체 사용자 대상 Brief 재생성 | On-demand는 해당 사용자만 |
| `processing` 중인 Brief DELETE | 데이터 무결성 파괴 |
| `daily_briefs` 직접 쓰기를 클라이언트에서 | AD-3: FastAPI만 허용 |
| 프론트엔드 코드 수정 | Story 2.4에서 이미 완성됨 |
| LLMProvider 호출 | Recommender만 실행 (Review 재생성 없음) |

### 신규 / 수정 파일 목록

```
# 신규 파일 (Backend)
api/routers/daily_briefs.py            (NEW — POST /daily-briefs/trigger)
api/tests/test_daily_briefs_trigger.py (NEW — 단위/통합 테스트)

# 수정 파일 (Backend)
api/pipeline/orchestrator.py           (UPDATE — run_ondemand_brief 함수 추가)
api/main.py                            (UPDATE — daily_briefs_router 등록)
api/routers/users.py                   (UPDATE — update_profile에 BackgroundTask 추가)

# 변경 없음 (프론트엔드 — Story 2.4 완성)
web/src/components/home/daily-brief-content.tsx  (NO CHANGE)
mobile/lib/features/home/screens/home_screen.dart (NO CHANGE)
mobile/lib/features/home/providers/daily_brief_provider.dart (NO CHANGE)
```

### References

- 에픽: `_bmad-output/planning-artifacts/epics.md` — Story 2.5 (line 498–518)
- 아키텍처: `ARCHITECTURE-SPINE.md` — AD-5(비동기), AD-15(On-demand 실행 모델), AD-3(데이터 접근), AD-12(관찰가능성)
- 이전 스토리: `2-4-home-screen-daily-brief-display.md` — Realtime 구독(line 80-144), handleRetry(line 161-177), Flutter _handleRetry(home_screen.dart:26-40)
- Recommender: `api/pipeline/recommender.py` — `create_daily_brief_for_user()` (line 80-223)
- Orchestrator: `api/pipeline/orchestrator.py` — `run_daily_pipeline()` 패턴 (line 17-89)
- DB 스키마: `_bmad-output/implementation-artifacts/db/001_initial_schema.sql` — daily_briefs UNIQUE(user_id, brief_date), CASCADE DELETE
- 기존 라우터 패턴: `api/routers/onboarding.py`, `api/routers/users.py`
- 인증 미들웨어: `api/middleware/auth.py` — HTTPBearer 인증 없으면 403

## Review Findings

- [x] [Review][Decision] 비원자적 Delete-Then-Create: 경쟁 조건 및 데이터 손실 위험 — Option 2 적용: DELETE 이후 실패 시 `brief_lost` 이벤트 로깅으로 추적 가능하게 함 (`_deleted_existing` 플래그 도입). [orchestrator.py:100-137]

- [x] [Review][Patch] `date.today()` 서버 타임존 미지정 — `datetime.now(timezone.utc).date().isoformat()`으로 교체 완료 [routers/daily_briefs.py:18, routers/users.py:60]
- [x] [Review][Patch] `create_daily_brief_for_user` 함수 내부 지연 임포트 제거 — 모듈 최상단 임포트로 이동, 테스트 patch 경로 `pipeline.orchestrator.create_daily_brief_for_user`로 업데이트 [orchestrator.py]
- [x] [Review][Patch] `test_trigger_returns_202` 에서 background task 인자 검증 누락 — `mock_run.assert_called_once_with(user_id, brief_date)` 어서션 추가 완료 [tests/test_daily_briefs_trigger.py]
- [x] [Review][Patch] AC-2 HTTP 통합 테스트 누락 — `test_update_profile_triggers_ondemand_brief` 추가 완료, 79개 테스트 전체 통과 [tests/test_daily_briefs_trigger.py]

- [x] [Review][Defer] POST /trigger 엔드포인트 속도 제한 없음 [routers/daily_briefs.py] — deferred, 인프라 레벨(API Gateway) 관심사
- [x] [Review][Defer] Background task 실패 시 클라이언트에 무음 실패 [orchestrator.py:147-156] — deferred, AD-5 설계 방침 (Realtime으로 완료 감지)
- [x] [Review][Defer] `pipeline_log`이 except 블록에서 자체 예외 발생 가능 [orchestrator.py:147-156] — deferred, 로깅 인프라 장애는 극히 드뭄
- [x] [Review][Defer] `_make_mock_client()` 헬퍼가 항상 side_effect로 덮어씌워져 실질적 데드코드 [tests/test_daily_briefs_trigger.py:56-64] — deferred, 테스트 품질, 기능 정확도에 영향 없음

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Dev Notes의 `test_trigger_requires_auth` 주석이 403이라 명시했으나 실제 `HTTPBearer`는 Authorization 헤더 없을 때 401 반환함. 테스트를 401로 수정.
- `run_ondemand_brief`에서 `create_daily_brief_for_user`를 함수 내부 로컬 임포트로 사용하므로 테스트에서 `pipeline.recommender.create_daily_brief_for_user` 경로로 patch해야 함.

### Completion Notes List

- Task 1: `run_ondemand_brief(user_id, brief_date)` 함수를 `orchestrator.py`에 추가. processing 중복 방지 → non-processing DELETE → processed Signal 조회 → `create_daily_brief_for_user` 호출 순서로 구현. 예외는 pipeline_log에 기록 후 re-raise 않음.
- Task 2: `api/routers/daily_briefs.py` 신규 생성. `POST /daily-briefs/trigger` → 202 + BackgroundTask 등록.
- Task 3: `api/main.py`에 `daily_briefs_router` 등록 (기존 라우터 패턴 준수).
- Task 4: `api/routers/users.py`의 `update_profile`에 `BackgroundTasks` 파라미터 추가, DB 업데이트 성공 후 `run_ondemand_brief` BackgroundTask 등록.
- Task 5: 6개 테스트 작성, 전체 78개 테스트 모두 통과 (회귀 없음).

### File List

- api/pipeline/orchestrator.py (수정 — run_ondemand_brief 함수 추가)
- api/routers/daily_briefs.py (신규 — POST /daily-briefs/trigger)
- api/main.py (수정 — daily_briefs_router 등록)
- api/routers/users.py (수정 — update_profile에 BackgroundTasks + on-demand 트리거 추가)
- api/tests/test_daily_briefs_trigger.py (신규 — 6개 단위/통합 테스트)

## Change Log

- Story 2.5 구현 완료 (2026-07-25): POST /api/v1/daily-briefs/trigger 엔드포인트 추가, 프로필 업데이트 후 자동 on-demand 트리거, 전체 테스트 78개 통과

## Status

done
