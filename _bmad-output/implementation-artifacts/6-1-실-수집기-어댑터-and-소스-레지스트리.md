---
baseline_commit: NO_VCS
---

# Story 6.1: 실 수집기 어댑터 & 소스 레지스트리

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

개발자로서,
StubCollector를 실제 외부 소스(RSS/Atom · HackerNews · GitHub Releases) 수집기로 대체하고 소스 레지스트리로 관리하고 싶다,
그래서 Daily Brief가 하드코딩 샘플 5건이 아니라 실제 최신 AI 기술 소식을 재료로 삼는다.

## Acceptance Criteria

**AC1 — 소스 레지스트리 + 어댑터 수집 (FR-8.1)**
- **Given** 소스 레지스트리에 활성 소스(RSS/Atom · HN · GitHub Releases) 목록이 설정되어 있을 때
- **When** 수집기가 실행되면
- **Then** 각 활성 소스에서 `RawArticle(technology_name, title, url, source_type, content)` 목록을 반환한다
- **And** 각 소스 어댑터는 `BaseCollector`를 상속하고 `collect() → list[RawArticle]`만 노출한다 (AD-16)
- **And** 외부 HTTP 요청은 certifi CA 번들로 TLS 검증하고 요청 타임아웃을 적용한다 (스파이크에서 확인된 SSL/타임아웃 이슈)

**AC2 — 소스 격리 & 피드 헬스 관측 (FR-8.1, AD-5, AD-12)**
- **Given** 일부 소스가 실패(404 / 타임아웃 / 파싱오류 / TLS오류)할 때
- **When** 수집이 진행되면
- **Then** 실패한 소스는 격리되어 로깅되고 나머지 소스 수집은 계속된다 (한 소스 실패가 배치를 중단시키지 않음)
- **And** 소스별 성공/실패 여부와 수집 건수가 `pipeline_log`(`stage="collector"`)로 기록된다 (피드 헬스 관측)

**AC3 — Exact 중복 제거 (FR-8.1)**
- **Given** 동일 URL 또는 정규화된 동일 제목의 기사가 여러 소스에서 수집될 때
- **When** 수집 결과를 반환하면
- **Then** exact 중복은 1건만 남기고 제거된다 (스파이크: `Agent Intrusion ×2` 완전중복, `Claude 암호취약점` 블로그+HN 동일주제 확인)
- **And** 제거된 중복 건수가 로깅된다

**AC4 — 오케스트레이터 통합, 파이프라인 무회귀 (AD-15)**
- **Given** `run_daily_pipeline`이 실행될 때
- **When** collect 단계가 실행되면
- **Then** 하드코딩 `StubCollector` 대신 실 수집기가 사용된다 (설정 플래그로 stub/real 전환 가능 — deferred-work `orchestrator.py:7` 하드코딩 해소)
- **And** 반환된 `RawArticle` 목록이 기존 `normalize()`에 그대로 흘러 시그널이 생성된다 (normalize v2는 Story 6.3 — **이 스토리는 normalize를 변경하지 않는다**)
- **And** 모든 소스가 실패해 0건이 수집돼도 파이프라인은 예외 없이 완료된다(0 signals, `error=None`)

> ⚠️ **스코프 경계 (중요):** 이 스토리는 **수집 + 레지스트리 + exact 중복 제거 + 오케스트레이터 배선**까지만 한다. 의미 클러스터링·관련성/세이프티 필터는 **Story 6.2**, `signals` 스키마 확장(`published_at`·인기 등)과 normalize v2는 **Story 6.3**, Recommender v2는 **6.4**. 여기서 임베딩·pgvector·LLM 호출·DB 마이그레이션을 하지 말 것.

## Tasks / Subtasks

