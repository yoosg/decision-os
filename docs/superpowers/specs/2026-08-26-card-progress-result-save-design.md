# 입문자 카드 진도/결과 저장 (슬라이스 ⑦) — 설계

- 날짜: 2026-08-26
- 범위: 입문자 프로젝트 카드의 ④ 진도 · ⑥ 체크리스트 · ⑦ 결과를 서버에 저장/복원
- 선행: PR #3(카드 생성+웹 상세화면), PR #4(백엔드 정리), PR #5(체인 상세 카드 대응) 머지 완료
- 관련 메모리: `beginner-card-next-steps` (남은 작업 1번)

## 배경 / 문제

입문자 프로젝트 카드 상세화면의 세 상호작용이 현재 **로컬 상태 + UI 토스트만**이라 새로고침하면 사라진다:

- ④ 진도: 마일스톤 체크박스 (`MilestoneList`)
- ⑥ 성공 체크리스트: 체크박스 (`SuccessChecklist`)
- ⑦ 결과: 🎉 성공 / 😵 막힘 / 🏳️ 포기 버튼 — 현재 placeholder 토스트("결과 기록은 곧 지원돼요")만

이 세 상태를 유저 스코프로 영속화하고, 카드가 렌더되는 모든 화면에서 복원한다.

## 결정 요약

| 항목 | 결정 |
|------|------|
| 저장 대상 | ④ + ⑥ + ⑦ 전부 (④·⑥은 구조적 쌍둥이라 함께 처리) |
| 데이터 모델 | 새 테이블 `project_card_progress` (JSONB 컬럼/outcomes 재사용 아님) |
| 저장 UX | 자동 저장(낙관적 업데이트 + 디바운스), 저장 버튼 없음 |
| API 형태 | 전체상태 PUT upsert(멱등) + GET 복원 |
| 불러오기 범위 | 카드 컴포넌트 레벨에서 처리 → 카드 뜨는 모든 화면 자동 적용 |
| 미인증 | 저장 스킵, 로컬 전용 폴백 |

## 1. 데이터 모델 — 새 테이블 `project_card_progress`

카드 1장 + 유저 1명당 한 행. 마이그레이션 `supabase/migrations/20260826000000_project_card_progress.sql`.

```sql
CREATE TABLE public.project_card_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID NOT NULL REFERENCES public.reviews(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    milestones_checked INT[] NOT NULL DEFAULT '{}',   -- ④ 진도: 체크된 인덱스
    checklist_checked  INT[] NOT NULL DEFAULT '{}',   -- ⑥ 체크리스트: 체크된 인덱스
    result TEXT CHECK (result IN ('success','stuck','dropped')),  -- ⑦ 결과, NULL=미선택
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (review_id, user_id)   -- upsert 키
);
```

설계 근거:
- 체크 상태는 **체크된 인덱스 배열**로 저장(카드 payload의 `milestones`/`success_checklist` 순서 기준). 텍스트 라벨 매칭보다 단순·안정적(카드 재생성 전까지 순서 불변).
- 카드(시스템 생성 콘텐츠)와 진행상태(유저 데이터)는 생명주기가 달라 별도 테이블로 분리 — 기존 `outcomes`/`decisions`/`engagement_events` 관례와 일치.
- RLS: 유저는 자기 `user_id` 행만 select/insert/update. 백엔드 쓰기는 service_role 클라이언트(기존 관례).
- `updated_at`은 upsert 시 갱신(트리거 또는 백엔드에서 명시 set — 기존 테이블 관례 따름).

⑦ 결과 enum 매핑: `success` ↔ 🎉 성공, `stuck` ↔ 😵 막힘, `dropped` ↔ 🏳️ 포기.

## 2. 백엔드 API — 라우터 `api/routers/project_cards.py`

`api/main.py`에 `prefix="/api/v1"`로 등록. 소유권 검증은 기존 `outcomes.py` 사슬(review_id → project_id → user_id) 재사용.

### GET `/api/v1/project-cards/{review_id}/progress`
- 인증 필요(`Depends(get_current_user)`).
- 소유권 확인 후 저장 행 반환. 없으면 빈 상태:
  `{"milestones_checked": [], "checklist_checked": [], "result": null}`.
- 응답: `APIResponse{data, error}`.

