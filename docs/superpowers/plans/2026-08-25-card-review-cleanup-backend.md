# 카드 코드리뷰 잔여 정리 (백엔드 버그 2개) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PR #3 자동 코드리뷰가 지적한 백엔드 버그 2개(pending INSERT `review_type` 드리프트, 카드 빈 문자열 미검증)를 TDD로 고친다.

**Architecture:** 순수 백엔드 로직 변경. 버그1은 토글→review_type 판단을 `resolve_review_type()` 헬퍼 하나로 통일하고 pending INSERT 3곳에 적용한다. 버그2는 `parse_and_validate_card`에 최상위 6개 문자열 블록의 빈 문자열 검증을 추가한다. 웹·DB 스키마 변경 없음.

**Tech Stack:** Python, FastAPI, pytest, Supabase 클라이언트(테스트는 MagicMock/FakeClient로 목).

## Global Constraints

- 작업 디렉터리 루트는 `api/`. 모든 pytest는 `api/`에서 실행: `cd api && python -m pytest ...`.
- 실패 시 예외는 기존 패턴대로 `LLMProviderError`(from `pipeline.llm.base`) 사용.
- 토글은 `settings.beginner_card_mode_enabled` (기본 False). 기본값에서 동작은 기존과 완전히 동일해야 함(회귀 금지).
- 기존 백엔드 테스트 전부 green 유지.

---

### Task 1: 버그 2 — 카드 빈 문자열 검증

먼저 착수(파일 1개로 독립적, 가장 단순).

**Files:**
- Modify: `api/pipeline/llm/prompts.py:274-306` (`parse_and_validate_card`)
- Test: `api/tests/test_project_card_prompt.py` (기존 파일에 추가)

**Interfaces:**
- Consumes: `parse_and_validate_card(raw: str) -> None`, `LLMProviderError`, `_valid_card()` 헬퍼(테스트 파일에 이미 존재).
- Produces: 없음(검증 로직 강화만).

대상 6개 최상위 문자열 블록: `skill_label`, `deliverable`, `success_preview`, `prerequisites`, `how_to_start`, `example_prompt`.

- [ ] **Step 1: 실패 테스트 추가**

`api/tests/test_project_card_prompt.py` 끝에 추가:

```python
_STRING_BLOCKS = [
    "skill_label", "deliverable", "success_preview",
    "prerequisites", "how_to_start", "example_prompt",
]


@pytest.mark.parametrize("field", _STRING_BLOCKS)
@pytest.mark.parametrize("bad", ["", "   "])
def test_empty_string_block_raises(field, bad):
    card = _valid_card()
    card[field] = bad
    with pytest.raises(LLMProviderError, match=field):
        parse_and_validate_card(json.dumps(card))


@pytest.mark.parametrize("field", _STRING_BLOCKS)
def test_non_string_block_raises(field):
    card = _valid_card()
    card[field] = 123
    with pytest.raises(LLMProviderError, match=field):
        parse_and_validate_card(json.dumps(card))
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd api && python -m pytest tests/test_project_card_prompt.py -v`
Expected: `test_empty_string_block_raises`, `test_non_string_block_raises`가 FAIL (현재는 빈 문자열/정수가 통과되므로 raise 안 됨).

- [ ] **Step 3: 검증 구현**

`api/pipeline/llm/prompts.py` `parse_and_validate_card` 안, `success_checklist` 검증 블록(현재 파일 306행 근처, `for c in checklist:` 루프) **뒤에** 아래를 추가:

```python
    for field in (
        "skill_label", "deliverable", "success_preview",
        "prerequisites", "how_to_start", "example_prompt",
    ):
        value = parsed[field]
        if not isinstance(value, str) or not value.strip():
            raise LLMProviderError(f"{field}가 비어있거나 문자열이 아님: {value!r}")
```

