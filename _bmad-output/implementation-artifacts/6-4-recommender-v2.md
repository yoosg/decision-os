---
baseline_commit: NO_VCS
---

# Story 6.4: Recommender v2

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

개발자로서,
Recommender의 **콜드스타트 점수를 substring 매칭에서 임베딩 코사인 유사도로 바꾸고, 6.3이 저장한 랭킹 메타데이터(최신성·인기·출처 권위)와 다양성(MMR)을 최종 점수에 반영**하고 싶다,
그래서 `"go"→"google"` 같은 오매칭 없이 개인화 정확도가 오르고, 브리핑이 같은 기술로 도배되지 않으며 최신·화제 시그널이 위로 올라온다.

> **🍎 프론트엔드 비유 (오너용):** 지금까지의 파이프라인을 "뉴스 편집국"에 비유해 왔다.
> - **6.1** 취재(수집), **6.2** 데스크 정리(클러스터·필터), **6.3** 토픽 카드에 메타 스티커 붙이기(발행시각·인기·권위 저장).
> - **6.4(이 스토리)** 는 그 카드들을 보고 **"이 독자에게 어떤 순서로 신문 1면을 짜줄까"를 정하는 편집장** 이다.
> - **지금 편집장의 문제 1 (오매칭):** 독자 관심사를 "글자가 겹치나"로만 본다. 독자가 `Go`(언어)에 관심 있다고 하면, 제목에 `Google`이 있는 기사도 "겹친다"고 착각해 위로 올린다(`go`가 `google` 안에 들어있으니까). → **v2는 "글자 겹침"이 아니라 "의미가 가까운가"(임베딩 코사인)로 본다.** 프론트로 치면 `string.includes()` 필터를 벡터 유사도 정렬로 바꾸는 것.
> - **지금 편집장의 문제 2 (도배·낡음):** 관련도만 보고 줄 세우면 1면이 전부 같은 기술(예: LangChain ×5)로 도배되고, 반년 전 뉴스가 오늘 뉴스보다 위에 올 수 있다. → **v2는 "관련도 × 최신성 × 화제성 × 출처 신뢰도"를 섞고, 같은 기술 반복은 눌러(MMR 다양성) 1면을 골고루 짠다.**
> - **핵심 제약:** 각 시그널의 `relevance_score`(0.1~1.0)라는 규칙과 "같은 입력이면 항상 같은 순서"(결정론)는 그대로 지킨다. 프론트로 치면 **정렬 키를 바꾸되, 컴포넌트가 기대하는 데이터 계약(점수 범위·안정 정렬)은 안 깬다.**
> - **6.3과의 관계:** 6.3은 카드에 스티커를 *붙이기만* 했다(저장). 6.4는 그 스티커를 *실제로 읽어서 순위에 쓴다*. 6.3 Dev Notes가 명시했듯 `recommender.py`의 `SELECT`에 6.3이 추가한 컬럼(`published_at`·`popularity`·`source_authority`)을 이제 넣는다.

## Acceptance Criteria

**AC1 — 콜드스타트: substring 제거 → 프로필/시그널 임베딩 코사인 (FR-8.4, 리뷰 파인딩 "go→google")**
- **Given** Memory가 없는 사용자(콜드스타트)이고 `llm`이 주입되어 있을 때
- **When** 관련성 기본 점수를 산출하면
- **Then** 프로필 텍스트(`tech_stack` + `interests` 조합)를 `llm.embed_text`로 임베딩한 벡터와, 각 Signal 임베딩 벡터의 **코사인 유사도**로 점수를 낸다 (substring `in` 매칭 완전 제거)
- **And** `"go"`(tech_stack)가 제목 `"Google announces..."`인 무관 시그널을 **끌어올리지 않는다** (오매칭 해소 — 전용 테스트로 증명)
- **And** `relevance_score` 불변식을 유지한다: 최종 저장값 ∈ **[0.1, 1.0]**, 정렬은 **결정론적**(동점은 `signal_id` 오름차순 tie-break)
- **And** 코사인은 **순수 파이썬**으로 계산한다 (numpy·외부 벡터 DB 금지 — 6.2 `_cosine` 패턴과 동일, AD-2/AD-6)

**AC2 — 랭킹 피처: 최신성·인기·출처 권위 반영 (FR-8.4, 6.3 메타데이터 소비)**
- **Given** `signals` row에 6.3이 저장한 `published_at`·`popularity`·`source_authority`가 있을 때
- **When** 최종 점수를 산출하면
- **Then** `recommender.py`의 Signal `SELECT`가 `id,technology_name,title,summary`에서 **`published_at,popularity,source_authority`를 포함하도록 확장**된다 (6.3 Dev Notes가 6.4로 넘긴 작업)
- **And** **최신성 감쇠**(published_at이 최근일수록 가점, 반감기 기반), **인기**(popularity 로그 정규화), **출처 권위**(source_authority/4)가 기본 관련도와 결합된다
- **And** 결합식은 가중 블렌드로 **[0.1, 1.0] 불변식을 보존**한다: `combined = clamp(0.1, 1.0, 0.70·base_relevance + 0.15·recency_norm + 0.10·popularity_norm + 0.05·authority_norm)` (가중치는 초기값 — 6.5 측정으로 튜닝, 상수로 분리)
- **And** `published_at`이 `NULL`(stub/pass-through/값없는 RSS)인 시그널은 최신성 페널티 없이 **중립 처리**(`recency_norm=0.5`)되어 안전 저하한다 (AD-5)

