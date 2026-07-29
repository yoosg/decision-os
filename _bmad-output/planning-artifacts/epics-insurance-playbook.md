---
stepsCompleted: [step-01, step-02, step-03, step-04]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-decision-os-2026-07-21/prd.md
  - _bmad-output/planning-artifacts/architecture/architecture-decision-os-2026-07-21/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/ux-designs/ux-decision-os-2026-07-21/DESIGN.md
  - _bmad-output/planning-artifacts/ux-designs/ux-decision-os-2026-07-21/EXPERIENCE.md
---

# Decision OS - Epic Breakdown

## Overview

이 문서는 Decision OS의 전체 에픽 및 스토리 분해를 제공하며, PRD, UX 디자인, 아키텍처 요구사항을 구현 가능한 스토리로 분해합니다.

## Requirements Inventory

### Functional Requirements

FR-0.1: 사용자는 계정을 생성하고 로그인할 수 있다
FR-0.2: 모든 보험 정보, Decision 이력, Outcome 데이터는 사용자 계정에 귀속된다
FR-1.1: 사용자는 가입 보험 정보를 수동으로 입력할 수 있다 (보험사, 상품명, 보험료, 보장 항목)
FR-1.2: [ASSUMPTION] 보험증권 이미지를 업로드하면 주요 항목을 자동으로 파싱한다 (OCR/LLM 멀티모달 — 기술 방식 Deferred)
FR-1.3: 청구 이력을 입력할 수 있다 (청구 일자, 항목, 금액, 처리 결과)
FR-1.4: 비교 견적을 입력할 수 있다 (타 보험사 또는 비교 사이트에서 가져온 견적 정보)
FR-2.1: 사용자의 현재 보험 구성과 청구 이력을 분석해 보장 적절성 리포트를 생성한다
FR-2.2: 현재 보험료 수준이 적정한지 LLM 기반으로 평가 근거를 제시한다; 비교 견적이 입력된 경우 견적과의 구체적 비교 분석을 추가로 제공한다
FR-2.3: 갱신·약관 변경 내용을 요약하고, 주요 변경점과 수락 여부에 대한 검토 의견을 제공한다
FR-2.4: [ASSUMPTION] 사용자의 생애 주기 정보(가족 구성, 연령대 등)를 입력받아 현재 상황에 보험이 적합한지 맥락적 분석을 제공한다 (수집 범위 UX 설계 시 확정)
FR-3.1: 사용자는 각 Review에 대한 최종 결정을 기록할 수 있다 (채택 / 보류 / 무시)
FR-3.2: 결정 당시의 이유와 메모를 함께 저장할 수 있다
FR-3.3: 결정 이력을 시간순으로 조회할 수 있다
FR-4.1: 사용자는 이전 결정의 결과를 기록할 수 있다 (지급 / 거절 / 추가서류 요청)
FR-4.2: 기록된 Outcome은 이후 Review 생성 시 맥락으로 반영된다
FR-5.1: 현재 보유 보험 현황을 한눈에 볼 수 있는 요약 화면(Home Inbox + HealthScoreCard)을 제공한다
FR-5.2: 진행 중인 Review 및 미결정 항목을 확인할 수 있다
FR-5.3: 과거 Decision·Outcome 이력을 타임라인으로 조회할 수 있다 (Memory Timeline)

### NonFunctional Requirements

NFR-1: 타겟 시장 — 한국 시장 전용; 한국 보험 상품·법규·용어 기준으로 설계한다
NFR-2: 데이터 프라이버시 — 보험·청구 이력 등 민감 금융 데이터는 사용자 계정 범위 내에서만 접근 가능해야 한다; 모든 Playbook 테이블에 RLS 필수; service_role key 클라이언트 노출 금지
NFR-3: AI 신뢰성 — AI 검토 결과는 참고 의견임을 명시하며, 근거를 함께 제시해야 한다; HonestBox는 불확실성 존재 시 절대 생략 불가; LegalDisclaimerBar 필수 상시 표시
NFR-4: 폼팩터 — 모바일 웹(375–430px) 및 데스크탑 웹(≥768px, max-width 480px) 모두 지원; Flutter iOS/Android 앱 추가 지원
NFR-5: 콜드 스타트 — 청구 이력이 없어도 기본 Review가 가능해야 한다
NFR-6: 접근성 — WCAG 2.2 AA 준수; 모든 인터랙티브 요소 44×44pt 터치 타겟; 색상만으로 정보 전달 금지; prefers-reduced-motion 지원
NFR-7: 성능/비동기 — Review 생성은 비동기(202 즉시 응답); processing 상태 타임아웃 5분; 모든 FastAPI 로그 JSON 구조화 + review_id 포함

### Additional Requirements

아키텍처에서 도출된 기술 요구사항:

- **스타터 템플릿 없음 (Greenfield)**: Next.js + FastAPI + Flutter + Supabase 조합으로 신규 구성. Epic 1 Story 1에서 프로젝트 초기 설정 필요
- **스택 고정 (AD-2)**: Next.js (Railway MVP → Vercel), Flutter (iOS/Android), FastAPI (Railway MVP → Render/Fly.io), Supabase (PostgreSQL + Auth + Storage + pgvector + Realtime), LLM: OpenAI Responses API (Chat Completions 불허)
- **데이터 접근 패턴 (AD-3)**: 읽기 → Supabase JS SDK/supabase_flutter SDK 직접 조회 (anon key + JWT + RLS); 쓰기 → FastAPI 경유 (service_role key); 집계·크로스-테이블 읽기 → FastAPI 경유
- **Playbook 데이터 모델 (AD-4)**: 공통 테이블(`projects`, `reviews`, `decisions`, `outcomes`, `activities`); Insurance 전용 테이블(`insurance_policies`, `insurance_claims`, `insurance_documents`); `reviews.context_snapshot`·`reviews.result`는 `{"schema_version": int, "review_type": str, "payload": {...}}` JSONB 봉투 형식 고정
- **Review 비동기 실행 (AD-5)**: 트리거 → 202 즉시 응답 → BackgroundTask; 상태 머신: `pending → processing → completed | failed`; `completed`·`failed` 진입 후 추가 변경 금지; 프론트는 Supabase Realtime 또는 폴링으로 완료 감지
- **AI Review 엔진 패턴 (AD-6)**: `ReviewContextBuilder` 타입별 구현; `LLMProvider` 인터페이스 (`generate(ReviewContext) → LLMResponse`); RAG는 pgvector(Supabase)만 허용; 새 Review 타입 = 새 `ReviewContextBuilder` 구현
- **Memory 테이블 (AD-7)**: MVP부터 `memories` 테이블 포함; `memory_type`: `decision_pattern` | `preference` | `outcome_insight` | `context`; `summary` 임베딩(VECTOR 1536) 저장; FastAPI만 쓰기 가능
- **MVP 보험 Playbook 범위 (AD-8)**: 사용자당 Insurance Project 1개 자동 생성("내 보험 관리"); MVP 첫 Review 타입: 병원 영수증 → 청구 가능 보험 분석; Memory 구현 및 Anthropic/Local LLM은 MVP 제외
- **RLS 구현 패턴 (AD-9)**: Playbook 테이블 RLS는 `project_id → projects.user_id` 서브쿼리 방식 필수; 테이블 내 `user_id` 직접 비정규화 방식 금지
- **보안 (AD-10)**: 파일 업로드 MIME 타입·크기 상한 검증(FastAPI); LLM 호출 시 시스템 프롬프트와 사용자 데이터 분리; Railway 환경변수로 시크릿 관리; PIPA 최소 수집 원칙
- **테스트 전략 (AD-11)**: 비즈니스 로직·`ReviewContextBuilder` → FastAPI 단위 테스트(실제 Supabase 테스트 DB, 프로덕션 DB 모킹 금지); LLM Provider → `LLMProvider` 인터페이스 모킹; 비동기 Review 상태 전이 → BackgroundTask 통합 테스트; Next.js → 컴포넌트 단위 테스트
- **관찰 가능성 (AD-12)**: 모든 FastAPI 로그 JSON 구조화, `review_id`·`playbook_type` 필드 포함; `processing` 상태 타임아웃 설정값 초과 시 `failed` 전이; 모든 FastAPI 예외는 `review_id` 포함 로그 필수
- **API 계약 (AD-13)**: 인증: `Authorization: Bearer {Supabase JWT}`; 기본 경로: `/api/v1/`; 응답 봉투: `{"data": ..., "error": null | {"code": str, "message": str}}`; 웹/모바일 분기 엔드포인트 금지
- **Flutter 상태관리 (AD-14)**: Riverpod 2.x 단일 표준; `@riverpod` 코드 생성 방식 사용; 비동기 Review 상태는 `StreamProvider`로 Supabase Realtime 구독

