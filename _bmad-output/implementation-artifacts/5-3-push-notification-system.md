---
baseline_commit: NO_VCS
---

# Story 5.3: Push Notification System

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

사용자로서,
매일 09:00 Daily Brief 알림, 저녁 20:00 Queue Today 리마인더, Learn Now 3일 후 Outcome 입력 요청을 받을 수 있기를 원한다,
그래서 앱을 열지 않아도 학습 루프를 놓치지 않는다.

**범위 참고 (반드시 먼저 읽을 것)**: 이 스토리는 **이미 존재하는 FCM 인프라 위에 나머지 2종 트리거 + 클라이언트 수신 처리를 완성**하는 것이다. Trigger #1(Daily Brief 09:00)의 백엔드는 **이미 Story 2.3에서 완전히 구현되어 동작 중**이다(`api/pipeline/fcm.py`, `api/pipeline/orchestrator.py:run_push_job`, `api/main.py` 스케줄러 09:00 job). Flutter의 **FCM 토큰 등록·갱신도 이미 구현되어 있다**(`fcm_provider.dart`, `main.dart`, 로그인/가입 시 등록). **처음부터 다시 만들지 말 것.** 아래 "이미 구현된 것 vs 이 스토리에서 만들 것" 표를 기준으로 델타만 구현한다.

**플랫폼 범위**: **Flutter + FastAPI 전용.** epics.md AC의 모든 클라이언트 동작은 Flutter API(`FirebaseMessaging.instance.getInitialMessage()`, `onMessage`, `onMessageOpenedApp`)로 명시되어 있다. **Web(Next.js PWA) Push는 이 스토리 범위 밖**이다 — `web/`에는 현재 firebase/FCM 코드가 전무하며(전수 grep 0건), AD-2/AD-17이 "Next.js PWA FCM Web SDK"를 언급하나 AC는 순수 Flutter다. Web PWA Push는 별도 스토리로 defer(아래 "범위 경계" 참조).

## 이미 구현된 것 vs 이 스토리에서 만들 것 (⚠️ 재구현 금지)

| 항목 | 상태 | 위치 |
|------|------|------|
| `user_devices` 테이블 + RLS + `updated_at` 트리거 | ✅ 존재 | `supabase/migrations/20260723000000_initial_schema.sql:35-43, 279, 298-303, 396-397` |
| `POST /api/v1/devices/register` (UPSERT, 크로스유저 토큰 이전) | ✅ 존재 | `api/routers/devices.py` |
| Firebase Admin 초기화(`init_firebase`, 스레드 안전) | ✅ 존재 | `api/pipeline/fcm.py:20-44` |
| **Trigger #1** Daily Brief push (`send_daily_brief_push`, `run_daily_brief_push_job`, 페이지네이션) | ✅ 존재 | `api/pipeline/fcm.py:47-174` |
| Trigger #1 스케줄러 wiring (`run_push_job` @09:00 KST) | ✅ 존재 | `api/pipeline/orchestrator.py:169-200`, `api/main.py:68-76` |
| `firebase_service_account_json` 설정 | ✅ 존재 | `api/core/config.py:15, 43-48` |
| firebase-admin==6.5.0, apscheduler==3.10.4 | ✅ 존재 | `api/requirements.txt:12-13` |
| Flutter FCM 토큰 등록/갱신(`registerFcmTokenWithToken`, `registerFcmToken`, `onTokenRefresh`) | ✅ 존재 | `mobile/lib/features/auth/providers/fcm_provider.dart`, `mobile/lib/main.dart:39-42` |
| Flutter 로그인/가입 시 토큰 등록 호출 | ✅ 존재 | `signin_screen.dart:120`, `signup_screen.dart:153` |
| firebase_core/firebase_messaging 패키지 + `Firebase.initializeApp` | ✅ 존재 | `mobile/pubspec.yaml:17-18`, `mobile/lib/main.dart:21` |
| **Trigger #2** Queue Today 리마인더 (백엔드 job + 20:00 스케줄러) | ❌ **신규** | `api/pipeline/fcm.py`(추가), `orchestrator.py`(추가), `main.py`(스케줄러) |
| **Trigger #3** Outcome 입력 요청 (Learn Now +3일, 1회, 백엔드 job + 스케줄러) | ❌ **신규** | 동상 + **신규 마이그레이션** |
| Trigger #3 중복 방지용 `decisions.outcome_reminder_sent_at` 컬럼 | ❌ **신규 마이그레이션** | `supabase/migrations/`, `_bmad-output/implementation-artifacts/db/` |
| push 메시지에 `data` 페이로드(type, signal_id) 추가 → 홈 딥링크·하이라이트 | ❌ **신규** | `api/pipeline/fcm.py` 3종 메시지 전부 |
| Flutter iOS 알림 권한 요청(`requestPermission`) | ❌ **신규** | `mobile/lib/main.dart` 또는 fcm_provider |
| Flutter foreground 수신 처리(`onMessage`, OS 알림 미표시 + 홈 하이라이트) | ❌ **신규** | 루트 위젯 + 하이라이트 provider |
| Flutter background tap(`onMessageOpenedApp`) → `/home` 라우팅 | ❌ **신규** | 루트 위젯 |
| Flutter terminated tap(`getInitialMessage()`) → `/home` 라우팅 | ❌ **신규** | 루트 위젯 |
| 홈 화면 top SignalCard 강조(하이라이트) 상태 | ❌ **신규** | `home_screen.dart` + provider |

## Acceptance Criteria

