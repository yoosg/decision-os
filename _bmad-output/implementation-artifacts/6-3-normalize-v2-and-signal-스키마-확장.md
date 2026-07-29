---
baseline_commit: NO_VCS
---

# Story 6.3: normalize v2 & Signal 스키마 확장

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

개발자로서,
6.2가 만든 **클러스터(다중 출처 토픽)를 `signals` 테이블에 랭킹 메타데이터(발행 시각·인기·출처 권위·클러스터 식별키)와 함께 저장**하고 싶다,
그래서 다음 스토리(6.4 Recommender v2)가 최신성·인기·출처 권위를 실제 데이터로 랭킹에 쓸 수 있고, 같은 날 재실행해도 클러스터 단위로 중복 없이 dedup된다.

> **🍎 프론트엔드 비유 (오너용):** 지금까지의 파이프라인을 "뉴스 편집국"에 비유하면,
> - **6.1**은 여러 매체에서 기사를 긁어오는 **취재**,
> - **6.2**는 같은 사건 기사끼리 묶고(클러스터) 광고·스팸을 버리는 **데스크 정리**,
> - **6.3(이 스토리)**은 그렇게 묶은 "토픽 카드"를 **신문 DB에 저장할 때, 카드에 메타 정보 스티커를 붙이는 일**이다.
> - 지금은 카드에 `제목`·`기술이름`·`날짜`만 붙는다. 6.3은 여기에 **"이 사건이 실제로 언제 터졌나(published_at)", "얼마나 화제인가(인기=HN 추천수 등)", "출처가 얼마나 믿을 만한가(공식 블로그 > 깃허브 > 커뮤니티)", "어느 클러스터에서 왔나(cluster_key)"** 스티커를 추가한다.
> - 왜 필요하냐면, 다음 편집자(6.4 추천 엔진)가 "오래된 뉴스보다 최신을, 아무도 안 보는 것보다 화제인 것을, 루머보다 공식 발표를" 위로 올리려면 이 스티커가 카드에 **미리 붙어 있어야** 하기 때문이다. 스티커 붙이는 일(6.3)과 그걸 보고 순위 매기는 일(6.4)은 분리한다.
> - DB 컬럼을 추가하므로, 프론트로 치면 **"기존 테이블/타입에 새 필드를 추가하는 마이그레이션"** 이다. 기존 데이터는 기본값으로 채워지고, 기존 화면(consumer)은 새 필드를 몰라도 안 깨진다.

## Acceptance Criteria

**AC1 — Signal 스키마 확장 마이그레이션 (FR-8.4 준비)**
- **Given** 새 마이그레이션 파일(`supabase/migrations/`)을 실행하면
- **Then** `public.signals`에 다음 컬럼이 **가산적(additive)** 으로 추가된다:
  - `published_at TIMESTAMPTZ` (nullable) — 클러스터 내 원문 최신 발행 시각(UTC)
  - `popularity INTEGER NOT NULL DEFAULT 0` — 인기 신호 집계(예: HN points 합)
  - `source_authority SMALLINT NOT NULL DEFAULT 0` — 클러스터 내 최고 출처 권위 등급(0~4)
  - `cluster_key TEXT` (nullable) — 6.2 클러스터 식별키(다중 출처 토픽 lineage)
- **And** 기존 행은 기본값(`published_at=NULL`, `popularity=0`, `source_authority=0`, `cluster_key=NULL`)으로 안전하게 채워진다(백필 불필요, 무회귀)
- **And** 최신성 랭킹용 인덱스 `idx_signals_published_at (published_at DESC NULLS LAST)`가 생성된다
- **And** **클러스터 기반 dedup 보완**을 위해 `UNIQUE (cluster_key, signal_date) WHERE cluster_key IS NOT NULL` 부분 UNIQUE 인덱스가 추가된다 — 기존 `uq_signals_technology_date`(technology_name, signal_date)는 **유지**(전환이 아니라 보완, AC 문구 "전환/보완" 중 보완 채택 — Dev Notes "설계 결정 D2")

**AC2 — normalize v2: 클러스터당 1 Signal + N signal_sources + 메타데이터 기록 (FR-8.2/8.4)**
- **Given** 6.2 `cluster_and_filter`가 반환한(각 클러스터=배치 내 고유 `technology_name` 라벨 + `cluster_key`를 가진) `list[RawArticle]`이 있을 때
- **When** `normalize()` v2가 실행되면
- **Then** 클러스터(=라벨)당 `signals` row 1개 + 멤버 수만큼 `signal_sources` row N개가 저장된다 (기존 동작 유지)
- **And** 저장되는 `signals` row에 다음 메타데이터가 **클러스터 멤버 집계로** 기록된다:
  - `published_at` = 멤버들의 `published_at` 중 **최댓값(가장 최신)**. 멤버 모두 값이 없으면 `NULL`
  - `popularity` = 멤버들의 `popularity` **합**
  - `source_authority` = 멤버들의 `source_type`을 등급 매핑(`official_blog`=4 > `github`=3 > `hn`=2 > `reddit`=1 = `youtube`=1 > `other`=0)한 값의 **최댓값**
  - `cluster_key` = 멤버들의 `cluster_key`(클러스터 내 동일; 없으면 `NULL`)