### UX Design Requirements

UX-DR1: 디자인 토큰 시스템 구현 — Surface(surface-base/raised/card/card-alt/overlay), Text(primary/secondary/tertiary/disabled), Border(subtle/card), Accent/Status(accent-primary/foreground, status-positive/positive-bg/warning/uncertain, error/error-bg, honest-box) 색상 토큰을 CSS 커스텀 프로퍼티로 구현; 모노크로매틱 팔레트; Dark mode 토큰은 MVP 제외
UX-DR2: 타이포그래피 스케일 구현 — Screen Title(28-30px/700/-0.5px), Section Title(22-24px/700/-0.3px), Body Large(17px/600/-0.2px), Body(15-16px/500-600), Label(13px/600), Caption(11-12px/500-600/0.4-0.8px), Badge(10px/700/0.5px uppercase) — system-ui 폰트 스택; 한국어 lang="ko" 루트 설정; 영어 고유명사(Review, CODEF, AI, Memory, NEW, OS, ID) lang="en" 인라인 마킹
UX-DR3: 레이아웃·스페이싱 시스템 구현 — Mobile-first, 20px horizontal padding, max-width 480px(≥768px desktop); 4·8·12·16·20·24·32·48px 스페이싱 스케일; surface color steps으로 깊이 표현(그림자 없음 — nav-plus FAB 단일 예외); 카드·버튼·시트 코너 반경 토큰 구현
UX-DR4: 5탭 하단 내비게이션 구현 — 홈/프로젝트/+(FAB)/메모리/프로필; + 탭은 화면 전환 없이 PlusBottomSheet 트리거; nav-plus: 52×52px 원형, accent-primary 배경, box-shadow(0 4px 16px rgba(0,0,0,0.25)) 단일 허용; bottom safe area 20px
UX-DR5: ContextStickyBar 컴포넌트 구현 — Review 상세 전용 fixed bottom 바; disabled/enabled 2상태; 섹션(Summary+Recommendation+HonestBox+Evidence+Risk) 뷰포트 진입 또는 키보드/스크린리더 포커스 시 활성화; Short Review 예외 조건(HonestBox 없음 AND 청구액 < 50,000원) 백엔드 플래그로 처리; 완전한 ARIA 패키지(aria-disabled, aria-live, aria-label, aria-describedby, DOM 위치 역전); 강제 스크롤 금지; prefers-reduced-motion 지원
UX-DR6: InboxCard 컴포넌트 구현 — surface-card 배경, 16px 반경, 16px padding; NEW 배지(accent-primary 배경, 최초 열기 시 제거); 우선순위 정렬(NEW Review > Event 후보 > 진행중 Action); 복합 aria-label(제목+배지+타임스탬프) 명시적 제공
UX-DR7: EventCandidateCard 컴포넌트 구현 — InboxCard와 동일한 시각 쉘; 미확인 상태 필수 유지, 자동 확인 절대 금지; 명시적 "보험 프로젝트에 반영" CTA 필수; OCR 4개 필드 데이터 표시(병원명, 진료일, 진료비, 진료 유형)
UX-DR8: HealthScoreCard 컴포넌트 구현 — 반전 색상(accent-primary 배경, white 텍스트); 점수 56px/weight 800; 아크 링 시각(64×64px); 동향 방향 표시; AI 생성 문구 및 규제 면책 표시; 점수 방법론 info 아이콘; 카드 탭 → Insurance Project 상세 이동
UX-DR9: PlusBottomSheet 컴포넌트 구현 — surface-overlay scrim; 4가지 옵션(병원 영수증 촬영 강조, 병원 방문 직접 등록, 보험 정보 추가, 기타 기록); 단일 레이어 제한(Bottom Sheet 스택 금지); drag/scrim 탭 dismiss; Android back gesture는 시트만 닫기
UX-DR10: MemoryTimelineItem 컴포넌트 구현 — 수직 타임라인(2px border-subtle 좌측 척추); 12px 도트(Event=text-secondary, Review/Decision=text-primary, Outcome=색상+글리프 구분: 지급=status-positive+₩, 거절=text-primary+✕, 추가서류=text-secondary+?); surface-card 카드(12px 반경, 12×14px padding); 월 구분선; 탭 → 원본 화면 이동(아카이브 시 read-only 전체 내용 뷰)
UX-DR11: OCRFieldRow 컴포넌트 구현 — Default/Error/Confirmed/PlausibilityWarning 4개 상태; 각 필드 독립 편집 가능(다른 필드 초기화 없음); AI 면책 문구("AI가 인식한 내용입니다. 정확하지 않을 수 있습니다.") 필드 목록 상단 1회 고정; 금액 과대 추출 경고(예: 외래 진료비 > 500,000원) 차단 없이 경고만 표시
UX-DR12: HonestBox 컴포넌트 구현 — Review 상세 Recommendation 이후 Evidence 이전 필수 위치; 불확실성 존재 시 절대 생략 불가; severity 플래그("standard"|"high")에 따른 left-border accent(3px, status-warning); 헤딩 "AI가 확인하지 못한 정보" verbatim; 보험료 인상 관련 필드 필수 포함
UX-DR13: LegalDisclaimerBar 컴포넌트 구현 — Review 상세(ContextStickyBar 상단) 및 서류 체크리스트 화면(CTA 상단) 필수 렌더링; non-dismissable; 법적 문구 verbatim("본 분析은 참고 정보이며, 보험사의 최종 심사 기준과 다를 수 있습니다. Decision OS는 보험 모집 또는 중개 행위를 하지 않습니다."); 배경 surface-base, top border border-subtle
UX-DR14: 접근성 플로어 구현 — WCAG 2.2 AA; 모든 인터랙티브 요소 44×44pt 터치 타겟; 한국어 화폐 금액 aria-label 철자 표기(₩72,000 → "칠만 이천 원"); prefers-reduced-motion 전역 지원(모든 로딩 애니메이션 정적 대체, 트랜지션 즉시 전환); Outcome 입력 카드 role="radio"/radiogroup 구현; 색상 독립성(색상만으로 정보 전달 금지)
UX-DR15: 온보딩 플로우 구현 — CODEF 자동 연동 경로(신뢰 신호 → 내보험다보여 ID/PW → 로딩(~30초) → 건강도 결과); 수동 입력 폴백; 부분 성공(N/M 건 연동) 처리; 알림 권한 최초 1회(건강도 결과 화면 직후) 요청; 온보딩 이후 재요청 금지(iOS: OS 설정 앱으로 안내)
UX-DR16: Push 알림 패턴 구현 — 4가지 트리거(새 Review/Event 후보/Outcome 입력 요청/후속 Action); 3일 재알림 정책(1회만); 딥링크 → Home Inbox 진입(Review 직접 딥링크 금지); 마케팅·재참여 알림 금지
UX-DR17: 상태 패턴 전체 구현 — 빈 Inbox, Review 생성 중/실패, OCR 실패, Event 후보 미확인, ContextStickyBar disabled/enabled, Decision 3상태(채택→서류체크리스트, 보류→Inbox 복귀, 무시→아카이브+토스트), Outcome 대기, 연동 실패·부분성공, Memory 첫 사용자 빈 상태 등 명세된 모든 상태 패턴 구현
UX-DR18: Contextual Chat 구현 — Review 상세/Insurance Project 상세/병원 방문 직접 등록 3개 화면에서만 진입 가능; 진입 시 컨텍스트 객체 자동 전달; 세션 비지속(앱 종료 시 초기화); Chat에서 Decision 불가(채택 CTA 없음); floating chat FAB 절대 금지
UX-DR19: Voice & Tone 준수 — AI Review 제목은 가능성 프레이밍 필수("가능성이 있습니다", "해당될 수 있습니다"); 선언형 제목 금지; 마이크로카피 참조 테이블 준수(채택/보류/무시 레이블 고정, 동의어 치환 금지); 긴급 언어 금지; 거절 Outcome 화면의 맥락 카피 명세 준수