**AC3 — 다양성(MMR): 같은 기술 도배 방지 (FR-8.4)**
- **Given** 점수가 매겨진 후보 시그널들과 그 임베딩이 있을 때
- **When** 최종 순서(position)를 정하면
- **Then** **MMR**(Maximal Marginal Relevance) greedy 재랭킹으로, 이미 선택된 시그널과 임베딩 코사인이 높은(=주제가 겹치는) 시그널의 우선순위를 낮춘다: `mmr = λ·combined − (1−λ)·max_{선택됨} cosine(embᵢ, embⱼ)`, λ=0.7(상수)
- **And** MMR 재랭킹도 **결정론적**이다(동점은 `signal_id` tie-break)
- **And** 저장 시 `daily_brief_signals.position`은 MMR 순서, `relevance_score`는 `combined` 점수(0.1~1.0)를 기록한다
- **And** 임베딩이 없는 시그널(임베딩 실패)은 중복 페널티 0으로 취급되어 **탈락하지 않고** 순서에만 뒤로 밀린다 (AD-5)

**AC4 — Memory RAG 대칭화 + weight 재검토 (리뷰 파인딩: query/doc 임베딩 텍스트 비대칭)**
- **Given** Memory 보유 사용자의 RAG 블렌딩 경로에서
- **When** `match_memories` RPC용 query 벡터를 만들면
- **Then** Signal의 RAG-query 임베딩 텍스트를 **memory 문서 임베딩 텍스트(summary)와 대칭**이 되도록 맞춘다 — `_signal_embed_text`를 `technology_name + title + summary`에서 **`summary` 중심**(summary 없으면 title 폴백)으로 변경 (memory는 `memory_manager`에서 `summary`만 임베딩 → 동일 표현 공간)
- **And** 콜드스타트 코사인(프로필 vs 시그널)도 **동일한 단일 시그널 임베딩**을 재사용한다(시그널당 임베딩 1회 유지 — 설계 A-2 "배치당 1회 임베딩" 불변, 비용 증가 없음)
- **And** `_RAG_WEIGHT`(현재 0.5)를 **재검토**한다: 콜드스타트 base가 substring 카운트(0.1~1.0 이산)에서 코사인(0.1~1.0 연속)으로 바뀌어 스케일이 달라졌으므로, weight 값을 상수로 유지하되 근거 주석을 갱신(정확한 최적값은 6.5 측정 대상 — 이 스토리는 스케일 정합성만 보장)

**AC5 — Memory 보유 경로 유지 + v2 결합 (AC 원문, AD-2/6)**
- **Given** Memory 보유 사용자일 때
- **When** 추천을 수행하면
- **Then** 기존 `match_memories` RAG 블렌딩 경로를 **유지**하되, base 관련도는 v2 콜드스타트(코사인)로, 최종 점수는 v2 랭킹 피처(AC2)·다양성(AC3)과 결합된다
- **And** `match_memories`의 `user_id` 스코프 강제(AC-A3 5.4)·RPC 실패 안전 폴백(AD-5)은 그대로 보존된다

**AC6 — 무회귀 & 안전 저하 (AD-5, AD-15)**
- **Given** v2 스코어링 도입 후
- **When** `llm`이 미주입(테스트·오프라인)이거나 프로필/시그널 임베딩이 실패할 때
- **Then** 예외 없이 **안전 저하**한다: `llm is None` → 콜드스타트 폴백(아래 D1 결정), 개별 임베딩 실패 → 해당 시그널만 폴백, RAG 전체 실패 → base로 폴백. brief 생성은 항상 지속
- **And** 배치(`run_recommender`)·온디맨드(`create_daily_brief_for_user` 직접 호출) 두 경로 모두 정상 동작하고, brief 상태 전이(pending→processing→completed/failed)·중복 스킵·stuck 정리 로직은 **무변경**
- **And** `cd api && pytest -q` 전체 회귀(현재 **202 passed**) 통과 + v2 신규 테스트 추가

> ⚠️ **스코프 경계 (중요):** 이 스토리는 **Recommender 스코어링 로직 v2**(콜드스타트 임베딩 전환 + 랭킹 피처 결합 + MMR + RAG 대칭화)까지만 한다.
> - **하지 말 것:** engagement 로깅·측정 하네스·오프라인 평가 리포트(→ **6.5**), 시그널 임베딩을 DB 컬럼으로 **영속화**(pgvector signals.embedding — 이번엔 인프로세스 배치 임베딩 재사용, 신규 컬럼/마이그레이션 금지), 새 마이그레이션(6.3이 컬럼 이미 추가), 외부 벡터 DB 도입, 6.1~6.3 수집·클러스터·normalize·스키마 변경(무변경), `daily_briefs` 상태머신·스케줄러(AD-15) 변경.
> - **가중치·λ·반감기는 "최적값"이 목표가 아니다** — 합리적 초기 상수 + 상수 분리 + 근거 주석까지. 실제 튜닝은 6.5가 데이터로 한다.
> - **RAG weight 절대 재검토를 "제거"로 오해 말 것** — RAG 블렌딩 경로는 유지(AC5). weight는 스케일 정합성 관점에서 값 검토 + 근거 주석 갱신.

## Tasks / Subtasks

- [x] **Task 1 — 시그널 SELECT 확장 + 임베딩 텍스트 대칭화** (AC: 2, 4)
  - [x] `recommender.py`의 두 SELECT를 확장: `_build_signal_embeddings`, `create_daily_brief_for_user` — `select("id,technology_name,title,summary")` → `select("id,technology_name,title,summary,published_at,popularity,source_authority")`. `.eq("status","processed")` 유지
  - [x] `_signal_embed_text`를 **summary 중심**으로 변경: `summary`가 있으면 `summary`, 없으면 `title` 폴백, 둘 다 없으면 `""`(→ 임베딩 스킵, 기존 동작). memory(`summary`)와 대칭 (AC4)
  - [x] ⚠️ 이 변경은 **콜드스타트 코사인·RAG query 둘 다에 쓰이는 단일 임베딩**에 영향 — 의도된 대칭화. 시그널당 임베딩 1회 유지(설계 A-2 불변)

