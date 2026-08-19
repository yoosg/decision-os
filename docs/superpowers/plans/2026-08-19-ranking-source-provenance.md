# 소스 프로비넌스 랭킹 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 큐레이션된 도구-릴리스 피드(source_type=github)에서 온 시그널을 base에 전역 가점(+0.3)해 일반 블로그/HN 위로 올린다.

**Architecture:** `recommender.py`에 `_source_boost(signal)`를 추가하고 `_score_signals` base 루프에서 `_clamp(base + _lexical_boost(...) + _source_boost(...))`로 결합한다. 시그널이 소스를 들고 오도록 `create_daily_brief_for_user`의 시그널 fetch select에 중첩 `signal_sources(source_type)`를 추가한다. 언어 무관(소스 메타 판정), 전역(모든 유저 공통).

**Tech Stack:** Python(순수 함수), pytest, Supabase PostgREST 중첩 select.

## Global Constraints

- 부스트 상수: `_TOOL_RELEASE_SOURCE_TYPES = {"github"}`, `_TOOL_RELEASE_BOOST = 0.3`.
- 1차 하이브리드 렉시컬 가점(`_lexical_boost`)은 **유지**(무해). 소스 부스트를 그 위에 더한다.
- 임베딩 텍스트·결합 가중치(`_W_RELEVANCE=0.70` 등)·MMR(`_MMR_LAMBDA=0.7`)·`_SOURCE_AUTHORITY` 등급·`_W_AUTHORITY`·프론트/DB 스키마: **변경 금지**.
- `_clamp`으로 base [0.1, 1.0] 유지.
- `signal_sources` 없음/빈/None → boost 0(safe).
- 백엔드 테스트: `api/` 에서 `.venv/bin/python -m pytest`.
- 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

### Task 1: 소스 프로비넌스 부스트 + `_score_signals` 결합 + 시그널 fetch

**Files:**
- Modify: `api/pipeline/recommender.py` (상수 2개, `_source_boost`, `_score_signals` base 루프, `create_daily_brief_for_user` 시그널 select line ~522)
- Test: `api/tests/test_recommender_pipeline.py`

**Interfaces:**
- Consumes: 기존 `_clamp`, `_lexical_boost`, `_score_signals`, `create_daily_brief_for_user`.
- Produces:
  - `_source_boost(signal: dict) -> float` — 시그널 `signal_sources` 중 `source_type`이 `_TOOL_RELEASE_SOURCE_TYPES`에 있으면 `_TOOL_RELEASE_BOOST`, 아니면 0.0.
  - `_score_signals`의 base_scores에 `_source_boost`가 더해진 뒤 `_clamp`됨(시그니처·반환 불변).
  - `create_daily_brief_for_user` 시그널 fetch가 `signal_sources(source_type)`를 포함해 각 시그널 dict에 `signal_sources` 리스트가 실림.

- [ ] **Step 1: `_source_boost` 단위 테스트 작성 (실패 확인용)**

`api/tests/test_recommender_pipeline.py` 끝에 추가:

```python
# ─── _source_boost (전역 도구-릴리스 프로비넌스 가점) ──────────────────────────────

def test_source_boost_github_release():
    from pipeline.recommender import _source_boost, _TOOL_RELEASE_BOOST
    sig = {"signal_sources": [{"source_type": "github"}]}
    assert _source_boost(sig) == _TOOL_RELEASE_BOOST


def test_source_boost_non_tool_sources_zero():
    from pipeline.recommender import _source_boost
    sig = {"signal_sources": [{"source_type": "hn"}, {"source_type": "official_blog"}]}
    assert _source_boost(sig) == 0.0


def test_source_boost_missing_sources_zero():
    from pipeline.recommender import _source_boost
    assert _source_boost({}) == 0.0
    assert _source_boost({"signal_sources": None}) == 0.0
    assert _source_boost({"signal_sources": []}) == 0.0


def test_source_boost_mixed_with_github_boosts():
    from pipeline.recommender import _source_boost, _TOOL_RELEASE_BOOST
    sig = {"signal_sources": [{"source_type": "hn"}, {"source_type": "github"}]}
    assert _source_boost(sig) == _TOOL_RELEASE_BOOST
```

- [ ] **Step 2: 실패 확인**

Run: `cd api && .venv/bin/python -m pytest tests/test_recommender_pipeline.py -k source_boost -v`
Expected: FAIL — `ImportError: cannot import name '_source_boost'`(함수·상수 미구현).

- [ ] **Step 3: 상수 + `_source_boost` 구현**

`api/pipeline/recommender.py`의 하이브리드 렉시컬 상수 블록(`_LEXICAL_BOOST_CAP = 0.6` 아래)에 추가:

```python
# ── 전역 도구-릴리스 프로비넌스 가점: 큐레이션된 GitHub 릴리스 피드 시그널을 상위로 ──────
# 언어 무관(소스 메타로 판정). 일반 블로그/HN 잡담보다 "진짜 도구 릴리스"를 우선.
_TOOL_RELEASE_SOURCE_TYPES = {"github"}
_TOOL_RELEASE_BOOST = 0.3
```

`_lexical_boost` 함수 아래에 추가:

```python
def _source_boost(signal: dict) -> float:
    """시그널의 소스 중 하나라도 큐레이션 도구-릴리스 피드(_TOOL_RELEASE_SOURCE_TYPES)면 가점.
    signal_sources는 [{"source_type": ...}] 중첩 리스트(없으면 0.0)."""
    for src in (signal.get("signal_sources") or []):
        if (src or {}).get("source_type") in _TOOL_RELEASE_SOURCE_TYPES:
            return _TOOL_RELEASE_BOOST
    return 0.0
```

- [ ] **Step 4: 단위 테스트 통과 확인**

Run: `cd api && .venv/bin/python -m pytest tests/test_recommender_pipeline.py -k source_boost -v`
Expected: 4개 PASS.

- [ ] **Step 5: `_score_signals` 결합 테스트 작성 (실패 확인용)**

같은 파일에 추가:

```python
def test_score_signals_applies_source_boost(monkeypatch):
    """base 평탄화(0.1)·빈 프로필(렉시컬 0)에서 github 소스 시그널이 source_boost로 1위가 된다.
    match id를 정렬상 뒤(sig-b)로 둬 RED가 확실히 실패하게 설계."""
    import pipeline.recommender as rec
    monkeypatch.setattr(rec, "compute_relevance_score", lambda sig, prof: 0.1)
    signals = [
        {"id": "sig-a", "technology_name": "Mermaid", "title": "", "summary": "diagrams",
         "popularity": 0, "source_authority": 2, "published_at": None,
         "signal_sources": [{"source_type": "hn"}]},
        {"id": "sig-b", "technology_name": "LangGraph release", "title": "", "summary": "x",
         "popularity": 0, "source_authority": 2, "published_at": None,
         "signal_sources": [{"source_type": "github"}]},
    ]
    ordered, _variant = rec._score_signals(
        signals, {}, "u1", MagicMock(), "2026-08-19", llm=None, signal_embeddings=None
    )
    assert ordered[0][0] == "sig-b"
```

두 시그널의 `source_authority`를 **둘 다 2**로 맞춘 이유: authority 항이 차이를 만들지 않게 해
**오직 `_source_boost`만** 랭킹 차이의 원인이 되도록 격리(RED 신뢰성). base 평탄화(0.1)·빈 프로필
(렉시컬 0)·published_at=None·popularity=0으로 나머지 항도 동일 → source_boost 없으면 tie.

- [ ] **Step 6: 실패 확인**

Run: `cd api && .venv/bin/python -m pytest tests/test_recommender_pipeline.py::test_score_signals_applies_source_boost -v`
Expected: FAIL — source_boost 미결합 시 sig-a/sig-b combined 완전 동일 → `sorted(key=(-combined, signal_id))` tie-break으로 `sig-a`가 1위 → `ordered[0][0]`이 "sig-b"가 아니어서 assert 실패.

- [ ] **Step 7: `_score_signals` base 루프에 source_boost 결합**

`api/pipeline/recommender.py`의 base 루프 마지막 줄(현재):

```python
        base_scores[sid] = _clamp(base + _lexical_boost(sig, user_profile))
```

를 아래로 교체:

```python
        base_scores[sid] = _clamp(base + _lexical_boost(sig, user_profile) + _source_boost(sig))
```

- [ ] **Step 8: 결합 테스트 통과 확인**

Run: `cd api && .venv/bin/python -m pytest tests/test_recommender_pipeline.py::test_score_signals_applies_source_boost -v`
Expected: PASS.

- [ ] **Step 9: 시그널 fetch select에 소스 포함**

`api/pipeline/recommender.py`의 `create_daily_brief_for_user` 시그널 조회(현재 select):

```python
            .select("id,technology_name,title,summary,published_at,popularity,source_authority")
```

를 아래로 교체(도구 부스트가 실데이터에서 작동하도록 소스를 실어옴):

```python
            .select("id,technology_name,title,summary,published_at,popularity,source_authority,signal_sources(source_type)")
```

- [ ] **Step 10: 파일 전체 + 전체 스위트 회귀 확인**

Run: `cd api && .venv/bin/python -m pytest tests/test_recommender_pipeline.py -q`
Expected: 신규 5개 포함 전부 PASS(기존 픽스처는 signal_sources 없음 → source_boost 0 → 회귀 없음).

Run: `cd api && .venv/bin/python -m pytest -q`
Expected: 전체 PASS.

- [ ] **Step 11: 커밋**

```bash
git add api/pipeline/recommender.py api/tests/test_recommender_pipeline.py
git commit -m "feat(recommender): 소스 프로비넌스 가점 — 도구 릴리스(github) 전역 우선

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 배포 후 정성 검증 (수동, 실행 아님)

- test-history 브리핑 온디맨드 재생성(세션쿠키 `sb-<ref>-auth-token` 토큰 재조립 →
  `POST decision-os-production.up.railway.app/api/v1/daily-briefs/trigger`) 후,
  `daily_brief_signals`에서 github-소스(LangGraph 등)가 hn-소스(픽션/Mermaid)보다 상위 position인지 확인.
- 과하면 `_TOOL_RELEASE_BOOST` 조정, 부족하면 `_TOOL_RELEASE_SOURCE_TYPES` 확장 검토.
