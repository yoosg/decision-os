---
baseline_commit: NO_VCS
---

# Story 6.2: 의미 클러스터링 & 관련성/세이프티 필터

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

개발자로서,
수집된 기사를 **키워드 휴리스틱이 아니라 임베딩 의미 유사도로 클러스터링**하고, 시그널 생성 이전에 무관/유해 기사를 걸러내고 싶다,
그래서 하나의 시그널이 토픽 단위로 일관되게 묶이고(다중 출처), 노이즈가 배제되며, LLM 호출 수가 원문 수가 아니라 토픽 수에 비례한다.

> **🍎 프론트엔드 비유 (오너용):** 6.1이 "여러 뉴스 사이트에서 기사 30개를 긁어온" 단계라면, 6.2는 **비슷한 기사끼리 폴더로 묶고(클러스터링) + 광고·스팸을 휴지통으로 버리는(필터)** 단계다.
> - 지금(6.1)은 제목에 "Claude"라는 **글자**가 들어있으면 같은 폴더에 넣는다 → "storage"에 "RAG"가 우연히 들어있어서 엉뚱하게 묶이고, 아무 키워드도 안 걸리면 15개를 죄다 "General AI"라는 잡동사니 폴더 하나에 던져 넣는다.
> - 6.2는 **기사의 "의미"를 숫자 벡터(임베딩)로 바꾼 뒤, 벡터가 서로 가까운 기사끼리** 같은 폴더에 넣는다. "google"이라는 글자 없이도 "구글이 새 모델을 냈다"는 두 기사를 같은 토픽으로 인식한다. (검색창에 오타를 내도 비슷한 결과를 찾아주는 그 원리와 같다.)
> - 그리고 이 무거운 "요약 AI 호출"(SignalBuilder)을 **폴더 개수만큼만** 부르게 만든다 — 기사 30개마다 30번 부르는 게 아니라, 토픽 8개면 8번. 비용이 확 줄어든다.

## Acceptance Criteria

**AC1 — 의미 임베딩 클러스터링 (FR-8.2)**
- **Given** 6.1 수집기가 반환한(또는 stub) exact-dedup된 `list[RawArticle]`이 있을 때
- **When** 클러스터링을 수행하면
- **Then** 각 기사를 `text-embedding-3-small`(1536차원, `settings.openai_embedding_model` 재사용)로 임베딩한다
- **And** 임베딩 간 **코사인 유사도가 임계치(`cluster_similarity_threshold`) 이상**인 기사들은 1개 클러스터로 묶인다 (스파이크 검증 케이스: **Claude 암호취약점 공식 블로그 + 동일 주제 HN 글 → 반드시 1개 클러스터**)
- **And** 서로 무관한 기사는 별개 클러스터로 남는다
- **And** **외부 벡터 DB를 도입하지 않는다** (AD-2/AD-6). 임베딩은 기존 `LLMProvider.embed_text`로 생성하고, pre-persist(정규화 이전) 기사에 대한 유사도 계산은 **인프로세스**로 수행한다 (근거·주의는 Dev Notes "설계 결정 D1" 참조)

**AC2 — 관련성/세이프티 필터 (FR-8.3)**
- **Given** 시그널 생성(=normalize) 이전 단계에서
- **When** 관련성/세이프티 필터를 적용하면
- **Then** **AI/개발 기술 도메인과 무관한 기사**(스파이크: "smart rings" 등)와 **유해 기사**는 제외되어 하위 파이프라인으로 넘어가지 않는다
- **And** 관련성 판정은 **도메인 앵커 임베딩과의 코사인 유사도**(`relevance_min_similarity` 미만이면 무관)로 수행한다 — 클러스터링용으로 이미 계산한 임베딩을 재사용(임베딩 1패스)
- **And** **제외된 각 기사의 판정 근거가 로깅된다** (`event="article_filtered"`, `reason="off_domain" | "unsafe"`, `url`, 유사도 점수)

**AC3 — 파이프라인 순서: 필터·클러스터가 SignalBuilder(LLM) 이전 (NFR-2, AD-15)**
- **Given** `run_daily_pipeline`이 실행될 때
- **When** collect 이후 단계를 보면
- **Then** 순서가 **Collect → [6.2 필터 → 클러스터] → Normalize → SignalBuilder(LLM) → …** 가 된다
- **And** 결과적으로 **생성되는 signal 수 = 클러스터 수**이고, `build_signals`(LLM)의 호출 수가 **원문 기사 수가 아니라 클러스터(토픽) 수에 비례**한다 (스파이크: 원문 30건이 15개 무의미 시그널로 뭉개지던 문제 → 의미 토픽 수만큼만 시그널·LLM 호출)
- **And** 클러스터링 산출물은 **기존 `normalize()`를 수정하지 않고** 그대로 흘러야 한다 (normalize v2·스키마 확장은 **Story 6.3** — 이 스토리는 `normalizer.py`를 변경하지 않는다)