- [x] **Task 2 — 콜드스타트 v2: 프로필 임베딩 + 코사인 관련도** (AC: 1, 6)
  - [x] 순수 파이썬 코사인/norm 헬퍼 추가(D3): `_norm(vec)`, `_cosine(a, b, norm_a, norm_b)` — 6.2 `clustering.py`와 동일 시그니처(모듈 간 결합 회피 위해 recommender에 로컬 정의)
  - [x] `_embed_profile(user_profile, llm, brief_date) -> list[float] | None`: `tech_stack + interests`를 공백 조인해 임베딩. 빈 프로필/임베딩 실패 → `None`(로깅, safe-degrade)
  - [x] `compute_relevance_score_v2(signal_emb, signal_norm, profile_emb, profile_norm) -> float`: 코사인 → `clamp(0.1, 1.0, cosine)`. 임베딩 없으면 호출 전 폴백 처리
  - [x] 기존 `compute_relevance_score`(substring)는 **삭제하지 않고 AD-5 폴백 전용으로 보존**(D1) — `llm is None` 또는 프로필 임베딩 불가 시에만 사용. docstring에 "v1 FALLBACK ONLY" 명시
  - [x] ⚠️ substring이 **llm 주입 정상 경로에는 절대 관여하지 않도록** 분기 — profile_emb/norm 유효 시 코사인, 아니면 폴백

- [x] **Task 3 — 랭킹 피처 결합(최신성·인기·권위)** (AC: 2, 6)
  - [x] 모듈 상수 분리: `_W_RELEVANCE=0.70`, `_W_RECENCY=0.15`, `_W_POPULARITY=0.10`, `_W_AUTHORITY=0.05`, `_RECENCY_HALFLIFE_DAYS=7`
  - [x] `_recency_norm(published_at, brief_date) -> float`: `published_at` None → `0.5`(중립). 있으면 `0.5 ** (age_days / halflife)`를 [0,1]로. 미래 timestamp는 age 음수 방어(→ 1.0 캡)
  - [x] `_popularity_norm(popularity, batch_max_logpop) -> float`: `log1p(popularity) / batch_max_logpop`([0,1], batch_max=0이면 0). 배치 내 정규화(같은 브리프 후보들 기준)
  - [x] `_authority_norm(source_authority) -> float`: `source_authority / 4.0`(0~4 등급 → 0~1). None → 0
  - [x] `combined = clamp(0.1, 1.0, _W_RELEVANCE·base + _W_RECENCY·recency + _W_POPULARITY·pop + _W_AUTHORITY·auth)`
  - [x] ⚠️ 결합 후에도 **[0.1,1.0] 불변식**을 `_clamp`로 보장 — `daily_brief_signals.relevance_score`(FLOAT NOT NULL, DB CHECK 없음 → 코드로 강제)

- [x] **Task 4 — MMR 다양성 재랭킹** (AC: 3, 6)
  - [x] `_mmr_rerank(scored_with_emb, lambda_=0.7) -> list[tuple[str, float]]`: `[(signal_id, combined, emb, norm)]`에서 greedy 선택 — 매 라운드 `mmr = λ·combined − (1−λ)·max_{선택됨} cosine`. 최고 mmr 선택, 동점은 `signal_id` tie-break
  - [x] 임베딩 없는 시그널은 `max cosine = 0`(중복 페널티 0) → 탈락 없이 뒤로. 선택 집합에 임베딩 없으면 코사인 항 스킵
  - [x] 임베딩 전무(llm None 또는 전부 실패) → MMR 스킵, `sorted((-combined, signal_id))` 폴백
  - [x] 반환은 **MMR 순서** 리스트 — `create_daily_brief_for_user`가 `enumerate`로 position 부여(기존 골격 유지, 정렬 소스만 MMR로)

- [x] **Task 5 — `_score_signals` v2 조립** (AC: 1, 2, 3, 4, 5, 6)
  - [x] `_score_signals` 재작성: (1) 프로필 임베딩 1회, (2) 시그널별 base = 코사인(profile, signal) 또는 폴백, (3) Memory 보유 시 RAG 블렌드(기존 match_memories 경로 유지, top_sim 가산), (4) 랭킹 피처 결합 → combined, (5) MMR 재랭킹 → 순서 확정
  - [x] 시그널 dict에서 `published_at`(ISO str)·`popularity`·`source_authority` 파싱 — `published_at` 파싱 실패/None → 중립. `datetime.fromisoformat` 방어적 처리(`_parse_dt`, 'Z'/naive 정규화)
  - [x] Memory 체크(memories count)·`match_memories` RPC·user_id 격리·RPC 실패 폴백·전체 예외 폴백(AD-5) **로직 보존** — base 계산만 코사인으로 교체, 블렌드 후 랭킹 피처·MMR 추가
  - [x] `_RAG_WEIGHT` 근거 주석 갱신(콜드스타트 base 스케일 변화 반영, AC4/D2). 값 유지(0.5)
  - [x] `pipeline_log` 이벤트 확장: `memory_rag_applied`/`memory_rag_coldstart`/`memory_rag_query_failed`에 `scorer="v2"` 표식 추가 — 관측성(AD-12)