### PUT `/api/v1/project-cards/{review_id}/progress`
- 인증 필요. 소유권 확인.
- Body: `{milestones_checked: int[], checklist_checked: int[], result: 'success'|'stuck'|'dropped'|null}`.
- 전체 상태 upsert(멱등) — `(review_id, user_id)` 유니크 키로 insert-or-update.
- 유효성:
  - 인덱스는 해당 카드 payload의 `milestones`/`success_checklist` 길이 범위 내 정수(범위 초과 → 422).
  - result는 enum 또는 null(그 외 → 422).
  - review_type이 `project_card`가 아니면 400/404(카드 아닌 리뷰엔 진행상태 없음).
- 응답: 갱신된 상태를 `APIResponse.data`로 반환.

에러 규약(기존 관례):
- 미인증 → 401
- 소유권 없음/미존재 review → 404
- 유효성 실패 → 422

## 3. 웹 연결 — 자동저장 훅 + 카드 컴포넌트 배선

카드 렌더 컴포넌트가 스스로 로드·저장 → 카드가 뜨는 모든 화면(홈 리뷰 상세 / 히스토리 체인 상세 / 큐 리뷰 / 스탠드얼론) 자동 적용.

### 새 훅 `useCardProgress(reviewId)`
파일: `web/src/components/home/review/use-card-progress.ts`

- 마운트 시 GET으로 저장 상태 로드 → 초기 체크 집합/결과 세팅.
- 상태: `milestonesChecked:Set<number>`, `checklistChecked:Set<number>`, `result:'success'|'stuck'|'dropped'|null`.
- 토글/결과 선택 시 **낙관적 업데이트**(UI 즉시) + **디바운스 600ms** 후 PUT(전체 상태).
- 토큰은 기존 패턴 `createClient().auth.getSession()`으로 획득. **토큰 없으면 저장 스킵**(로컬 전용 폴백, 네트워크 요청 안 함).
- 저장 실패 시 토스트("저장 실패, 재시도 중")만 표시. 다음 토글에서 재시도.
- base URL: `process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://localhost:8000"`.

### 컴포넌트 변경
- `project-card-blocks.tsx`: `MilestoneList`/`SuccessChecklist`의 로컬 `useCheckedSet` → `useCardProgress`가 관리하는 상태 사용. 진도 카운터(`checked.size/total`) 유지.
- `project-card-content.tsx`: ⑦ 결과 버튼의 placeholder 토스트 제거 → 실제 선택 반영. 선택된 결과에 시각적 활성 표시(기존 스타일 재사용).
- `review_id`는 상세 화면들이 이미 넘기는 review 데이터에서 컴포넌트로 전달.

## 4. ⑦ 결과 인터랙션 의미

- **단일 선택, 변경 가능**: 세 버튼 중 하나만 활성. 다른 버튼 누르면 전환.
- **같은 버튼 재탭 시 해제(null)** 허용 — 오선택 되돌리기 용이.
- 결과 선택은 **기록만** 함(YAGNI). "프로젝트 완료 처리"·화면 이동·리마인더 등 후속 액션은 범위 밖.

## 5. 테스트 / 검증

웹은 테스트 러너 없음(`web-test-runner-vitest` 메모리) → 백엔드 pytest + 웹 tsc/Playwright 수동.

### 백엔드 pytest (`api/tests/test_project_cards.py`)
- GET: 빈 상태 / 저장된 상태 반환.
- PUT: 신규 insert, 기존 update(멱등 — 같은 body 두 번 → 한 행 유지).
- 소유권 없는 review_id → 404.
- 잘못된 result enum / 범위 초과 인덱스 → 422.
- 미인증 → 401.
- review_type != project_card → 400/404.

### 웹
- `tsc --noEmit` 통과.
- Playwright 라이브 검증: 체크 후 새로고침 시 유지 / 결과 선택 유지 / 로그아웃 상태에서 에러 없이 로컬 동작.
- 시드 유저(`test-history@decisionos.dev` / `Test1234!`)로 카드 모드 켠 뒤 실제 카드에서 왕복 확인.

## 범위 밖 (다음 슬라이스)

- `example_prompt` 온보딩 도메인 개인화
- 상세화면 디테일 고도화 (3a 화면 폴리시 / 3b 생성내용 심화)
- "진행중 프로젝트 목록" 등 진행상태 기반 조회 화면