**AC4 — 안전 저하(safe degradation) & 무회귀 (AD-5, AD-15)**
- **Given** LLM/임베딩을 사용할 수 없거나(예: `openai_api_key` 미설정 → `llm=None`) 임베딩 호출이 실패할 때
- **When** 6.2 단계가 실행되면
- **Then** 예외로 배치를 중단시키지 않고, 클러스터링·필터를 건너뛴 **pass-through(6.1 그대로의 `RawArticle` 목록)** 로 안전 저하하여 파이프라인이 계속된다 (recommender의 `llm=None` 폴백과 동일 철학)
- **And** 개별 기사 임베딩 실패는 격리되어 로깅되고, 해당 기사만 영향을 받는다 (전체 중단 금지)
- **And** `settings.collector_mode == "stub"` 및 기존 전체 회귀(`pytest -q`, 현재 179 passed)가 그대로 통과한다

> ⚠️ **스코프 경계 (중요):** 이 스토리는 **임베딩 + 인프로세스 의미 클러스터링 + 관련성/세이프티 필터 + 오케스트레이터 배선**까지만 한다.
> - **하지 말 것:** `signals`/`signal_sources` **스키마 변경·마이그레이션**(`published_at`·인기·cluster_key 컬럼 등 → **6.3**), `normalizer.py` 로직 변경(**6.3 normalize v2**), Recommender 점수식 변경(**6.4**), engagement 로깅/측정(**6.5**), 외부 벡터 DB 도입, DB에 raw 기사 임베딩 영속화.
> - 클러스터 식별을 DB 스키마(cluster_key)로 정식화하는 것은 6.3. 6.2는 **normalize가 이미 하는 `technology_name` 그룹핑을 활용**해 "클러스터 = 고유 라벨"로 흘려보내는 **경량 브리지**만 놓는다 (Dev Notes "설계 결정 D2").

## Tasks / Subtasks

- [x] **Task 1 — 설정 추가** (AC: 1, 2, 4)
  - [x] `core/config.py` `Settings`에 추가:
    - `clustering_enabled: bool = True` — 안전 롤아웃/긴급 차단 토글(끄면 6.1 pass-through)
    - `cluster_similarity_threshold: float = 0.82` — 코사인 유사도 클러스터 병합 임계치(초기값, 튜닝 대상 — Dev Notes "임계치 튜닝" 참조)
    - `relevance_min_similarity: float = 0.20` — 도메인 앵커 유사도 하한(미만이면 off_domain)
  - [x] `.env.example`에 세 항목 주석 추가. `openai_embedding_model`은 **이미 존재 — 재사용**(신규 추가 금지)
  - [x] 값은 상수가 아니라 `settings.`로 참조(하드코딩 금지) — 리뷰 튜닝 용이성

- [x] **Task 2 — 클러스터링/필터 모듈 신규** (AC: 1, 2, 4)
  - [x] `api/pipeline/clustering.py` 신규. 공개 진입점 하나: `cluster_and_filter(articles: list[RawArticle], llm: LLMProvider | None, brief_date: str = "") -> list[RawArticle]`
  - [x] **safe-degrade 가드(맨 앞):** `articles`가 비었거나 `not settings.clustering_enabled` 또는 `llm is None` → 입력을 **그대로 반환**하고 `event="clustering_skipped"`(reason) 로깅 (AC4)
  - [x] **임베딩 1패스:** 각 기사에 대해 `llm.embed_text(_embed_text(a))` 호출. 임베딩 텍스트 = `f"{a.technology_name} {a.title}"`(6.1이 `content`를 안 채움 — 6.3 스코프이므로 title 중심). **개별 실패는 try/except로 격리** → `event="article_embed_failed"`(url, error) 로깅 후 그 기사는 제외 목록이 아니라 **원본 라벨 유지 pass-through 후보**로 처리(전체 중단 금지, AC4)
  - [x] **관련성 필터:** 모듈 로드시 1회 계산하는 **도메인 앵커 임베딩**(고정 문장, Dev Notes "도메인 앵커" 참조)과 각 기사 임베딩의 코사인 유사도가 `relevance_min_similarity` 미만 → 제외, `event="article_filtered", reason="off_domain", url, similarity` 로깅 (AC2)
  - [x] **세이프티 필터:** 경량 블록리스트 휴리스틱(제목 소문자 매칭)으로 유해 기사 제외 → `event="article_filtered", reason="unsafe", url` 로깅. (LLM Moderation API 사용 여부는 열린 결정 — Dev Notes "설계 결정 D3", 기본은 휴리스틱)
  - [x] **클러스터링(인프로세스, pgvector 아님):** 생존 기사들을 코사인 유사도 임계치 기준 **단일 패스 greedy** 로 묶는다 — 각 기사를 이미 만들어진 클러스터의 대표(첫 멤버 또는 running centroid) 중 유사도 ≥ `cluster_similarity_threshold`인 첫 클러스터에 배정, 없으면 새 클러스터 생성. 코사인은 **순수 파이썬**(dot/‖·‖) — numpy 신규 의존성 추가 금지(Dev Notes "코사인 구현")
  - [x] **클러스터 → RawArticle 재라벨(브리지):** 각 클러스터에 **배치 내 고유** `technology_name` 라벨을 부여하고, 클러스터 멤버 전부를 그 라벨로 재생성(`dataclasses.replace(a, technology_name=label)`). 라벨 생성·고유화 규칙은 Dev Notes "설계 결정 D2" 준수(라벨 충돌로 두 클러스터가 normalize에서 1시그널로 합쳐지면 안 됨)
  - [x] `event="clustering_done"`(input=n, filtered_off_domain=x, filtered_unsafe=y, embed_failed=z, cluster_count=k) 로깅. 반환: 재라벨된 `list[RawArticle]`(클러스터당 N개 소스, 모두 동일 고유 라벨)

