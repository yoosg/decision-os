# 랭킹 하이브리드 관련도 (Recommender 관련도 개선)

- 날짜: 2026-08-19
- 브랜치: `feat/ranking-hybrid-relevance` (base: main)
- 관련: [[engagement-diagnostic-2026-08]] 정성 점검에서 발견, [[epic-6-real-data-ingestion]] Recommender v2

## 문제 (정성 진단 근거)

오너(AI 엔지니어 · RAG 서비스 · 관심 RAG/Agent · 스택 Python/FastAPI/Next.js)의 2026-08-18
브리핑에서 **랭킹이 역전**됐다: 오너 스택에 정확히 맞는 LangChain/LangGraph 릴리스가 6·10·13·14위로
밀리고, 픽션 작성 터미널 UI·Mermaid 에디터·Markdown SVG 같은 오프토픽이 3·4·5위 상위에 올랐다.

원인: `_score_signals`의 관련도(base)가 **"프로필 텍스트 ↔ 시그널 summary" 임베딩 코사인**에만
의존한다. 릴리스 노트 summary("1.5.0 릴리스, 버그 수정")는 일반적 changelog 문구라 "RAG/Agent"와
의미적으로 안 붙어 **오너의 정확한 도구가 낮은 코사인**을 받는다. v1엔 스택 substring 매칭(+0.4)이
있었으나 v2가 순수 임베딩으로 바꾸며 그 신호가 빠졌다(v1은 "go→google" 오매칭 때문에 폐기).

## 목표

임베딩 코사인(의미 유사도)은 유지하되, **명시적 스택/관심 렉시컬 가점**을 base에 더해
"내가 매일 쓰는 바로 그 도구" 소식을 확실히 상위로 올린다(하이브리드).

## 설계

### 1) 렉시컬 가점 `_lexical_boost(signal, user_profile) -> float`

- 대상 텍스트: 시그널의 `technology_name + " " + title + " " + summary`(소문자화).
- 매칭 대상: 유저 `tech_stack`(각 항목), `interests`(각 항목).
- **단어경계/토큰 매칭**: 대상 텍스트를 소문자화 후 영숫자 토큰으로 분리(`re.findall(r"[a-z0-9]+", text)`)하여
  **토큰 집합 멤버십**으로 매칭한다. 이렇게 하면 "go"가 "google"에 substring으로 잘못 걸리지 않는다
  (v1 폐기 사유 회피). 스택/관심 항목도 동일 토큰화하여, 다중 토큰 항목("llama index" 등)은
  **모든 토큰이 존재**할 때 매칭으로 본다.
- 가점(상수 분리, 조정 가능): 매칭된 스택 항목당 `_STACK_BOOST=0.3`, 관심 항목당 `_INTEREST_BOOST=0.2`.
  합산 상한 `_LEXICAL_BOOST_CAP=0.6`(과도 가점 방지).
- 반환: `min(sum_of_boosts, _LEXICAL_BOOST_CAP)`. 매칭 없으면 `0.0`.

### 2) base에 가점 적용 — `_score_signals` (line ~349-359)

base 산출 루프의 두 경로(v2 코사인 / substring 폴백) **모두**에 동일 가점을 얹는다:

```python
for sig in signals:
    sid = sig["id"]
    emb = embeddings.get(sid)
    sig_norm = norms.get(sid, 0.0)
    if profile_emb is not None and profile_norm > 0 and emb is not None and sig_norm > 0:
        base = compute_relevance_score_v2(emb, sig_norm, profile_emb, profile_norm)
    else:
        base = compute_relevance_score(sig, user_profile)
    base_scores[sid] = _clamp(base + _lexical_boost(sig, user_profile))
```

`_clamp`으로 [0.1, 1.0] 불변식 유지. 이후 Memory RAG 블렌드·랭킹 피처 결합·MMR은 **불변**.

### 3) 안 건드리는 것

- **임베딩 텍스트(summary)**: Memory RAG 대칭성(6.4 AC4) 유지 위해 그대로. 가점은 임베딩과 별개 신호라
  대칭성 안 깨짐.
- **결합 가중치/MMR**: `_W_RELEVANCE=0.70` 등, `_MMR_LAMBDA=0.7` 그대로. 가중치 튜닝은 실사용 데이터가
  없어 근거 없는 손댐([[engagement-diagnostic-2026-08]] 결론) → 이번엔 렉시컬 가점만으로 역전이
  교정되는지 본다.
- **프론트/DB 스키마**: 변경 없음. `relevance_score`(=combined)의 의미만 개선.

### 4) 에러 / 엣지

- 빈 `tech_stack`/`interests` → 가점 0(기존 동작 동일).
- 토큰화 대상이 비거나 특수문자만 → 매칭 0, 예외 없음.
- 다중 토큰 스택 항목의 부분 매칭은 매칭 아님(전 토큰 존재 필요) — 오탐 억제.
- 기존 NaN 방어(`_as_float`)·`_clamp` 재사용.

## 테스트 (`api/tests/`)

- **`_lexical_boost` 단위**:
  - 스택 매칭("langgraph" in technology_name) 시그널이 무매칭 시그널보다 가점 큼.
  - **"go"가 "google"에 오매칭 안 됨**(토큰 경계) — 회귀 방지 핵심.
  - 관심 매칭("rag") 가점 적용.
  - 다중 토큰 스택("llama index")은 두 토큰 다 있을 때만 매칭.
  - 상한 `_LEXICAL_BOOST_CAP` 초과 안 함.
  - 빈 프로필 → 0.
- **`_score_signals` 통합**: 동일 코사인 base라도 스택 매칭 시그널의 최종 base가 더 높음
  (기존 `test_recommender_pipeline.py` 관례로 client/llm 모킹). 매칭 없으면 기존 점수 불변.
- **회귀**: 기존 recommender/파이프라인 테스트 전부 그린.
- **정성 검증(수동)**: 오너(yousk6347) 브리핑을 온디맨드 재생성(또는 다음 배치) 후, LangChain/LangGraph
  릴리스가 픽션 UI·Mermaid보다 상위로 오는지 DB에서 확인.

## 범위 밖 (YAGNI)

- 결합 가중치 데이터 튜닝(6.5 held-out 측정 영역, 데이터 부족으로 보류).
- 임베딩 대상 텍스트 변경, 프로필 임베딩 구조화.
- 오프도메인 필터(수집단) 강화.
- 소스 프로비넌스 가점(시그널이 온 소스 피드가 유저 스택과 일치 시 가점) — 향후 후보.
- 클릭/열람 이력 기반 개인화 학습.

## 요약 (변경 파일)

- `api/pipeline/recommender.py` — `_lexical_boost` 헬퍼 + 상수(`_STACK_BOOST/_INTEREST_BOOST/_LEXICAL_BOOST_CAP`) 추가, `_score_signals` base 루프에 가점 적용
- `api/tests/…` — `_lexical_boost` 단위 + `_score_signals` 통합/회귀 테스트
