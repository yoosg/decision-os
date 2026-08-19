# 소스 프로비넌스 랭킹 (전역 도구-릴리스 우선)

- 날짜: 2026-08-19
- 브랜치: `feat/ranking-source-provenance` (base: main)
- 관련: [[ranking-relevance-thread]] 2차 접근, [[engagement-diagnostic-2026-08]]

## 문제

브리핑 랭킹 역전: 큐레이션된 AI 도구 릴리스(LangGraph/LangChain/vLLM…)가 픽션 작성 UI·Mermaid
에디터 등 오프토픽 아래로 밀린다. 1차 시도(하이브리드 렉시컬 가점, merged 4fcff08)는 프로필 토큰이
시그널 텍스트에 **정확히** 있어야 발동하는데, 시그널이 한국어라("에이전트" vs 영어 "agent") 오너
케이스에서 사실상 무효였다([[ranking-relevance-thread]] 프로덕션 검증).

## 관측 근거 (소스가 유형을 깨끗이 가름)

| 시그널 유형 | source_type | source_authority |
|---|---|---|
| LangGraph/LangChain 릴리스 (도구) | **github** | 3 |
| 픽션 UI·Mermaid·소설쓰기 (오프토픽) | hn | 2 |
| Markdown SVG (잡블로그) | official_blog | 4 |

`source_type="github"` = 큐레이션된 도구-릴리스 GitHub 피드(langgraph/langchain/llama_index/vllm/
ollama/llama.cpp, `collector/registry.py` SOURCES) = **"진짜 도구 소식"의 고정밀·언어무관 신호**.
현재 이 신호는 `source_authority`(github=3)에만 반영되고 랭킹 가중치가 5%(`_W_AUTHORITY=0.05`)뿐이라
코사인(70%)에 묻혀 역전이 난다. 게다가 잡블로그(official_blog=4)가 도구 릴리스(github=3)보다 위로
잡히는 미스캘리브레이션도 있다.

## 목표

큐레이션된 도구-릴리스 피드에서 온 시그널을 **전역(모든 유저 공통)**으로 상위에 올린다.
개인화가 아니라 "진짜 도구 릴리스 > 일반 블로그/HN 잡담"이라는 콘텐츠-품질 스탠스. 언어 무관.

## 설계

### 1) `_source_boost(signal) -> float` — `recommender.py`

- 시그널의 중첩 `signal_sources`(list of `{"source_type": ...}`) 중 하나라도 `source_type`이
  `_TOOL_RELEASE_SOURCE_TYPES = {"github"}`에 속하면 `_TOOL_RELEASE_BOOST = 0.3` 반환, 아니면 `0.0`.
- `signal_sources`가 없거나 빈 리스트/None이면 `0.0`(safe).

```python
_TOOL_RELEASE_SOURCE_TYPES = {"github"}
_TOOL_RELEASE_BOOST = 0.3

def _source_boost(signal: dict) -> float:
    for src in (signal.get("signal_sources") or []):
        if (src or {}).get("source_type") in _TOOL_RELEASE_SOURCE_TYPES:
            return _TOOL_RELEASE_BOOST
    return 0.0
```

### 2) base 결합 — `_score_signals` base 루프

기존 하이브리드 렉시컬 가점(무해, 유지) 위에 소스 부스트를 더한다:

```python
base_scores[sid] = _clamp(base + _lexical_boost(sig, user_profile) + _source_boost(sig))
```

base 가중치가 0.70이라 +0.3 부스트가 랭킹을 확실히 끌어올린다. `_clamp`으로 [0.1, 1.0] 유지.

### 3) 시그널 조회에 소스 포함 — `create_daily_brief_for_user`

스코어링용 시그널 fetch(현재 `select("id,technology_name,title,summary,published_at,popularity,source_authority")`,
line ~522)에 중첩 임베딩을 추가:

```python
.select("id,technology_name,title,summary,published_at,popularity,source_authority,signal_sources(source_type)")
```

PostgREST 중첩 select로 각 시그널이 `signal_sources: [{"source_type": "github"}, ...]`를 들고 온다.
스코어링 시그널은 전부 이 fetch(→ `_score_signals`)를 경유하므로 이 한 곳이면 충분하다.

### 4) 안 건드리는 것

- 임베딩 텍스트·결합 가중치(`_W_RELEVANCE=0.70` 등)·MMR(`_MMR_LAMBDA=0.7`)·`_SOURCE_AUTHORITY` 등급·
  `_W_AUTHORITY`·프론트/DB 스키마: **불변**.
- official_blog=4 미스캘리브레이션: 소스 부스트가 도구 릴리스에 +0.3을 줘 우회로 해결 → authority 재보정 안 함(YAGNI).
- 1차 렉시컬 가점: 무해하므로 유지(영어 토큰 나올 땐 도움).

### 5) 에러 / 엣지

- `signal_sources` 미포함/빈/None → boost 0(예외 없음).
- 여러 소스 중 하나만 github여도 부스트(도구 피드 프로비넌스면 충분).
- 기존 테스트 시그널 dict는 `signal_sources` 키 없음 → boost 0 → 회귀 없음.

## 테스트 (`api/tests/`)

- **`_source_boost` 단위**:
  - `signal_sources`에 `{"source_type":"github"}` 있음 → `_TOOL_RELEASE_BOOST`.
  - hn/official_blog만 있음 → 0.
  - `signal_sources` 없음/빈/None → 0.
- **`_score_signals` 통합**: github 소스 시그널이 동일 코사인 base의 hn 소스 시그널보다 상위(1위).
  (base 평탄화 monkeypatch, match id를 정렬상 뒤로 둬 RED 신뢰성 확보 — 1차 패턴 재사용.)
- **회귀**: 기존 recommender/파이프라인 테스트 전부 그린(signal_sources 없는 기존 픽스처는 부스트 0).
- **정성 검증(수동)**: test-history 브리핑 온디맨드 재생성(세션쿠키 토큰 → `POST /api/v1/daily-briefs/trigger`)
  후 `daily_brief_signals`에서 github-소스(LangGraph 등)가 hn-소스(픽션/Mermaid)보다 상위 position인지
  확인. (전역 부스트라 test-history 프로필과 무관하게 먹혀야 함.)

## 범위 밖 (YAGNI)

- 유저별 개인화(관심 한↔영 매핑 등).
- `source_authority` 등급/가중치 재보정.
- 큐레이션 소스 집합 확장(특정 official_blog를 도구로 승격 등).
- 렉시컬 가점 크로스링구얼 개선/제거.

## 요약 (변경 파일)

- `api/pipeline/recommender.py` — `_source_boost` + 상수 2개, `_score_signals` base 루프에 부스트 결합, `create_daily_brief_for_user` 시그널 select에 `signal_sources(source_type)` 추가
- `api/tests/test_recommender_pipeline.py` — `_source_boost` 단위 + `_score_signals` 통합/회귀