- [x] **Task 3 — 오케스트레이터 배선** (AC: 3, 4)
  - [x] `api/pipeline/orchestrator.py` `run_daily_pipeline`: collect 직후(`collect_done` 로그 뒤), `normalize` 직전에 `articles = cluster_and_filter(articles, llm, brief_date=brief_date)` 삽입
  - [x] 기존 `llm = OpenAIProvider(...)`를 그대로 재사용(신규 생성 금지). Provider 구성 실패 시 `llm=None`으로 넘겨 pass-through 되도록(현재 orchestrator는 llm 생성 실패를 잡지 않음 — 배치 경로에선 실패 시 전체 try/except가 `pipeline_failed`로 잡음. **6.2는 llm 인스턴스가 있으면 그대로 전달**, None 처리는 모듈 가드가 담당)
  - [x] collect_done 이후 `event="cluster_done"` 로그(clustering 모듈이 내부 로깅하므로 orchestrator는 얇게) 및 이후 `normalize→build→review→recommender` 흐름·이벤트명 **불변**
  - [x] `run_ondemand_brief`는 collect/normalize를 하지 않으므로(이미 생성된 signal 재사용) **수정 불필요** — 회귀만 확인

- [x] **Task 4 — 테스트** (AC: 1, 2, 3, 4)
  - [x] `api/tests/test_clustering.py` 신규. **오프라인 원칙**: 실제 OpenAI 호출 금지 — `llm`은 `MagicMock`(또는 소형 fake)으로 `embed_text`가 **결정론적 벡터**를 반환하게 스텁(키워드→고정 벡터 맵 또는 텍스트 해시 기반). 도메인 앵커 임베딩도 같은 스텁을 타도록 주입 경로 설계
  - [x] **클러스터링:** 유사 벡터 2건(예: Claude 블로그 + HN) → 1클러스터(1 라벨, 소스 2). 무관 벡터 → 별개 클러스터. 임계치 경계값 검증
  - [x] **관련성 필터:** 앵커와 먼 벡터("smart rings" 대역) → 제외 + `article_filtered/off_domain` 로깅 확인
  - [x] **세이프티 필터:** 블록리스트 매칭 제목 → 제외 + `article_filtered/unsafe` 로깅 확인
  - [x] **라벨 고유성:** 라벨이 우연히 같아질 두 클러스터가 **normalize에서 1시그널로 합쳐지지 않음**을 검증(재라벨 결과의 distinct technology_name 수 == cluster_count)
  - [x] **파이프라인 순서/LLM 비례(AC3):** 통합 스타일 테스트 — 재라벨 산출물을 실제 `normalize(...)`(Supabase는 기존 `test_pipeline_foundation.py` 패턴대로 MagicMock)에 흘려 **생성 signal 수 == cluster 수**임을 검증. 원문 수 > 클러스터 수인 픽스처로 "LLM 호출이 원문이 아닌 토픽 수에 비례"를 대변
  - [x] **safe-degrade(AC4):** `llm=None` → 입력 그대로 반환(길이·라벨 불변). `clustering_enabled=False` → pass-through. 한 기사 `embed_text`가 예외 → 그 기사만 영향, 나머지 정상 + `article_embed_failed` 로깅
  - [x] **회귀:** `cd api && pytest -q` 전체 통과(현재 179 passed 유지). `test_recommender_pipeline.py`의 orchestrator 테스트(stub 모드 고정)가 새 단계로 깨지지 않는지 확인 — stub 모드에서도 `cluster_and_filter`가 호출되므로, 그 테스트의 llm mock이 `embed_text`를 갖거나 clustering이 안전 저하되도록 보장(Dev Notes "회귀 주의")