- [x] **Task 1 — 의존성 & 설정 추가** (AC: 1, 4)
  - [x] `api/requirements.txt`에 `feedparser`(RSS/Atom 파싱)와 `certifi`(명시적 CA 핀) 추가. `httpx==0.28.1`는 이미 존재 — 재사용
  - [x] `.venv`에 설치 후 import 확인 (feedparser 6.0.13, certifi 2026.07.22 기설치)
  - [x] `core/config.py` `Settings`에 `collector_mode: str = "real"` 추가(값: `"real"` | `"stub"`), HTTP 타임아웃 `collector_timeout_seconds: float = 10.0` 추가. `.env.example`에 주석 항목 추가
- [x] **Task 2 — 소스 레지스트리** (AC: 1)
  - [x] `api/pipeline/collector/registry.py` 신규: 활성 소스 목록을 코드 상수(`SOURCES`)로 정의(각 항목 `name`·`kind`(rss/hn/github)·`url`/`queries`·`source_type`·`enabled`). **DB 테이블 아님** — 스키마는 6.3 스코프
  - [x] 스파이크 `_FEEDS` 5개 + `_HN_QUERIES` 시드 + GitHub Releases 1개로 사용. `enabled=False`로 비활성 토글 가능하게
  - [x] 레지스트리에서 활성 항목만 필터해 어댑터 인스턴스 목록을 만드는 팩토리 함수(`build_collectors`) 제공
- [x] **Task 3 — 어댑터 구현 (BaseCollector 상속)** (AC: 1, 2)
  - [x] `api/pipeline/collector/rss.py` `RssCollector`: `feedparser`로 RSS/Atom 파싱, 피드당 상한(`_MAX_PER_FEED`) 적용. GitHub Releases는 `<repo>/releases.atom` 형태로 동일 RSS 경로 재사용
  - [x] `api/pipeline/collector/hackernews.py` `HackerNewsCollector`: HN Algolia `search_by_date` REST(`tags=story`, **https 교정**), 쿼리별 상한(`_PER_QUERY`)·전체 상한(`_MAX_HN`) 적용
  - [x] `api/pipeline/collector/github.py` `GitHubReleasesCollector`: repo releases.atom을 `RssCollector` 로직으로 처리 — `source_type="github"`, tech는 repo 문맥으로 파생
  - [x] 각 어댑터는 **공유 `httpx.Client`**(`timeout`, `follow_redirects=True`, `verify=certifi.where()`, `User-Agent` 헤더)로 요청. `technology_name` 채우기: 스파이크 `_derive_tech` 키워드 휴리스틱 이식(임시 — 6.2 클러스터링이 대체). 매치 없으면 `"General AI"`
  - [x] `technology_name`이 비면 normalize가 스킵하므로 절대 빈 문자열 반환 금지 (`derive_tech`는 항상 non-empty)
- [x] **Task 4 — 수집 오케스트레이션(격리 + 중복제거)** (AC: 2, 3)
  - [x] `api/pipeline/collector/aggregator.py` `run_collectors()` 신규: 레지스트리 어댑터를 순회, **각 어댑터 호출을 try/except로 격리** — 실패 시 `pipeline_log(stage="collector", level="error", event="source_failed", source=name, error=...)` 남기고 다음 소스 계속(AD-5)
  - [x] 성공 소스는 `pipeline_log(stage="collector", event="source_collected", source=name, article_count=n)`
  - [x] 전 소스 합산 후 **exact 중복 제거**: `seen_urls`(정확 URL) + `seen_titles`(정규화 = `title.strip().lower()`) 셋 기준. 제거 건수 `event="dedup_done", removed=k` 로깅
  - [x] 반환: dedup된 `list[RawArticle]`
- [x] **Task 5 — 오케스트레이터 통합** (AC: 4)
  - [x] `api/pipeline/orchestrator.py`: `StubCollector()` 직접 사용 대신 `settings.collector_mode`에 따라 real `run_collectors()` 또는 `StubCollector` 선택하는 분기로 교체
  - [x] 기존 `collect_done` 로그(`article_count`)와 이후 `normalize(...)` 호출 흐름은 **그대로 유지**
  - [x] `run_ondemand_brief`는 collect를 하지 않으므로 **수정 불필요**(회귀 확인 완료)