- **And** upsert는 기존과 동일하게 `on_conflict="technology_name,signal_date", ignore_duplicates=True`를 유지한다(같은 날 재실행 시 중복 생성 없음 — 신규 컬럼은 최초 insert 시에만 기록, 재실행 시 no-op은 허용/문서화)

**AC3 — 메타데이터 출처(published_at·popularity)를 수집기에서 실제로 확보 (FR-8.1 확장)**
- **Given** 현재 `RawArticle`에는 `published_at`·`popularity` 필드가 없고, 수집기(RSS/HN)가 이 값을 버리고 있을 때
- **When** 6.3이 이를 확장하면
- **Then** `RawArticle`에 `published_at: datetime | None = None`, `popularity: int = 0`, `cluster_key: str | None = None` 필드가 **기존 필드 뒤에 기본값과 함께** 추가된다(positional 생성 기존 테스트 무회귀 — Dev Notes "회귀 주의")
- **And** **RSS 수집기**는 `entry.published_parsed`(있으면)를 UTC `datetime`으로 변환해 `published_at`에 채운다(없으면 `None`)
- **And** **HackerNews 수집기**는 `hit["points"]`를 `popularity`에, `hit["created_at_i"]`(unix) 또는 `created_at`(ISO)를 `published_at`에 채운다(없으면 각각 `0`/`None`)
- **And** 6.2 클러스터링은 재라벨(`dataclasses.replace`) 시 `technology_name`·`cluster_key`만 바꾸므로 `published_at`·`popularity`는 **자동으로 보존**된다(clustering.py의 임베딩/필터 로직은 변경하지 않음 — cluster_key 부여만 추가)

**AC4 — 무회귀 & 다운스트림 안전 (AD-5, AD-15)**
- **Given** 신규 컬럼 추가 후
- **When** 기존 소비자(`signal_builder`=`SELECT *`, `recommender`=명시 컬럼 `id,technology_name,title,summary`, `run_ondemand_brief`=`id`)가 실행되면
- **Then** 어느 소비자도 깨지지 않는다(가산 컬럼은 명시 SELECT에 안 잡히고, `SELECT *`는 무시). Recommender가 신규 컬럼을 **사용**하는 것은 6.4 스코프 — 이 스토리는 저장까지만
- **And** `published_at`/`popularity`를 만들 수 없는 경로(예: 임베딩 실패 pass-through 기사, stub 수집기, 값 없는 RSS)에서도 예외 없이 안전 저하(`None`/`0`)로 저장된다
- **And** `cd api && pytest -q` 전체 회귀(현재 **192 passed**) 통과 + 신규 테스트 추가

> ⚠️ **스코프 경계 (중요):** 이 스토리는 **스키마 마이그레이션 + normalize v2 메타데이터 집계·저장 + RawArticle/수집기 메타데이터 확보 + cluster_key 부여**까지만 한다.
> - **하지 말 것:** Recommender **점수식 변경**(published_at/popularity/source_authority를 랭킹에 *사용*, MMR·최신성 감쇠 → **6.4**), 콜드스타트 임베딩 전환(**6.4**), Memory RAG weight 재검토(**6.4**), engagement 로깅·측정 하네스(**6.5**), 외부 벡터 DB 도입, 6.2 임베딩/클러스터링/필터 **판정 로직** 변경(6.3은 clustering에 `cluster_key` 부여 한 줄만 추가).
> - **`technology_name` 기반 upsert dedup을 cluster_key 기반으로 완전 전환하지 말 것** — cluster_key는 nullable(pass-through 기사는 null)이라 upsert 키로 쓰면 null 처리가 복잡해진다. cluster_key는 **저장·부분 UNIQUE 보완**만, 실제 dedup 키는 기존 (technology_name, signal_date) 유지(D2).

## Tasks / Subtasks

