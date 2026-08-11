# 학습 경로 링크 검증 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 학습 경로 생성 시점에 리소스 링크 생존을 검증해, 확실히 죽은 링크(404/410/네트워크 실패)만 검색 링크로 교체하고 프론트에 '검색으로 찾기'로 표시한다.

**Architecture:** 백엔드 `coach.py` 파이프라인이 LLM 결과를 검증한 직후, 신규 `link_verifier.py`가 URL을 동시(concurrent) GET으로 확인한다. 죽은 링크는 구글 검색 링크 + `is_search_fallback` 플래그로 교체된다. 검증은 토글로 on/off 하며, 실패해도 원본 링크로 학습 경로를 정상 생성한다(안전 폴백). 프론트는 플래그가 있으면 외부링크 아이콘 대신 '🔍 검색으로 찾기' 라벨을 렌더한다.

**Tech Stack:** Python, httpx(동기 Client, 이미 설치됨), pytest, Next.js 16 / React 19 (TypeScript).

## Global Constraints

- 반환 resources 리스트는 입력과 **같은 길이(5)·같은 순서·같은 `type`**을 유지한다.
- `applied_idea`(빈 `url`) 카드는 검증 대상에서 제외한다.
- "깨짐" 판정은 보수적: **404, 410, 네트워크 실패(timeout/connect 등)만**. 403·401·429·5xx는 유지.
- 검색 링크: `https://www.google.com/search?q=<urlencoded>`, query = `"{technology_name} {라벨}"`.
- 프론트: 추가 키(`is_search_fallback`)는 백엔드 검증(`_LEARNING_PATH_RESOURCE_KEYS`가 `issubset`)을 깨지 않는다.
- 새 코드/주석은 기존 코드처럼 **한국어 주석** 스타일을 따른다.

---

### Task 1: 백엔드 `link_verifier` 모듈 (핵심 로직 + 유닛 테스트)

**Files:**
- Create: `api/pipeline/link_verifier.py`
- Test: `api/tests/test_link_verifier.py`

**Interfaces:**
- Consumes: `httpx.Client`(주입).
- Produces:
  - `BROWSER_UA: str`
  - `build_http_client() -> httpx.Client` — `follow_redirects=True`, 브라우저 UA 헤더.
  - `verify_and_fix_links(resources: list[dict], technology_name: str, client: httpx.Client, timeout: float) -> list[dict]`
  - `_search_url(technology_name: str, resource_type: str) -> str`

- [ ] **Step 1: 실패하는 유닛 테스트 작성**

Create `api/tests/test_link_verifier.py`:

```python
from unittest.mock import MagicMock

import httpx
import pytest

from pipeline.link_verifier import verify_and_fix_links, _search_url


class _Resp:
    def __init__(self, status_code: int):
        self.status_code = status_code


def _client(status_by_url: dict):
    """url→상태코드(int) 또는 예외 인스턴스를 돌려주는 mock httpx.Client."""
    client = MagicMock()

    def _get(url, timeout=None):
        val = status_by_url[url]
        if isinstance(val, Exception):
            raise val
        return _Resp(val)

    client.get.side_effect = _get
    return client


def _resources():
    return [
        {"type": "official_docs", "title": "T1", "url": "https://a.dev/docs", "descriptor": "d1"},
        {"type": "core_material", "title": "T2", "url": "https://b.dev/guide", "descriptor": "d2"},
        {"type": "github", "title": "T3", "url": "https://github.com/x/y", "descriptor": "d3"},
        {"type": "practice_example", "title": "T4", "url": "https://c.dev/ex", "descriptor": "d4"},
        {"type": "applied_idea", "title": "T5", "url": "", "descriptor": "d5"},
    ]


def test_alive_links_are_kept_unchanged():
    urls = {r["url"]: 200 for r in _resources() if r["url"]}
    out = verify_and_fix_links(_resources(), "LangGraph", _client(urls), 5.0)
    assert [r["url"] for r in out[:4]] == [r["url"] for r in _resources()[:4]]
    assert all("is_search_fallback" not in r for r in out)


def test_404_link_is_replaced_with_search_and_flagged():
    urls = {r["url"]: 200 for r in _resources() if r["url"]}
    urls["https://a.dev/docs"] = 404
    out = verify_and_fix_links(_resources(), "LangGraph", _client(urls), 5.0)
    assert out[0]["is_search_fallback"] is True
    assert out[0]["url"].startswith("https://www.google.com/search?q=")
    assert "LangGraph" in out[0]["url"]
    # 제목/설명/타입은 원본 유지
    assert (out[0]["title"], out[0]["descriptor"], out[0]["type"]) == ("T1", "d1", "official_docs")


def test_410_link_is_replaced():
    urls = {r["url"]: 200 for r in _resources() if r["url"]}
    urls["https://b.dev/guide"] = 410
    out = verify_and_fix_links(_resources(), "LangGraph", _client(urls), 5.0)
    assert out[1]["is_search_fallback"] is True


@pytest.mark.parametrize("err", [httpx.TimeoutException("t"), httpx.ConnectError("c")])
def test_network_failures_are_replaced(err):
    urls = {r["url"]: 200 for r in _resources() if r["url"]}
    urls["https://c.dev/ex"] = err
    out = verify_and_fix_links(_resources(), "LangGraph", _client(urls), 5.0)
    assert out[3]["is_search_fallback"] is True


@pytest.mark.parametrize("code", [401, 403, 429, 500, 503])
def test_ambiguous_statuses_are_kept(code):
    urls = {r["url"]: 200 for r in _resources() if r["url"]}
    urls["https://a.dev/docs"] = code
    out = verify_and_fix_links(_resources(), "LangGraph", _client(urls), 5.0)
    assert "is_search_fallback" not in out[0]
    assert out[0]["url"] == "https://a.dev/docs"


def test_applied_idea_empty_url_is_untouched_and_not_requested():
    urls = {r["url"]: 200 for r in _resources() if r["url"]}
    client = _client(urls)
    out = verify_and_fix_links(_resources(), "LangGraph", client, 5.0)
    assert out[4]["url"] == ""
    assert "is_search_fallback" not in out[4]
    requested = {call.args[0] for call in client.get.call_args_list}
    assert "" not in requested


def test_length_order_and_types_preserved():
    urls = {r["url"]: 404 for r in _resources() if r["url"]}
    out = verify_and_fix_links(_resources(), "LangGraph", _client(urls), 5.0)
    assert len(out) == 5
    assert [r["type"] for r in out] == [r["type"] for r in _resources()]


def test_search_url_includes_tech_and_label_encoded():
    url = _search_url("Llama Index", "official_docs")
    assert url.startswith("https://www.google.com/search?q=")
    # 공백은 quote_plus로 '+' 인코딩
    assert "Llama+Index" in url
    assert "%EA%B3%B5%EC%8B%9D" in url  # '공식'의 URL 인코딩 일부
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd api && python -m pytest tests/test_link_verifier.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.link_verifier'`

- [ ] **Step 3: `link_verifier.py` 구현**

Create `api/pipeline/link_verifier.py`:

```python
"""학습 경로 리소스의 외부 링크 생존을 검증하고, 죽은 링크를 검색 링크로 교체한다.

브라우저에서는 CORS 때문에 타 도메인 링크 생존을 확인할 수 없어, 학습 경로 생성 시점에
서버에서 검증한다. 멀쩡한 링크를 검색으로 잘못 교체하는 오검출을 피하려고 '깨짐' 판정은
404/410/네트워크 실패로만 보수적으로 한정한다(403 등 봇 차단·일시 장애는 유지).
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote_plus

import httpx

_log = logging.getLogger(__name__)

# 검색 쿼리에 붙일 자료유형 라벨(검색어 최적화용).
_SEARCH_LABELS = {
    "official_docs": "공식 문서",
    "core_material": "핵심 자료",
    "github": "github",
    "practice_example": "실습 예제",
}

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# 확실히 사라진 경우만 깨짐으로 본다.
_DEAD_STATUS = {404, 410}


def build_http_client() -> httpx.Client:
    """링크 검증용 httpx.Client. 리다이렉트를 따라가고 브라우저 UA를 사용한다."""
    return httpx.Client(follow_redirects=True, headers={"User-Agent": BROWSER_UA})


def _search_url(technology_name: str, resource_type: str) -> str:
    label = _SEARCH_LABELS.get(resource_type, "")
    query = f"{technology_name} {label}".strip()
    return f"https://www.google.com/search?q={quote_plus(query)}"


def _is_alive(client: httpx.Client, url: str, timeout: float) -> bool:
    """살아있으면 True. 404/410/네트워크 실패면 False. 그 외(403 등)는 True(보수적)."""
    try:
        resp = client.get(url, timeout=timeout)
    except httpx.HTTPError:
        return False
    return resp.status_code not in _DEAD_STATUS


def verify_and_fix_links(
    resources: list[dict],
    technology_name: str,
    client: httpx.Client,
    timeout: float,
) -> list[dict]:
    """URL이 있는 리소스의 생존을 동시 검증해, 죽은 링크는 검색 링크로 교체한 새 리스트를 반환.

    반환 리스트는 입력과 같은 길이·순서·type을 유지하고, url이 빈 리소스는 건드리지 않는다.
    """
    targets = [i for i, r in enumerate(resources) if (r.get("url") or "").strip()]
    if not targets:
        return [dict(r) for r in resources]

    with ThreadPoolExecutor(max_workers=len(targets)) as executor:
        alive_flags = list(
            executor.map(lambda i: _is_alive(client, resources[i]["url"], timeout), targets)
        )
    dead = {i for i, alive in zip(targets, alive_flags) if not alive}

    result = []
    for i, r in enumerate(resources):
        new_r = dict(r)
        if i in dead:
            new_r["url"] = _search_url(technology_name, r.get("type", ""))
            new_r["is_search_fallback"] = True
            _log.info("dead link replaced with search: type=%s", r.get("type"))
        result.append(new_r)
    return result
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd api && python -m pytest tests/test_link_verifier.py -q`
Expected: PASS (모든 케이스)

