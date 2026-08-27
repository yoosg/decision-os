# 입문자 카드 진도/결과 저장 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 입문자 프로젝트 카드의 ④ 진도·⑥ 체크리스트·⑦ 결과를 유저 스코프로 서버에 저장/복원한다.

**Architecture:** 새 테이블 `project_card_progress`(카드 1장 × 유저 1명 = 1행)에 체크된 인덱스 배열과 결과 enum을 저장한다. FastAPI가 `GET/PUT /api/v1/project-cards/{review_id}/progress`로 전체상태 upsert(멱등)를 제공하고, 웹은 `useCardProgress` 훅으로 낙관적 업데이트 + 디바운스 자동저장한다. 인터랙티브 카드 화면(`ProjectCardContent`)에만 배선하고, 읽기전용 화면(체인 상세)은 `progress` prop 부재 시 기존 로컬 동작으로 폴백한다.

**Tech Stack:** Supabase(Postgres) 마이그레이션, FastAPI + supabase-py(service_role), Next.js(비표준 — 아래 제약 참고) + React 클라이언트 컴포넌트, pytest.

## Global Constraints

- **결과 enum은 `success` | `stuck` | `dropped`** (DB CHECK · API Literal · 웹 키 전부 동일). 기존 웹의 `give_up` 키는 `dropped`로 교체한다.
- **웹 저장 쓰기는 전부 FastAPI 경유**(service_role). 웹은 Supabase에 직접 쓰지 않는다. RLS는 SELECT(own row)만 부여, INSERT/UPDATE/DELETE 정책 부재 → service_role만 쓰기(기존 `engagement_events` AD-3 패턴).
- **미인증(토큰 없음) 또는 `reviewId` 부재 시 저장 스킵**하고 로컬 전용으로 폴백한다. 네트워크 요청을 보내지 않으며 에러도 아니다.
- **웹 저장 요청은 디바운스 600ms**로 묶고 낙관적 업데이트(UI 먼저)한다. base URL: `process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://localhost:8000"`. 인증 헤더: `Authorization: Bearer <supabase access_token>`.
- **웹 코드 작성 전 `web/AGENTS.md` 준수**: 이 Next.js는 비표준이므로 새 API/규칙 사용 시 `node_modules/next/dist/docs/`의 관련 가이드를 먼저 확인한다. (이 슬라이스는 클라이언트 컴포넌트 + fetch만 사용하므로 서버/라우팅 API 변경 없음.)
- **웹 테스트 러너 없음**(`web-test-runner-vitest` 메모리): `*.test.tsx`는 실행 안 됨. 웹 검증 = `tsc --noEmit` + Playwright 수동. 단, 기존 `*.test.tsx`가 컴파일 대상이면 시그니처 변경 시 함께 고쳐 tsc를 통과시킨다.
- **응답 포맷**: 백엔드는 `core.schemas.APIResponse{data, error}`. 에러 규약: 미인증 401 / 소유권 없음·미존재 404 / 유효성 실패 422 / 카드 아님(review_type != project_card) 404.

---

## File Structure

- Create: `supabase/migrations/20260826000000_project_card_progress.sql` — 새 테이블·인덱스·RLS·updated_at 트리거.
- Create: `api/routers/project_cards.py` — GET/PUT 진행상태 라우터.
- Modify: `api/main.py` — 라우터 등록.
- Create: `api/tests/test_project_cards.py` — 라우터 단위 테스트.
- Create: `web/src/components/home/review/use-card-progress.ts` — 로드/자동저장 훅.
- Modify: `web/src/components/home/review/project-card-blocks.tsx` — 옵셔널 `progress` 컨트롤드 배선.
- Modify: `web/src/components/home/review/project-card-content.tsx` — `reviewId` prop·⑦ 결과 실제 반영·훅 사용.
- Modify: `web/src/components/home/review/review-page-content.tsx` — `reviewId={uiState.reviewId}` 전달.
- Modify(테스트 tsc 유지): `web/src/components/home/review/__tests__/project-card-content.test.tsx`, `.../project-card-blocks.test.tsx` — 필요 시 prop 시그니처 정합.

---

### Task 1: DB 마이그레이션 — `project_card_progress`

**Files:**
- Create: `supabase/migrations/20260826000000_project_card_progress.sql`

**Interfaces:**
- Produces: 테이블 `public.project_card_progress(id, review_id, user_id, milestones_checked int[], checklist_checked int[], result text, created_at, updated_at)`, UNIQUE `(review_id, user_id)`. 백엔드(Task 2)가 이 컬럼명으로 읽고 쓴다.

- [ ] **Step 1: 마이그레이션 파일 작성**

`supabase/migrations/20260826000000_project_card_progress.sql`:

```sql
-- 입문자 카드 진도/결과 저장 — project_card_progress
--
-- 왜/무엇을:
--   입문자 프로젝트 카드 상세화면의 ④ 진도(마일스톤 체크)·⑥ 성공 체크리스트·⑦ 결과가
--   지금은 로컬 상태라 새로고침 시 유실된다. 이 테이블은 "카드 1장 × 유저 1명 = 1행"의
--   개인 진행상태를 영속화한다. 체크 상태는 카드 payload(milestones/success_checklist)의
--   인덱스 배열로 저장한다(카드 재생성 전까지 순서 안정).
--
--   쓰기 소유권(AD-3): 쓰기는 FastAPI service_role만. RLS는 SELECT만 user_id=auth.uid()
--   허용(engagement_events·memories와 동형). INSERT/UPDATE/DELETE 정책 부재 → service_role만.
--   가산적(additive): 신규 테이블 1개만 추가, 기존 테이블·행·정책 무변경(무회귀).
--   모든 DDL은 IF NOT EXISTS(멱등).

CREATE TABLE IF NOT EXISTS public.project_card_progress (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id          UUID NOT NULL REFERENCES public.reviews(id) ON DELETE CASCADE,
    user_id            UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    milestones_checked INTEGER[] NOT NULL DEFAULT '{}',
    checklist_checked  INTEGER[] NOT NULL DEFAULT '{}',
    result             TEXT CHECK (result IN ('success', 'stuck', 'dropped')),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (review_id, user_id)
);

-- 유저별 진행상태 조회
CREATE INDEX IF NOT EXISTS idx_card_progress_user
    ON public.project_card_progress (user_id);

-- RLS — SELECT only (user_id 직접 컬럼, engagement_events와 동형). 쓰기는 service_role만(AD-3).
ALTER TABLE public.project_card_progress ENABLE ROW LEVEL SECURITY;

CREATE POLICY "project_card_progress_select" ON public.project_card_progress FOR SELECT
    USING (user_id = auth.uid());

-- updated_at 자동 갱신 (기존 public.set_updated_at() 재사용)
CREATE TRIGGER trg_project_card_progress_updated_at
    BEFORE UPDATE ON public.project_card_progress
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

- [ ] **Step 2: 로컬/원격에 적용**

Supabase MCP `apply_migration`(name: `project_card_progress`, 위 SQL) 또는 로컬 `supabase db push`로 적용.

- [ ] **Step 3: 적용 검증**

`mcp__supabase__execute_sql`로 실행:
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'project_card_progress'
ORDER BY ordinal_position;
```
Expected: `milestones_checked`/`checklist_checked` = `ARRAY`, `result` = `text`, `review_id`/`user_id` = `uuid` 포함.

RLS 확인:
```sql
SELECT policyname, cmd FROM pg_policies
WHERE tablename = 'project_card_progress';
```
Expected: `project_card_progress_select` / `SELECT` 한 행.

- [ ] **Step 4: 커밋**

```bash
git add supabase/migrations/20260826000000_project_card_progress.sql
git commit -m "feat(cards): project_card_progress 테이블 — 진도/결과 저장 스키마"
```

---

### Task 2: 백엔드 라우터 — GET/PUT progress

**Files:**
- Create: `api/routers/project_cards.py`
- Modify: `api/main.py` (라우터 import + include)
- Test: `api/tests/test_project_cards.py`

**Interfaces:**
- Consumes: `core.schemas.APIResponse`, `core.supabase.get_supabase`, `middleware.auth.get_current_user`. 테이블 컬럼(Task 1).
- Produces: 라우터 `router`(prefix `/project-cards`). 엔드포인트:
  - `GET /project-cards/{review_id}/progress` → `APIResponse(data={"milestones_checked": int[], "checklist_checked": int[], "result": str|None})`
  - `PUT /project-cards/{review_id}/progress` (body `ProgressRequest`) → 동일 형태 `data` 반환.
- `ProgressRequest`: `milestones_checked: list[int]`, `checklist_checked: list[int]`, `result: Literal["success","stuck","dropped"] | None = None`.

- [ ] **Step 1: 실패하는 테스트 작성**

`api/tests/test_project_cards.py`:

```python
"""project_card_progress 엔드포인트 단위 테스트."""
import time
from unittest.mock import MagicMock, patch

import jwt as pyjwt
from fastapi.testclient import TestClient

TEST_SECRET = "test-super-secret-key-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_REVIEW_ID = "rev-abc-111"
TEST_PROJECT_ID = "proj-xyz-222"
TEST_PROGRESS_ID = "prog-def-555"


def _make_token(user_id: str = TEST_USER_ID) -> str:
    payload = {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")


def _chain() -> MagicMock:
    c = MagicMock()
    for attr in ("select", "insert", "update", "eq", "in_", "limit", "order"):
        getattr(c, attr).return_value = c
    return c


def _base_mock(
    *,
    review_row: dict | None,
    progress_first: list,
    progress_write: list | None = None,
) -> MagicMock:
    """메서드 기반 mock — reviews 소유권 조회 + project_card_progress select/write."""
    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        c = MagicMock()
        if table_name == "reviews":
            ch = _chain()
            ch.execute.return_value.data = [review_row] if review_row else []
            c.select.return_value = ch
        elif table_name == "projects":
            ch = _chain()
            ch.execute.return_value.data = [{"id": TEST_PROJECT_ID}]
            c.select.return_value = ch
        elif table_name == "project_card_progress":
            select_ch = _chain()
            select_ch.execute.return_value.data = progress_first
            write_ch = _chain()
            write_ch.execute.return_value.data = progress_write or [{"id": TEST_PROGRESS_ID}]
            c.select.return_value = select_ch
            c.insert.return_value = write_ch
            c.update.return_value = write_ch
        return c

    mock_client.table.side_effect = table_side_effect
    return mock_client


_CARD_REVIEW = {
    "id": TEST_REVIEW_ID,
    "project_id": TEST_PROJECT_ID,
    "review_type": "project_card",
    "result": {"payload": {"milestones": [{}, {}, {}], "success_checklist": ["a", "b"]}},
}


def _client(mock_client):
    with patch("routers.project_cards.get_supabase", return_value=mock_client):
        from main import app
        return TestClient(app)


def test_get_empty_progress_returns_defaults(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)
    mock_client = _base_mock(review_row=_CARD_REVIEW, progress_first=[])
    with patch("routers.project_cards.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            res = client.get(
                f"/api/v1/project-cards/{TEST_REVIEW_ID}/progress",
                headers={"Authorization": f"Bearer {_make_token()}"},
            )
    assert res.status_code == 200
    assert res.json()["data"] == {"milestones_checked": [], "checklist_checked": [], "result": None}


def test_put_inserts_new_progress(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)
    written = [{"id": TEST_PROGRESS_ID, "milestones_checked": [0, 2],
               "checklist_checked": [1], "result": "success"}]
    mock_client = _base_mock(review_row=_CARD_REVIEW, progress_first=[], progress_write=written)
    with patch("routers.project_cards.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            res = client.put(
                f"/api/v1/project-cards/{TEST_REVIEW_ID}/progress",
                headers={"Authorization": f"Bearer {_make_token()}"},
                json={"milestones_checked": [0, 2], "checklist_checked": [1], "result": "success"},
            )
    assert res.status_code == 200
    assert res.json()["data"]["result"] == "success"
    assert res.json()["data"]["milestones_checked"] == [0, 2]


def test_put_out_of_range_index_returns_422(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)
    mock_client = _base_mock(review_row=_CARD_REVIEW, progress_first=[])
    with patch("routers.project_cards.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            res = client.put(
                f"/api/v1/project-cards/{TEST_REVIEW_ID}/progress",
                headers={"Authorization": f"Bearer {_make_token()}"},
                json={"milestones_checked": [3], "checklist_checked": [], "result": None},
            )
    assert res.status_code == 422


def test_put_bad_result_enum_returns_422(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)
    mock_client = _base_mock(review_row=_CARD_REVIEW, progress_first=[])
    with patch("routers.project_cards.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            res = client.put(
                f"/api/v1/project-cards/{TEST_REVIEW_ID}/progress",
                headers={"Authorization": f"Bearer {_make_token()}"},
                json={"milestones_checked": [], "checklist_checked": [], "result": "give_up"},
            )
    assert res.status_code == 422


def test_unowned_review_returns_404(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)
    # projects 소유권 조회가 빈 결과 → 404
    mock_client = _base_mock(review_row=_CARD_REVIEW, progress_first=[])

    def table_side_effect(table_name: str) -> MagicMock:
        c = MagicMock()
        if table_name == "reviews":
            ch = _chain(); ch.execute.return_value.data = [_CARD_REVIEW]; c.select.return_value = ch
        elif table_name == "projects":
            ch = _chain(); ch.execute.return_value.data = []; c.select.return_value = ch  # 소유권 없음
        return c
    mock_client.table.side_effect = table_side_effect

    with patch("routers.project_cards.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            res = client.get(
                f"/api/v1/project-cards/{TEST_REVIEW_ID}/progress",
                headers={"Authorization": f"Bearer {_make_token()}"},
            )
    assert res.status_code == 404


def test_non_card_review_returns_404(monkeypatch):
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)
    research_review = {**_CARD_REVIEW, "review_type": "research"}
    mock_client = _base_mock(review_row=research_review, progress_first=[])
    with patch("routers.project_cards.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            res = client.get(
                f"/api/v1/project-cards/{TEST_REVIEW_ID}/progress",
                headers={"Authorization": f"Bearer {_make_token()}"},
            )
    assert res.status_code == 404


def test_missing_auth_returns_401():
    mock_client = _base_mock(review_row=_CARD_REVIEW, progress_first=[])
    with patch("routers.project_cards.get_supabase", return_value=mock_client):
        from main import app
        with TestClient(app) as client:
            res = client.get(f"/api/v1/project-cards/{TEST_REVIEW_ID}/progress")
    assert res.status_code == 401
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd api && python -m pytest tests/test_project_cards.py -v`
Expected: FAIL / ERROR — `routers.project_cards` 모듈 없음(import 실패).

