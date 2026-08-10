# 시그널 학습가치 필터 + 수집원 큐레이션 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 클러스터링 뒤·normalize 앞에 LLM 학습가치 분류 단계를 추가해 뉴스/오피니언 시그널을 드롭하고 깨끗한 기술명을 부여하며, 수집원을 도구/릴리스 중심으로 큐레이션한다.

**Architecture:** 새 `pipeline/curator.py` 단계가 클러스터(`cluster_key`) 단위로 LLM 배치 1회를 호출해 `{keep, category, name}`을 받고, drop + 라벨 교체 후 결과를 normalize로 넘긴다. LLM 부재/실패/개수불일치 시 전량 통과(safe-degrade). 수집원은 `registry.py`/`hackernews.py`에서 뉴스원 제거 + GitHub 릴리스 + HN 품질필터로 정리한다.

**Tech Stack:** Python 3.11, pytest, httpx, feedparser, OpenAI Responses API / Gemini, Supabase.

## Global Constraints

- 테스트 오프라인 원칙(절대): 실제 OpenAI/Gemini/네트워크 호출 금지. `llm`은 `MagicMock`, HTTP는 mock client로 대체.
- 예외 계약(AD-5): 어댑터/단계는 실패를 삼키지 않되, **파이프라인 단계(curator)는 safe-degrade로 전량 통과**하여 배치를 죽이지 않는다.
- LLM 응답은 항상 `LLMResponse(content=<JSON 문자열>)` 형태로 반환(기존 패턴 유지). 파싱/검증은 `pipeline/llm/prompts.py`에 둔다.
- 임베딩 차원은 1536 고정(기존). 이 작업은 임베딩을 추가하지 않는다.
- 새 provider 메서드는 abstract 추가이므로 **base + openai + gemini 세 곳 모두** 구현해야 인스턴스화가 깨지지 않는다.

---

## File Structure

- `api/pipeline/llm/prompts.py` (수정) — 학습가치 분류 프롬프트/빌더/검증기.
- `api/pipeline/llm/base.py` (수정) — 추상 메서드 `classify_learnability`.
- `api/pipeline/llm/openai_provider.py` (수정) — 구현.
- `api/pipeline/llm/gemini_provider.py` (수정) — 구현.
- `api/pipeline/curator.py` (신규) — `curate_learnability` 단계.
- `api/core/config.py` (수정) — `learnability_filter_enabled` 토글.
- `api/pipeline/orchestrator.py` (수정) — 단계 배선.
- `api/pipeline/collector/registry.py` (수정) — `Source` 확장 + `SOURCES` 큐레이션.
- `api/pipeline/collector/hackernews.py` (수정) — `min_points`/`tags` 지원.
- 테스트: `api/tests/test_learnability_prompts.py`, `api/tests/test_curator.py`, `api/tests/test_collector_curation.py` (신규).

**작업 디렉터리 주의:** 모든 명령은 `api/`에서 실행. 테스트: `cd api && python -m pytest ...`.

---

## Task 1: 학습가치 분류 LLM 메서드 (prompts + base + 두 provider)

**Files:**
- Modify: `api/pipeline/llm/prompts.py`
- Modify: `api/pipeline/llm/base.py`
- Modify: `api/pipeline/llm/openai_provider.py`
- Modify: `api/pipeline/llm/gemini_provider.py`
- Test: `api/tests/test_learnability_prompts.py`

**Interfaces:**
- Produces:
  - `prompts.LEARNABILITY_KEEP_CATEGORIES: list[str]` = `["new_tool","tool_update","technique_research","framework_library"]`
  - `prompts.LEARNABILITY_DROP_CATEGORIES: list[str]` = `["business_news","opinion","social_ethics","general_news"]`
  - `prompts.LEARNABILITY_CATEGORIES: list[str]` (합집합)
  - `prompts.build_learnability_user_input(topics: list[dict]) -> str` (topics 원소: `{"id": int, "label": str, "title": str}`)
  - `prompts.parse_and_validate_learnability(raw: str, expected_count: int) -> list[dict]` (결과 리스트 반환; 위반 시 `LLMProviderError`)
  - `LLMProvider.classify_learnability(self, topics: list[dict]) -> LLMResponse` (content = JSON `{"results":[{"id","keep","category","name"}]}`)