### FR Coverage Map

FR-0.1: Epic 1 — 계정 생성/로그인
FR-0.2: Epic 1 — 사용자 계정 귀속
FR-1.1: Epic 1 — 수동 보험 정보 입력 (온보딩 + + sheet)
FR-1.2: Post-MVP — 이미지 파싱 방식 미확정 (Architecture Deferred)
FR-1.3: Epic 2 — 영수증 촬영/직접 입력 = 청구 이력 이벤트
FR-1.4: Epic 4 — 비교 견적 입력
FR-2.1: Epic 2 — 병원 영수증 → 청구 가능 보험 분석 (MVP 첫 Review 타입)
FR-2.2: Epic 2 + 4 — 기본 LLM 평가(E2) + 견적 비교 추가(E4)
FR-2.3: Post-MVP — 갱신·약관 검토는 2번째 Review 타입 (AD-8 순차 확장)
FR-2.4: Post-MVP — 생애 주기 수집 범위 미확정 (Architecture Deferred)
FR-3.1: Epic 3 — Decision 기록 (채택/보류/무시)
FR-3.2: Epic 3 — 결정 이유·메모 저장
FR-3.3: Epic 3 — 결정 이력 시간순 조회
FR-4.1: Epic 3 — Outcome 기록 (지급/거절/추가서류)
FR-4.2: Epic 3 — Outcome → 다음 Review 맥락 반영
FR-5.1: Epic 1 + 2 — Health Score (E1) + Home Inbox 완성 (E2)
FR-5.2: Epic 2 + 4 — 진행 중 Review (E2 Home) + Inbox Full List (E4)
FR-5.3: Epic 3 — Memory Timeline 조회

## Epic List

### Epic 1: 앱 기반 구성 + 계정 + 보험 정보 온보딩
사용자가 앱에 가입하고, 보험 정보를 자동 연동(CODEF 내보험다보여) 또는 직접 입력하여, 첫 보험 건강도 점수와 기본 Project 현황을 확인할 수 있다.
**FRs covered:** FR-0.1, FR-0.2, FR-1.1, FR-5.1(일부)

### Epic 2: 이벤트 등록 → 비동기 AI Review → Review 상세 검토
사용자가 병원 영수증을 촬영하거나 방문 이력을 직접 입력하면, AI가 청구 가능 보험을 비동기로 분석한 Review를 Home Inbox에서 확인하고, Review 상세에서 섹션별로 검토할 수 있다.
**FRs covered:** FR-1.3, FR-2.1, FR-2.2(기본 LLM 평가), FR-5.1(Home Inbox 완성), FR-5.2(진행 중 Review)

### Epic 3: Decision 기록 + 서류 Checklist + Outcome 추적 + Memory Timeline
사용자가 Review에 대해 결정(채택/보류/무시)을 내리고, 청구 서류 체크리스트를 관리하며, 보험금 지급 결과(Outcome)를 기록하고, 전체 의사결정 이력을 Memory Timeline에서 시간 순으로 조회할 수 있다.
**FRs covered:** FR-3.1, FR-3.2, FR-3.3, FR-4.1, FR-4.2, FR-5.3

### Epic 4: 비교 견적 관리 + Home Inbox 전체 보기 + Contextual Chat
사용자가 타사 비교 견적을 입력해 AI 보험료 분석에 반영하고, Inbox 전체 목록을 조회하며, Review/Project 맥락에서 AI에게 직접 질문할 수 있다.
**FRs covered:** FR-1.4, FR-2.2(견적 비교 추가), FR-5.2(Inbox Full List)

---

## Epic 1: 앱 기반 구성 + 계정 + 보험 정보 온보딩

사용자가 앱에 가입하고, 보험 정보를 자동 연동(CODEF 내보험다보여) 또는 직접 입력하여, 첫 보험 건강도 점수와 기본 Project 현황을 확인할 수 있다.

**생성 테이블:** `projects`, `insurance_policies`

### Story 1.1: 이메일 회원가입 및 로그인 (풀스택 초기화 포함)

As a new user,
I want to create an account and log in to Decision OS,
So that my insurance data and decisions are securely tied to my personal account.

**Acceptance Criteria:**

**Given** 앱에 처음 접속한 사용자가 회원가입 화면에서 이메일과 비밀번호를 입력했을 때
**When** "회원가입" CTA를 탭하면
**Then** Supabase Auth에 계정이 생성되고, `projects` 테이블에 Insurance Project("내 보험 관리", `playbook_type=insurance`)가 자동으로 1개 생성되며, 온보딩 Welcome 화면으로 이동한다
**And** 이미 가입된 이메일 재시도 시 "이미 사용 중인 이메일입니다" 오류 메시지가 표시된다

