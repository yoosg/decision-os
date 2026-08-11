# 학습 경로 링크 검증 (작업 B — 1단계)

작성일: 2026-08-10
브랜치: `feat/learning-link-verification`

## 배경 / 문제

학습 화면(`web/.../home/review/[signalId]/learning-path`)은 LLM(`coach.py` + `LEARNING_PATH_SYSTEM_PROMPT`)이 생성한 리소스 카드 5장을 보여준다:
`official_docs / core_material / github / practice_example / applied_idea`.

각 카드는 `{type, title, url, descriptor}` 구조이며, URL을 누르면 새 탭으로 이동한다.
문제는 LLM이 만든 URL 중 일부가 **존재하지 않는 페이지(죽은 링크)** 라는 점이다. 현재는 URL이
비었거나 형식이 잘못된 경우 **비활성(클릭 불가) 카드**로 방치되고, 형식은 맞지만 404인 링크는
그대로 열려 사용자가 죽은 페이지를 만난다. → 학습 경로의 신뢰성이 떨어진다.

## 목표

생성 시점에 각 링크의 생존 여부를 확인하고, **확실히 죽은 링크만** 검색 링크로 교체한다.
카드 5장 수와 순서는 그대로 유지한다.

## 비목표 (이번 범위 밖)

- 경로 구조 안내(전체 목표 / 번호 순서 / '무엇을 배우나') — 작업 B의 다음 스텝.
- 생성 후 시간이 지나 썩는 링크 재검증 — 커버하지 않음(학습 경로는 생성 직후 조회되는 경우가
  대부분이라 생성 시점 검증으로 충분하다고 판단).
- `applied_idea` 카드 — 원래 URL이 없는(빈 문자열) 아이디어 카드이므로 검증 대상에서 제외.

## 설계

### 왜 백엔드(생성 시점)인가

브라우저에서 타 도메인 URL의 생존 여부를 직접 확인하는 것은 CORS 정책상 대부분 차단된다.
따라서 검증은 백엔드가 학습 경로를 생성하는 시점(`coach.py` 파이프라인)에서 서버-투-서버
HTTP 요청으로 수행한다.

### 1. 백엔드 — 링크 검증 모듈

**새 파일** `api/pipeline/link_verifier.py` — 단일 책임 유닛.

```
def verify_and_fix_links(
    resources: list[dict],
    technology_name: str,
    client: httpx.Client,
    timeout: float,
) -> list[dict]:
    """URL이 있는 리소스의 생존을 확인해 죽은 링크는 검색 링크로 교체한 새 리스트를 반환."""
```

- **검사 대상**: `url`이 비어있지 않은 리소스만. (`applied_idea`는 빈 url이므로 자동 제외)
- **요청 방식**:
  - `GET`, `follow_redirects=True`, 브라우저 유사 `User-Agent` 헤더, 타임아웃 `timeout`(기본 ~5s).
  - 4개 URL을 **동시(concurrent)** 처리 — `concurrent.futures.ThreadPoolExecutor`
    (coach 파이프라인은 BackgroundTask 안에서 동기 실행되므로 스레드풀로 병렬화).
- **"깨짐" 판정 (보수적)**:
  - 깨짐 = 연결/DNS 실패 · 타임아웃 · 최종 상태코드 **404 또는 410** (확실히 사라진 경우).
  - **애매하면 유지** = 403 · 401 · 429 · 5xx. 봇 차단/일시 장애일 때가 많아, 멀쩡한 링크를
    검색으로 날려버리는 오검출을 막기 위해 그대로 둔다.
- **교체 동작**: 깨진 리소스는 원본을 복제하되
  - `url` → 구글 검색 링크: `https://www.google.com/search?q=<urlencoded query>`
    - query = `f"{technology_name} {korean_label}"` (예: `"LangGraph 공식 문서"`).
      `github` 타입은 `f"{technology_name} github"`.
    - 라벨 매핑: official_docs=공식 문서 / core_material=핵심 자료 / github=github /
      practice_example=실습 예제.
  - `is_search_fallback: True` 플래그 추가.