- [x] **Task 1 — 마이그레이션 작성** (AC: 1)
  - [x] `supabase/migrations/20260731000000_signals_schema_v2.sql` 신규 (파일명 timestamp는 기존 최신 `20260730000000`보다 뒤 — 정렬 순서 보장)
  - [x] `ALTER TABLE public.signals ADD COLUMN IF NOT EXISTS ...` 4개(published_at, popularity, source_authority, cluster_key) — 모두 `IF NOT EXISTS`, NOT NULL 컬럼은 `DEFAULT` 명시(기존 행 백필)
  - [x] `CREATE INDEX IF NOT EXISTS idx_signals_published_at ON public.signals(published_at DESC NULLS LAST);`
  - [x] `CREATE UNIQUE INDEX IF NOT EXISTS uq_signals_cluster_date ON public.signals(cluster_key, signal_date) WHERE cluster_key IS NOT NULL;`
  - [x] 상단 주석에 "왜/무엇을"(6.3 랭킹 메타데이터, 6.4가 소비) + 기존 `uq_signals_technology_date` 유지 이유 기록 (기존 마이그레이션 주석 스타일 따를 것 — `20260730000000_signals_unique_technology_date.sql` 참고)
  - [x] **적용:** Supabase MCP `apply_migration`으로 원격 적용 완료(오너 승인). 4개 컬럼·2개 인덱스 생성 확인, 기존 `uq_signals_technology_date` 유지 확인, 기존 11행 DEFAULT 백필. (Completion Notes 기록)

- [x] **Task 2 — RawArticle 메타데이터 필드 확장** (AC: 3)
  - [x] `api/pipeline/models.py` `RawArticle`에 **기존 필드 뒤에** 추가: `published_at: datetime | None = None`, `popularity: int = 0`, `cluster_key: str | None = None`
  - [x] `from datetime import datetime` import 추가
  - [x] ⚠️ **필드는 반드시 `content` 뒤(맨 끝)에 기본값과 함께** 추가 — 기존 테스트가 positional 생성(`RawArticle("MCP", "title", "url", "official_blog")`)을 쓰므로 순서 변경 시 대량 회귀(Dev Notes "회귀 주의")

- [x] **Task 3 — 수집기에서 메타데이터 확보** (AC: 3)
  - [x] `api/pipeline/collector/rss.py`: `feed.entries` 순회 시 `getattr(entry, "published_parsed", None)`(time.struct_time)를 `datetime(*st[:6], tzinfo=timezone.utc)`로 변환해 `RawArticle(..., published_at=...)`. 없거나 파싱 실패 → `None`(try/except로 격리, 수집 자체는 계속). `popularity`는 RSS에 없음 → 기본 0
  - [x] `api/pipeline/collector/hackernews.py`: `hit.get("points")` → `popularity`(int, None이면 0), `hit.get("created_at_i")`(unix 초) → `datetime.fromtimestamp(v, tz=timezone.utc)`; 없으면 `hit.get("created_at")`(ISO8601) 파싱 시도, 둘 다 없으면 `None`
  - [x] `api/pipeline/collector/github.py`: **무변경으로 충족** — GitHubReleasesCollector가 RssCollector.collect()를 상속하므로 releases.atom 엔트리의 `published_parsed`가 rss.py 변경으로 자동 채워짐(과설계 회피). Completion Notes 명시
  - [x] `api/pipeline/collector/stub.py`: stub 기사는 `published_at=None, popularity=0` 유지(값 강제 주입 불필요) — normalize v2가 None/0 안전 저하로 처리
  - [x] **파싱은 반드시 방어적으로**(외부 데이터 형식 변동 대비): 개별 필드 파싱 실패가 그 기사/소스 수집을 중단시키지 않도록 try/except 격리 후 안전 기본값(AD-5)

- [x] **Task 4 — clustering에 cluster_key 부여** (AC: 2, 3)
  - [x] `api/pipeline/clustering.py` `_relabel()`: 각 클러스터에 **결정론적 `cluster_key`** 부여 후 멤버 재생성 시 `replace(a, technology_name=label, cluster_key=key)`
  - [x] `cluster_key` 계산: 클러스터 멤버 url을 정렬·조인해 짧은 해시 — `hashlib.sha1("\n".join(sorted(m[0].url for m in members)).encode()).hexdigest()[:16]` (헬퍼 `_cluster_key`로 분리)
  - [x] `import hashlib` 추가
  - [x] pass-through(임베딩 실패) 기사는 클러스터를 안 거치므로 `cluster_key=None` 유지 — normalize는 technology_name 경로로 처리(정상)
  - [x] ⚠️ clustering의 **임베딩·필터·greedy 병합 판정 로직은 변경 금지** — cluster_key 부여만 추가. `published_at`/`popularity`는 `replace`가 자동 보존

- [x] **Task 5 — normalize v2: 메타데이터 집계·저장** (AC: 2, 4)
  - [x] `api/pipeline/normalizer.py`: 그룹핑·upsert·signal_sources insert **골격 유지**. upsert payload에 신규 4개 컬럼 추가
  - [x] 그룹(클러스터) 단위 집계 헬퍼 `_aggregate_metadata` 추가(published_at=max, popularity=sum, source_authority=max등급, cluster_key=첫 멤버)
  - [x] 모듈 상수 `_SOURCE_AUTHORITY = {"official_blog": 4, "github": 3, "hn": 2, "reddit": 1, "youtube": 1, "other": 0}` 추가
  - [x] upsert dict에 신규 4개 컬럼 추가
  - [x] `signal_created` 로그에 `published_at`/`popularity`/`source_authority` 추가 — 관측성(AD-12)
  - [x] ⚠️ `ignore_duplicates=True`라 conflict 시 신규 컬럼 no-op(최초 insert 시에만 기록) — MVP 허용(D4). Completion Notes 명시