### Review Findings

_Code review 2026-07-29 (Blind Hunter / Edge Case Hunter / Acceptance Auditor 3-layer)._

- [x] [Review][Patch] 클러스터링/라벨 비결정성 → 같은 brief_date 재실행 시 시그널 중복 위험 (decision 해결 2026-07-29: 클러스터링 직전 결정론적 정렬로 patch) — greedy 클러스터링이 수집기 입력 순서에 의존하고, 특히 다수 "General AI" 클러스터의 고유 라벨이 순서에 따라 달라짐. normalizer가 `(technology_name, signal_date)`로 upsert dedup하므로 재실행 시 라벨이 달라지면 dedup이 빗나가 같은 날 중복 시그널 생성 가능. 해결: `cluster_and_filter`에서 클러스터링 전 `url` 기준 정렬 [api/pipeline/clustering.py:137-151,158-187]

- [x] [Review][Patch] 임베딩 실패 pass-through 기사가 세이프티 필터를 우회 (제목 기반 `_is_unsafe`는 임베딩이 불필요한데도 passthrough 경로에서 미적용 → AC2 위반) [api/pipeline/clustering.py:207,214]
- [x] [Review][Patch] 세이프티 블록리스트의 단어조각 `"porn"` — 모듈 자체 "단어 조각 금지(D3)" 규칙 위반, "Adiporn" 등 오탐 유발 [api/pipeline/clustering.py:41]
- [x] [Review][Patch] `cluster_similarity_threshold` / `relevance_min_similarity` 범위검증 없음 — 코사인 [-1,1]을 벗어난 오설정(예: 82)이 조용히 통과 [api/core/config.py:26-28]

- [x] [Review][Defer] N+1 순차 임베딩 호출(배치 없음) [api/pipeline/clustering.py:96-107] — deferred, provider batch 메서드 추가 필요(6.2 범위 밖)
- [x] [Review][Defer] 임베딩/LLM 호출 타임아웃 미설정(collector_timeout은 HTTP 수집기 전용) [api/pipeline/clustering.py:98] — deferred, 모든 LLM 호출 공통 선재 이슈
- [x] [Review][Defer] 동일 url 중복 기사 → signal_sources 중복 행 [api/pipeline/normalizer.py:74-83] — deferred, 수집기 dedup 의존(선재)
- [x] [Review][Defer] 생존 기사 similarity 미로깅 — 임계치 튜닝 관측성 개선 [api/pipeline/clustering.py:119-133] — deferred, enhancement
- [x] [Review][Defer] 테스트가 합성 3D 벡터만 사용 — 실제 1536D 임계치/anchor 실패 경로 미검증 [api/tests/test_clustering.py] — deferred, test coverage
- [x] [Review][Defer] `_embed_text`가 content 무시(title 중심) — 6.3에서 content를 채우면 조용히 품질 저하 [api/pipeline/clustering.py:47-49] — deferred, 6.3 scope

## Dev Notes

### 아키텍처 준수 (반드시 따를 것)

- **AD-16 (외부 콘텐츠 수집 패턴):** "Normalizer/Deduplicator가 RawArticle → Signal(기술 단위) 변환 전담; 하나의 Signal = 하나의 기술/변화 + 다출처 묶음." 6.2의 클러스터링이 바로 이 "기술 단위 묶음"의 **의미 기반 구현**이다. 6.1의 `derive_tech` 키워드 휴리스틱(스톱갭)을 의미 클러스터가 대체·보완한다. 어댑터/수집 계층은 건드리지 않는다.
- **AD-2 / AD-6 (pgvector 전용, 외부 벡터 DB 금지):** RAG/벡터 검색은 Supabase pgvector로만. **신규 벡터 DB(Pinecone·Weaviate 등) 도입 절대 금지.** 임베딩 모델은 기존 `text-embedding-3-small`(`memory_manager`·`recommender`와 동일)로 통일 — 모델 혼용 금지(차원·의미공간 불일치). ⚠️ pre-persist 기사 유사도 계산 방식은 "설계 결정 D1" 참조.
- **AD-5 (격리 / safe degradation):** 개별 기사 임베딩 실패·LLM 부재는 격리·폴백. 6.1 aggregator의 소스 격리, recommender의 `llm=None`/RAG 실패 → 콜드스타트 폴백과 **동일 철학**. 6.2 단계 실패가 배치를 죽이면 안 된다.
- **AD-12 (관찰 가능성):** 모든 로그는 `pipeline_log(stage=..., brief_date=..., user_count=0, ...)` 시그니처. 6.2는 `stage="clustering"` 사용. 필터/클러스터 판정 근거를 남겨 품질 관측(AC2 요구).
- **AD-15 (Batch First):** 6.2는 `run_daily_pipeline`(06:00 KST)의 collect~normalize 사이 단계. On-demand 경로는 collect/normalize를 건너뛰므로 무관.