- [ ] **Step 1: 검증기 실패 테스트 작성**

Create `api/tests/test_learnability_prompts.py`:

```python
import json
import pytest

from pipeline.llm.base import LLMProviderError
from pipeline.llm import prompts


def _ok(results):
    return json.dumps({"results": results})


def test_parse_valid_returns_results():
    raw = _ok([
        {"id": 0, "keep": False, "category": "business_news", "name": "OpenAI 협력 사례"},
        {"id": 1, "keep": True, "category": "tool_update", "name": "LangGraph 0.3"},
    ])
    out = prompts.parse_and_validate_learnability(raw, expected_count=2)
    assert len(out) == 2
    assert out[1]["keep"] is True and out[1]["name"] == "LangGraph 0.3"


def test_count_mismatch_raises():
    raw = _ok([{"id": 0, "keep": True, "category": "new_tool", "name": "X"}])
    with pytest.raises(LLMProviderError):
        prompts.parse_and_validate_learnability(raw, expected_count=2)


def test_bad_category_raises():
    raw = _ok([{"id": 0, "keep": True, "category": "nonsense", "name": "X"}])
    with pytest.raises(LLMProviderError):
        prompts.parse_and_validate_learnability(raw, expected_count=1)


def test_missing_key_raises():
    raw = _ok([{"id": 0, "keep": True, "category": "new_tool"}])  # name 없음
    with pytest.raises(LLMProviderError):
        prompts.parse_and_validate_learnability(raw, expected_count=1)


def test_empty_name_raises():
    raw = _ok([{"id": 0, "keep": True, "category": "new_tool", "name": "  "}])
    with pytest.raises(LLMProviderError):
        prompts.parse_and_validate_learnability(raw, expected_count=1)


def test_user_input_includes_titles_and_ids():
    s = prompts.build_learnability_user_input([
        {"id": 0, "label": "General AI", "title": "OpenAI 협력 과정"},
    ])
    assert "OpenAI 협력 과정" in s and "0" in s
```

- [ ] **Step 2: 실패 확인**

Run: `cd api && python -m pytest tests/test_learnability_prompts.py -v`
Expected: FAIL — `AttributeError: module 'pipeline.llm.prompts' has no attribute 'parse_and_validate_learnability'`

- [ ] **Step 3: prompts.py에 프롬프트/빌더/검증기 추가**

`api/pipeline/llm/prompts.py` 하단(다른 상수/함수 곁)에 추가:

```python
LEARNABILITY_KEEP_CATEGORIES = ["new_tool", "tool_update", "technique_research", "framework_library"]
LEARNABILITY_DROP_CATEGORIES = ["business_news", "opinion", "social_ethics", "general_news"]
LEARNABILITY_CATEGORIES = LEARNABILITY_KEEP_CATEGORIES + LEARNABILITY_DROP_CATEGORIES

LEARNABILITY_CLASSIFY_PROMPT = """당신은 AI 기술 큐레이터입니다. 주어진 토픽들이 '학습가치'가 있는지 분류하세요.
판정 기준: "프론트엔드 개발자가 이번 주에 바로 배우거나 코드에 적용할 수 있는가?"

keep=true 카테고리: new_tool(신규 도구/서비스), tool_update(도구 업데이트/릴리스),
technique_research(바로 적용 가능한 기법/연구), framework_library(프레임워크/라이브러리).
keep=false 카테고리: business_news(비즈니스/제휴/투자), opinion(오피니언/인터뷰),
social_ethics(사회·윤리·규제 논쟁), general_news(그 외 잡뉴스).

애매하면 보수적으로 keep=true 로 둡니다(과도한 삭제 금지).
각 토픽에 대해 keep에 맞는 category를 고르고, 사람이 읽기 좋은 짧은 기술명 name(한국어, 40자 이내)을 생성하세요.

반드시 아래 JSON 객체만 반환하세요(마크다운 없이). results 배열은 입력 토픽과 같은 개수·같은 id를 가져야 합니다:
{"results": [{"id": 0, "keep": true, "category": "tool_update", "name": "..."}]}"""

_LEARNABILITY_KEYS = {"id", "keep", "category", "name"}


def build_learnability_user_input(topics: list[dict]) -> str:
    lines = [
        f'- id={t.get("id")} | label={t.get("label", "")} | title={t.get("title", "")}'
        for t in topics
    ]
    return "다음 토픽들을 분류하세요:\n" + "\n".join(lines) + "\n\nJSON 객체로 반환하세요."


def parse_and_validate_learnability(raw: str, expected_count: int) -> list[dict]:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise LLMProviderError(f"LLM 응답이 JSON 객체가 아님: {type(parsed).__name__}")
    results = parsed.get("results")
    if not isinstance(results, list) or len(results) != expected_count:
        raise LLMProviderError(f"results 개수 불일치: 기대 {expected_count}, 실제 {results!r}")
    for r in results:
        if not isinstance(r, dict) or not _LEARNABILITY_KEYS.issubset(r.keys()):
            raise LLMProviderError(f"result 항목 키 누락: {r}")
        if r["category"] not in LEARNABILITY_CATEGORIES:
            raise LLMProviderError(f"category 허용 목록 밖: {r['category']}")
        if not isinstance(r["name"], str) or not r["name"].strip():
            raise LLMProviderError(f"name 비어있음: {r!r}")
        if not isinstance(r["keep"], bool):
            raise LLMProviderError(f"keep 이 bool 아님: {r!r}")
    return results
```

