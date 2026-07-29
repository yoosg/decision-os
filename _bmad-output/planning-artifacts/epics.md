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

이 문서는 Decision OS AI Research Playbook의 전체 에픽 및 스토리 분해를 제공하며, PRD, UX 디자인, 아키텍처 요구사항을 구현 가능한 스토리로 분해합니다.

## Requirements Inventory

### Functional Requirements

FR-0.1: 사용자는 계정을 생성하고 로그인할 수 있다
FR-0.2: 온보딩 시 역할(Role)과 관심 기술 영역(Project/Focus)을 입력할 수 있다 (7단계 wizard: Role → Experience → Tech Stack → Project/Goal → Interests → Daily Learning Time)
FR-0.3: 모든 학습 이력, Decision, Outcome, Memory 데이터는 사용자 계정에 귀속된다

FR-1.1: 매일 사용자에게 관련성 높은 AI 기술 Signal을 큐레이션해 Daily Brief로 제공한다
FR-1.2: Signal은 기사 하나가 아니라, 하나의 기술 또는 변화에 대한 여러 출처(공식 블로그, GitHub, Reddit, HN, YouTube 등)를 묶은 Decision Event다
FR-1.3: Signal은 중복 제거 및 정규화 처리를 거쳐 생성된다
FR-1.4: [ASSUMPTION] 개인화된 Memory를 기반으로 Signal의 우선순위와 관련성이 조정된다

FR-2.1: 각 Signal에 대해 사용자가 "배울지 말지" 결정할 수 있도록 충분한 Research Review를 생성한다
FR-2.2: Research Review는 13개 섹션을 반드시 포함한다: (1)한 줄 정의, (2)핵심 개념 설명, (3)해결하는 문제, (4)왜 중요한가, (5)기존 기술과 차이, (6)사용자 관련성, (7)학습 목표, (8)예상 학습 시간·난이도, (9)실무 적용 가능성, (10)위험 요소, (11)추천 이유, (12)참고 출처, (13)HonestBox
FR-2.3: 사용자는 Review 하나만 읽어도 해당 기술의 기본 개념을 이해할 수 있어야 한다

FR-3.1: 사용자는 각 Review에 대해 세 가지 CTA 중 하나를 선택할 수 있다: Learn Now / Queue / Ignore
FR-3.2: Queue 선택 시 타이밍을 지정할 수 있다: Today / This Week / Later
FR-3.3: 결정 당시의 이유와 메모를 함께 저장할 수 있다
FR-3.4: 결정 이력을 시간순으로 조회할 수 있다

FR-4.1: "Learn Now"를 선택하면 해당 기술에 대한 Learning Path를 생성한다
FR-4.2: Learning Path는 공식 문서, 핵심 자료, GitHub, 실습 예제, 적용 아이디어를 기반으로 구성된다 (5가지 고정 리소스 타입, 순서 고정)

FR-5.1: 사용자는 학습 결과를 Outcome으로 기록할 수 있다: Completed / Applied / Dropped / Not Useful
FR-5.2: Outcome 기록 시 피드백을 남길 수 있다: 유용했는가(토글), 적용했는가(Applied 선택 시 프로젝트 메모), 실제 학습 시간(분), 메모
FR-5.3: 기록된 Outcome은 이후 Signal 추천 및 Review 생성 시 맥락으로 반영된다

FR-6.1: 시스템은 사용자의 Decision·Outcome 이력을 기반으로 Memory를 구축한다
FR-6.2: Memory는 다음 항목으로 구성된다: Preference, Skill, Project, Decision History, Outcome History; 임베딩(vector 1536) 저장
FR-6.3: Memory를 기반으로 Daily Brief와 Research Review의 추천 품질을 지속적으로 개선한다

FR-7.1: 오늘의 Daily Brief와 미결정 Signal을 한눈에 확인할 수 있는 홈 화면을 제공한다
FR-7.2: Queue에 쌓인 학습 항목과 예정 일정을 Today / This Week / Later 그룹으로 확인할 수 있다
FR-7.3: 과거 Decision·Outcome 이력을 Memory Timeline으로 조회할 수 있다 (Signal → Review → Decision → Outcome 체인)

FR-8.1: 실제 외부 소스(RSS/Atom, HackerNews, GitHub Releases)에서 AI 기술 기사를 수집한다 [POST-MVP, Epic 6]
FR-8.2: 수집 기사를 의미 유사도로 클러스터링하여 동일 주제를 1개 Signal(다중 출처)로 묶는다 [POST-MVP, Epic 6]
FR-8.3: 도메인 무관/유해/저품질 기사를 시그널 생성 이전에 필터링한다 [POST-MVP, Epic 6]
FR-8.4: Recommender는 프로필/관심사 임베딩과 최신성·다양성·인기 피처로 시그널을 랭킹한다 (substring 매칭 제거) [POST-MVP, Epic 6]
FR-8.5: 노출·열람·결정 engagement를 로깅하고 추천 품질(RAG vs 콜드 스타트)을 오프라인 평가한다 [POST-MVP, Epic 6]

### NonFunctional Requirements

NFR-1: 타겟 시장: 한국 시장 전용; 한국어 UI, lang="ko" HTML root 설정; 한국 AI 커뮤니티 맥락에서 설계한다
NFR-2: 데이터 프라이버시: 학습 이력, Decision, Memory 등 사용자 데이터는 사용자 계정 범위 내에서만 접근 가능해야 한다; RLS 필수; PIPA 최소 수집 원칙
NFR-3: AI 신뢰성: Review 결과는 참고 의견임을 명시하며, 근거를 함께 제시해야 한다; HonestBox로 불확실성 항상 공개
NFR-4: 폼팩터: 모바일 웹(375–430px), 데스크탑 웹(≥768px centered 480px max) 및 Flutter 네이티브 앱(iOS/Android) 모두 지원한다
NFR-5: 콜드 스타트: Memory가 없어도 Role·Focus 기반으로 기본 Daily Brief와 Review가 가능해야 한다

### Additional Requirements

아키텍처(ARCHITECTURE-SPINE.md)에서 추출한 구현에 영향을 미치는 기술 요구사항:

- **스택 (AD-2):** Next.js (Railway→Vercel) · Flutter (iOS/Android) · FastAPI (Railway→Render/Fly.io) · Supabase (PostgreSQL+Auth+Storage+pgvector+Realtime) · FCM; 외부 벡터DB, 별도 인증 서버, FCM 외 Push 서비스 금지
- **데이터 접근 (AD-3):** 읽기 → Supabase 직접(RLS+anon key+JWT); 쓰기 → FastAPI 경유(service_role); `reviews/decisions/outcomes/activities/memories/learning_paths` 테이블 쓰기는 FastAPI만
- **데이터 모델 (AD-4):** `projects.playbook_type`이 도메인 분기 단일 진입점; `reviews.context_snapshot/result` JSONB 봉투 형식 고정 (`{schema_version, review_type, payload}`); `signals`는 플랫폼 레벨, `daily_briefs/learning_paths`는 사용자 레벨
- **비동기 AI (AD-5):** 모든 LLM 호출(Review 생성, Learning Path)은 BackgroundTask 비동기; 202 즉시 응답; Supabase Realtime 또는 폴링으로 완료 감지; 상태 머신: `pending → processing → completed | failed`; completed/failed 진입 후 추가 변경 금지
- **AI Review 엔진 (AD-6):** `ReviewContextBuilder` (타입별 구현) + `LLMProvider` 인터페이스 `generate(ReviewContext) → LLMResponse`; MVP는 OpenAI Responses API (Chat Completions 불허); RAG는 pgvector(Supabase)만
- **Memory (AD-7):** MVP부터 `memories` 테이블 포함; `memory_type`: preference|skill|project|decision_history|outcome_history; `summary` 임베딩 저장; FastAPI만 쓰기
- **MVP 범위 (AD-8):** 사용자당 AI Research Project 1개 자동 생성; Decision CTA 3종; Queue 타이밍 3종; Outcome 4종; Research Review 13섹션 필수; `Learn Now` 선택 시에만 Learning Path 생성
- **RLS 패턴 (AD-9):** Playbook 테이블 RLS는 `project_id → projects.user_id` 서브쿼리; user_id 직접 테이블은 `user_id = auth.uid()` 단순 정책
- **보안 (AD-10):** 파일 업로드 허용 MIME·크기 검증; 시스템 프롬프트와 사용자 데이터 컨텍스트 분리 전달; Railway 환경변수로 시크릿 관리; PIPA 최소 수집
- **테스트 (AD-11):** 비즈니스 로직/ReviewContextBuilder/Agent 파이프라인은 실제 Supabase 테스트 DB 연결(프로덕션 DB 모킹 금지); LLM Provider만 인터페이스 모킹; 비동기 상태 전이는 BackgroundTask 통합 테스트
- **관찰가능성 (AD-12):** FastAPI 로그 JSON 구조화, `review_id/playbook_type` 필드 포함; 배치 파이프라인 로그 `brief_date/pipeline_stage/user_count` 포함; `processing` 상태 타임아웃 → `failed` 전이
- **API 계약 (AD-13):** `Authorization: Bearer {Supabase JWT}`; 기본 경로 `/api/v1/`; 응답 봉투 `{"data": ..., "error": null|{"code", "message"}}`; 웹/모바일 분기 엔드포인트 금지
- **Flutter 상태관리 (AD-14):** Riverpod 2.x 단일 표준; `@riverpod` 코드 생성; 비동기 상태는 `StreamProvider`로 Supabase Realtime 구독
- **Agent Workflow (AD-15):** 배치 파이프라인 (APScheduler, 06:00 KST): Collector→Normalizer→Signal Builder→Reviewer→Recommender→Daily Brief DB 저장 → 09:00 FCM Push; On-demand는 Recommender 이후만 (신규가입·프로필변경·Brief실패·사용자재요청 시에만)
- **Collector 패턴 (AD-16):** Source 어댑터 인터페이스; `collect() → list[RawArticle]`; Normalizer가 Signal 변환 전담; 새 Source = 새 어댑터 구현
- **Push Notification (AD-17):** FCM 유일 Push 서비스; Push 트리거 3종: Daily Brief 준비(09:00), Queue Today 리마인더(20:00), Outcome 입력 요청(Learn Now 후 3일); 클라이언트 로그인·앱 오픈 시 FCM 토큰 `/api/v1/devices/register` 등록