### 설계 결정 (Dev가 반드시 이 방향으로 구현)

**D1 — "pgvector 코사인" AC 문구의 해석 (핵심):**
AC1은 "pgvector 코사인 유사도로 클러스터링"을 명시하지만, **클러스터링 대상 기사는 아직 DB에 영속화되기 전(pre-persist)** 이다. 기사 임베딩을 DB `vector` 컬럼에 저장해 `<=>`로 질의하려면 **테이블/마이그레이션이 필요한데, 그것은 6.3(Signal 스키마 확장) 스코프**다. 따라서 6.2는:
- 임베딩은 기존 스택(`text-embedding-3-small`, `LLMProvider.embed_text`)으로 생성 — RAG와 동일 모델(AD-6 정합).
- pre-persist 기사 간 코사인 유사도는 **인프로세스(순수 파이썬)로 계산**한다. 배치당 기사 수는 소규모(스파이크 30건, 상한 수십 건)라 O(n²) 순수 파이썬으로 충분(<0.1s).
- 이는 AC의 **본질 요구("외부 벡터 DB 미도입 + 동일 임베딩 스택")를 충족**한다. DB `<=>` 연산자를 문자 그대로 쓰지 않는 이유는 위 스코프 경계 때문 — 6.3에서 기사/클러스터가 스키마화되면 그때 pgvector 네이티브 경로로 전환 가능.
- **✅ 확정(오너 승인 2026-07-29):** 인프로세스 순수 파이썬 방식으로 구현한다. 임시 테이블 + pgvector round-trip은 채택하지 않는다(마이그레이션은 6.3으로 유지).

**D2 — 클러스터 → 시그널 브리지 (normalize 무수정으로 1클러스터=1시그널):**
현재 `normalize()`는 `groups.setdefault(a.technology_name, [])`로 **technology_name 그룹핑** 후 `signals.upsert(on_conflict="technology_name,signal_date", ignore_duplicates=True)` + `signal_sources.insert`. 이를 **바꾸지 않고**(6.3 스코프) 1클러스터=1시그널을 달성하려면, 클러스터링이 **각 클러스터에 배치 내 고유한 `technology_name` 라벨**을 부여하고 멤버 전부를 그 라벨로 재생성하면 된다. 그러면 normalize의 groupby가 자연히 클러스터당 1그룹 → 1 signal + N signal_sources를 만든다.
- **라벨 생성:** 클러스터 대표 기사(첫 멤버)의 `derive_tech`(rss.py에 존재, import 재사용) 결과를 기본 라벨로. 
- **⚠️ 고유화(치명적):** `derive_tech`는 매치 없으면 **모두 `"General AI"`** 를 낸다 → 서로 다른 두 클러스터가 같은 라벨이 되면 normalize가 **다시 1시그널로 합쳐 6.1의 문제가 재현**된다. 반드시 **배치 내 라벨 고유성 보장**: 이미 사용된 라벨이면 대표 기사 제목에서 파생한 짧은 판별자(예: 제목 앞부분 slug/토큰)를 접미로 붙이거나 `"General AI #2"` 식 인덱스 접미 등으로 distinct하게 만든다. 테스트(Task 4 "라벨 고유성")로 강제.
- 이 라벨은 임시 브리지다 — 6.3 normalize v2가 cluster_key 컬럼으로 정식 대체. 여기서 라벨 품질을 과설계하지 말 것(SignalBuilder가 어차피 title/summary를 LLM으로 다시 씀).

**D3 — 세이프티 필터 구현 수준 (✅ 확정: 오너 승인 2026-07-29):**
MVP 6.2는 **경량 블록리스트 휴리스틱**(제목 소문자 매칭)으로 구현한다. OpenAI Moderation API는 호출·비용·비결정 테스트 부담이 있어 **미채택**(도입 시 필터 단계가 또 하나의 LLM 의존이 됨). 관련성 필터가 이미 도메인 밖 대부분을 걸러주므로 세이프티는 명백한 유해어 차단으로 충분. 강화가 필요하면 6.5(측정) 이후 데이터로 판단.

### 도메인 앵커 (관련성 필터)

관련성 = "이 기사가 AI/개발 기술 도메인인가?"를 저비용으로 판정하기 위해, **고정 도메인 설명 문장 1개를 임베딩(모듈 로드시 1회, llm으로)** 해 앵커 벡터로 삼고 각 기사 임베딩과의 코사인 유사도로 판정한다. 앵커 문장 예: `"artificial intelligence, machine learning, large language models, software development, and developer tools"`. 
- 앵커 임베딩도 `llm.embed_text`를 타므로 테스트에서 동일 스텁으로 결정론화 가능하게 **주입/캐싱 경로**를 설계(모듈 전역 lazy 캐시 + 테스트에서 초기화 가능하게, 또는 `cluster_and_filter` 내부에서 llm으로 계산해 재사용). `relevance_min_similarity=0.20`은 초기값 — text-embedding-3-small의 코사인 분포상 무관 문서는 대개 0.1 내외, 도메인 문서는 0.3+ 관측 경향(튜닝 대상, 상수 아닌 settings).

