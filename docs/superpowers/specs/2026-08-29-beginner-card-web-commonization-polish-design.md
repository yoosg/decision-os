# 입문자 카드 — 웹 공용화 + 폴리시 (슬라이스 3a)

- 날짜: 2026-08-29
- 범위: **웹만**. 백엔드·카드 스키마·프롬프트 변경 없음(그건 슬라이스 3b, 별도).
- 성격: 한 슬라이스에서 **공용화(리팩터) 먼저 → 폴리시(시각) 이어서**. 커밋을 두 단계로 나눠 리뷰 부담을 낮춘다.
- 대상 화면: 입문자 프로젝트 카드가 렌더되는 모든 곳
  - `project-card-content.tsx` — 인터랙티브 카드(홈/큐, `reviewId` 보유, 진도 저장 O)
  - `chain-detail-content.tsx` — 읽기전용 카드(히스토리 체인, 저장 X)
  - 두 곳 다 `ProjectCardMeta`/`ProjectCardBlocks`를 공유하므로 폴리시가 자동 반영된다.

## 목표

지금 카드는 모든 블록이 같은 시각 무게·여백(24px)이라 긴 스크롤이 밋밋하고, 블록 성격(정보/인터랙티브/프롬프트)이 구분되지 않는다. 동시에 카드 코드에는 중복(환경변수·토큰·백링크·체크박스 리스트·리뷰 타입 문자열 분기)이 흩어져 있다.

- **공용화**: 동작을 그대로 두고 중복을 제거해 폴리시가 손댈 토대를 깨끗이 만든다.
- **폴리시**: 승인된 방향 **C(하이브리드 강조) + 모노크롬**으로 블록에 위계를 준다.

---

## 파트 1 — 공용화 (behavior-preserving, 먼저)

각 항목은 **동작 무변경**이 원칙. 검증은 tsc + Playwright E2E(아래 "검증").

### 1.1 API 베이스 URL / 액세스 토큰 헬퍼 — 전체 11곳 치환

현재 `process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://localhost:8000"`가 11곳, `getSession()→access_token` 패턴이 다수 파일에 복붙돼 있다.

- 신규 `web/src/lib/api.ts` (plain `.ts`, **`"use client"` 아님** — RSC 경계 안전, 메모리 `web-rsc-client-boundary-values` 준수):
  - `export const API_BASE_URL = process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://localhost:8000";` (NEXT_PUBLIC은 빌드타임 인라인 → 순수 상수라 어디서든 import 가능)
  - `export async function getAccessToken(): Promise<string | null>` — `createClient().auth.getSession()`에서 `access_token` 반환 (브라우저 supabase 사용, 클라이언트 컴포넌트에서만 호출)
- **11개 FASTAPI_URL 사용처 전부** `API_BASE_URL`로 치환:
  outcome/page · chat/page · learning-path/page · onboarding/page · use-card-progress · review-page-content · daily-brief-content · context-sticky-bar · profile-content · queue-content · lib/engagement.ts
- `getSession()→access_token` 인라인들도 `getAccessToken()`로 치환.
- 주의: 카드 밖 파일(온보딩·프로필·큐·데일리브리프)도 건드리므로 동작 무변경을 E2E로 넓게 확인.

### 1.2 `ReviewType` 유니온 + 판별 유니온으로 `as` 캐스트 제거

현재 `reviewType: string | null` + `payload as ProjectCardPayload` 캐스트가 `chain-detail-content`(2곳)·`review-page-content`에 흩어져 있어, 오타/누락이 런타임까지 샌다.

- 신규 `web/src/components/home/review/review-types.ts`:
  - `export type ReviewType = "research" | "project_card";`
  - `export function isProjectCard(t: ReviewType | string | null): t is "project_card"` (문자열 → 타입 좁히기)