### UX Design Requirements

DESIGN.md와 EXPERIENCE.md에서 추출한 구현 가능한 UX 요구사항:

UX-DR1: **디자인 토큰 시스템 구현** — 색상 팔레트(surface-base #FFFFFF, surface-raised #F9F9F9, surface-card #F2F2F2, surface-card-alt #ECECEC, accent-primary #0D0D0D, accent-foreground #FFFFFF, status-positive #16A34A, status-warning #B45309, error #EF4444, surface-honest-box #F5F5F5 등), 타이포그래피 스케일(screen-title 28–30px/700, section-title 22–24px/700, body-large 17px/600, body 15–16px/500, label 13px/600, caption 11–12px/500, badge 10px/700/uppercase), 여백 시스템(4px 기준단위, 20px 화면 좌우 패딩, 16px 카드 내부 패딩), 모서리 반경 시스템(card 16px, pill 9999px, sheet 24px, badge 9999px, timeline-card 12px, option-card 14px) 전체 구현

UX-DR2: **ContextStickyBar 컴포넌트** — Research Review 상세 화면 하단 고정; disabled/enabled 2상태; 섹션 1–6, 10, 11 engagement 완료 시 활성화(IntersectionObserver + viewport/focus); 비활성 시 추천 텍스트 withheld(lock 아이콘, 힌트 텍스트); 활성 시 Learn Now(accent-primary) + Queue/Ignore ghost pills; ARIA 패키지 완전 구현(aria-disabled, aria-live, aria-label, ctx-hint, DOM 위치는 section 13 이후); Dynamic Type ≥150% 시 텍스트 truncate; bar height >40vh 시 secondary ghost pills collapse

UX-DR3: **SignalCard 컴포넌트** — surface-card 배경, 16px radius, 16px 패딩; NEW 배지(accent-primary bg, 미열람 Signal); 관련성 태그 행(12px/text-secondary); 메타 행(11px/text-tertiary: 출처 수, 예상 읽기 시간); composite aria-label 명시적 구현

UX-DR4: **QueueItem 컴포넌트** — TODAY/THIS WEEK/LATER 타이밍 배지(surface-card-alt bg); 미완료 상태(status-warning text, no fill); 일정 변경 텍스트 링크 → bottom sheet; min-height 44px; Semantics composite label

UX-DR5: **OutcomeCard 컴포넌트** — 4종 선택 카드 라디오 그룹(Completed/Applied/Dropped/Not Useful); 선택 상태 border-accent 1.5px(fill 아님); 14px radius, min-height 52px; `role="radiogroup"` + `aria-checked` 구현; Applied 선택 시 추가 프로젝트 입력 필드 표시

UX-DR6: **LearningPathCard 컴포넌트** — 5가지 고정 리소스 타입(공식문서/핵심자료/GitHub/실습예제/적용아이디어), 순서 고정; resource type label 10px/uppercase; 외부 링크 chevron-external 아이콘; surface-card 배경

UX-DR7: **MemoryTimelineItem 컴포넌트** — 수직 타임라인 좌측 2px spine(border-subtle); 12px 도트; Outcome별 color+glyph 병행(✓/→/✕/−); 도트 glyph ExcludeSemantics + Semantics label; 월 구분선; 탭 → 원본 화면 이동; 아카이빙된 Review는 "보관된 Review" 배너 표시

UX-DR8: **HonestBox 컴포넌트** — surface-honest-box (#F5F5F5) 배경; 12px radius; "AI가 확인하지 못한 정보" 제목(11px/uppercase/700/text-secondary); graduated severity: high → status-warning 3px 좌측 border, standard → 보더 없음; AI backend에서 severity 플래그 전달, 프론트는 렌더링만

UX-DR9: **4탭 하단 내비게이션 + Flutter GoRouter** — 홈/큐/히스토리/프로필 4탭; border-top 1px border-subtle; `StatefulShellRoute.indexedStack`; 각 탭 독립 스택(`GlobalKey<NavigatorState>`); 딥링크: `/home` redirect (Research Review 직접 딥링크 금지)

UX-DR10: **7단계 온보딩 wizard** — Welcome → Role(6+1 옵션) → Experience(3옵션) → Tech Stack(multi-select) → Project/Goal(6+1옵션) → Interests(multi-select) → Daily Learning Time(3옵션); 단계별 option card; 뒤로 가기 허용(First Brief Generating 제외); `PopScope(canPop: false)` for First Brief Generating; 알림 권한 요청 화면(첫 Daily Brief 생성 완료 후 1회)

UX-DR11: **Research Review 상세 화면** — 13섹션 h1/h2/h3 헤딩 계층; `data-section-key` 속성; IntersectionObserver engagement tracking(threshold: 0.1); `bar_gate_override` 백엔드 플래그 처리; Contextual Chat 진입점(section 13 하단 텍스트 링크 "AI에게 질문하기"); 생성 중 전체 화면 로딩("앱을 닫아도 됩니다.")

UX-DR12: **알림 권한 요청 패턴** — 온보딩 첫 Daily Brief 생성 완료 후 단 1회 요청; iOS: UNUserNotificationCenter; Android 13+: POST_NOTIFICATIONS via permission_handler; 거부 시 Profile에 "알림 설정" 행 표시(OS Settings 이동, 인앱 재요청 금지)

UX-DR13: **접근성 기준 WCAG 2.2 AA** — 최소 44×44pt 탭 타겟; 색상 독립 상태 표시(glyph 병행); Dynamic Type 지원(fixed height 금지, intrinsic+padding); Reduce Motion: `prefers-reduced-motion` 시 모든 로딩 dot-pulse → 정적, 활성화 전환 → 즉시; VoiceOver/TalkBack engagement tracking 지원(viewport 진입 또는 focus 시 섹션 marked "seen")

UX-DR14: **한국어/영어 언어 마킹** — `lang="ko"` HTML root; 영어 고유명사 `lang="en"` inline 마킹(Review, Signal, Memory, Learn Now, Queue, Ignore, Daily Brief, Learning Path, Outcome, NEW, Applied, Completed, Dropped 등); 한국어 본문 line-height 1.5–1.6; 대문자 badge letter-spacing 명시(0.5–1.2px)

UX-DR15: **Flutter Material 3 ThemeData 완전 override** — `ColorScheme/TextTheme/ShapeTheme` 전체 DESIGN.md 값으로 교체; `splashFactory: NoSplash.splashFactory`(ink/ripple 전면 금지); `showModalBottomSheet` 전용(AlertDialog/showDialog 금지); SafeArea; edge-to-edge(`SystemUiMode.edgeToEdge`); 하단 Bottom Sheet: `RoundedRectangleBorder(top: 24px)`, 수동 drag handle(36×4px/#DDD)

UX-DR16: **Push Notification 패턴** — FCM 단일 서비스; Push 트리거 3종: Daily Brief 준비 "오늘의 AI CTO 브리핑이 준비됐습니다 — [Signal 제목]"(09:00), Queue Today 리마인더 "오늘 학습하기로 한 [Signal 제목]이 남아있습니다"(20:00), Outcome 입력 요청 "학습 결과를 기록해 주세요 — [Signal 제목]"(3일 후); stale notification policy(3일 후 1회 follow-up, 이후 없음); 딥링크 → 항상 Home 랜딩

UX-DR17: **전체 상태 패턴 구현** — Home Daily Brief 6상태(준비됨/생성중/생성실패/신규Signal없음/콜드스타트/전체확인), Research Review 4상태(bar disabled/bar enabled/생성중/Queue서브선택), Queue 6상태(empty/Today그룹/ThisWeek그룹/Later그룹/미완료항목/일정변경), Learning Path 4상태(생성중/준비됨/Outcome요청/생성실패), Onboarding 8상태, History 4상태, Profile 4상태, Contextual Chat 4상태

UX-DR18: **인터랙션 프리미티브 및 금지 패턴** — 탭 단일 primary 인터랙션; Bottom Sheet dismiss(drag/scrim/back); 햅틱 피드백(Learn Now, 기록하기, Queue 타이밍 선택 시); 금지: Floating AI FAB, 카루셀, 자동 Decision 확인, 드래그 리오더(V1), 모달 2중 스택, 롱프레스, V2 + 버튼, 진행률 표시줄/스트릭/달성 배지

### FR Coverage Map

FR-0.1: Epic 1 — 계정 생성·로그인
FR-0.2: Epic 1 — 온보딩 7단계 wizard (Role·Experience·Tech Stack·Project/Goal·Interests·Daily Learning Time)
FR-0.3: Epic 1 — 사용자 데이터 계정 귀속
FR-1.1: Epic 2 — Daily Brief 큐레이션 및 제공
FR-1.2: Epic 2 — Signal = 다출처 기술 묶음 Decision Event
FR-1.3: Epic 2 — Signal 중복 제거·정규화
FR-1.4: Epic 2 — Memory 기반 Signal 우선순위·관련성 조정 [ASSUMPTION]
FR-2.1: Epic 3 — Signal별 Research Review 생성
FR-2.2: Epic 3 — Research Review 13섹션 필수 구조
FR-2.3: Epic 3 — Review 1회 읽기로 기술 기본 개념 이해 가능
FR-3.1: Epic 3 — Decision CTA 3종 (Learn Now / Queue / Ignore)
FR-3.2: Epic 3 — Queue 타이밍 지정 (Today / This Week / Later)
FR-3.3: Epic 3 — 결정 이유·메모 저장
FR-3.4: Epic 5 — 결정 이력 시간순 조회 (Memory Timeline)
FR-4.1: Epic 4 — Learn Now 선택 시 Learning Path 생성
FR-4.2: Epic 4 — Learning Path 5가지 고정 리소스 타입
FR-5.1: Epic 4 — Outcome 4종 기록 (Completed / Applied / Dropped / Not Useful)
FR-5.2: Epic 4 — Outcome 피드백 (유용도·적용 여부·학습 시간·메모)
FR-5.3: Epic 4 — Outcome이 이후 추천에 반영
FR-6.1: Epic 4 — Decision·Outcome 이력 기반 Memory 구축
FR-6.2: Epic 4 — Memory 5가지 타입·임베딩 저장
FR-6.3: Epic 5 — Memory 기반 Daily Brief·Review 추천 품질 향상
FR-7.1: Epic 2 — 홈 화면 Daily Brief 요약 (SignalCard)
FR-7.2: Epic 5 — Queue 항목·예정 일정 확인
FR-7.3: Epic 5 — Decision·Outcome 이력 Memory Timeline 조회

## Epic List

### Epic 1: Platform Foundation & User Identity

사용자가 계정을 만들고, 역할·관심 기술을 설정하여 개인화된 학습 경험을 시작할 수 있다. 이 에픽 완료 후 사용자는 회원가입·로그인하고, 7단계 온보딩을 완료하면 첫 Daily Brief 생성이 시작되는 상태까지 도달한다.

**FRs covered:** FR-0.1, FR-0.2, FR-0.3
**NFRs covered:** NFR-1, NFR-2, NFR-4, NFR-5
**Architecture covered:** AD-2, AD-3, AD-4, AD-9, AD-10, AD-13, AD-14
**UX-DRs covered:** UX-DR1, UX-DR9, UX-DR10, UX-DR14, UX-DR15

### Epic 2: Daily Brief & AI Signal Pipeline

매일 아침 사용자 프로필에 맞는 AI 기술 Signal이 큐레이션되어 홈 화면에 표시된다. 배치 파이프라인이 06:00에 실행되어 09:00 FCM Push 후 홈 화면에 SignalCard가 표시되는 상태까지 완성된다.

**FRs covered:** FR-1.1, FR-1.2, FR-1.3, FR-1.4, FR-7.1
**Architecture covered:** AD-5(부분), AD-6, AD-12, AD-15, AD-16
**UX-DRs covered:** UX-DR3, UX-DR17(Home Daily Brief 6상태)

### Epic 3: Research Review & Decision

사용자가 Signal을 선택하면 AI가 13섹션 Research Review를 생성하고, 사용자는 이를 읽은 후 Learn Now / Queue / Ignore 중 하나를 결정할 수 있다. ContextStickyBar 섹션 engagement 활성화를 포함한 전체 Decision 플로우가 완성된다.

**FRs covered:** FR-2.1, FR-2.2, FR-2.3, FR-3.1, FR-3.2, FR-3.3
**NFRs covered:** NFR-3
**Architecture covered:** AD-5(on-demand Review 비동기 트리거), AD-8
**UX-DRs covered:** UX-DR2, UX-DR8, UX-DR11, UX-DR17(Research Review 4상태, Queue 서브선택)

### Epic 4: Learning Path & Outcome

"Learn Now"를 선택한 사용자가 AI가 생성한 Learning Path를 따라 학습하고, 결과를 Outcome으로 기록하면 Memory에 저장되어 Decision Loop가 완결된다.

**FRs covered:** FR-4.1, FR-4.2, FR-5.1, FR-5.2, FR-5.3, FR-6.1, FR-6.2
**Architecture covered:** AD-5(Learning Path 비동기), AD-7, AD-11
**UX-DRs covered:** UX-DR5, UX-DR6, UX-DR17(Learning Path 4상태, Outcome 상태)

### Epic 5: Queue, History & Personalization

사용자가 예약된 학습 항목을 Queue에서 관리하고, Memory Timeline에서 과거 결정 이력을 조회하며, Memory 기반 개인화 추천과 Push 알림까지 완성된 MVP 경험을 누린다.

**FRs covered:** FR-3.4, FR-6.3, FR-7.2, FR-7.3
**Architecture covered:** AD-17(FCM Push 3종 트리거 전체)
**UX-DRs covered:** UX-DR4, UX-DR7, UX-DR12, UX-DR13, UX-DR16, UX-DR17(Queue/History/Profile 상태), UX-DR18

### Epic 6: 실데이터 수집 & 시그널 품질 v2

StubCollector를 실제 소스(RSS/HN/GitHub)로 대체하고, 의미 기반 클러스터링·관련성 필터로 시그널 품질을 높이며, Recommender를 임베딩 기반으로 고도화하고, 추천 품질을 측정 가능하게 한다. 이 에픽 완료 후 Daily Brief가 실제 최신 AI 기술 소식을 **토픽 단위**로 큐레이션하고, RAG 개인화 효과를 데이터로 검증할 수 있다.

**FRs covered:** FR-8.1, FR-8.2, FR-8.3, FR-8.4, FR-8.5 (신규 — 2026-07-29 스파이크 기반, 원 PRD 이후 추가)
**NFRs covered:** NFR-2(비용 통제), NFR-3(배치 회복탄력성)
**Architecture covered:** AD-2/AD-6(pgvector 전용, 외부 벡터DB 불허), AD-5(배치 사용자/소스 단위 격리), AD-16(Collector 어댑터 패턴)

---

## Epic 1: Platform Foundation & User Identity

사용자가 계정을 만들고, 역할·관심 기술을 설정하여 개인화된 학습 경험을 시작할 수 있다. 이 에픽 완료 후 사용자는 회원가입·로그인하고, 7단계 온보딩을 완료하면 첫 Daily Brief 생성이 시작되는 상태까지 도달한다.

### Story 1.1: Project Scaffolding & Database Foundation

개발자로서,
전체 플랫폼의 기반 인프라가 설정되어 있기를 원한다,
그래서 이후 모든 기능 스토리가 일관된 아키텍처 위에서 구현될 수 있다.

**Acceptance Criteria:**

**Given** 빈 레포지토리가 있을 때
**When** 프로젝트 초기화를 완료하면
**Then** Next.js 앱, FastAPI 앱, Flutter 앱이 각각 별도 패키지로 존재하고 로컬에서 실행된다
**And** `GET /api/v1/health` → `{"data": {"status": "ok"}, "error": null}` 응답을 반환한다
**And** 모든 FastAPI 응답은 `{"data": ..., "error": null | {"code": str, "message": str}}` 봉투 형식을 따른다

**Given** Supabase 프로젝트가 연결되어 있을 때
**When** 마이그레이션을 실행하면
**Then** `users`, `projects`, `user_devices` 테이블이 생성된다
**And** `projects` 테이블에 `playbook_type` 컬럼이 존재하고 `ai_research` 값을 허용한다
**And** `users`, `projects`, `user_devices` 테이블에 RLS가 활성화되어 있다
**And** `projects` RLS 정책: `EXISTS (SELECT 1 FROM projects WHERE id = project_id AND user_id = auth.uid())`

**Given** Next.js 앱이 실행 중일 때
**When** CSS를 검사하면
**Then** DESIGN.md의 전체 색상 토큰이 CSS 커스텀 프로퍼티(`--surface-base`, `--accent-primary` 등)로 정의되어 있다
**And** 타이포그래피 스케일(screen-title 28-30px/700 ~ badge 10px/700/uppercase) 클래스가 정의되어 있다
**And** 여백 시스템(4px 기준, 20px 화면 패딩) 및 모서리 반경 토큰이 정의되어 있다

**Given** Flutter 앱이 실행 중일 때
**When** ThemeData를 검사하면
**Then** `ColorScheme`, `TextTheme`, `ShapeTheme` 전체가 DESIGN.md 값으로 override되어 있다
**And** `ThemeData(splashFactory: NoSplash.splashFactory)`로 잉크/리플 효과가 전면 비활성화되어 있다
**And** Riverpod 2.x `ProviderScope`가 앱 루트에 감싸져 있다

### Story 1.2: User Authentication

사용자로서,
이메일과 비밀번호로 계정을 만들고 로그인할 수 있기를 원한다,
그래서 내 학습 이력과 결정 기록이 내 계정에 안전하게 귀속된다.

**Acceptance Criteria:**

**Given** 신규 사용자가 회원가입 화면에 있을 때
**When** 이메일·비밀번호를 입력하고 가입 버튼을 누르면
**Then** Supabase Auth를 통해 계정이 생성되고 세션이 시작된다
**And** 온보딩 wizard 화면으로 이동한다
**And** Next.js와 Flutter 모두 동일한 Supabase Auth를 사용한다

**Given** 기존 사용자가 로그인 화면에 있을 때
**When** 등록된 이메일·비밀번호를 입력하면
**Then** 세션이 복원되고 홈 화면(또는 미완료 온보딩)으로 이동한다
**And** FastAPI 미들웨어가 `Authorization: Bearer {Supabase JWT}` 헤더를 검증한다

**Given** 사용자가 로그인한 상태일 때
**When** Flutter 앱 로그인·오픈 시
**Then** FCM 토큰이 `POST /api/v1/devices/register`로 FastAPI에 등록되고 `user_devices` 테이블에 저장된다
**And** FCM 토큰이 클라이언트 코드에 노출되지 않는다 (FastAPI 경유 전송)

**Given** 잘못된 이메일/비밀번호가 입력되었을 때
**When** 로그인을 시도하면
**Then** 에러 메시지가 화면에 표시되고 앱 크래시 없이 계속 사용 가능하다

### Story 1.3: Web Navigation Shell

웹 사용자로서,
4개 탭(홈/큐/히스토리/프로필)으로 구성된 하단 내비게이션으로 앱을 탐색할 수 있기를 원한다,
그래서 주요 기능 영역에 항상 빠르게 접근할 수 있다.

**Acceptance Criteria:**

**Given** 로그인한 사용자가 앱에 접근할 때
**When** 어떤 화면에서든 하단 내비게이션을 확인하면
**Then** 홈·큐·히스토리·프로필 4개 탭이 고정 표시된다
**And** 탭 바 상단에 `border-top: 1px solid var(--border-subtle)` 구분선이 있다
**And** 탭 배경은 `surface-base` (#FFFFFF)이다

**Given** `<html>` 루트 요소를 검사할 때
**When** 페이지가 로드되면
**Then** `lang="ko"` 속성이 설정되어 있다
**And** "Review", "Signal", "Memory", "Learn Now", "Queue", "Ignore", "Daily Brief", "Learning Path", "Outcome", "NEW", "Applied", "Completed", "Dropped" 텍스트는 `<span lang="en">` 처리된다

**Given** 각 탭에 placeholder 화면이 있을 때
**When** 탭을 선택하면
**Then** 해당 탭의 화면으로 이동하고 URL이 `/home`, `/queue`, `/history`, `/profile`로 변경된다
**And** 데스크탑(≥768px)에서는 콘텐츠가 중앙 정렬, 최대 480px 너비로 표시된다

### Story 1.4: Flutter Navigation Shell

Flutter 앱 사용자로서,
4개 탭으로 구성된 하단 내비게이션으로 앱을 탐색할 수 있기를 원한다,
그래서 탭별로 독립적인 내비게이션 스택이 유지되어 탭을 오가도 이전 위치가 보존된다.

**Acceptance Criteria:**

**Given** Flutter 앱이 실행 중일 때
**When** GoRouter 설정을 확인하면
**Then** `StatefulShellRoute.indexedStack`으로 4개 탭 브랜치(홈/큐/히스토리/프로필)가 설정되어 있다
**And** 각 탭은 독립적인 `GlobalKey<NavigatorState>`를 보유한다
**And** 탭 루트 경로: `/home`, `/queue`, `/history`, `/profile`

**Given** 사용자가 홈 탭의 특정 화면으로 내비게이션한 후 큐 탭으로 이동했을 때
**When** 다시 홈 탭을 탭하면
**Then** 홈 탭의 이전 화면 위치가 그대로 복원된다

**Given** Android 사용자가 홈/큐/히스토리/프로필 최상위 탭에 있을 때
**When** 시스템 back 버튼을 누르면
**Then** 앱이 종료된다 (back 인터셉션 없음)

**Given** 앱이 실행 중일 때
**When** 화면을 확인하면
**Then** `SafeArea`가 모든 화면 본문에 적용되어 있다
**And** `SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge)` 설정이 적용되어 있다
**And** `SystemChrome.setSystemUIOverlayStyle(SystemUiOverlayStyle.dark)`로 상태 바 아이콘이 다크 모드이다

### Story 1.5: Onboarding Wizard

신규 사용자로서,
7단계 온보딩 wizard를 완료하여 내 역할·경험·기술 스택·관심 영역을 등록할 수 있기를 원한다,
그래서 나에게 맞는 개인화된 Daily Brief를 받을 수 있다.

**Acceptance Criteria:**

**Given** 처음 로그인한 사용자일 때
**When** 앱을 시작하면
**Then** Welcome 화면("오늘 배워야 할 AI, 매일 브리핑해드립니다" / 28px/700)이 표시된다
**And** 온보딩 완료 여부는 로컬 스토리지로 판단하여 미완료 시 온보딩으로 라우팅된다

**Given** 온보딩 진행 중일 때
**When** 각 단계를 확인하면
**Then** Role(6+1 옵션), Experience(3옵션), Tech Stack(multi-select pill), Project/Goal(6+1옵션), Interests(multi-select), Daily Learning Time(15분/30분/1시간) 순서로 진행된다
**And** 단계별 기본 CTA("다음" / 마지막 단계는 "완료")는 1개 이상 선택 시 활성화된다
**And** 뒤로 가기(back chevron)로 이전 단계로 돌아갈 수 있다

**Given** 사용자가 마지막 단계("완료")를 탭했을 때
**When** API 호출이 성공하면
**Then** `POST /api/v1/onboarding/complete`가 호출되어 UserProfile이 저장된다
**And** FastAPI가 사용자를 위한 AI Research Project 1개를 자동 생성한다 (`playbook_type: "ai_research"`, name: "내 AI 학습")
**And** "오늘의 Daily Brief를 생성 중입니다." 전체화면 로딩 화면이 표시된다
**And** Flutter에서 해당 로딩 화면은 `PopScope(canPop: false)`로 back이 차단된다

**Given** Daily Brief 생성이 완료된 후(또는 타임아웃 후)
**When** 사용자가 알림 권한 요청 화면을 확인하면
**Then** "매일 AI CTO 브리핑을 받아보시겠어요?" 화면이 표시된다
**And** iOS: `UNUserNotificationCenter.requestAuthorization`, Android 13+: `POST_NOTIFICATIONS` permission_handler 사용
**And** "허용" / "나중에(ghost pill)" 두 CTA가 존재하며 둘 다 Home으로 이동한다
**And** 이 권한 요청은 앱 생명주기에서 단 1회만 표시된다

### Story 1.6: Profile Screen

사용자로서,
내 프로필(역할·경험·기술 스택·관심 영역·일일 학습 시간)을 조회하고 편집할 수 있기를 원한다,
그래서 변경된 상황에 맞게 Daily Brief 개인화 기준을 업데이트할 수 있다.

**Acceptance Criteria:**

**Given** 로그인한 사용자가 프로필 탭에 있을 때
**When** 프로필 화면을 확인하면
**Then** Role, Experience, Tech Stack, Project/Goal, Interests, Daily Learning Time 항목이 표시된다
**And** 우상단에 "편집" CTA가 있다
**And** 알림 설정 행이 존재한다

**Given** 사용자가 "편집"을 탭했을 때
**When** 편집 모드에서 항목을 수정하고 "저장"을 누르면
**Then** `PATCH /api/v1/users/profile`이 호출되어 프로필이 업데이트된다
**And** 낙관적 업데이트 후 토스트 "프로필이 업데이트됐습니다. 다음 Daily Brief에 반영됩니다."가 3초간 표시된다
**And** "취소"를 누르면 변경사항 없이 조회 모드로 돌아간다

**Given** 사용자가 온보딩에서 알림 권한을 거부했을 때
**When** 프로필 화면의 "알림 설정" 행을 탭하면
**Then** iOS/Android OS 설정 앱으로 이동한다 (인앱 재요청 없음)
**And** 화면에 "기기 설정에서 알림을 허용할 수 있습니다." 안내 문구가 표시된다

**Given** 사용자가 웹 또는 Flutter 앱에서 프로필을 편집할 때
**When** 동일한 계정으로 다른 플랫폼을 확인하면
**Then** 업데이트된 프로필 정보가 동기화되어 표시된다

---

## Epic 2: Daily Brief & AI Signal Pipeline

매일 아침 사용자 프로필에 맞는 AI 기술 Signal이 큐레이션되어 홈 화면에 표시된다. 배치 파이프라인이 06:00 KST에 실행되어 09:00 FCM Push 후 홈 화면에 SignalCard가 표시되는 상태까지 완성된다.

### Story 2.1: Signal Pipeline Foundation

백엔드 개발자로서,
외부 AI 콘텐츠를 수집하여 기술 단위 Signal로 정규화할 수 있기를 원한다,
그래서 Daily Brief 생성의 원재료가 매일 안정적으로 공급된다.

**Acceptance Criteria:**

**Given** 파이프라인 DB 스키마 마이그레이션을 실행하면
**Then** `signals`, `signal_sources`, `daily_briefs`, `daily_brief_signals` 테이블이 생성된다
**And** `signals.status`: `raw | processed | archived` 값을 허용한다
**And** `daily_briefs` RLS: `user_id = auth.uid()` 단순 정책이 적용된다

**Given** Collector 어댑터 인터페이스가 구현되어 있을 때
**When** `collect()`를 실행하면
**Then** `list[RawArticle]`을 반환한다
**And** 파이프라인 검증용 스텁 어댑터 1개가 구현되어 하드코딩된 `RawArticle` 목록을 반환한다 (실제 소스 연결은 MVP 이후 어댑터 파일 추가로 확장, 하위 파이프라인 수정 없음)

**Given** Normalizer/Deduplicator가 `list[RawArticle]`을 처리할 때
**When** 동일 기술에 대한 여러 출처 기사가 입력되면
**Then** 하나의 `Signal`(기술 단위)로 묶어 `signals` 테이블에 저장한다
**And** 중복 Signal은 생성하지 않는다 (같은 기술명+날짜 기준)
**And** 각 출처는 `signal_sources`에 개별 레코드로 저장된다

**Given** FastAPI 파이프라인 로그를 확인할 때
**Then** 모든 로그는 JSON 구조화 형식이고 `brief_date`, `pipeline_stage`, `user_count` 필드를 포함한다

### Story 2.2: Signal Builder & Reviewer Agent

백엔드 개발자로서,
정규화된 Signal에 대해 AI가 Research Review를 사전 생성할 수 있기를 원한다,
그래서 사용자가 SignalCard를 탭했을 때 Review가 즉시 또는 빠르게 제공된다.

**Acceptance Criteria:**

**Given** `signals` 테이블에 `processed` 상태의 Signal이 있을 때
**When** Reviewer Agent가 실행되면
**Then** 각 Signal에 대해 `reviews` 테이블에 레코드가 생성된다 (`status: pending`)
**And** BackgroundTask로 비동기 실행된다: `pending → processing → completed | failed`
**And** `completed` 또는 `failed` 상태 진입 후 추가 상태 변경은 금지된다

**Given** `LLMProvider` 인터페이스가 정의되어 있을 때
**When** MVP 구현체를 확인하면
**Then** OpenAI Responses API를 사용한다 (Chat Completions API 사용 불가)
**And** 인터페이스 메서드: `generate(context: ReviewContext) → LLMResponse`
**And** 에러는 `LLMProviderError`로 표준화된다

**Given** `ReviewContextBuilder`가 Signal을 처리할 때
**When** Research Review를 생성하면
**Then** `reviews.result` JSONB는 `{"schema_version": 1, "review_type": "research", "payload": {...}}` 봉투를 따른다
**And** payload에 13섹션 데이터가 포함된다: 한 줄 정의, 핵심 개념, 해결하는 문제, 왜 중요한가, 기존 기술 차이, 사용자 관련성, 학습 목표, 예상 학습 시간·난이도, 실무 적용 가능성, 위험 요소, 추천 이유, 참고 출처, HonestBox
**And** HonestBox payload에 `severity: "standard" | "high"` 플래그가 포함된다

**Given** Review 생성이 `failed` 상태일 때
**Then** 소스 Signal 데이터가 보존된다
**And** 자동 재시도는 없다 (사용자 재트리거 방식)
**And** FastAPI 로그에 `review_id`, `playbook_type` 필드가 포함된다

### Story 2.3: Recommender & Daily Brief Batch Pipeline

백엔드 개발자로서,
APScheduler 배치 파이프라인이 매일 06:00 KST에 자동 실행되어 사용자별 Daily Brief를 생성하고 09:00에 FCM Push를 전송하기를 원한다,
그래서 사용자가 매일 아침 개인화된 AI 기술 브리핑을 받을 수 있다.

**Acceptance Criteria:**

**Given** APScheduler가 FastAPI에 등록되어 있을 때
**When** 매일 06:00 KST가 되면
**Then** Collector → Normalizer → Signal Builder → Reviewer → Recommender → Daily Brief DB 저장 순서로 파이프라인이 실행된다
**And** 각 사용자의 프로필(Role, Tech Stack, Project/Goal, Interests)을 기반으로 Signal 관련성 점수가 계산된다
**And** `daily_brief_signals` 테이블에 `relevance_score`와 `position`이 저장된다

**Given** Daily Brief 생성이 완료되면
**When** 09:00 KST가 되면
**Then** FCM을 통해 "오늘의 AI CTO 브리핑이 준비됐습니다 — [Signal 제목]" Push가 전송된다
**And** `user_devices` 테이블의 FCM 토큰을 사용한다
**And** FastAPI가 FCM REST API의 단일 전송 지점이다 (클라이언트 직접 발송 불가)

**Given** Memory가 없는 신규 사용자일 때
**When** Recommender가 실행되면
**Then** Role·Tech Stack·Project/Goal·Interests 기반으로 기본 관련성 점수가 계산된다 (콜드 스타트)

**Given** 파이프라인 실행 중 특정 단계가 실패하면
**Then** 해당 사용자의 Brief 생성만 실패하고 다른 사용자는 영향받지 않는다
**And** `processing` 상태 타임아웃 임계값 초과 시 `failed`로 전이된다

### Story 2.4: Home Screen — Daily Brief Display

사용자로서,
홈 화면에서 오늘의 AI CTO 브리핑을 확인하고 SignalCard를 탭하여 상세 Review로 이동할 수 있기를 원한다,
그래서 매일 관련성 높은 AI 기술을 빠르게 파악할 수 있다.

**Acceptance Criteria:**

**Given** Daily Brief가 준비된 상태에서 홈 탭을 열면
**Then** "오늘의 AI CTO 브리핑" 섹션 헤딩(22px/700) + 날짜가 표시된다
**And** `relevance_score` 순서로 SignalCard 목록이 표시된다
**And** 미열람 Signal에는 NEW 배지(accent-primary bg, 10px/700/uppercase)가 표시된다
**And** SignalCard 구조: 제목(16px/600) + NEW 배지 + 관련성 태그(12px/text-secondary) + 출처 수·예상 읽기 시간(11px/text-tertiary)

**Given** SignalCard의 composite aria-label을 확인하면
**Then** `aria-label="[Signal 제목], NEW, 출처 [N]개, 읽기 약 [N]분"` 형태로 명시적으로 제공된다 (DOM 연결 방식 금지)

**Given** Daily Brief가 생성 중인 상태일 때
**Then** "오늘의 Daily Brief를 생성하는 중입니다." + 세 점 pulse 애니메이션이 표시된다
**And** `prefers-reduced-motion` 시 pulse 애니메이션이 정적으로 대체된다

**Given** Daily Brief 생성이 실패했을 때
**Then** "오늘의 Daily Brief를 생성하지 못했습니다." + "다시 시도하기" CTA가 표시된다

**Given** 오늘 새로운 Signal이 없을 때
**Then** "오늘은 새로운 Signal이 없습니다. 어제 Queue에 저장한 항목을 이어서 학습할 수 있습니다." + "큐 보기" CTA가 표시된다

**Given** 사용자가 오늘의 모든 Signal을 열람했을 때
**Then** SignalCard 목록 하단에 "오늘 브리핑을 모두 확인했습니다." 캡션이 표시된다

### Story 2.5: On-demand Daily Brief Trigger

사용자로서,
신규 가입·프로필 변경·Brief 실패 시 Daily Brief를 즉시 요청할 수 있기를 원한다,
그래서 배치 주기를 기다리지 않고도 최신 Daily Brief를 받을 수 있다.

**Acceptance Criteria:**

**Given** 온보딩이 완료되어 첫 Daily Brief가 필요할 때
**When** `POST /api/v1/daily-briefs/trigger`가 호출되면
**Then** 202 Accepted가 즉시 반환된다
**And** BackgroundTask로 Recommender 이후 단계만 실행된다 (Signal은 이미 생성된 것 사용)
**And** Supabase Realtime 구독 또는 폴링으로 완료를 감지한다

**Given** 사용자가 프로필을 수정했을 때
**When** `PATCH /api/v1/users/profile` 완료 후
**Then** On-demand Brief 트리거가 자동으로 실행되어 새 프로필 기반 Brief가 생성된다

**Given** Daily Brief 생성이 완료되면
**When** 홈 화면을 Realtime으로 구독 중일 때
**Then** 신규 Brief가 자동으로 화면에 반영된다 (수동 새로고침 불필요)

---

## Epic 3: Research Review & Decision

사용자가 Signal을 선택하면 AI가 13섹션 Research Review를 생성하고, 사용자는 이를 읽은 후 Learn Now / Queue / Ignore 중 하나를 결정할 수 있다. ContextStickyBar 섹션 engagement 활성화를 포함한 전체 Decision 플로우가 완성된다.

### Story 3.1: Research Review 상세 화면

사용자로서,
SignalCard를 탭하면 해당 기술의 13섹션 Research Review를 읽을 수 있기를 원한다,
그래서 배울지 말지 결정하기에 충분한 맥락을 얻을 수 있다.

**Acceptance Criteria:**

**Given** 사용자가 홈 화면에서 SignalCard를 탭했을 때
**When** Research Review 상세 화면이 로드되면
**Then** Signal 제목이 `h1`으로 표시된다
**And** 13개 섹션이 순서대로 표시된다: (1)한 줄 정의 (2)핵심 개념 (3)해결하는 문제 (4)왜 중요한가 (5)기존 기술 차이 (6)사용자 관련성 (7)학습 목표 (8)예상 학습 시간·난이도 (9)실무 적용 가능성 (10)위험 요소 (11)추천 이유 (12)참고 출처 (13)HonestBox
**And** 각 섹션 헤딩은 `h2`이고 `data-section-key` 속성을 가진다

**Given** Section 6(사용자 관련성)이 표시될 때
**Then** "현재 프로필 기준" 레이블(11px/text-secondary)이 생성 텍스트 위에 표시된다
**And** 해당 사용자의 Role·Tech Stack·Project/Goal을 기반으로 개인화된 내용이 표시된다 (일반적 내용 금지)

**Given** HonestBox(섹션 13)를 확인하면
**Then** 배경 `surface-honest-box` (#F5F5F5), 12px radius로 표시된다
**And** 제목은 "AI가 확인하지 못한 정보" (11px/uppercase/700/text-secondary)이다
**And** severity가 `high`인 항목은 `status-warning` (#B45309) 3px 좌측 border가 적용된다
**And** severity가 `standard`인 항목은 border 없이 표시된다
**And** Review에 불확실성이 있으면 HonestBox는 반드시 표시된다 (생략 금지)

**Given** section 13(HonestBox) 아래를 확인하면
**Then** "AI에게 질문하기" 텍스트 링크(13px/text-secondary/underline)가 표시된다
**And** ContextStickyBar는 DOM에서 section 13 이후에 위치한다 (시각적으로는 fixed bottom)

### Story 3.2: On-demand Research Review 생성

사용자로서,
SignalCard를 탭했을 때 Review가 준비되지 않은 경우 생성을 기다리며 완료되면 자동으로 확인할 수 있기를 원한다,
그래서 파이프라인 사전 생성에 실패해도 Review를 볼 수 있다.

**Acceptance Criteria:**

**Given** 사용자가 SignalCard를 탭했을 때 해당 Review의 status가 `pending` 또는 `processing`이면
**Then** 전체화면 로딩 상태가 표시된다: "Research Review를 생성하는 중입니다. 앱을 닫아도 됩니다."
**And** "홈으로 돌아가기" CTA가 표시된다
**And** Supabase Realtime으로 해당 `review_id` 완료를 구독한다

**Given** Review가 없거나 `failed` 상태일 때
**When** 사용자가 SignalCard를 탭하면
**Then** `POST /api/v1/reviews/trigger` → 202 Accepted가 즉시 반환된다
**And** FastAPI BackgroundTask로 ReviewContextBuilder 실행 → LLMProvider 호출 → DB 저장 순으로 처리된다
**And** 상태 머신: `pending → processing → completed | failed`

**Given** Review 생성이 `completed`로 전환되면
**When** Realtime 알림이 프론트에 도달하면
**Then** 로딩 화면이 사라지고 13섹션 Research Review가 자동으로 표시된다 (수동 새로고침 불필요)

**Given** Review 생성이 `failed`로 전환되면
**Then** 에러 메시지와 "다시 시도하기" CTA가 표시된다
**And** 소스 Signal 데이터는 보존된다

### Story 3.3: ContextStickyBar & Decision

사용자로서,
Research Review의 핵심 섹션을 읽은 후 ContextStickyBar가 활성화되어 Learn Now / Queue / Ignore 중 하나를 결정할 수 있기를 원한다,
그래서 충분한 근거를 바탕으로 학습 결정을 내릴 수 있다.

**Acceptance Criteria:**

**Given** Research Review 상세 화면이 처음 로드될 때
**Then** ContextStickyBar는 disabled 상태로 표시된다
**And** Primary CTA 배경: `text-disabled` (#D1D1D1), 잠금 아이콘(SVG 14px) 표시
**And** 힌트 텍스트(`id="ctx-hint"`): "추천 근거를 먼저 확인해 주세요 ↑" (11px/text-secondary)
**And** 추천 텍스트는 withheld(표시 안 함), Queue/Ignore 버튼은 hidden

**Given** 사용자가 섹션 1–6, 10, 11을 스크롤(또는 포커스)할 때
**When** 각 섹션 heading이 viewport에 진입하거나 키보드/스크린리더 포커스를 받으면
**Then** 해당 섹션이 "seen"으로 기록된다 (IntersectionObserver threshold: 0.1)
**And** 필수 섹션 세트 완료 시 ContextStickyBar가 enabled 상태로 전환된다
**And** `aria-live="polite"` 영역이 "Learn Now 버튼을 사용할 수 있습니다"를 발화한다
**And** `prefers-reduced-motion` 시 전환 애니메이션 없이 즉시 전환된다

**Given** ContextStickyBar가 enabled 상태일 때
**Then** Primary CTA: "Learn Now" (accent-primary bg, accent-foreground text)
**And** Secondary ghost pills: "Queue", "Ignore" (각 min-height 44px)
**And** 추천 텍스트가 CTA 위에 공개된다 (예: "지금 배울 것을 권장합니다")

**Given** 사용자가 "Learn Now"를 탭하면
**Then** Decision(`choice: "learn_now"`)이 `POST /api/v1/decisions`로 저장된다
**And** Learning Path 화면으로 이동한다 (Epic 4에서 구현)

**Given** 사용자가 "Queue"를 탭하면
**Then** Queue 타이밍 선택 Bottom Sheet가 열린다: Today / This Week / Later
**And** 한 개를 선택하면 시트가 닫히고 Decision(`choice: "queue"`, `queue_timing`)이 저장된다
**And** 비차단 토스트 "이번 주 학습 예정으로 저장됐습니다."가 표시된다
**And** Bottom Sheet: `showModalBottomSheet`, `RoundedRectangleBorder(top: 24px)`, 수동 drag handle(36×4px/#DDD)

**Given** 사용자가 Queue 타이밍 선택 Bottom Sheet에서 메모를 남기고 싶을 때
**Then** Decision 저장 시 선택적 메모 입력 필드가 제공된다
**And** `decisions.memo` TEXT 컬럼에 함께 저장된다 (FR-3.3)

**Given** 사용자가 "Ignore"를 탭하면
**Then** Decision(`choice: "ignore"`)이 저장된다
**And** 비차단 토스트 "이 Signal은 히스토리에서 다시 볼 수 있습니다." (3초)가 표시된다
**And** 홈 화면으로 이동한다

**Given** ContextStickyBar의 ARIA를 확인하면
**Then** disabled CTA: `aria-disabled="true"`, `aria-label="Learn Now — 비활성화됨. 리뷰 내용을 먼저 읽어 주세요"`, `aria-describedby="ctx-hint"`
**And** Queue CTA: `aria-label="Queue — 이 Signal을 큐에 저장"`, Ignore CTA: `aria-label="Ignore — 이 Signal을 무시"`
**And** 모든 CTA는 `<button>` 요소이다

### Story 3.4: Contextual Chat

사용자로서,
Research Review 화면 내에서 AI에게 해당 기술에 관한 질문을 할 수 있기를 원한다,
그래서 Review만으로 해소되지 않은 궁금증을 바로 해결할 수 있다.

**Acceptance Criteria:**

**Given** Research Review 상세 화면의 "AI에게 질문하기" 링크를 탭하면
**Then** Contextual Chat 화면이 현재 탭 브랜치 스택에 push된다 (`/home/review/:signalId/chat`)
**And** 현재 Research Review의 Signal ID가 시스템 컨텍스트로 자동 전달된다
**And** 첫 AI 메시지: "이 Review에 대해 궁금한 점을 물어보세요."

**Given** Contextual Chat이 열려 있을 때
**Then** 홈/큐/히스토리/프로필 어디에도 Chat 진입점이 없다 (Floating FAB 금지)
**And** Chat 내에 Learn Now / Queue / Ignore CTA가 없다

**Given** back 제스처로 Chat을 닫으면
**Then** Research Review 상세 화면의 이전 스크롤 위치로 돌아간다

**Given** AI 응답이 실패하거나 타임아웃되면
**Then** "응답을 받지 못했습니다. 잠시 후 다시 시도해 주세요." 인라인 에러 + 재시도 CTA가 표시된다

**Given** 사용자가 앱을 닫고 다시 Chat에 진입하면
**Then** 이전 대화가 복원되지 않고 새 세션으로 시작된다 (v1 세션 비영속)

---

## Epic 4: Learning Path & Outcome

"Learn Now"를 선택한 사용자가 AI가 생성한 Learning Path를 따라 학습하고, 결과를 Outcome으로 기록하면 Memory에 저장되어 Decision Loop가 완결된다.

### Story 4.1: Learning Path 생성 & 화면

사용자로서,
"Learn Now" 결정 후 내 프로필에 맞는 Learning Path를 받아 5가지 리소스를 순서대로 학습할 수 있기를 원한다,
그래서 어디서 시작해야 할지 고민 없이 바로 학습을 시작할 수 있다.

**Acceptance Criteria:**

**Given** 사용자가 "Learn Now"를 탭하면
**When** `POST /api/v1/learning-paths/trigger`가 호출되면
**Then** 202 Accepted가 즉시 반환된다
**And** BackgroundTask로 비동기 생성된다: `pending → processing → completed | failed`
**And** `learning_paths` 테이블에 `decision_id`, `signal_id`, `resources`(JSONB), `status` 컬럼이 존재한다

**Given** Learning Path가 생성 중일 때
**Then** "학습 경로를 생성하는 중입니다." + 세 점 pulse 애니메이션이 표시된다
**And** `prefers-reduced-motion` 시 정적으로 대체된다
**And** Supabase Realtime으로 완료를 구독한다

**Given** Learning Path가 `completed`로 전환되면
**Then** 5가지 리소스가 고정 순서로 표시된다: (1)공식 문서 (2)핵심 자료 (3)GitHub (4)실습 예제 (5)적용 아이디어
**And** 각 LearningPathCard: resource type label(10px/uppercase/700/text-secondary) + 제목(15px/600) + descriptor(13px/text-secondary) + chevron-external 아이콘
**And** "적용 아이디어"는 사용자의 현재 Project/Goal 기반으로 개인화된 내용이다

**Given** 사용자가 외부 링크를 탭하고 앱으로 돌아오면
**Then** Learning Path 화면 하단에 비차단 프롬프트가 표시된다: "학습을 완료했나요? 결과를 기록해 주세요." + "결과 기록하기" CTA
**And** 이 프롬프트는 외부 링크를 1회 이상 방문한 후에만 표시된다

**Given** Learning Path 생성이 `failed`이면
**Then** "학습 경로를 생성하지 못했습니다." + "다시 시도하기" + "홈으로 돌아가기" CTA가 표시된다

### Story 4.2: Outcome 기록

사용자로서,
학습 결과(Completed / Applied / Dropped / Not Useful)를 기록하고 선택적 피드백을 남길 수 있기를 원한다,
그래서 내 학습 이력이 누적되어 다음 추천의 질이 높아진다.

**Acceptance Criteria:**

**Given** 사용자가 Outcome 입력 화면에 진입하면
**Then** 화면 헤딩 "학습 결과를 기록해 주세요" (28px/700)가 표시된다
**And** 어느 Signal에 대한 Outcome인지 Signal 제목 참조(13px/text-secondary)가 표시된다
**And** 4개 OutcomeCard가 라디오 그룹으로 표시된다: Completed("학습을 완료했습니다") / Applied("실제 프로젝트에 적용했습니다") / Dropped("학습을 중단했습니다") / Not Useful("현재 상황에 맞지 않았습니다")

**Given** OutcomeCard의 선택 상태를 확인하면
**Then** 선택된 카드: `accent-primary` 1.5px border (배경 fill 변경 없음)
**And** 미선택 카드: `border-card` (#DCDCDC) 1px border
**And** 라디오 그룹 ARIA: `role="radiogroup"`, `aria-label="학습 결과를 선택해 주세요"`, 각 카드 `aria-checked="true/false"`, `aria-label="Completed — 학습을 완료했습니다"` 형태

**Given** 사용자가 "Applied"를 선택하면
**Then** 선택 카드 아래에 추가 입력 필드가 나타난다: "어떤 프로젝트에 적용했나요? (선택)" 단일 라인 텍스트

**Given** 선택적 피드백 필드를 확인하면
**Then** 유용했는가 토글(예/아니오), 실제 학습 시간 입력(숫자+분), 메모 멀티라인 입력이 항상 표시된다 (필수 아님)

**Given** 사용자가 OutcomeCard 하나를 선택하고 "기록하기" CTA를 탭하면
**Then** `POST /api/v1/outcomes`로 Outcome이 저장된다
**And** `outcomes.status`: `completed | applied | dropped | not_useful`
**And** 비차단 토스트 "결과가 기록됐습니다. 다음 Daily Brief에 반영됩니다." (3초)가 표시된다
**And** 홈 화면으로 이동한다

### Story 4.3: Memory Manager

백엔드 개발자로서,
Outcome이 기록되면 FastAPI가 AI를 통해 Memory를 추출·저장하기를 원한다,
그래서 축적된 Memory가 이후 Daily Brief 개인화와 Research Review 품질 향상에 활용된다.

**Acceptance Criteria:**

**Given** Outcome이 `POST /api/v1/outcomes`로 저장되면
**When** FastAPI BackgroundTask가 실행되면
**Then** Decision Loop 체인(Signal + Review + Decision + Outcome)을 기반으로 Memory가 추출된다
**And** `memories` 테이블에 저장된다: `user_id`, `memory_type`, `summary`, `embedding`(vector 1536)
**And** `memory_type`: `preference | skill | project | decision_history | outcome_history` 중 적절한 값

**Given** `memories` 테이블의 RLS를 확인하면
**Then** `user_id = auth.uid()` 단순 정책이 적용되어 있다
**And** 모든 INSERT는 FastAPI만 수행한다 (클라이언트 직접 쓰기 금지)

**Given** Memory가 저장될 때
**Then** `summary` 텍스트의 임베딩(1536차원 벡터)이 함께 저장된다
**And** 이 임베딩은 이후 Recommender의 RAG(pgvector) 조회에 활용된다

**Given** 테스트 환경에서 Memory Manager를 검증할 때
**Then** 실제 Supabase 테스트 DB에 연결하여 테스트한다 (프로덕션 DB 모킹 금지)
**And** LLMProvider는 인터페이스 모킹으로 대체 가능하다

---

## Epic 5: Queue, History & Personalization

사용자가 예약된 학습 항목을 Queue에서 관리하고, Memory Timeline에서 과거 결정 이력을 조회하며, Memory 기반 개인화 추천과 Push 알림까지 완성된 MVP 경험을 누린다.

### Story 5.1: Queue 탭

사용자로서,
Queue에 저장한 학습 항목을 Today / This Week / Later 그룹으로 확인하고 일정을 변경할 수 있기를 원한다,
그래서 배우기로 한 기술을 잊지 않고 원하는 시점에 학습할 수 있다.

**Acceptance Criteria:**

**Given** 큐 탭을 열면
**Then** Today / This Week / Later 그룹 헤딩(22px/700) 순서로 QueueItem이 표시된다
**And** 각 그룹에 항목이 없으면 해당 그룹 헤딩은 표시되지 않는다
**And** 모든 항목이 없으면 "큐에 저장된 학습 항목이 없습니다. Signal을 읽고 Queue를 선택하면 여기에 저장됩니다." 빈 상태가 표시된다

**Given** QueueItem을 확인하면
**Then** 타이밍 배지(TODAY/THIS WEEK/LATER, 10px/uppercase/700, surface-card-alt bg) + Signal 제목(15px/600) + 예상 시간(12px/text-secondary) + "일정 변경" 텍스트 링크 + chevron이 표시된다
**And** min-height: 44px
**And** Semantics composite label: `aria-label="Today 예약됨, [Signal 제목], 약 [N]분"`

**Given** 자정이 지난 Today 항목이 남아 있을 때
**Then** "미완료" 배지(status-warning 텍스트, 배경 fill 없음)가 표시된다

**Given** "일정 변경" 링크를 탭하면
**Then** Today / This Week / Later 선택 Bottom Sheet가 열린다
**And** 선택 즉시 낙관적 업데이트로 배지가 변경되고 비동기로 저장된다
**And** `PATCH /api/v1/decisions/:id`로 `queue_timing`이 업데이트된다

**Given** QueueItem을 탭하면
**Then** 해당 Signal의 Research Review 상세 화면으로 이동한다 (큐 탭 브랜치 스택 내 push)

### Story 5.2: History / Memory Timeline

사용자로서,
히스토리 탭에서 내 모든 결정 이력을 Signal→Review→Decision→Outcome 체인으로 시간순 조회할 수 있기를 원한다,
그래서 과거 학습 결정과 결과를 되돌아보고 다음 결정에 참고할 수 있다.

**Acceptance Criteria:**

**Given** 히스토리 탭을 열면
**Then** 결정 이력이 역시간순으로 표시되고 월 구분선(11px/text-secondary)으로 나뉜다
**And** 이력이 없으면 "아직 기록된 학습 결정이 없습니다. Signal을 읽고 Learn Now를 선택하면 이곳에 기록이 시작됩니다." 빈 상태가 표시된다

**Given** Memory Timeline을 확인하면
**Then** 좌측 2px spine(border-subtle)에 12px 도트가 연결된다
**And** Signal 도트: text-secondary fill
**And** Review/Decision 도트: text-primary fill
**And** Outcome 도트: color+glyph 병행 — Completed(status-positive+"✓") / Applied(status-positive+"→") / Dropped(text-primary+"✕") / Not Useful(text-secondary+"−")
**And** glyph는 `ExcludeSemantics`로 감싸고 도트 요소에 `Semantics(label: "Applied 결과 — [Signal 제목]")` 적용

**Given** Timeline 카드를 확인하면
**Then** surface-card bg, 12px radius, 12×14px padding
**And** type label(10px/uppercase/700/text-secondary) + 제목(14px/600) + 날짜(12px/text-secondary)
**And** 날짜는 text-tertiary가 아닌 text-secondary 사용 (기능 정보이므로 대비 부족 색상 금지)

**Given** Timeline 항목을 탭하면
**Then** 해당 Signal의 체인 상세(Signal→Review→Decision→Outcome 전체)로 이동한다
**And** Review가 아카이빙된 경우 "보관된 Review" 배너와 함께 전체 내용이 읽기 전용으로 표시된다

**Given** Learn Now 후 Outcome이 아직 없는 항목을 확인하면
**Then** Outcome 노드에 "미완료" 상태(text-secondary, "?" glyph 도트)가 표시된다

### Story 5.3: Push Notification System

사용자로서,
매일 09:00 Daily Brief 알림, 저녁 Queue Today 리마인더, Learn Now 3일 후 Outcome 입력 요청을 받을 수 있기를 원한다,
그래서 앱을 열지 않아도 학습 루프를 놓치지 않는다.

**Acceptance Criteria:**

**Given** Daily Brief 생성이 완료되고 09:00 KST가 되면
**Then** FCM Push가 전송된다: "오늘의 AI CTO 브리핑이 준비됐습니다 — [Signal 제목]"
**And** Push를 탭하면 앱이 홈 화면으로 열린다 (Research Review 직접 딥링크 금지)
**And** 홈 화면에서 해당 SignalCard가 상단에 강조 표시된다

**Given** 사용자가 Today Queue 항목을 남긴 채 20:00 KST가 되면
**Then** FCM Push가 전송된다: "오늘 학습하기로 한 [Signal 제목]이 남아있습니다"
**And** 해당 항목이 없으면 Push가 전송되지 않는다

**Given** Learn Now 결정 후 3일이 지나도 Outcome이 기록되지 않으면
**Then** FCM Push가 전송된다: "학습 결과를 기록해 주세요 — [Signal 제목]"
**And** 이후 해당 항목에 대한 추가 Push는 없다 (1회 follow-up 후 중단)

**Given** 앱이 foreground 상태에서 Push가 수신되면
**Then** OS 알림이 표시되지 않는다
**And** 홈 탭에 있을 경우 해당 SignalCard에만 brief highlight가 표시된다

**Given** 앱이 terminated(완전 종료) 상태에서 Push를 탭하면
**Then** `FirebaseMessaging.instance.getInitialMessage()`로 payload를 감지하고 `/home`으로 라우팅된다

### Story 5.4: Memory 기반 개인화 & 접근성 마감

개발자로서,
Memory RAG가 Recommender에 연동되고 WCAG 2.2 AA 접근성 요건과 금지 인터랙션 패턴이 앱 전체에 적용되어 있기를 원한다,
그래서 MVP가 프로덕션 수준의 완성된 경험으로 출시될 수 있다.

**Acceptance Criteria:**

**Given** Recommender가 실행될 때 Memory가 존재하는 사용자이면
**Then** `memories` 테이블의 임베딩을 pgvector HNSW 인덱스로 조회하여 Signal 관련성 점수에 반영한다
**And** 외부 벡터 DB를 사용하지 않는다 (Supabase pgvector 전용)
**And** Memory가 없는 사용자는 콜드 스타트 로직(프로필 기반)으로 폴백된다

**Given** 앱의 모든 인터랙티브 요소를 확인하면
**Then** 최소 44×44pt 탭 타겟을 충족한다
**And** 상태 정보가 색상만으로 전달되는 요소가 없다 (glyph 또는 텍스트 레이블 병행)
**And** 모든 fixed height 컨테이너가 text-bearing 요소에 사용되지 않는다 (intrinsic + padding 방식)

**Given** `prefers-reduced-motion`이 활성화된 환경에서
**Then** 모든 로딩 dot-pulse 애니메이션이 정적으로 대체된다
**And** Bottom Sheet open/close가 즉시 appear/disappear로 대체된다
**And** ContextStickyBar 활성화 전환이 즉시 전환으로 대체된다

**Given** 앱 전체를 검토하면
**Then** Floating AI Chat FAB가 어디에도 없다
**And** 카루셀 또는 수평 스크롤 콘텐츠가 없다
**And** 시스템이 Learn Now / Queue / Ignore를 자동 선택하는 경로가 없다
**And** 진행률 표시줄, 스트릭, 달성 배지가 없다
**And** 2중 모달 스택이 없다 (Bottom Sheet는 한 번에 1개)
**And** 화면당 `btn-primary`(accent-primary 배경)가 1개를 초과하지 않는다

---

## Epic 6: 실데이터 수집 & 시그널 품질 v2

StubCollector를 실제 외부 소스로 대체하고, 의미 클러스터링·관련성 필터로 시그널 품질을 높이며, Recommender를 임베딩 기반으로 고도화하고, 추천 품질을 측정 가능하게 한다.

**신규 FR (2026-07-29 실 RSS/HN 스파이크 `planning-artifacts/research/spike-rss-2026-07-29.py` 기반, 원 PRD 이후 추가):**
- **FR-8.1:** 시스템은 실제 외부 소스(RSS/Atom, HackerNews, GitHub Releases)에서 AI 기술 기사를 수집한다.
- **FR-8.2:** 시스템은 수집 기사를 의미 유사도로 클러스터링하여 동일 주제를 1개 Signal(다중 출처)로 묶는다.
- **FR-8.3:** 시스템은 도메인 무관/유해/저품질 기사를 시그널 생성 이전에 필터링한다.
- **FR-8.4:** Recommender는 프로필/관심사 임베딩과 최신성·다양성·인기 피처로 시그널을 랭킹한다.
- **FR-8.5:** 시스템은 노출·열람·결정 engagement를 로깅하고 추천 품질(RAG vs 콜드스타트)을 오프라인 평가한다.

> **스파이크 근거 요약:** 실 RSS 4/5 피드 + HN 10건 = 30건 수집 성공. 그러나 키워드 `technology_name` 그룹핑이 **50%(15/30)를 "General AI" 뭉텅이**로 분류 → normalize가 무관 기사 15개를 1개 무의미 시그널로 뭉갬(LLM 요약 = "지리정보+긴컨텍스트+시뮬+검색AI..." 뒤죽박죽). 동일 기사 다중소스(Claude 암호취약점 블로그+HN), 완전중복(Agent Intrusion ×2), 노이즈/유해물, 피드 헬스(LangChain 0건) 문제 확인.

### Story 6.1: 실 수집기 어댑터 & 소스 레지스트리

개발자로서,
StubCollector를 실제 외부 소스 수집기로 대체하고 싶다,
그래서 Daily Brief가 하드코딩 샘플이 아니라 실제 최신 AI 기술 소식을 재료로 삼는다.

**Acceptance Criteria:**

**Given** 소스 레지스트리에 활성 소스(RSS/HN/GitHub) 목록이 설정되어 있을 때
**When** 수집기가 실행되면
**Then** 각 소스에서 `RawArticle(technology_name, title, url, source_type, content)` 목록을 반환한다
**And** 각 소스 어댑터는 `BaseCollector`를 상속한다 (AD-16)
**And** 외부 HTTP 요청은 certifi CA로 검증하고 타임아웃을 적용한다 (스파이크에서 확인된 SSL/타임아웃 이슈)

**Given** 일부 소스가 실패(404/타임아웃/파싱오류)할 때
**When** 수집이 진행되면
**Then** 실패한 소스는 격리되어 로깅되고 나머지 소스 수집은 계속된다 (AD-5)
**And** 소스별 성공/실패/건수가 `pipeline_log`에 기록된다 (피드 헬스 관측)

**Given** 동일 URL 또는 정규화된 동일 제목의 기사가 여러 소스에서 수집될 때
**When** 수집 결과를 반환하면
**Then** exact 중복은 제거된다 (스파이크: Agent Intrusion ×2 중복 확인)

### Story 6.2: 의미 클러스터링 & 관련성/세이프티 필터

개발자로서,
수집 기사를 의미 기반으로 클러스터링하고 노이즈를 걸러내고 싶다,
그래서 시그널이 토픽 단위로 일관되며 무관/유해 콘텐츠가 배제된다.

**Acceptance Criteria:**

**Given** 수집된 기사 목록이 있을 때
**When** 클러스터링을 수행하면
**Then** 각 기사를 임베딩(`text-embedding-3-small`)하여 pgvector 코사인 유사도로 클러스터링한다
**And** 임계치 이상 유사한 기사들은 1개 클러스터(=1 Signal 후보, 다중 출처)로 묶인다 (스파이크: Claude 암호취약점 블로그+HN → 1시그널이어야 함)
**And** 외부 벡터 DB를 사용하지 않는다 (AD-2/AD-6, Supabase pgvector 전용)

**Given** 시그널 생성 이전 단계에서
**When** 관련성/세이프티 필터를 적용하면
**Then** AI/개발 기술 도메인과 무관하거나 유해한 기사는 제외된다 (스파이크: "smart rings", 유해 콘텐츠 유입 확인)
**And** 필터 판정 근거가 로깅된다

**Given** LLM 시그널 생성 비용을 통제해야 할 때
**When** 파이프라인 순서를 보면
**Then** 클러스터링·필터가 SignalBuilder(LLM) **이전**에 실행되어, LLM 호출 수가 원문 수가 아니라 클러스터(토픽) 수에 비례한다 (NFR-2)

### Story 6.3: normalize v2 & Signal 스키마 확장

개발자로서,
클러스터를 다중 출처 Signal로 저장하고 랭킹 메타데이터를 기록하고 싶다,
그래서 Recommender가 최신성·인기·출처 권위를 활용할 수 있다.

**Acceptance Criteria:**

**Given** 마이그레이션을 실행하면
**Then** `signals`에 `published_at TIMESTAMPTZ`, 소스 권위, 인기(예: HN points 집계) 컬럼이 추가된다
**And** 시그널 식별을 클러스터 기반으로 전환/보완한다 (스파이크에서 발견된 `(technology_name, signal_date)` UNIQUE 제약 부재/취약성 반영)

**Given** 클러스터 목록이 있을 때
**When** normalize v2가 실행되면
**Then** 클러스터당 1개 `signals` row + N개 `signal_sources` row를 저장한다
**And** `published_at`은 클러스터 내 최신 기사 기준, 인기는 소스 신호 집계로 기록된다

### Story 6.4: Recommender v2

개발자로서,
콜드스타트를 임베딩 기반으로 바꾸고 랭킹 피처를 추가하고 싶다,
그래서 substring 오매칭 없이 개인화 정확도가 오르고 브리핑이 다양·최신해진다.

**Acceptance Criteria:**

**Given** Memory가 없는 사용자(콜드스타트)일 때
**When** 관련성을 산출하면
**Then** 프로필 tech_stack/interests를 임베딩한 벡터와 Signal 임베딩의 코사인 유사도로 점수를 낸다 (substring 매칭 제거 — "go"→"google" 오매칭 해소, 리뷰 파인딩)
**And** `relevance_score` 불변식(0.1~1.0, 결정론적 정렬)을 유지한다

**Given** 시그널 랭킹 시
**When** 최종 점수를 산출하면
**Then** 최신성 감쇠·다양성(MMR 등 같은 기술 도배 방지)·인기 피처가 반영된다
**And** Memory RAG의 query/문서 임베딩 텍스트 비대칭(리뷰 파인딩: signal=tech+title+summary vs memory=summary)이 해소되고 RAG weight가 재검토된다

**Given** Memory 보유 사용자일 때
**When** 추천을 수행하면
**Then** 기존 `match_memories` RAG 블렌딩 경로를 유지하되 v2 피처와 결합한다 (AD-2/6)

### Story 6.5: 측정 하네스 & Engagement 로깅

개발자로서,
추천 품질을 측정할 데이터와 평가 절차를 갖고 싶다,
그래서 "고도화"가 실제로 효과 있는지 데이터로 판단할 수 있다.

**Acceptance Criteria:**

**Given** 사용자가 Daily Brief를 소비할 때
**When** impression/open/read-through/decision 이벤트가 발생하면
**Then** 이벤트가 타임스탬프·signal_id·user_id와 함께 로깅된다 (신규 테이블 또는 기존 확장)
**And** 로깅은 사용자 경험을 차단하지 않는다 (비동기/best-effort)

**Given** 로깅된 engagement 데이터가 있을 때
**When** 오프라인 평가를 수행하면
**Then** RAG 재랭킹이 콜드스타트 대비 held-out engagement 지표(예: Learn Now율, read-through)에서 개선되는지 비교 리포트를 산출한다
**And** 지표 정의(CTR·read-through·Learn Now율·Outcome 유용도)가 문서화된다