### 코사인 구현 & 임계치 튜닝

- **코사인:** `dot(a,b) / (norm(a)*norm(b))`. 순수 파이썬(`sum(x*y ...)`, `math.sqrt`). 1536차원 × 수십 벡터 = 무시 가능 비용. **numpy 등 신규 의존성 추가 금지**(requirements.txt 유지). 정규화 벡터 캐싱(각 벡터 norm 1회 계산)으로 O(n²) 반복 최적화.
- **임계치:** `cluster_similarity_threshold=0.82`는 초기 가정값. text-embedding-3-small에서 "동일 주제 다른 표현"은 대략 0.8+ 코사인. 너무 높으면 같은 토픽이 안 묶이고(과분할), 너무 낮으면 다른 토픽이 합쳐진다(과병합 — 6.1의 "General AI" 재현). 6.1 리뷰 Deferred(HN 상한·클러스터링 튜닝)와 함께 실데이터로 조정. 테스트는 임계치를 픽스처로 주입해 경계 검증.

### 수집할 기존 파일 — 현재 상태 / 변경 / 보존

- **`api/pipeline/orchestrator.py`** (변경): `run_daily_pipeline` L46~52 collect 블록 직후(`collect_done` 로그 뒤), `normalize` 호출(L55 부근) 직전에 `cluster_and_filter(articles, llm, brief_date=...)` 한 줄 삽입. `llm`은 이미 상단에서 생성됨(L36~40). 나머지 흐름·이벤트명 불변. `run_ondemand_brief`는 무수정.
- **`api/pipeline/normalizer.py`** (보존, **무변경** — 6.3 스코프): `normalize()`가 `technology_name`으로 그룹핑 + `on_conflict="technology_name,signal_date"` upsert. 6.2는 이 계약을 존중해 "클러스터=고유 라벨"로 흘린다(D2). **빈 technology_name은 스킵되므로 라벨은 항상 non-empty 보장.**
- **`api/pipeline/models.py`** (보존, 무변경): `RawArticle(technology_name, title, url, source_type, content="")`. 재라벨은 `dataclasses.replace`로 새 인스턴스 생성 권장(원본 mutation 회피). `content`는 6.1이 안 채움 — 임베딩 텍스트는 `technology_name + title`.
- **`api/pipeline/collector/rss.py`** (보존): `derive_tech(text)` 함수 존재 — 클러스터 라벨 기본값 생성에 **import 재사용**(중복 구현 금지). `_TECH_KEYWORDS`도 여기 있음.
- **`api/pipeline/collector/aggregator.py`** (보존): `run_collectors()`가 반환하는 dedup된 `list[RawArticle]`이 6.2 입력. exact dedup은 이미 됨 — 6.2는 **의미(near-duplicate) 병합**을 추가하는 것(exact와 다른 층).
- **`api/pipeline/llm/base.py` / `openai_provider.py`** (보존, 재사용): `LLMProvider.embed_text(text) -> list[float]`(1536 검증 포함). **배치 임베딩 메서드는 없음** — 기사별 `embed_text` 반복 호출(수십 건 OK). 향후 배치 최적화는 6.4/후속. 신규 추상 메서드 추가하지 말 것(인터페이스 안정).
- **`api/pipeline/recommender.py`** (참고, 무변경): `_signal_embed_text`·`_embed_signal_list`가 이미 "embed 후 격리/폴백" 패턴을 보여줌 — 6.2 임베딩 격리 로직의 레퍼런스. Recommender 점수식 변경은 6.4.
- **`api/pipeline/logger.py`** (보존, 재사용): `pipeline_log(stage, brief_date, user_count=0, level="info", **extra)`.
- **`api/core/config.py`** (변경): Task 1 세 필드 추가. 기존 `openai_embedding_model` 재사용.

### 라이브러리 / 버전

- **신규 의존성 없음.** `openai>=1.82.0`(embed_text), 표준 라이브러리 `math`·`dataclasses`만. **numpy·scikit-learn·외부 벡터 DB 도입 금지.**
- 임베딩 모델: `text-embedding-3-small`(1536) — 전 파이프라인 통일(변경 금지).

### 회귀 주의 (반드시 확인)