**Given** 기존 계정 보유 사용자가 이메일/비밀번호를 입력했을 때
**When** "로그인" CTA를 탭하면
**Then** Supabase JWT가 발급되고, Home 화면으로 진입한다
**And** 틀린 비밀번호 입력 시 "이메일 또는 비밀번호가 올바르지 않습니다" 메시지가 표시된다

**Given** FastAPI 기반 API 서버가 실행 중일 때
**When** 클라이언트가 `Authorization: Bearer {JWT}` 헤더 없이 보호된 엔드포인트를 호출하면
**Then** `{"data": null, "error": {"code": "UNAUTHORIZED", "message": "..."}}` 형식의 401 응답을 반환한다

> 구현 범위 포함: Next.js 앱 기본 구조, FastAPI 앱 기본 구조(구조화 JSON 로그 포함), Supabase 프로젝트 설정, `projects` 테이블 + `activities` 테이블 + RLS(`project_id → projects.user_id` 서브쿼리 방식), CSS 디자인 토큰 시스템(surface/text/border/accent/status), 타이포그래피 스케일, 모바일-퍼스트 레이아웃(20px padding, max-width 480px)
>
> **Flutter 앱(iOS/Android)은 웹 MVP 완성 후 별도 에픽으로 분리.** Architecture AD-2·AD-3·AD-14(Riverpod 2.x, supabase_flutter SDK)는 해당 에픽에서 구현. 현재 에픽 1–4는 Next.js 웹 전용 범위.

---

### Story 1.2: CODEF 내보험다보여 자동 보험 연동

As a new user in onboarding,
I want to import my insurance policies automatically using my 내보험다보여 account,
So that I can see all my current insurance coverage without entering each policy manually.

**Acceptance Criteria:**

**Given** 온보딩 Welcome 화면에서 "자동으로 가져오기" 선택 후 신뢰 신호 화면 확인 완료 후
**When** 내보험다보여 ID/PW 입력 후 "가져오기 시작" CTA를 탭하면
**Then** "보험 정보를 가져오는 중입니다. 약 30초 소요됩니다." 로딩 화면이 표시되고, 로딩 중 재제출이 비활성화된다
**And** CODEF API 성공 시 가져온 보험 정책이 `insurance_policies` 테이블에 `source=codef` 태그로 저장되고, 건강도 결과 화면으로 이동한다

**Given** CODEF API가 오류 또는 타임아웃을 반환했을 때
**When** 연동 실패가 감지되면
**Then** "자동 연동에 실패했습니다." 화면에 "직접 입력할게요" CTA와 "다시 시도하기" CTA가 표시된다
**And** "직접 입력할게요" 탭 시 수동 보험 입력 화면으로 이동한다

**Given** CODEF API가 부분 성공(M건 중 N건만 연동)을 반환했을 때
**When** 연동 결과가 표시되면
**Then** "보험 N건 연동됨 (총 M건 중)" 메시지와 "직접 추가하기" CTA가 함께 표시된다

> 구현 범위 포함: `insurance_policies` 테이블 + RLS, FastAPI CODEF 연동 엔드포인트, 신뢰 신호 화면("비밀번호는 저장하지 않습니다" / "언제든지 연동 해제 가능")

---

### Story 1.3: 수동 보험 정보 직접 입력

As a user who cannot or prefers not to use CODEF,
I want to manually enter my insurance policy details one by one,
So that I can still receive an insurance health analysis with my self-reported data.

**Acceptance Criteria:**

**Given** 온보딩에서 "직접 입력할게요" 선택 또는 CODEF 실패 폴백으로 수동 입력 화면 진입 후
**When** 보험사, 상품명, 월 보험료, 주요 보장을 입력하고 "보험 추가" CTA를 탭하면
**Then** 해당 보험이 `insurance_policies` 테이블에 `source=manual` 태그로 저장되고, 폼이 초기화되며, 추가된 보험이 목록에 표시된다
**And** 추가된 보험 항목 옆에 삭제 아이콘이 제공된다

**Given** 보험 1건 이상 추가된 상태에서
**When** "완료" CTA를 탭하면
**Then** 건강도 결과 화면으로 이동한다

**Given** 보험을 0건 추가한 상태에서
**When** "나중에 추가하기" CTA를 탭하면
**Then** 빈 보험 목록 상태로 건강도 결과 화면으로 이동하며, 이후 + Bottom Sheet "보험 정보 추가"를 통해 추가할 수 있다

---

### Story 1.4: 보험 건강도 점수 생성 및 온보딩 완료 화면

As a user who has connected or entered insurance data,
I want to see my AI-generated Insurance Health Score with a plain-language interpretation,
So that I immediately understand my overall insurance coverage quality and can decide to allow notifications.

**Acceptance Criteria:**

**Given** 온보딩(CODEF 연동 또는 수동 입력) 완료 후 건강도 결과 화면에 진입했을 때
**When** FastAPI Health Score 계산이 완료되면
**Then** HealthScoreCard(0–100 점수, 아크 링, 상태 레이블, 보험 N건/월 N원/다음 Review 스탯 바)와 AI 생성 2–3줄 평문 해석이 표시된다
**And** "보험업법상 인가된 평가 지표가 아닙니다" 면책 문구가 표시된다

**Given** 건강도 결과 화면이 로드된 직후
**When** 알림 권한 요청 UI("새 Review가 생성되면 알려드릴까요?" / "허용" / "나중에")가 표시될 때
**Then** "허용" 탭 시 OS 알림 권한 요청이 실행되고, "나중에" 탭 시 권한 요청 없이 진행된다
**And** 이 화면 이후 앱 내에서 알림 권한 재요청이 발생하지 않으며, iOS에서는 거부 후 OS 설정 앱 안내만 허용된다

**Given** `source=manual` 태그 보험이 1건 이상 포함된 보험 데이터로 Health Score가 생성된 경우
**When** 이후 해당 Project에서 Review가 생성될 때
**Then** HonestBox에 "일부 보험 정보는 직접 입력 자료로, AI가 실제 약관을 확인하지 못했습니다" 항목이 필수로 포함된다

---

### Story 1.5: 5탭 내비게이션 + Insurance Project 상세 + Profile 기본

As a logged-in user,
I want to navigate the app through the bottom tab bar and view my full Insurance Project details and profile settings,
So that I can see my policy list, health score, and manage my integration and notification preferences.

**Acceptance Criteria:**

**Given** 로그인된 사용자가 앱을 사용 중일 때
**When** 하단 탭 바가 표시되면
**Then** 홈/프로젝트/+(FAB)/메모리/프로필 5개 탭이 표시되고, + 탭은 52×52px 원형 accent-primary 버튼으로 내비게이션 바 위에 떠있으며 `box-shadow: 0 4px 16px rgba(0,0,0,0.25)`가 적용된다
**And** + 탭 탭 시 화면 전환 없이 PlusBottomSheet 스켈레톤이 올라온다 (옵션 구현은 Epic 2)

