# 입문자 카드 체인 상세 대응 (웹)

- 날짜: 2026-08-25
- 슬라이스: history chain 카드 대응 (beginner-card-next-steps ⑦결과 저장 슬라이스의 선행 조건)

## 문제

체인 상세(`/history/chain/[signalId]`)의 REVIEW 노드가 `review_type`을 읽지 않고 무조건
`ReviewSections`(13섹션)로 렌더한다. `project_card` 리뷰는 payload 구조가 달라서 체인 상세에서 깨진다.

관련 파일:

- `web/src/app/(app)/history/chain/[signalId]/page.tsx` — `result` 봉투에서 `payload`만 꺼내고 `review_type`은 무시.
- `web/src/components/history/chain-detail-content.tsx` — REVIEW 노드가 항상 `ReviewSections`에 직결.
- 정상 동작 참고: `web/src/components/home/review/review-page-content.tsx` — `reviewType === "project_card"`면 `ProjectCardContent`, 아니면 `ResearchReviewContent`로 분기.

`review_type` 값: `"project_card"`(입문자 7블록 카드) vs 그 외(`"research"`/undefined → 13섹션 표준 리뷰).

## 설계 결정

### 결정 1 — 체인 REVIEW 칸의 카드 렌더 범위: 메타 배지 포함

체인의 카드 본문은 **메타 배지(🏷️난이도·⏱예상시간 / 🎓스킬) + 7블록**으로 렌더한다.
배지를 포함해야 일반 카드 화면과 시각적으로 일관되고 카드 정체성이 유지된다.

`ProjectCardContent`는 화면 전체 껍데기(뒤로가기 "홈으로", 제목 h1, 7블록, "⑦ 결과 남기기" UI, 토스트)라
그대로 넣으면 체인의 뒤로가기·SIGNAL 제목·OUTCOME 칸과 **이중 중첩**된다.
따라서 체인에는 순수 본문(배지 + 블록)만 넣는다. "결과 남기기" UI는 넣지 않는다(체인 OUTCOME 칸이 담당).

### 결정 2 — 재사용 방식: 공용 본문 컴포넌트 신설(ProjectCardMeta)

배지 렌더를 `ProjectCardMeta` 컴포넌트로 추출해 `ProjectCardContent`와 체인 양쪽이 공유한다.
research가 체인에서 `<ReviewSections/>` 한 줄로 붙는 것과 대칭이며, 배지 스타일이 한 곳에만 있어 DRY.
(대안 B 인라인 복제 → 스타일 불일치 위험, 대안 C variant prop → 한 컴포넌트가 두 맥락을 떠안고
`screen-container`/padding 이중 중첩 위험. 둘 다 기각.)

## 구현 범위

### 1. 데이터 흐름 (`page.tsx`)

- `reviewRow.result` 타입에 `review_type?: string | null` 추가.
- `ChainDetailData.review`를 `{ reviewType: string | null; payload: ReviewPayload | ProjectCardPayload } | null`로 확장.
- 조립부: `review: payload ? { reviewType, payload } : null` (payload는 기존처럼 `result.payload`, reviewType은 `result.review_type ?? null`).

### 2. 컴포넌트 추출 (`ProjectCardMeta`)

- 위치: `web/src/components/home/review/project-card-blocks.tsx`에 `ProjectCardMeta`를 함께 export
  (`CARD_DIFFICULTY_LABEL`이 이미 거기 정의돼 있어 import가 깔끔).
- 내용: `ProjectCardContent`의 배지 두 줄(difficulty/estimated_minutes 배지 + skill_label 줄)만.
  **제목 h1은 추출 대상 아님** — 체인에선 SIGNAL 칸이 제목을 담당.
- `ProjectCardContent`는 title 아래에서 `<ProjectCardMeta payload={payload} />`를 호출하도록 교체.
  기존 화면은 **픽셀 동일**해야 한다(회귀 기준).

### 3. 분기 렌더링 (`chain-detail-content.tsx`)

REVIEW 노드에서 `reviewType`으로 분기:

```tsx
{review.reviewType === "project_card" ? (
  <>
    <ProjectCardMeta payload={review.payload as ProjectCardPayload} />
    <ProjectCardBlocks payload={review.payload as ProjectCardPayload} />
  </>
) : (
  <ReviewSections payload={review.payload as ReviewPayload} />
)}
```

- 뒤로가기·제목·"결과 남기기"는 넣지 않는다(체인이 이미 가짐).

## 테스트 / 검증

- 현재 브랜치(main)엔 실행 러너가 없음(비실행 `*.test.tsx`만). 작업 브랜치에서 러너 유무를 먼저 확인.
  - 러너 있으면 TDD로 chain-detail 분기(카드/리서치 두 케이스) 및 `ProjectCardMeta` 렌더 테스트 추가.
  - 없으면 `tsc` 타입체크 + Playwright로 체인 상세 두 케이스 수동 검증.
- 회귀 포인트: 기존 카드 화면(`ProjectCardContent`)이 리팩터 후에도 동일하게 보이는지.
- 검증 시나리오:
  1. `project_card` 리뷰 → 체인 REVIEW 칸에 배지 + 7블록, "결과 남기기" 없음, OUTCOME 칸 정상.
  2. `research`/undefined 리뷰 → 기존 13섹션 그대로.