- [ ] **Step 4: 검증기 테스트 통과 확인**

Run: `cd api && python -m pytest tests/test_learnability_prompts.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: base 추상 메서드 + 두 provider 구현 추가**

`api/pipeline/llm/base.py`의 `LLMProvider`에 추가(다른 abstractmethod 곁, `embed_text` 위):

```python
    @abstractmethod
    def classify_learnability(self, topics: list[dict]) -> LLMResponse:
        """토픽 배치를 학습가치로 분류. content = JSON {"results":[{"id","keep","category","name"}]}."""
        ...
```

`api/pipeline/llm/openai_provider.py`의 `OpenAIProvider`에 추가(`embed_text` 위):

```python
    def classify_learnability(self, topics: list[dict]) -> LLMResponse:
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=prompts.LEARNABILITY_CLASSIFY_PROMPT,
                input=prompts.build_learnability_user_input(topics),
                text={"format": {"type": "json_object"}},
            )
            raw = response.output_text
            prompts.parse_and_validate_learnability(raw, expected_count=len(topics))
            return LLMResponse(content=raw, model=self._model)
        except LLMProviderError:
            raise
        except OpenAIError as e:
            raise LLMProviderError(str(e)) from e
        except Exception as e:
            raise LLMProviderError(str(e)) from e
```

`api/pipeline/llm/gemini_provider.py`의 `GeminiProvider`에 추가(`embed_text` 위):

```python
    def classify_learnability(self, topics: list[dict]) -> LLMResponse:
        raw = self._generate(
            prompts.LEARNABILITY_CLASSIFY_PROMPT,
            prompts.build_learnability_user_input(topics), as_json=True,
        )
        prompts.parse_and_validate_learnability(raw, expected_count=len(topics))
        return LLMResponse(content=raw, model=self._model)
```

- [ ] **Step 6: provider 인스턴스화 회귀 확인**

기존 provider 테스트가 abstract 추가로 깨지지 않는지 확인.
Run: `cd api && python -m pytest tests/test_gemini_provider.py -v`
Expected: PASS (기존 그대로)

- [ ] **Step 7: 커밋**

```bash
cd api && git add pipeline/llm/prompts.py pipeline/llm/base.py pipeline/llm/openai_provider.py pipeline/llm/gemini_provider.py tests/test_learnability_prompts.py
git commit -m "feat(llm): classify_learnability 배치 분류 메서드 + 프롬프트/검증기

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: curator 단계 + config 토글 + orchestrator 배선

**Files:**
- Create: `api/pipeline/curator.py`
- Modify: `api/core/config.py`
- Modify: `api/pipeline/orchestrator.py`
- Test: `api/tests/test_curator.py`

