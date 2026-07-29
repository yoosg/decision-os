---
baseline_commit: NO_VCS
---

# Story 3.1: Research Review 상세 화면

Status: done

## Story

사용자로서,
SignalCard를 탭하면 해당 기술의 13섹션 Research Review를 읽을 수 있기를 원한다,
그래서 배울지 말지 결정하기에 충분한 맥락을 얻을 수 있다.

## Acceptance Criteria

**AC-1: 화면 진입 및 제목**
- **Given** 사용자가 홈 화면에서 SignalCard를 탭했을 때
- **When** Research Review 상세 화면이 로드되면
- **Then** Signal 제목이 `h1`으로 표시된다

**AC-2: 13섹션 구조**
- **Then** 13개 섹션이 순서대로 표시된다: (1)한 줄 정의 (2)핵심 개념 설명 (3)해결하는 문제 (4)왜 중요한가 (5)기존 기술 차이 (6)사용자 관련성 (7)학습 목표 (8)예상 학습 시간·난이도 (9)실무 적용 가능성 (10)위험 요소 (11)추천 이유 (12)참고 출처 (13)HonestBox
- **And** 각 섹션 헤딩은 `h2`이고 `data-section-key` 속성을 가진다 (Flutter: Semantics semanticsLabel 또는 key 사용)

**AC-3: Section 6 개인화 레이블**
- **Given** Section 6(사용자 관련성)이 표시될 때
- **Then** "현재 프로필 기준" 레이블 (11px/text-secondary)이 `user_relevance` 내용 위에 표시된다

