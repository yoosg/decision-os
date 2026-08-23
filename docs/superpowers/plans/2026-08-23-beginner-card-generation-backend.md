# 입문자 프로젝트 카드 생성(백엔드) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 13섹션 "Research Review" 생성 경로 옆에, 입문자용 **7블록 "프로젝트 카드"**를 LLM으로 생성·검증·저장하는 백엔드 경로를 토글 뒤에 추가한다.

**Architecture:** 기존 리뷰 생성 파이프라인(`api/pipeline/`)의 패턴을 그대로 따른다. 프롬프트·스키마·검증은 `pipeline/llm/prompts.py`에, 생성 메서드는 `LLMProvider` 인터페이스(`pipeline/llm/base.py`)와 3개 구현체(OpenAI/Gemini/Mock)에 추가한다. `reviewer.py`의 파이프라인은 config 토글(`beginner_card_mode_enabled`)로 카드 경로/기존 경로를 분기한다. 카드는 `reviews.result` JSONB 봉투에 `review_type="project_card"`로 저장(마이그레이션 불필요 — `review_type` 컬럼에 값 CHECK 없음).

**Tech Stack:** Python 3.11 · FastAPI · pytest (asyncio_mode=auto) · Supabase(Postgres) · OpenAI Responses API / Google GenAI

## Global Constraints

- 테스트 실행 위치: `api/` 디렉터리에서 `pytest tests/<file>::<test> -v`.
- 카드는 **제네릭(개인화 없음)** — 개인화(도메인 예시)는 다음 슬라이스. 이 슬라이스는 유저 프로필을 카드 생성에 쓰지 않는다.
- LLM 응답 형식 규칙(기존과 동일): OpenAI Responses API `json_object` 포맷은 input 메시지에 `json` 단어가 있어야 함 → 카드 input 끝에도 `"\n\n반드시 JSON 객체로 응답하세요."`를 붙인다.
- 저장 봉투 불변: `{"schema_version": 1, "review_type": <str>, "payload": <dict>}` (DB `chk_result_envelope` 제약).
- `playbook_type`은 `'ai_research'` 유지(CHECK 제약). 카드는 `review_type`으로만 구분.
- 에러 표준화: 검증 실패는 `LLMProviderError`를 던진다(기존 패턴).
- 토글 기본값 `beginner_card_mode_enabled=False` — 켜기 전까지 기존 13섹션 경로가 그대로 동작(안전 롤아웃).

---

### Task 1: 카드 스키마 · 프롬프트 · 검증 (`prompts.py`)

순수 함수/상수만 추가한다. LLM·DB 무관, 단위 테스트가 쉽다.

**Files:**
- Modify: `api/pipeline/llm/prompts.py` (파일 끝에 추가)
- Test: `api/tests/test_project_card_prompt.py` (신규)

**Interfaces:**
- Produces:
  - `REQUIRED_CARD_BLOCKS: list[str]`
  - `CARD_DIFFICULTIES: list[str]` = `["first_step", "basic", "challenge"]`
  - `PROJECT_CARD_SYSTEM_PROMPT: str`
  - `build_card_user_content(context: ReviewContext) -> str`
  - `parse_and_validate_card(raw: str) -> None` (검증 실패 시 `LLMProviderError`)

- [ ] **Step 1: 실패하는 테스트 작성**

Create `api/tests/test_project_card_prompt.py`:

