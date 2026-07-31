# Decision OS — 동작 원리 (How It Works)

> "각 기능이 실제로 어떻게 동작하는가"를 백엔드 코드(`api/pipeline/`) 기준으로 정리한 문서.
> 데이터 구조·테이블 역할은 [`IMPLEMENTATION-STATUS.md`](./IMPLEMENTATION-STATUS.md) 참고.
>
> 최종 갱신: 2026-07-30

전체를 관통하는 비유는 **자동화된 신문사 편집국**이다 — 기자가 기사를 모으고 → 편집자가 중복을 정리하고 → 논설위원이 독자별 해설을 쓰고 → 1면을 배치하고 → 독자 반응을 기억해 다음 날 편집에 반영한다.

---

## 0. 큰 틀 · 공통 패턴

### 실행 모드 2가지
- **배치 파이프라인** — 매일 06:00 KST, `orchestrator.run_daily_pipeline()`. 수집→브리핑까지 한 번에. 09:00 KST FCM 푸시.
- **이벤트 기반** — 사용자 액션 시 FastAPI `BackgroundTask`로 처리: 온디맨드 리뷰, 학습 자료 생성, 메모리 저장, 온디맨드 브리핑.

### 어디서나 반복되는 패턴 3가지
1. **비동기 상태머신** — `pending → processing → completed | failed`. `reviews`·`learning_paths`·`daily_briefs` 모두 동일. 무거운 LLM 작업이라 "접수증 먼저 주고 백그라운드에서 처리".
2. **안전 저하 (safe-degrade, AD-5)** — 한 소스/한 항목이 실패해도 전체가 죽지 않고 폴백. LLM이 없으면 규칙 기반으로 내려앉는다.
3. **LLM은 교체 가능한 부품** (`LLMProvider` 추상화) + **임베딩은 배치당 1회만** 계산해 재사용.

---

## 1. 시그널 수집 → 브리핑 저장

배치 5단계 — `api/pipeline/orchestrator.py:49-89`

### 1) 수집 · `collector/aggregator.py`
- RSS·GitHub·HackerNews 어댑터를 **각각 격리 호출**(한 소스가 죽어도 나머지 계속, `try/except`).
- 결과를 합쳐 **URL/제목 완전일치 중복 제거** → `RawArticle` 목록.
- 설정 `collector_mode="stub"`이면 `StubCollector`(가짜 데이터)로 대체.

### 2) 클러스터링 & 필터 · `clustering.py` (품질 핵심)
- 각 기사(제목+기술명)를 **임베딩**(text-embedding-3-small).
- **세이프티 필터**(제목 블록리스트) → **관련성 필터**("AI/개발 기술" 앵커 문장과의 코사인 유사도가 임계 미만이면 도메인 밖으로 탈락).
- **greedy 코사인 클러스터링** — 의미가 비슷한 기사끼리 묶음 (예: 같은 GPT 출시를 다룬 기사 5개 → 토픽 1개).
- 클러스터마다 **고유 라벨**(`technology_name`) + **결정론적 `cluster_key`**(멤버 URL 해시) 부여 → 재실행해도 같은 결과.
- LLM 없으면 통째로 pass-through(안전 저하).

### 3) 정규화 · `normalizer.py`
- 클러스터(=토픽) 단위로 `signals`에 **upsert** (`technology_name + signal_date` UNIQUE, `status='raw'`).
- 원문 링크들은 `signal_sources`에 저장 (1 signal ↔ N sources).
- 랭킹용 집계 메타 기록: `published_at`=멤버 중 최신, `popularity`=합, `source_authority`=최고 등급(공식블로그 4 > github 3 > hn 2 > reddit/youtube 1 > other 0).

### 4) 시그널 빌더 · `signal_builder.py`
- raw 시그널마다 LLM에 기술명+출처를 주고 **제목·요약 생성** → `status='processed'`.
- LLM 호출이 원문 수가 아니라 **토픽 수**에 비례 = 비용 절감.