**AC-4: HonestBox 스타일링**
- **Given** HonestBox(섹션 13)를 확인하면
- **Then** 배경 `surface-honest-box` (#F5F5F5), 12px radius로 표시된다
- **And** 제목은 "AI가 확인하지 못한 정보" (11px/uppercase/700/text-secondary)이다
- **And** severity가 `high`인 항목은 `status-warning` (#B45309) 3px 좌측 border가 적용된다
- **And** severity가 `standard`인 항목은 border 없이 표시된다
- **And** `honest_box.content`가 비어 있지 않은 경우 반드시 표시된다 (생략 금지)

**AC-5: "AI에게 질문하기" 링크 및 ContextStickyBar DOM 위치**
- **Given** section 13(HonestBox) 아래를 확인하면
- **Then** "AI에게 질문하기" 텍스트 링크 (13px/text-secondary/underline)가 표시된다
- **And** ContextStickyBar는 DOM에서 section 13 이후에 위치한다 (시각적으로는 fixed bottom)

## Tasks / Subtasks

### [WEB] Next.js Research Review 상세 화면 구현

- [x] Task 1: `web/src/app/(app)/home/review/[signalId]/page.tsx` 전면 교체 — Server Component로 Review 데이터 페치 (AC: #1, #2)
  - [x] 1.1 `createServerSupabaseClient()` 사용해 `reviews` 테이블 조회: `signal_id = signalId AND status = 'completed' AND playbook_type = 'ai_research'`, `select('result, bar_gate_override, signals(title)')`
  - [x] 1.2 Review 없음(null) 또는 status≠completed 시: "리뷰를 준비하는 중입니다." 안내 + "홈으로 돌아가기" 링크 (Story 3.2에서 교체 예정임을 주석으로 명시)
  - [x] 1.3 Review 있음: `<ResearchReviewContent>` 클라이언트 컴포넌트에 `review`, `signalTitle` props 전달

- [x] Task 2: `web/src/components/home/review/research-review-content.tsx` 신규 생성 — 13섹션 렌더링 (AC: #1, #2, #3)
  - [x] 2.1 `"use client"` 선언 (Story 3.3의 IntersectionObserver 및 ContextStickyBar 상태를 위해 필수)
  - [x] 2.2 h1으로 `signalTitle` 렌더링
  - [x] 2.3 SECTION_CONFIG 배열 순서대로 13개 섹션 렌더링:
    - 각 섹션: `<h2 data-section-key={sectionKey}>` + 내용
    - Section 6 (`user_relevance`): h2 아래 "현재 프로필 기준" 레이블 추가 (11px/text-secondary)
    - Section 8 (`learning_time_difficulty`): `estimated_hours`시간 + `difficulty` (beginner→입문, intermediate→중급, advanced→고급)
    - Section 12 (`reference_sources`): URL 목록을 tappable 링크로
  - [x] 2.4 `<HonestBox>` 컴포넌트 렌더링 (content 비어있지 않을 때만)
  - [x] 2.5 "AI에게 질문하기" 텍스트 링크 (`/home/review/${signalId}/chat`) 렌더링
  - [x] 2.6 `<ContextStickyBar>` 컴포넌트 렌더링 (DOM 최하단, 시각적 fixed bottom)

- [x] Task 3: `web/src/components/home/review/honest-box.tsx` 신규 생성 (AC: #4)
  - [x] 3.1 Props: `content: string, severity: 'standard' | 'high'`
  - [x] 3.2 컨테이너: `background: var(--surface-honest-box)`, `border-radius: 12px`, `padding: 16px`
  - [x] 3.3 severity='high': `border-left: 3px solid var(--status-warning)`
  - [x] 3.4 제목: "AI가 확인하지 못한 정보" — 11px, uppercase, font-weight 700, color `var(--text-secondary)`
  - [x] 3.5 내용: `text-body` 스타일로 렌더링

- [x] Task 4: `web/src/components/home/review/context-sticky-bar.tsx` 신규 생성 — 정적 disabled 상태 (AC: #5)
  - [x] 4.1 `position: fixed; bottom: 64px; left: 0; right: 0` — bottom-nav(64px) 위에 위치
  - [x] 4.2 DOM 선언 위치: `research-review-content.tsx`에서 HonestBox + "AI에게 질문하기" 링크 **이후** 선언
  - [x] 4.3 disabled CTA: `<button aria-disabled="true" aria-label="Learn Now — 비활성화됨. 리뷰 내용을 먼저 읽어 주세요" aria-describedby="ctx-hint">`
  - [x] 4.4 CTA 내 Lock 아이콘 (14px SVG) + "Learn Now" 텍스트
  - [x] 4.5 CTA 배경: `var(--text-disabled)` (#D1D1D1)
  - [x] 4.6 힌트 텍스트: `<p id="ctx-hint">` "추천 근거를 먼저 확인해 주세요 ↑" (11px/text-secondary)
  - [x] 4.7 `aria-live="polite"` 상태 영역 (visually hidden, 현재 빈 문자열 — Story 3.3에서 채움)
  - [x] 4.8 Queue/Ignore 버튼: `display: none` (Story 3.3에서 추가)
  - [x] 4.9 `prefers-reduced-motion` 미디어 쿼리 스켈레톤 추가 (Story 3.3 전환 애니메이션을 위해)

- [x] Task 5: `web/src/components/home/review/__tests__/research-review-content.test.tsx` 신규 생성 (AC: #1~#5)
  - [x] 5.1 h1으로 signal title 렌더링 검증
  - [x] 5.2 13개 섹션 순서 검증 (data-section-key 속성 확인)
  - [x] 5.3 Section 6 "현재 프로필 기준" 레이블 검증
  - [x] 5.4 HonestBox: content 비어있으면 미표시, content 있으면 표시 검증
  - [x] 5.5 HonestBox severity='high' → warning border 클래스/스타일 검증
  - [x] 5.6 "AI에게 질문하기" 링크 href 검증
  - [x] 5.7 ContextStickyBar: aria-disabled="true" 검증, DOM 위치가 마지막임을 검증

### [FLUTTER] Flutter Research Review 상세 화면 구현

- [x] Task 6: `mobile/lib/features/home/providers/research_review_provider.dart` 신규 생성
  - [x] 6.1 `ResearchReview` 데이터 클래스: `reviewId, signalId, signalTitle, result, barGateOverride, status`
  - [x] 6.2 `ReviewPayload` 데이터 클래스: 13개 섹션 필드 + `learning_time_difficulty` 중첩 클래스
  - [x] 6.3 `@riverpod Future<ResearchReview?> researchReview(ResearchReviewRef ref, String signalId)` 구현
    - Supabase에서 `reviews` JOIN `signals(title)` 조회 (status='completed', playbook_type='ai_research', signal_id=signalId)
    - `result` JSONB → `ReviewPayload.fromJson()` 변환
  - [x] 6.4 `part 'research_review_provider.g.dart'` 및 `flutter pub run build_runner build` 실행

- [x] Task 7: `mobile/lib/features/home/screens/research_review_screen.dart` 신규 생성 — placeholder 교체 (AC: #1~#5)
  - [x] 7.1 `ResearchReviewScreen(String signalId)` StatelessWidget (ConsumerWidget)
  - [x] 7.2 `ref.watch(researchReviewProvider(signalId))` → AsyncValue 핸들링
    - loading: CircularProgressIndicator
    - error/null: "리뷰를 준비하는 중입니다." + "홈으로 돌아가기" TextButton
    - data: `_ReviewBody` 위젯
  - [x] 7.3 `_ReviewBody` 위젯: `SingleChildScrollView` + `Column` 구조
    - 맨 위: 뒤로가기 (`context.go('/home')`)
    - `Semantics(header: true)` + `Text(signalTitle, style: displayMedium)` → h1 역할
    - 13개 섹션 순서대로 `_ReviewSection` 위젯 렌더링
    - Section 6: "현재 프로필 기준" 레이블 (12px, textSecondary)
    - `_HonestBox` 위젯 (content 비어있지 않을 때)
    - "AI에게 질문하기" GestureDetector/TextButton (`/home/review/$signalId/chat`)
    - `_ContextStickyBar` (Stack 활용 fixed 위치)
  - [x] 7.4 `_ReviewSection`: `Semantics(header: true)` + h2 역할 텍스트 + 내용
  - [x] 7.5 `_HonestBox`: `Container` (color: AppColors.surfaceHonestBox, borderRadius: 12), 제목 (11px/uppercase/700/textSecondary), severity='high' → `Border(left: BorderSide(color: AppColors.statusWarning, width: 3))`
  - [x] 7.6 `_ContextStickyBar` disabled 상태 (Stack overlay, bottom: 64 BottomNav 높이 위)

- [x] Task 8: `mobile/lib/core/router/app_router.dart` 수정 — placeholder → real screen
  - [x] 8.1 import `research_review_placeholder_screen.dart` → `research_review_screen.dart`로 교체
  - [x] 8.2 `ResearchReviewPlaceholderScreen` → `ResearchReviewScreen` 교체

- [x] Task 9: `mobile/lib/features/home/screens/research_review_placeholder_screen.dart` 삭제
  - [x] 9.1 파일 삭제 (기존 stub이 완전히 대체됨)

## Dev Notes

### 핵심 아키텍처 제약 (AD-3, AD-2)

- **읽기**: Supabase SDK 직접 조회 (RLS + anon key + JWT) — FastAPI 경유 없음
- **쓰기**: 없음 (Story 3.1은 읽기 전용)
- signals 테이블은 RLS 없음 (플랫폼 레벨), reviews는 `project_id → projects.user_id` 서브쿼리 RLS

### Review JSONB 구조 (`reviews.result.payload`)

백엔드가 저장하는 정확한 payload 구조 (`api/pipeline/llm/base.py` REQUIRED_SECTIONS 기준):

```typescript
interface ReviewPayload {
  one_line_definition: string;         // Section 1: 한 줄 정의
  key_concepts: string;                // Section 2: 핵심 개념 설명
  problems_solved: string;             // Section 3: 해결하는 문제
  why_it_matters: string;              // Section 4: 왜 중요한가
  vs_existing_tech: string;            // Section 5: 기존 기술과의 차이
  user_relevance: string;              // Section 6: 사용자 관련성 (개인화됨)
  learning_goals: string;              // Section 7: 학습 목표
  learning_time_difficulty: {          // Section 8: 예상 학습 시간·난이도
    estimated_hours: number;
    difficulty: 'beginner' | 'intermediate' | 'advanced';
  };
  practical_applicability: string;     // Section 9: 실무 적용 가능성
  risks: string;                       // Section 10: 위험 요소 (bar gate 필수)
  recommendation_reason: string;       // Section 11: 추천 이유 (bar gate 필수)
  reference_sources: string[];         // Section 12: 참고 출처 (URL 목록)
  honest_box: {
    content: string;                   // 비어있으면 HonestBox 숨김
    severity: 'standard' | 'high';
  };
}
```

`reviews.result` 봉투 구조 (최상위):
```json
{
  "schema_version": 1,
  "review_type": "research",
  "payload": { /* 위 ReviewPayload */ }
}
```

→ 프론트엔드에서 접근: `review.result.payload.one_line_definition` 등

### SECTION_CONFIG 배열 (웹, data-section-key)

Story 3.3의 IntersectionObserver가 이 key를 참조하므로 정확히 일치해야 함:

```typescript
const SECTION_CONFIG = [
  { key: 'one_line_definition',       label: '한 줄 정의',           sectionNum: 1 },
  { key: 'key_concepts',              label: '핵심 개념 설명',        sectionNum: 2 },
  { key: 'problems_solved',           label: '해결하는 문제',         sectionNum: 3 },
  { key: 'why_it_matters',            label: '왜 지금 중요한가',      sectionNum: 4 },
  { key: 'vs_existing_tech',          label: '기존 기술과의 차이',    sectionNum: 5 },
  { key: 'user_relevance',            label: '사용자 관련성',         sectionNum: 6 },
  { key: 'learning_goals',            label: '학습 목표',             sectionNum: 7 },
  { key: 'learning_time_difficulty',  label: '예상 학습 시간 + 난이도', sectionNum: 8 },
  { key: 'practical_applicability',   label: '실무 적용 가능성',      sectionNum: 9 },
  { key: 'risks',                     label: '위험 요소',             sectionNum: 10 },
  { key: 'recommendation_reason',     label: '추천 이유',             sectionNum: 11 },
  { key: 'reference_sources',         label: '참고 출처',             sectionNum: 12 },
] as const;
// Section 13 (HonestBox)은 별도 컴포넌트로 분리
```

Story 3.3의 bar gate 필수 섹션: `one_line_definition`, `key_concepts`, `problems_solved`, `why_it_matters`, `vs_existing_tech`, `user_relevance`, `risks`, `recommendation_reason` (1–6, 10, 11)

### 웹 Supabase 쿼리 패턴

```typescript
// page.tsx (Server Component) — createServerSupabaseClient() 사용
const { data: reviewRow } = await supabase
  .from('reviews')
  .select('result, bar_gate_override, signals(title)')
  .eq('signal_id', signalId)
  .eq('status', 'completed')
  .eq('playbook_type', 'ai_research')
  .maybeSingle();  // single() 아님 — 없을 수 있음

const signalTitle = (reviewRow?.signals as { title: string } | null)?.title ?? '';
const payload = reviewRow?.result?.payload as ReviewPayload | undefined;
```

`signals` join: `reviews.signal_id → signals.id` FK 관계로 Supabase JS SDK가 자동 해결.

### Flutter Supabase 쿼리 패턴

기존 `daily_brief_provider.dart` 패턴 준수 (Supabase.instance.client 직접 사용):

```dart
final response = await Supabase.instance.client
  .from('reviews')
  .select('id, result, bar_gate_override, signals(title)')
  .eq('signal_id', signalId)
  .eq('status', 'completed')
  .eq('playbook_type', 'ai_research')
  .maybeSingle();

if (response == null) return null;
final signals = response['signals'] as Map<String, dynamic>?;
final signalTitle = signals?['title'] as String? ?? '';
final resultJson = response['result'] as Map<String, dynamic>?;
final payload = resultJson?['payload'] as Map<String, dynamic>?;
```

### 웹 디자인 토큰 (globals.css에 이미 정의됨)

| 용도 | 변수 | 값 |
|------|------|----|
| HonestBox 배경 | `--surface-honest-box` | #F5F5F5 |
| HonestBox border (high) | `--status-warning` | #B45309 |
| disabled CTA 배경 | `--text-disabled` | #D1D1D1 |
| 레이블 / 힌트 텍스트 | `--text-secondary` | #595D6A |

### ContextStickyBar — DOM 위치 vs 시각적 위치

```
[h1 Signal 제목]
[Section 1 ~ 12 내용]
[HonestBox — Section 13]
[AI에게 질문하기 텍스트 링크]
↑ DOM 내 선언 위치 ↑

// ContextStickyBar 선언 — DOM에서 마지막
<ContextStickyBar />  // position: fixed; bottom: 64px (bottom-nav 위)
```

스크린 리더(VoiceOver/TalkBack)는 DOM 순서대로 포커스 이동 → 섹션 읽기 완료 후 CTA 도달.

AppLayout (`web/src/app/(app)/layout.tsx`): `<main className="flex-1 pb-16">` — pb-16(64px)이 bottom-nav 공간. ContextStickyBar `bottom: 64px` 으로 nav 위에 위치.

### 이 스토리의 범위 경계 (중요)

| 항목 | 이 스토리 (3.1) | 이후 스토리 |
|------|----------------|------------|
| completed Review 표시 | ✅ | — |
| Review 없음 / pending / failed 처리 | placeholder만 | Story 3.2 |
| Realtime 구독 (완료 감지) | ❌ | Story 3.2 |
| IntersectionObserver 섹션 tracking | ❌ | Story 3.3 |
| ContextStickyBar enable/disable 로직 | disabled 정적 상태만 | Story 3.3 |
| Learn Now / Queue / Ignore 결정 CTA | ❌ | Story 3.3 |
| Contextual Chat 화면 | 링크만 | Story 3.4 |
| bar_gate_override 처리 | ❌ | Story 3.3 |

### 절대 금지사항

| 금지 | 이유 |
|------|------|
| FastAPI `/api/v1/reviews/*` 호출 | 읽기는 Supabase SDK 직접 (AD-3) |
| `reviews` INSERT/UPDATE/DELETE | 쓰기는 FastAPI만 (AD-3) |
| signal_id로 단독 signals 조회 후 reviews 별도 조회 | 단일 join 쿼리로 해결 |
| ContextStickyBar 비활성화 CTA를 클릭 가능하게 | aria-disabled="true", 클릭 이벤트 없음 |
| HonestBox를 항상 렌더링 | content 비어있으면 숨김 |
| `review.result` 직접 접근 | 반드시 `review.result.payload` 접근 (봉투 구조) |

### 신규 / 수정 파일 목록

```
# 웹 신규 파일
web/src/components/home/review/research-review-content.tsx   (NEW)
web/src/components/home/review/honest-box.tsx                (NEW)
web/src/components/home/review/context-sticky-bar.tsx        (NEW)
web/src/components/home/review/__tests__/research-review-content.test.tsx (NEW)

# 웹 수정 파일
web/src/app/(app)/home/review/[signalId]/page.tsx            (UPDATE — stub 전면 교체)

# Flutter 신규 파일
mobile/lib/features/home/providers/research_review_provider.dart   (NEW)
mobile/lib/features/home/providers/research_review_provider.g.dart (NEW — build_runner)
mobile/lib/features/home/screens/research_review_screen.dart       (NEW — placeholder 교체)

# Flutter 수정 파일
mobile/lib/core/router/app_router.dart                             (UPDATE — import 교체)

# Flutter 삭제 파일
mobile/lib/features/home/screens/research_review_placeholder_screen.dart (DELETE)
```

### 이전 스토리 학습 (2-5, 2-4)

- **Supabase join 패턴**: `signals(title)` 처럼 FK 관계를 `.select()` 안에서 직접 명시 (daily_brief_provider.dart:85 — `signals(id, title, summary)`)
- **WebAgent에서 CLAUDE.md 주의**: `web/AGENTS.md` — "This is NOT the Next.js you know. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code."
- **`maybeSingle()` vs `single()`**: 결과가 0개일 수 있는 쿼리는 반드시 `maybeSingle()` 사용 (`.single()`은 0개 시 throw)
- **Flutter Riverpod**: `@riverpod` 코드 생성 방식 (AD-14), `build_runner build` 필수
- **Flutter 라우터**: `app_router.dart`에서 import 교체만으로 라우터 반영됨 (GoRouter path는 그대로 `review/:signalId`)
- **기존 테스트 패턴**: 테스트 러너 미설치 (`@ts-nocheck` + 스펙 문서 역할) — `signal-card.test.tsx` 패턴 그대로 따름

### References

- 에픽: `_bmad-output/planning-artifacts/epics.md` — Epic 3 전체 (line 521–656), Story 3.1 (line 525–553)
- 아키텍처: `ARCHITECTURE-SPINE.md` — AD-3(데이터 접근), AD-5(비동기 패턴), AD-9(RLS), AD-11(테스트), AD-14(Flutter 상태관리)
- UX: `EXPERIENCE.md` — Research Review Sections (line 213–246), Context Sticky Bar (line 154–183)
- Review 페이로드 구조: `api/pipeline/llm/base.py` — REQUIRED_SECTIONS (line 5–12), `api/pipeline/reviewer.py` — result 저장 (line 128–132)
- LLM 시스템 프롬프트(payload 포맷 참고): `api/pipeline/llm/openai_provider.py` — RESEARCH_REVIEW_SYSTEM_PROMPT
- DB 스키마: `_bmad-output/implementation-artifacts/db/001_initial_schema.sql` — reviews 테이블, RLS
- 기존 웹 stub: `web/src/app/(app)/home/review/[signalId]/page.tsx`
- Flutter stub: `mobile/lib/features/home/screens/research_review_placeholder_screen.dart`
- Flutter 라우터: `mobile/lib/core/router/app_router.dart`
- Flutter 테마: `mobile/lib/core/theme/app_theme.dart` — AppColors.surfaceHonestBox, statusWarning, textDisabled
- 이전 스토리 패턴: `_bmad-output/implementation-artifacts/2-5-on-demand-daily-brief-trigger.md`
- Supabase 쿼리 패턴: `mobile/lib/features/home/providers/daily_brief_provider.dart`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- TypeScript: `signals` join 결과 타입이 배열로 추론되어 `as unknown as { title: string }` 이중 캐스팅 적용
- Flutter build_runner: 기존 `test/profile_test.dart` 파싱 오류가 있었으나 당사 파일과 무관. `.g.dart` 생성 성공 확인
- `url_launcher` 미설치로 Flutter 참고 출처 탭 시 외부 브라우저 열기 비활성 (GestureDetector UI만 제공)

### Completion Notes List

- 웹: `page.tsx` Server Component → Supabase `reviews JOIN signals` 단일 쿼리, `maybeSingle()` 사용
- 웹: `research-review-content.tsx` Client Component — SECTION_CONFIG 12개 + HonestBox(13) 분리, Section 6 "현재 프로필 기준" 레이블 포함
- 웹: `honest-box.tsx` — severity 별 border-left 스타일 적용, content 비어있으면 상위에서 렌더링 안 함
- 웹: `context-sticky-bar.tsx` — fixed bottom 64px, aria-disabled CTA, aria-live 영역, prefers-reduced-motion 스켈레톤
- 웹: 테스트 스펙 파일 — 기존 패턴(Jest 미설치, @ts-nocheck) 동일 방식으로 AC 1-5 커버
- Flutter: `research_review_provider.dart` — Riverpod @riverpod, ReviewPayload.fromJson(), build_runner 성공
- Flutter: `research_review_screen.dart` — ConsumerWidget, Stack 구조 ContextStickyBar, Semantics header, HonestBox, back nav
- Flutter: `app_router.dart` — placeholder import/widget 교체, placeholder 파일 삭제
- Flutter analyze: No issues found

### File List

web/src/app/(app)/home/review/[signalId]/page.tsx (UPDATED)
web/src/components/home/review/research-review-content.tsx (NEW)
web/src/components/home/review/honest-box.tsx (NEW)
web/src/components/home/review/context-sticky-bar.tsx (NEW)
web/src/components/home/review/__tests__/research-review-content.test.tsx (NEW)
mobile/lib/features/home/providers/research_review_provider.dart (NEW)
mobile/lib/features/home/providers/research_review_provider.g.dart (NEW — build_runner)
mobile/lib/features/home/screens/research_review_screen.dart (NEW)
mobile/lib/core/router/app_router.dart (UPDATED)
mobile/lib/features/home/screens/research_review_placeholder_screen.dart (DELETED)

### Review Findings

- [x] [Review][Decision] Web HonestBox: `<p>` 태그 사용 — dismissed, HonestBox는 별도 컴포넌트 의도 (Story 3.3 bar gate 대상 아님)
- [x] [Review][Decision] Mobile HonestBox: `Semantics(header: true)` 없음 — dismissed, D1과 동일 결정
- [x] [Review][Defer] Mobile ContextStickyBar: `Positioned(bottom: 64)` — SafeArea 미적용 시 기기 하단 safe-area inset 누락 가능 `mobile/lib/features/home/screens/research_review_screen.dart:170` — deferred, 코드로 확인 어려움, 실기기 시각적 확인 필요
- [x] [Review][Patch] Flutter LearningTimeDifficulty.fromJson: `estimated_hours` 키 누락 시 `null as num` TypeError → AsyncError (provider가 pending 상태로 전락) `mobile/lib/features/home/providers/research_review_provider.dart:16`
- [x] [Review][Patch] Flutter LearningTimeDifficulty.fromJson: `difficulty` 키 누락 시 `null as String` TypeError → AsyncError `mobile/lib/features/home/providers/research_review_provider.dart:17`
- [x] [Review][Patch] Supabase 쿼리 오류 무음 처리: `error`를 destructure 하지 않아 네트워크/권한 오류가 "준비 중" 상태로 표시됨 `web/src/app/(app)/home/review/[signalId]/page.tsx:17`
- [x] [Review][Patch] Flutter ReviewPayload.fromJson: `reference_sources` 리스트에 비-String 요소가 있으면 TypeError `mobile/lib/features/home/providers/research_review_provider.dart:79`
- [x] [Review][Patch] Flutter response['id'] as String: null/비-String 시 TypeError — null-safe 캐스트 필요 `mobile/lib/features/home/providers/research_review_provider.dart:130`
- [x] [Review][Patch] Web ContextStickyBar: `aria-disabled="true"`만으로는 키보드 포커스/활성화 차단 안 됨 — `disabled` 속성 추가 필요 `web/src/components/home/review/context-sticky-bar.tsx:43`
- [x] [Review][Patch] Mobile Section 6 레이블 폰트 크기: 12px (스펙: 11px) `mobile/lib/features/home/screens/research_review_screen.dart:221`
- [x] [Review][Patch] Web page.tsx: `as unknown as { title: string }` 이중 캐스트 — 타입 안전성 우회, Supabase 생성 타입 또는 type guard 사용 권장 `web/src/app/(app)/home/review/[signalId]/page.tsx:25`
- [x] [Review][Patch] Web 빈 payload 화면: "홈으로" 뒤로가기 링크와 "홈으로 돌아가기" 텍스트 링크 중복 (동일 `/home` 경로) `web/src/app/(app)/home/review/[signalId]/page.tsx:33`
- [x] [Review][Patch] Flutter ResearchReview.status: DB 응답 무관 'completed'로 하드코딩 `mobile/lib/features/home/providers/research_review_provider.dart:135`
- [x] [Review][Defer] Flutter 참고 출처 GestureDetector onTap 빈 핸들러 `mobile/lib/features/home/screens/research_review_screen.dart:258` — deferred, url_launcher 미설치로 인한 의도적 제한 (Dev Notes 기록됨)
- [x] [Review][Defer] 테스트 파일이 실행 불가 스펙 문서 역할 `web/src/components/home/review/__tests__/research-review-content.test.tsx` — deferred, 프로젝트 전체 패턴 (Jest 미설치)
- [x] [Review][Defer] renderSectionContent: 복잡한 타입에 대한 String() fallback — deferred, 현재 SECTION_CONFIG 키는 모두 string 타입, 미래 확장 시 검토
- [x] [Review][Defer] SECTION_CONFIG as const 타입과 renderSectionContent string 파라미터 불일치 — deferred, 런타임 버그 없음
- [x] [Review][Defer] estimated_hours 크로스플랫폼 표시 불일치 (Flutter: toStringAsFixed(0), Web: 원본 number) — deferred, 1.5h 케이스만 차이 발생
- [x] [Review][Defer] signalId URL 파라미터 유효성 검사 없음 — deferred, RLS 보호로 실질적 위험 없음
- [x] [Review][Defer] signals join 배열 반환 가능성 — deferred, many-to-one FK 관계상 단일 객체 반환이 표준 동작
- [x] [Review][Defer] signalTitle 빈 문자열 시 h1 공백 렌더링 — deferred, LLM 파이프라인이 title 보장

## Change Log

- 2026-07-25: Story 3.1 구현 완료 — 웹(Next.js) 4개 신규 파일 + page.tsx 교체, Flutter 2개 신규 파일 + router 교체 + placeholder 삭제. TypeScript 타입 검사 통과, Flutter analyze 0 issues.
