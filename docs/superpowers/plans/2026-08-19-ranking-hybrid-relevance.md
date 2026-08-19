# 랭킹 하이브리드 관련도 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recommender 관련도(base)에 명시적 스택/관심 렉시컬 가점을 더해(임베딩 코사인 유지) 유저가 쓰는 도구(LangChain/LangGraph 등) 소식을 브리핑 상위로 올린다.

**Architecture:** `pipeline/recommender.py`에 순수 함수 `_lexical_boost(signal, user_profile)`를 추가하고, `_score_signals`의 base 산출 루프에서 `base_scores[sid] = _clamp(base + _lexical_boost(...))`로 적용한다. 매칭은 토큰 집합 멤버십(단어 경계)이라 "go→google" substring 오매칭이 없다. 임베딩 텍스트·결합 가중치·MMR·프론트/DB는 불변.

**Tech Stack:** Python(순수 함수, `re` 토큰화), pytest.

## Global Constraints

- 임베딩 대상 텍스트(summary)·결합 가중치(`_W_RELEVANCE=0.70` 등)·`_MMR_LAMBDA=0.7`·프론트/DB 스키마는 **변경 금지**.
- 가점 상수: `_STACK_BOOST=0.3`, `_INTEREST_BOOST=0.2`, `_LEXICAL_BOOST_CAP=0.6`.
- 매칭은 **토큰 집합 부분집합**(항목의 모든 토큰이 시그널 텍스트 토큰에 존재)이어야 함 — substring 금지("go"가 "google"에 안 걸림).
- `_clamp`으로 [0.1, 1.0] 불변식 유지.
- 백엔드 테스트: `api/` 에서 `.venv/bin/python -m pytest`.
- 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

### Task 1: 렉시컬 가점 헬퍼 + `_score_signals` 결합

**Files:**
- Modify: `api/pipeline/recommender.py` (`import re`, 상수 3개, `_lexical_boost`, `_score_signals` base 루프 line ~349-359)
- Test: `api/tests/test_recommender_pipeline.py`

**Interfaces:**
- Consumes: 기존 `_clamp`, `compute_relevance_score`, `compute_relevance_score_v2`, `_score_signals`.
- Produces:
  - `_lexical_boost(signal: dict, user_profile: dict) -> float` — 시그널 `technology_name+title+summary` 토큰에 유저 `tech_stack`/`interests` 항목(토큰화)이 부분집합으로 포함되면 스택당 `_STACK_BOOST`·관심당 `_INTEREST_BOOST` 합산(상한 `_LEXICAL_BOOST_CAP`), 무매칭 0.0.
  - `_score_signals`의 base_scores에 위 가점이 더해진 뒤 `_clamp`됨(반환 타입·시그니처 불변).

- [ ] **Step 1: `_lexical_boost` 단위 테스트 작성 (실패 확인용)**

`api/tests/test_recommender_pipeline.py` 끝에 추가:

```python
# ─── _lexical_boost (하이브리드 관련도 가점) ──────────────────────────────────────

def test_lexical_boost_stack_match_beats_no_match():
    from pipeline.recommender import _lexical_boost
    sig_match = {"technology_name": "LangGraph 1.2", "title": "", "summary": "release"}
    sig_none = {"technology_name": "Mermaid editor", "title": "", "summary": "diagrams"}
    user = {"tech_stack": ["LangGraph"], "interests": []}
    assert _lexical_boost(sig_match, user) > _lexical_boost(sig_none, user)
    assert _lexical_boost(sig_none, user) == 0.0


def test_lexical_boost_go_does_not_match_google():
    from pipeline.recommender import _lexical_boost
    sig = {"technology_name": "Google AI", "title": "", "summary": "google blog"}
    user = {"tech_stack": ["Go"], "interests": []}
    assert _lexical_boost(sig, user) == 0.0


def test_lexical_boost_interest_match():
    from pipeline.recommender import _lexical_boost, _INTEREST_BOOST
    sig = {"technology_name": "RAG pipeline", "title": "", "summary": "retrieval"}
    user = {"tech_stack": [], "interests": ["RAG"]}
    assert _lexical_boost(sig, user) == _INTEREST_BOOST


def test_lexical_boost_multitoken_requires_all_tokens():
    from pipeline.recommender import _lexical_boost
    sig_partial = {"technology_name": "llama release", "title": "", "summary": ""}
    sig_full = {"technology_name": "llama index update", "title": "", "summary": ""}
    user = {"tech_stack": ["llama index"], "interests": []}
    assert _lexical_boost(sig_partial, user) == 0.0
    assert _lexical_boost(sig_full, user) > 0.0


def test_lexical_boost_capped():
    from pipeline.recommender import _lexical_boost, _LEXICAL_BOOST_CAP
    sig = {"technology_name": "python fastapi nextjs rag agent", "title": "", "summary": ""}
    user = {"tech_stack": ["python", "fastapi", "nextjs"], "interests": ["rag", "agent"]}
    # 3*0.3 + 2*0.2 = 1.3 → cap 0.6
    assert _lexical_boost(sig, user) == _LEXICAL_BOOST_CAP


def test_lexical_boost_empty_profile():
    from pipeline.recommender import _lexical_boost
    sig = {"technology_name": "LangGraph", "title": "", "summary": ""}
    assert _lexical_boost(sig, {"tech_stack": [], "interests": []}) == 0.0
```

- [ ] **Step 2: 실패 확인**

Run: `cd api && .venv/bin/python -m pytest tests/test_recommender_pipeline.py -k lexical_boost -v`
Expected: FAIL — `ImportError: cannot import name '_lexical_boost'`(함수·상수 미구현).

- [ ] **Step 3: `re` import + 상수 + `_lexical_boost` 구현**

`api/pipeline/recommender.py` 상단 import에 `re` 추가:

```python
import math
import re
```

`_MMR_LAMBDA = 0.7` 아래(상수 블록 끝)에 추가:

```python
# ── 하이브리드 관련도: 명시적 스택/관심 렉시컬 가점(임베딩 위에 얹음) ──────────────
# base = clamp(cosine + lexical_boost). "내가 쓰는 도구" 소식을 상위로. 토큰 집합 멤버십
# 매칭이라 "go"가 "google"에 substring 오매칭되지 않는다(v1 폐기 사유 회피).
_STACK_BOOST = 0.3
_INTEREST_BOOST = 0.2
_LEXICAL_BOOST_CAP = 0.6
```

`_clamp` 근처(순수 헬퍼 영역)에 추가:

```python
def _tokenize(text: str) -> set[str]:
    """소문자 영숫자 토큰 집합. 단어 경계 매칭용."""
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _lexical_boost(signal: dict, user_profile: dict) -> float:
    """시그널 텍스트 토큰에 유저 스택/관심 항목(토큰화)이 부분집합으로 포함되면 가점.
    스택당 _STACK_BOOST, 관심당 _INTEREST_BOOST, 합산 상한 _LEXICAL_BOOST_CAP. 무매칭 0.0."""
    text_tokens = _tokenize(
        f"{signal.get('technology_name') or ''} {signal.get('title') or ''} {signal.get('summary') or ''}"
    )
    if not text_tokens:
        return 0.0
    boost = 0.0
    for tech in (user_profile.get("tech_stack") or []):
        item = _tokenize(tech)
        if item and item <= text_tokens:
            boost += _STACK_BOOST
    for interest in (user_profile.get("interests") or []):
        item = _tokenize(interest)
        if item and item <= text_tokens:
            boost += _INTEREST_BOOST
    return min(boost, _LEXICAL_BOOST_CAP)
```

- [ ] **Step 4: 단위 테스트 통과 확인**

Run: `cd api && .venv/bin/python -m pytest tests/test_recommender_pipeline.py -k lexical_boost -v`
Expected: 6개 PASS.

- [ ] **Step 5: `_score_signals` 결합 테스트 작성 (실패 확인용)**

같은 파일에 추가(가점이 base에 실제로 반영돼 랭킹을 바꾸는지 — base를 평탄화해 가점만 차이나게):