- [ ] **Step 3: 라우터 구현**

`api/routers/project_cards.py`:

```python
"""project_card_progress 엔드포인트 — 입문자 카드 진도/결과 저장."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from core.schemas import APIResponse
from core.supabase import get_supabase
from middleware.auth import get_current_user

router = APIRouter(prefix="/project-cards", tags=["project-cards"])


class ProgressRequest(BaseModel):
    milestones_checked: list[int] = []
    checklist_checked: list[int] = []
    result: Literal["success", "stuck", "dropped"] | None = None


def _load_owned_card(client, review_id: str, user_id: str) -> dict:
    """review_id → 소유권·카드타입 검증 후 review row 반환. 실패 시 404."""
    review_rows = (
        client.table("reviews")
        .select("id, project_id, review_type, result")
        .eq("id", review_id)
        .execute()
        .data
    )
    if not review_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    review = review_rows[0]

    if review.get("review_type") != "project_card":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    project_rows = (
        client.table("projects")
        .select("id")
        .eq("id", review["project_id"])
        .eq("user_id", user_id)
        .execute()
        .data
    )
    if not project_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    return review


def _card_lengths(review: dict) -> tuple[int, int]:
    """카드 payload의 milestones·success_checklist 길이."""
    payload = ((review.get("result") or {}).get("payload")) or {}
    milestones = payload.get("milestones") or []
    checklist = payload.get("success_checklist") or []
    return len(milestones), len(checklist)


def _row_to_data(row: dict | None) -> dict:
    if not row:
        return {"milestones_checked": [], "checklist_checked": [], "result": None}
    return {
        "milestones_checked": row.get("milestones_checked") or [],
        "checklist_checked": row.get("checklist_checked") or [],
        "result": row.get("result"),
    }


@router.get("/{review_id}/progress", response_model=APIResponse)
def get_progress(
    review_id: str,
    user_id: Annotated[str, Depends(get_current_user)],
) -> APIResponse:
    client = get_supabase()
    _load_owned_card(client, review_id, user_id)

    rows = (
        client.table("project_card_progress")
        .select("milestones_checked, checklist_checked, result")
        .eq("review_id", review_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )
    return APIResponse(data=_row_to_data(rows[0] if rows else None))


@router.put("/{review_id}/progress", response_model=APIResponse)
def put_progress(
    review_id: str,
    body: ProgressRequest,
    user_id: Annotated[str, Depends(get_current_user)],
) -> APIResponse:
    client = get_supabase()
    review = _load_owned_card(client, review_id, user_id)

    n_milestones, n_checklist = _card_lengths(review)

    def _validate(indices: list[int], length: int, field: str) -> None:
        for i in indices:
            if i < 0 or i >= length:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{field} index {i} out of range (0..{length - 1})",
                )

    _validate(body.milestones_checked, n_milestones, "milestones_checked")
    _validate(body.checklist_checked, n_checklist, "checklist_checked")

    # dedup + 정렬(안정적 저장)
    milestones = sorted(set(body.milestones_checked))
    checklist = sorted(set(body.checklist_checked))

    values = {
        "milestones_checked": milestones,
        "checklist_checked": checklist,
        "result": body.result,
    }

    existing = (
        client.table("project_card_progress")
        .select("id")
        .eq("review_id", review_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )

    if existing:
        written = (
            client.table("project_card_progress")
            .update(values)
            .eq("id", existing[0]["id"])
            .execute()
            .data
        )
    else:
        written = (
            client.table("project_card_progress")
            .insert({**values, "review_id": review_id, "user_id": user_id})
            .execute()
            .data
        )

    row = written[0] if written else {**values}
    return APIResponse(data=_row_to_data(row))
```

- [ ] **Step 4: 라우터 등록**

`api/main.py`에서 다른 라우터 import 근처에 추가하고 include:
```python
from routers.project_cards import router as project_cards_router
```
```python
app.include_router(project_cards_router, prefix="/api/v1")
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd api && python -m pytest tests/test_project_cards.py -v`
Expected: PASS (7 passed).

- [ ] **Step 6: 전체 스위트 회귀 확인**