```python
import json

import pytest

from pipeline.llm.base import LLMProviderError, ReviewContext
from pipeline.llm.prompts import (
    REQUIRED_CARD_BLOCKS,
    build_card_user_content,
    parse_and_validate_card,
)


def _valid_card() -> dict:
    return {
        "skill_label": "웹폼 만들고 데이터 저장하기",
        "difficulty": "first_step",
        "estimated_minutes": 30,
        "deliverable": "이름과 메모를 입력해 저장하는 간단한 웹페이지",
        "success_preview": "저장을 누르면 목록에 내가 쓴 내용이 나타난다",
        "prerequisites": "없어요, 바로 시작!",
        "how_to_start": "AI 코딩 도구를 열고 아래 예시 프롬프트를 붙여넣어 시작하세요.",
        "example_prompt": "이름과 메모를 입력받아 저장하는 간단한 웹페이지를 만들어줘.",
        "milestones": [
            {"action": "화면 뼈대 만들기", "done_signal": "입력칸이 화면에 뜬다"},
            {"action": "저장 기능 붙이기", "done_signal": "제출하면 데이터가 남는다"},
            {"action": "확인하고 다듬기", "done_signal": "저장한 내용이 다시 보인다"},
        ],
        "troubleshooting": [
            {"symptom": "저장을 눌러도 반응이 없다", "fix": "'저장 버튼을 눌렀을 때 저장되도록 고쳐줘'라고 요청하세요."},
        ],
        "success_checklist": ["입력칸이 보인다", "저장하면 목록에 나타난다"],
    }


def test_valid_card_passes():
    parse_and_validate_card(json.dumps(_valid_card()))  # 예외 없이 통과


def test_missing_block_raises():
    card = _valid_card()
    del card["deliverable"]
    with pytest.raises(LLMProviderError, match="필수 블록 누락"):
        parse_and_validate_card(json.dumps(card))


def test_bad_difficulty_raises():
    card = _valid_card()
    card["difficulty"] = "expert"
    with pytest.raises(LLMProviderError, match="difficulty"):
        parse_and_validate_card(json.dumps(card))


def test_milestones_out_of_range_raises():
    card = _valid_card()
    card["milestones"] = card["milestones"][:2]  # 2개 → 3~5 위반
    with pytest.raises(LLMProviderError, match="milestones"):
        parse_and_validate_card(json.dumps(card))


def test_non_positive_minutes_raises():
    card = _valid_card()
    card["estimated_minutes"] = 0
    with pytest.raises(LLMProviderError, match="estimated_minutes"):
        parse_and_validate_card(json.dumps(card))


def test_all_required_blocks_present_in_valid_fixture():
    card = _valid_card()
    assert all(k in card for k in REQUIRED_CARD_BLOCKS)


def test_build_card_user_content_includes_topic_and_sources():
    ctx = ReviewContext(
        technology_name="간단한 챗봇",
        signal_sources=[{"source_type": "github", "url": "https://x", "title": "예제"}],
    )
    out = build_card_user_content(ctx)
    assert "간단한 챗봇" in out
    assert "https://x" in out
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd api && pytest tests/test_project_card_prompt.py -v`
Expected: FAIL — `ImportError: cannot import name 'REQUIRED_CARD_BLOCKS'` (및 `build_card_user_content`, `parse_and_validate_card`).

- [ ] **Step 3: 구현 추가**

Append to `api/pipeline/llm/prompts.py` (파일 맨 끝):