```python
def test_score_signals_applies_lexical_boost(monkeypatch):
    """base를 평탄화(0.1)해도 스택 매칭 시그널이 lexical_boost로 1위가 된다.
    match 시그널 id를 정렬상 뒤(sig-b)로 둬, 가점 없으면 tie-break(signal_id 오름차순)로
    non-match(sig-a)가 1위가 되도록 → RED가 확실히 실패하게 설계."""
    import pipeline.recommender as rec
    monkeypatch.setattr(rec, "compute_relevance_score", lambda sig, prof: 0.1)
    signals = [
        {"id": "sig-a", "technology_name": "Mermaid editor", "title": "", "summary": "diagrams",
         "popularity": 0, "source_authority": 0, "published_at": None},
        {"id": "sig-b", "technology_name": "LangGraph release", "title": "", "summary": "x",
         "popularity": 0, "source_authority": 0, "published_at": None},
    ]
    user = {"tech_stack": ["LangGraph"], "interests": []}
    ordered, _variant = rec._score_signals(
        signals, user, "u1", MagicMock(), "2026-08-19", llm=None, signal_embeddings=None
    )
    assert ordered[0][0] == "sig-b"
```

- [ ] **Step 6: 실패 확인**

Run: `cd api && .venv/bin/python -m pytest tests/test_recommender_pipeline.py::test_score_signals_applies_lexical_boost -v`
Expected: FAIL — `llm=None` 경로는 `sorted(key=(-combined, signal_id))` 반환. 가점 전엔 sig-a/sig-b의 combined가 동일(base 0.1, recency/pop/auth 동일)이라 tie-break로 `sig-a`가 1위 → `ordered[0][0]`이 "sig-b"가 아니어서 assert 실패.

- [ ] **Step 7: `_score_signals` base 루프에 가점 적용**

`api/pipeline/recommender.py`의 base 산출 루프(현재):

```python
        if profile_emb is not None and profile_norm > 0 and emb is not None and sig_norm > 0:
            base_scores[sid] = compute_relevance_score_v2(emb, sig_norm, profile_emb, profile_norm)
        else:
            # AD-5 폴백: llm None, 빈 프로필, 임베딩 실패 → substring(정상 경로엔 관여 안 함)
            base_scores[sid] = compute_relevance_score(sig, user_profile)
```

를 아래로 교체:

```python
        if profile_emb is not None and profile_norm > 0 and emb is not None and sig_norm > 0:
            base = compute_relevance_score_v2(emb, sig_norm, profile_emb, profile_norm)
        else:
            # AD-5 폴백: llm None, 빈 프로필, 임베딩 실패 → substring(정상 경로엔 관여 안 함)
            base = compute_relevance_score(sig, user_profile)
        # 하이브리드: 임베딩 코사인 위에 명시적 스택/관심 가점(clamp로 불변식 유지)
        base_scores[sid] = _clamp(base + _lexical_boost(sig, user_profile))
```

- [ ] **Step 8: 결합 테스트 통과 확인**

Run: `cd api && .venv/bin/python -m pytest tests/test_recommender_pipeline.py::test_score_signals_applies_lexical_boost -v`
Expected: PASS.

- [ ] **Step 9: 파일 전체 + 전체 스위트 회귀 확인**

Run: `cd api && .venv/bin/python -m pytest tests/test_recommender_pipeline.py -q`
Expected: 신규 7개 포함 전부 PASS.

Run: `cd api && .venv/bin/python -m pytest -q`
Expected: 전체 PASS(회귀 없음).

- [ ] **Step 10: 커밋**

```bash
git add api/pipeline/recommender.py api/tests/test_recommender_pipeline.py
git commit -m "feat(recommender): 하이브리드 관련도 — 스택/관심 렉시컬 가점

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 배포 후 정성 검증 (수동, 실행 아님)

- 오너(yousk6347) 브리핑을 온디맨드 재생성 또는 다음 06:00 배치 후, `daily_brief_signals`에서
  LangChain/LangGraph 릴리스가 픽션 UI·Mermaid보다 상위 position으로 오는지 확인.
- 과하면 `_STACK_BOOST/_INTEREST_BOOST/_LEXICAL_BOOST_CAP` 조정.
