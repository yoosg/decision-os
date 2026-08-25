# 코드리뷰 잔여 정리 — 백엔드 버그 2개 (설계)

- 날짜: 2026-08-25
- 범위: PR #3(입문자 프로젝트 카드) 자동 코드리뷰에서 넘긴 **백엔드 버그 2개**만.
  - history chain 카드 대응(웹)·웹 리팩터는 이번 슬라이스에서 **제외** (각각 별 슬라이스).
- 검증: pytest TDD (실패 테스트 먼저 → 통과).

## 배경

PR #3로 입문자 프로젝트 카드가 머지됨. `review_type` 컬럼이 `research`(13섹션) / `project_card`(카드)를 가르는데, 카드 생성 여부는 전역 토글 `settings.beginner_card_mode_enabled`로 결정된다(현재 OFF). 자동 코드리뷰가 아래 두 결함을 지적했다.

---

## 버그 1 — pending INSERT의 `review_type` 하드코딩

### 문제

토글 판단식 `"project_card" if settings.beginner_card_mode_enabled else "research"`가 **`reviewer.py:64` 한 곳에만** 존재한다. 정작 리뷰 레코드를 처음 만드는 **pending INSERT 3곳 중 2곳**은 `"research"`로 하드코딩되어 있다:

- `api/routers/reviews.py:72` — 온디맨드 생성 경로(**실사용 경로**, 리뷰는 on-demand 생성).
- `api/pipeline/reviewer.py:171-177` — 배치 경로(현재 pregeneration OFF라 비활성).

카드 모드 ON일 때, pending 행은 `review_type="research"`로 들어갔다가 완료 전이(`_execute_review_pipeline`) 시점에야 `project_card`로 교정된다. 전이 전 조회/실패 시 컬럼이 실제 봉투(`context_snapshot.review_type`)와 불일치한다.

### 원인

로직이 한 곳에 있고 나머지는 복붙으로 어긋난 것 = **드리프트**. 근본 해결은 진실 공급원을 하나로 만드는 것.

### 접근 (채택: A — 단일 헬퍼)

- `api/pipeline/reviewer.py`에 헬퍼 추가:
  ```python
  def resolve_review_type() -> str:
      return "project_card" if settings.beginner_card_mode_enabled else "research"
  ```
- 사용처 3곳을 헬퍼 호출로 교체:
  - `reviewer.py:64` (`review_type_value = resolve_review_type()`)
  - `reviewer.py:175` (pending insert)
  - `reviews.py:72` (pending insert) — `from pipeline.reviewer import resolve_review_type` (이미 `run_review_from_pending`를 import 중이라 결합도 증가 없음)

**대안 B(비채택)**: 각 자리에 삼항 인라인. 디프는 작지만 복붙 3벌 → 재드리프트 위험. 이번 버그의 원인이 정확히 이것이므로 비채택.

### 사이드이펙트

- `reviews.py`에 import 1줄 추가.
- 동작 변화: 카드 모드 ON이면 pending 행도 처음부터 `project_card`. 모드 OFF(현 상태)에선 기존과 완전히 동일(`research`).

---

## 버그 2 — 카드 빈 문자열 미검증

### 문제

`parse_and_validate_card`(`api/pipeline/llm/prompts.py:274`)가 최상위 문자열 블록에 대해 **"키 존재"만** 검사하고 `""`/공백을 통과시킨다 → 웹에서 빈 섹션이 렌더된다. 리스트인 `success_checklist`는 이미 `.strip()` 체크가 있어(라인 305) 그와 일관되지 않다.

### 접근

아래 **6개 최상위 문자열 블록**에 대해 `isinstance(str)` + `.strip()` 비어있지 않음 검증 추가:

`skill_label`, `deliverable`, `success_preview`, `prerequisites`, `how_to_start`, `example_prompt`

- 실패 시 기존 패턴대로 `LLMProviderError(...)` raise → 파이프라인 failed 전이.
- **범위 밖(이번 슬라이스 제외)**: `milestones`의 `action`/`done_signal`, `troubleshooting`의 `symptom`/`fix` 등 리스트 내부 문자열. (오너 결정: 최상위 6개만.)
- `difficulty`(enum 검증됨), `estimated_minutes`(int 검증됨)는 대상 아님.

### 사이드이펙트

- LLM이 빈 문자열을 반환하면 이제 통과 대신 failed 전이. 정상 응답엔 영향 없음.

---

## 테스트 (pytest, TDD)

- `api/tests/`에 버그별 실패 테스트 먼저 작성 → 구현으로 통과.
- 버그 1:
  - 카드 모드 ON에서 pending INSERT payload의 `review_type == "project_card"` 검증(온디맨드 경로 `reviews.py` + 배치 `reviewer.py`).
  - 모드 OFF에서 `"research"` 유지(회귀 방지) — 기존 `test_signal_builder_reviewer.py:253` 유지/보강.
- 버그 2:
  - 6개 필드 각각에 대해 `""`/공백이면 `LLMProviderError` raise. 정상 카드는 통과(기존 `test_card_pipeline.py` green 유지).

## 완료 기준

- 위 테스트 전부 green, 기존 백엔드 테스트 회귀 없음.
- 웹/DB 스키마 변경 없음(순수 백엔드 로직).
