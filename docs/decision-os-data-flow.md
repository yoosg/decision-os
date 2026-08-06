# Decision OS — 수집부터 메모리 개인화까지 전체 흐름

> 시스템은 **두 개의 층**으로 돈다.
> **① 수집 파이프라인** (모두에게 동일한 콘텐츠를 만드는 배치) →
> **② 개인화 되먹임 루프** (사용자 행동으로 각자의 추천을 다듬는 순환).
> ①의 결과물(Signal)을 ②가 소비하고, ②의 결과물(Memory)이 다시 ①의 마지막 단계(추천)로 되먹여진다.

넷플릭스 비유: ①은 "새 영화를 사와 카탈로그에 채우는 일"(누구에게나 동일), ②는 "내가 뭘 보고 평가했는지로 내 홈 화면이 바뀌는 일"(사람마다 다름).

---

## 한눈에 보는 전체 흐름

```
[① 수집 파이프라인 — 매일 06:00 KST 배치]
 수집(Collect) → 클러스터·필터(Cluster&Filter) → 정규화(Normalize)
   → 시그널 생성(Build Signals) → 리뷰 생성(Review) → 추천(Recommender) → Daily Brief
                                                                  │
                                                                  ▼
[② 개인화 되먹임 루프 — 사용자 행동 기반, 상시]
 Daily Brief(브리핑) → Review(리뷰) → Decision(결정) → Learning Path(학습)
   → Outcome(결과) → Memory(메모리 추출·임베딩)
                                        │
                                        └──▶ 다음 Recommender가 Memory RAG로 개인화 ──▶ 브리핑
```

---

## ① 수집 파이프라인 (배치, 06:00 KST)

`api/pipeline/orchestrator.py::run_daily_pipeline`. 모든 사용자 공통으로 그날의 재료(Signal)를 만든다.

| 단계 | 하는 일 | 코드 | LLM/외부 |
|---|---|---|---|
| 1. 수집(Collect) | 외부 소스에서 원문 기사 긁어오기. 소스: **GitHub, HackerNews, RSS(공식 블로그 등)**. `collector_mode=stub`면 하드코딩 5건 폴백 | `pipeline/collector/aggregator.py` (`run_collectors`) | HTTP |
| 2. 클러스터·필터(Cluster&Filter) | 같은 주제 기사 묶기(임베딩 유사도) + 관련성/세이프티 필터. 결과 = 토픽 클러스터 | `pipeline/clustering.py` | 임베딩 |
| 3. 정규화(Normalize) | 클러스터 → `signals`(status=`raw`) + `signal_sources` 저장. `technology_name+signal_date` 중복은 무시(재실행 안전) | `pipeline/normalizer.py` | — |
| 4. 시그널 생성(Build Signals) | `raw` 시그널마다 **제목·요약을 LLM으로 생성**, status=`processed`로 승격 | `pipeline/signal_builder.py` | **LLM 호출** |
| 5. 리뷰 생성(Review) | `processed` 시그널마다 **모든 `ai_research` 프로젝트**에 대해 13섹션 Research Review 생성 | `pipeline/reviewer.py` | **LLM 호출** |
| 6. 추천(Recommender) | onboarding 완료 사용자 전원에게 Daily Brief 생성 + 시그널 랭킹(개인화) | `pipeline/recommender.py` | 임베딩 |

- 산출물: `signals`, `signal_sources`, `reviews`, `daily_briefs`, `daily_brief_signals`.
- ⚠️ 4·5단계는 LLM 유료 호출. 크레딧/한도가 막히면 시그널이 `raw`에 멈추고 브리핑이 안 만들어진다.
- 안전 저하(safe-degrade): 임베딩 실패 등은 예외를 막고 **콜드 스타트**로 폴백해 브리핑 생성은 이어진다.

---

## Daily Brief 노출 (사용자 진입점)

- 홈 화면은 `daily_briefs`에서 오늘 날짜·해당 사용자의 브리핑을 조회한다.
- 상태 흐름: `pending/processing`(생성 중) → `completed`(시그널 카드 표시) / `failed`.
- 브리핑이 없으면 화면은 "생성 중" 상태로 폴링(약 2분). 즉 **06:00 배치가 먼저 만들어 둬야** 정상 노출된다.

---

## ② 개인화 되먹임 루프 (사용자 행동 기반)

브리핑에서 시작해 사용자의 결정·결과가 Memory로 쌓이고, 그 Memory가 다음 추천을 개인화한다.