**Interfaces:**
- Consumes: `prompts.parse_and_validate_learnability`, `LLMProvider.classify_learnability`, `RawArticle`(필드 `technology_name`, `cluster_key`), `settings.learnability_filter_enabled`.
- Produces: `curator.curate_learnability(articles: list[RawArticle], llm: LLMProvider | None, brief_date: str = "") -> list[RawArticle]`

**설계 메모(curator 규칙):**
- 그룹핑 키: `cluster_key`. `cluster_key is None`(pass-through)인 기사는 각자 개별 토픽으로 취급(키=`f"__none__:{url}"`), 원본 라벨 유지.
- 각 토픽 대표 = 그룹 첫 기사. 대표의 `technology_name`(label)·`title`을 분류 입력으로.
- keep=false → 그룹 전체 드롭. keep=true → 그룹 전원 `technology_name = name`.
- 결정론 정렬: 입력을 `cluster_key or ""` + `url`로 정렬해 토픽 id가 안정적이게.
- safe-degrade: `not articles` / 토글 off / `llm is None` / 호출·파싱 예외 → 입력 그대로 반환.

- [ ] **Step 1: 실패 테스트 작성**

Create `api/tests/test_curator.py`:

```python
import json
from unittest.mock import MagicMock, patch

from pipeline.curator import curate_learnability
from pipeline.llm.base import LLMProviderError, LLMResponse
from pipeline.models import RawArticle


def _llm(results):
    llm = MagicMock()
    llm.classify_learnability.return_value = LLMResponse(
        content=json.dumps({"results": results})
    )
    return llm


def _art(label, title, url, ck):
    return RawArticle(label, title, url, "hn", cluster_key=ck)


def test_drops_non_learnable_and_renames_kept():
    articles = [
        _art("General AI", "OpenAI 353,000명 협력", "u0", "ck0"),
        _art("LangGraph", "LangGraph 0.3 릴리스", "u1", "ck1"),
    ]
    # 정렬(ck0<ck1) 후 id 0=OpenAI, 1=LangGraph
    llm = _llm([
        {"id": 0, "keep": False, "category": "business_news", "name": "OpenAI 협력"},
        {"id": 1, "keep": True, "category": "tool_update", "name": "LangGraph 0.3"},
    ])
    with patch("pipeline.curator.settings") as s:
        s.learnability_filter_enabled = True
        out = curate_learnability(articles, llm, brief_date="d")
    assert len(out) == 1
    assert out[0].url == "u1" and out[0].technology_name == "LangGraph 0.3"


def test_cluster_members_share_new_name():
    articles = [
        _art("General AI", "Claude MCP 커넥터", "u0", "ck"),
        _art("General AI", "HN: Claude MCP 토론", "u1", "ck"),
    ]
    llm = _llm([{"id": 0, "keep": True, "category": "new_tool", "name": "Claude MCP"}])
    with patch("pipeline.curator.settings") as s:
        s.learnability_filter_enabled = True
        out = curate_learnability(articles, llm, brief_date="d")
    assert len(out) == 2
    assert {a.technology_name for a in out} == {"Claude MCP"}


def test_safe_degrade_when_disabled():
    articles = [_art("X", "t", "u", "ck")]
    with patch("pipeline.curator.settings") as s:
        s.learnability_filter_enabled = False
        out = curate_learnability(articles, MagicMock(), brief_date="d")
    assert out == articles


def test_safe_degrade_when_llm_none():
    articles = [_art("X", "t", "u", "ck")]
    with patch("pipeline.curator.settings") as s:
        s.learnability_filter_enabled = True
        out = curate_learnability(articles, None, brief_date="d")
    assert out == articles


def test_safe_degrade_on_llm_error():
    articles = [_art("X", "t", "u", "ck")]
    llm = MagicMock()
    llm.classify_learnability.side_effect = LLMProviderError("boom")
    with patch("pipeline.curator.settings") as s:
        s.learnability_filter_enabled = True
        out = curate_learnability(articles, llm, brief_date="d")
    assert out == articles


def test_dropped_topic_is_logged():
    articles = [_art("General AI", "AI 아티스트 논쟁", "u0", "ck0")]
    llm = _llm([{"id": 0, "keep": False, "category": "social_ethics", "name": "논쟁"}])
    with patch("pipeline.curator.settings") as s, \
         patch("pipeline.curator.pipeline_log") as log:
        s.learnability_filter_enabled = True
        curate_learnability(articles, llm, brief_date="d")
    events = [c.kwargs.get("event") for c in log.call_args_list]
    assert "topic_dropped" in events
```