- [x] **Task 6 — 테스트** (AC: 1~6)
  - [x] `tests/test_recommender_pipeline.py` 확장(신규 19 테스트):
    - 콜드스타트 코사인: 프로필과 의미 가까운 시그널이 먼 시그널보다 높은 점수(임베딩 mock로 벡터 지정)
    - **오매칭 방지 회귀:** tech_stack=`["go"]`, 시그널 제목=`"Google announces X"`(무관 임베딩) → 끌어올리지 않음(substring이었으면 매칭됐을 케이스)
    - 불변식: 모든 combined ∈ [0.1,1.0]; 동점 입력 → `signal_id` 오름차순 결정론
    - 랭킹 피처: 동일 base에서 최신(published_at 최근)·고인기(popularity↑)·고권위 시그널이 상위; published_at None 중립
    - MMR: 유사 임베딩 시그널 → 상위에 몰리지 않고 분산; 임베딩 없는 시그널 탈락 안 함
    - RAG 대칭: `_signal_embed_text` = summary 기반(단위 검증); memory 보유 경로 단일 임베딩 재사용 검증
    - AD-5: llm None → substring 폴백; 프로필 임베딩 실패 → 폴백; RPC 실패 → base 폴백
  - [x] ⚠️ 기존 RAG/콜드스타트 테스트(8개)는 랭킹 피처 결합으로 기대값을 v2로 갱신(`_combine_neutral` 헬퍼) — 삭제 없이 커버리지 유지
  - [x] **오프라인 원칙(절대):** 실 네트워크·실 OpenAI·실 DB 금지. Supabase `MagicMock`, llm `MagicMock(embed_text=...)`
  - [x] **회귀:** `cd api && pytest -q` → **221 passed** (202 baseline + 신규 19, 전부 green)

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Opus 4.8)

### Debug Log References

- Baseline 회귀: `cd api && pytest -q` → 202 passed (착수 전 확인).
- v2 개편 직후 기존 8개 score/RAG 테스트가 랭킹 피처 결합(`combined = 0.7·blended + 0.15·0.5`)으로 실패 → 기대값을 `_combine_neutral` 헬퍼로 v2 갱신(삭제 없이 커버리지 유지).
- 신규 테스트 `test_popularity_norm`에서 `math` 미import → 테스트 파일에 `import math` 추가.
- 최종: `pytest -q` → **221 passed, 0 failed**.

### Completion Notes List

- **AC1 (콜드스타트 코사인 + go→google 오매칭 해소):** 정상(llm 주입) 경로 base를 substring→프로필/시그널 임베딩 코사인(`compute_relevance_score_v2`)으로 전환. `_cosine`/`_norm`은 순수 파이썬(numpy·외부 벡터DB 금지, AD-2/6). 전용 회귀 테스트 `test_coldstart_no_substring_pullup_go_google`로 tech="go"가 "Google" 제목 무관 시그널을 끌어올리지 않음을 증명. 불변식 [0.1,1.0]·`signal_id` 결정론 tie-break 유지.
- **AC2 (랭킹 피처):** 두 SELECT를 `published_at,popularity,source_authority`로 확장(6.3이 준비한 컬럼 소비). `_recency_norm`(반감기 7일, None→0.5 중립, 미래→1.0 캡)·`_popularity_norm`(배치 내 log1p 정규화)·`_authority_norm`(/4.0)을 가중 블렌드로 결합, `_clamp`로 [0.1,1.0] 보존.
- **AC3 (MMR):** `_mmr_rerank` greedy(`λ=0.7`), 동점 `signal_id` tie-break. 임베딩 없는 시그널은 중복 페널티 0으로 탈락 없이 뒤로. `relevance_score`=combined, `position`=MMR 순서(D4).
- **AC4 (RAG 대칭화):** `_signal_embed_text`를 `tech+title+summary`→**summary 중심**(없으면 title 폴백)으로 변경 — memory(`summary`만 임베딩)와 동일 표현 공간. 콜드스타트·RAG query가 시그널당 단일 임베딩 공유(A-2 불변, 비용 증가 없음).
- **AC5 (Memory 경로 유지):** `match_memories` RAG 블렌딩·user_id 스코프 강제·RPC 실패 폴백 로직 보존, base만 코사인으로 교체 후 랭킹 피처·MMR과 결합.
- **AC6 (무회귀·안전 저하):** `llm None`→substring 폴백, 프로필/시그널 임베딩 실패→해당 폴백, RAG 전체 실패→base 폴백. brief 상태머신·중복 스킵·stuck 정리·배치/온디맨드 두 경로 무변경. 전체 회귀 221 passed.
- **D1/D2/D3:** 오너 확인 → 추천안대로. D1=substring "v1 FALLBACK ONLY" 보존, D2=`_RAG_WEIGHT=0.5` 값 유지+스케일 정합성 주석 갱신(정규화 리팩터는 6.5), D3=`_norm`/`_cosine` recommender 로컬 정의.
- **관측성(AD-12):** RAG 관련 pipeline_log 이벤트에 `scorer="v2"` 표식 추가.
- 마이그레이션·models·clustering·normalizer·orchestrator·memory_manager 무변경(단일 모듈 + 테스트에 국한).

### File List

- `api/pipeline/recommender.py` (수정) — 코사인 콜드스타트(`compute_relevance_score_v2`, `_embed_profile`, `_norm`/`_cosine`) + 랭킹 피처(`_recency_norm`/`_popularity_norm`/`_authority_norm`, `_as_float`/`_parse_dt`, 가중치 상수) + MMR(`_mmr_rerank`) + `_score_signals` v2 재작성 + 두 SELECT 확장 + `_signal_embed_text` summary 대칭화 + `compute_relevance_score` v1 폴백 격리 + `_RAG_WEIGHT` 주석 갱신
- `api/tests/test_recommender_pipeline.py` (수정) — v2 신규 19 테스트(코사인 순위·go→google 회귀·불변식/결정론·랭킹 피처·MMR 분산·RAG 대칭·AD-5 폴백·헬퍼 단위) + 기존 8 테스트 v2 기대값 갱신(`_combine_neutral`) + `import math`

## Dev Notes

### 아키텍처 준수 (반드시 따를 것)