```python
REQUIRED_CARD_BLOCKS = [
    "skill_label", "difficulty", "estimated_minutes",
    "deliverable", "success_preview", "prerequisites",
    "how_to_start", "example_prompt",
    "milestones", "troubleshooting", "success_checklist",
]

CARD_DIFFICULTIES = ["first_step", "basic", "challenge"]

PROJECT_CARD_SYSTEM_PROMPT = """당신은 '개발 입문자'를 위한 학습 코치입니다. 주어진 기술/토픽으로 입문자가 직접 만들어보는(바이브코딩) '프로젝트 카드'를 JSON으로 작성하세요.
전문용어를 피하고 쉬운 말로, 누구에게나 동일한 '표준' 내용으로 작성합니다(특정 개인 맞춤 아님).
반드시 아래 11개 키를 모두 포함한 JSON 객체만 반환하세요(마크다운 코드블록 없이):
{
  "skill_label": "이 카드로 배우는 것 (한 줄, 예: '웹폼 만들고 데이터 저장하기')",
  "difficulty": "first_step|basic|challenge 중 하나",
  "estimated_minutes": 30,
  "deliverable": "완성하면 손에 쥐어지는 결과물 (2-3문장)",
  "success_preview": "이렇게 보이면 성공 — 완성 화면/상태 묘사 (1-2문장)",
  "prerequisites": "시작 전 준비물/세팅. 없으면 '없어요, 바로 시작!'",
  "how_to_start": "표준 진입점과 첫 단계 (2-4문장, 누구에게나 동일)",
  "example_prompt": "AI 코딩 도구에 복붙할 수 있는 표준 예시 프롬프트 (구체적으로)",
  "milestones": [{"action": "무엇을 함", "done_signal": "끝나면 이렇게 보임"}],
  "troubleshooting": [{"symptom": "자주 나는 문제/에러", "fix": "복붙하거나 시도할 복구 방법"}],
  "success_checklist": ["다 됐는지 확인할 체크 항목"]
}
규칙:
- milestones는 큰 단계 3~5개만(잘게 쪼개지 말 것 — 지시서가 아니라 지도).
- troubleshooting 최소 1개, success_checklist 최소 1개.
- estimated_minutes는 양의 정수(분).
- 모든 문구는 한국어, 입문자가 겁먹지 않는 친근한 말투."""

_CARD_MILESTONE_KEYS = {"action", "done_signal"}
_CARD_TROUBLE_KEYS = {"symptom", "fix"}


def build_card_user_content(context: ReviewContext) -> str:
    return (
        f"기술/토픽: {context.technology_name}\n\n"
        f"출처:\n{format_sources(context.signal_sources)}\n\n"
        f"위 토픽으로 '개발 입문자'가 직접 만들어볼 수 있는 프로젝트 카드를 JSON으로 작성하세요."
    )


def parse_and_validate_card(raw: str) -> None:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise LLMProviderError(f"LLM 응답이 유효한 JSON이 아님: {e}") from e
    if not isinstance(parsed, dict):
        raise LLMProviderError(f"LLM 응답이 JSON 객체가 아님: {type(parsed).__name__}")
    missing = [k for k in REQUIRED_CARD_BLOCKS if k not in parsed]
    if missing:
        raise LLMProviderError(f"프로젝트 카드에 필수 블록 누락: {missing}")
    if parsed["difficulty"] not in CARD_DIFFICULTIES:
        raise LLMProviderError(f"difficulty 허용 목록 밖: {parsed['difficulty']}")
    minutes = parsed["estimated_minutes"]
    if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
        raise LLMProviderError(f"estimated_minutes가 양의 정수가 아님: {minutes!r}")
    milestones = parsed["milestones"]
    if not isinstance(milestones, list) or not (3 <= len(milestones) <= 5):
        raise LLMProviderError(f"milestones는 3~5개여야 함: {milestones!r}")
    for m in milestones:
        if not isinstance(m, dict) or not _CARD_MILESTONE_KEYS.issubset(m.keys()):
            raise LLMProviderError(f"milestone 항목 키 누락: {m!r}")
    trouble = parsed["troubleshooting"]
    if not isinstance(trouble, list) or len(trouble) < 1:
        raise LLMProviderError(f"troubleshooting은 최소 1개여야 함: {trouble!r}")
    for t in trouble:
        if not isinstance(t, dict) or not _CARD_TROUBLE_KEYS.issubset(t.keys()):
            raise LLMProviderError(f"troubleshooting 항목 키 누락: {t!r}")
    checklist = parsed["success_checklist"]
    if not isinstance(checklist, list) or len(checklist) < 1:
        raise LLMProviderError(f"success_checklist는 최소 1개여야 함: {checklist!r}")
    for c in checklist:
        if not isinstance(c, str) or not c.strip():
            raise LLMProviderError(f"success_checklist 항목이 빈 문자열: {c!r}")
```

주의: `prompts.py`는 이미 상단에서 `json`, `LLMProviderError`, `ReviewContext`, `format_sources`를 import/정의하고 있으므로 추가 import 불필요.

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd api && pytest tests/test_project_card_prompt.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: 커밋**

```bash
git add api/pipeline/llm/prompts.py api/tests/test_project_card_prompt.py
git commit -m "feat(cards): 프로젝트 카드 스키마·프롬프트·검증 추가"
```

---

### Task 2: `generate_card` 인터페이스 + 3개 Provider 구현 + Mock

