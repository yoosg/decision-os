# 온디맨드 리뷰 전환 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매일 배치가 새 시그널 × 전체 유저로 리뷰를 사전생성하던 것을, 토글(기본 off) 뒤로 숨겨 유저가 시그널 상세를 열 때만 온디맨드로 생성하게 한다.

**Architecture:** `run_daily_pipeline`의 step 5(`review_all_for_signal` 루프)를 `settings.review_pregeneration_enabled`(기본 False)로 감싼다. off면 스킵 → 온디맨드(기존 폴백 경로: 프론트 trigger → `POST /reviews/trigger` → pending→completed)가 주 경로가 된다. 다른 배치 단계·프론트·추천은 불변.

**Tech Stack:** Python(FastAPI, pydantic BaseSettings, pytest). LLM/DB는 이 변경에서 직접 안 건드림.

## Global Constraints

- 토글 기본값 **False**(온디맨드). 긴급 롤백은 Railway 변수 `review_pregeneration_enabled=true`.
- 기존 안전 토글 패턴 준수: `core/config.py`의 `clustering_enabled`/`learnability_filter_enabled`/`link_verification_enabled`와 동일한 `bool` 필드 스타일.
- 배치의 나머지 단계(collect/cluster/curate/normalize/build_signals/recommender)와 프론트 온디맨드 경로는 **변경 금지**.
- reviews 테이블/기존 행 마이그레이션·정리 **없음**.
- 백엔드 테스트: `api/` 에서 `.venv/bin/python -m pytest`.
- 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

### Task 1: 배치 리뷰 사전생성을 토글(기본 off) 뒤로

**Files:**
- Modify: `api/core/config.py` (신규 토글 필드)
- Modify: `api/pipeline/orchestrator.py:78-84` (step 5를 토글로 감싸기)
- Test: `api/tests/test_recommender_pipeline.py` (off 케이스 신규 + 기존 순서 테스트 조정)

**Interfaces:**
- Consumes: 없음.
- Produces:
  - `settings.review_pregeneration_enabled: bool`(기본 `False`).
  - `run_daily_pipeline(brief_date)` 동작: 토글 False면 `review_all_for_signal` 미호출로 step 5 스킵(반환 dict 스키마 불변: `{"brief_date","signals","briefs","error"}`), True면 기존대로 시그널마다 호출.

- [ ] **Step 1: off 케이스 실패 테스트 작성**

`api/tests/test_recommender_pipeline.py` 끝에 추가:

```python
def test_run_daily_pipeline_skips_review_when_pregeneration_off():
    """review_pregeneration_enabled=False면 배치가 step5(review_all_for_signal)를 건너뛴다."""
    import pipeline.orchestrator
    call_order = []

    def mock_collect(self):
        call_order.append("collect")
        from pipeline.models import RawArticle
        return [RawArticle("LangGraph", "Title", "https://a.com", "official_blog")]

    def mock_normalize(articles, signal_date, client, brief_date):
        call_order.append("normalize")
        return ["sig-1"]

    def mock_build(signal_ids, client, llm, brief_date):
        call_order.append("build")
        return ["sig-1"]

    def mock_review(signal_id, client, llm, brief_date):
        call_order.append("review")
        return ["rev-1"]

    def mock_recommend(signal_ids, client, brief_date, llm=None):
        call_order.append("recommend")
        return 1

    with (
        patch("pipeline.orchestrator.settings.collector_mode", "stub"),
        patch("pipeline.orchestrator.settings.review_pregeneration_enabled", False),
        patch("pipeline.orchestrator.StubCollector.collect", mock_collect),
        patch("pipeline.orchestrator.normalize", mock_normalize),
        patch("pipeline.orchestrator.build_signals", mock_build),
        patch("pipeline.orchestrator.review_all_for_signal", mock_review),
        patch("pipeline.orchestrator.run_recommender", mock_recommend),
        patch("pipeline.orchestrator.get_supabase", return_value=MagicMock()),
        patch("pipeline.orchestrator.get_llm_provider", return_value=MagicMock()),
    ):
        result = pipeline.orchestrator.run_daily_pipeline("2026-07-24")

    assert "review" not in call_order
    assert call_order == ["collect", "normalize", "build", "recommend"]
    assert result["error"] is None
    assert result["briefs"] == 1
```