- [ ] **Step 2: 실패 확인**

Run: `cd api && python -m pytest tests/test_curator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.curator'`

- [ ] **Step 3: config 토글 추가**

`api/core/config.py`에서 `clustering_enabled` 선언 곁에 추가:

```python
    # learnability_filter_enabled: 학습가치 필터 on/off (긴급 차단 토글). 끄면 전량 통과.
    learnability_filter_enabled: bool = True
```

- [ ] **Step 4: curator.py 구현**

Create `api/pipeline/curator.py`:

```python
"""학습가치 분류 단계.

clustering 뒤·normalize 앞. cluster_key 단위 토픽으로 묶어 LLM 배치 1회 호출로
keep/drop + 깨끗한 이름을 받아, 뉴스/오피니언 토픽을 드롭하고 keep 토픽의 라벨을 교체한다.

safe-degrade(AD-5): 토글 off / llm 부재 / 호출·파싱·개수불일치 → 입력 전량 통과.
"""
from __future__ import annotations

import json
from dataclasses import replace

from core.config import settings
from pipeline.llm.base import LLMProvider
from pipeline.logger import pipeline_log
from pipeline.models import RawArticle

_STAGE = "curator"


def _group(articles: list[RawArticle]) -> list[tuple[str, list[RawArticle]]]:
    """cluster_key 단위 그룹핑. None 키는 url별 개별 토픽으로. 결정론 정렬."""
    ordered = sorted(articles, key=lambda a: ((a.cluster_key or ""), a.url))
    groups: dict[str, list[RawArticle]] = {}
    order: list[str] = []
    for a in ordered:
        key = a.cluster_key if a.cluster_key is not None else f"__none__:{a.url}"
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(a)
    return [(k, groups[k]) for k in order]


def curate_learnability(
    articles: list[RawArticle], llm: LLMProvider | None, brief_date: str = ""
) -> list[RawArticle]:
    if not articles or not settings.learnability_filter_enabled or llm is None:
        reason = ("empty_input" if not articles
                  else "disabled" if not settings.learnability_filter_enabled
                  else "no_llm")
        pipeline_log(stage=_STAGE, brief_date=brief_date, user_count=0,
                     event="curation_skipped", reason=reason, input=len(articles))
        return list(articles)

    grouped = _group(articles)
    topics = [
        {"id": i, "label": members[0].technology_name, "title": members[0].title}
        for i, (_key, members) in enumerate(grouped)
    ]

    try:
        resp = llm.classify_learnability(topics)
        results = json.loads(resp.content)["results"]
        if len(results) != len(topics):
            raise ValueError(f"results 개수 불일치: {len(results)} != {len(topics)}")
        by_id = {int(r["id"]): r for r in results}
    except Exception as e:
        pipeline_log(stage=_STAGE, brief_date=brief_date, user_count=0, level="warning",
                     event="curation_degraded", error=str(e)[:200], input=len(articles))
        return list(articles)

    out: list[RawArticle] = []
    dropped = 0
    for i, (_key, members) in enumerate(grouped):
        r = by_id.get(i)
        if r is None or not r.get("keep", True):
            dropped += 1
            pipeline_log(stage=_STAGE, brief_date=brief_date, user_count=0,
                         event="topic_dropped",
                         category=(r or {}).get("category"),
                         title=members[0].title, label=members[0].technology_name)
            continue
        name = r["name"]
        out.extend(replace(a, technology_name=name) for a in members)

    pipeline_log(stage=_STAGE, brief_date=brief_date, user_count=0,
                 event="curation_done", input=len(articles),
                 topics=len(topics), dropped=dropped, kept_articles=len(out))
    return out
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd api && python -m pytest tests/test_curator.py -v`
Expected: PASS (6 passed)

- [ ] **Step 6: orchestrator 배선**

`api/pipeline/orchestrator.py` 상단 import에 추가:

```python
from pipeline.curator import curate_learnability
```

