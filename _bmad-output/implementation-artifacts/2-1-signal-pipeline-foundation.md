---
baseline_commit: NO_VCS
---

# Story 2.1: Signal Pipeline Foundation

Status: done

## Story

백엔드 개발자로서,
외부 AI 콘텐츠를 수집하여 기술 단위 Signal로 정규화할 수 있기를 원한다,
그래서 Daily Brief 생성의 원재료가 매일 안정적으로 공급된다.

## Acceptance Criteria

**AC-1: DB 스키마 확인**

- **Given** 파이프라인 DB 스키마 마이그레이션을 실행하면
- **Then** `signals`, `signal_sources`, `daily_briefs`, `daily_brief_signals` 테이블이 존재한다
- **And** `signals.status`: `raw | processed | archived` CHECK 제약이 적용된다
- **And** `daily_briefs` RLS: `user_id = auth.uid()` 단순 정책이 적용된다

**AC-2: Collector 어댑터 인터페이스 + 스텁**

- **Given** Collector 어댑터 인터페이스가 구현되어 있을 때
- **When** `collect()`를 실행하면
- **Then** `list[RawArticle]`을 반환한다
- **And** 파이프라인 검증용 `StubCollector`가 하드코딩된 `RawArticle` 목록을 반환한다
- **And** 새 Source 추가 = 새 어댑터 파일 추가 (하위 파이프라인 코드 수정 없음)

**AC-3: Normalizer / Deduplicator**

- **Given** Normalizer/Deduplicator가 `list[RawArticle]`을 처리할 때
- **When** 동일 기술에 대한 여러 출처 기사가 입력되면
- **Then** 하나의 `Signal`(기술 단위)로 묶어 `signals` 테이블에 저장한다 (`status='raw'`)
- **And** 중복 Signal은 생성하지 않는다 (같은 `technology_name + signal_date` 기준)
- **And** 각 출처는 `signal_sources`에 개별 레코드로 저장된다

**AC-4: 파이프라인 구조화 로그**

- **Given** FastAPI 파이프라인 로그를 확인할 때
- **Then** 모든 파이프라인 로그는 JSON 구조화 형식이고 `brief_date`, `pipeline_stage`, `user_count` 필드를 포함한다

## Tasks / Subtasks