**Given** "프로젝트" 탭 탭 또는 HealthScoreCard 탭으로 Insurance Project 상세 화면 진입 시
**When** 화면이 로드되면
**Then** 상단에 HealthScoreCard(accent-primary 반전 배경, 점수/아크/스탯 바), 연동된 보험 목록(보험사/상품명/월 보험료/source 태그), Review 이력 섹션(빈 상태)이 표시된다
**And** CODEF 마지막 동기화 날짜가 표시되며, 30일 이상 경과 시 "보험 정보가 30일 이상 지났습니다" 경고 배지와 "다시 가져오기" CTA가 표시된다

**Given** "프로필" 탭 진입 시
**When** Profile 화면이 로드되면
**Then** CODEF 연동 상태(연동됨 / 미연동), 알림 설정 항목(알림 허용 → OS 설정 앱 안내), "연동 해제" CTA, 계정/데이터 관리 기본 항목이 표시된다

---

## Epic 2: 이벤트 등록 → 비동기 AI Review → Review 상세 검토

사용자가 병원 영수증을 촬영하거나 방문 이력을 직접 입력하면, AI가 청구 가능 보험을 비동기로 분석한 Review를 Home Inbox에서 확인하고, Review 상세에서 섹션별로 검토할 수 있다.

**생성 테이블:** `insurance_documents` (2.1), `reviews` + `insurance_claims` (2.3)

### Story 2.1: PlusBottomSheet + 영수증 촬영 + OCR 결과 확인

As a user who visited a hospital,
I want to photograph my receipt and review the AI-extracted fields,
So that I can register the visit event accurately without typing all the details manually.

**Acceptance Criteria:**

**Given** 홈 화면에서 + 탭을 탭했을 때
**When** PlusBottomSheet가 올라오면
**Then** 4개 옵션(병원 영수증 촬영 / 병원 방문 직접 등록 / 보험 정보 추가 / 기타 기록)이 표시되고, "병원 영수증 촬영"이 시각적으로 강조된다
**And** drag handle 아래로 또는 scrim 탭 시 Sheet가 닫힌다; Back gesture(Android)는 Sheet만 닫고 탭 전환 없음

**Given** PlusBottomSheet에서 "병원 영수증 촬영"을 탭했을 때
**When** 네이티브 카메라가 열리고 영수증을 촬영하면
**Then** 이미지가 FastAPI에 업로드되어 MIME 타입·크기 검증 후 Supabase Storage에 저장되고, OCR 처리가 실행된다
**And** OCR 성공 시 4개 필드(병원명, 진료일, 진료비, 진료 유형)가 추출되어 OCR 결과 확인 화면으로 이동한다

**Given** OCR 결과 확인 화면에서 필드를 검토할 때
**When** 화면이 로드되면
**Then** 상단에 "AI가 인식한 내용입니다. 정확하지 않을 수 있습니다." 문구가 1회 표시되고, 4개 OCRFieldRow가 각각 Default/Error/Confirmed/PlausibilityWarning 상태로 표시된다
**And** 각 필드는 독립적으로 탭해서 수정 가능하며, 수정 완료 시 Confirmed 상태(checkmark + "필드명 ✓")로 전환된다

**Given** 진료비 필드 값이 플라우저빌리티 임계값(외래 기준 500,000원)을 초과할 때
**When** OCR 결과가 표시되면
**Then** 해당 필드에 `status-warning` 테두리와 "일반적인 외래 진료비보다 높습니다. 금액을 다시 확인해 주세요." 경고 텍스트가 표시된다
**And** 사용자가 값을 수정하지 않아도 "확인" CTA 제출이 가능하다 (차단하지 않음)

**Given** OCR 처리가 실패하여 필드를 인식하지 못했을 때
**When** 오류가 감지되면
**Then** "영수증을 인식하지 못했습니다." 메시지와 "직접 입력하기" CTA(→ Story 2.2 화면), "다시 촬영하기" CTA가 표시된다

---

### Story 2.2: 병원 방문 직접 등록 폼

As a user without a receipt or with a failed OCR,
I want to manually enter my hospital visit details through a form,
So that I can register the event and trigger an AI Review without a photograph.

**Acceptance Criteria:**

**Given** PlusBottomSheet에서 "병원 방문 직접 등록" 선택 또는 OCR 실패 후 "직접 입력하기" 탭으로 진입했을 때
**When** 직접 등록 폼 화면이 로드되면
**Then** 병원명, 진료일, 진료비, 진료 유형 4개 필드가 빈 상태로 표시되고, 병원명 필드에 자동 포커스된다
**And** "이벤트로 저장" CTA는 필수 항목이 모두 입력되기 전까지 비활성화된다

**Given** 모든 필수 필드를 입력한 상태에서 "이벤트로 저장" CTA를 탭했을 때
**When** 제출 처리가 진행되면
**Then** CTA가 로딩 상태(스피너)로 전환되고 필드가 비편집 상태가 되며, 성공 시 입력 데이터로 Event 후보 확인 화면으로 이동한다

**Given** 필수 필드가 비어 있는 상태에서 "이벤트로 저장"을 탭했을 때
**When** 유효성 검사가 실행되면
**Then** 비어 있는 각 필수 필드에 error 테두리와 "필수 항목입니다." 힌트 텍스트가 표시된다
**And** 포커스가 첫 번째 오류 필드로 이동한다; toast 없음

---

### Story 2.3: Event 후보 확인 + 비동기 AI Review 생성

As a user who has entered or confirmed a hospital visit,
I want to confirm the event candidate and trigger an AI insurance analysis,
So that the system generates a Review while I can continue using the app or close it.

**Acceptance Criteria:**

**Given** OCR 결과 확인 또는 직접 등록 완료 후 Event 후보 확인 화면에 진입했을 때
**When** 화면이 로드되면
**Then** "병원명 · 진료일 · 진료비" 정보가 표시된 EventCandidateCard가 표시되고, "보험 프로젝트에 반영" CTA와 "취소 / 다시 확인" 옵션이 함께 제공된다
**And** 이벤트는 사용자가 명시적으로 "보험 프로젝트에 반영"을 탭하기 전까지 자동으로 확인되지 않는다

**Given** 사용자가 "보험 프로젝트에 반영" CTA를 탭했을 때
**When** 이벤트가 확인되면
**Then** FastAPI에 Review 트리거 요청이 전송되어 202 Accepted가 즉시 반환되고, `reviews` 테이블에 `status=pending` Review가 생성되며, 분析 중 화면으로 이동한다
**And** `insurance_claims` 테이블에 이벤트 데이터(병원명, 진료일, 진료비, 진료 유형)가 저장된다

**Given** Review BackgroundTask가 실행 중일 때
**When** ReviewContextBuilder가 컨텍스트를 조립하면
**Then** 해당 Project의 `insurance_policies` 데이터 조회, pgvector RAG 약관 검색, LLMProvider(`generate(ReviewContext) → LLMResponse`) 호출이 순차적으로 실행된다
**And** LLM 응답 수신 후 `reviews` 테이블에 `status=completed`, `result` JSONB(`{"schema_version": 1, "review_type": "receipt_analysis", "payload": {...}}`), Review 제목(가능성 프레이밍 필수)이 저장된다; `completed` 진입 후 추가 변경 금지

