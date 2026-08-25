# 입문자 프로젝트 카드 상세화면 (웹) — 설계

- 날짜: 2026-08-24
- 브랜치: feat/beginner-vibecoding-pivot
- 관련: [[2026-08-23-beginner-vibecoding-pivot-design]] (7블록 골격 원본), 백엔드 카드 생성 커밋 70a78a1~56602e6

## 배경

백엔드는 이미 입문자 프로젝트 카드를 생성·저장한다. `beginner_card_mode_enabled` 토글이 켜지면
파이프라인이 `review_type="project_card"`로 카드 payload(11키)를 만들어 `reviews.result`에 저장하고,
`reviews.review_type` 컬럼도 함께 맞춘다(커밋 56602e6). 꺼져 있으면 기존 `research`(13섹션)가 나온다.

웹 상세화면은 아직 `research` 13섹션만 그린다(`research-review-content` → `review-sections`).
이 작업은 **웹 상세화면이 `review_type`에 따라 카드 UI(7블록) 또는 기존 13섹션을 그리도록 분기**한다.

## 범위 (이번 슬라이스)

**"화면 먼저"** — 7블록을 전부 렌더한다. 다만:

- ④ 마일스톤 체크박스 / ⑥ 성공 체크리스트: **로컬 상태만**(새로고침 시 초기화). 진도 저장 API 없음.
- ⑦ 결과 남기기(성공/막힘/포기): **UI만**. 클릭 시 "곧 지원돼요" 토스트. 결과 기록 API 없음.
- 백엔드 진도·결과 저장 API, `example_prompt` 온보딩 도메인 개인화는 **다음 슬라이스**.

## 데이터

카드 payload = 백엔드 `REQUIRED_CARD_BLOCKS` 11키 (`api/pipeline/llm/prompts.py`):

```ts
interface ProjectCardPayload {
  skill_label: string;                     // 헤더: 이걸로 배우는 것
  difficulty: "first_step" | "basic" | "challenge";
  estimated_minutes: number;
  deliverable: string;                     // ①
  success_preview: string;                 // ①
  prerequisites: string;                   // ②
  how_to_start: string;                    // ③
  example_prompt: string;                  // ③ (현재 표준 예시, 개인화 미구현)
  milestones: { action: string; done_signal: string }[];   // ④
  troubleshooting: { symptom: string; fix: string }[];     // ⑤
  success_checklist: string[];             // ⑥
}
```

`review_type`은 `reviews.result.review_type`에 들어있다(초기 로드·실시간 재조회 양쪽에서 접근 가능).

## 아키텍처 — 분기 위치

**`ReviewPageContent`의 `completed` 상태에서만 분기한다.**

생성 파이프라인(트리거 → pending/processing → completed, 실시간 구독, 재시도)은 카드와 research가
동일하다. 다른 것은 완성된 payload를 어떻게 렌더하느냐뿐이다.

- `page.tsx`가 `reviewRow.result?.review_type`을 읽어 `initialReview`에 실어 보낸다.
- `ReviewPageContent`의 `completed` UI 상태에 `reviewType` 필드를 추가한다.
  - 초기: `initialReview.reviewType`
  - 실시간: 재조회 콜백이 이미 `result`를 select하므로 `data.result.review_type`에서 읽는다.
- `completed`일 때: `review_type === "project_card"` → `<ProjectCardContent>`, 그 외(기본) → `<ResearchReviewContent>`.
- `generating` / `failed` 상태 렌더는 **그대로 공유**.

**폴백**: `review_type`이 없는 과거 리뷰 행(`undefined`)은 `research`로 폴백한다(안전 기본값).

## 컴포넌트 구조

기존 `research-review-content` ↔ `review-sections` 2분할을 미러링한다.

- **`web/src/components/home/review/project-card-content.tsx`** (client)
  - 레이아웃 래퍼: 뒤로가기 링크, 헤더(제목 · 난이도 뱃지 · ⏱분 · 🎓skill_label), 블록 오케스트레이션,
    ⑦ 결과 바(인라인, 게이트 없음).
  - `research-review-content.tsx`의 카드 버전. props: `signalId, signalTitle, payload`.