| 노드 | 트리거 | 하는 일 | 코드 |
|---|---|---|---|
| 브리핑(Daily Brief) | 앱 진입 | 추천된 시그널 카드 목록 노출 | 홈 화면 |
| 리뷰(Review) | 시그널 카드 탭 | 해당 시그널의 Research Review 표시(배치에서 미리 생성됨) | `routers/reviews.py` |
| **결정(Decision)** | 사용자 선택 | **지금 학습 / 보관(queue) / 스킵** 중 택1 기록 | `routers/decisions.py` |
| 학습(Learning Path) | "지금 학습" 결정 | 5종 리소스(공식문서·핵심자료·GitHub·실습·적용아이디어) 학습 경로 생성 | `routers/learning_paths.py` |
| **결과(Outcome)** | 학습 후 입력 | "유용했나? 실제 학습 시간?" 등 결과 기록 | `routers/outcomes.py` |
| 메모리(Memory) | **Outcome 제출이 트리거** | 아래 참조 | `pipeline/memory_manager.py` |

### 메모리 추출 (되먹임의 연료)

- Outcome이 제출되면 백그라운드로 `run_memory_manager_from_outcome` 실행.
- **Signal + Review + Decision + Outcome** 4개를 엮은 체인을 LLM에 넘겨 재사용 가능한 Memory를 추출한다.
  - `memory_type`: `preference / skill / project / decision_history / outcome_history` 중 하나
  - `summary`: 1~2문장 한국어 요약
- 추출된 Memory의 **`summary`를 임베딩**해 `memories`(벡터 1536차원) 테이블에 저장.
- 실패해도 예외 전파 없이 로그만 남긴다(개인화는 부가 기능, 본류를 막지 않음).

### 되먹임: Memory → 다음 추천 개인화

`recommender.py::_score_signals`에서:

1. **기본 = 콜드 스타트**: 사용자 프로필 임베딩 ↔ 시그널 임베딩 코사인 유사도로 점수.
2. **Memory 보유 시 = RAG 승격**: `match_memories` RPC로 내 과거 Memory 중 이 시그널과 가까운 것을 찾아, 그 유사도를 점수에 **블렌딩** → `relevance_score` 조정 → 노출 순위 변화.
3. Memory 없음 / LLM 없음 / RAG 실패 → **콜드 스타트로 폴백**(개인화만 꺼지고 브리핑은 정상).

**핵심:** 이 루프는 "무엇이 수집되는가"를 바꾸지 않는다. 이미 수집된 시그널 중 **너에게 무엇을·어떤 순서로 보여줄지(선별·랭킹)** 만 개인화한다. "수집 자체의 고도화"는 ①의 앞단(수집원 큐레이션·클러스터링 품질)이며 별개 축이다.

---

## 스케줄 / 트리거 요약

| 시각(KST) | 잡 | 내용 | 코드 |
|---|---|---|---|
| 06:00 | `daily_pipeline` | ① 수집 파이프라인 전체 실행 | `orchestrator.run_daily_pipeline` |
| 09:00 | `daily_push` | 브리핑 준비 FCM 푸시 | `orchestrator.run_push_job` |
| 10:00 | `outcome_reminder` | 결과(Outcome) 입력 리마인더 | `orchestrator.run_outcome_reminder_job_entry` |
| 20:00 | `queue_reminder` | 보관함(Queue Today) 학습 리마인더 | `orchestrator.run_queue_reminder_job_entry` |
| 상시 | on-demand | 특정 사용자 브리핑 재생성(추천 이후 단계만) | `orchestrator.run_ondemand_brief` (`POST /daily-briefs/trigger`) |

- 스케줄러는 서버(FastAPI) 내부 APScheduler. 서버가 06:00에 떠 있지 않으면 그날 배치는 누락된다(놓친 잡 소급 실행 안 함).

---

## 데이터 산출물(주요 테이블)

- `signals`, `signal_sources` — 수집·정규화 결과(재료)
- `reviews` — 시그널×프로젝트별 13섹션 리뷰
- `daily_briefs`, `daily_brief_signals` — 사용자별 그날의 브리핑과 노출 시그널·점수
- `decisions`, `learning_paths`, `outcomes` — 사용자 행동 기록
- `memories`(vector 1536) — 개인화 되먹임의 연료

---

## 한 줄 정리

**수집(공통 재료 생산) → 브리핑 노출 → 사용자의 결정·학습·결과 → 메모리(개인화 연료) → 다음 추천에 되먹임.**
수집 파이프라인이 "무엇을 만들지"를, 개인화 루프가 "누구에게 무엇을 먼저 보여줄지"를 담당한다.