- **AD-2 / AD-6 (pgvector 전용, 외부 벡터 DB·numpy 금지):** 콜드스타트 코사인·MMR 코사인은 **인프로세스 순수 파이썬**으로 계산(6.2 `clustering.py`가 확립한 패턴). 시그널 임베딩을 DB에 영속화(pgvector `signals.embedding` 컬럼)하지 않는다 — 배치당 인프로세스 임베딩 재사용(설계 A-2). 새 벡터 컬럼·마이그레이션 금지.
- **AD-5 (격리 / safe degradation):** `llm` 부재, 프로필/시그널 임베딩 실패, RAG RPC 실패 — 어느 것도 배치를 죽이지 않고 폴백(콜드스타트 substring 또는 base). 한 사용자·한 시그널 실패가 전체 brief를 막으면 안 된다. `run_recommender`의 사용자별 try/except 격리(L446-470)·stuck 정리(L47-67) 무변경.
- **AD-12 (관찰 가능성):** `pipeline_log` 이벤트에 v2 스코어러 표식·핵심 피처값을 남겨, 6.5 측정 이전에도 "왜 이 순서인지" 추적 가능하게.
- **AD-15 (Batch First + On-demand Fallback):** 6.4는 **Recommender 단계 내부** 로직만 바꾼다. 배치(`run_daily_pipeline` → `run_recommender`)와 온디맨드(`run_ondemand_brief` → `create_daily_brief_for_user`, Signals 이미 생성됨) **두 경로 모두** 새 스코어링을 탄다. 실행 모델·순서·시그니처는 무변경.
- **AD-16 (Signal = 기술/변화 + 다출처):** 6.4는 이 Signal 단위를 소비만 한다. 6.3이 만든 `source_authority`(다출처 중 최고 권위)·`popularity`(다출처 인기 합)를 랭킹에 반영 — 다출처 묶음의 "권위·화제성"을 순위로 환산.

### 설계 결정 (Dev가 반드시 이 방향으로 구현)

**D1 — substring `compute_relevance_score`는 삭제가 아니라 "AD-5 폴백 전용"으로 격리:**
AC1은 "substring 매칭 제거"를 요구한다. 이는 **정상(llm 주입) 경로에서 substring이 관여하지 않게** 하라는 뜻이다.
- **채택:** 정상 경로 base = 코사인(프로필, 시그널). `llm is None`(테스트·오프라인) 또는 프로필 임베딩 불가일 때만 `compute_relevance_score`(substring)로 폴백. 함수는 남기되 주석에 "v1 fallback only" 명시.
- **이유:** `llm None`인 경로(단위 테스트 다수, 임베딩 배치 실패)에서 모든 시그널을 flat 0.1로 주면 순서가 무의미해진다. substring을 **저하 모드 안전망**으로 남기면 AD-5를 지키면서 정상 경로 오매칭은 사라진다.
- **오너 확인 대상:** "완전 삭제(폴백도 flat 0.1)" vs "폴백 전용 보존" — 스토리 말미 질문 D1.

**D2 — RAG weight 재검토: 스케일 정합성만, 최적값은 6.5:**
`_RAG_WEIGHT=0.5`는 base가 substring 카운트(0.1, 0.4, 0.7, 1.0…)일 때 튜닝됐다. v2에서 base가 코사인(연속 0.1~1.0, 실무상 0.1~0.6에 밀집)으로 바뀌면 `base + 0.5·top_sim`의 균형이 달라진다.
- **채택:** 이 스토리에선 **값을 유지(0.5)하되 근거 주석을 갱신** — "base가 코사인으로 바뀜, 최적 weight는 6.5 held-out 측정으로 확정"이라 명시. 6.5 전에 임의로 크게 바꾸면 근거 없는 튜닝이 된다.
- **대안:** RAG 블렌드를 base와 동일 스케일로 정규화(예: `combined_base = (1-w)·cold + w·rag_sim`, w∈[0,1]). 더 깔끔하나 기존 테스트·행동을 크게 흔든다 → 6.5 이후 리팩터 권장. **오너 확인 대상(질문 D2).**

**D3 — 코사인 헬퍼: recommender에 로컬 정의(모듈 간 결합 회피):**
6.2 `clustering.py`에 `_norm`/`_cosine`(순수 파이썬)이 이미 있다. 재사용하려면 import하거나 공용 모듈로 추출해야 한다.
- **채택:** recommender에 **동일 시그니처로 ~6줄 로컬 정의**(과설계 회피 — 6.3이 github.py에서 취한 것과 같은 판단). `clustering`↔`recommender` import 결합·공용 모듈 신설을 피한다.
- **대안:** `pipeline/vector_utils.py` 공용 모듈로 추출 후 clustering·recommender 공유. DRY하지만 clustering 리팩터(회귀 위험)·모듈 신설 비용. 중복이 6줄이라 이득이 작다. **오너 확인 대상(질문 D3).**

**D4 — MMR은 position만 바꾼다, relevance_score는 combined 유지:**
MMR은 "관련도 vs 중복"의 재랭킹이라 **순서(position)** 를 바꾸지만, `relevance_score`에 MMR 페널티까지 반영하면 점수 의미가 흐려진다.
- **채택:** `relevance_score` = `combined`(0.1~1.0, 관련도·피처 결합), `position` = MMR 순서. 프론트/화면은 relevance_score를 "이 시그널이 나와 얼마나 맞나"로, position을 "브리프 내 순서"로 각각 소비 — 계약 분리 명확.

**D5 — published_at 파싱 방어(6.3 리뷰 Defer 인접):**
6.3은 `published_at`을 aware datetime으로 저장하지만, DB에서 읽을 때 ISO 문자열(`+00:00` 또는 `Z`)로 온다. `_recency_norm`은 이를 파싱해 age를 계산.
- **채택:** `datetime.fromisoformat` 방어적 처리(파싱 실패·None → 중립 0.5), naive/aware 혼재 시 aware 정규화(6.3 normalizer가 취한 방어와 동일 결). 미래 timestamp(age<0)는 recency_norm=1.0 캡. HN 밀리초 오염(6.3 Defer)은 여기서도 미도달이나 age 음수 방어가 1차 안전망.