Run: `cd api && python -m pytest -q`
Expected: 신규 7 포함 통과. (사전 존재하는 `test_reviews_trigger.py`의 2건 실패는 이 슬라이스와 무관한 기존 기술부채 — 신규 실패만 없으면 OK.)

- [ ] **Step 7: 커밋**

```bash
git add api/routers/project_cards.py api/main.py api/tests/test_project_cards.py
git commit -m "feat(cards): 진도/결과 저장 API — GET/PUT project-cards progress"
```

---

### Task 3: 웹 자동저장 훅 `useCardProgress`

**Files:**
- Create: `web/src/components/home/review/use-card-progress.ts`

**Interfaces:**
- Produces: `useCardProgress(reviewId: string | null): CardProgress`
  ```ts
  export type CardResult = "success" | "stuck" | "dropped";
  export interface CardProgress {
    milestonesChecked: Set<number>;
    checklistChecked: Set<number>;
    result: CardResult | null;
    toggleMilestone: (i: number) => void;
    toggleChecklist: (i: number) => void;
    setResult: (r: CardResult | null) => void;
    saveError: boolean;
  }
  ```
  Task 4(blocks)·Task 5(content)가 이 shape를 소비한다.

- [ ] **Step 1: 훅 구현**

`web/src/components/home/review/use-card-progress.ts`:

```ts
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createClient } from "@/lib/supabase";

export type CardResult = "success" | "stuck" | "dropped";

export interface CardProgress {
  milestonesChecked: Set<number>;
  checklistChecked: Set<number>;
  result: CardResult | null;
  toggleMilestone: (i: number) => void;
  toggleChecklist: (i: number) => void;
  setResult: (r: CardResult | null) => void;
  saveError: boolean;
}

const FASTAPI_URL = process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://localhost:8000";
const DEBOUNCE_MS = 600;

async function getToken(): Promise<string | null> {
  const { data: { session } } = await createClient().auth.getSession();
  return session?.access_token ?? null;
}

export function useCardProgress(reviewId: string | null): CardProgress {
  const [milestonesChecked, setMilestones] = useState<Set<number>>(new Set());
  const [checklistChecked, setChecklist] = useState<Set<number>>(new Set());
  const [result, setResultState] = useState<CardResult | null>(null);
  const [saveError, setSaveError] = useState(false);

  // 최신 상태를 debounced save가 읽도록 ref로 유지
  const latest = useRef({ milestonesChecked, checklistChecked, result });
  latest.current = { milestonesChecked, checklistChecked, result };
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const hydratedRef = useRef(false);

  // 마운트 시 저장상태 로드(있으면). 토큰/ reviewId 없으면 로컬 전용.
  useEffect(() => {
    if (!reviewId) return;
    let cancelled = false;
    (async () => {
      const token = await getToken();
      if (!token || cancelled) return;
      try {
        const res = await fetch(`${FASTAPI_URL}/api/v1/project-cards/${reviewId}/progress`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok || cancelled) return;
        const json = await res.json();
        const d = json?.data;
        if (!d || cancelled) return;
        setMilestones(new Set<number>(d.milestones_checked ?? []));
        setChecklist(new Set<number>(d.checklist_checked ?? []));
        setResultState((d.result as CardResult | null) ?? null);
      } catch {
        // 로드 실패 — 로컬 전용으로 진행
      } finally {
        hydratedRef.current = true;
      }
    })();
    return () => { cancelled = true; };
  }, [reviewId]);

  const scheduleSave = useCallback(() => {
    if (!reviewId) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      const token = await getToken();
      if (!token) return; // 미인증 → 로컬 전용
      try {
        const res = await fetch(`${FASTAPI_URL}/api/v1/project-cards/${reviewId}/progress`, {
          method: "PUT",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            milestones_checked: [...latest.current.milestonesChecked],
            checklist_checked: [...latest.current.checklistChecked],
            result: latest.current.result,
          }),
        });
        setSaveError(!res.ok);
      } catch {
        setSaveError(true);
      }
    }, DEBOUNCE_MS);
  }, [reviewId]);

  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);

  const toggleMilestone = useCallback((i: number) => {
    setMilestones((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
    scheduleSave();
  }, [scheduleSave]);

  const toggleChecklist = useCallback((i: number) => {
    setChecklist((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
    scheduleSave();
  }, [scheduleSave]);

  const setResult = useCallback((r: CardResult | null) => {
    setResultState(r);
    scheduleSave();
  }, [scheduleSave]);

  return {
    milestonesChecked, checklistChecked, result,
    toggleMilestone, toggleChecklist, setResult, saveError,
  };
}
```