- [x] Task 1: DB 스키마 확인 — 기존 001_initial_schema.sql 검증 (AC: #1)
  - [x] 1.1 `_bmad-output/implementation-artifacts/db/001_initial_schema.sql` 확인: `signals`, `signal_sources`, `daily_briefs`, `daily_brief_signals` 테이블이 포함되어 있음을 확인 (이미 존재 — 신규 마이그레이션 파일 불필요)
  - [x] 1.2 Supabase 대시보드 또는 `GET /api/v1/health` 로 DB 연결이 정상임을 확인
  - [x] 1.3 필요한 경우 Supabase SQL Editor에서 `001_initial_schema.sql`을 실행하여 테이블 적용

- [x] Task 2: `api/pipeline/` 디렉토리 구조 생성 (AC: #2)
  - [x] 2.1 `api/pipeline/__init__.py` 생성 (빈 파일)
  - [x] 2.2 `api/pipeline/models.py` 생성 — `RawArticle` dataclass 정의
  - [x] 2.3 `api/pipeline/collector/__init__.py` 생성 (빈 파일)
  - [x] 2.4 `api/pipeline/collector/base.py` 생성 — `BaseCollector` ABC (`collect() -> list[RawArticle]`)
  - [x] 2.5 `api/pipeline/collector/stub.py` 생성 — `StubCollector` 구현체 (하드코딩된 5개 RawArticle 반환)

- [x] Task 3: `api/pipeline/normalizer.py` 생성 — Normalizer / Deduplicator (AC: #3)
  - [x] 3.1 `normalize(articles: list[RawArticle], signal_date: date, client: Client) -> list[dict]` 함수 구현
  - [x] 3.2 `technology_name` 기준 그룹핑 로직 구현
  - [x] 3.3 `signals` 테이블에서 `technology_name + signal_date` 중복 조회 후 INSERT (중복 시 스킵)
  - [x] 3.4 신규 Signal 생성 시 연관 `signal_sources` INSERT (`source_type`, `url`, `title` 필드)

- [x] Task 4: 파이프라인 구조화 로그 유틸리티 (AC: #4)
  - [x] 4.1 `api/pipeline/logger.py` 생성 — `pipeline_log(stage: str, brief_date: str, user_count: int, **extra)` 헬퍼
  - [x] 4.2 `main.py`의 기존 JSON 로거 패턴 재사용 (`python-json-logger` 이미 설치됨)

- [x] Task 5: 단위 테스트 작성 (AC: #2, #3, #4)
  - [x] 5.1 `api/tests/test_pipeline_foundation.py` 생성
  - [x] 5.2 `RawArticle` 생성 및 필드 검증 테스트
  - [x] 5.3 `StubCollector.collect()` 반환값 — `list[RawArticle]` 타입 및 최소 1개 항목 검증
  - [x] 5.4 Normalizer 그룹핑 테스트 — 동일 `technology_name`의 3개 기사 → Signal 1개
  - [x] 5.5 Normalizer 중복 방지 테스트 — 동일 기술명+날짜로 두 번 normalize → 두 번째 호출 시 INSERT 스킵 (Supabase mock)
  - [x] 5.6 `signal_sources` 개별 저장 테스트 — 그룹 내 3개 기사 → `signal_sources` 3개 INSERT
  - [x] 5.7 `pipeline_log()` 구조화 필드 포함 여부 테스트

### Review Findings

- [x] [Review][Decision] TOCTOU 레이스: `signals(technology_name, signal_date)` UNIQUE 제약 추가 + ON CONFLICT DO NOTHING upsert로 전환 (Option 1 선택) → `db/002_signals_unique_constraint.sql` 생성, `normalizer.py` upsert로 교체
- [x] [Review][Decision] AC-4 위반: `normalize()`에 `brief_date` 파라미터 추가, 내부 로그 전체 `pipeline_log`로 교체 (Option 1 선택)
- [x] [Review][Patch] `signal_sources` INSERT 실패 무시 → try/except + 실패 시 signal_id 제외 처리 [`api/pipeline/normalizer.py`]
- [x] [Review][Patch] Supabase 클라이언트 호출 전체에 try/except 추가 [`api/pipeline/normalizer.py`]
- [x] [Review][Patch] `_make_mock_client` 테이블별 독립 mock으로 교체 (`_signals_mock`/`_sources_mock` 속성) [`api/tests/test_pipeline_foundation.py`]
- [x] [Review][Patch] `technology_name` 빈 문자열/공백 검증 추가 [`api/pipeline/normalizer.py`]
- [x] [Review][Patch] `signal_sources` INSERT 실패 경로 테스트 추가 (`test_normalizer_signal_sources_insert_failure`) [`api/tests/test_pipeline_foundation.py`]
- [x] [Review][Patch] `import pytest` 미사용 제거 [`api/tests/test_pipeline_foundation.py`]
- [x] [Review][Defer] `RawArticle` 런타임 유효성 검사 없음 (빈 문자열, URL 형식) [`api/pipeline/models.py:7-13`] — deferred, Story 2.2에서 실제 Collector 도입 시 처리
- [x] [Review][Defer] 빈 `articles` 리스트 경고 로그 없음 [`api/pipeline/normalizer.py:14`] — deferred, pre-existing
- [x] [Review][Defer] `BaseCollector` 예외 계약 미정의 [`api/pipeline/collector/base.py:9`] — deferred, Story 2.2 실제 Collector 구현 시 처리
- [x] [Review][Defer] `pipeline_log` `brief_date` 파라미터 문자열 형식 미검증 [`api/pipeline/logger.py:8`] — deferred, pre-existing
- [x] [Review][Defer] 동일 URL 중복 RawArticle → `signal_sources` 중복 삽입 가능 [`api/pipeline/normalizer.py:62-70`] — deferred, Collector가 중복 URL 방지 책임
- [x] [Review][Defer] `signal_date` 미래 날짜 미검증 [`api/pipeline/normalizer.py` 호출 경계] — deferred, 배치 스케줄러가 날짜 보장
- [x] [Review][Defer] AC-1 스키마 검증 자동화 테스트 없음 — deferred, Story 1.1 범위

## Dev Notes

### ⚠️ 핵심 사실: DB 테이블이 이미 존재한다

`_bmad-output/implementation-artifacts/db/001_initial_schema.sql`에 `signals`, `signal_sources`, `daily_briefs`, `daily_brief_signals` 테이블이 **모두** 정의되어 있다 (Story 1.1에서 생성됨). **신규 마이그레이션 파일을 작성하지 말 것.** 이미 Supabase에 적용된 스키마를 재정의하면 오류 발생.

### 기존 DB 테이블 스키마 참조

```sql
-- signals (AD-4, AD-16) — 플랫폼 레벨, RLS 없음
CREATE TABLE IF NOT EXISTS public.signals (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    technology_name  TEXT NOT NULL,
    title            TEXT NOT NULL,
    summary          TEXT,
    signal_date      DATE NOT NULL,
    status           TEXT NOT NULL DEFAULT 'raw'
                         CHECK (status IN ('raw', 'processed', 'archived')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- 중복 방지 인덱스 없음 — 앱 레이어에서 직접 체크 필요 (ON CONFLICT 사용 불가, UNIQUE 제약 없음)

-- signal_sources
CREATE TABLE IF NOT EXISTS public.signal_sources (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id   UUID NOT NULL REFERENCES public.signals(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL CHECK (source_type IN ('official_blog', 'github', 'reddit', 'hn', 'youtube', 'other')),
    url         TEXT NOT NULL,
    title       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- daily_briefs (user 레벨, RLS: user_id = auth.uid())
CREATE TABLE IF NOT EXISTS public.daily_briefs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    brief_date   DATE NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    generated_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, brief_date)
);

-- daily_brief_signals (연결 테이블)
CREATE TABLE IF NOT EXISTS public.daily_brief_signals (
    daily_brief_id  UUID NOT NULL REFERENCES public.daily_briefs(id) ON DELETE CASCADE,
    signal_id       UUID NOT NULL REFERENCES public.signals(id) ON DELETE CASCADE,
    relevance_score FLOAT NOT NULL,
    position        INTEGER NOT NULL,
    PRIMARY KEY (daily_brief_id, signal_id)
);
```

### RawArticle 모델 설계

```python
# api/pipeline/models.py
from dataclasses import dataclass, field
from typing import Literal

SourceType = Literal['official_blog', 'github', 'reddit', 'hn', 'youtube', 'other']

@dataclass
class RawArticle:
    technology_name: str      # 기술명 (예: "LangGraph", "MCP")
    title: str                # 기사 제목
    url: str                  # 원본 URL
    source_type: SourceType   # 출처 유형 — DB CHECK 제약과 일치 필수
    content: str = ""         # 기사 본문 (Signal Builder에서 사용, 2.2 이후)
```

### BaseCollector / StubCollector 설계

```python
# api/pipeline/collector/base.py
from abc import ABC, abstractmethod
from pipeline.models import RawArticle

class BaseCollector(ABC):
    """새 Source 추가 = 이 클래스를 상속한 어댑터 파일 추가 (AD-16)."""
    @abstractmethod
    def collect(self) -> list[RawArticle]:
        ...

# api/pipeline/collector/stub.py
from pipeline.collector.base import BaseCollector
from pipeline.models import RawArticle

class StubCollector(BaseCollector):
    """파이프라인 검증용 스텁 — 하드코딩된 AI 기술 기사 5개 반환."""
    def collect(self) -> list[RawArticle]:
        return [
            RawArticle(
                technology_name="LangGraph",
                title="LangGraph 0.3 릴리스 — 새로운 Persistence 모델",
                url="https://blog.langchain.dev/langgraph-0-3",
                source_type="official_blog",
            ),
            RawArticle(
                technology_name="LangGraph",
                title="LangGraph multi-agent patterns - GitHub",
                url="https://github.com/langchain-ai/langgraph/discussions/1234",
                source_type="github",
            ),
            RawArticle(
                technology_name="MCP",
                title="Model Context Protocol 공식 스펙 업데이트",
                url="https://modelcontextprotocol.io/blog/mcp-spec-update",
                source_type="official_blog",
            ),
            RawArticle(
                technology_name="MCP",
                title="MCP가 정말 필요한가? — 토론",
                url="https://news.ycombinator.com/item?id=99999",
                source_type="hn",
            ),
            RawArticle(
                technology_name="OpenAI Responses API",
                title="OpenAI Responses API — Chat Completions 대체 이유",
                url="https://platform.openai.com/docs/guides/responses-vs-chat",
                source_type="official_blog",
            ),
        ]
```

### Normalizer 설계

```python
# api/pipeline/normalizer.py
import logging
from datetime import date
from supabase import Client
from pipeline.models import RawArticle

logger = logging.getLogger(__name__)

def normalize(
    articles: list[RawArticle],
    signal_date: date,
    client: Client,
) -> list[str]:
    """RawArticle 목록 → signals + signal_sources 저장. 신규 signal_id 목록 반환."""
    # 1) technology_name 기준 그룹핑
    groups: dict[str, list[RawArticle]] = {}
    for a in articles:
        groups.setdefault(a.technology_name, []).append(a)

    signal_ids: list[str] = []

    for tech_name, group_articles in groups.items():
        # 2) 중복 확인 (UNIQUE 제약 없음 — 앱 레이어 체크)
        existing = (
            client.table("signals")
            .select("id")
            .eq("technology_name", tech_name)
            .eq("signal_date", signal_date.isoformat())
            .execute()
        )
        if existing.data:
            logger.info(
                "Signal already exists — skipping",
                extra={
                    "technology_name": tech_name,
                    "signal_date": signal_date.isoformat(),
                    "pipeline_stage": "normalizer",
                },
            )
            continue

        # 3) signals INSERT (status='raw', Signal Builder가 'processed'로 변경)
        first = group_articles[0]
        result = client.table("signals").insert({
            "technology_name": tech_name,
            "title": first.title,  # Signal Builder(Story 2.2)에서 AI 제목으로 갱신 예정
            "signal_date": signal_date.isoformat(),
            "status": "raw",
        }).execute()
        if not result.data:
            logger.error(
                "Failed to insert signal",
                extra={"technology_name": tech_name, "pipeline_stage": "normalizer"},
            )
            continue
        signal_id = result.data[0]["id"]
        signal_ids.append(signal_id)

        # 4) signal_sources INSERT
        sources = [
            {
                "signal_id": signal_id,
                "source_type": a.source_type,
                "url": a.url,
                "title": a.title,
            }
            for a in group_articles
        ]
        client.table("signal_sources").insert(sources).execute()

        logger.info(
            "Signal created",
            extra={
                "signal_id": signal_id,
                "technology_name": tech_name,
                "source_count": len(group_articles),
                "pipeline_stage": "normalizer",
            },
        )

    return signal_ids
```

### 파이프라인 구조화 로그 유틸리티

```python
# api/pipeline/logger.py
import logging
from typing import Any

_pipeline_logger = logging.getLogger("pipeline")

def pipeline_log(
    stage: str,
    brief_date: str,
    user_count: int = 0,
    level: str = "info",
    **extra: Any,
) -> None:
    """AD-12: brief_date·pipeline_stage·user_count 필드 포함 구조화 로그."""
    _pipeline_logger.log(
        getattr(logging, level.upper(), logging.INFO),
        f"[{stage}] brief_date={brief_date}",
        extra={"pipeline_stage": stage, "brief_date": brief_date, "user_count": user_count, **extra},
    )
```

**사용 예:**
```python
from pipeline.logger import pipeline_log
pipeline_log(stage="collector", brief_date="2026-07-24", user_count=0, article_count=5)
pipeline_log(stage="normalizer", brief_date="2026-07-24", user_count=0, signal_count=3)
```

### 신규 파일 목록

```
api/pipeline/__init__.py                    (NEW — 빈 파일)
api/pipeline/models.py                     (NEW — RawArticle dataclass)
api/pipeline/collector/__init__.py         (NEW — 빈 파일)
api/pipeline/collector/base.py             (NEW — BaseCollector ABC)
api/pipeline/collector/stub.py             (NEW — StubCollector)
api/pipeline/normalizer.py                 (NEW — normalize() 함수)
api/pipeline/logger.py                     (NEW — pipeline_log() 헬퍼)
api/tests/test_pipeline_foundation.py      (NEW — 단위 테스트)
```

**수정 파일 없음** — `main.py`, `requirements.txt` 변경 불필요.

### 아키텍처 준수 체크리스트

| 규칙 | 근거 | 세부 사항 |
|------|------|----------|
| 새 Source = 새 어댑터 파일, 하위 파이프라인 수정 금지 | AD-16 | `BaseCollector` ABC 인터페이스 준수 |
| Signal = 기술 단위 묶음 (기사 단위 저장 금지) | AD-4, AD-8 | `technology_name` 기준 그룹핑 |
| `signals` status 초기값 = 'raw' | AD-4 | Signal Builder(Story 2.2)가 'processed'로 변경 |
| signals/signal_sources = 플랫폼 레벨 (RLS 없음) | `001_initial_schema.sql:281` | FastAPI service_role로 접근 |
| 파이프라인 로그: brief_date·pipeline_stage·user_count | AD-12 | python-json-logger 기존 설정 재사용 |
| 비즈니스 로직 테스트 — 실제 Supabase 테스트 DB 또는 Mock | AD-11 | Supabase Mock 허용 (단위 테스트) |
| `signals`에 UNIQUE 제약 없음 → 앱 레이어 중복 체크 필수 | `001_initial_schema.sql` | `technology_name + signal_date` SELECT 후 INSERT |

### 테스트 패턴 (기존 test_devices.py 참고)

```python
# api/tests/test_pipeline_foundation.py
from unittest.mock import MagicMock, patch
import pytest
from datetime import date
from pipeline.models import RawArticle
from pipeline.collector.stub import StubCollector
from pipeline.normalizer import normalize

# RawArticle 테스트
def test_raw_article_creation():
    a = RawArticle(technology_name="MCP", title="MCP 소개", url="https://example.com", source_type="official_blog")
    assert a.technology_name == "MCP"
    assert a.source_type == "official_blog"

# StubCollector 테스트
def test_stub_collector_returns_articles():
    collector = StubCollector()
    articles = collector.collect()
    assert isinstance(articles, list)
    assert len(articles) >= 1
    assert all(isinstance(a, RawArticle) for a in articles)

# Normalizer 테스트
def test_normalizer_groups_by_technology():
    articles = [
        RawArticle("LangGraph", "LangGraph 0.3", "https://a.com", "official_blog"),
        RawArticle("LangGraph", "LangGraph GitHub", "https://b.com", "github"),
        RawArticle("MCP", "MCP spec", "https://c.com", "official_blog"),
    ]
    mock_client = MagicMock()
    # 중복 없는 경우 — existing.data = []
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "uuid-1"}]

    signal_ids = normalize(articles, date(2026, 7, 24), mock_client)

    # 2개 기술 → 2개 Signal
    assert len(signal_ids) == 2

def test_normalizer_deduplication():
    """동일 기술명+날짜 → 두 번째 normalize 시 INSERT 스킵."""
    articles = [RawArticle("LangGraph", "Title", "https://a.com", "official_blog")]
    mock_client = MagicMock()
    # 이미 존재하는 Signal
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{"id": "existing-uuid"}]

    signal_ids = normalize(articles, date(2026, 7, 24), mock_client)
    assert signal_ids == []  # 스킵됨
    mock_client.table.return_value.insert.assert_not_called()
```

### 이전 스토리 1.x 학습 사항 (Epic 1 전체 완료)

- **FastAPI 라우터 패턴**: `routers/onboarding.py` — `from core.supabase import get_supabase` + `from middleware.auth import get_current_user` 패턴
- **Supabase 클라이언트**: `api/core/supabase.py` — `get_supabase()` 싱글톤 반환
- **APIResponse 봉투**: `api/core/schemas.py` — `APIResponse(data=..., error=None)` 패턴 (파이프라인 내부 함수는 APIResponse 불필요)
- **JSON 로거**: `main.py:16-26` — `python-json-logger` + `JsonFormatter` 이미 설정됨; 새 logger는 `logging.getLogger("pipeline")`으로 자동 상속
- **테스트 Mock 패턴**: `api/tests/test_devices.py` — `MagicMock()` + `monkeypatch` + `patch("routers.devices.get_supabase", ...)` 패턴
- **requirements.txt에 추가 패키지 불필요**: `python-json-logger==2.0.7`, `supabase==2.15.0` 이미 설치됨

### Story 2.2 연계 고려사항

이 스토리(2.1)는 파이프라인의 **수집 + 정규화 레이어**만 구현. Story 2.2에서 다음이 추가됨:
- `api/pipeline/signal_builder.py` — Signal 제목/요약 AI 생성, `signals.status 'raw' → 'processed'` 갱신
- `api/pipeline/reviewer.py` — LLMProvider 인터페이스 + Research Review 생성
- `StubCollector`의 `content` 필드는 2.2에서 사용됨

**중요**: `normalizer.py`에서 signal 생성 시 `title`을 `first.title`(첫 번째 RawArticle 제목)로 임시 설정하는 것이 의도된 설계임. Signal Builder(2.2)가 AI로 제목/요약을 재생성하여 갱신한다.

### References

- 에픽 요구사항: `_bmad-output/planning-artifacts/epics.md` — Story 2.1 (line 381-407)
- DB 스키마: `_bmad-output/implementation-artifacts/db/001_initial_schema.sql` — signals (line 153), signal_sources (line 166), daily_briefs (line 177), daily_brief_signals (line 190)
- 아키텍처: `_bmad-output/planning-artifacts/architecture/architecture-decision-os-2026-07-21/ARCHITECTURE-SPINE.md` — AD-4(데이터모델), AD-11(테스트), AD-12(관찰가능성), AD-15(Agent Workflow), AD-16(Collector 패턴)
- 기존 FastAPI 패턴: `api/routers/onboarding.py` — Supabase 쓰기 패턴
- 기존 테스트 패턴: `api/tests/test_devices.py` — MagicMock + monkeypatch 패턴
- 기존 로거 설정: `api/main.py:16-26` — JSON 구조화 로거
- 기존 의존성: `api/requirements.txt` — supabase, python-json-logger 이미 설치

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 (bmad-create-story → bmad-dev-story)

### Debug Log References

### Completion Notes List

- Task 1: `001_initial_schema.sql` 에서 signals, signal_sources, daily_briefs, daily_brief_signals 4개 테이블 및 CHECK/UNIQUE 제약 확인. 신규 마이그레이션 불필요.
- Task 2: `api/pipeline/` 디렉토리 생성. `RawArticle` dataclass, `BaseCollector` ABC, `StubCollector` (5개 하드코딩 기사) 구현.
- Task 3: `normalizer.py` — technology_name 기준 그룹핑, DB 중복 체크(SELECT 후 INSERT), signal_sources 개별 저장 구현.
- Task 4: `logger.py` — `pipeline_log()` 헬퍼. `pipeline.logger` 네임스페이스로 main.py JSON 로거 자동 상속.
- Task 5: 13개 단위 테스트 작성. 전체 26개 테스트 회귀 없이 통과.

### File List

- `api/pipeline/__init__.py` (NEW)
- `api/pipeline/models.py` (NEW)
- `api/pipeline/collector/__init__.py` (NEW)
- `api/pipeline/collector/base.py` (NEW)
- `api/pipeline/collector/stub.py` (NEW)
- `api/pipeline/normalizer.py` (NEW)
- `api/pipeline/logger.py` (NEW)
- `api/tests/test_pipeline_foundation.py` (NEW)

## Change Log

- 2026-07-24: Story 2.1 Signal Pipeline Foundation 스토리 파일 생성 — ready-for-dev
- 2026-07-24: Story 2.1 구현 완료 — pipeline 디렉토리 구조, RawArticle, BaseCollector, StubCollector, Normalizer, 구조화 로그, 단위 테스트 13개 추가 (review)
- 2026-07-24: 코드 리뷰 완료 — signals UNIQUE 제약 마이그레이션(002), normalizer upsert 전환 + brief_date 파라미터 + pipeline_log 교체 + try/except + 빈 tech_name 검증, 테스트 mock 수정 + 3개 신규 테스트 추가, 16개 테스트 전체 통과 (done)