### 수집할 기존 파일 — 현재 상태 / 변경 / 보존

- **`api/pipeline/recommender.py`** (변경 — 이 스토리의 전부):
  - `compute_relevance_score`(L22-44): substring. **보존하되 폴백 전용화**(D1).
  - `_signal_embed_text`(L90-98): 현재 `tech+title+summary`. **summary 중심으로 변경**(AC4).
  - `_embed_signal_list`(L101-126): 배치 임베딩. **골격 유지**(_signal_embed_text만 바뀜).
  - `_build_signal_embeddings`(L129-142) / `create_daily_brief_for_user` SELECT(L298-304): **컬럼 확장**(published_at/popularity/source_authority).
  - `_score_signals`(L145-254): **핵심 재작성** — base 코사인 + RAG 블렌드 + 랭킹 피처 + MMR. Memory 체크·RPC·격리·폴백 **로직 보존**.
  - `create_daily_brief_for_user`(L257-401): brief 상태머신·중복 스킵·daily_brief_signals insert **골격 유지**. `scored` 소스가 MMR 순서로 바뀔 뿐.
  - `run_recommender`(L404-479): stuck 정리·사용자 격리·배치 임베딩 **무변경**.
- **`api/pipeline/memory_manager.py`** (보존, 무변경): memory는 `summary`만 임베딩(L73). 6.4는 시그널 query를 **여기에 맞춘다**(대칭화 방향 = 시그널→memory, memory 재임베딩/백필 없음). memory 임베딩 텍스트를 바꾸면 기존 저장 임베딩 전체 백필이 필요하므로 **금지**.
- **`api/pipeline/clustering.py`** (보존, 참고): `_norm`/`_cosine`(L61-73) 시그니처를 recommender 로컬 헬퍼가 따른다(D3). clustering 자체 무변경.
- **`api/pipeline/orchestrator.py`** (보존, 무변경): `run_recommender(signal_ids, client, brief_date, llm)` 호출 시그니처 불변.
- **`api/pipeline/models.py`** (보존, 무변경): RawArticle은 수집 단계 모델 — recommender는 DB `signals` dict를 다룸.
- **`supabase/migrations/`** (무변경): 6.3의 `20260731000000_signals_schema_v2.sql`이 컬럼 이미 추가. **새 마이그레이션 없음.**
- **`match_memories` RPC**(DB 함수): user_id 스코프 강제(5.4). query_embedding 차원(1536) 불변 — `_signal_embed_text`가 텍스트만 바꾸므로 벡터 차원·RPC 계약 무영향.

### 라이브러리 / 버전

- **신규 의존성 없음.** 표준 라이브러리 `math`(코사인), `datetime`(recency), 기존 `LLMProvider.embed_text`(text-embedding-3-small, 1536차원). **numpy·외부 벡터 DB·신규 pip 패키지 금지**(6.2/6.3과 동일 원칙).
- DB: 6.3이 추가한 스칼라 컬럼 읽기만. pgvector는 `match_memories` RPC(기존)만 사용 — 6.4가 새 벡터 저장/인덱스 만들지 않음.
- OpenAI: 임베딩은 `embed_text`(기존 provider 메서드, AD-7). 스코어링 자체는 LLM 생성 호출 없음(임베딩만). Responses API 등 생성 경로 무관.

### 회귀 주의 (반드시 확인)

- **기존 `_score_signals`/콜드스타트 테스트 대량 수정 예상:** substring→코사인 전환으로 `compute_relevance_score` 기대값 테스트(L23-56)·RAG 테스트(L480~)가 mock 임베딩 기반으로 바뀐다. **삭제가 아니라 v2 기대값으로 갱신** — AC별 커버리지 유지.
- **relevance_score 불변식:** `daily_brief_signals.relevance_score`는 `FLOAT NOT NULL`(DB CHECK 없음, migration L198). [0.1,1.0]은 **코드 clamp로만** 보장 — combined·RAG 블렌드·MMR 어느 단계도 이 범위를 벗어나 저장하면 안 됨. 화면(home) 컴포넌트가 0~1 가정 시 회귀.
- **position 계약:** `daily_brief_signals.position`은 1-based(L369 `pos+1`), `idx_daily_brief_signals_brief(daily_brief_id, position)` 인덱스 존재. MMR 순서가 position에 그대로 매핑 — 중복/누락 position 금지(enumerate 유지).
- **온디맨드 경로:** `run_ondemand_brief`는 collect/normalize를 건너뛰고 recommender 이후만(AD-15) — `create_daily_brief_for_user`를 직접 호출하는지 확인하고 두 경로 다 테스트. Signals SELECT 확장이 온디맨드에도 적용돼야 함.
- **임베딩 1회 불변(A-2):** 시그널당 `embed_text` 1회, 사용자 재임베딩 금지. 프로필 임베딩은 사용자당 1회 추가(콜드스타트 base용) — 배치 N사용자면 N회(프로필은 작아 저비용). 시그널을 사용자마다 재임베딩하지 말 것.
- **결정론:** 모든 정렬·MMR tie-break에 `signal_id`를 최종 키로. dict 순회 순서·set 비결정성이 순위에 새지 않게(6.2 리뷰 파인딩 "결정론적 정렬"과 동일 주의).
- `cd api && pytest -q` → 현재 **202 passed**. 6.4 후 그대로 통과 + 신규.

### 파일 구조 (수정)