### 5) 추천 + 브리핑 저장 · `recommender.py`
- 아래 [3. 브리핑 저장](#3-브리핑-저장--추천-점수-계산)에서 상세. 결과를 `daily_briefs` + `daily_brief_signals`에 저장. 이후 09:00 KST FCM 푸시.

> **온디맨드 브리핑** (`run_ondemand_brief`) — 신규가입/프로필변경/브리핑 실패/재요청 시. **이미 만들어진 processed 시그널로 추천 단계만** 실행 → 새 유저가 "생성 중"에 갇히지 않게.

---

## 2. 리뷰를 어떻게 구성하나 · `reviewer.py`

**핵심: 같은 시그널이라도 사용자마다 프로필에 맞춘 개인화 리뷰가 따로 생성된다.**
`review_all_for_signal`이 processed 시그널 하나에 대해 **모든 ai_research 프로젝트(=사용자)** 를 순회한다.

각 리뷰 — `_execute_review_pipeline`:
1. `reviews` INSERT(pending) → processing 전이.
2. 입력 수집: signal + signal_sources + **그 사용자 프로필**(role/tech_stack/interests/experience).
3. **`context_snapshot` 저장** — JSONB 봉투 `{schema_version, review_type:"research", payload:{signal, sources, user_profile}}`. "이 리뷰를 만들 때 어떤 입력을 썼는가"의 스냅샷(재현·감사용; 나중에 시그널이 바뀌어도 당시 기록 유지).
4. LLM 호출 → **13개 필수 섹션**(한 줄 정의, honest_box 등) 파싱·검증.
5. `result`에 JSONB 봉투로 저장, completed 전이.

이 JSONB 봉투 형식이 "플레이북 무관 공통 테이블"의 어댑터다 — 보험 리뷰도 payload만 다르고 껍데기는 동일.

> **온디맨드 리뷰** (`run_review_from_pending`) — 사용자가 특정 시그널 리뷰를 즉석 요청하면 pending 생성 후 동일 파이프라인을 BackgroundTask로 실행.

---

## 3. 브리핑 저장 · 추천 점수 계산 · `recommender.py`

사용자별로 오늘의 processed 시그널 후보를 점수화한다 — `_score_signals`.

**점수 조립 순서:**
1. **base 관련도** = 코사인(프로필 임베딩, 시그널 임베딩) [v2]. LLM 없으면 substring 키워드 매칭 폴백.
   - 프로필(tech_stack+interests)은 사용자당 1회, 시그널 summary는 배치당 1회 임베딩(재사용).
2. **Memory RAG 블렌드** ⭐ — 사용자에게 memory가 있으면, pgvector RPC **`match_memories`**(시그널 임베딩 ↔ 그 사용자 기억들)로 **가장 가까운 기억 유사도(top_sim)** 를 구해:
   `blended = clamp(base + 0.5 × top_sim, 0.1, 1.0)`
   → "이 시그널이 **과거에 내가 유용하다고 남긴 기억과 의미적으로 가까우면** 가점".
3. **랭킹 피처 결합**: `combined = 0.70×관련도 + 0.15×최신성(반감기 7일) + 0.10×인기 + 0.05×권위`.
4. **MMR 재랭킹**(λ=0.7): 관련도가 높으면서 서로 겹치지 않게(다양성) 재정렬.

**저장** — `create_daily_brief_for_user`:
- `daily_briefs` INSERT(pending → processing → completed).
- `daily_brief_signals`에 각 시그널의 `relevance_score`(=combined), `position`(=순위) 저장.
- 동시에 `engagement_events`에 impression을 `variant`(rag/coldstart)로 남김(효과 측정용, Epic 6.5).
- 홈 화면은 이 `daily_brief_signals`를 `position` 순으로 읽어 표시.

---

## 4. 학습 자료를 어떻게 만드나 · `coach.py`

**트리거**: 사용자가 리뷰를 보고 **"지금 학습"** → `decisions(choice=learn_now)` 생성 → `POST /learning-paths/trigger`가 `learning_paths` pending 생성 후 BackgroundTask (`routers/learning_paths.py`).

파이프라인 — `_execute_learning_path_pipeline`:
1. pending → processing.
2. 체인 조회: signal+sources, 그리고 **decision → review → project → user_profile**(role/tech_stack/**project_goal**/experience).
3. LLM 호출(`generate_learning_path`) → **resources 정확히 5개**, 정해진 type 순서 검증.
4. `resources` JSONB로 저장, completed.

프론트는 이 resources를 학습 카드로 렌더하고, 외부 링크를 열고 돌아오면(`visibilitychange`) "결과 기록"으로 유도한다.

---

## 5. 메모리에 어떻게 저장하나 · `memory_manager.py`

**트리거**: 사용자가 **결과(Outcome) 기록** → `outcomes` INSERT 성공 **직후** BackgroundTask.

`_execute_memory_extraction`:
1. **Decision Loop 체인 전체 조회**: outcome → decision → review(result) → project(user_id) → signal(technology_name). 즉 "무슨 기술을(signal) / 어떻게 결정하고(choice·memo) / 실제 결과가 어땠는지(status·useful·memo)"를 한 세트로.
2. LLM(`extract_memory`)에 이 맥락을 주면 → `{memory_type, summary}` **한 줄 요약** 생성 (예: "이 사용자는 RAG 실무 적용에 관심이 높고 LangGraph를 유용하게 사용함").
3. summary를 **임베딩(vector)** → `memories`에 `{user_id, memory_type, summary, embedding, source_decision_id}` INSERT.
4. 실패해도 예외를 던지지 않고 로그만 남긴다(메모리는 부가 기능 — 없어도 앱은 동작).

포인트: 원본 이력(reviews/decisions/outcomes)을 통째로 복사하지 않고 **"요약 + 벡터"만** 남긴다(장기 맥락 압축, AD-7).

---

## 6. 메모리를 그 뒤에 어떻게 사용하나 · 다시 `recommender.py`

**다음 브리핑을 만들 때** 개인화 점수에 녹아든다([3번 2단계](#3-브리핑-저장--추천-점수-계산)의 Memory RAG 블렌드).

- pgvector RPC `match_memories(query_embedding=시그널 임베딩, match_user_id, match_count)`가 그 사용자 기억 중 코사인 최근접 유사도를 반환.
- 시그널이 "내가 과거 유용하다고 남긴 기억"과 의미적으로 가까우면 점수 가산 → 개인화 강화.
- 적용 여부는 `variant`(rag/coldstart)로 로깅되어 held-out engagement로 가중치를 튜닝한다(Epic 6.5).

### 닫힌 루프

```
결정(decision) + 결과(outcome) ──► 기억(memory, 벡터)
        ▲                                    │
        │                                    ▼
   다음 브리핑 추천에 가점 ◄──── match_memories(RAG)
```

과거 행동이 다음 추천을 개선하고, 그 효과가 rag/coldstart로 측정되어 가중치 튜닝으로 이어진다.

---

## 부록 · 파일 레퍼런스

| 단계 | 파일 | 진입 함수 |
|---|---|---|
| 배치 오케스트레이션 | `api/pipeline/orchestrator.py` | `run_daily_pipeline` / `run_ondemand_brief` / `run_push_job` |
| 수집 | `api/pipeline/collector/aggregator.py` | `run_collectors` |
| 클러스터링·필터 | `api/pipeline/clustering.py` | `cluster_and_filter` |
| 정규화 | `api/pipeline/normalizer.py` | `normalize` |
| 시그널 빌더 | `api/pipeline/signal_builder.py` | `build_signals` |
| 리뷰 | `api/pipeline/reviewer.py` | `review_all_for_signal` / `_execute_review_pipeline` |
| 추천·브리핑 | `api/pipeline/recommender.py` | `run_recommender` / `create_daily_brief_for_user` / `_score_signals` |
| 학습 자료 | `api/pipeline/coach.py` | `_execute_learning_path_pipeline` |
| 메모리 저장 | `api/pipeline/memory_manager.py` | `_execute_memory_extraction` |
| LLM 추상화 | `api/pipeline/llm/` | `LLMProvider` / `OpenAIProvider` |
| 참여 로깅 | `api/pipeline/engagement.py` | `log_engagement_bulk` |
