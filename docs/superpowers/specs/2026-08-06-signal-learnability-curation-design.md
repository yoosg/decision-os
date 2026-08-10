# 시그널 수집 품질 개선 — 학습가치 필터 + 수집원 큐레이션 (설계)

- 날짜: 2026-08-06
- 브랜치: `feat/signal-learnability-curation`
- 기준: 현재 `main` (backup 브랜치 무관, 새로 구현)

## 배경 / 문제

오너 의도는 **"새 AI 도구·기술 소식을 빠르게 파악해 바로 학습으로 잇는 것"**이다.
그러나 현재 `main` 파이프라인은 의도와 무관한 시그널을 통과시킨다. 대표 사례:

> "일반 AI: 353,000명과의 협력 과정"

이런 비즈니스/오피니언/사회이슈성 뉴스는 학습으로 전환되지 않아 노이즈가 된다.

### 근본 원인 (현재 main 코드 기준)

1. **수집원에 뉴스/오피니언이 섞임** — `api/pipeline/collector/registry.py`의 `SOURCES`에
   The Verge AI(뉴스), 죽은 LangChain RSS, 품질 필터 없는 broad HackerNews가 있음.
2. **학습가치 판별 단계 부재** — "배울 기술/도구 vs 뉴스/오피니언"을 구분하는 로직이 없어
   전부 시그널이 됨.
3. **네이밍 품질** — `derive_tech`가 키워드 매치 실패 시 "General AI(일반 AI)"로 뭉개고
   제목 조각을 붙여 "일반 AI: 353,000명…" 같은 라벨을 만든다.

## 목표 / 성공 기준

각 시그널 후보를 다음 기준으로 처리한다 (오너와 합의):

| 유형 | 예시 | 처리 |
|---|---|---|
| 신규 도구 업데이트 | "LangGraph 0.3 릴리스 — 체크포인트 API" | **keep** |
| 신규 기능/도구 | "Anthropic, Claude에 MCP 커넥터 출시" | **keep** |
| 기법/연구 (바로 적용 가능) | "새 논문: Diffusion 추론 2배 가속 기법" | **keep** |
| 비즈니스/제휴 뉴스 | "OpenAI, 353,000명과 협력한 과정" | **drop** |
| 오피니언/인터뷰 | "Fender CEO의 AI 비유" | **drop** |
| 사회/윤리 뉴스 | "AI 아티스트 보상 논쟁" | **drop** |

판정 기준 문장: **"프론트엔드 개발자가 이번 주에 바로 배우거나 코드에 적용할 수 있는가?"**

## 접근 (선택: 접근 C)