- [x] **Task 6 — 테스트** (AC: 1, 2, 3, 4)
  - [x] `api/tests/test_pipeline_foundation.py` 확장: 집계 검증(published_at=max, popularity=sum, authority=최고, cluster_key) + None/0 안전 저하 + RawArticle 필드 기본값/값지정. 기존 normalize 4테스트 무회귀
  - [x] `api/tests/test_clustering.py` 확장: cluster_key 부여(non-null, 클러스터 내 동일)·결정론·클러스터별 distinct·`replace` 후 published_at/popularity 보존
  - [x] `api/tests/test_collector_real.py` 확장: RSS `published_parsed`→UTC, 없으면 None; HN `points`→popularity·`created_at_i`→published_at·`created_at` ISO 폴백·메타 부재 안전저하. 오프라인 원칙(httpx mock)
  - [x] **회귀:** `cd api && pytest -q` → **202 passed**(192 baseline + 10 신규). 마이그레이션은 MCP 적용으로 검증(컬럼·인덱스 존재 SQL 확인)

### Review Findings

<!-- bmad-code-review 2026-07-29 — Blind Hunter + Edge Case Hunter + Acceptance Auditor (3 layers, 0 failed). AC1~AC4 전부 충족 확인. -->

- [x] [Review][Patch] pass-through 라벨이 relabeled 클러스터 라벨과 충돌해 별개 토픽이 1 signal로 병합될 수 있음 — pass-through(임베딩 실패) 기사의 원본 `technology_name`을 `_relabel`의 `used` 집합에 미리 등록(seed)해 relabeled 클러스터가 겹치면 판별자 라벨을 받도록 수정(오너 결정: 옵션1). D2 "1클러스터=1시그널" 불변식을 pass-through까지 확장. [api/pipeline/clustering.py:189-246]
- [x] [Review][Patch] `_cluster_key`가 멤버 url을 dedup하지 않아 동일 url 중복 시 "같은 멤버집합 ⇒ 같은 key" 계약이 깨짐 — `sorted(set(...))`으로 수정 [api/pipeline/clustering.py:185]
- [x] [Review][Patch] `_aggregate_metadata`의 `max(published_dts)`가 naive/aware datetime 혼재 시 TypeError로 배치 전체 중단(try 밖 호출) — 현재 수집기는 항상 aware라 미도달이나 타입(`datetime | None`)은 naive를 허용하므로 방어적으로 aware 정규화 후 max [api/pipeline/normalizer.py:29-30]
- [x] [Review][Defer] HN `created_at_i` 밀리초/미래 timestamp에 sanity 상한이 없어 `max()` 오염 가능 [api/pipeline/collector/hackernews.py:34-54] — deferred, 외부 형식 변동(Algolia 초→밀리초) 대비 방어. 현재 형식에선 미도달
- [x] [Review][Defer] `uq_signals_cluster_date` 비-CONCURRENT UNIQUE 인덱스 — signals 테이블 대형화 시 빌드 중 쓰기 잠금 [supabase/migrations/20260731000000_signals_schema_v2.sql:34-36] — deferred, MVP 소규모 테이블에선 무해. 스케일 이후 재검토

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Code, bmad-dev-story)

### Debug Log References

- 회귀 baseline: `cd api && pytest -q` → 192 passed (착수 전 확인)
- 소스 변경 후: 192 passed (무회귀 확인)
- 신규 테스트 추가 후: **202 passed** (10 신규 전부 green)
- 마이그레이션 검증: `information_schema.columns` → 4개 신규 컬럼 확인, `pg_indexes` → `idx_signals_published_at`·`uq_signals_cluster_date`·`uq_signals_technology_date`(기존 유지) 확인

### Completion Notes List