**Given** BackgroundTask가 5분 내에 완료되지 않거나 오류를 반환했을 때
**When** 실패가 감지되면
**Then** `reviews.status`가 `failed`로 전환되고, 업로드 파일은 보존되며, 자동 재시도 없음
**And** 분析 중 화면에서는 "분析을 완료하지 못했습니다." 메시지와 "다시 분析하기" CTA, "홈으로 돌아가기" CTA가 표시된다

**Given** 분析 중 화면에서 "홈으로 돌아가기"를 탭하거나 앱을 닫았을 때
**When** Review가 아직 완료되지 않은 상태이면
**Then** Home의 Inbox 섹션 상단에 "분析 중입니다. 앱을 닫아도 됩니다." 배너가 표시된다

> 구현 범위 포함: `reviews` 테이블 + RLS, `insurance_claims` 테이블 + RLS, ReviewContextBuilder(`receipt_analysis` 타입), LLMProvider 인터페이스 + OpenAI Responses API 구현체, pgvector HNSW 인덱스 기본 설정, FastAPI 구조화 로그(`review_id` + `playbook_type` 필드 필수)

---

### Story 2.4: Home Inbox — Review 카드, 상태 관리 및 Push 알림

As a user waiting for or receiving a Review,
I want to see the current state of my pending items in the Home Inbox and receive a push notification when a Review is ready,
So that I know exactly what needs my attention without having to manually check.

**Acceptance Criteria:**

**Given** 로그인된 사용자가 Home 화면을 열었을 때
**When** 대기 중인 Inbox 항목이 없으면
**Then** 빈 Inbox 상태로 Project 현황 카드와 "다음 Review 예정: [날짜]" 레이블이 표시된다; 차분하고 정보 제공적인 빈 상태이며 축하 메시지 없음

**Given** Supabase Realtime 구독이 활성화된 상태에서 `reviews.status`가 `completed`로 전환됐을 때
**When** 프론트엔드가 Realtime 이벤트를 수신하면
**Then** Home Inbox에 새 Review InboxCard가 즉시 추가된다; 카드에 "NEW" 배지(accent-primary 배경), Review 제목, 타임스탬프가 표시된다
**And** 앱이 백그라운드 또는 종료 상태일 경우 Push 알림("새 Review가 있습니다 — [Review 제목]")이 발송된다

**Given** Home Inbox에 여러 항목이 있을 때
**When** Inbox 섹션이 렌더링되면
**Then** NEW Review > Event 후보 > 진행 중 Action 우선순위 순으로 정렬된다
**And** InboxCard 탭 시 해당 항목의 상세 화면으로 이동한다; 복합 aria-label("제목, NEW, 날짜")이 명시적으로 제공된다

**Given** Review `status=failed`인 항목이 Inbox에 있을 때
**When** InboxCard가 렌더링되면
**Then** "분析 실패 — [이벤트 요약]" 제목과 "다시 분析하기" CTA가 표시된다

---

### Story 2.5: Review 상세 화면 + ContextStickyBar + HonestBox + LegalDisclaimerBar

As a user who received a Review,
I want to read through all Review sections and have the action button activate only after I've engaged with the key content,
So that I make an informed decision rather than acting on the recommendation alone.

**Acceptance Criteria:**

**Given** Home Inbox에서 Review InboxCard를 탭했을 때
**When** Review 상세 화면이 로드되면
**Then** Summary / Recommendation / HonestBox / Evidence / Risk/Uncertainty 섹션이 순서대로 표시된다; `h1`=Review 제목, `h2`=각 섹션 헤딩 heading hierarchy 준수
**And** 보험료 인상 여부 관련 필드(청구 이력의 갱신 보험료 영향 여부)가 Evidence 또는 Recommendation 바로 아래에 포함된다

**Given** Review 상세 화면이 처음 로드됐을 때
**When** ContextStickyBar가 표시되면
**Then** disabled 상태로 렌더링된다: primary CTA `text-disabled` 배경, lock 아이콘, `aria-disabled="true"`, hint text "추천 근거를 먼저 확인해 주세요 ↑", secondary CTAs 숨김, 추천 텍스트 비공개
**And** disabled CTA 탭 시 shake animation이나 error toast 없이 hint text만 표시된다

**Given** 사용자가 Summary, Recommendation, HonestBox, Evidence, Risk/Uncertainty 섹션을 모두 뷰포트에 진입시키거나 키보드/스크린리더 포커스를 통과시켰을 때
**When** 마지막 필수 섹션이 확인되면
**Then** ContextStickyBar가 enabled 상태로 전환된다: primary CTA accent-primary 배경, 추천 텍스트 공개, secondary CTAs("나중에 검토" / "무시") 표시
**And** `aria-live="polite"` 영역이 "청구 준비 시작 버튼을 사용할 수 있습니다"를 1회 발화한다; `prefers-reduced-motion` 시 전환 애니메이션 없이 즉시 전환

**Given** Review에 불확실성이 존재할 때
**When** HonestBox가 Review 상세에 렌더링될 때
**Then** Recommendation 섹션 직후, Evidence 섹션 직전에 위치한다; 헤딩 "AI가 확인하지 못한 정보" verbatim; `severity=high` 항목은 left-border `status-warning` 3px accent 적용, `severity=standard`는 border 없음
**And** 불확실성이 존재하는 Review에서 HonestBox가 생략되면 렌더링 오류로 처리된다

**Given** Review 상세 화면이 렌더링될 때
**When** LegalDisclaimerBar가 표시되면
**Then** ContextStickyBar 바로 위에 non-dismissable로 고정된다; 닫기 버튼·접기 없음; 법적 문구 verbatim: "본 분析은 참고 정보이며, 보험사의 최종 심사 기준과 다를 수 있습니다. Decision OS는 보험 모집 또는 중개 행위를 하지 않습니다."

**Given** 모든 인터랙티브 요소가 렌더링될 때
**When** 사용자가 터치 입력을 시도하면
**Then** 모든 인터랙티브 요소의 터치 타겟이 최소 44×44pt 이상이다
**And** `lang="ko"`가 HTML 루트에 설정되고, Review/CODEF/AI/Memory/NEW/OS/ID는 해당 위치에 `lang="en"` 인라인 마킹이 적용된다

> AI Review 제목 생성 규칙: "가능성이 있습니다", "해당될 수 있습니다", "N건 확인됨" 등 가능성 프레이밍 필수; 선언형 제목 금지 (FastAPI Review 생성 프롬프트에 하드 제약으로 포함)

---

## Epic 3: Decision 기록 + 서류 Checklist + Outcome 추적 + Memory Timeline

사용자가 Review에 대해 결정(채택/보류/무시)을 내리고, 청구 서류 체크리스트를 관리하며, 보험금 지급 결과(Outcome)를 기록하고, 전체 의사결정 이력을 Memory Timeline에서 시간 순으로 조회할 수 있다.