- [x] **Task 6 — 테스트** (AC: 1, 2, 3, 4)
  - [x] `api/tests/test_collector_real.py` 신규: 네트워크 미접속(오프라인) — `httpx.Client.get`을 MagicMock으로 대체하고 고정 RSS/Atom·HN JSON 픽스처 주입
  - [x] RSS 파싱 → `RawArticle` 매핑, HN JSON → 매핑, `source_type` 정확성 검증
  - [x] **격리**: 한 소스가 예외를 던져도 나머지 결과가 반환되고 실패가 로깅됨을 검증
  - [x] **중복제거**: 동일 URL·동일(정규화) 제목 입력이 1건으로 축약됨을 검증
  - [x] **certifi/타임아웃**: `httpx.Client` 생성 인자에 `verify`(certifi)·`timeout`이 전달됨을 검증
  - [x] 기존 `tests/test_pipeline_foundation.py`의 `StubCollector` 테스트 **유지**(StubCollector 존속). `test_recommender_pipeline.py`의 orchestrator 테스트 2건은 stub 모드로 고정(오프라인 보장). `pytest -q` 전체 회귀 통과(179 passed)

## Dev Notes

### 아키텍처 준수 (반드시 따를 것)

- **AD-16 (외부 콘텐츠 수집 패턴):** Collector는 Source 어댑터 인터페이스로 추상화 — 각 어댑터 `collect() → list[RawArticle]`. Source별 파싱 로직이 하위 파이프라인(Signal Builder 등)에 새면 안 됨. **새 소스 추가 = 새 어댑터 + 레지스트리 항목, 하위 파이프라인 무수정.** REST vs 스크래핑은 어댑터 내부 구현(스파인에 고정 안 함) — 이 스토리에서 **RSS/Atom=feedparser, HN=Algolia REST**로 확정(architecture Deferred "Source별 수집 API 방식"을 여기서 해소).
- **AD-5 (소스 격리):** 개별 소스 실패는 격리 — 한 피드 실패가 배치 전체를 죽이지 않는다. 스파이크에서 LangChain 피드 0건/일부 SSL 실패 확인됨.
- **AD-12 (관찰 가능성):** 배치 로그는 `brief_date`·`pipeline_stage`·`user_count` 포함. `pipeline_log(stage="collector", brief_date=..., user_count=0, ...)` 시그니처 사용(기존 `logger.py`). 소스별 건수·성공/실패를 남겨 피드 헬스 관측.
- **AD-2/AD-6:** 이 스토리는 **pgvector/임베딩/LLM 미사용**. 클러스터링·RAG는 6.2/6.4. 여기서 벡터 DB나 OpenAI 호출을 추가하지 말 것.
- **AD-15 (Batch First):** collect는 `run_daily_pipeline`(06:00 KST 배치)의 1단계. On-demand 경로는 collect를 건너뛰므로 무관.

### 수집할 기존 파일 — 현재 상태 / 변경 / 보존