(주의: `parsed[field]`는 안전하다 — 위쪽 `missing` 체크에서 6개 키의 존재가 이미 보장됨.)

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd api && python -m pytest tests/test_project_card_prompt.py -v`
Expected: 신규 테스트 + 기존 `test_valid_card_passes` 등 전부 PASS.

- [ ] **Step 5: 커밋**

```bash
git add api/pipeline/llm/prompts.py api/tests/test_project_card_prompt.py
git commit -m "fix(cards): parse_and_validate_card — 최상위 6개 문자열 블록 빈값/비문자열 검증

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: 버그 1 — `resolve_review_type()` 헬퍼로 pending INSERT 통일

**Files:**
- Modify: `api/pipeline/reviewer.py` (헬퍼 추가 + 64행 + 171-177행 insert)
- Modify: `api/routers/reviews.py:9` (import), `api/routers/reviews.py:72` (insert)
- Test: `api/tests/test_card_pipeline.py` (헬퍼 단위 테스트 추가)
- Test: `api/tests/test_reviews_trigger.py` (온디맨드 경로 토글-on 테스트 추가)
- Test: `api/tests/test_signal_builder_reviewer.py` (배치 경로 토글-on 테스트 추가)

**Interfaces:**
- Produces: `pipeline.reviewer.resolve_review_type() -> str` — `settings.beginner_card_mode_enabled`가 True면 `"project_card"`, 아니면 `"research"` 반환.
- Consumes: `reviewer.settings`(monkeypatch 대상), `_make_reviewer_mock_client()`(test_signal_builder_reviewer.py), TestClient 목 패턴(test_reviews_trigger.py).

- [ ] **Step 1: 실패 테스트 추가 — 헬퍼 단위**

`api/tests/test_card_pipeline.py` 끝에 추가:

```python
def test_resolve_review_type_toggle_on(monkeypatch):
    monkeypatch.setattr(reviewer.settings, "beginner_card_mode_enabled", True)
    assert reviewer.resolve_review_type() == "project_card"


def test_resolve_review_type_toggle_off(monkeypatch):
    monkeypatch.setattr(reviewer.settings, "beginner_card_mode_enabled", False)
    assert reviewer.resolve_review_type() == "research"
```

- [ ] **Step 2: 실패 테스트 추가 — 온디맨드 경로(reviews.py)**

`api/tests/test_reviews_trigger.py` 끝에 추가 (기존 `test_trigger_review_returns_202_with_review_id` 구조 재사용):

```python
def test_trigger_review_pending_review_type_follows_card_toggle(monkeypatch):
    """카드 모드 ON이면 pending INSERT의 review_type이 project_card로 들어간다."""
    import middleware.auth as auth_module
    import pipeline.reviewer as reviewer_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)
    monkeypatch.setattr(reviewer_module.settings, "beginner_card_mode_enabled", True)

    insert_payloads = []
    reviews_call_count = [0]

    def table_side_effect(table_name):
        c = _chain()
        if table_name == "projects":
            c.execute.return_value.data = [{"id": TEST_PROJECT_ID}]
        elif table_name == "reviews":
            reviews_call_count[0] += 1
            if reviews_call_count[0] == 1:
                c.execute.return_value.data = []  # 멱등성 체크: 기존 없음
            else:
                c.execute.return_value.data = [{"id": TEST_REVIEW_ID}]

                def capture_insert(payload):
                    insert_payloads.append(payload)
                    return c
                c.insert.side_effect = capture_insert
        return c

    mock_client = MagicMock()
    mock_client.table.side_effect = table_side_effect

    with patch("routers.reviews.get_supabase", return_value=mock_client), \
         patch("routers.reviews.run_review_from_pending"):
        from main import app
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/reviews/trigger",
                json={"signal_id": TEST_SIGNAL_ID},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )

    assert response.status_code == 202
    assert len(insert_payloads) == 1
    assert insert_payloads[0]["review_type"] == "project_card"
```

- [ ] **Step 3: 실패 테스트 추가 — 배치 경로(reviewer.py:175)**

`api/tests/test_signal_builder_reviewer.py`의 `test_reviewer_inserts_pending_review` **바로 아래**에 추가:

```python
def test_reviewer_pending_insert_review_type_follows_card_toggle(monkeypatch):
    """카드 모드 ON이면 배치 경로 pending INSERT의 review_type도 project_card."""
    import pipeline.reviewer as reviewer_module
    monkeypatch.setattr(reviewer_module.settings, "beginner_card_mode_enabled", True)
    mock_client = _make_reviewer_mock_client()
    llm = MockLLMProvider()

    review_signal("sig-uuid", "proj-uuid", mock_client, llm, brief_date="2026-07-24")

    mock_client._reviews_mock.insert.assert_called_once()
    insert_payload = mock_client._reviews_mock.insert.call_args[0][0]
    assert insert_payload["review_type"] == "project_card"
```

- [ ] **Step 4: 세 테스트 파일 모두 실패 확인**

Run:
```bash
cd api && python -m pytest \
  tests/test_card_pipeline.py::test_resolve_review_type_toggle_on \
  tests/test_reviews_trigger.py::test_trigger_review_pending_review_type_follows_card_toggle \
  tests/test_signal_builder_reviewer.py::test_reviewer_pending_insert_review_type_follows_card_toggle -v
```
Expected: 헬퍼 테스트는 `AttributeError: module 'pipeline.reviewer' has no attribute 'resolve_review_type'`로 FAIL, 나머지 둘은 `review_type == "research"`라서 assert FAIL.

- [ ] **Step 5: 헬퍼 추가 + 3곳 적용**

`api/pipeline/reviewer.py` 모듈 최상단(함수 `_execute_review_pipeline` 정의 **위**, import 블록 아래, `_log = ...` 근처)에 추가:

```python
def resolve_review_type() -> str:
    """카드 모드 토글에 따라 review_type 문자열을 반환.

    pending INSERT(배치·온디맨드)와 완료 전이가 공유하는 단일 진실 공급원.
    """
    return "project_card" if settings.beginner_card_mode_enabled else "research"
```

같은 파일 64행을 교체:

```python
        review_type_value = resolve_review_type()
```

같은 파일 171-177행 insert의 `"review_type"` 줄을 교체:

```python
            "review_type": resolve_review_type(),
```

`api/routers/reviews.py:9` import 교체:

```python
from pipeline.reviewer import resolve_review_type, run_review_from_pending
```

`api/routers/reviews.py:72`의 `"review_type"` 줄을 교체:

```python
            "review_type": resolve_review_type(),
```

- [ ] **Step 6: 신규 + 기존 테스트 통과 확인**

Run:
```bash
cd api && python -m pytest \
  tests/test_card_pipeline.py \
  tests/test_reviews_trigger.py \
  tests/test_signal_builder_reviewer.py -v
```
Expected: 신규 3개 PASS. 기존 `test_reviewer_inserts_pending_review`(토글 기본 off → `"research"`)도 PASS 유지(회귀 없음).

- [ ] **Step 7: 커밋**

```bash
git add api/pipeline/reviewer.py api/routers/reviews.py \
  api/tests/test_card_pipeline.py api/tests/test_reviews_trigger.py \
  api/tests/test_signal_builder_reviewer.py
git commit -m "fix(cards): pending INSERT review_type를 resolve_review_type() 헬퍼로 통일

토글 판단이 reviewer.py 한 곳에만 있어 pending INSERT 2곳이 research로 하드코딩된
드리프트 해결. 온디맨드(reviews.py)·배치(reviewer.py) 경로 모두 토글 반영.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: 전체 백엔드 회귀 확인

**Files:** 없음(검증만).

- [ ] **Step 1: 백엔드 전체 테스트**

Run: `cd api && python -m pytest -q`
Expected: 전부 PASS. 실패 시 해당 Task로 돌아가 수정.

---

## Self-Review 결과

- **스펙 커버리지:** 버그1(3곳 통일 + 헬퍼) = Task 2, 버그2(6개 문자열) = Task 1, 회귀 = Task 3. 스펙의 "웹/DB 변경 없음"·"pytest TDD" 준수. 갭 없음.
- **플레이스홀더:** 없음(모든 코드/명령/기대출력 명시).
- **타입 일관성:** `resolve_review_type() -> str` 이름·시그니처가 Task 2 전체에서 일치. `_STRING_BLOCKS` 6개 필드가 스펙과 일치.