- **`web/src/components/home/review/project-card-blocks.tsx`**
  - `ProjectCardPayload` 타입 + ①~⑥ 블록 렌더 + 작은 프레젠테이션 조각(난이도 뱃지, 마일스톤/체크리스트 아이템, 복사 버튼).
  - `review-sections.tsx`의 카드 버전.

## 블록 렌더 & 인터랙션

```
헤더   제목 · [🏷️난이도 뱃지] · ⏱N분 · 🎓skill_label
① 📦 완성하면 이게 나와   deliverable + 「이렇게 보이면 성공」 success_preview
② 🧰 시작 전 준비물       prerequisites
③ 🚀 이렇게 시작해        how_to_start + [예시 프롬프트 박스 + 📋복사]
④ 🗺️ 진행 과정           milestones[] 체크박스 · 「2/4」 진도 · 각 action + done_signal
⑤ 🆘 막히면 이렇게        troubleshooting[] (symptom → fix)
⑥ ✅ 다 됐는지 확인       success_checklist[] 체크박스
⑦ 결과 남기기 (인라인)    [🎉 성공] [😵 막힘] [🏳️ 포기]  ← UI만, 클릭 시 토스트
```

- **난이도 뱃지**: `first_step→첫걸음`, `basic→기본`, `challenge→도전`. research의 `DIFFICULTY_LABEL` 패턴을 카드용으로 별도 정의.
- **④ / ⑥ 체크박스**: 로컬 `useState`(체크된 인덱스 `Set`). 새로고침 시 초기화. ④는 진도 카운트("2/4") 표시.
- **③ 복사 버튼**: `navigator.clipboard.writeText(example_prompt)` → 짧은 토스트/체크 피드백. ③ 라벨은
  개인화 미구현이므로 "🎯 너를 위한 예시"가 아닌 중립적 "예시 프롬프트"로 둔다.
- **⑦ 버튼**: 렌더만. 클릭 시 "결과 기록은 곧 지원돼요" 토스트. 스텁 성격을 코드 주석으로 명시.

## 디자인 시스템 준수

- 인라인 스타일 + 유틸 클래스(`text-body`, `text-section-title`, `text-screen-title`, `text-label`)
- CSS 변수(`--text-secondary`, `--accent-primary`, `--border-subtle`, `--surface-base`)
- 하단 고정 요소는 이 화면엔 없음(⑦ 인라인). `screen-container` + 하단 패딩 컨벤션 따름.

## 에러 처리

백엔드가 completed 전 11키 + `difficulty` 허용값을 검증하므로 payload는 신뢰한다.
다만 배열 필드(`milestones`, `troubleshooting`, `success_checklist`)는 방어적으로 `?? []` 폴백만 얇게 둔다.

## 검증 방식

**이 브랜치에는 실행 가능한 테스트 러너가 없다**(package.json에 `test` 스크립트/vitest 없음).
기존 `*.test.tsx`는 상단에 "Jest/Vitest 미설정 — 스펙 문서 역할"이라 명시된 **미실행 스펙 문서**다.
따라서 기존 컨벤션을 따른다:

1. **스펙 문서** (`*.test.tsx`, 미실행): 기존 파일들과 동일한 헤더 주석 + `@ts-nocheck` + jest-style API로
   의도한 동작을 문서화한다.
   - `project-card-content.test.tsx`: 7블록 전부 렌더 / 난이도 뱃지 매핑(first_step→첫걸음) /
     ④ 체크박스 토글 → 진도 카운트 / ③ 복사 버튼이 `navigator.clipboard.writeText` 호출
   - `review-page-content` 분기: `review_type="project_card"` → 카드, `"research"`/`undefined` → 13섹션
2. **타입체크**: `npx tsc --noEmit`로 빌드 타입 통과 확인.
3. **시각 확인**: Playwright로 카드 상세화면을 실제 렌더해 7블록·인터랙션 확인(스크린샷).

## 비범위 (다음 슬라이스)

- ④/⑦ 진도·결과 저장 백엔드 API + 웹 연결
- `example_prompt` 온보딩 도메인 개인화
- 홈 피드 "이어서 하기"(시작했지만 미완 카드) 연동
```