- **불변식**: 반환 리스트는 입력과 **같은 길이·같은 순서·같은 type**. `title`/`descriptor`는 원본 유지.

### 2. 백엔드 — coach 파이프라인 통합

`coach.py::_execute_learning_path_pipeline`에서 resources를 파싱·검증한 직후(현재 라인 ~91),
`completed` 상태로 저장하기 직전에 검증 단계를 삽입한다.

- `settings.link_verification_enabled`(신규, 기본 `True`) 토글. `False`면 검증을 건너뛰고 원본 저장.
- `httpx.Client`를 생성해 `verify_and_fix_links`에 주입(테스트 용이성 — 컬렉터들의 주입 패턴과 동일).
- **안전 폴백**: 검증 로직에서 예외가 나면 로깅 후 **원본 resources로 진행**. 링크 확인 실패가
  학습 경로 생성 전체를 실패시키지 않도록 한다.
- 타임아웃 값: 기존 `settings.collector_timeout_seconds` 재사용 또는 신규
  `settings.link_verification_timeout_seconds`(기본 5.0). → 신규 설정으로 분리(수집기와 목적이 다름).

### 3. 설정 (`core/config.py`)

```
link_verification_enabled: bool = True
link_verification_timeout_seconds: float = 5.0
```

### 4. 프론트 — 검색 표시

- `web/.../learning-path/learning-path-card.tsx`
  - `LearningPathResource`에 `is_search_fallback?: boolean` 추가.
  - `is_search_fallback`가 `true`면 외부링크(↗) 아이콘 대신 **`🔍 검색으로 찾기`** 라벨을 표시.
  - 카드는 여전히 클릭 가능 → 검색 URL을 새 탭으로 연다(기존 `handleClick` 그대로).
- 스키마 검증(`_LEARNING_PATH_RESOURCE_KEYS`는 `issubset`이라 추가 키 허용)·`len==5`·type 순서
  검사는 그대로 통과하므로 파이프라인 변경 불필요.

## 데이터 흐름

```
LLM generate_learning_path
  → JSON parse + 검증(5개, type 순서)        [기존]
  → verify_and_fix_links(resources, tech, httpx.Client)   [신규]
       · GET 각 url (동시) → 404/410/네트워크실패면 search+flag 교체
  → learning_paths.resources = 검증된 resources, status=completed  [저장]
  → (프론트) 카드 렌더, is_search_fallback이면 '🔍 검색으로 찾기'
```

## 테스트 계획

**백엔드** (`api/tests/test_link_verifier.py`, 주입된 httpx.Client mock):
- 200 → 원본 유지, 플래그 없음.
- 404 → 검색 링크 + `is_search_fallback=True`, title/descriptor/type 유지.
- 410 → 교체.
- 타임아웃/연결오류 → 교체.
- 403 / 429 / 500 → **유지**(교체 안 함).
- `applied_idea`(빈 url) → 무변경, 검사 안 함.
- 반환 리스트 길이·순서·type 불변 확인.
- 검색 query에 technology_name + 라벨 포함, URL 인코딩 정상.

**백엔드 통합** (`test_learning_paths.py`):
- 토글 `False` → verify 호출 없이 원본 저장(pass-through).
- verify 예외 → 원본 resources로 completed 저장(안전 폴백).

**프론트** (`learning-path-card.vitest.tsx`):
- `is_search_fallback=true` → '🔍 검색으로 찾기' 라벨 렌더, 클릭 시 search url open.
- 플래그 없음 → 기존 외부링크 아이콘 렌더.

## 파일 변경 요약

- 신규 `api/pipeline/link_verifier.py`
- 수정 `api/pipeline/coach.py` (검증 단계 삽입)
- 수정 `api/core/config.py` (토글 2개)
- 수정 `web/src/components/home/learning-path/learning-path-card.tsx` (플래그 + 검색 라벨)
- 신규 `api/tests/test_link_verifier.py`
- 수정 `api/tests/test_learning_paths.py` (통합 케이스)
- 신규 `web/.../learning-path-card.vitest.tsx`
