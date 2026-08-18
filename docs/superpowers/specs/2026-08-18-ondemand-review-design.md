# 온디맨드 리뷰 전환 (배치 리뷰 사전생성 제거)

- 날짜: 2026-08-18
- 브랜치: `feat/ondemand-review` (base: main)
- 관련: [[signal-quality-roadmap]] 비용 구조, `review/[signalId]/page.tsx` completed-우선 조회(선행 수정 33a3119)

## 문제

매일 06:00 KST 배치(`pipeline/orchestrator.py::run_daily_pipeline` step 5)가
`review_all_for_signal`로 **새 시그널마다 × 모든 ai_research 프로젝트(=전체 유저)**에
Research Review를 사전생성한다. 각 건이 GPT 완성 호출이라 비용이 **(새 시그널 수 × 유저 수)**로
곱하며 커진다. 접속·열람과 무관하게 매일 발생하고, **유저가 영영 안 볼 시그널의 리뷰까지** 만든다.
(증거: reviews 테이블 3,872행, 시그널 하나에 유저별 completed 13개.)

## 목표

배치의 리뷰 사전생성을 제거하고, **유저가 실제로 시그널 상세를 연 경우에만** 리뷰를
생성(온디맨드)한다. 비용을 "시그널×유저"에서 "실제 열람 수"로 낮춘다.

## 배경 — 이미 존재하는 온디맨드 경로

- 프론트 `components/home/review/review-page-content.tsx`: `initialReview`가 없거나
  `failed`면 `POST /api/v1/reviews/trigger` 호출 → pending INSERT → BackgroundTask 생성 →
  Supabase Realtime 구독으로 completed 수신 → 표시. 로딩 UI(`ReviewGeneratingState`) 존재.
- 백엔드 `routers/reviews.py::trigger_review`: pending/processing 리뷰 있으면 재사용(멱등).
- 서버 페이지 `review/[signalId]/page.tsx`: completed 우선 조회(선행 수정)로 재열람 시 즉시 표시.

즉 온디맨드는 오늘도 폴백으로 동작 중이며, 이 전환은 그것을 **주 경로로 승격**하는 것.

## 설계

### 1) 토글 추가 — `api/core/config.py`

기존 안전 롤아웃 토글(`clustering_enabled`, `learnability_filter_enabled`,
`link_verification_enabled`)과 동일 패턴으로:

```python
# review_pregeneration_enabled: 배치(06:00)의 리뷰 사전생성 on/off.
# 기본 False = 온디맨드(유저가 시그널 상세를 열 때만 생성). 긴급 시 True로 사전생성 복귀.
review_pregeneration_enabled: bool = False
```

### 2) 배치 step 5 조건 분기 — `api/pipeline/orchestrator.py`

`run_daily_pipeline`의 step 5(현재 `for signal_id in processed_ids: review_all_for_signal(...)`)를
토글로 감싼다:

```python
# 5. Reviewer — 기본 off(온디맨드). 토글 on일 때만 전체 유저 사전생성.
total_reviews = 0
if settings.review_pregeneration_enabled:
    for signal_id in processed_ids:
        review_ids = review_all_for_signal(signal_id, client, llm, brief_date=brief_date)
        total_reviews += len(review_ids)
pipeline_log(stage="orchestrator", brief_date=brief_date, user_count=0,
             event="review_done", review_count=total_reviews)
```

토글 off면 step 5 전체를 건너뛴다(`review_all_for_signal` 미호출). 나머지 단계
(collect / cluster / curate / normalize / build_signals / recommender)는 불변.

### 3) 동작 흐름 (전환 후)

- 06:00 배치: 새 시그널 수집 + 브리핑 생성. **리뷰 미생성.**
- 유저가 홈 브리핑 → 시그널 상세 진입 → 리뷰 없음 → 온디맨드 trigger →
  pending→processing→completed → 로딩 후 표시.
- 재진입/두 번째 열람: completed 있으면 즉시 표시.

### 4) 의존성 (안전 확인)

- 추천/브리핑(`pipeline/recommender.py`)은 reviews를 **참조하지 않음**(grep 확인). 홈/푸시 안 깨짐.
- `review_all_for_signal`의 프로덕션 호출부는 **orchestrator step 5 단 한 곳**(grep 확인).
- `coach.py`(학습경로)·`memory_manager.py`는 "유저가 결정한 시그널"의 리뷰만 접근 →
  그 시그널은 유저가 이미 열었으므로 온디맨드로 completed 존재. 문제 없음.
- 기존 reviews 행은 그대로 둔다(마이그레이션/정리 없음). 온디맨드는 completed 있으면 재생성 안 함.

### 5) 에러 / 롤백

- 롤백: 토글 `review_pregeneration_enabled=True`(Railway 변수)로 즉시 사전생성 복귀.
- 온디맨드 실패: 기존 `failed` 상태 + "다시 시도" UI 그대로. 신규 에러 로직 없음.

## 테스트

- **orchestrator 단위 테스트**(`api/tests/`):
  - 토글 **off → step 5 스킵**: `run_daily_pipeline` 실행 시 `review_all_for_signal`가
    호출되지 않고 결과 없이 나머지 파이프라인이 정상 완료.
  - 토글 **on → 호출**: 기존 동작(시그널마다 `review_all_for_signal` 호출) 유지.
  - 기존 `test_recommender_pipeline.py`가 `pipeline.orchestrator.review_all_for_signal`를
    patch/기대하므로, 토글 기본값 변경에 맞춰 해당 테스트에서 토글을 명시적으로 켜거나
    스킵 기대로 조정한다(어느 쪽이든 회귀 없이 통과해야 함).
- **온디맨드 경로**: 기존 `reviews trigger` 테스트가 커버(신규 코드 없음).

## 범위 밖 (YAGNI)

- 브리핑에 포함된 시그널만 미리 데우는 "brief-scoped 사전생성"(옵션 B).
- 백엔드 trigger의 completed-idempotency 추가(무-리뷰 동시열람 race는 기존에도 존재하는
  희귀 케이스 — 별건).
- 기존 사전생성 리뷰 행 정리/삭제.
- 프론트 로딩 UX 변경(현행 `ReviewGeneratingState` 유지).

## 요약 (변경 파일)

- `api/core/config.py` — `review_pregeneration_enabled: bool = False` 추가
- `api/pipeline/orchestrator.py` — step 5를 토글로 감싸기
- `api/tests/…` — 토글 off/on 분기 테스트, 기존 recommender 파이프라인 테스트 조정