- **오너 결정 D1 = A안 채택:** RSS/HN 수집기 + RawArticle 확장으로 실제 발행시각·HN points를 확보(스텁 대신 실데이터). 6.4가 진짜 최신성·인기로 랭킹할 수 있게 함.
- **마이그레이션 원격 적용 완료(오너 승인):** Supabase MCP `apply_migration`으로 원격 `public.signals`에 반영. 가산 컬럼 4개(published_at nullable, popularity int NOT NULL DEFAULT 0, source_authority smallint NOT NULL DEFAULT 0, cluster_key text nullable) + 인덱스 2개 생성. 기존 11행은 DEFAULT로 안전 백필(popularity=0, source_authority=0, 나머지 NULL). 기존 `uq_signals_technology_date` 유지(dedup 키 불변, D2). `supabase/migrations/`의 .sql 파일도 함께 커밋되어 로컬/재현 경로 일치.
- **github.py 무변경:** GitHubReleasesCollector가 RssCollector.collect()를 상속 → rss.py의 published_at 파싱이 releases.atom에도 자동 적용(과설계 회피).
- **D4 한계 명시(MVP 허용):** normalize의 `upsert(..., ignore_duplicates=True)`는 conflict 시 no-op이라, 같은 (technology_name, signal_date)가 이미 있으면 신규 메타데이터가 **갱신되지 않고 최초 insert 시에만 기록**됨. 하루 1배치 멱등성 유지가 목적이며, 재실행 시 최신 published_at/popularity로 갱신하는 update 경로는 6.4/후속에서 필요 시 도입.
- **스코프 준수:** recommender.py·signal_builder.py·orchestrator.py 무변경(6.4가 신규 컬럼을 랭킹에 *사용*). clustering의 임베딩/필터/greedy 판정 로직 무변경 — cluster_key 부여만 추가.

### File List

- `supabase/migrations/20260731000000_signals_schema_v2.sql` (신규)
- `api/pipeline/models.py` (수정 — RawArticle +3 필드, datetime import)
- `api/pipeline/normalizer.py` (수정 — `_SOURCE_AUTHORITY` 상수, `_aggregate_metadata` 헬퍼, upsert payload 4컬럼, signal_created 로그 확장)
- `api/pipeline/clustering.py` (수정 — `_cluster_key` 헬퍼, `_relabel`에서 cluster_key 부여, hashlib import)
- `api/pipeline/collector/rss.py` (수정 — `_entry_published_at` 헬퍼, published_at 채움, datetime import)
- `api/pipeline/collector/hackernews.py` (수정 — `_hit_popularity`·`_hit_published_at` 헬퍼, popularity·published_at 채움, datetime import)
- `api/tests/test_pipeline_foundation.py` (수정 — RawArticle 필드 확장 + normalize v2 집계·안전저하 테스트 4개)
- `api/tests/test_clustering.py` (수정 — cluster_key 부여·결정론·메타 보존 테스트 3개)
- `api/tests/test_collector_real.py` (수정 — RSS/HN 메타데이터 파싱 테스트 3개)

## Dev Notes

### 아키텍처 준수 (반드시 따를 것)

- **AD-16 (외부 콘텐츠 수집 패턴):** "하나의 Signal = 하나의 기술/변화 + 다출처 묶음." 6.3은 이 다출처 묶음(클러스터)을 **DB에 스키마화**하는 단계다. 6.2가 인프로세스로 만든 클러스터를 `cluster_key`로 영속화해 lineage를 남긴다. 어댑터 인터페이스(`collect() → list[RawArticle]`)는 유지하되, RawArticle의 **데이터 필드만** 확장(메서드/계약 불변).
- **AD-2 / AD-6 (pgvector 전용, 외부 벡터 DB 금지):** 6.3은 벡터를 새로 저장하지 않는다(기사 임베딩 영속화는 여전히 스코프 밖). `published_at`/`popularity`는 스칼라 컬럼. **신규 벡터 DB·임베딩 컬럼 추가 금지.**
- **AD-5 (격리 / safe degradation):** 수집기의 개별 필드 파싱 실패(깨진 날짜·누락 points)는 격리 → 안전 기본값(None/0). normalize의 집계도 값 없는 멤버를 건너뛰고 계속. 한 기사 때문에 배치가 죽으면 안 된다.
- **AD-12 (관찰 가능성):** normalize의 `signal_created` 로그에 신규 메타데이터 추가. 마이그레이션 SQL 상단 주석에 의도 기록.
- **AD-15 (Batch First):** 6.3은 `run_daily_pipeline`의 normalize 단계 내부. `run_ondemand_brief`는 collect/normalize를 건너뛰므로 **무관**(회귀만 확인).

### 설계 결정 (Dev가 반드시 이 방향으로 구현)

**D1 — published_at·popularity의 출처: 수집기 확장 (✅ 이 스토리의 채택 방향, 오너 확인 대상):**
AC2는 "published_at은 클러스터 내 최신 기사 기준, 인기는 소스 신호 집계"를 요구한다. 그런데 현재 `RawArticle`은 이 값을 **담지 않고**, 수집기(rss/hn)가 `published_parsed`·`points`를 **버린다**. 따라서 AC를 충실히 충족하려면 값의 출처가 필요하다.
- **채택:** `RawArticle`에 필드 추가 + RSS/HN 수집기가 실제 발행시각·points를 채운다(Task 2·3). 이유: **6.4 Recommender v2가 최신성·인기를 실제 데이터로 랭킹**하는 것이 Epic 6의 핵심 목표(FR-8.4)인데, 여기서 값을 스텁(published_at=signal_date, popularity=source count)으로 채우면 6.4가 **조용히 가짜 신호로 랭킹**하게 된다.
- **대안(미채택) B:** 수집기·RawArticle 무변경, normalize에서 `published_at=signal_date`, `popularity=len(sources)`(소스 개수)로 계산. 스코프는 작지만 "최신성"이 하루 단위로 뭉개지고(같은 signal_date=동일 값) points 기반 인기를 못 씀 → 6.4 품질 저하 위험. **소스 개수도 "소스 신호 집계"의 한 해석이라 AC 문구상 완전 위반은 아님** — 그래서 오너 판단 대상(스토리 말미 질문).
- 이 스토리 파일은 **A(수집기 확장)** 를 전제로 작성됨. 오너가 B를 택하면 Task 2·3을 축소하고 normalize 집계를 signal_date/소스개수로 바꾸면 됨(나머지 구조 동일).