**Files:**
- Modify: `api/pipeline/llm/base.py` (추상 메서드 추가)
- Modify: `api/pipeline/llm/openai_provider.py` (구현)
- Modify: `api/pipeline/llm/gemini_provider.py` (구현)
- Modify: `api/tests/mocks.py` (`VALID_CARD_RESPONSE` + `generate_card`)
- Test: `api/tests/test_project_card_generation.py` (신규)

**Interfaces:**
- Consumes: `parse_and_validate_card`, `PROJECT_CARD_SYSTEM_PROMPT`, `build_card_user_content` (Task 1)
- Produces:
  - `LLMProvider.generate_card(self, context: ReviewContext) -> LLMResponse` (추상)
  - 3개 구현체의 `generate_card`
  - `tests.mocks.VALID_CARD_RESPONSE: str`, `MockLLMProvider.generate_card`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `api/tests/test_project_card_generation.py`:

```python
from pipeline.llm.base import ReviewContext
from pipeline.llm.prompts import parse_and_validate_card
from tests.mocks import VALID_CARD_RESPONSE, MockLLMProvider


def test_mock_generate_card_returns_valid_card():
    llm = MockLLMProvider()
    ctx = ReviewContext(technology_name="간단한 챗봇", signal_sources=[])
    resp = llm.generate_card(ctx)
    parse_and_validate_card(resp.content)  # 예외 없이 통과
    assert resp.model == "mock"


def test_valid_card_response_constant_passes_validation():
    parse_and_validate_card(VALID_CARD_RESPONSE)


def test_mock_generate_card_raises_when_configured():
    import pytest
    from pipeline.llm.base import LLMProviderError

    llm = MockLLMProvider(raise_error=True)
    ctx = ReviewContext(technology_name="x", signal_sources=[])
    with pytest.raises(LLMProviderError):
        llm.generate_card(ctx)
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd api && pytest tests/test_project_card_generation.py -v`
Expected: FAIL — `ImportError: cannot import name 'VALID_CARD_RESPONSE'` (또는 `MockLLMProvider` 인스턴스화 실패: 추상 메서드 `generate_card` 미구현).

- [ ] **Step 3a: 추상 메서드 추가** — `api/pipeline/llm/base.py`

`generate` 추상 메서드 바로 아래(76-77행 다음)에 추가:

```python
    @abstractmethod
    def generate_card(self, context: ReviewContext) -> LLMResponse:
        """입문자용 7블록 프로젝트 카드 JSON 생성 (제네릭, 개인화 없음)."""
        ...
```

- [ ] **Step 3b: OpenAI 구현** — `api/pipeline/llm/openai_provider.py`

`generate` 메서드(28-45행) 바로 아래에 추가:

```python
    def generate_card(self, context: ReviewContext) -> LLMResponse:
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=prompts.PROJECT_CARD_SYSTEM_PROMPT,
                input=f"{prompts.build_card_user_content(context)}\n\n반드시 JSON 객체로 응답하세요.",
                text={"format": {"type": "json_object"}},
            )
            raw = response.output_text
            prompts.parse_and_validate_card(raw)
            return LLMResponse(content=raw, model=self._model)
        except LLMProviderError:
            raise
        except OpenAIError as e:
            raise LLMProviderError(str(e)) from e
        except Exception as e:
            raise LLMProviderError(str(e)) from e
```

- [ ] **Step 3c: Gemini 구현** — `api/pipeline/llm/gemini_provider.py`

`generate` 메서드(70-76행) 바로 아래에 추가:

```python
    def generate_card(self, context: ReviewContext) -> LLMResponse:
        raw = self._generate(
            prompts.PROJECT_CARD_SYSTEM_PROMPT,
            prompts.build_card_user_content(context), as_json=True,
        )
        prompts.parse_and_validate_card(raw)
        return LLMResponse(content=raw, model=self._model)
```

- [ ] **Step 3d: Mock 구현** — `api/tests/mocks.py`

(1) `VALID_MEMORY_RESPONSE` 상수 아래(35행 다음)에 추가:

```python
VALID_CARD_RESPONSE = json.dumps({
    "skill_label": "웹폼 만들고 데이터 저장하기",
    "difficulty": "first_step",
    "estimated_minutes": 30,
    "deliverable": "이름과 메모를 입력해 저장하는 간단한 웹페이지",
    "success_preview": "저장을 누르면 목록에 내가 쓴 내용이 나타난다",
    "prerequisites": "없어요, 바로 시작!",
    "how_to_start": "AI 코딩 도구를 열고 아래 예시 프롬프트를 붙여넣어 시작하세요.",
    "example_prompt": "이름과 메모를 입력받아 저장하는 간단한 웹페이지를 만들어줘.",
    "milestones": [
        {"action": "화면 뼈대 만들기", "done_signal": "입력칸이 화면에 뜬다"},
        {"action": "저장 기능 붙이기", "done_signal": "제출하면 데이터가 남는다"},
        {"action": "확인하고 다듬기", "done_signal": "저장한 내용이 다시 보인다"},
    ],
    "troubleshooting": [
        {"symptom": "저장을 눌러도 반응이 없다", "fix": "'저장 버튼을 눌렀을 때 저장되도록 고쳐줘'라고 요청하세요."},
    ],
    "success_checklist": ["입력칸이 보인다", "저장하면 목록에 나타난다"],
})
```

(2) `__init__`(39-50행) 전체를 아래로 교체(파라미터 `card_content` + 필드 `self._card_content` 추가):

```python
    def __init__(
        self,
        content: str = VALID_13_SECTION_RESPONSE,
        raise_error: bool = False,
        signal_content: str | None = None,
        learning_path_content: str | None = None,
        card_content: str | None = None,
    ):
        self._content = content
        self._raise_error = raise_error
        self._signal_content = signal_content or VALID_SIGNAL_RESPONSE
        self._learning_path_content = learning_path_content or VALID_LEARNING_PATH_RESPONSE
        self._card_content = card_content or VALID_CARD_RESPONSE
        self.build_signal_calls: list[tuple] = []
```

(3) `generate` 메서드(52-55행) 아래에 추가:

```python
    def generate_card(self, context: ReviewContext) -> LLMResponse:
        if self._raise_error:
            raise LLMProviderError("mock LLM error")
        return LLMResponse(content=self._card_content, model="mock")
```

- [ ] **Step 4: 테스트 통과 확인 (전체 회귀 포함)**

Run: `cd api && pytest tests/test_project_card_generation.py -v`
Expected: PASS (3 passed)

Run(회귀): `cd api && pytest tests/ -q`
Expected: 기존 테스트 전부 PASS (추상 메서드 추가로 깨진 Provider 없음 — 구현체는 OpenAI/Gemini/Mock 3개뿐, 모두 구현됨).

- [ ] **Step 5: 커밋**

```bash
git add api/pipeline/llm/base.py api/pipeline/llm/openai_provider.py api/pipeline/llm/gemini_provider.py api/tests/mocks.py api/tests/test_project_card_generation.py
git commit -m "feat(cards): generate_card 인터페이스 + OpenAI/Gemini/Mock 구현"
```

---

### Task 3: 파이프라인 분기 — 토글로 카드 저장 (`config.py` + `reviewer.py`)

토글이 켜지면 `_execute_review_pipeline`이 `generate_card`를 호출하고 `review_type="project_card"`로 저장한다. 꺼져 있으면 기존 13섹션 경로 그대로.

**Files:**
- Modify: `api/core/config.py` (토글 1개 추가)
- Modify: `api/pipeline/reviewer.py` (분기)
- Test: `api/tests/test_card_pipeline.py` (신규)

**Interfaces:**
- Consumes: `settings.beginner_card_mode_enabled` (신규), `llm.generate_card`, `parse_and_validate_card`
- Produces: `reviews.result` = `{"schema_version":1, "review_type":"project_card", "payload": <card>}` (토글 ON일 때)

- [ ] **Step 1: 실패하는 테스트 작성**

Create `api/tests/test_card_pipeline.py`:

```python
from unittest.mock import MagicMock

import pipeline.reviewer as reviewer
from tests.mocks import MockLLMProvider


class _Exec:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    """table(name).select/update/eq/...().execute().data 체인 흉내 + update 페이로드 캡처."""
    def __init__(self, name, data_map, captures):
        self._name = name
        self._data_map = data_map
        self._captures = captures

    def select(self, *a, **k):
        return self

    def update(self, payload):
        self._captures.append((self._name, payload))
        return self

    def insert(self, payload):
        self._captures.append((self._name, payload))
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return _Exec(self._data_map.get(self._name, []))


class _FakeClient:
    def __init__(self, data_map):
        self._data_map = data_map
        self.captures = []

    def table(self, name):
        return _FakeTable(name, self._data_map, self.captures)


def _data_map():
    return {
        "signals": [{
            "technology_name": "간단한 웹폼",
            "title": "간단한 웹폼 만들기",
            "summary": "요약",
            "signal_date": "2026-08-23",
        }],
        "signal_sources": [{"source_type": "github", "url": "https://x", "title": "예제"}],
        "projects": [{"user_id": "user-1"}],
        "user_profiles": [{"role": None, "tech_stack": [], "interests": [], "experience_level": None}],
    }


def _completed_result(client):
    for name, payload in client.captures:
        if name == "reviews" and payload.get("status") == "completed":
            return payload["result"]
    return None


def test_pipeline_stores_project_card_when_toggle_on(monkeypatch):
    monkeypatch.setattr(reviewer.settings, "beginner_card_mode_enabled", True)
    client = _FakeClient(_data_map())
    llm = MockLLMProvider()

    ok = reviewer._execute_review_pipeline(
        review_id="rev-1", signal_id="sig-1", project_id="proj-1",
        client=client, llm=llm,
    )

    assert ok is True
    result = _completed_result(client)
    assert result is not None
    assert result["review_type"] == "project_card"
    assert "milestones" in result["payload"]
    assert "skill_label" in result["payload"]


def test_pipeline_stores_research_when_toggle_off(monkeypatch):
    monkeypatch.setattr(reviewer.settings, "beginner_card_mode_enabled", False)
    client = _FakeClient(_data_map())
    llm = MockLLMProvider()  # 기본 generate() = 13섹션 응답

    ok = reviewer._execute_review_pipeline(
        review_id="rev-2", signal_id="sig-2", project_id="proj-2",
        client=client, llm=llm,
    )

    assert ok is True
    result = _completed_result(client)
    assert result is not None
    assert result["review_type"] == "research"
    assert "one_line_definition" in result["payload"]
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd api && pytest tests/test_card_pipeline.py -v`
Expected: FAIL — `AttributeError: ... has no attribute 'beginner_card_mode_enabled'` (config 토글 미존재) 또는 카드 테스트에서 `review_type == "research"`로 나와 assert 실패.

- [ ] **Step 3a: config 토글 추가** — `api/core/config.py`

`review_pregeneration_enabled` 정의(41행) 바로 아래에 추가:

```python
    # beginner_card_mode_enabled: 리뷰 생성 시 13섹션 Research Review 대신
    # 입문자용 7블록 프로젝트 카드를 생성/저장(review_type="project_card").
    # 기본 False = 안전 롤아웃(켜기 전까지 기존 경로 유지).
    beginner_card_mode_enabled: bool = False
```

- [ ] **Step 3b: 파이프라인 분기** — `api/pipeline/reviewer.py`

(1) import에 `settings`와 카드 검증 함수 추가. 상단 import 블록(7-10행)을 아래로 교체:

```python
from pipeline.llm.base import LLMProvider, LLMProviderError, ReviewContext, REQUIRED_SECTIONS
from pipeline.llm.factory import get_llm_provider
from pipeline.llm.prompts import parse_and_validate_card
from pipeline.logger import pipeline_log
from core.config import settings
from core.supabase import get_supabase
```