- [ ] **Step 5: 커밋**

```bash
git add api/pipeline/link_verifier.py api/tests/test_link_verifier.py
git commit -m "feat: 학습 경로 링크 검증 모듈(link_verifier) 추가"
```

---

### Task 2: 설정 토글 + coach 파이프라인 통합

**Files:**
- Modify: `api/core/config.py` (토글 2개 추가)
- Modify: `api/pipeline/coach.py` (검증 단계 삽입)
- Test: `api/tests/test_learning_paths.py` (기존 completes 테스트 네트워크 차단 + 신규 케이스)

**Interfaces:**
- Consumes: `pipeline.link_verifier.verify_and_fix_links`, `pipeline.link_verifier.build_http_client`, `core.config.settings`.
- Produces: `coach.verify_and_fix_links`(모듈에 임포트되어 테스트에서 monkeypatch 가능), `settings.link_verification_enabled`, `settings.link_verification_timeout_seconds`.

- [ ] **Step 1: 설정 토글 추가**

Modify `api/core/config.py` — `learnability_filter_enabled` 줄 아래(라인 ~34 부근)에 추가:

```python
    # 학습 경로 링크 검증: 생성 시점에 리소스 URL 생존 확인 → 죽은 링크(404/410/네트워크 실패)는 검색 링크로 교체.
    # 긴급 차단 토글(끄면 원본 링크 그대로 저장).
    link_verification_enabled: bool = True
    link_verification_timeout_seconds: float = 5.0
```

- [ ] **Step 2: 실패하는 통합 테스트 작성**

Modify `api/tests/test_learning_paths.py`:

(a) 기존 `test_execute_learning_path_pipeline_completes`에 `monkeypatch` 파라미터를 추가하고, 네트워크를 타지 않도록 verify를 항등함수로 대체 — 함수 시그니처와 본문 시작을 아래로 교체:

```python
def test_execute_learning_path_pipeline_completes(monkeypatch):
    """정상 실행 시 learning_paths 테이블에 completed 상태 + resources 업데이트."""
    from tests.mocks import MockLLMProvider
    from pipeline import coach as coach_mod
    # 링크 검증이 실제 네트워크를 타지 않도록 항등함수로 대체(검증 로직은 test_link_verifier에서 검증).
    monkeypatch.setattr(coach_mod, "verify_and_fix_links", lambda resources, *a, **k: resources)
```

(b) 파일 끝에 신규 테스트 3개 추가:

```python
def _completes_client():
    """completes/failed 테스트와 동일한 성공 경로 mock client + 상태 기록 리스트를 돌려준다."""
    mock_client = MagicMock()
    statuses: list[str] = []
    datas: list[dict] = []

    def table_side_effect(table_name):
        c = _chain()
        if table_name == "signals":
            c.execute.return_value.data = [{
                "id": TEST_SIGNAL_ID, "technology_name": "LangGraph", "summary": "요약",
            }]
        elif table_name == "signal_sources":
            c.execute.return_value.data = []
        elif table_name == "decisions":
            c.execute.return_value.data = [{"review_id": TEST_REVIEW_ID}]
        elif table_name == "reviews":
            c.execute.return_value.data = [{"project_id": TEST_PROJECT_ID}]
        elif table_name == "projects":
            c.execute.return_value.data = [{"user_id": TEST_USER_ID}]
        elif table_name == "user_profiles":
            c.execute.return_value.data = [{
                "role": "backend", "tech_stack": ["Python"],
                "project_goal": "ai_side_project", "experience_level": "intermediate",
            }]
        elif table_name == "learning_paths":
            def update_side_effect(data):
                datas.append(data)
                if "status" in data:
                    statuses.append(data["status"])
                return c
            c.update.side_effect = update_side_effect
        return c

    mock_client.table.side_effect = table_side_effect
    return mock_client, statuses, datas


def test_pipeline_calls_verify_when_enabled(monkeypatch):
    """토글 on이면 verify 결과가 completed의 resources로 저장된다."""
    from tests.mocks import MockLLMProvider
    from pipeline import coach as coach_mod

    marker = [{"type": "official_docs", "title": "X", "url": "https://s", "descriptor": "d",
               "is_search_fallback": True}]
    called = {}
    def fake_verify(resources, tech, client, timeout):
        called["tech"] = tech
        return marker
    monkeypatch.setattr(coach_mod.settings, "link_verification_enabled", True)
    monkeypatch.setattr(coach_mod, "verify_and_fix_links", fake_verify)

    mock_client, statuses, datas = _completes_client()
    coach_mod._execute_learning_path_pipeline(
        TEST_LEARNING_PATH_ID, TEST_DECISION_ID, TEST_SIGNAL_ID, mock_client, MockLLMProvider()
    )
    assert "completed" in statuses
    completed = next(d for d in datas if d.get("status") == "completed")
    assert completed["resources"] == marker
    assert called["tech"] == "LangGraph"


def test_pipeline_skips_verify_when_disabled(monkeypatch):
    """토글 off면 verify를 호출하지 않고 원본 resources로 저장한다."""
    from tests.mocks import MockLLMProvider
    from pipeline import coach as coach_mod

    def boom(*a, **k):
        raise AssertionError("verify는 호출되면 안 됨")
    monkeypatch.setattr(coach_mod.settings, "link_verification_enabled", False)
    monkeypatch.setattr(coach_mod, "verify_and_fix_links", boom)

    mock_client, statuses, datas = _completes_client()
    coach_mod._execute_learning_path_pipeline(
        TEST_LEARNING_PATH_ID, TEST_DECISION_ID, TEST_SIGNAL_ID, mock_client, MockLLMProvider()
    )
    completed = next(d for d in datas if d.get("status") == "completed")
    assert len(completed["resources"]) == 5


def test_pipeline_falls_back_to_original_when_verify_raises(monkeypatch):
    """verify가 예외를 던져도 원본 resources로 completed 저장(안전 폴백)."""
    from tests.mocks import MockLLMProvider
    from pipeline import coach as coach_mod

    def boom(*a, **k):
        raise RuntimeError("verify 폭발")
    monkeypatch.setattr(coach_mod.settings, "link_verification_enabled", True)
    monkeypatch.setattr(coach_mod, "verify_and_fix_links", boom)

    mock_client, statuses, datas = _completes_client()
    coach_mod._execute_learning_path_pipeline(
        TEST_LEARNING_PATH_ID, TEST_DECISION_ID, TEST_SIGNAL_ID, mock_client, MockLLMProvider()
    )
    assert "completed" in statuses
    completed = next(d for d in datas if d.get("status") == "completed")
    assert len(completed["resources"]) == 5
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd api && python -m pytest tests/test_learning_paths.py -q`
Expected: FAIL — `AttributeError: module 'pipeline.coach' has no attribute 'verify_and_fix_links'`

- [ ] **Step 4: coach.py에 검증 단계 통합**

Modify `api/pipeline/coach.py`:

(a) 임포트 추가 (기존 `from core.supabase import get_supabase` 아래):

```python
from core.config import settings
from pipeline.link_verifier import build_http_client, verify_and_fix_links
```

(b) resources 검증 블록(현재 라인 ~91, `if resource_types != LEARNING_PATH_RESOURCE_TYPES:` 검사 직후)과 `completed 상태 전이` 사이에 삽입:

```python
        # 링크 검증: 죽은 링크(404/410/네트워크 실패)를 검색 링크로 교체.
        # 검증 자체가 실패해도 원본 resources로 진행한다(링크 확인 실패가 학습 경로 생성을 막지 않도록).
        if settings.link_verification_enabled:
            try:
                with build_http_client() as http_client:
                    resources = verify_and_fix_links(
                        resources,
                        signal_data["technology_name"],
                        http_client,
                        settings.link_verification_timeout_seconds,
                    )
            except Exception:
                _log.exception(
                    "link verification failed; proceeding with original resources learning_path_id=%s",
                    learning_path_id,
                )
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd api && python -m pytest tests/test_learning_paths.py tests/test_link_verifier.py -q`
Expected: PASS (전체)

- [ ] **Step 6: 커밋**

```bash
git add api/core/config.py api/pipeline/coach.py api/tests/test_learning_paths.py
git commit -m "feat: coach 파이프라인에 링크 검증 통합 + 토글/안전 폴백"
```

---

### Task 3: 프론트 — '검색으로 찾기' 표시

**Files:**
- Modify: `web/src/components/home/learning-path/learning-path-card.tsx`

**Interfaces:**
- Consumes: 백엔드가 저장한 resource의 선택적 `is_search_fallback` 플래그.
- Produces: 플래그가 있으면 외부링크 아이콘 대신 '🔍 검색으로 찾기' 라벨.

- [ ] **Step 1: 인터페이스에 플래그 추가**

Modify `learning-path-card.tsx` — `LearningPathResource` 인터페이스에 필드 추가:

```typescript
export interface LearningPathResource {
  type: "official_docs" | "core_material" | "github" | "practice_example" | "applied_idea" | string;
  title: string;
  url: string;
  descriptor: string;
  is_search_fallback?: boolean;
}
```

- [ ] **Step 2: 우측 아이콘 영역을 조건부 렌더로 교체**

`LearningPathCard` 본문에서 `const isEnglishLabel = ...` 아래에 파생값 추가:

```typescript
  const isSearchFallback = Boolean(resource.is_search_fallback);
```

그리고 우측 `{hasUrl && ( <svg ... /> )}` 블록 전체를 아래로 교체:

```tsx
        {hasUrl &&
          (isSearchFallback ? (
            <span
              className="text-badge"
              style={{ flexShrink: 0, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}
            >
              🔍 검색으로 찾기
            </span>
          ) : (
            <svg
              aria-hidden="true"
              width="14"
              height="14"
              viewBox="0 0 14 14"
              fill="none"
              style={{ flexShrink: 0, color: "var(--text-tertiary)" }}
            >
              <path
                d="M5.5 2.5H2.5C1.94772 2.5 1.5 2.94772 1.5 3.5V11.5C1.5 12.0523 1.94772 12.5 2.5 12.5H10.5C11.0523 12.5 11.5 12.0523 11.5 11.5V8.5"
                stroke="currentColor"
                strokeWidth="1.3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path d="M8 1.5H12.5V6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M12.5 1.5L6.5 7.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          ))}
```

- [ ] **Step 3: 린트/타입 확인**

Run: `cd web && npx next lint --file src/components/home/learning-path/learning-path-card.tsx`
Expected: 에러 없음. (lint 미설정이면 `npx tsc --noEmit -p .` 로 타입만 확인 — 신규 에러 없음)

- [ ] **Step 4: 수동 검증(앱 실행)**

로컬에서 web(:3000) + backend(:8000) 실행 후, 학습 경로가 있는 signal의 `learning-path` 화면을 연다.
- 정상 링크 카드: 우측에 외부링크(↗) 아이콘.
- (검증용) `settings.link_verification_timeout_seconds`를 아주 짧게(예: 0.001) 두거나, 존재하지 않는 URL을 반환하도록 유도해 재생성 → 해당 카드 우측에 **'🔍 검색으로 찾기'** 라벨, 클릭 시 구글 검색 새 탭.

- [ ] **Step 5: 커밋**

```bash
git add web/src/components/home/learning-path/learning-path-card.tsx
git commit -m "feat: 학습 카드에 검색 대체 링크 표시(is_search_fallback)"
```

---

## 완료 후

- `docs/superpowers/plans/` 이 계획 파일 커밋.
- 필요 시 브랜치 `feat/learning-link-verification` → main 통합은 `superpowers:finishing-a-development-branch` 참고.
- 메모리 `signal-quality-roadmap` 업데이트: 작업 B 1단계(링크 검증) 완료, 다음은 경로 구조 안내(목표/순서/무엇을배우나).