- `ChainDetailData.review`를 **판별 유니온**으로:
  ```ts
  review:
    | { reviewType: "project_card"; payload: ProjectCardPayload }
    | { reviewType: "research"; payload: ReviewPayload }
    | null;
  ```
  → 분기에서 `payload as ...` 캐스트 2곳 제거(좁혀짐). 데이터를 만드는 `chain/[signalId]/page.tsx`는 `reviewType`에 맞춰 좁혀 넘기도록 수정.
- `review-page-content`의 `reviewType?: string | null`도 `ReviewType | null`로 교체.

### 1.3 `BackLink` 컴포넌트

동일한 chevron SVG + inline-flex 라벨이 3곳(`project-card-content` 홈으로, `chain-detail-content` 히스토리로, `research-review-content` 홈으로)에 복붙.

- 신규 `web/src/components/ui/back-link.tsx`: props `{ href: string; children: ReactNode }`. chevron SVG + `text-label`·`--text-secondary`·`marginBottom` 스타일 캡슐화.
- 위 3곳을 `<BackLink href=...>홈으로</BackLink>` 형태로 교체.
- 범위 밖: `learning-path`/`generating`/`failed`의 "홈으로 돌아가기"는 버튼 스타일이 달라 건드리지 않는다.

### 1.4 `CheckableList<T>` 추출 (마일스톤 ↔ 성공 체크리스트)

`MilestoneList`와 `SuccessChecklist`가 체크박스 행 골격(ul 리셋·label flex·체크박스 정렬)을 중복.

- `project-card-blocks.tsx` 안에 제네릭 `CheckableList<T>` 추출:
  - props `{ items: T[]; checked: Set<number>; onToggle: (i:number)=>void; renderLabel: (item:T)=>ReactNode; header?: ReactNode }`
  - ul/li/label/checkbox 골격 + 상단 `header`(옵션, 예: `0/2` 카운트) 담당
- `MilestoneList` = `CheckableList` + `renderLabel`(action 블록 + `끝나면 · done_signal`) + header(카운트)
- `SuccessChecklist` = `CheckableList` + `renderLabel`(문자열) (header 없음)
- **동작·prop 무변경**: `ProjectCardBlocks`가 progress/로컬 폴백으로 넘기는 `checked`/`onToggle` 계약 그대로.

### 1.5 (범위 명시) 토스트

`role="status"` fixed 토스트가 6곳에 있으나 위치·지속·스타일이 제각각. 카드의 저장-실패 토스트(`project-card-content`)는 **이번 슬라이스에서 그대로 유지**(공용화·폴리시 대상 아님). 6곳 공용 `Toast` 추출은 **별도 슬라이스로 defer**(블래스트 반경·스타일 편차 큼). → 데드코드/불필요 추상화 방지(YAGNI).

---

## 파트 2 — 폴리시 (시각, 방향 C · 모노크롬, 이어서)

승인된 목업(`.superpowers/brainstorm/.../fullcard.html`의 after) 기준. **앱 모노크롬 토큰만 사용**(`--accent-primary:#0D0D0D`, 회색 계열). 색 신규 도입 없음.

적용 위치는 `project-card-blocks.tsx`(`ProjectCardMeta`·`ProjectCardBlocks`)와 `project-card-content.tsx`. 기존 인라인 스타일 + CSS 변수 관례 유지.

### 2.1 헤더 / 난이도 뱃지 (`ProjectCardMeta`)

- 난이도 뱃지: 회색 pill(`--surface-card`) + **모노크롬 단계 도트** — `첫걸음 ●○○` / `기본 ●●○` / `도전 ●●●`. (신호등 색 미사용 — 오너 지시 "색은 앱 톤에")
- 시간·스킬을 한 줄로 압축: `⏱ 30분 · 🎓 {skill_label}` → 헤더 3줄에서 2줄로.
- 도트 표현은 난이도별 상수 맵(`first_step→●○○` 등)으로. `CARD_DIFFICULTY_LABEL`은 라벨 텍스트로 계속 사용.