- **`api/pipeline/collector/base.py`** (보존, 선택적 확장): `BaseCollector(ABC)` — 추상 `collect() → list[RawArticle]`. 새 어댑터는 이걸 상속. deferred-work: "BaseCollector 예외 계약 미정의" — 어댑터는 예외를 **밖으로 던지고**, 격리는 aggregator(Task 4)가 담당하도록 계약을 정한다(어댑터 내부에서 삼키지 말 것).
- **`api/pipeline/collector/stub.py`** (보존): `StubCollector` — 하드코딩 5건. **삭제 금지.** `collector_mode="stub"` 및 기존 테스트가 의존. real 모드에서만 대체.
- **`api/pipeline/models.py`** (보존, 무변경): `RawArticle(technology_name, title, url, source_type: SourceType, content="")`. `SourceType = Literal['official_blog','github','reddit','hn','youtube','other']`. 어댑터의 `source_type`은 반드시 이 리터럴 중 하나 — HN=`'hn'`, GitHub=`'github'`, 블로그=`'official_blog'`, 그 외=`'other'`.
- **`api/pipeline/normalizer.py`** (보존, **무변경** — 6.3 스코프): 현재 `normalize()`는 `groups.setdefault(a.technology_name, [])`로 **technology_name 그룹핑** 후 `signals.upsert(on_conflict="technology_name,signal_date", ignore_duplicates=True)` + `signal_sources.insert`. → **6.1의 `RawArticle.technology_name`이 비면 시그널이 생성되지 않는다**(빈 값 스킵 로직 L23-31). 반드시 채울 것. 동일 URL이 중복으로 들어오면 signal_sources 중복 삽입 가능(deferred-work L168) → 6.1의 dedup이 이를 예방하는 것이 핵심 가치.
- **`api/pipeline/orchestrator.py`** (변경): L7 import, L46-50 collect 블록. `StubCollector()` 직접 인스턴스화를 설정 분기로 교체. 나머지(normalize→build_signals→reviewer→recommender) 흐름·로그 이벤트명 **불변**.
- **`api/pipeline/logger.py`** (보존, 재사용): `pipeline_log(stage, brief_date, user_count=0, level="info", **extra)`.

### 스파이크 레퍼런스 (그대로 복붙 금지 — 프로덕션 이식)