**D2 — cluster_key: 전환이 아니라 "보완" (dedup 키는 technology_name 유지):**
AC1은 "시그널 식별을 클러스터 기반으로 전환/보완"이라 했다. **보완**을 채택한다:
- `cluster_key`를 **저장**하고 `UNIQUE(cluster_key, signal_date) WHERE cluster_key IS NOT NULL` 부분 인덱스로 클러스터 dedup을 **보강**한다.
- 하지만 normalize의 **upsert dedup 키는 기존 `(technology_name, signal_date)` 유지**한다. 이유: (1) 6.2가 이미 클러스터당 배치 내 고유 technology_name 라벨을 보장하므로 technology_name 그룹핑 = 클러스터 그룹핑이다. (2) `cluster_key`는 pass-through 기사에서 **null**이라 upsert 충돌 키로 쓰면 null 다중행 처리가 지저분하다. (3) 기존 `uq_signals_technology_date`(20260730)를 깨지 않아 무회귀.
- 즉 cluster_key는 **lineage·관측·6.4용 메타데이터 + 부분 UNIQUE 안전망**이지, 이 스토리에서 dedup 주체를 바꾸는 게 아니다. 완전 전환(cluster_key 단일 키화)은 후속 스토리/리팩터에서 raw 기사 영속화와 함께 재검토.

**D3 — source_authority는 SMALLINT 등급(0~4):**
"소스 권위"를 별도 룩업 테이블/문자열이 아니라 **source_type 파생 정수 등급**으로 저장한다(`official_blog`=4 > `github`=3 > `hn`=2 > `reddit`=`youtube`=1 > `other`=0). 이유: 6.4가 랭킹 피처로 바로 곱/가중하기 쉽고, 계산이 signal_sources에서 결정론적. 클러스터 내 **최고 등급**을 저장(다출처 중 가장 권위 있는 소스가 그 토픽의 신뢰도 대표). 등급 값·매핑은 튜닝 대상이나 이 스토리에선 위 고정값으로 시작.

**D4 — 신규 컬럼은 최초 insert 시에만 기록(ignore_duplicates no-op 허용):**
`upsert(..., ignore_duplicates=True)`는 conflict 시 아무 것도 안 하고 빈 data 반환 → normalizer가 스킵. 따라서 같은 (technology_name, signal_date)가 이미 있으면 신규 메타데이터는 **갱신되지 않는다**. MVP에서는 허용(멱등·단순, 하루 1배치). 재실행 시 최신 published_at/popularity로 갱신하는 upsert(update 경로)는 6.4/후속에서 필요 시 도입. 이 한계를 Completion Notes에 명시.

### 수집할 기존 파일 — 현재 상태 / 변경 / 보존