> 주의: `scheduleSave`는 상태 setter 직후 호출되며 최신 값은 `latest.current`(렌더마다 갱신)에서 읽는다. setter의 함수형 업데이트 결과가 다음 렌더에 `latest.current`로 반영된 뒤 600ms 타이머가 발화하므로 최신 상태가 전송된다.

- [ ] **Step 2: 타입 체크**

Run: `cd web && npx tsc --noEmit`
Expected: 신규 파일로 인한 에러 없음(기존 에러가 있다면 이 파일과 무관).

- [ ] **Step 3: 커밋**

```bash
git add web/src/components/home/review/use-card-progress.ts
git commit -m "feat(web/cards): useCardProgress — 로드+디바운스 자동저장 훅"
```

---

### Task 4: `ProjectCardBlocks` 컨트롤드 배선(옵셔널 progress)

**Files:**
- Modify: `web/src/components/home/review/project-card-blocks.tsx`

**Interfaces:**
- Consumes: `CardProgress`(Task 3).
- Produces: `ProjectCardBlocks`가 옵셔널 `progress?: CardProgress`를 받는다. 없으면 기존 로컬 `useCheckedSet` 동작(무회귀 — 체인 상세 등 읽기전용 화면).

- [ ] **Step 1: import 추가**

`project-card-blocks.tsx` 상단(파일 최상단 import 블록):
```ts
import type { CardProgress } from "./use-card-progress";
```

- [ ] **Step 2: `MilestoneList`/`SuccessChecklist`를 컨트롤드로 변경**

두 컴포넌트가 `checked`/`onToggle`을 props로 받도록 교체:
```tsx
function MilestoneList({
  milestones,
  checked,
  onToggle,
}: {
  milestones: ProjectCardPayload["milestones"];
  checked: Set<number>;
  onToggle: (i: number) => void;
}) {
  return (
    <div>
      <p className="text-label" style={{ color: "var(--text-secondary)", marginBottom: "8px" }}>
        {checked.size}/{milestones.length}
      </p>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {milestones.map((m, i) => (
          <li key={i} style={{ marginBottom: "12px" }}>
            <label style={{ display: "flex", gap: "8px", alignItems: "flex-start", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={checked.has(i)}
                onChange={() => onToggle(i)}
                style={{ marginTop: "3px" }}
              />
              <span>
                <span className="text-body" style={{ display: "block" }}>{m.action}</span>
                <span className="text-body" style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
                  끝나면: {m.done_signal}
                </span>
              </span>
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SuccessChecklist({
  items,
  checked,
  onToggle,
}: {
  items: string[];
  checked: Set<number>;
  onToggle: (i: number) => void;
}) {
  return (
    <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
      {items.map((it, i) => (
        <li key={i} style={{ marginBottom: "8px" }}>
          <label style={{ display: "flex", gap: "8px", alignItems: "flex-start", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={checked.has(i)}
              onChange={() => onToggle(i)}
              style={{ marginTop: "3px" }}
            />
            <span className="text-body">{it}</span>
          </label>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 3: `ProjectCardBlocks`가 progress 소스를 결정**

기존 `useCheckedSet`는 로컬 폴백용으로 유지하고, `ProjectCardBlocks`에서 두 소스를 결합:
```tsx
export function ProjectCardBlocks({
  payload,
  progress,
}: {
  payload: ProjectCardPayload;
  progress?: CardProgress;
}) {
  // 로컬 폴백(progress 미제공 시). 훅은 항상 무조건 호출.
  const localMilestones = useCheckedSet();
  const localChecklist = useCheckedSet();

  const milestoneChecked = progress ? progress.milestonesChecked : localMilestones.checked;
  const milestoneToggle = progress ? progress.toggleMilestone : localMilestones.toggle;
  const checklistChecked = progress ? progress.checklistChecked : localChecklist.checked;
  const checklistToggle = progress ? progress.toggleChecklist : localChecklist.toggle;

  return (
    <>
      {/* ①~③ 기존 그대로 (deliverable / prerequisites / how_to_start) */}
      {/* ... 변경 없음 ... */}

      {/* ④ 진행 과정 */}
      <section style={{ marginBottom: "24px" }}>
        <h2 className="text-section-title" style={{ marginBottom: "8px" }}>🗺️ 진행 과정</h2>
        <MilestoneList
          milestones={payload.milestones ?? []}
          checked={milestoneChecked}
          onToggle={milestoneToggle}
        />
      </section>

      {/* ⑤ 막히면 이렇게 — 변경 없음 */}

      {/* ⑥ 다 됐는지 확인 */}
      <section style={{ marginBottom: "24px" }}>
        <h2 className="text-section-title" style={{ marginBottom: "8px" }}>✅ 다 됐는지 확인</h2>
        <SuccessChecklist
          items={payload.success_checklist ?? []}
          checked={checklistChecked}
          onToggle={checklistToggle}
        />
      </section>
    </>
  );
}
```
> ①②③⑤ 섹션 및 `CopyPromptButton`는 기존 코드 그대로 둔다. 위에서 바뀐 부분은 함수 시그니처, ④·⑥의 자식 props, 그리고 상단 소스 결정 로직뿐이다.

- [ ] **Step 4: 타입 체크**

Run: `cd web && npx tsc --noEmit`
Expected: `project-card-blocks.tsx` 관련 에러 없음. (체인 상세는 `progress` 없이 호출 → 옵셔널이라 통과.)

- [ ] **Step 5: 커밋**

```bash
git add web/src/components/home/review/project-card-blocks.tsx
git commit -m "refactor(web/cards): ProjectCardBlocks 컨트롤드 progress(옵셔널) 배선"
```

---

### Task 5: `ProjectCardContent` ⑦ 결과 + reviewId 배선 & 라이브 검증

**Files:**
- Modify: `web/src/components/home/review/project-card-content.tsx`
- Modify: `web/src/components/home/review/review-page-content.tsx`
- Modify(필요 시): `web/src/components/home/review/__tests__/project-card-content.test.tsx`

**Interfaces:**
- Consumes: `useCardProgress`(Task 3), `ProjectCardBlocks progress` prop(Task 4).
- `ProjectCardContent` props에 `reviewId?: string` 추가(옵셔널 — 없으면 로컬 전용).

- [ ] **Step 1: `ProjectCardContent` 수정**

`project-card-content.tsx`:
```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ProjectCardBlocks, ProjectCardMeta, type ProjectCardPayload } from "./project-card-blocks";
import { useCardProgress, type CardResult } from "./use-card-progress";