**생성 테이블:** `decisions` (3.1), `outcomes` (3.3), `memories` (3.4)

### Story 3.1: 채택 Decision 기록 + 서류 Checklist 화면

As a user who has read a Review and decided to file a claim,
I want to tap the primary action button to record my decision and see the required documents,
So that I know exactly what to prepare before submitting the claim to my insurer.

**Acceptance Criteria:**

**Given** Review 상세에서 ContextStickyBar가 enabled 상태이고 사용자가 "채택 — 직접 청구" CTA를 탭했을 때
**When** Decision이 처리되면
**Then** FastAPI에 Decision 쓰기 요청이 전송되어 `decisions` 테이블에 `choice=채택`, `review_id`, 타임스탬프가 저장된다
**And** 확인 다이얼로그 없이 즉시 서류 Checklist 화면으로 이동하고, 해당 Review의 Inbox 항목 상태가 "보험 청구 진행 중"으로 변경된다

**Given** 서류 Checklist 화면이 로드됐을 때
**When** 화면이 표시되면
**Then** LegalDisclaimerBar("본 分析은 참고 정보이며...")가 primary CTA 위에 non-dismissable로 고정되고, 상단 서브헤더("다음 단계는 보험사 앱 또는 창구에서 직접 진행합니다. Decision OS는 청구 절차에 관여하지 않습니다.")가 표시된다
**And** AI가 생성한 필요 서류 목록(예: 진단서, 진료비 영수증, 개인정보 활용동의서)이 체크리스트 항목으로 표시되며, 각 항목은 독립적으로 체크 가능하다

**Given** 서류 Checklist 화면의 각 체크리스트 항목에서
**When** 항목을 탭해 확장하면
**Then** "이 서류를 구하기 어렵다면" 도움말 행이 펼쳐진다
**And** 화면 하단에 "서류 준비가 어려워요" secondary CTA가 표시된다 (Contextual Chat 진입점; Chat 구현은 Epic 4)

**Given** 결정 당시 이유 또는 메모를 기록하고 싶은 사용자가
**When** Checklist 화면에서 메모 입력 필드에 텍스트를 입력하면
**Then** 해당 내용이 `decisions.memo` 필드에 저장된다

---

### Story 3.2: 보류/무시 Decision 처리

As a user who is not ready to act on a Review,
I want to defer it for later or dismiss it entirely,
So that my Inbox stays clean while the Review remains accessible when I need it.

**Acceptance Criteria:**

**Given** Review 상세에서 ContextStickyBar enabled 상태의 "나중에 검토" ghost CTA를 탭했을 때
**When** 보류 Decision이 처리되면
**Then** FastAPI에 `choice=보류` Decision이 저장되고, 확인 다이얼로그 없이 Review가 Inbox로 복귀하며, "NEW" 배지가 "보류"로 즉시 교체된다 (낙관적 업데이트)
**And** Inbox 카드에 "보류한 날로부터 N일째" 시간 표시가 추가된다

**Given** 보류 Decision이 기록된 날로부터 90일이 경과했을 때
**When** 시스템이 경과를 감지하면
**Then** "보류 중인 보험 청구 Review가 있습니다." Push 알림이 1회 발송된다; 90일 이후 추가 재알림 없음

**Given** Review 상세에서 "무시" ghost CTA를 탭했을 때
**When** 무시 Decision이 처리되면
**Then** FastAPI에 `choice=무시` Decision이 저장되고, Review가 active Inbox에서 제거되며, 3초 non-blocking toast "이 Review는 메모리에서 다시 볼 수 있습니다."가 표시된다
**And** 확인 다이얼로그 없음; 무시된 Review는 Memory Timeline에서 해당 이벤트 체인의 일부로 조회 가능하다

**Given** Inbox 항목이 3일간 확인되지 않았을 때
**When** 시스템이 미확인 상태를 감지하면
**Then** 해당 항목에 대한 follow-up Push 알림이 1회 발송된다; 3일 후 추가 Push 없음

---

### Story 3.3: Outcome 입력 + Inbox 카드 + Push 알림

As a user who filed an insurance claim after adopting a Review,
I want to record the claim result when the insurer makes a decision,
So that the outcome feeds into my decision history and improves future AI Reviews.

**Acceptance Criteria:**

**Given** 채택 Decision 이후 N일이 경과했고 Outcome이 아직 입력되지 않았을 때
**When** 시스템이 Outcome 미입력을 감지하면
**Then** Home Inbox에 "보험금 지급 결과를 입력해 주세요" InboxCard가 추가되고, Push 알림 "보험금 지급 결과를 입력해 주세요"가 1회 발송된다
**And** 동일 항목에 대한 추가 Push 없음 (3일 재알림 정책 적용)

**Given** Inbox의 Outcome 요청 카드를 탭해 Outcome 입력 화면에 진입했을 때
**When** 화면이 로드되면
**Then** "지급 완료 / 거절됨 / 추가 서류 요청" 3가지 선택지가 `role="radiogroup"` 내 `role="radio"` 구현으로 표시된다
**And** primary CTA "기록하기"는 선택지 중 하나를 탭하기 전까지 비활성화된다

**Given** 사용자가 "지급 완료"를 선택하고 금액을 입력한 후 "기록하기"를 탭했을 때
**When** Outcome이 저장되면
**Then** FastAPI가 `outcomes` 테이블에 `result=지급`, 금액, 날짜를 저장한다
**And** 화폐 금액은 `aria-label="칠만 이천 원"` 방식으로 철자 표기 aria-label이 적용된다

**Given** 사용자가 "거절됨"을 선택하고 "기록하기"를 탭했을 때
**When** Outcome이 저장되면
**Then** 맥락 카피가 표시된다: "이번 청구가 거절됐습니다. AI 分析은 참고 정보이며, 보험사의 심사 기준에 따라 결과가 다를 수 있습니다. 거절 사유를 기록하면 다음 분析에 반영됩니다."
**And** 거절 사유 텍스트 입력 필드(선택 입력)가 제공되며, 사유는 `outcomes.note`에 저장되어 해당 Project의 이후 Review 컨텍스트에 반영된다

**Given** Outcome이 저장됐을 때
**When** FastAPI가 Outcome을 처리하면
**Then** Event → Review → Decision → Outcome 체인이 `memories` 테이블에 기본 기록으로 삽입된다 (AI 자동 추출은 MVP 제외; 직접 체인 참조 저장)

---

### Story 3.4: Memory Timeline 화면

As a user who wants to review past decisions,
I want to see a chronological timeline of all my events, Reviews, decisions, and outcomes,
So that I can track the full history of my insurance decision loop in one place.

**Acceptance Criteria:**

**Given** "메모리" 탭을 탭했을 때
**When** Memory Timeline 화면이 로드되면
**Then** 확인된 Event, Review, Decision, Outcome이 시간 역순으로 MemoryTimelineItem 컴포넌트로 표시된다; 2px `border-subtle` 수직 척추, 12px 도트(Event=text-secondary, Review/Decision=text-primary, Outcome=색상+글리프 구분), 월 구분선 포함
**And** Outcome 도트는 색상만으로 구분하지 않는다: 지급=status-positive+₩ 글리프, 거절=text-primary+✕ 글리프, 추가서류/대기=text-secondary+? 글리프