- **`supabase/migrations/`** (신규 파일 1): 파일명 규칙 `YYYYMMDDhhmmss_name.sql`. 최신은 `20260730000000_signals_unique_technology_date.sql`. 신규는 `20260731000000_signals_schema_v2.sql`. 주석 스타일(왜/증상/해결) 참고. 초기 스키마의 signals 정의는 `20260723000000_initial_schema.sql` L158-168.
- **`api/pipeline/models.py`** (변경): 현재 `RawArticle(technology_name, title, url, source_type, content="")` — 5필드. 뒤에 3필드 추가(default 포함). `datetime` import. **순서 절대 앞당기지 말 것**(positional 생성 회귀).
- **`api/pipeline/normalizer.py`** (변경 — 이 스토리의 핵심): 현재 `groups.setdefault(technology_name)` → upsert(on_conflict, ignore_duplicates) → signal_sources insert. 골격 유지, upsert payload에 4컬럼 + 집계 헬퍼 + `_SOURCE_AUTHORITY` 상수 추가. 빈 technology_name 스킵·에러 격리 로직 **보존**.
- **`api/pipeline/clustering.py`** (변경 — 최소): `_relabel()`에서 `replace(a, technology_name=label)` → `replace(a, technology_name=label, cluster_key=key)`. `import hashlib`. **임베딩/필터/greedy 로직(L47-151) 무변경.** `published_at`/`popularity`는 replace가 자동 보존.
- **`api/pipeline/collector/rss.py`** (변경): `collect()` 엔트리 루프에서 `published_parsed` → UTC datetime. `derive_tech`·bozo 처리·`_MAX_PER_FEED` 등 **기존 로직 보존**.
- **`api/pipeline/collector/hackernews.py`** (변경): hit에서 `points`/`created_at_i` 매핑. 격리·URL 폴백·`_MAX_HN` 등 **보존**.
- **`api/pipeline/collector/github.py`** (선택적 변경): 발행시각 저비용이면 채우고 아니면 None. 과설계 금지.
- **`api/pipeline/collector/stub.py`** (보존): 값 미주입(None/0). normalize가 안전 저하.
- **`api/pipeline/signal_builder.py`** (보존, 무변경): `SELECT *`로 signals 읽고 title/summary/status만 update → 신규 컬럼 자동 무시. 안전.
- **`api/pipeline/recommender.py`** (보존, 무변경 — 이 스토리): `SELECT id,technology_name,title,summary`만 함 → 신규 컬럼 미조회. **6.4에서** 여기 select에 published_at/popularity/source_authority 추가하고 점수식에 반영. 지금 건드리지 말 것.
- **`api/pipeline/orchestrator.py`** (보존, 무변경): normalize 호출 시그니처 불변(`normalize(articles, today, client, brief_date=...)`).

### 라이브러리 / 버전

- **신규 의존성 없음.** 표준 라이브러리 `datetime`(`datetime`, `timezone`), `hashlib`, `time`(struct_time 변환)만. `feedparser`(이미 6.1에서 사용)의 `published_parsed`. **numpy·외부 벡터 DB 금지**(6.2와 동일 원칙).
- DB: Supabase Postgres + pgvector(기존). 마이그레이션은 순수 DDL(`ALTER TABLE ADD COLUMN`, `CREATE INDEX`). pgvector 미사용.

### 회귀 주의 (반드시 확인)

- **positional RawArticle 생성:** `test_pipeline_foundation.py`가 `RawArticle("LangGraph", "Title", "url", "official_blog")`처럼 **위치 인자**로 생성한다(L88-159). 신규 필드를 **반드시 `content` 뒤에 default와 함께** 추가해야 이 테스트들이 안 깨진다. 필드 순서를 바꾸면 대량 회귀.
- **normalize upsert 인자 변경:** upsert dict에 키를 추가하는 것은 기존 테스트(반환값·호출 여부만 검증)에 무해하나, `call_args`로 payload를 정밀 검증하는 신규 테스트를 추가할 때 기존 `_make_mock_client`(`test_pipeline_foundation.py` L60-86)를 재사용할 것.
- **소비자 무회귀:** signal_builder(SELECT *), recommender(명시 컬럼), ondemand(id) 모두 신규 컬럼에 무영향. `daily_brief_signals`·`reviews`·`learning_paths`의 signal FK도 컬럼 추가와 무관.
- **마이그레이션 멱등:** 모든 DDL에 `IF NOT EXISTS` — 재적용 안전. NOT NULL 컬럼은 DEFAULT 필수(기존 행 백필).
- `cd api && pytest -q` → 현재 **192 passed**. 6.3 후 그대로 통과 + 신규 테스트.

### 파일 구조 (신규/수정)

```
supabase/migrations/20260731000000_signals_schema_v2.sql   (신규 — published_at/popularity/source_authority/cluster_key + 인덱스 2)
api/pipeline/models.py            (수정 — RawArticle +3 필드, datetime import)
api/pipeline/normalizer.py        (수정 — 집계 헬퍼 + _SOURCE_AUTHORITY + upsert payload 4컬럼)
api/pipeline/clustering.py        (수정 — _relabel에 cluster_key 부여, hashlib import)
api/pipeline/collector/rss.py     (수정 — published_at from published_parsed)
api/pipeline/collector/hackernews.py (수정 — popularity/published_at from points/created_at)
api/pipeline/collector/github.py  (선택 — published_at, 저비용 시)
api/tests/test_pipeline_foundation.py (수정 — normalize v2 집계·None 안전 저하 테스트)
api/tests/test_clustering.py      (수정 — cluster_key 부여·메타 보존 테스트)
api/tests/test_collector_real.py  (수정/신규 — RSS/HN 메타데이터 파싱 테스트)
```

### 테스트 표준