interface Props {
  signalId: string;
  signalTitle: string;
  payload: ProjectCardPayload;
  reviewId?: string;
}

const OUTCOMES: { key: CardResult; label: string }[] = [
  { key: "success", label: "🎉 성공" },
  { key: "stuck", label: "😵 막힘" },
  { key: "dropped", label: "🏳️ 포기" },
];

export function ProjectCardContent({ signalTitle, payload, reviewId }: Props) {
  const progress = useCardProgress(reviewId ?? null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  // 저장 실패 시 토스트
  useEffect(() => {
    if (progress.saveError) setToast("저장 실패, 재시도 중");
  }, [progress.saveError]);

  return (
    <div className="screen-container" style={{ paddingTop: "24px", paddingBottom: "96px" }}>
      {/* 홈으로 백링크 — 기존 그대로 */}
      <Link
        href="/home"
        className="text-label"
        style={{ display: "inline-flex", alignItems: "center", gap: "4px", color: "var(--text-secondary)", marginBottom: "20px" }}
      >
        <svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M10 4L6 8l4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        홈으로
      </Link>

      <h1 className="text-screen-title" style={{ marginBottom: "12px" }}>{signalTitle}</h1>
      <ProjectCardMeta payload={payload} />

      <ProjectCardBlocks payload={payload} progress={progress} />

      {/* ⑦ 결과 남기기 — 단일선택, 재탭 시 해제 */}
      <section style={{ marginTop: "8px" }}>
        <h2 className="text-section-title" style={{ marginBottom: "8px" }}>결과 남기기</h2>
        <div style={{ display: "flex", gap: "8px" }}>
          {OUTCOMES.map((o) => {
            const active = progress.result === o.key;
            return (
              <button
                key={o.key}
                type="button"
                aria-pressed={active}
                onClick={() => progress.setResult(active ? null : o.key)}
                style={{
                  flex: 1,
                  minHeight: "44px",
                  borderRadius: "9999px",
                  border: active ? "1px solid var(--text-primary, #111)" : "1px solid var(--border-subtle, #E5E5E5)",
                  background: active ? "var(--surface-card, #F2F2F2)" : "transparent",
                  cursor: "pointer",
                  fontSize: "14px",
                  fontWeight: active ? 700 : 500,
                }}
              >
                {o.label}
              </button>
            );
          })}
        </div>
      </section>

      {toast && (
        <div
          role="status"
          aria-live="polite"
          style={{
            position: "fixed",
            bottom: "calc(80px + env(safe-area-inset-bottom))",
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            zIndex: 60,
            pointerEvents: "none",
          }}
        >
          <div style={{ background: "rgba(0,0,0,0.75)", color: "#fff", padding: "10px 20px", borderRadius: "9999px", fontSize: "14px" }}>
            {toast}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 호출부에서 `reviewId` 전달**

`review-page-content.tsx` line ~188 `ProjectCardContent` 렌더에 prop 추가:
```tsx
<ProjectCardContent
  signalId={signalId}
  signalTitle={uiState.signalTitle}
  payload={uiState.payload as ProjectCardPayload}
  reviewId={uiState.reviewId}
/>
```
(`uiState.reviewId`는 `completed` 상태에 이미 존재 — line 14/38/92.)

- [ ] **Step 3: 테스트 파일 tsc 정합 확인**

Run: `cd web && npx tsc --noEmit`
Expected: 에러 없음. 만약 `__tests__/project-card-content.test.tsx`가 컴파일 대상이라 새 시그니처로 에러가 나면, 해당 `render(<ProjectCardContent ... />)` 호출을 그대로 두되(모든 새 prop이 옵셔널이라 통과해야 함) 에러 메시지를 근거로만 수정한다. `give_up` 문자열을 단언하는 테스트가 있으면 `dropped`로 갱신한다.

- [ ] **Step 4: 라이브 검증(Playwright)**

사전: 백엔드(:8000)+웹(:3000) 로컬 실행, `beginner_card_mode_enabled` ON, 시드 유저 `test-history@decisionos.dev` / `Test1234!` 로그인.
검증 절차(Playwright MCP):
1. 카드 상세 진입 → ④ 마일스톤 2개 체크, ⑥ 체크리스트 1개 체크, ⑦ "🎉 성공" 탭.
2. 페이지 새로고침 → 체크 2개/1개, ⑦ 성공 활성 상태가 **복원**되는지 확인.
3. ⑦ "🎉 성공" 재탭 → 해제(비활성) 확인, 새로고침 후 결과 null 유지.
4. 로그아웃(또는 시크릿) 상태에서 같은 화면 진입 → 체크는 로컬로 동작하고 콘솔 에러/저장요청 없음(로컬 폴백).

Expected: 1~4 모두 관찰대로 동작. 스크린샷으로 전후 캡처.

- [ ] **Step 5: DB 왕복 확인**

`mcp__supabase__execute_sql`:
```sql
SELECT milestones_checked, checklist_checked, result
FROM public.project_card_progress
WHERE review_id = '<검증에 쓴 review_id>';
```
Expected: 화면에서 체크한 인덱스/결과와 일치하는 한 행.

- [ ] **Step 6: 커밋**

```bash
git add web/src/components/home/review/project-card-content.tsx \
        web/src/components/home/review/review-page-content.tsx \
        web/src/components/home/review/__tests__/project-card-content.test.tsx
git commit -m "feat(web/cards): ⑦ 결과 저장 + reviewId 배선 — 카드 진도/결과 영속화"
```

---

## Self-Review

**Spec coverage:**
- §1 데이터 모델 → Task 1 ✓ (테이블·인덱스 배열·result enum·UNIQUE·RLS·트리거)
- §2 API(GET/PUT·소유권·유효성·에러규약) → Task 2 ✓ (7 테스트가 200/422/404/401·멱등 커버)
- §3 웹 훅·낙관적·디바운스·토큰폴백·컴포넌트 배선 → Task 3(훅)·4(blocks)·5(content) ✓
- §4 ⑦ 단일선택·재탭 해제·기록만 → Task 5 Step 1 ✓
- §5 테스트/검증(백엔드 pytest·웹 tsc+Playwright·시드 왕복) → Task 2 Step 5-6, Task 5 Step 4-5 ✓
- 범위 밖(example_prompt·폴리시·조회화면) → 계획에 미포함 ✓

**Placeholder scan:** "①②③⑤ 기존 그대로"는 실제 변경 없는 섹션을 명시적으로 보존하라는 지시(플레이스홀더 아님) — 전체 파일이 Read된 상태이며 바뀌는 부분의 코드는 전량 기재됨. 기타 TBD/TODO 없음.

**Type consistency:** `CardProgress`/`CardResult` shape가 Task 3 정의 ↔ Task 4·5 소비에서 동일(`milestonesChecked`/`checklistChecked`/`result`/`toggleMilestone`/`toggleChecklist`/`setResult`/`saveError`). result enum `success|stuck|dropped`가 DB CHECK·API Literal·웹 OUTCOMES·PUT body에서 일치. GET/PUT 응답 키 `milestones_checked`/`checklist_checked`/`result`가 백엔드 `_row_to_data` ↔ 훅 로드 파싱에서 일치.

## 스코프 노트(설계 대비 정련)

- 스펙 §3/§4의 "모든 화면"은 **인터랙티브 카드 화면**(`ProjectCardContent` — 홈/큐/스탠드얼론 리뷰 상세, review_id 보유·유일 호출부)로 구체화한다. **체인 상세**는 서버 컴포넌트 읽기전용 아카이브이며 `review` 객체에 review_id가 없어, `ProjectCardBlocks`의 `progress` 미제공 → 기존 로컬 동작 유지(무회귀). 향후 체인에도 저장을 원하면 review_id 스레딩 + 클라이언트화가 별도 슬라이스로 필요.