```
api/pipeline/recommender.py            (수정 — 핵심: 코사인 콜드스타트 + 랭킹 피처 + MMR + RAG 대칭 + SELECT 확장)
api/tests/test_recommender_pipeline.py (수정 — v2 스코어링 테스트, 오매칭 회귀, 불변식/결정론, MMR, RAG 대칭, AD-5 폴백)
```
> 마이그레이션·models·clustering·normalizer·orchestrator·memory_manager **무변경**. 단일 모듈(recommender) + 그 테스트에 국한 — 6.3 대비 표면적이 작다(스키마 이미 준비됨).

### 테스트 표준

- **프레임워크:** pytest 8.3.4, `pytest.ini`(`testpaths=tests`, `asyncio_mode=auto`), `test_*.py`, `api/tests/`.
- **오프라인 원칙(절대):** 실 네트워크·실 OpenAI·실 DB 금지. Supabase `MagicMock`(기존 `_rag_score_client`·`_make_mock_client` 패턴), llm `MagicMock`(`embed_text.return_value`/`side_effect`로 벡터 주입). 코사인 검증은 알려진 벡터(예: 직교 `[1,0,…]`/`[0,1,…]`, 동일 벡터)로 결정적.
- **커버리지 대상:** (1) 콜드스타트 코사인 순위, (2) **go→google 오매칭 회귀**, (3) [0.1,1.0] 불변식 + 결정론 tie-break, (4) 최신성/인기/권위 가점 + None 중립, (5) MMR 분산 + 임베딩 없는 시그널 생존, (6) `_signal_embed_text` summary 대칭 + RAG 경로 무회귀, (7) AD-5 폴백(llm None/임베딩 실패/RPC 실패), (8) 전체 회귀 202 passed.

### Project Structure Notes