**AC-1: Daily Brief 준비 알림 (Trigger #1) — data 페이로드 + 홈 하이라이트 완성**
- **Given** Daily Brief 생성이 완료되고(`daily_briefs.status='completed'`) 09:00 KST push job이 실행되면
- **Then** 사용자의 각 `user_devices.fcm_token`으로 FCM Push가 전송된다: title `"오늘의 AI CTO 브리핑이 준비됐습니다"`, body는 top Signal(position=1) 제목 [Source: epics.md:824-827, 기존 `fcm.py:47-61` — 이미 동작]
- **And** 메시지에 `data: {"type": "daily_brief", "signal_id": <top signal id>}` 페이로드가 포함된다(**신규** — 기존 `send_daily_brief_push`는 `notification`만 전송, 딥링크·하이라이트 대상 식별용 `data` 추가 필요)
- **And** Push를 탭하면 앱이 **홈 화면(`/home`)으로** 열린다 — Research Review 직접 딥링크 금지(AC 명시)
- **And** 홈 화면에서 `signal_id`에 해당하는 SignalCard가 상단에 강조(하이라이트) 표시된다

**AC-2: Queue Today 리마인더 (Trigger #2) — 신규 백엔드 job + 20:00 스케줄러**
- **Given** 사용자가 오늘 `queue_timing='today'`로 설정한 Queue 결정(`decisions.choice='queue'`)을 남긴 채 20:00 KST가 되면
- **Then** 해당 사용자의 각 기기로 FCM Push가 전송된다: title `"오늘 학습하기로 한 Signal이 남아있습니다"`, body는 해당 Signal 제목 [Source: epics.md:829-830, UX-DR16 epics.md:116]
- **And** 대상 Queue Today 항목이 없는 사용자에게는 Push가 전송되지 않는다(AC 명시)
- **And** 메시지에 `data: {"type": "queue_reminder", "signal_id": <해당 signal id>}` 페이로드가 포함된다
- **And** 대상 판정: `choice='queue'` AND `queue_timing='today'` AND `updated_at`의 KST 날짜 == 오늘(설계 결정 2 — 오늘 "today"로 설정된 항목만; 자정 넘겨 이월된 항목은 5.1 "미완료(overdue)"로 처리되며 재알림하지 않음)

**AC-3: Outcome 입력 요청 (Trigger #3) — 신규 백엔드 job + 3일 경과 + 1회 제한**
- **Given** `choice='learn_now'` 결정 후 3일(KST)이 지나도 해당 Decision에 Outcome이 기록되지 않았고, 아직 리마인더를 보낸 적이 없으면(`outcome_reminder_sent_at IS NULL`)
- **Then** 사용자의 각 기기로 FCM Push가 전송된다: title `"학습 결과를 기록해 주세요"`, body는 해당 Signal 제목 [Source: epics.md:833-834, UX-DR16]
- **And** 전송 후 해당 Decision의 `outcome_reminder_sent_at`을 현재 시각으로 기록하여 **이후 추가 Push를 중단한다(1회 follow-up 후 중단)** [Source: epics.md:835, UX-DR16 "stale notification policy(3일 후 1회 follow-up, 이후 없음)"]
- **And** 메시지에 `data: {"type": "outcome_reminder", "signal_id": <해당 signal id>}` 페이로드가 포함된다
- **And** 대상 판정: `choice='learn_now'` AND `created_at <= now - 3일(KST)` AND 연결된 `outcomes` row 없음 AND `outcome_reminder_sent_at IS NULL`

**AC-4: Foreground 수신 — OS 알림 미표시 + 홈 하이라이트**
- **Given** 앱이 foreground 상태에서 Push가 수신되면(`FirebaseMessaging.onMessage`)
- **Then** OS 시스템 알림 배너가 표시되지 않는다(Flutter foreground 기본 동작; iOS는 `setForegroundNotificationPresentationOptions`로 배너 억제, `flutter_local_notifications` 도입 금지 — 스코프 확대)
- **And** 사용자가 홈 탭에 있을 경우 `data.signal_id`에 해당하는 SignalCard에만 brief highlight가 표시된다(홈에 없으면 조용히 무시 — 강제 내비게이션 금지) [Source: epics.md:837-839]

**AC-5: Terminated 상태 탭 → 홈 라우팅**
- **Given** 앱이 terminated(완전 종료) 상태에서 Push를 탭하면
- **Then** `FirebaseMessaging.instance.getInitialMessage()`로 payload를 감지하고 `/home`으로 라우팅된다 [Source: epics.md:841-842]
- **And** background(실행 중이나 미포커스) 상태 탭은 `FirebaseMessaging.onMessageOpenedApp`으로 감지되어 동일하게 `/home`으로 라우팅된다(AC-5의 background 대응 — epics.md는 terminated만 명시하나 완전한 동작을 위해 background tap도 처리; deep link는 항상 `/home` 랜딩 — UX-DR16)

## Tasks / Subtasks

### [Backend] Trigger #1 data 페이로드 보강

- [x] Task 1: `api/pipeline/fcm.py` — `send_daily_brief_push`에 `data` 페이로드 추가 (AC: 1)
  - [x] 1.1 `send_daily_brief_push(user_id, fcm_token, top_signal_title, brief_date, signal_id: str)` 시그니처에 `signal_id` 추가(기존 호출부 `run_daily_brief_push_job:159-161`도 `top[0]["signal_id"]` 전달하도록 수정 — 이 값은 이미 `_fetch`에서 조회 중이라 추가 쿼리 불필요)
  - [x] 1.2 `messaging.Message(...)`에 `data={"type": "daily_brief", "signal_id": signal_id}` 추가. FCM `data` 값은 **모두 문자열이어야 함** — `signal_id`는 이미 문자열(UUID)
  - [x] 1.3 기존 `notification` 블록·폴백 타이틀(`_PUSH_FALLBACK_TITLE`)·로깅·반환 계약은 그대로 유지(회귀 금지). 기존 테스트 `test_recommender_pipeline.py:278-294`가 통과하도록 시그니처 변경에 맞춰 테스트도 갱신

### [Backend] Trigger #2 Queue Today 리마인더

- [x] Task 2: `api/pipeline/fcm.py` — Queue 리마인더 push 함수 신규 (AC: 2)
  - [x] 2.1 `send_queue_reminder_push(user_id, fcm_token, signal_title, signal_id)` — `send_daily_brief_push`와 동일 구조: title `"오늘 학습하기로 한 Signal이 남아있습니다"`, body `signal_title`(빈 값 폴백), `data={"type":"queue_reminder","signal_id":...}`. 빈/None `fcm_token` 사전 가드 추가(deferred-work.md:180 권고 반영)
  - [x] 2.2 `run_queue_reminder_job(client, run_date: str) -> int` — KST 오늘 날짜 기준 대상 결정 조회 후 사용자별 기기에 전송, 전송 성공 수 반환
    - 쿼리: `decisions` where `choice='queue'`, `queue_timing='today'`. Supabase `updated_at`을 KST로 변환해 오늘 날짜인 것만 필터(서버는 UTC 저장 — Python에서 `updated_at`을 파싱해 `+9h` 후 date 비교; 타임존 라이브러리 불필요, Asia/Seoul 고정 UTC+9 — 5.1과 동일 판단)
    - 각 decision → `reviews.signal_id` → `signals.title` 조회(중첩 embed 또는 순차 조회). decision의 소유자 `user_id`는 `decisions → reviews → projects.user_id` 체인으로 획득(RLS 아님, service_role 조회이므로 명시적 join 필요) → 해당 user의 `user_devices.fcm_token` 목록 조회
    - **페이지네이션**: `_fetch_all_completed_briefs`(fcm.py:84-103)와 동일한 `_PAGE_SIZE=1000` range 루프 패턴 적용
    - 로깅: `pipeline_log(stage="fcm_queue_reminder", ...)` — `run_daily_brief_push_job`의 로그 이벤트 명명 규칙 답습(`push_job_started`/`push_sent`/`no_targets` 등)
  - [x] 2.3 한 사용자가 today 항목을 여러 개 남긴 경우 처리 방침: **사용자당 1건의 push**(가장 최근 `updated_at` 항목의 Signal 제목 사용) — 알림 스팸 방지. 설계 결정 3에 문서화

- [x] Task 3: `api/pipeline/orchestrator.py` — Queue 리마인더 job 래퍼 신규 (AC: 2)
  - [x] 3.1 `run_queue_reminder_job_entry(run_date: str | None = None) -> dict` — `run_push_job`(169-200) 패턴 복제: `init_firebase` 가드(firebase 미초기화 시 skip + warning 로그) → `fcm.run_queue_reminder_job` 호출 → `{"run_date","sent","error"}` 반환, 예외 시 `pipeline_log` 기록
  - [x] 3.2 `run_date` 기본값 `date.today().isoformat()`(스케줄러가 Asia/Seoul TZ이므로 KST 기준 오늘)

- [x] Task 4: `api/main.py` — 20:00 KST 스케줄러 job 등록 (AC: 2)
  - [x] 4.1 lifespan 내 기존 스케줄러에 job 추가: `scheduler.add_job(run_queue_reminder_job_entry, CronTrigger(hour=20, minute=0, timezone="Asia/Seoul"), id="queue_reminder", replace_existing=True, misfire_grace_time=300)` (기존 `daily_pipeline`/`daily_push`와 동일 옵션)
  - [x] 4.2 `logger.info("APScheduler started", extra={"jobs":[...]})` 목록에 `queue_reminder@20:00KST` 추가
  - [x] 4.3 import 추가: `from pipeline.orchestrator import ..., run_queue_reminder_job_entry`

### [Backend] Trigger #3 Outcome 입력 요청 (+ 마이그레이션)

- [x] Task 5: 신규 마이그레이션 — `decisions.outcome_reminder_sent_at` 컬럼 (AC: 3) — **⚠️ 두 위치에 동일 DDL 작성**(저장소가 이중 마이그레이션 디렉터리 운용: `supabase/migrations/`는 타임스탬프, `_bmad-output/implementation-artifacts/db/`는 순번)
  - [x] 5.1 `supabase/migrations/20260728000000_decisions_outcome_reminder_sent_at.sql` 신규:
    ```sql
    -- Story 5.3 Trigger #3: Outcome 입력 리마인더 1회 발송 추적 컬럼.
    -- Learn Now 후 3일 경과 + Outcome 미기록 + 미발송(NULL) 조건으로 1회만 push 후 기록.
    ALTER TABLE public.decisions
        ADD COLUMN IF NOT EXISTS outcome_reminder_sent_at TIMESTAMPTZ;
    ```
  - [x] 5.2 `_bmad-output/implementation-artifacts/db/003_decisions_outcome_reminder_sent_at.sql` 동일 내용 신규(db 폴더 최신은 `002_*`)
  - [x] 5.3 **Supabase MCP `apply_migration`으로 라이브 DB에 적용**(dev-story 검증 단계에서 실제 컬럼 존재 확인 — 5.2 Dev Notes의 live DB 검증 관행 답습). 컬럼은 nullable, 기본 NULL이므로 기존 row에 안전

- [x] Task 6: `api/pipeline/fcm.py` — Outcome 리마인더 push 함수 신규 (AC: 3)
  - [x] 6.1 `send_outcome_reminder_push(user_id, fcm_token, signal_title, signal_id)` — Task 2.1과 동일 구조: title `"학습 결과를 기록해 주세요"`, `data={"type":"outcome_reminder","signal_id":...}`, 빈 토큰 가드
  - [x] 6.2 `run_outcome_reminder_job(client, run_date: str) -> int`:
    - 대상 쿼리: `decisions` where `choice='learn_now'` AND `outcome_reminder_sent_at IS NULL` AND `created_at <= (now_kst - 3 days)`. `created_at` 비교는 UTC 기준 3일 전 timestamp로 서버측 필터(`.lte("created_at", cutoff_iso)`) — KST/UTC 오프셋은 3일(72h) 단위라 날짜 경계 민감도 낮으나, cutoff는 `datetime.now(timezone.utc) - timedelta(days=3)`로 계산
    - 각 decision에 대해 `outcomes` 존재 여부 확인(`.eq("decision_id", d.id).limit(1)`) — 있으면 skip
    - Outcome 없는 대상만: `reviews.signal_id → signals.title` + `user_id`(projects 체인) + `user_devices` 조회 후 전송
    - **전송 성공/실패와 무관하게** 처리한 decision의 `outcome_reminder_sent_at`을 UPDATE(재시도 시 중복 발송 방지 — "1회"는 발송 시도 1회로 해석; 설계 결정 4에 근거 명시). 단, 기기가 없어(토큰 0건) 아무것도 못 보낸 경우의 처리는 설계 결정 4 참조
    - 페이지네이션·로깅은 Task 2.2와 동일 패턴(`stage="fcm_outcome_reminder"`)

- [x] Task 7: `api/pipeline/orchestrator.py` + `api/main.py` — Outcome 리마인더 스케줄러 (AC: 3)
  - [x] 7.1 `run_outcome_reminder_job_entry(run_date=None) -> dict` — Task 3과 동일 패턴(init_firebase 가드 포함)
  - [x] 7.2 `main.py`에 daily 스케줄러 job 추가: `CronTrigger(hour=10, minute=0, timezone="Asia/Seoul")`, `id="outcome_reminder"` — **시각은 설계 결정 5**(epics/architecture가 Trigger #3에 고정 시각 미지정; Trigger #1=09:00·#2=20:00과 겹치지 않는 10:00 KST 기본값, 매일 1회 3일 경과분 스캔). logger jobs 목록에 추가

### [Backend] 테스트

- [x] Task 8: `api/tests/test_push_reminders.py` 신규 (AC: 2, 3) — `test_recommender_pipeline.py`의 `pipeline.fcm.messaging.send` patch 패턴 답습
  - [x] 8.1 `send_queue_reminder_push` / `send_outcome_reminder_push`: 성공(`messaging.send` mock)·예외 False·빈 토큰 가드 검증
  - [x] 8.2 `run_queue_reminder_job`: (a) today 대상 있는 사용자 push 발송, (b) 대상 없으면 0건, (c) 이월(updated_at 어제) 항목 제외, (d) 사용자당 1건 검증 — Supabase 클라이언트 mock
  - [x] 8.3 `run_outcome_reminder_job`: (a) 3일 경과·outcome 없음·미발송 → push + `outcome_reminder_sent_at` UPDATE 호출 검증, (b) outcome 존재 시 skip, (c) `outcome_reminder_sent_at` 이미 있으면 대상 제외(쿼리 필터), (d) 3일 미경과 제외
  - [x] 8.4 `send_daily_brief_push` 시그니처 변경(signal_id 추가)에 따른 기존 `test_recommender_pipeline.py` 갱신 — `data` 페이로드 포함 검증 추가

### [Flutter] 수신 처리 인프라

- [x] Task 9: `mobile/lib/features/notifications/providers/highlighted_signal_provider.dart` 신규 (AC: 1, 4) — 하이라이트 대상 signal_id 상태
  - [x] 9.1 `@riverpod class HighlightedSignal extends _$HighlightedSignal` — `String? build() => null;`, `void set(String signalId)`, `void clear()`. AD-14(Riverpod 2.x `@riverpod` 코드생성) 준수. **`keepAlive` 불필요**(홈 탭 전환 시 유지되도록 — 단, 하이라이트는 일시적이므로 AutoDispose 기본 유지하되 홈 화면이 watch하는 동안 살아있음)
  - [x] 9.2 `daily_brief_provider.dart`의 `SeenSignalIds`(Notifier) 패턴을 구조 모델로 삼는다(동일 `@riverpod` class 스타일)

- [x] Task 10: `mobile/lib/features/notifications/fcm_message_handler.dart` 신규 (AC: 1, 4, 5) — 메시지 → 액션 매핑 순수 로직 분리(테스트 용이성)
  - [x] 10.1 `void handleMessageOpened(RemoteMessage message, GoRouter router)` — `message.data['signal_id']`가 있으면 `router.go('/home')`(항상 홈 랜딩, UX-DR16) 후 필요 시 하이라이트 set. **Research Review 직접 이동 금지**(AC-1)
  - [x] 10.2 `void handleForegroundMessage(RemoteMessage message, WidgetRef ref)` — `signal_id` 있으면 `ref.read(highlightedSignalProvider.notifier).set(signalId)`. 내비게이션 없음(AC-4 — 강제 이동 금지, 현재 화면 유지)
  - [x] 10.3 라우팅과 하이라이트 set의 순서/타이밍 주의: `go('/home')` 후 홈이 마운트되며 highlight를 watch하도록. set을 라우팅 직후 호출

- [x] Task 11: `mobile/lib/main.dart` — 권한 요청 + 리스너 배선 (AC: 4, 5)
  - [x] 11.1 `Firebase.initializeApp` 직후 `await FirebaseMessaging.instance.requestPermission()`(iOS 알림 권한 — 현재 미요청 시 iOS에서 토큰/알림 미수신). 반환 무시(거부해도 앱 정상 동작, best-effort)
  - [x] 11.2 iOS foreground 배너 억제: `await FirebaseMessaging.instance.setForegroundNotificationPresentationOptions(alert: false, badge: false, sound: false)` (AC-4 — OS 알림 미표시)
  - [x] 11.3 **terminated 초기 메시지 처리**: `getInitialMessage()`는 라우터가 준비된 후 처리해야 하므로, 결과를 저장해 두었다가 `MyApp` 마운트 후 소비하거나, `MyApp`을 `ConsumerStatefulWidget`으로 바꿔 `initState`에서 `WidgetsBinding.addPostFrameCallback`으로 `ref.read(appRouterProvider)` 획득 후 `handleMessageOpened` 호출(설계 결정 6 — 리스너 배선 위치)
  - [x] 11.4 기존 `onTokenRefresh` 리스너(main.dart:39-42)는 그대로 유지

- [x] Task 12: `MyApp`을 `ConsumerStatefulWidget`으로 전환하여 런타임 리스너 등록 (AC: 1, 4, 5) — `mobile/lib/main.dart`
  - [x] 12.1 `initState`에서(또는 첫 프레임 후) `FirebaseMessaging.onMessage.listen((m) => handleForegroundMessage(m, ref))` + `FirebaseMessaging.onMessageOpenedApp.listen((m) => handleMessageOpened(m, ref.read(appRouterProvider)))` 등록
  - [x] 12.2 `getInitialMessage()` 결과가 있으면 첫 프레임 후 `handleMessageOpened` 호출(Task 11.3)
  - [x] 12.3 리스너 `StreamSubscription`을 `dispose`에서 취소. **기존 `MaterialApp.router`/테마/`appRouterProvider` watch 동작은 완전히 보존**(회귀 금지 — `MyApp`은 현재 `ConsumerWidget`, 라우터를 watch 중)
  - [x] 12.4 background(터미네이트 아님) tap = `onMessageOpenedApp`으로 커버(AC-5 And절). **`FirebaseMessaging.onBackgroundMessage`(top-level 핸들러)는 등록하지 않는다** — foreground 아닌 상태의 알림 표시는 OS가 자동 처리하며, 이 스토리는 background *데이터* 처리가 없으므로 불필요(스코프 확대 방지)

### [Flutter] 홈 하이라이트

- [x] Task 13: `mobile/lib/features/home/screens/home_screen.dart` — SignalCard 강조 (AC: 1, 4)
  - [x] 13.1 `build`에서 `final highlightedId = ref.watch(highlightedSignalProvider);` 추가
  - [x] 13.2 `_buildSignalList`에 `highlightedId` 전달 → 매칭되는 `signalId`의 `SignalCard`에 강조 스타일 적용. **강조는 기존 `isSeen` 시각 언어와 구분되는 별도 표현**(예: 좌측 accent 보더 또는 배경 틴트) — DESIGN.md에 "highlight" 시각 스펙이 명시돼 있지 않다면(전수 검색 후) 설계 결정 7로 문서화하고 기존 토큰(`AppColors`) 재사용
  - [x] 13.3 상단 강조: `data.signal_id`가 daily_brief top(position=1)이라 이미 리스트 상단이지만, 하이라이트는 "해당 카드"를 강조하는 것이며 리스트 재정렬은 하지 않는다(AC-1 "상단에 강조" = top signal이 곧 하이라이트 대상)
  - [x] 13.4 하이라이트 소비/해제 정책: 사용자가 해당 카드를 탭(또는 홈 재진입/일정 시간)하면 `clear()`. 최소 구현은 카드 탭 시 `mark(seen)`과 함께 `clear()` 호출(과설계 금지 — 자동 페이드 타이머는 선택)

### [Flutter] 테스트

- [x] Task 14: `mobile/test/fcm_handler_test.dart` 신규 (AC: 1, 4, 5)
  - [x] 14.1 `handleMessageOpened`: `data.signal_id` 존재 시 라우터 `go('/home')` 호출 검증(Mock GoRouter), Research Review 경로로 가지 않음 확인
  - [x] 14.2 `handleForegroundMessage`: `highlightedSignalProvider`가 signal_id로 set되는지 검증(ProviderContainer)
  - [x] 14.3 `HighlightedSignal` notifier: set/clear 동작 유닛 테스트
  - [x] 14.4 회귀 확인: `flutter test`로 `home_screen_test`/`navigation_shell_test` 등 기존 스위트 무회귀(단, 저장소에 사전 존재하는 `profile_test.dart` 컴파일 오류는 이 스토리 무관 — 5.1/5.2 문서화됨)

## Dev Notes

### 핵심 아키텍처 제약

- **AD-2 / AD-17 (FCM 단일 Push)**: FCM이 유일한 Push 서비스. FastAPI가 단일 전송 지점(FCM REST via firebase-admin). 클라이언트는 로그인/앱 오픈 시 토큰을 `/api/v1/devices/register`에 등록(이미 구현). Push 트리거 3종 고정: Daily Brief 준비(09:00), Queue Today(20:00), Outcome 요청(Learn Now 후 3일). **APNs 직접/별도 Web Push 금지, 클라이언트 직접 발송 금지.** [Source: ARCHITECTURE-SPINE.md#AD-17, #AD-2]
- **AD-3 (쓰기 소유권)**: `decisions.outcome_reminder_sent_at` UPDATE는 **FastAPI service_role만** 수행(리마인더 job 내부). 클라이언트가 이 컬럼을 쓰지 않는다. `user_devices` 조회도 job은 service_role로 수행(RLS 우회). [Source: ARCHITECTURE-SPINE.md#AD-3]
- **AD-15 (배치 + 스케줄러)**: Trigger들은 APScheduler(Asia/Seoul TZ) cron job. 기존 `daily_pipeline@06:00`·`daily_push@09:00`와 동일 스케줄러 인스턴스(lifespan 내부 생성). Trigger #1 push는 이미 배치 파이프라인 완료 후 09:00에 발송되도록 wiring됨. [Source: ARCHITECTURE-SPINE.md#AD-15, main.py:57-76]
- **AD-12 (관찰 가능성)**: 모든 job 로그는 `pipeline_log`(JSON 구조화). 기존 `stage="fcm"` 규칙을 따라 신규 job은 `stage="fcm_queue_reminder"`/`stage="fcm_outcome_reminder"`. [Source: ARCHITECTURE-SPINE.md#AD-12, fcm.py 전반]
- **AD-14 (Flutter Riverpod)**: 하이라이트 상태는 `@riverpod` 코드생성 Notifier. FCM 리스너는 Riverpod async 모델 밖의 앱 레벨 스트림이므로 루트 `ConsumerStatefulWidget`에서 `ref`로 브릿지. `build_runner build --delete-conflicting-outputs`로 `.g.dart` 생성 필요. [Source: ARCHITECTURE-SPINE.md#AD-14]
- **AD-13 (API 계약)**: 신규 클라이언트 엔드포인트 없음(등록 엔드포인트 기존). 이 스토리의 백엔드 신규는 전부 **내부 스케줄러 job**이며 HTTP 표면이 없다.

### 설계 결정 1: 이 스토리는 "델타 완성" — Trigger #1 백엔드는 재구현 금지

Trigger #1(Daily Brief push)의 전체 백엔드 경로(`send_daily_brief_push` → `run_daily_brief_push_job` → `run_push_job` → 09:00 스케줄러)는 Story 2.3에서 이미 구현·테스트 완료되어 프로덕션 스케줄러에 등록돼 있다. 이 스토리에서 Trigger #1에 대해 하는 유일한 백엔드 변경은 **`data` 페이로드 추가**(Task 1)로 홈 딥링크·하이라이트가 동작하게 하는 것뿐이다. Flutter 토큰 등록/갱신도 이미 있다. **새 등록 엔드포인트·새 Firebase 초기화·새 Daily Brief job을 만들지 말 것.**

### 설계 결정 2: Queue Today "남아있음" 판정 = updated_at KST 오늘

`decisions`에는 "queue 완료" 상태나 `queue_timing_set_at` 전용 컬럼이 없다(5.1 deferred-work.md:14에 이 한계가 이미 기록됨). `UNIQUE(review_id)`로 한 review당 결정 1건이므로 queue 항목을 "학습 완료"로 전이시키는 코드 경로도 현재 없다. 따라서 "오늘 학습하기로 한 항목이 남아있음"은 **`choice='queue'` AND `queue_timing='today'` AND `updated_at`의 KST 날짜 == 실행일**로 해석한다(오늘 today로 설정/재설정된 항목). 자정을 넘겨 이월된 항목은 5.1의 "미완료(overdue)" 배지로 이미 시각화되며, 이 리마인더는 재발송하지 않는다(매일 스팸 방지 + self-dedup). `updated_at` 기반의 취약성(무관한 트리거 갱신)은 5.1에서 이미 알려진 스펙 한계로 defer됨 — 이 스토리는 동일 기준을 재사용한다. 전용 `queue_timing_set_at` 컬럼 도입은 범위 밖(5.1 deferred 항목).

### 설계 결정 3: 사용자당 Queue 리마인더 1건

한 사용자가 today 항목을 여럿 남겼어도 20:00에 push 1건만 발송(가장 최근 `updated_at` 항목 제목). 근거: 알림 스팸 방지 + AC 문구가 단수("[Signal 제목]이 남아있습니다")다. 여러 항목 요약("외 N건")은 MVP 스코프 밖.

### 설계 결정 4: Outcome 리마인더 "1회" = 발송 시도 1회 (sent_at으로 dedup)

`outcome_reminder_sent_at`을 **전송 시도 후 무조건 기록**한다(전송 실패·기기 없음 포함). 근거: (a) "1회 follow-up 후 중단"의 핵심은 사용자를 반복적으로 괴롭히지 않는 것이고, (b) 기기가 없거나 토큰 만료로 실패한 건을 매일 재시도하면 3일 경과 대상이 영구히 매일 스캔·재시도되어 로그 노이즈·부하가 된다. **예외**: 기기 토큰이 0건인 사용자는 애초에 push 대상이 아니므로 `sent_at`을 기록하지 않는 편이 "기기 등록 후 첫 스캔에서 1회 발송"을 살린다 — **기기 토큰 ≥1건일 때만 `sent_at` 기록**(토큰 있는데 전송 예외면 기록해서 중단, 토큰 없으면 미기록해 다음날 재시도). 이 미묘함을 코드 주석에 명시.

### 설계 결정 5: Trigger #3 스케줄 시각 = 10:00 KST (변경 가능)

epics.md/ARCHITECTURE-SPINE.md는 Trigger #3에 고정 발송 시각을 지정하지 않는다("Learn Now 후 3일"만 명시). 매일 1회 "3일 경과 미기록" 대상을 스캔하는 daily job이 필요하며, 09:00(Daily Brief)·20:00(Queue)과 겹치지 않는 **10:00 KST**를 기본값으로 한다. 운영 중 조정 가능(cron 상수만 변경).

### 설계 결정 6: FCM 리스너 배선 위치 = 루트 ConsumerStatefulWidget

`onMessage`/`onMessageOpenedApp`/`getInitialMessage`는 라우터 접근이 필요하다(→ `/home` 이동). 최상위 `MyApp`을 `ConsumerStatefulWidget`으로 전환해 `ref.read(appRouterProvider)`로 라우터를 얻고, `getInitialMessage`(terminated)는 첫 프레임 후 `addPostFrameCallback`으로 처리한다. top-level 함수를 요구하는 `onBackgroundMessage`는 **등록하지 않는다**(background/terminated에서 OS가 알림을 자동 표시하고, 데이터-only 백그라운드 처리가 이 스토리에 없음).

### 설계 결정 7: 홈 하이라이트 시각 스펙

DESIGN.md/EXPERIENCE.md에 SignalCard "highlight" 전용 시각 스펙이 없다면(구현 전 전수 검색), 기존 `isSeen` 상태와 시각적으로 구분되는 최소 표현(좌측 accent 보더 또는 옅은 배경 틴트)을 `AppColors` 토큰으로 구성하고 문서화한다. WCAG(UX-DR13): 색상만으로 정보 전달 금지 원칙상 하이라이트는 "정보"라기보다 "주의 유도"이며 카드 콘텐츠 자체는 그대로 접근 가능하므로 색상 강조로 충분(단, 대비 부족 색상 금지 — 5.2 findings의 text-tertiary 교훈).

### 기존 데이터 흐름 (반드시 보존)

- **`send_daily_brief_push` 시그니처 변경**(signal_id 추가)은 유일 호출부 `run_daily_brief_push_job:159-161`과 테스트 `test_recommender_pipeline.py:278-294`를 함께 수정해야 함. body 폴백(`_PUSH_FALLBACK_TITLE`)·로깅·반환 계약 보존.
- **`main.dart` FCM 토큰 등록/갱신 흐름**(로그인/가입 → `registerFcmTokenProvider`, `onTokenRefresh`)은 변경하지 않는다. 권한 요청·리스너 배선만 추가.
- **`MyApp`의 `appRouterProvider` watch + `MaterialApp.router`**: `ConsumerStatefulWidget` 전환 시 라우터 watch가 깨지지 않도록(리다이렉트·auth 스트림 동작 보존).
- **`home_screen.dart`의 `seenSignalIdsProvider`·낙관적 pending·brief 상태머신**: 하이라이트 watch/전달만 추가하고 기존 렌더 분기 보존.

### DB 스키마 참조 (기존, 신규 컬럼 1개만 추가)

```sql
-- user_devices (migration :35-43) — id, user_id(FK auth.users, CASCADE), fcm_token, platform CHECK(web/ios/android), UNIQUE(user_id,fcm_token)
-- decisions (:94-107) — choice CHECK(learn_now/queue/ignore), queue_timing CHECK(today/this_week/later), UNIQUE(review_id)
--   ➕ 신규: outcome_reminder_sent_at TIMESTAMPTZ NULL (Task 5)
-- outcomes (:110-124) — decision_id FK(CASCADE), status CHECK(...); decision_id에 UNIQUE 없음(5.2 설계결정 2 — 존재 여부만 확인하므로 무관)
-- reviews (:61-91) — signal_id nullable, project_id FK(projects)
-- projects (:50-57) — user_id FK; user 소유권 획득 체인: decisions→reviews.project_id→projects.user_id
-- signals (:158-) — title NOT NULL, RLS(live DB는 enabled + signals_select 정책; service_role은 우회)
```

user 소유권 조인 체인(리마인더 job이 service_role로 대상 사용자·기기 식별):
`decisions.review_id → reviews.project_id → projects.user_id → user_devices.user_id`

### 재사용 패턴 (그대로 따를 것)

- **`api/pipeline/fcm.py`의 `send_daily_brief_push`**: Queue/Outcome push 함수의 구조 모델(Message 조립·try/except·pipeline_log·bool 반환).
- **`api/pipeline/fcm.py`의 `_fetch_all_completed_briefs` + `run_daily_brief_push_job`**: 페이지네이션 range 루프(`_PAGE_SIZE=1000`)·사용자별 기기 순회·success_count 집계 패턴.
- **`api/pipeline/orchestrator.py`의 `run_push_job`(169-200)**: `init_firebase` 가드 + 예외 로깅 + dict 반환 래퍼 패턴(신규 두 entry 함수의 모델).
- **`api/main.py` lifespan 스케줄러 등록(60-76)**: `add_job(..., CronTrigger(..., timezone="Asia/Seoul"), misfire_grace_time=300, replace_existing=True)` 패턴.
- **`api/tests/test_recommender_pipeline.py:278-294`**: `patch("pipeline.fcm.messaging.send")` FCM 테스트 패턴.
- **`mobile/lib/features/home/providers/daily_brief_provider.dart`의 `SeenSignalIds`**: `@riverpod` class Notifier(하이라이트 provider의 구조 모델).
- **`mobile/lib/main.dart`의 `onTokenRefresh` 리스너**: 앱 레벨 FCM 스트림 리스너 등록 위치·에러 무시(best-effort) 패턴.
- **`supabase/migrations/20260727000000_*.sql` + `db/002_*.sql`**: 이중 마이그레이션 작성 컨벤션(주석에 Story·목적 명시).

### 기존 코드베이스 현황 (수정/신규 대상)

**Backend 수정:**
- `api/pipeline/fcm.py` — `send_daily_brief_push`에 signal_id/data 추가 + Queue/Outcome push 함수·job 신규
- `api/pipeline/orchestrator.py` — Queue/Outcome entry 래퍼 2개 신규(`run_push_job` 모델)
- `api/main.py` — 스케줄러 job 2개 추가(20:00, 10:00) + import + logger 목록

**Backend 신규:**
- `supabase/migrations/20260728000000_decisions_outcome_reminder_sent_at.sql`
- `_bmad-output/implementation-artifacts/db/003_decisions_outcome_reminder_sent_at.sql`
- `api/tests/test_push_reminders.py`

**Flutter 수정:**
- `mobile/lib/main.dart` — requestPermission + foreground 옵션 + 리스너 배선 + `MyApp` → ConsumerStatefulWidget
- `mobile/lib/features/home/screens/home_screen.dart` — 하이라이트 watch/전달/렌더
- `mobile/lib/features/home/widgets/signal_card.dart` — (필요 시) `isHighlighted` prop 추가

**Flutter 신규:**
- `mobile/lib/features/notifications/providers/highlighted_signal_provider.dart` (+ `.g.dart`)
- `mobile/lib/features/notifications/fcm_message_handler.dart`
- `mobile/test/fcm_handler_test.dart`

**변경 없음(확인만):**
- `api/routers/devices.py`(등록 엔드포인트 완성), `mobile/lib/features/auth/providers/fcm_provider.dart`(토큰 등록 완성 — signin/signup에서 호출 중)

### 범위 경계

| 항목 | 이 스토리 (5.3) | 이후 |
|------|----------------|------|
| Trigger #1 data 페이로드 + 홈 딥링크/하이라이트 | ✅ | — |
| Trigger #2 Queue Today 리마인더(백엔드 job + 20:00) | ✅ | — |
| Trigger #3 Outcome 리마인더(백엔드 job + 3일 + 1회) + 마이그레이션 | ✅ | — |
| Flutter foreground/background/terminated 수신 처리 | ✅ | — |
| 홈 top SignalCard 하이라이트 | ✅ | — |
| **Web(Next.js PWA) FCM Push** | ❌ | 별도 스토리 — web에 firebase 코드 전무, AC가 Flutter 전용 |
| 만료 FCM 토큰(UNREGISTERED) `user_devices` 삭제 | ❌(선택) | deferred-work.md:177 — 여유 시 Task로 추가 가능, 필수 아님 |
| `queue_timing_set_at` 전용 컬럼(updated_at 대체) | ❌ | 5.1 deferred 항목 |
| Queue 리마인더 다중 항목 요약("외 N건") | ❌ | MVP 범위 밖(설계 결정 3) |
| /devices/register 속도 제한 | ❌ | 1.2 deferred, 인프라 레벨 |
| onBackgroundMessage(top-level 데이터 핸들러) | ❌ | 불필요(설계 결정 6) |
| Realtime 기반 인앱 알림 센터 | ❌ | 범위 밖 |

### 절대 금지사항

| 금지 | 이유 |
|------|------|
| Trigger #1 Daily Brief push 백엔드/등록 엔드포인트/Firebase 초기화 재구현 | 이미 Story 2.3에서 완성·스케줄러 등록됨(설계 결정 1) |
| Flutter FCM 토큰 등록/갱신 로직 재작성 | `fcm_provider.dart`+signin/signup에서 이미 동작 |
| Push 탭 시 Research Review로 직접 딥링크 | AC-1/UX-DR16 — deep link는 **항상 `/home` 랜딩** |
| foreground push에서 강제 화면 이동 | AC-4 — 현재 화면 유지, 홈에 있을 때만 카드 하이라이트 |
| `flutter_local_notifications` 도입해 foreground 알림 표시 | AC-4는 foreground OS 알림 **미표시** 요구 — 스코프 확대·모순 |
| `onBackgroundMessage` top-level 핸들러 등록 | background/terminated 알림은 OS 자동 표시, 데이터-only 처리 없음(설계 결정 6) |
| Web(Next.js)에 FCM 코드 추가 | 이 스토리 범위 밖 — AC 전부 Flutter |
| 클라이언트가 `outcome_reminder_sent_at` 쓰기 | AD-3 — service_role(job)만 쓰기 |
| FCM `data` 값에 비-문자열 전달 | FCM data는 전부 string이어야 함 |
| Outcome 리마인더를 3일 경과 대상에 매일 반복 발송 | AC-3 "1회 follow-up 후 중단" — sent_at으로 dedup(설계 결정 4) |
| 마이그레이션을 한 디렉터리에만 작성 | 저장소가 `supabase/migrations` + `db/` 이중 운용(Task 5) |
| KST 변환에 타임존 라이브러리 도입 | Asia/Seoul 고정 UTC+9, DST 없음 — 5.1/5.2와 동일 판단 |

### References

- 에픽: `_bmad-output/planning-artifacts/epics.md` — Story 5.3 AC 원문(line 816-842), Epic 5 개요(752-754), FR/UX 매핑(AD-17 요약 line 80, UX-DR16 line 116)
- 아키텍처: `ARCHITECTURE-SPINE.md` — AD-17(Push 전달), AD-2(FCM 단일 스택), AD-3(쓰기 소유권), AD-15(스케줄러 배치), AD-12(관찰성), AD-13(API 계약), AD-14(Flutter Riverpod)
- 기존 구현(재사용/보존): `api/pipeline/fcm.py`(Trigger #1 전체), `api/pipeline/orchestrator.py:169-200`(run_push_job), `api/main.py:57-76`(스케줄러), `api/routers/devices.py`(등록 엔드포인트), `api/core/config.py:15`(firebase 설정)
- Flutter 기존: `mobile/lib/main.dart`(Firebase init·onTokenRefresh), `mobile/lib/features/auth/providers/fcm_provider.dart`(토큰 등록), `signin_screen.dart:120`·`signup_screen.dart:153`(등록 호출), `mobile/lib/features/home/screens/home_screen.dart`(하이라이트 대상), `mobile/lib/features/home/providers/daily_brief_provider.dart`(SeenSignalIds 패턴), `mobile/lib/core/router/app_router.dart`(라우팅 대상 `/home`)
- DB 스키마: `supabase/migrations/20260723000000_initial_schema.sql` — `user_devices`(35-43), `decisions`(94-107), `outcomes`(110-124), RLS(279, 298-303); 마이그레이션 컨벤션: `20260727000000_learning_paths_unique_active.sql` + `db/002_signals_unique_constraint.sql`
- Deferred 참고: `_bmad-output/implementation-artifacts/deferred-work.md` — 만료 토큰 미삭제(177), 빈 fcm_token 가드(180), platform 'web' enum(113), updated_at 취약성(14)
- 이전 스토리: `5-2-history-memory-timeline.md`(live DB 검증 관행·RSC 경계 교훈·KST 판단), `5-1-queue-탭.md`(queue_timing/updated_at 판정·미완료 배지 로직)

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Opus 4.8) — BMad dev-story 워크플로우

### Debug Log References

- 백엔드 단위 테스트: `python3 -m pytest` → **148 passed** (신규 test_push_reminders.py 17건 + test_recommender_pipeline.py 시그니처/데이터 페이로드 갱신 포함, 회귀 0).
- Flutter 신규 테스트: `flutter test test/fcm_handler_test.dart` → **5 passed**.
- Flutter 회귀(프로필 의존 2파일 제외): home/queue/history/theme/auth/onboarding/widget → **81 passed**.
- Supabase MCP `apply_migration` 후 `information_schema.columns` 조회로 `decisions.outcome_reminder_sent_at`(TIMESTAMPTZ, nullable) 라이브 존재 확인.
- `dart analyze`(수정 파일) → 신규 코드 이슈 0 (main.dart의 `anonKey` deprecation은 사전 존재, 이 스토리 무관).

### Completion Notes List

**구현 요약 (델타만 — 설계 결정 1: Trigger #1 백엔드/토큰 등록 재구현 없음)**

- **AC-1 (Trigger #1 data)**: `send_daily_brief_push`에 `signal_id` 파라미터 + `data={"type":"daily_brief","signal_id":...}` 추가, 호출부(`run_daily_brief_push_job`)에서 top signal id 전달. 기존 notification/폴백/로깅/반환 계약 보존.
- **AC-2 (Trigger #2 Queue)**: `send_queue_reminder_push` + `run_queue_reminder_job`(fcm.py), `run_queue_reminder_job_entry`(orchestrator), 20:00 KST 스케줄러(main.py). 대상 = choice='queue' AND queue_timing='today' AND updated_at KST==run_date(설계 결정 2), 사용자당 1건(가장 최근 updated_at, 설계 결정 3), 이월 항목 제외.
- **AC-3 (Trigger #3 Outcome)**: 신규 마이그레이션 `outcome_reminder_sent_at`(2개 디렉터리 + 라이브 적용), `send_outcome_reminder_push` + `run_outcome_reminder_job`, `run_outcome_reminder_job_entry`, 10:00 KST 스케줄러(설계 결정 5). 3일 경과·outcome 없음·미발송 대상에 1회 발송 후 sent_at 기록; **토큰 0건이면 미기록해 다음날 재시도**(설계 결정 4).
- **AC-4 (Foreground)**: `setForegroundNotificationPresentationOptions(alert:false...)`로 OS 배너 억제, `handleForegroundMessage`가 하이라이트만 set(내비게이션 없음). `flutter_local_notifications`/`onBackgroundMessage` 미도입.
- **AC-5 (Terminated/Background tap)**: `MyApp`을 `ConsumerStatefulWidget`으로 전환, `onMessageOpenedApp` 리스너 + `getInitialMessage` 첫 프레임 처리, `handleMessageOpened`가 **항상 `/home`** 라우팅(Research Review 직접 딥링크 금지) 후 하이라이트 set. 기존 `appRouterProvider` watch·`onTokenRefresh`·`MaterialApp.router` 보존.
- **홈 하이라이트**: `HighlightedSignal`(@riverpod Notifier) 신규, `SignalCard.isHighlighted`(accent 보더+틴트, 설계 결정 7 — DESIGN.md에 전용 스펙 없어 queue의 '강조 보더' 선례 재사용), 카드 탭 시 clear.

**범위 밖(설계대로 제외)**: Web(Next.js) FCM, 만료 토큰 삭제, `queue_timing_set_at` 전용 컬럼, `onBackgroundMessage`.

**사전 존재 이슈(이 스토리 무관)**: `mobile/lib/features/profile/screens/profile_screen.dart`의 `AppSettings.openNotificationSettings` 미존재(app_settings 5.1.1 드리프트, Story 5.1/5.2 문서화) → `profile_test.dart`·`navigation_shell_test.dart` 컴파일 불가. 본 스토리는 해당 파일 미수정.

### File List

**Backend (수정)**
- `api/pipeline/fcm.py` — send_daily_brief_push data 페이로드; Queue/Outcome push 함수·job·소유권 조인 헬퍼·KST 헬퍼 신규
- `api/pipeline/orchestrator.py` — run_queue_reminder_job_entry / run_outcome_reminder_job_entry 신규 + import
- `api/main.py` — 10:00·20:00 KST 스케줄러 job 2개 + import + logger jobs 목록

**Backend (신규)**
- `supabase/migrations/20260728000000_decisions_outcome_reminder_sent_at.sql`
- `_bmad-output/implementation-artifacts/db/003_decisions_outcome_reminder_sent_at.sql`
- `api/tests/test_push_reminders.py`

**Backend (테스트 갱신)**
- `api/tests/test_recommender_pipeline.py` — send_daily_brief_push signal_id 시그니처 + data 페이로드 검증

**Flutter (신규)**
- `mobile/lib/features/notifications/providers/highlighted_signal_provider.dart` (+ `.g.dart`)
- `mobile/lib/features/notifications/fcm_message_handler.dart`
- `mobile/test/fcm_handler_test.dart`

**Flutter (수정)**
- `mobile/lib/main.dart` — 권한 요청 + foreground 옵션 + 리스너 배선 + MyApp → ConsumerStatefulWidget
- `mobile/lib/features/home/screens/home_screen.dart` — 하이라이트 watch/전달/clear
- `mobile/lib/features/home/widgets/signal_card.dart` — isHighlighted prop + accent 보더

## Change Log

| 날짜 | 변경 내용 |
|------|----------|
| 2026-07-28 | Story 5.3 생성 (create-story 워크플로우) — Epic 5 세 번째 스토리. 기존 FCM 인프라(Trigger #1·토큰 등록) 위에 Trigger #2/#3 + Flutter 수신 처리 델타 완성으로 범위 확정. |
| 2026-07-28 | Story 5.3 구현 완료 (dev-story) — Trigger #1 data 페이로드, Trigger #2 Queue 리마인더(20:00), Trigger #3 Outcome 리마인더(10:00)+마이그레이션, Flutter foreground/background/terminated 수신 처리 + 홈 하이라이트. 백엔드 148 + Flutter fcm 5/회귀 81 통과. Status → review. |
| 2026-07-28 | code-review (bmad-code-review, 3-layer 적대적 리뷰) — Acceptance Auditor AC 위반/금지사항 위반 0건. Patch 2, Defer 6, Dismiss 16. |

## Review Findings

_bmad-code-review · 2026-07-28 · Blind Hunter + Edge Case Hunter + Acceptance Auditor (3-layer). AC 위반·절대 금지사항 위반 0건. 지적 대부분은 스펙 설계 결정(2·4·6·7)이 명시적으로 수용한 사항 → dismiss._

### Patch (수정 권장, 명확)

- [x] [Review][Patch] Queue 리마인더 '가장 최근 updated_at' 선택이 ISO 문자열 사전식(lexicographic) 비교 → `_parse_utc()` 파싱 후 datetime 비교로 교체(fixed). [api/pipeline/fcm.py:339-341]
- [x] [Review][Patch] 설계 결정 4의 미묘한 분기(토큰 ≥1건인데 전송 예외 → `outcome_reminder_sent_at` 기록해 중단) 테스트 추가: `test_outcome_job_marks_sent_even_when_send_fails`(fixed). [api/tests/test_push_reminders.py]

### Defer (실재하나 지금 조치 대상 아님 — deferred-work.md 기록)

- [x] [Review][Defer] `updated_at` 자동 갱신 트리거가 Queue 'today' 판정을 약화(무관 갱신도 오늘로 재자격) — 설계 결정 2/5.1에서 이미 알려진 스펙 한계로 수용. [api/pipeline/fcm.py:319-322] — deferred, pre-existing
- [x] [Review][Defer] 소유권 조인 N+1 + 무제한 클라이언트측 스캔 → 대규모 시 느림/misfire 위험(확장성). MVP 규모 무해. [api/pipeline/fcm.py:301-343, 452-490] — deferred
- [x] [Review][Defer] 소비되지 않은/리스트에 없는 하이라이트 미해제(카드 탭 시에만 clear) — 설계 결정 7이 자동 해제를 선택사항으로 defer. [mobile/lib/features/home/screens/home_screen.dart:195-201] — deferred
- [x] [Review][Defer] Job `run_date`가 `date.today()`(시스템 TZ) 사용 — 비UTC/비KST 호스트에서 KST 필터와 어긋남. 기존 `run_push_job` 패턴 답습, 실 발송 시각(10:00/20:00 KST)이 UTC 날짜 경계 미교차라 UTC 배포 하 무해. [api/pipeline/orchestrator.py:213, 246] — deferred
- [x] [Review][Defer] Queue 리마인더 일일 멱등성 마커 부재 → 스케줄러 misfire/재기동 시 중복 발송 가능(outcome job의 sent_at 같은 가드 없음). [api/pipeline/fcm.py:294] — deferred
- [x] [Review][Defer] `outcome_reminder_sent_at` UPDATE가 성공 전송 후 예외 나면(catch됨) 미기록 → 다음날 재발송 가능('1회' 보장 깨짐, 희귀). [api/pipeline/fcm.py:485-490] — deferred