클러스터링 뒤·normalize 앞에 **학습가치 분류 단계**를 새로 두되, 그 LLM 단계가
**판정(keep/drop)과 동시에 깨끗한 기술명까지 생성**한다. 뉴스 유입(#2)과 엉성한
네이밍(#3)을 한 단계에서 함께 해결한다. 수집원 큐레이션(#1)을 1차 방어로 병행한다.

- 두 레버의 역할 분담: 수집원 큐레이션 = 애초에 덜 들어오게(1차), 학습가치 필터 =
  새어든 뉴스를 의미 기준으로 잡음(2차). 중첩 방어.

## 데이터 흐름

```
Collect (수집원 큐레이션 ← 변경)
      ↓
cluster_and_filter (임베딩·관련성·세이프티·클러스터링 — 기존 유지)
      ↓
★ curate_learnability (신규: LLM 배치 분류 → drop + 깨끗한 이름)
      ↓
normalize → signal_builder → reviewer → recommender (기존 그대로)
```

- 클러스터링 **뒤**에 두는 이유: LLM 호출이 원문 수가 아니라 **토픽(클러스터) 수**에
  비례 → 비용이 배치 1회로 통제됨 (기존 "LLM 전에 클러스터" 원칙과 일치).
- normalize(=DB 저장) **앞**에 두는 이유: 버릴 것을 저장 전에 버려 저장 후 삭제 뒤처리
  불필요.

## 컴포넌트 설계

### 1. 학습가치 분류기 — `api/pipeline/curator.py` (신규)

공개 진입점:

```python
def curate_learnability(
    articles: list[RawArticle], llm: LLMProvider | None, brief_date: str = ""
) -> list[RawArticle]:
    ...
```

동작:
1. `cluster_key`로 기사를 토픽 단위로 그룹핑 (clustering이 이미 부여).
2. 각 토픽의 대표 제목 + 현재 라벨을 배치로 모아 `llm.classify_learnability(topics)` 1회 호출.
3. `keep=false` 토픽은 드롭. `keep=true` 토픽은 멤버 전원의 `technology_name`을 응답 `name`으로 교체.
4. 반환: 살아남은 기사들 (드롭된 클러스터 제외, 라벨 교체됨).

safe-degrade 가드 (기존 `clustering.py`와 동일 철학, AD-5):
- `llm is None` / `settings.learnability_filter_enabled == False` / 빈 입력 → 전량 통과, 라벨 원본 유지.
- LLM 호출 실패 / JSON 파싱 실패 / **응답 개수 ≠ 토픽 개수** → 전량 통과 (한 배치 실패가
  그날 브리핑을 통째로 죽이지 않게).
- 드롭 시 `event="topic_dropped"` (제목·카테고리 포함) 로깅 → 오탐 감사.

### 2. LLM 메서드 — `classify_learnability`

`pipeline/llm/base.py`(추상) + `openai_provider.py` + `gemini_provider.py`에 추가.
프롬프트/검증기는 `pipeline/llm/prompts.py`에 배치 (기존 패턴).

입력 (토픽 리스트):
```json
[{"id": 0, "label": "General AI", "title": "OpenAI, 353,000명과 협력한 과정"},
 {"id": 1, "label": "LangGraph", "title": "LangGraph 0.3 릴리스 — 체크포인트 API"}]
```

출력 (입력과 동일 순서·개수):
```json
[{"id": 0, "keep": false, "category": "business_news", "name": "OpenAI 협력 사례"},
 {"id": 1, "keep": true,  "category": "tool_update",   "name": "LangGraph 0.3"}]
```

카테고리 taxonomy (프롬프트에 명시):
- **keep** → `new_tool`, `tool_update`, `technique_research`, `framework_library`
- **drop** → `business_news`, `opinion`, `social_ethics`, `general_news`

프롬프트 지침: 위 판정 기준 문장 사용. **애매하면 보수적으로 keep** (과도 삭제 방지).

검증기 `parse_and_validate_learnability(raw, expected_count)`:
- JSON 배열 여부, 길이 == expected_count, 각 원소 키(`id/keep/category/name`) 존재,
  `category`가 허용 목록, `name` 비어있지 않음. 위반 시 `LLMProviderError` → curator가
  safe-degrade로 폴백.

### 3. 수집원 큐레이션 — `registry.py` + `hackernews.py`

`Source` dataclass 확장 (HN 품질 필터 옵션):
```python
min_points: int = 0          # HN 점수 하한
tags: tuple[str, ...] = ()   # 예: ("show_hn",)
```
`_build_one`이 HN 어댑터에 `min_points`/`tags` 전달.

`HackerNewsCollector` 확장: `min_points`로 점수 미달 hit 제거 (Algolia
`numericFilters=points>=N`), `tags`로 Show HN 등 태그 필터.

`SOURCES` 변경:

| 조치 | 대상 | 이유 |
|---|---|---|
| 제거 | The Verge AI | 뉴스/오피니언 주 오염원 |
| 제거 | LangChain RSS | 죽은 피드 → GitHub 릴리스로 대체 |
| 유지 | Hugging Face, Simon Willison, Google AI | 도구/기술 중심 양질 |
| 추가 | GitHub 릴리스: `langchain-ai/langchain`, `run-llama/llama_index`, `vllm-project/vllm`, `ollama/ollama`, `ggml-org/llama.cpp` | 도구 업데이트 직통 |
| 추가 | HN `min_points≈50` + `Show HN` 태그 소스 | 저품질 뉴스 차단 + 도구 출시 포착 |
| 추가(검증) | OpenAI 블로그 RSS | 1차 소식원. 피드 실존/생존은 구현 때 확인 |

> 새 피드 URL은 구현 단계에서 생존 확인. 수집기에 피드 헬스 로깅(`source_failed`/`bozo`)이
> 이미 있어 죽은 피드는 자동 노출 → `enabled=False`로 끈다.

### 4. 설정 — `core/config.py`

- `learnability_filter_enabled: bool = True` (안전 롤아웃/긴급 차단 토글).

### 5. 오케스트레이터 — `pipeline/orchestrator.py`

`cluster_and_filter` 직후·`normalize` 직전에 한 줄 삽입:
```python
articles = curate_learnability(articles, llm, brief_date=brief_date)
```

## 테스트 전략 (TDD)

- `curator`: keep/drop 분기, 라벨 교체, safe-degrade 3종(llm None / 파싱 실패 / 개수 불일치)
  전량 통과, 드롭 로깅.
- `classify_learnability` (provider): mock 응답 파싱/검증, 잘못된 category·개수 → `LLMProviderError`.
- `HackerNewsCollector`: `min_points` 미달 hit 제거, `tags` 파라미터 전달.
- `registry`: The Verge 부재, GitHub 릴리스 소스 존재, HN min_points 세팅.
- `orchestrator`: 새 단계가 cluster 뒤·normalize 앞에 호출되는지 (호출 순서/신호 수 검증).

## 리스크 / 사이드이펙트

- 필터 경로에 LLM 의존 추가 → safe-degrade 가드로 완화 (기존 clustering과 동일).
- 분류기 오탐(학습가치 있는 항목 잘못 드롭) 가능 → 보수적 keep + 드롭 로깅으로 감사·튜닝.
- 새 GitHub/RSS 피드 생존 불확실 → 피드 헬스 로깅 + `enabled` 토글로 대응.
- 배치 LLM 호출 1회 추가 → 비용은 토픽 수 비례라 미미.

## 범위 밖 (YAGNI)

- Moderation API 도입 (기존 경량 블록리스트 유지).
- 사용자별 학습가치 기준 커스터마이징.
- 드롭된 뉴스의 별도 아카이브/피드.