- `test_recommender_pipeline.py`의 orchestrator 통합 테스트 2건은 **stub 모드 고정**(6.1에서 오프라인 보장 위해). 하지만 stub 모드에서도 `cluster_and_filter`가 호출된다 → 그 테스트가 주입/사용하는 `llm` mock이 `embed_text`를 가지고 있지 않으면 clustering이 예외 격리로 pass-through될 수는 있으나, **의도치 않은 동작 변화 없는지 확인**. 안전책: 그 테스트들이 `clustering_enabled=False` 또는 `llm=None` 경로를 타도록 하거나, mock `embed_text`를 제공. 산출 signal 수 assertion이 있으면 clustering이 stub 5건을 어떻게 묶는지에 영향받으므로, **stub 경로에서 clustering을 건너뛰게** 하는 편이 회귀 안전(예: stub 모드에선 6.2를 skip, 또는 테스트에서 enabled=False). Dev가 기존 테스트 assertion을 먼저 읽고 결정할 것.
- `cd api && pytest -q` → 현재 179 passed. 6.2 후에도 그대로 통과 + 신규 테스트 추가가 목표.

### 파일 구조 (신규/수정)

```
api/pipeline/clustering.py          (신규 — cluster_and_filter: embed→filter→cluster→relabel)
api/pipeline/orchestrator.py        (수정 — collect_done 뒤/normalize 앞에 한 단계 삽입)
api/core/config.py                  (수정 — clustering_enabled, cluster_similarity_threshold, relevance_min_similarity)
api/.env.example                    (수정 — 신규 설정 주석)
api/tests/test_clustering.py        (신규 — 클러스터/필터/라벨고유성/순서/safe-degrade/회귀)
```

### 테스트 표준

- **프레임워크:** pytest 8.3.4, `pytest.ini`(`testpaths=tests`, `asyncio_mode=auto`), 파일명 `test_*.py`, `api/tests/`.
- **오프라인 원칙(절대):** 실제 OpenAI 호출 금지. `llm`을 `MagicMock`/소형 fake로 대체하고 `embed_text`가 **결정론적 벡터** 반환(키워드→고정 벡터 또는 텍스트 해시 기반 저차원 벡터로도 코사인 성질 검증 가능 — 실제 1536차원일 필요 없음, 단 provider의 1536 검증은 mock이 우회). Supabase가 필요한 통합 테스트(normalize)는 기존 `test_pipeline_foundation.py`의 MagicMock 패턴 참고. respx 미설치 — 도입 금지.
- **커버리지 대상:** near-dup 병합(1클러스터), 무관 분리, off_domain/unsafe 필터+로깅, 라벨 고유성(distinct==cluster_count), 순서/LLM 비례(signal 수==cluster 수), safe-degrade(llm None/enabled False/embed 실패 격리).

### Project Structure Notes