`_bmad-output/planning-artifacts/research/spike-rss-2026-07-29.py`는 **throwaway 스파이크**. 재사용 가능한 검증된 패턴:
- `httpx.Client(timeout=10.0, follow_redirects=True, headers={"User-Agent": ...})` + `feedparser.parse(r.content)`
- HN Algolia: `GET http(s)://hn.algolia.com/api/v1/search_by_date?query=..&tags=story&hitsPerPage=N`, `hit["url"] or item?id=objectID`
- `seen_urls` 중복 제거 셋, 피드당/HN 전체 상한
- `_FEEDS`(HuggingFace/Simon Willison/Google AI/The Verge AI/LangChain) + `_HN_QUERIES`(LLM/OpenAI/Anthropic Claude/RAG) 시드
- **개선점(스파이크 대비 반드시 반영):** ① `verify=certifi.where()` 명시(스파이크는 http:// Algolia 사용 — **https로 교정**), ② 제목 정규화 dedup 추가(URL만으론 부족), ③ 어댑터/aggregator 분리(스파이크는 단일 클래스), ④ `print` 대신 `pipeline_log`.

### 스파이크가 드러낸 함정 (스코프 밖이지만 인지)

- `technology_name` 키워드 휴리스틱이 30건 중 50%를 `"General AI"`로 뭉갬 → normalize가 무관 기사 15개를 1개 무의미 시그널로 합침. **6.1의 휴리스틱은 임시 스톱갭**이며 6.2 의미 클러스터링이 근본 해결. 6.1에서 휴리스틱을 과설계하지 말 것.
- 유해/무관 콘텐츠("smart rings"), 피드 헬스(LangChain 0건) → **관련성/세이프티 필터는 6.2**. 6.1은 수집·격리·dedup·관측까지만.

### 라이브러리 / 버전

- **feedparser** (신규): RSS/Atom 파서, 순수 파이썬, 표준 라이브러리 관용. 최신 6.0.11. `feedparser.parse(bytes|str)` — `entries[i].title`, `.link` 사용. 네트워크는 하지 않음(바이트를 받아 파싱만) → httpx로 받아 넘기면 테스트가 오프라인 가능.
- **httpx==0.28.1** (기존 재사용): 동기 `httpx.Client`. `verify` 인자에 CA 경로/`ssl.SSLContext` 전달 가능. 기본도 certifi지만 AC 충족 위해 명시.
- **certifi** (명시 핀): `certifi.where()` → CA 번들 경로.
- **금지:** requests(httpx 표준), 외부 벡터 DB, 신규 OpenAI 호출, DB 마이그레이션.

### 파일 구조 (신규/수정)

```
api/pipeline/collector/
  base.py            (기존, 예외계약 주석 명확화 — 선택)
  stub.py            (기존, 유지)
  registry.py        (신규 — 활성 소스 목록 + 어댑터 팩토리)
  rss.py             (신규 — RssCollector)
  hackernews.py      (신규 — HackerNewsCollector)
  github.py          (신규 — GitHubReleasesCollector)
  aggregator.py      (신규 — 격리 순회 + exact dedup + 로깅)
api/pipeline/orchestrator.py   (수정 — collector_mode 분기)
api/core/config.py             (수정 — collector_mode, collector_timeout_seconds)
api/requirements.txt           (수정 — feedparser, certifi)
api/.env.example               (수정 — 신규 설정 주석)
api/tests/test_collector_real.py (신규)
```

### 테스트 표준

- **프레임워크:** pytest 8.3.4, `pytest.ini`(`testpaths=tests`, `asyncio_mode=auto`). 파일명 `test_*.py`, `api/tests/`에 위치.
- **오프라인 원칙:** 실제 네트워크 호출 금지 — `httpx.Client.get`을 `unittest.mock`(`MagicMock`/`patch`/`monkeypatch`)으로 대체하고 고정 RSS/Atom 문자열·HN JSON 픽스처 주입(기존 `test_pipeline_foundation.py`가 Supabase를 MagicMock으로 대체하는 패턴 참고). respx 미설치 — 도입하지 말고 monkeypatch 사용.
- **커버리지 대상:** 어댑터 매핑, 격리(한 소스 예외 → 나머지 반환), dedup(URL+정규화 제목), certifi/timeout 인자 전달, orchestrator 분기(stub/real).
- **회귀:** `cd api && pytest -q` 전체 통과. 특히 `test_pipeline_foundation.py`(StubCollector) 그린 유지.

### Project Structure Notes

- 백엔드는 `api/` 루트에서 실행(`pytest.ini`, `requirements.txt` 위치). import는 `pipeline.*`, `core.*` (PYTHONPATH=`api`). 로컬 실행/DB 접속은 [[local-run-setup]] 참고.
- 소스 레지스트리는 **코드 상수**로 시작 — DB 소스 테이블은 명시적으로 Story 6.3/미래 스코프. 6.1에서 마이그레이션·`list_tables` 변경 금지.
- 충돌/변이: 없음. 신규 파일 위주 + orchestrator 1개 분기 + config 2필드 추가.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.1: 실 수집기 어댑터 & 소스 레지스트리 (L904-925)]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 6 (L891-902), FR-8.1~8.5 (L53-57, L896-900)]
- [Source: architecture/.../ARCHITECTURE-SPINE.md#AD-16 외부 콘텐츠 수집 패턴 (L308-311)]
- [Source: architecture/.../ARCHITECTURE-SPINE.md#AD-5 (L155), #AD-12 (L252-255), #AD-15 (L273-276), #Deferred(Source별 수집 API 방식) (L328)]
- [Source: api/pipeline/collector/base.py, stub.py, models.py]
- [Source: api/pipeline/orchestrator.py L7,46-53 / normalizer.py / logger.py]
- [Source: api/core/config.py, api/requirements.txt, api/tests/test_pipeline_foundation.py]
- [Source: _bmad-output/planning-artifacts/research/spike-rss-2026-07-29.py (throwaway 레퍼런스)]
- [Source: _bmad-output/implementation-artifacts/deferred-work.md L164-175 (Collector/dedup/오케스트레이터 하드코딩), L228-233 (normalizer 예외 삼킴)]
- [Source: _bmad-output/implementation-artifacts/db/001_initial_schema.sql L153-174 (signals/signal_sources 스키마 — 6.1은 무변경)]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Opus 4.8) — BMad dev-story workflow

### Debug Log References

- 회귀 실패 1건 → 수정: `test_recommender_pipeline.py::test_run_daily_pipeline_calls_stages_in_order`. 원인은 `collector_mode` 기본값을 `"real"`로 두어 orchestrator가 `StubCollector.collect` 패치를 우회(실 네트워크 경로 진입). orchestrator 테스트 2건을 `settings.collector_mode="stub"`으로 고정해 stub 경로·오프라인 보장으로 해결. 최종 `pytest -q` → 179 passed.

### Completion Notes List

- **AC1**: `registry.py`(RSS 5 + HN + GitHub Releases 1, `enabled` 토글) + 3개 어댑터(`RssCollector`/`HackerNewsCollector`/`GitHubReleasesCollector`, 모두 `BaseCollector.collect()→list[RawArticle]`). aggregator가 공유 `httpx.Client(verify=certifi.where(), timeout=settings.collector_timeout_seconds, follow_redirects=True, User-Agent)`를 생성해 어댑터에 주입.
- **AC2**: `run_collectors()`가 어댑터별 호출을 try/except로 격리 — 실패 시 `source_failed`(level=error) 로깅 후 다음 소스 계속, 성공 시 `source_collected`(article_count). `BaseCollector` 예외 계약을 "어댑터는 던지고 aggregator가 격리"로 명문화(base.py docstring).
- **AC3**: exact dedup = 정확 URL + 정규화 제목(`strip().lower()`) 셋. `dedup_done`(removed, total) 로깅.
- **AC4**: orchestrator collect 단계를 `settings.collector_mode` 분기(real=`run_collectors`, stub=`StubCollector`)로 교체. 이후 `normalize→build→review→recommender` 흐름·로그 이벤트명 불변. 0건 수집 시 `normalize([])→[]`로 예외 없이 완료(`error=None`) — 테스트로 검증. `run_ondemand_brief` 무수정.
- **스코프 준수**: normalizer/models/DB 스키마 무변경, 임베딩·pgvector·LLM·마이그레이션 미도입(6.2/6.3/6.4 스코프). `StubCollector` 삭제하지 않고 stub 모드로 존속.
- **참고(6.2로 이월)**: `derive_tech` 휴리스틱은 임시 스톱갭 — 매치 없으면 `"General AI"`로 뭉치는 한계(스파이크에서 확인)는 6.2 의미 클러스터링이 근본 해결. 관련성/세이프티 필터도 6.2. httpx 0.28에서 `verify=<str>` deprecation 경고가 있으나 AC(`certifi.where()` 명시)·기능상 정상.

### File List

- `api/pipeline/collector/registry.py` (신규 — 소스 레지스트리 + `build_collectors` 팩토리)
- `api/pipeline/collector/rss.py` (신규 — `RssCollector` + `derive_tech` 휴리스틱)
- `api/pipeline/collector/hackernews.py` (신규 — `HackerNewsCollector`, HN Algolia https)
- `api/pipeline/collector/github.py` (신규 — `GitHubReleasesCollector`)
- `api/pipeline/collector/aggregator.py` (신규 — `run_collectors` 격리 순회 + exact dedup + 로깅)
- `api/pipeline/collector/base.py` (수정 — 예외 계약 docstring 명확화)
- `api/pipeline/orchestrator.py` (수정 — `collector_mode` 분기)
- `api/core/config.py` (수정 — `collector_mode`, `collector_timeout_seconds`)
- `api/requirements.txt` (수정 — feedparser==6.0.13, certifi==2026.07.22)
- `api/.env.example` (수정 — 신규 설정 주석)
- `api/tests/test_collector_real.py` (신규 — 16 테스트: 매핑/격리/dedup/certifi·timeout/orchestrator 분기)
- `api/tests/test_recommender_pipeline.py` (수정 — orchestrator 테스트 2건 stub 모드 고정)

## Change Log

- 2026-07-29: Story 6.1 구현 완료 — StubCollector를 실 수집기(RSS/HN/GitHub) + 소스 레지스트리 + 격리 + exact dedup으로 대체, orchestrator `collector_mode` 분기 배선. 신규 6파일 + 수정 6파일, 신규 테스트 16건, 전체 회귀 179 passed. Status → review. (claude-opus-4-8)