### 2.2 완성물 = 히어로 블록 (`ProjectCardBlocks` ①)

- `deliverable`+`success_preview`를 **검정 히어로 박스**로: `background:var(--accent-primary,#0D0D0D)`, `color:#fff`, `borderRadius:14px`.
  - 라벨 `📦 완성하면 이게 나와`(작게, opacity), value(`deliverable`, bold), preview(`✓ {success_preview}`, 흐리게).
- 목적: 카드 진입 즉시 "완성하면 뭐가 나오는지"를 각인(동기부여).

### 2.3 정보 블록 — 담백하게 (② 준비물, ⑤ 막히면)

- 카드/배경 없이 섹션 타이틀 + 본문 텍스트. 본문은 `--text-secondary`로 눌러 인터랙티브/히어로와 대비.
- ⑤ 막히면: 증상(bold) + `→ 처방`(흐리게) 포맷.

### 2.4 프롬프트 박스 + 복사 피드백 (③ 이렇게 시작해)

- 프롬프트 박스: `--surface-raised` 유지.
- 복사 버튼 상태: `📋 복사` → 클릭 시 `✓ 복사됨`(검정 fill: `background:#0D0D0D; color:#fff`)로 눌린 상태를 또렷이. 2초 후 원복(기존 타이머 로직 유지).

### 2.5 인터랙티브 블록 — 좌측 액센트 (④ 진행 과정, ⑥ 다 됐는지)

- `background:#F7F7F7`(≈surface-card) + **좌측 3px 검정 액센트 바**(`border-left:3px solid #0D0D0D`, `borderRadius:0 12px 12px 0`) → "여기는 네가 체크하는 곳" 시각 신호.
- ④ 헤더에 카운트를 우측 정렬(`0/2`). 마일스톤 보조문구 `끝나면: ` → `끝나면 · `.

### 2.6 여백 리듬 / 결과 버튼 (⑦)

- 블록 그룹 사이 얇은 구분선(`#F0F0F0`) + 성격별 간격으로 스크롤에 리듬.
- 결과 버튼(성공/막힘/포기): 구조·저장 로직 무변경. 활성 = 검정 테두리 + `--surface-card` fill(기존 유지).

### 폴리시 불변식(회귀 금지)

- 진도 저장(`useCardProgress`) 계약·`progress` 옵셔널 prop·로컬 폴백 **무변경** — 시각만 변경.
- 체인 상세(읽기전용, `progress` 없음)에서도 동일 컴포넌트가 회귀 없이 렌더.
- 접근성: 체크박스 `label` 연결·터치 타깃(≥44px)·`aria-pressed`(결과 버튼) 유지.

---

## 검증 (메모리 `web-test-runner-vitest`: main엔 vitest 러너 없음 → tsc + Playwright)

1. `tsc --noEmit` (또는 `next build` 타입체크) 통과 — 특히 1.2 판별 유니온 후 캐스트 제거가 컴파일로 검증됨.
2. Playwright 라이브 E2E:
   - 인터랙티브 카드(홈): 렌더 · 복사(✓ 복사됨) · 체크박스 토글→디바운스 저장→새로고침 복원 · 결과 버튼.
   - 체인 상세(읽기전용): 카드/리서치 분기 정상 렌더, 저장 없음.
   - 공용화 회귀: 온보딩·프로필·큐·데일리브리프가 API_BASE_URL/getAccessToken 치환 후에도 정상 동작(happy-path).
3. before/after 시각 스냅샷 비교(스크린샷).

## 스코프 아웃 (하지 않음)

- 백엔드·카드 스키마·프롬프트(3b 생성 내용 심화), `example_prompt` 개인화(별도 슬라이스).
- 6곳 공용 `Toast` 추출(별도 슬라이스로 defer).
- 리서치용 `DIFFICULTY_LABEL`(review-sections) — 카드와 별개 도메인이라 손대지 않음.
- 신규 색 도입(모노크롬 유지).