- [ ] **Step 2: 실패 확인**

Run: `cd api && .venv/bin/python -m pytest tests/test_recommender_pipeline.py::test_run_daily_pipeline_skips_review_when_pregeneration_off -v`
Expected: FAIL — `settings`에 `review_pregeneration_enabled` 속성이 없어 `patch`가 `AttributeError`를 낸다(토글 미구현 RED). (속성이 있었더라도 현재는 review가 항상 호출돼 `"review" not in call_order`가 실패.)

- [ ] **Step 3: config에 토글 추가**

`api/core/config.py`의 기존 토글들(`link_verification_enabled` 근처) 아래에 추가:

```python
    # review_pregeneration_enabled: 배치(06:00)의 리뷰 사전생성 on/off.
    # 기본 False = 온디맨드(유저가 시그널 상세를 열 때만 생성). 긴급 시 True로 사전생성 복귀.
    review_pregeneration_enabled: bool = False
```

- [ ] **Step 4: orchestrator step 5를 토글로 감싸기**

`api/pipeline/orchestrator.py`의 현재 step 5:

```python
        # 5. Reviewer (signal_id마다 모든 ai_research 프로젝트)
        total_reviews = 0
        for signal_id in processed_ids:
            review_ids = review_all_for_signal(signal_id, client, llm, brief_date=brief_date)
            total_reviews += len(review_ids)
        pipeline_log(stage="orchestrator", brief_date=brief_date, user_count=0,
                     event="review_done", review_count=total_reviews)
```

를 아래로 교체:

```python
        # 5. Reviewer — 기본 off(온디맨드). 토글 on일 때만 시그널×전체 유저 사전생성.
        total_reviews = 0
        if settings.review_pregeneration_enabled:
            for signal_id in processed_ids:
                review_ids = review_all_for_signal(signal_id, client, llm, brief_date=brief_date)
                total_reviews += len(review_ids)
        pipeline_log(stage="orchestrator", brief_date=brief_date, user_count=0,
                     event="review_done", review_count=total_reviews)
```

- [ ] **Step 5: off 테스트 통과 확인**

Run: `cd api && .venv/bin/python -m pytest tests/test_recommender_pipeline.py::test_run_daily_pipeline_skips_review_when_pregeneration_off -v`
Expected: PASS.

- [ ] **Step 6: 기존 순서 테스트를 on 케이스로 조정**

기본값이 off로 바뀌어 `test_run_daily_pipeline_calls_stages_in_order`(리뷰 호출 순서를 기대)가 깨진다. 그 테스트의 `with (` 블록 안, `patch("pipeline.orchestrator.settings.collector_mode", "stub"),` 바로 아래에 토글 on 패치를 추가한다:

```python
        patch("pipeline.orchestrator.settings.collector_mode", "stub"),
        patch("pipeline.orchestrator.settings.review_pregeneration_enabled", True),
```

(나머지 줄·assert `call_order == ["collect", "normalize", "build", "review", "recommend"]`는 그대로 유지 — 이 테스트가 "on → review 호출" 분기를 커버한다.)

- [ ] **Step 7: 파일 전체 + 전체 스위트 통과 확인**

Run: `cd api && .venv/bin/python -m pytest tests/test_recommender_pipeline.py -v`
Expected: off 신규 테스트 + 조정된 순서 테스트 포함 전부 PASS.

Run: `cd api && .venv/bin/python -m pytest -q`
Expected: 전체 PASS(회귀 없음).

- [ ] **Step 8: 커밋**

```bash
git add api/core/config.py api/pipeline/orchestrator.py api/tests/test_recommender_pipeline.py
git commit -m "feat(pipeline): 배치 리뷰 사전생성을 토글(기본 off) 뒤로 — 온디맨드 전환

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 배포 후 확인 (수동, 실행 아님)

- Railway 백엔드 로그에서 다음 06:00 배치의 `review_done` 이벤트 `review_count=0` 확인.
- 시그널 상세 최초 진입 시 온디맨드 생성(로딩 후 표시) 정상 동작.
- 롤백 필요 시 Railway 변수 `review_pregeneration_enabled=true` 설정 후 재배포.