- 백엔드는 `api/` 루트 실행(PYTHONPATH=`api`, import `pipeline.*`·`core.*`). 로컬 실행/DB 접속은 [[local-run-setup]] 참고.
- 6.4는 **마이그레이션 불필요**(6.3이 스키마 준비). 실 DB 검증이 필요하면 [[seed-test-user-supabase]] 패턴으로 시드 후 배치 실행 — 단, 단위 테스트는 전부 오프라인 mock.
- 이 스토리는 [[epic-6-real-data-ingestion]]의 4번째 단계(6.1 수집·6.2 클러스터·6.3 스키마/저장·**6.4 랭킹**·6.5 측정). 6.4 이후 6.5가 이 랭킹의 효과를 held-out engagement로 측정한다.
- 충돌/변이: 없음. 단일 모듈 로직 교체 + 테스트. 스키마·다른 파이프라인 단계 무영향.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.4 Recommender v2 (AC: 콜드스타트 임베딩·MMR·최신성·RAG 대칭), #Epic 6 스파이크 근거·FR-8.4]
- [Source: _bmad-output/implementation-artifacts/6-3-normalize-v2-and-signal-스키마-확장.md#Dev Notes recommender.py "6.4에서 select에 published_at/popularity/source_authority 추가"(L195), #스코프 경계(L64-66), #source_authority 등급 D3(L178-179)]
- [Source: api/pipeline/recommender.py L22-44 (compute_relevance_score substring — 폴백화), L90-98 (_signal_embed_text — summary 대칭화), L129-142·L298-304 (SELECT 확장), L145-254 (_score_signals — v2 재작성), L15-19 (_RAG_WEIGHT/_RAG_MATCH_COUNT)]
- [Source: api/pipeline/clustering.py L57-73 (_norm/_cosine 순수 파이썬 패턴 — recommender 로컬 헬퍼 시그니처), L9 (numpy 금지 원칙)]
- [Source: api/pipeline/memory_manager.py L69-79 (memory summary만 임베딩 — 대칭 기준, 백필 금지)]
- [Source: api/pipeline/llm/base.py (LLMProvider.embed_text → list[float] 1536차원, AD-7)]
- [Source: supabase/migrations/20260723000000_initial_schema.sql L195-198 (daily_brief_signals.relevance_score FLOAT NOT NULL, position), 20260731000000_signals_schema_v2.sql (published_at/popularity/source_authority 컬럼 — 6.4가 소비)]
- [Source: api/tests/test_recommender_pipeline.py L23-56 (compute_relevance_score 테스트 — v2 갱신), L478-541+ (_rag_score_client·_SIG·_EMB·_score_signals 테스트 — 확장 기준)]
- [Source: architecture/architecture-decision-os-2026-07-21/ARCHITECTURE-SPINE.md#AD-2/AD-6 (pgvector 전용·외부 벡터DB 금지, L23-26·188-189), #AD-15 (Batch First + On-demand, L그래프), #AD-16 (다출처 묶음)]

### 🟡 오너 확인이 필요한 결정 (dev-story 착수 전 권장)

CLAUDE.md 규칙(추천안·이유·사이드이펙트 표기)에 따라 세 가지를 짚습니다. **세 개 모두 "추천안대로" 진행해도 무방하며**, dev-story는 아래 추천 방향으로 작성되어 있습니다.

- **D1 — substring 폴백 유지 vs 완전 삭제 (추천: 폴백 전용 보존)**
  - **추천 이유:** `llm`이 없는 경로(단위 테스트 다수·임베딩 배치 실패)에서 substring을 안전망으로 남기면 AD-5(안전 저하)를 지키면서, 정상 경로 오매칭("go→google")은 사라진다. AC1의 취지(정상 경로에서 substring 제거)를 충족하면서 저하 모드에서 순위가 flat 0.1로 뭉개지지 않는다.
  - **사이드이펙트:** 죽은 것처럼 보이는 함수가 코드에 남아(주석으로 "fallback only" 명시 필요), 리뷰어가 "왜 안 지웠나" 물을 수 있음. 완전 삭제를 택하면 `llm None` 경로가 전부 flat 0.1 → 그 경로 순위 품질 저하(단, 실사용은 항상 llm 주입이라 영향 작음).

- **D2 — RAG weight 처리 (추천: 값 유지 + 근거 주석 갱신, 정규화 리팩터는 6.5로 연기)**
  - **추천 이유:** 최적 weight는 데이터(held-out engagement)로 정해야 하는데 그건 6.5 스코프다. 지금 임의로 크게 바꾸면 근거 없는 튜닝. 스케일 정합성(코사인 base로 전환)만 주석에 남기고 값은 유지하는 게 안전.
  - **사이드이펙트:** base가 코사인(0.1~0.6 밀집)으로 바뀌어 `+0.5·top_sim`의 상대 영향이 v1보다 커질 수 있음 → Memory 사용자에서 RAG가 과하게 지배할 여지. 대안(정규화 블렌드 `(1-w)·cold + w·sim`)은 더 균형적이나 기존 테스트·행동을 크게 흔들어 6.4 리스크를 키움. 6.5 측정 후 리팩터 권장.

- **D3 — 코사인 헬퍼 위치 (추천: recommender 로컬 정의)**
  - **추천 이유:** 중복이 ~6줄뿐이라 공용 모듈 신설·clustering 리팩터(회귀 위험)보다 로컬 정의가 이득. 6.3이 github.py에서 취한 "과설계 회피"와 같은 판단.
  - **사이드이펙트:** `clustering._cosine`과 `recommender._cosine`이 각자 존재(경미한 DRY 위반). 향후 코사인 수정 시 두 곳을 봐야 함 — 규모 커지면 `pipeline/vector_utils.py`로 추출 권장(그때 clustering도 함께).

### Review Findings

_Code review 2026-07-29 (3-layer: Blind Hunter · Edge Case Hunter · Acceptance Auditor). AC1~6·D1~D5·스코프 경계 전부 준수 확인됨. 아래는 잔여 파인딩._

- [x] [Review][Decision→Dismissed] MMR 임베딩 없는 시그널의 다양성 페널티 0 비대칭 — `_mmr_rerank`에서 임베딩 실패 시그널은 `max_sim=0`(페널티 0)이라, 같은 combined면 중복 페널티를 받은 임베딩 시그널보다 위로 올라올 수 있음. **오너 결정(2026-07-29): 그대로 유지** — 임베딩 실패는 드문 저하 경로이고 AC3 핵심("탈락 안 함")은 지켜짐, 랭킹 미세조정은 6.5(측정 기반) 스코프. [recommender.py:150-154]
- [x] [Review][Patch] `_as_float` NaN/inf 미방어 — popularity가 NaN이면 `_popularity_norm`→`combined`가 NaN으로 오염되어 정렬·MMR 비교 교란 및 `relevance_score`에 NaN 기록(프런트 0~1 가정 위반). **적용됨: `_as_float`에 `math.isnan/isinf`→0.0 가드.** [recommender.py:58-66]
- [x] [Review][Patch] `_RECENCY_HALFLIFE_DAYS` 0 나눗셈 잠재 — 6.5 튜닝으로 값 편집이 예고된 상수인데 0 방어 없어 `age_days / 0` → ZeroDivisionError. **적용됨: `halflife = _RECENCY_HALFLIFE_DAYS or 1` 가드.** [recommender.py:89-90]
- [x] [Review][Defer] `_clamp` 상한(1.0) 도달 불가 + 테스트 명명 불일치 — 가중치 합=1.0이라 combined는 항상 ≤1.0, 상한 clamp는 dead. `test_score_signals_clamped_to_one`이 이름과 달리 상한 경로를 실제 검증 못 함(하한 0.1만 유효). [recommender.py:41-43, test_recommender_pipeline.py:530] — deferred, 테스트 품질(불변식 자체는 안전)
- [x] [Review][Defer] signal↔memory 임베딩 텍스트 대칭이 파일 간 암묵 계약 — `_signal_embed_text`(summary 중심)와 `memory_manager`의 summary 임베딩이 대칭이어야 AC4 성립하나, 강제하는 공유 헬퍼·계약 테스트 없음. 한쪽이 텍스트 구성 바꿔도 무경고로 어긋남. [recommender.py:242-249] — deferred, 유지보수성(현재 memory_manager.py:73 summary-only로 정합)
- [x] [Review][Defer] `_recency_norm`이 date-only brief_date를 자정으로 해석 — 당일 게시 시그널이 age<0→recency 1.0으로 뭉개져 당일 내 최신성 변별력 소실(recency weight 0.15라 영향 경미, 최신 우대라 일부 의도적). [recommender.py:76-88] — deferred, 경미(6.5 튜닝 시 함께 검토)

## Change Log

- 2026-07-29: Code review(3-layer) — AC1~6·D1~D5·스코프 경계 전부 준수 확인. 파인딩: decision 1(MMR 임베딩없음 비대칭)·patch 2(_as_float NaN 방어·halflife 0나눗셈)·defer 3·dismiss 10(brief_date 파싱붕괴/코사인 차원불일치 등은 상위 검증·단일모델로 도달불가).
- 2026-07-29: Story 6.4 컨텍스트 생성(create-story) — 콜드스타트 임베딩 코사인 전환 + 랭킹 피처(최신성·인기·권위) 결합 + MMR 다양성 + Memory RAG 임베딩 대칭화 설계. 6.3이 준비한 스키마 컬럼 소비. Status → ready-for-dev.
- 2026-07-29: Story 6.4 구현(dev-story) — recommender.py v2 개편(코사인 콜드스타트 + 랭킹 피처 + MMR + RAG summary 대칭 + SELECT 확장), substring은 v1 폴백 격리(D1), `_RAG_WEIGHT=0.5` 유지+주석 갱신(D2), 코사인 헬퍼 로컬 정의(D3). 신규 19 테스트 추가 + 기존 8 테스트 v2 기대값 갱신. `pytest -q` 221 passed(202 baseline + 19). Status → review.