**Given** Memory Timeline에 기록된 항목이 없을 때
**When** 첫 사용자가 메모리 탭을 열면
**Then** "아직 기록된 의사결정이 없습니다. 첫 이벤트를 등록하면 이곳에 기록이 시작됩니다." 빈 상태 텍스트가 표시된다; 일러스트레이션 없음

**Given** Memory Timeline에서 특정 항목을 탭했을 때
**When** 탭 이벤트가 발생하면
**Then** 해당 항목의 원본 화면(Review 상세, Outcome 입력 결과 등)으로 이동한다
**And** 원본 Review가 아카이브된 경우 "보관된 Review" 배너가 표시된 read-only 전체 내용 화면이 렌더링된다; 요약본이 아닌 전체 내용 보존

**Given** 결정 이력을 시간순으로 조회해야 할 때
**When** Memory Timeline이 렌더링되면
**Then** Decision 항목은 `choice`(채택/보류/무시)와 `memo`(있는 경우), 타임스탬프를 포함하여 표시된다

> 구현 범위 포함: `memories` 테이블 스키마(memory_type, summary 텍스트, embedding VECTOR(1536) 컬럼 포함) + FastAPI Outcome 처리 후 기본 체인 기록; embedding 생성 및 AI 자동 추출은 MVP 제외

---

## Epic 4: 비교 견적 관리 + Home Inbox 전체 보기 + Contextual Chat

사용자가 타사 비교 견적을 입력해 AI 보험료 분석에 반영하고, Inbox 전체 목록을 조회하며, Review/Project 맥락에서 AI에게 직접 질문할 수 있다.

**생성 테이블:** 없음 (기존 테이블 활용)

### Story 4.1: 비교 견적 입력 및 보험료 적정성 분석 반영

As a user who has gathered quotes from other insurers,
I want to enter comparison quotes so the AI can evaluate whether my current premiums are appropriate,
So that I can make an informed decision about switching or keeping my current policies.

**Acceptance Criteria:**

**Given** + Bottom Sheet에서 "보험 정보 추가" 옵션을 탭했을 때
**When** 비교 견적 입력 화면이 로드되면
**Then** 보험사명, 상품명, 월 보험료, 주요 보장 항목 필드와 함께 "견적 추가" CTA가 표시된다
**And** 추가된 견적이 `insurance_policies` 테이블에 `source=quote` 태그로 저장되고 Insurance Project 상세의 견적 목록에 표시된다

**Given** `source=quote` 태그 견적이 1건 이상 존재하는 Project에서 Review가 생성될 때
**When** ReviewContextBuilder가 컨텍스트를 조립하면
**Then** 현재 보험료와 입력된 비교 견적의 구체적 비교 분석이 Review `result.payload`에 포함된다
**And** 비교 견적이 없는 경우 기존 LLM 기반 보험료 적정성 평가만 제공된다

**Given** `source=quote` 태그 보험이 포함된 Review가 생성됐을 때
**When** Review 상세에서 HonestBox가 렌더링되면
**Then** "비교 견적은 사용자가 직접 입력한 정보로, AI가 실제 약관 내용을 확인하지 못했습니다." 항목이 포함된다

---

### Story 4.2: Home Inbox 전체 보기 (Inbox Full List)

As a user with many pending Inbox items,
I want to see the complete list of all items on a dedicated screen,
So that I can manage everything without the home screen truncating my list.

**Acceptance Criteria:**

**Given** Home Inbox 항목이 5건을 초과할 때
**When** Home Inbox 섹션 하단에 "전체 보기" 링크가 표시되면
**Then** 탭 시 Inbox Full List 화면으로 이동한다

**Given** Inbox Full List 화면이 로드됐을 때
**When** 항목이 있으면
**Then** NEW Review > Event 후보 > 진행 중 Action 우선순위 순으로 동일한 InboxCard 컴포넌트로 렌더링된다
**And** 20건 초과 시 무한 스크롤 또는 "더 보기" 페이지네이션이 적용된다; 인라인 광고 또는 프로모션 콘텐츠 없음

**Given** Inbox Full List 화면에 항목이 없을 때
**When** 화면이 로드되면
**Then** "모든 항목을 확인했습니다." 텍스트와 작은 체크마크 아이콘(24px, text-secondary)이 표시된다; 축하 메시지 없음

---

### Story 4.3: Contextual Chat

As a user reviewing a Review, Project, or registering an event,
I want to ask the AI questions in context,
So that I can get clarification without leaving my current screen or making a premature decision.

**Acceptance Criteria:**

**Given** Review 상세, Insurance Project 상세, 병원 방문 직접 등록 화면 중 하나에 있을 때
**When** 화면 내 "AI에게 질문하기" 텍스트 링크(13px / text-secondary / underline)를 탭하면
**Then** Contextual Chat 화면이 현재 화면 위 navigation stack으로 푸시된다; modal 또는 Bottom Sheet 아님
**And** 시스템이 현재 컨텍스트 객체를 자동으로 전달한다 (Review ID → Review 내용 + Project 컨텍스트; Project ID → Project 요약 + 보험 목록; Event 초안 → 현재 입력 필드)

**Given** Contextual Chat 화면이 로드됐을 때
**When** 첫 AI 메시지가 표시되면
**Then** 컨텍스트를 인식하는 안내 메시지("이 Review에 대해 궁금한 점을 물어보세요." 등)가 표시되고, 입력 바에 포커스가 위치한다
**And** AI 메시지는 좌측 정렬(surface-card 배경), 사용자 메시지는 우측 정렬(accent-primary 배경, accent-foreground 텍스트)로 렌더링된다

**Given** 사용자가 Chat 화면에서 back navigation을 실행했을 때
**When** 이전 화면으로 복귀하면
**Then** 이전 화면의 스크롤 위치가 유지된다; Chat 화면이 originating screen 위에 요약 또는 메시지를 표시하지 않는다
**And** 세션은 비지속(앱 종료 또는 화면 재진입 시 초기화)되어 이전 대화 내용이 남지 않는다

**Given** Chat에서 AI 응답이 실패하거나 타임아웃됐을 때
**When** 오류가 감지되면
**Then** 마지막 AI 메시지 아래 "응답을 받지 못했습니다. 잠시 후 다시 시도해 주세요." 인라인 메시지와 재시도 CTA가 표시된다

**Given** 사용자가 Chat 화면에 있을 때
**When** 어떤 상황에서도
**Then** Chat 내에 "채택", "청구", "보험 해지" 등 Decision을 실행하는 CTA가 존재하지 않는다; Decision은 반드시 Review 상세의 ContextStickyBar를 통해서만 가능하다

> AI Review 제목 생성 규칙: "가능성이 있습니다", "해당될 수 있습니다", "N건 확인됨" 등 가능성 프레이밍 필수; 선언형 제목 금지 (FastAPI Review 생성 프롬프트에 하드 제약으로 포함)