- **프레임워크:** pytest 8.3.4, `pytest.ini`(`testpaths=tests`, `asyncio_mode=auto`), 파일명 `test_*.py`, `api/tests/`.
- **오프라인 원칙(절대):** 실 네트워크·실 OpenAI·실 DB 호출 금지. Supabase는 `MagicMock`(기존 `_make_mock_client` 패턴), httpx client는 mock(기존 6.1 수집기 테스트 패턴). 마이그레이션 SQL은 DB 필요라 pytest 미대상 — 파일·문법은 리뷰 또는 supabase MCP 적용으로 검증.
- **커버리지 대상:** (1) normalize 집계 정확성(published_at=max, popularity=sum, authority=max등급, cluster_key 저장), (2) None/0 안전 저하, (3) RawArticle 필드 확장 무회귀(positional), (4) 수집기 메타 파싱(published_parsed→UTC, points→popularity), (5) clustering cluster_key 부여·메타 보존, (6) 전체 회귀 192 passed.

### Project Structure Notes

- 백엔드는 `api/` 루트 실행(PYTHONPATH=`api`, import는 `pipeline.*`·`core.*`). 로컬 실행/DB 접속은 [[local-run-setup]] 참고.
- 6.2까지 DB 무변경 → **6.3에서 처음 마이그레이션 필요.** 적용 경로: Supabase MCP `apply_migration`(원격) 또는 로컬 `supabase db push`. [[seed-test-user-supabase]]의 MCP SQL 패턴 참고.
- 충돌/변이: 없음. 가산 컬럼 + 인덱스 2 + 코드 최소 수정. 기존 UNIQUE·소비자 무영향.
- 이 스토리는 [[epic-6-real-data-ingestion]]의 3번째 단계(6.1 수집·6.2 클러스터·**6.3 스키마/저장**·6.4 랭킹·6.5 측정).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.3 (L950-965), #Epic 6 스파이크 근거 (L891-902), #FR-8.1/8.2/8.4 (L53-56, L896-899)]
- [Source: _bmad-output/implementation-artifacts/6-2-의미-클러스터링-and-관련성-세이프티-필터.md#스코프 경계(L53-55)·D2 라벨 브리지(L129-133)·Deferred(L108 content 6.3 스코프)·File List(L239-243)]
- [Source: api/pipeline/normalizer.py (technology_name 그룹핑 + on_conflict upsert + signal_sources insert — v2 변경 대상)]
- [Source: api/pipeline/models.py L7-13 (RawArticle 5필드 — 뒤에 3필드 추가)]
- [Source: api/pipeline/clustering.py L177-187 (_relabel — cluster_key 부여 지점), L190-235 (cluster_and_filter url 정렬 결정론)]
- [Source: api/pipeline/collector/rss.py L56-84 (collect 엔트리 루프 — published_parsed 미사용), hackernews.py L59-79 (hit points/created_at 미사용)]
- [Source: supabase/migrations/20260723000000_initial_schema.sql L158-178 (signals/signal_sources DDL), 20260730000000_signals_unique_technology_date.sql (uq_signals_technology_date — 유지 대상, 주석 스타일 참고)]
- [Source: api/pipeline/signal_builder.py (SELECT * — 신규 컬럼 무시), recommender.py L136,300 (명시 컬럼 select — 6.4에서 확장), orchestrator.py L64-67 (normalize 호출 불변)]
- [Source: api/tests/test_pipeline_foundation.py L60-159 (_make_mock_client + normalize 테스트 — 확장/무회귀 기준)]
- [Source: architecture/.../ARCHITECTURE-SPINE.md#AD-16 (L308-311, 다출처 묶음=클러스터 스키마화), #AD-5(격리), #AD-12(관측), #AD-15(Batch First)]

### 🟡 오너 확인이 필요한 결정 (dev-story 착수 전 권장)

- **D1 (published_at·popularity 출처):** 이 스토리는 **A안 — 수집기(RSS/HN) + RawArticle 확장으로 실제 발행시각·HN points 확보**를 전제로 작성됨. **추천 이유:** Epic 6 핵심(FR-8.4)이 "최신성·인기로 랭킹"인데, 6.4가 쓸 값을 지금 스텁으로 채우면 6.4가 가짜 신호로 랭킹하게 됨. **사이드이펙트:** 수집기·RawArticle·테스트가 함께 바뀌어 스코프가 커짐(파일 3개 추가 수정). **대안 B(스코프 최소):** 수집기 무변경, normalize에서 `published_at=signal_date`, `popularity=소스 개수`로 저장 — 지금은 작지만 최신성이 하루로 뭉개지고 points를 못 씀. 오너가 B를 원하면 Task 2·3 축소 후 집계식만 교체(나머지 동일).

## Change Log

- 2026-07-29: Story 6.3 컨텍스트 생성(create-story) — 스키마 확장 + normalize v2 + 수집기 메타데이터 확보 설계. Status → ready-for-dev.
- 2026-07-29: dev-story 구현 완료(D1=A안, 마이그레이션 원격 적용 승인). 스키마 v2 마이그레이션 작성·MCP 적용, RawArticle +3필드, RSS/HN 수집기 메타데이터 확보, clustering cluster_key 부여, normalize v2 집계·저장, 테스트 10개 추가(202 passed). Status → review.