`run_daily_pipeline`의 `cluster_and_filter` 호출 직후·`normalize` 직전에 삽입(현재 파일 58~63행 사이):

```python
        # 2.5 Curate — 학습가치 분류: 뉴스/오피니언 드롭 + 깨끗한 이름. safe-degrade(AD-5).
        articles = curate_learnability(articles, llm, brief_date=brief_date)
        pipeline_log(stage="orchestrator", brief_date=brief_date, user_count=0,
                     event="curate_done", article_count=len(articles))
```

- [ ] **Step 7: 전체 파이프라인 테스트 회귀 확인**

Run: `cd api && python -m pytest tests/ -q`
Expected: PASS (기존 + 신규 모두 통과)

- [ ] **Step 8: 커밋**

```bash
cd api && git add pipeline/curator.py core/config.py pipeline/orchestrator.py tests/test_curator.py
git commit -m "feat(pipeline): 학습가치 필터(curate_learnability) 단계 + 오케스트레이터 배선 + 토글

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: 수집원 큐레이션 (Source 확장 + HN 품질필터 + registry)

**Files:**
- Modify: `api/pipeline/collector/hackernews.py`
- Modify: `api/pipeline/collector/registry.py`
- Test: `api/tests/test_collector_curation.py`

**Interfaces:**
- Consumes: `RawArticle`, `HackerNewsCollector`, `Source`.
- Produces:
  - `HackerNewsCollector(..., min_points: int = 0, tags: tuple[str, ...] = ())` — 점수 미달 hit 제거 + Algolia `numericFilters`/`tags` 반영.
  - `Source(..., min_points: int = 0, tags: tuple[str, ...] = ())` 필드 추가; `_build_one`이 HN에 전달.

- [ ] **Step 1: 실패 테스트 작성**

Create `api/tests/test_collector_curation.py`:

```python
from unittest.mock import MagicMock

from pipeline.collector.hackernews import HackerNewsCollector
from pipeline.collector import registry


def _resp(hits):
    r = MagicMock()
    r.json.return_value = {"hits": hits}
    r.raise_for_status.return_value = None
    return r


def test_min_points_filters_low_score_hits():
    client = MagicMock()
    client.get.return_value = _resp([
        {"title": "big tool launch", "url": "https://a", "points": 120, "objectID": "1"},
        {"title": "low signal news", "url": "https://b", "points": 3, "objectID": "2"},
    ])
    c = HackerNewsCollector(["LLM"], client, min_points=50, per_query=10)
    out = c.collect()
    urls = {a.url for a in out}
    assert "https://a" in urls and "https://b" not in urls


def test_min_points_sent_as_numeric_filter():
    client = MagicMock()
    client.get.return_value = _resp([])
    HackerNewsCollector(["LLM"], client, min_points=50).collect()
    params = client.get.call_args.kwargs["params"]
    assert params.get("numericFilters") == "points>=50"


def test_tags_included_in_params():
    client = MagicMock()
    client.get.return_value = _resp([])
    HackerNewsCollector([""], client, tags=("show_hn",)).collect()
    params = client.get.call_args.kwargs["params"]
    assert "show_hn" in params["tags"]


def test_registry_has_no_verge_and_has_github_releases():
    names = [s.name for s in registry.SOURCES]
    assert "The Verge AI" not in names
    kinds_urls = [(s.kind, s.url) for s in registry.SOURCES]
    assert ("github", "vllm-project/vllm") in kinds_urls
    hn = [s for s in registry.SOURCES if s.kind == "hn"]
    assert any(s.min_points >= 50 for s in hn)
```

- [ ] **Step 2: 실패 확인**

Run: `cd api && python -m pytest tests/test_collector_curation.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'min_points'`

- [ ] **Step 3: HackerNewsCollector에 min_points/tags 추가**

`api/pipeline/collector/hackernews.py` `__init__` 시그니처에 파라미터 추가(`per_query` 뒤):

```python
        min_points: int = 0,
        tags: tuple[str, ...] = (),
```

`__init__` 본문에 저장:

```python
        self._min_points = min_points
        self._tags = tags