- 백엔드는 `api/` 루트 실행(PYTHONPATH=`api`, import는 `pipeline.*`·`core.*`). 로컬 실행/DB 접속은 [[local-run-setup]] 참고.
- 클러스터링은 **DB 무변경** — `list_tables`/마이그레이션 금지(6.3 스코프). pgvector 네이티브 클러스터링은 6.3에서 스키마화 후 재검토(D1).
- 충돌/변이: 없음. 신규 파일 1 + orchestrator 1줄 삽입 + config 3필드.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.2 (L927-948), #Epic 6 스파이크 근거 (L891-902), #FR-8.2/8.3 (L54-55, L897-898)]
- [Source: _bmad-output/implementation-artifacts/6-1-실-수집기-어댑터-and-소스-레지스트리.md#스코프 경계·스파이크가 드러낸 함정(L45,108-111)·Review Findings Deferred(L222,227)]
- [Source: architecture/.../ARCHITECTURE-SPINE.md#AD-16 (L308-311), #AD-2 (L23-26), #AD-6 (L188-191), #AD-5 (L155-158), #AD-12 (L252-255), #AD-15 (L273-276)]
- [Source: api/pipeline/orchestrator.py L36-58 (llm 생성 + collect→normalize→build 흐름)]
- [Source: api/pipeline/normalizer.py (technology_name 그룹핑 + on_conflict upsert — 6.2 무변경)]
- [Source: api/pipeline/collector/rss.py (derive_tech·_TECH_KEYWORDS 재사용), aggregator.py (dedup된 입력)]
- [Source: api/pipeline/llm/base.py·openai_provider.py (embed_text→list[float] 1536), recommender.py (_embed_signal_list 격리 패턴)]
- [Source: api/core/config.py (openai_embedding_model 재사용), requirements.txt (numpy 없음 — 순수 파이썬 코사인)]
- [Source: _bmad-output/implementation-artifacts/db/001_initial_schema.sql (signals/signal_sources·pgvector extension — 6.2 무변경), 002_signals_unique_constraint.sql (technology_name,signal_date UNIQUE — D2 라벨 고유성 이유), 004_match_memories_rpc.sql (pgvector <=> 코사인 참조 패턴)]
- [Source: _bmad-output/planning-artifacts/research/spike-rss-2026-07-29.py (throwaway — "General AI" 50% 뭉갬·smart rings·Claude 다중소스 근거)]

### ✅ 확정된 결정 (오너 승인 2026-07-29 — dev는 이 방향으로 구현)

- **D1 (유사도 계산):** **인프로세스 순수 파이썬** 채택. 임시 테이블 + pgvector `<=>` round-trip은 미채택 — 마이그레이션은 6.3 스코프로 유지. numpy 등 신규 의존성 추가 금지.
- **D3 (세이프티 필터):** **경량 블록리스트 휴리스틱** 채택. OpenAI Moderation API는 미채택(필터 단계의 추가 LLM 의존·비용·비결정 테스트 회피).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (BMad Dev Story workflow)

### Debug Log References

- `cd api && pytest -q` → **192 passed** (baseline 179 + 신규 13), 회귀 0건.
- `pytest tests/test_clustering.py -q` → 13 passed.
- 린터 미구성(ruff/flake8 없음) — 정적 검사 스킵.

### Completion Notes List

**구현 요약 (AC1~4 충족):**
- **AC1 (의미 클러스터링):** `pipeline/clustering.py` 신규. `LLMProvider.embed_text`(text-embedding-3-small 재사용)로 기사별 임베딩 1패스 → 순수 파이썬 코사인(단일 패스 greedy)으로 `cluster_similarity_threshold` 기준 병합. 외부 벡터 DB·numpy 미도입(D1 확정 방향).
- **AC2 (관련성/세이프티 필터):** 배치마다 도메인 앵커 문장을 1회 임베딩 → 각 기사와 코사인 `relevance_min_similarity` 미만이면 `off_domain` 제외. 세이프티는 경량 블록리스트 휴리스틱(제목 매칭)으로 `unsafe` 제외(D3 확정 방향). 제외 사유는 `event="article_filtered"`(reason/url/similarity)로 로깅.
- **AC3 (파이프라인 순서):** `orchestrator.run_daily_pipeline`에 collect_done 직후·normalize 직전 `cluster_and_filter` 한 단계 삽입(+`cluster_done` 로그). `normalizer.py` 무변경 — 클러스터를 **배치 내 고유 technology_name 라벨**로 재라벨해(D2) normalize 그룹핑이 자연히 1클러스터=1시그널을 만든다. 통합 테스트로 생성 signal 수 == cluster 수(원문 3 > 클러스터 2) 검증.
- **AC4 (안전 저하·무회귀):** `articles` 빈 값 / `clustering_enabled=False` / `llm is None` → pass-through(`clustering_skipped`). 앵커 임베딩 실패 → 관련성 필터만 스킵. 개별 기사 임베딩 실패(및 zero-norm)는 격리 → `article_embed_failed` 로깅 후 원본 라벨 유지 pass-through(전체 중단 없음). 기존 orchestrator 통합 테스트(stub 모드, MagicMock llm)는 embed가 MagicMock→zero-norm→embed_failed 경로로 안전 저하되어 무회귀.

**설계 노트:**
- 도메인 앵커는 모듈 전역 캐시 대신 **배치당 1회 계산**으로 단순화(테스트 간 상태 오염 없음, 일 1회 배치라 비용 무시 가능) — 스토리가 허용한 경로.
- 클러스터 대표는 첫 멤버(running centroid 아님) — 결정론적·단순.
- 라벨 고유화: base(derive_tech) 충돌 시 제목 slug → `#n` 인덱스 순으로 판별자 부여(D2 "General AI" 재병합 방지).

**후속(스코프 밖, 의도적 미구현):** signals 스키마 확장·cluster_key 정식화·normalize v2(6.3), Recommender 점수식(6.4), engagement 로깅(6.5). 임계치(0.82/0.20)는 초기값 — 실데이터 튜닝 대상.

### File List

- `api/pipeline/clustering.py` (신규 — cluster_and_filter: embed→filter→cluster→relabel)
- `api/pipeline/orchestrator.py` (수정 — collect_done 뒤/normalize 앞 6.2 단계 삽입 + 단계 번호 주석 정리)
- `api/core/config.py` (수정 — clustering_enabled, cluster_similarity_threshold, relevance_min_similarity)
- `api/.env.example` (수정 — 신규 설정 3항목 주석 + 임베딩 모델 재사용 안내)
- `api/tests/test_clustering.py` (신규 — 클러스터/필터/라벨고유성/순서/safe-degrade/로깅 13 테스트)

## Change Log

- 2026-07-29: Story 6.2 구현 완료 — 의미 임베딩 클러스터링 + 관련성/세이프티 필터 + 오케스트레이터 배선. 신규 파일 2(clustering.py, test_clustering.py), 수정 3(orchestrator.py, config.py, .env.example). 테스트 192 passed(신규 13). Status → review.