(2) `_execute_review_pipeline` 안에서 `review_type` 값을 토글로 정하고, context_snapshot·LLM 호출·result를 분기. 현재 62-118행(“# 4) context_snapshot 저장”부터 `result = {...}` 까지)을 아래로 교체:

```python
        # 4) context_snapshot 저장
        review_type_value = "project_card" if settings.beginner_card_mode_enabled else "research"
        context_snapshot = {
            "schema_version": 1,
            "review_type": review_type_value,
            "payload": {
                "signal": {
                    "id": signal_id,
                    "technology_name": signal_data["technology_name"],
                    "title": signal_data["title"],
                    "summary": signal_data.get("summary"),
                    "signal_date": str(signal_data["signal_date"]),
                },
                "sources": sources,
                "user_profile": {
                    "role": profile.get("role"),
                    "tech_stack": profile.get("tech_stack", []),
                    "interests": profile.get("interests", []),
                    "experience_level": profile.get("experience_level"),
                },
            },
        }
        client.table("reviews").update({
            "context_snapshot": context_snapshot,
        }).eq("id", review_id).execute()

        # 5) ReviewContext 빌드 + LLM 호출
        context = ReviewContext(
            technology_name=signal_data["technology_name"],
            signal_sources=sources,
            user_role=profile.get("role"),
            user_tech_stack=profile.get("tech_stack") or [],
            user_interests=profile.get("interests") or [],
            user_experience_level=profile.get("experience_level"),
        )

        # 6) 생성 + 검증 (토글에 따라 카드 / 13섹션)
        if settings.beginner_card_mode_enabled:
            llm_response = llm.generate_card(context)
            parse_and_validate_card(llm_response.content)
            payload = json.loads(llm_response.content)
        else:
            llm_response = llm.generate(context)
            payload = json.loads(llm_response.content)
            missing = [k for k in REQUIRED_SECTIONS if k not in payload]
            if missing:
                raise ValueError(f"LLM 응답에 필수 섹션 누락: {missing}")

            ltd = payload.get("learning_time_difficulty")
            if not isinstance(ltd, dict) or "estimated_hours" not in ltd or "difficulty" not in ltd:
                raise ValueError(f"learning_time_difficulty 하위 필드 누락 또는 형식 오류: {ltd}")

            honest_box = payload.get("honest_box")
            if not isinstance(honest_box, dict):
                payload["honest_box"] = {"content": str(honest_box) if honest_box is not None else "", "severity": "standard"}
            elif honest_box.get("severity") not in ("standard", "high"):
                payload["honest_box"]["severity"] = "standard"

        result = {
            "schema_version": 1,
            "review_type": review_type_value,
            "payload": payload,
        }
```

주의: 이 교체는 기존 “7) completed 상태 전이” 블록(121행 이후)은 그대로 둔다. `result` 변수명·구조가 동일하므로 이후 로직 무변경.

- [ ] **Step 4: 테스트 통과 확인 (전체 회귀 포함)**

Run: `cd api && pytest tests/test_card_pipeline.py -v`
Expected: PASS (2 passed)

Run(회귀): `cd api && pytest tests/ -q`
Expected: 전체 PASS. 특히 기존 `tests/test_reviews_trigger.py`, `tests/test_signal_builder_reviewer.py`가 토글 기본 False라 13섹션 경로로 그대로 통과.

- [ ] **Step 5: 커밋**

```bash
git add api/core/config.py api/pipeline/reviewer.py api/tests/test_card_pipeline.py
git commit -m "feat(cards): beginner_card_mode 토글로 파이프라인 카드 분기"
```

---

## 이 슬라이스가 끝나면

- 토글 `BEGINNER_CARD_MODE_ENABLED=true` 설정 시, 온디맨드 리뷰 트리거(`POST /api/v1/reviews/trigger`) → 백그라운드 파이프라인이 **7블록 프로젝트 카드**를 생성해 `reviews.result`에 `review_type="project_card"`로 저장한다.
- 아직 **웹 렌더링은 없음**(상세화면은 다음 슬라이스). 검증은 pytest + DB row로 확인.
- 카드는 **제네릭**(개인화 예시 슬롯은 다음 슬라이스에서 `example_prompt`를 온보딩 도메인으로 채움).

## 다음 슬라이스 후보 (이 계획 범위 밖)

- 웹: 7블록 상세화면 렌더(`research-review-content.tsx`/`review-sections.tsx` 대체 경로, `review_type` 분기).
- 개인화 예시(③): 온보딩 도메인 → `example_prompt` 렌더.
- 수집 표준 필터 + 주1회 배치 + 초기 시드.