```

`collect()`의 `params` 구성을 태그·numericFilters 반영으로 교체(기존 `self._client.get(...)` 블록):

```python
                tag_expr = ",".join(("story", *self._tags))
                params = {"query": query, "tags": tag_expr, "hitsPerPage": self._per_query}
                if self._min_points > 0:
                    params["numericFilters"] = f"points>={self._min_points}"
                r = self._client.get(_HN_API, params=params)
```

`for hit in hits:` 루프 안, `title` 추출 직후에 점수 하한 가드 추가(서버 필터 누락 대비 이중 방어):

```python
                if self._min_points > 0 and _hit_popularity(hit) < self._min_points:
                    continue
```

- [ ] **Step 4: Source 확장 + registry 큐레이션**

`api/pipeline/collector/registry.py`의 `Source` dataclass에 필드 추가(`enabled` 위):

```python
    min_points: int = 0
    tags: tuple[str, ...] = field(default_factory=tuple)
```

`SOURCES` 리스트를 아래로 교체:

```python
SOURCES: list[Source] = [
    Source("Hugging Face", "rss", "official_blog", url="https://huggingface.co/blog/feed.xml"),
    Source("Simon Willison", "rss", "official_blog", url="https://simonwillison.net/atom/everything/"),
    Source("Google AI", "rss", "official_blog", url="https://blog.google/technology/ai/rss/"),
    Source("OpenAI Blog", "rss", "official_blog", url="https://openai.com/blog/rss.xml"),
    Source("langgraph releases", "github", "github", url="langchain-ai/langgraph"),
    Source("langchain releases", "github", "github", url="langchain-ai/langchain"),
    Source("llama_index releases", "github", "github", url="run-llama/llama_index"),
    Source("vllm releases", "github", "github", url="vllm-project/vllm"),
    Source("ollama releases", "github", "github", url="ollama/ollama"),
    Source("llama.cpp releases", "github", "github", url="ggml-org/llama.cpp"),
    Source("HackerNews", "hn", "hn", queries=("LLM", "OpenAI", "Anthropic Claude", "RAG"), min_points=50),
    Source("Show HN AI", "hn", "hn", queries=("AI", "LLM"), tags=("show_hn",), min_points=10),
]
```

`_build_one`의 HN 분기를 min_points/tags 전달로 교체:

```python
    if source.kind == "hn":
        return HackerNewsCollector(
            source.queries, client, name=source.name,
            min_points=source.min_points, tags=source.tags,
        )
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd api && python -m pytest tests/test_collector_curation.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: 수집기 회귀 확인**

Run: `cd api && python -m pytest tests/test_collector_real.py -q`
Expected: PASS (기존 그대로; 시그니처 변경이 기본값 호환이라 깨지지 않음)

- [ ] **Step 7: 커밋**

```bash
cd api && git add pipeline/collector/hackernews.py pipeline/collector/registry.py tests/test_collector_curation.py
git commit -m "feat(collector): 수집원 큐레이션(The Verge 제거·GitHub 릴리스·HN 품질필터)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Post-Implementation: 피드 생존 확인 (수동, 1회)

신규 RSS/GitHub 피드가 실제로 살아있는지 로컬 1회 실행으로 확인:

```bash
cd api && python -c "from pipeline.collector.aggregator import run_collectors; import json; \
arts = run_collectors(brief_date='verify'); \
print('total', len(arts)); \
print('verge', sum('theverge' in a.url for a in arts))"
```

Expected: `verge 0`, total > 0. 로그에서 `source_failed`가 뜨는 피드는 `registry.py`에서
`enabled=False`로 끈다(특히 `OpenAI Blog` URL은 변동 이력 있음 — 실패 시 비활성화).

---

## Self-Review (작성자 점검 완료)

- **스펙 커버리지:** #1 수집원(Task 3), #2 학습가치 필터(Task 1·2), #3 네이밍(Task 1·2 name 교체) 모두 태스크 존재. safe-degrade·토글·로깅·테스트 전략 반영.
- **플레이스홀더:** 없음(모든 스텝에 실제 코드/명령/기대출력).
- **타입 일관성:** `classify_learnability(topics)->LLMResponse`, `parse_and_validate_learnability(raw, expected_count)->list[dict]`, `curate_learnability(articles, llm, brief_date)->list[RawArticle]`, `Source(min_points, tags)` — 태스크 간 시그니처 일치.
