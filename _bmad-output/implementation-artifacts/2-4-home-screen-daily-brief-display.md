---
baseline_commit: NO_VCS
---

# Story 2.4: Home Screen — Daily Brief Display

Status: done

## Story

사용자로서,
홈 화면에서 오늘의 AI CTO 브리핑을 확인하고 SignalCard를 탭하여 상세 Review로 이동할 수 있기를 원한다,
그래서 매일 관련성 높은 AI 기술을 빠르게 파악할 수 있다.

## Acceptance Criteria

**AC-1: Daily Brief 준비됨 상태 — SignalCard 목록**

- **Given** 오늘 `daily_briefs.status = 'completed'`인 레코드가 존재할 때
- **When** 홈 탭을 열면
- **Then** 섹션 헤딩 "오늘의 AI CTO 브리핑" (22px/700, `.text-section-title`) + 오늘 날짜가 표시된다
- **And** `daily_brief_signals.position` 오름차순으로 SignalCard 목록이 표시된다
- **And** 각 SignalCard: 제목(16px/600) + NEW 배지 + 관련성 태그(12px/text-secondary) + "출처 N개 · 읽기 약 5분" 메타(11px/text-tertiary) + 우측 chevron
- **And** SignalCard 배경 `surface-card(#F2F2F2)`, radius 16px, 패딩 16px, 카드 간격 10px

**AC-2: NEW 배지 — 미열람 Signal**

- **Given** 사용자가 오늘 해당 SignalCard를 아직 탭하지 않았을 때
- **Then** NEW 배지 (`accent-primary` bg, `accent-foreground` text, 10px/700/uppercase, radius pill)가 제목 오른쪽에 표시된다
- **And** 사용자가 SignalCard를 탭한 후 홈으로 돌아오면 해당 카드의 NEW 배지가 사라진다
- **And** 세션 내 seen 상태는 Web: `sessionStorage`, Flutter: 메모리 상태(Provider)로 유지한다

**AC-3: SignalCard composite aria-label (UX-DR3)**

- **Given** SignalCard의 ARIA를 검사하면
- **Then** `aria-label="[Signal 제목], NEW, 출처 [N]개, 읽기 약 5분"` 형태로 명시적으로 제공된다
- **And** DOM 내부 텍스트 concatenation 방식 금지 — composite label을 명시적으로 작성

**AC-4: 생성 중 상태**

- **Given** `daily_briefs.status = 'pending' | 'processing'`이거나 오늘 레코드가 없을 때(콜드 스타트 waiting)
- **Then** "오늘의 Daily Brief를 생성하는 중입니다." + 세 점 pulse 애니메이션이 표시된다
- **And** `prefers-reduced-motion` 환경에서는 pulse 애니메이션 대신 점 3개가 정적으로 표시된다

**AC-5: 생성 실패 상태**

- **Given** `daily_briefs.status = 'failed'`일 때
- **Then** "오늘의 Daily Brief를 생성하지 못했습니다." 메시지가 표시된다
- **And** "다시 시도하기" primary CTA가 표시된다
- **And** CTA 탭 시 `POST /api/v1/daily-briefs/trigger`가 호출된다 (Story 2.5에서 구현되는 FastAPI 엔드포인트; 404 반환 시 에러 무시 후 생성 중 상태로 전환)
- **And** 호출 직후 UI는 AC-4 생성 중 상태로 전환된다

**AC-6: 새로운 Signal 없음 상태**

- **Given** `daily_briefs.status = 'completed'`이나 `daily_brief_signals`가 없을 때
- **Then** "오늘은 새로운 Signal이 없습니다. 어제 Queue에 저장한 항목을 이어서 학습할 수 있습니다." 메시지가 표시된다
- **And** "큐 보기" CTA가 표시되고, 탭 시 큐 탭(`/queue`)으로 이동한다

**AC-7: 모든 Signal 열람 완료**

- **Given** 오늘 Daily Brief의 모든 SignalCard를 탭한 후 홈으로 돌아왔을 때
- **Then** SignalCard 목록 하단에 "오늘 브리핑을 모두 확인했습니다." 캡션(11px/text-secondary)이 표시된다

**AC-8: SignalCard 탭 → Research Review 화면 이동**

- **Given** 사용자가 SignalCard를 탭하면
- **When** Web: `/home/review/[signalId]`로 이동, Flutter: 홈 브랜치 스택에 `/home/review/:signalId` push
- **Then** Research Review 상세 화면으로 이동한다 (Story 3.1에서 구현; 이 스토리에서는 라우트 설정 + placeholder만)
- **And** 해당 signalId가 seen 상태로 마킹된다

**AC-9: Supabase Realtime 구독**

- **Given** 홈 화면이 로드된 상태에서 백그라운드에서 Daily Brief 생성이 완료되면
- **Then** 수동 새로고침 없이 자동으로 SignalCard 목록이 표시된다
- **And** Realtime 구독 채널: `daily_briefs` 테이블, `user_id = auth.uid() AND brief_date = today`

## Tasks / Subtasks

### [WEB] Next.js 홈 화면 구현

- [x] Task 1: `globals.css`에 pulse 애니메이션 추가 (AC: #4)
  - [x] 1.1 `.dot-pulse` 클래스: 0.6s ease-in-out infinite opacity 1→0.3 애니메이션
  - [x] 1.2 `@media (prefers-reduced-motion: reduce)` 내에서 `.dot-pulse { animation: none; }` 추가

- [x] Task 2: `web/src/components/home/signal-card.tsx` 생성 — 순수 presentational (AC: #1, #2, #3)
  - [x] 2.1 Props: `id: string, title: string, relevanceTag: string, sourceCount: number, isSeen: boolean, onClick: () => void`
  - [x] 2.2 `aria-label` composite: `"${title}${!isSeen ? ', NEW' : ''}, 출처 ${sourceCount}개, 읽기 약 5분"` — 명시적 string 조합
  - [x] 2.3 NEW 배지: `!isSeen && <span lang="en">NEW</span>` — `aria-hidden="true"` (composite label에 포함됨)
  - [x] 2.4 관련성 태그: `signals.summary` 텍스트 사용 (MVP; AI 개인화 관련성 태그는 후속 스토리)
  - [x] 2.5 메타 행: `출처 {sourceCount}개 · 읽기 약 5분` (read time는 MVP 고정값 5분)
  - [x] 2.6 전체 카드를 `<button>` 또는 `<a>` 로 구현 (탭 타겟 min-height 44px, UX-DR13)
  - [x] 2.7 스타일: surface-card bg, 16px radius, 16px padding, 카드 사이 10px gap

- [x] Task 3: `web/src/components/home/three-dot-loading.tsx` 생성 (AC: #4)
  - [x] 3.1 세 점 `.`×3을 `<span>` 3개로 구현, 각 `.dot-pulse` 클래스 + `animation-delay` 0 / 0.2s / 0.4s
  - [x] 3.2 `prefers-reduced-motion`은 CSS에서 처리 (애니메이션 없이 정적 점 3개 표시됨)

- [x] Task 4: `web/src/components/home/daily-brief-content.tsx` 생성 — `'use client'` (AC: #1–9)
  - [x] 4.1 Props: `initialBrief: DailyBrief | null, initialSignals: SignalWithSources[]`
  - [x] 4.2 Supabase Realtime 구독: `createClient()` (브라우저 클라이언트, `web/src/lib/supabase.ts`)
        ```typescript
        supabase.channel('daily-brief-home')
          .on('postgres_changes', {
            event: '*',
            schema: 'public',
            table: 'daily_briefs',
            filter: `user_id=eq.${userId}&brief_date=eq.${today}`,
          }, (payload) => { /* 상태 업데이트 */ })
          .subscribe()
        ```
  - [x] 4.3 `useState<Set<string>>(new Set())` — seenSignalIds, sessionStorage에서 초기화
  - [x] 4.4 `handleCardClick(signalId)` — seenSignalIds에 추가 + sessionStorage 업데이트 + 라우터 이동
  - [x] 4.5 brief status에 따른 조건부 렌더링:
        - `'completed'` + signals.length > 0 → SignalCard 목록 (AC-1, 7)
        - `'completed'` + signals.length === 0 → "새로운 Signal 없음" (AC-6)
        - `'pending' | 'processing'` → ThreeDotLoading (AC-4)
        - `'failed'` → 에러 + "다시 시도하기" (AC-5)
        - null → ThreeDotLoading (아직 생성 안 됨)
  - [x] 4.6 `handleRetry()`: `POST /api/v1/daily-briefs/trigger` 호출 후 상태를 'pending'으로 임시 변경; 404 응답 시 에러 표시 없이 진행
  - [x] 4.7 `useEffect cleanup`: Realtime 채널 unsubscribe
  - [x] 4.8 "큐 보기" CTA: `useRouter().push('/queue')`

- [x] Task 5: `web/src/app/(app)/home/page.tsx` 업데이트 (AC: #1–9)
  - [x] 5.1 `export const metadata: Metadata = { title: "홈 | Decision OS" }` 추가 (Deferred 해소: 1-3 코드 리뷰)
  - [x] 5.2 Server Component: `createServerSupabaseClient()` 로 오늘의 brief + signals 초기 fetch
  - [x] 5.3 brief fetch: `daily_briefs` WHERE `user_id = auth.uid() AND brief_date = CURRENT_DATE` ORDER BY `generated_at DESC LIMIT 1`
  - [x] 5.4 signals fetch (brief가 completed일 때): `daily_brief_signals JOIN signals JOIN signal_sources(count)` WHERE `daily_brief_id = brief.id` ORDER BY `position ASC`
  - [x] 5.5 결과를 `<DailyBriefContent initialBrief={...} initialSignals={...} />` 에 전달
  - [x] 5.6 placeholder 텍스트("Story 2.4에서 구현 예정") 완전 제거

- [x] Task 6: `/home/review/[signalId]` 라우트 추가 (AC: #8)
  - [x] 6.1 `web/src/app/(app)/home/review/[signalId]/page.tsx` 생성 — placeholder ("Story 3.1에서 구현 예정" 텍스트)
  - [x] 6.2 Back 링크로 `/home` 복귀 포함

### [FLUTTER] Flutter 홈 화면 구현

- [x] Task 7: Riverpod Provider 생성 (AC: #1, #4, #9)
  - [x] 7.1 `mobile/lib/features/home/providers/daily_brief_provider.dart` 생성
  - [x] 7.2 `dailyBriefProvider`: `@riverpod StreamProvider<DailyBriefState>` — Supabase Realtime 구독
        - `supabase.from('daily_briefs').stream(primaryKey: ['id'])` 필터 `user_id == uid AND brief_date == today`
        - 스트림에서 최신 레코드의 status → `DailyBriefState` enum으로 매핑
  - [x] 7.3 `dailyBriefSignalsProvider`: `@riverpod FutureProvider<List<SignalItem>>` — brief_id 기반 signals 조회
  - [x] 7.4 `seenSignalIdsProvider`: `@riverpod StateProvider<Set<String>>` — 세션 내 seen 상태

- [x] Task 8: `mobile/lib/features/home/widgets/signal_card.dart` 생성 (AC: #1–3, 8)
  - [x] 8.1 `SignalCard extends StatelessWidget` — props: `signal: SignalItem, isSeen: bool, onTap: VoidCallback`
  - [x] 8.2 Semantics composite label: `"${signal.title}${!isSeen ? ', NEW' : ''}, 출처 ${signal.sourceCount}개, 읽기 약 5분"`
  - [x] 8.3 NEW 배지: `!isSeen` 시 accent-primary bg, text-white, 10px/700/uppercase
  - [x] 8.4 `InkWell` 금지 — `GestureDetector` 구현 (UX-DR15: NoSplash)
  - [x] 8.5 Card 대신 `Container`로 구현: `AppColors.surfaceCard` bg, `BorderRadius.circular(16)`, padding 16px
  - [x] 8.6 `min-height` 44px (UX-DR13 탭 타겟)

- [x] Task 9: `mobile/lib/features/home/widgets/three_dot_loading_indicator.dart` 생성 (AC: #4)
  - [x] 9.1 `ThreeDotLoadingIndicator extends StatefulWidget` — 3개 도트 opacity 애니메이션
  - [x] 9.2 `MediaQuery.of(context).disableAnimations` 체크: true면 정적 점 3개 (prefers-reduced-motion)
  - [x] 9.3 각 도트 0.2s delay 차이, 0.6s opacity cycle

- [x] Task 10: `mobile/lib/features/home/screens/home_screen.dart` 업데이트 (AC: #1–9)
  - [x] 10.1 `HomeScreen` → `ConsumerWidget`으로 변경
  - [x] 10.2 `ref.watch(dailyBriefStreamProvider)` — AsyncValue 처리 (loading / error / data)
  - [x] 10.3 brief status별 분기 렌더링 (AC-1, 4, 5, 6 상태 처리)
  - [x] 10.4 SignalCard 탭: `ref.read(seenSignalIdsProvider.notifier).mark(signalId)` + `context.go('/home/review/$signalId')`
  - [x] 10.5 "다시 시도하기": http.post로 `POST FASTAPI_BASE_URL/api/v1/daily-briefs/trigger` 호출
  - [x] 10.6 placeholder 텍스트 제거

- [x] Task 11: `/home/review/:signalId` GoRouter 브랜치 추가 (AC: #8)
  - [x] 11.1 `mobile/lib/core/router/app_router.dart` — 홈 브랜치에 `/home/review/:signalId` GoRoute 추가 (placeholder screen)
  - [x] 11.2 placeholder: `ResearchReviewPlaceholderScreen` (Story 3.1에서 교체)
  - [x] 11.3 `dart run build_runner build --delete-conflicting-outputs` 실행

- [x] Task 12: 테스트 (AC: #1–9)
  - [x] 12.1 Web: `web/src/components/home/__tests__/signal-card.test.tsx` — aria-label composite 검증, NEW 배지 조건 검증 (스펙 문서; 실행 가능 러너 없음)
  - [x] 12.2 Web: `daily-brief-content.test.tsx` — 6개 상태 렌더링 검증 (스펙 문서; 실행 가능 러너 없음)
  - [x] 12.3 Flutter: `mobile/test/home_screen_test.dart` — SignalCard 위젯 테스트: 탭 타겟 44px, NEW 배지 조건, 탭 후 seen 상태 (9개 통과)

### Review Findings

- [x] [Review][Decision] todayISO 타임존 기준 결정 — UTC 유지로 확정. 서버/DB도 UTC 기준이므로 프론트-백 일관성 유지. 한국(UTC+9) 사용자의 자정~오전 9시 구간 날짜 어긋남은 MVP 범위 밖으로 수용.

- [x] [Review][Patch] Web: `signals` 상태 고정 — Realtime `completed` 전환 후 SignalCard 미표시 [daily-brief-content.tsx:69]
- [x] [Review][Patch] Flutter: `context.go()` → `context.push()` — SignalCard 탭 시 히스토리 스택 교체됨 (AC-8) [home_screen.dart:182]
- [x] [Review][Patch] Flutter: `_handleRetry` 낙관적 UI 전환 누락 — 호출 직후 "생성 중" 상태로 전환 안 됨 (AC-5) [home_screen.dart:19-31]
- [x] [Review][Patch] Web: Realtime 구독 filter에 `brief_date` 복합 조건 누락 (AC-9) [daily-brief-content.tsx:87]
- [x] [Review][Patch] Web: Realtime `event: "*"` DELETE 시 `payload.new`가 `{}` — eventType guard 추가 [daily-brief-content.tsx:87]
- [x] [Review][Patch] Web: `handleRetry` 네트워크 오류 시 UI 영구 "생성 중" 상태 잠금 — 복구 불가 [daily-brief-content.tsx:121-137]
- [x] [Review][Patch] Flutter: `dailyBriefStream` `.first` 비결정적 — `generated_at` 내림차순 정렬 후 first 필요 [daily_brief_provider.dart:64]
- [x] [Review][Patch] Flutter: `briefAsync.error` → `_buildGenerating` 대신 `_buildFailed` 표시 [home_screen.dart:67]
- [x] [Review][Patch] Web+Flutter: 날짜 표시에 `text-tertiary` 사용 — DESIGN.md 위반 [daily-brief-content.tsx:147, home_screen.dart:57]
- [x] [Review][Patch] Flutter: `_handleRetry` 중복 탭 가드 누락 — 동시 POST 방지 필요 [home_screen.dart:19]

- [x] [Review][Defer] Web: `auth.getSession()` 대신 `auth.getUser()` 사용 권장 [daily-brief-content.tsx:125] — deferred, 보안 개선이나 FastAPI가 JWT 서명 검증하므로 즉각 위험 없음
- [x] [Review][Defer] Web: 생성 중 상태 `<p>`에 `aria-live`/`role="status"` 추가 [daily-brief-content.tsx:152] — deferred, 접근성 개선 사항, 별도 패스
- [x] [Review][Defer] Flutter: `SeenSignalIds` `keepAlive` 고려 [daily_brief_provider.dart:108] — deferred, `context.push()` 수정 후 영향 재평가
- [x] [Review][Defer] Web: `NEXT_PUBLIC_FASTAPI_URL` `.env.local.example`에 누락 — deferred, ops/docs 이슈
- [x] [Review][Defer] Web: `userId` 빈 문자열 가드 부재 [page.tsx:14] — deferred, 미들웨어/RLS가 인증 보장

## Dev Notes

### ⚠️ CRITICAL: Next.js 16 + React 19 Breaking Changes

`web/AGENTS.md` 경고 — "This is NOT the Next.js you know. Read `node_modules/next/dist/docs/` before writing any code."

**반드시 구현 전 확인:**
- `next/navigation` API (useRouter, usePathname) 변경 여부
- Server/Client Component 패턴 변경 여부
- `'use client'` 지시자 동작 변경 여부
- Metadata export 패턴 변경 여부
- Layout file 구조 변경 여부

Next.js 16에서 알려진 주의사항:
- `cookies()` async 필요 (이미 `supabase-server.ts`에 `await cookies()` 적용됨 — 기존 패턴 준수)
- `createClient()`는 `web/src/lib/supabase.ts`의 브라우저 클라이언트 함수명 (이미 확립된 패턴)

---

### 데이터 접근 패턴 (AD-3)

**읽기: Supabase 직접 (anon key + RLS)**

Web 서버 컴포넌트:
```typescript
import { createServerSupabaseClient } from "@/lib/supabase-server";

// 1. 오늘 Daily Brief 조회
const { data: brief } = await supabase
  .from("daily_briefs")
  .select("id, status, brief_date, generated_at")
  .eq("user_id", user.id)           // RLS로 user_id 자동 필터되지만 명시
  .eq("brief_date", todayISO)
  .order("generated_at", { ascending: false })
  .limit(1)
  .single();

// 2. Brief Signals 조회 (brief가 completed일 때만)
const { data: signals } = await supabase
  .from("daily_brief_signals")
  .select(`
    signal_id,
    relevance_score,
    position,
    signals (
      id,
      title,
      technology_name,
      summary
    )
  `)
  .eq("daily_brief_id", brief.id)
  .order("position", { ascending: true });

// 3. Signal별 출처 수 조회
const { data: sourceCounts } = await supabase
  .from("signal_sources")
  .select("signal_id")
  .in("signal_id", signalIds);
// → 클라이언트에서 groupBy(signal_id).count()로 집계
```

Web 클라이언트 컴포넌트 (Realtime):
```typescript
import { createClient } from "@/lib/supabase";  // 브라우저 클라이언트

const supabase = createClient();
const channel = supabase
  .channel("daily-brief-home")
  .on(
    "postgres_changes",
    {
      event: "*",
      schema: "public",
      table: "daily_briefs",
      filter: `user_id=eq.${userId}`,
    },
    (payload) => {
      if (payload.new.brief_date === todayISO) {
        setBrief(payload.new as DailyBrief);
      }
    }
  )
  .subscribe();

// cleanup
return () => { supabase.removeChannel(channel); };
```

**쓰기: FastAPI 경유 (AD-3)**
- "다시 시도하기" CTA → `POST {FASTAPI_BASE_URL}/api/v1/daily-briefs/trigger`
- Authorization: `Bearer {Supabase JWT}` (AD-13)
- 응답 봉투: `{"data": ..., "error": null}` (AD-13)
- **주의**: Story 2.5에서 FastAPI 엔드포인트 구현 예정. Story 2.4에서는 프론트엔드 호출만 구현. 404 응답 시 UI는 생성 중 상태 유지.

---

### Supabase JWT 획득 (Web Client Component)

```typescript
const { data: { session } } = await supabase.auth.getSession();
const token = session?.access_token;

// FastAPI 호출 시
await fetch(`${process.env.NEXT_PUBLIC_FASTAPI_URL}/api/v1/daily-briefs/trigger`, {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
});
```

---

### 6가지 홈 화면 상태 정의 (UX-DR17)

```typescript
type DailyBriefUIState =
  | { type: "loading" }                          // 데이터 초기 로드 중
  | { type: "generating" }                       // brief status: pending | processing
  | { type: "ready"; signals: SignalItem[] }     // brief status: completed, signals.length > 0
  | { type: "no-signals" }                       // brief status: completed, signals.length === 0
  | { type: "failed" }                           // brief status: failed
  | { type: "all-seen"; signals: SignalItem[] }  // ready이고 모두 seen 상태
```

---

### SignalCard 출처 수 처리

`signal_sources` 테이블: `signal_id`, `source_type`, `url`, ...

집계 쿼리 (서버에서 처리 권장):
```sql
SELECT signal_id, COUNT(*) as source_count
FROM signal_sources
WHERE signal_id = ANY('{uuid1, uuid2, ...}')
GROUP BY signal_id
```

MVP 폴백: `signal_sources` 데이터가 없으면 "출처 5개" 하드코딩 (스텁 어댑터는 RawArticle을 하드코딩해서 반환하므로 실제 출처 수가 없을 수 있음).

---

### 관련성 태그 (MVP)

에픽에서는 "AI-generated one-line relevance statement"를 요구하지만, 현재 `signals` 테이블에는 `summary` 필드만 존재. MVP에서:
- `signals.summary`를 관련성 태그로 사용
- 텍스트가 너무 길면 1줄로 truncate (`text-overflow: ellipsis`)
- AI 개인화 관련성 태그는 Future: `daily_brief_signals.relevance_tag TEXT` 컬럼 추가 또는 Review result 활용

---

### seen 상태 관리

**Web (sessionStorage):**
```typescript
const SEEN_KEY = `seen-signals-${todayISO}`;

// 초기화
const [seenIds, setSeenIds] = useState<Set<string>>(
  () => new Set(JSON.parse(sessionStorage.getItem(SEEN_KEY) ?? "[]"))
);

// 마킹
const markSeen = (signalId: string) => {
  const next = new Set([...seenIds, signalId]);
  setSeenIds(next);
  sessionStorage.setItem(SEEN_KEY, JSON.stringify([...next]));
};
```

**Flutter (메모리 상태):**
```dart
// providers/daily_brief_provider.dart
@riverpod
class SeenSignalIds extends _$SeenSignalIds {
  @override
  Set<String> build() => {};
  void mark(String id) => state = {...state, id};
}
```

---

### Flutter Provider 패턴 (AD-14)

```dart
// daily_brief_provider.dart

@riverpod
Stream<DailyBrief?> dailyBriefStream(DailyBriefStreamRef ref) {
  final today = DateFormat('yyyy-MM-dd').format(DateTime.now());
  final userId = Supabase.instance.client.auth.currentUser!.id;
  
  return Supabase.instance.client
    .from('daily_briefs')
    .stream(primaryKey: ['id'])
    .eq('user_id', userId)
    .eq('brief_date', today)
    .map((rows) {
      if (rows.isEmpty) return null;
      return DailyBrief.fromJson(rows.first);
    });
}

@riverpod
Future<List<SignalItem>> dailyBriefSignals(
  DailyBriefSignalsRef ref, 
  String briefId,
) async {
  final response = await Supabase.instance.client
    .from('daily_brief_signals')
    .select('signal_id, position, relevance_score, signals(id, title, technology_name, summary)')
    .eq('daily_brief_id', briefId)
    .order('position', ascending: true);
  // ... map to SignalItem
}
```

`dart run build_runner build --delete-conflicting-outputs` — Provider 생성 후 반드시 실행.

---

### GoRouter 브랜치 추가 (Flutter)

기존 `app_router.dart`의 홈 브랜치에 추가:

```dart
// 기존 홈 브랜치 GoRoute에 routes 추가
GoRoute(
  path: '/home',
  builder: (context, state) => const HomeScreen(),
  routes: [
    GoRoute(
      path: 'review/:signalId',
      builder: (context, state) {
        final signalId = state.pathParameters['signalId']!;
        return ResearchReviewPlaceholderScreen(signalId: signalId);
        // Story 3.1에서 ResearchReviewScreen으로 교체
      },
    ),
  ],
),
```

`build_runner` 재실행 필요.

---

### CSS 스타일 패턴 (기존 globals.css 준수)

```css
/* globals.css에 추가 */
@keyframes dot-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.dot-pulse {
  animation: dot-pulse 0.6s ease-in-out infinite;
}

@media (prefers-reduced-motion: reduce) {
  .dot-pulse { animation: none; }
}
```

기존 토큰 클래스 사용:
- `.text-section-title` — "오늘의 AI CTO 브리핑" 헤딩
- `.text-body-card` (16px/600) — SignalCard 제목
- `.text-caption` (11px/500) — 메타 행
- `.text-badge` (10px/700/uppercase) — NEW 배지
- `var(--surface-card)`, `var(--radius-card)`, `var(--text-secondary)`, `var(--text-tertiary)` 등

`<span lang="en">` 패턴 (UX-DR14) — NEW 배지, "Daily Brief" 텍스트 등

---

### 절대 금지 사항

| 금지 | 이유 |
|------|------|
| `daily_briefs` / `daily_brief_signals` 에 직접 쓰기 | AD-3: 쓰기는 FastAPI만 |
| service_role key를 클라이언트에 노출 | AD-3 보안 |
| "다시 시도하기" CTA 없이 에러 상태만 표시 | AC-5 요구사항 |
| NEW 배지에 DOM concatenation aria-label | AC-3: composite label 명시적 작성 필수 |
| Flutter에서 `InkWell` 기본 ripple 사용 | UX-DR15: NoSplash 전면 금지 |
| 진행률 표시줄, 스트릭, 달성 배지 | UX-DR18 금지 패턴 |
| Floating Chat FAB | UX-DR18 금지 패턴 |
| 탭 타겟 44px 미만 | UX-DR13 WCAG 2.2 AA |
| `text-tertiary` (#9CA3AF) 를 날짜/기능 정보 텍스트에 사용 | DESIGN.md: 대비 부족, 메타 행만 허용 |

---

### 이전 스토리에서 인계된 Deferred 해소

| Deferred 항목 | 해소 방법 |
|--------------|---------|
| `home/page.tsx` placeholder 페이지 metadata 미설정 (Story 1.3) | Task 5.1에서 `export const metadata` 추가 |
| `home/page.tsx` 개발 스토리 번호 노출 텍스트 (Story 1.3) | Task 5.6에서 placeholder 텍스트 완전 제거 |
| `home_screen.dart` "Story 2.4에서 구현 예정" placeholder (Story 1.4) | Task 10.4에서 실제 구현으로 교체 |

---

### 크로스 스토리 의존성

| 스토리 | 관계 | 영향 |
|--------|------|------|
| Story 2.5 (On-demand Trigger) | 미완료 선행 | "다시 시도하기" CTA 호출 대상 FastAPI 엔드포인트. Story 2.4에서 프론트 호출 코드 구현; 404면 무시하고 생성 중 상태 유지 |
| Story 3.1 (Research Review 상세) | 미완료 후속 | SignalCard 탭 시 이동 목적지. Story 2.4에서 placeholder 라우트 생성; Story 3.1에서 교체 |
| Story 2.1/2.2/2.3 (파이프라인) | 완료 선행 | `daily_briefs`, `daily_brief_signals`, `signals`, `signal_sources` 테이블 존재 확인 완료 |

---

### 환경 변수

Web에서 필요한 환경 변수:
```
NEXT_PUBLIC_SUPABASE_URL=...       # 이미 설정됨
NEXT_PUBLIC_SUPABASE_ANON_KEY=...  # 이미 설정됨
NEXT_PUBLIC_FASTAPI_URL=http://localhost:8000  # 추가 필요 (로컬)
```

Flutter에서 필요한 환경 변수:
```
# FASTAPI_BASE_URL은 String.fromEnvironment('FASTAPI_BASE_URL', defaultValue: 'http://localhost:8000')
# 이미 fcm_provider.dart, profile_provider.dart에서 동일 패턴 사용 — 동일하게 적용
```

---

### 아키텍처 준수 체크리스트

| 규칙 | 근거 | 세부 사항 |
|------|------|----------|
| 읽기는 Supabase 직접 (anon key + RLS) | AD-3 | `daily_briefs`, `daily_brief_signals`, `signals`, `signal_sources` |
| 쓰기는 FastAPI 경유 | AD-3 | Trigger CTA → `POST /api/v1/daily-briefs/trigger` |
| Authorization: Bearer {JWT} | AD-13 | FastAPI 호출 시 JWT 헤더 필수 |
| Flutter: Riverpod 2.x + @riverpod | AD-14 | `StreamProvider` for Realtime, `FutureProvider` for signals |
| Supabase Realtime으로 완료 감지 | AD-5 | 수동 새로고침 없이 자동 업데이트 |
| lang="ko" + 영어 고유명사 span 마킹 | NFR-1, UX-DR14 | "Daily Brief", "NEW", "Signal" 등 |
| prefers-reduced-motion 지원 | UX-DR13, AD-8 | pulse 애니메이션 정적 대체 |
| 탭 타겟 최소 44px | UX-DR13 | SignalCard, CTA 버튼 모두 |

---

### 신규 / 수정 파일 목록

```
# 신규 파일 (Web)
web/src/components/home/signal-card.tsx         (NEW)
web/src/components/home/three-dot-loading.tsx   (NEW)
web/src/components/home/daily-brief-content.tsx (NEW — 'use client')
web/src/app/(app)/home/review/[signalId]/page.tsx (NEW — placeholder)

# 수정 파일 (Web)
web/src/app/(app)/home/page.tsx                 (UPDATE — placeholder 교체)
web/src/app/globals.css                         (UPDATE — .dot-pulse 애니메이션 추가)

# 신규 파일 (Flutter)
mobile/lib/features/home/providers/daily_brief_provider.dart  (NEW)
mobile/lib/features/home/providers/daily_brief_provider.g.dart (NEW — 코드 생성)
mobile/lib/features/home/widgets/signal_card.dart             (NEW)
mobile/lib/features/home/widgets/three_dot_loading_indicator.dart (NEW)
mobile/lib/features/home/screens/research_review_placeholder_screen.dart (NEW)

# 수정 파일 (Flutter)
mobile/lib/features/home/screens/home_screen.dart  (UPDATE — placeholder 교체)
mobile/lib/core/router/app_router.dart             (UPDATE — /home/review/:signalId 라우트 추가)
mobile/lib/core/router/app_router.g.dart           (UPDATE — 코드 생성)
```

---

### References

- 에픽: `_bmad-output/planning-artifacts/epics.md` — Story 2.4 (line 467–496), Epic 2 목표 (line 161–168)
- 아키텍처: `ARCHITECTURE-SPINE.md` — AD-3(데이터 접근), AD-5(비동기/Realtime), AD-13(API 계약), AD-14(Flutter 상태관리), AD-15(on-demand 트리거)
- UX: `DESIGN.md` — SignalCard 컴포넌트 (line 69–71), 색상/타이포그래피 토큰 전체
- UX: `EXPERIENCE.md` — Signal Card 섹션 (line 187–210), Home Daily Brief States (line 383–391), State Patterns
- 이전 스토리 (플랫폼 셸): `1-3-web-navigation-shell.md`, `1-4-flutter-navigation-shell.md`
- 이전 스토리 (파이프라인): `2-3-recommender-and-daily-brief-batch-pipeline.md` — DB 스키마, Realtime 설계 참고
- Deferred Work: `deferred-work.md` — 1-3 deferred (placeholder, metadata) 해소 대상
- DB 스키마: `supabase/migrations/` — daily_briefs (generated_at 포함), daily_brief_signals, signals, signal_sources
- Supabase 클라이언트: `web/src/lib/supabase.ts` (브라우저), `web/src/lib/supabase-server.ts` (서버)
- Flutter AppColors: `mobile/lib/core/theme/app_theme.dart`
- Next.js 가이드: `node_modules/next/dist/docs/` (AGENTS.md 경고 준수 필수)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- TypeScript 타입 에러 (TS2352): Supabase 중첩 join 반환 타입 추론이 배열로 되어 있어 `as unknown as {...}` 이중 캐스트로 해결
- Flutter `ThreeDotLoadingIndicator` 테스트에서 pending timer 오류: `Future.delayed` 대신 `Timer`로 변경하고 `dispose`에서 `cancel()` 호출
- Semantics 테스트에서 `tester.getSemantics(find.byType(Semantics).first)` 빈 라벨 반환: `tester.ensureSemantics()` + `find.byType(SignalCard)` 조합으로 수정

### Completion Notes List

- Web: `globals.css`에 `.dot-pulse` 애니메이션 및 `prefers-reduced-motion` 처리 추가
- Web: `SignalCard` 컴포넌트: composite aria-label, NEW 배지(aria-hidden), `<button>` 탭 타겟(min-height 44px), surface-card 스타일 구현
- Web: `ThreeDotLoading` 컴포넌트: CSS 기반 애니메이션으로 `prefers-reduced-motion` 자동 처리
- Web: `DailyBriefContent` ('use client'): 6가지 UI 상태(generating/ready/no-signals/failed/all-seen), Supabase Realtime 구독, sessionStorage seen 상태 관리
- Web: `home/page.tsx`: Server Component로 daily_briefs + daily_brief_signals + signal_sources 초기 fetch, metadata 추가, placeholder 텍스트 제거
- Web: `/home/review/[signalId]` placeholder 라우트 (Next.js 16 async params 패턴 준수)
- Flutter: `DailyBrief`, `SignalItem` 모델 + `dailyBriefStreamProvider`, `dailyBriefSignalsProvider`, `seenSignalIdsProvider` Riverpod provider 생성
- Flutter: `SignalCard`: GestureDetector(NoSplash 준수), Semantics composite label, ExcludeSemantics NEW 배지, constraints(minHeight: 44)
- Flutter: `ThreeDotLoadingIndicator`: Timer 기반 staggered 애니메이션, `disableAnimations` 정적 대체
- Flutter: `HomeScreen` → ConsumerWidget: `dailyBriefStreamProvider` 구독, 6가지 상태 분기, `seenSignalIdsProvider` seen 마킹
- Flutter: `app_router.dart`: `/home/review/:signalId` 중첩 GoRoute + `ResearchReviewPlaceholderScreen` 추가
- Flutter: `build_runner` 실행 완료: `daily_brief_provider.g.dart`, `app_router.g.dart` 재생성
- Web 테스트: Jest/Vitest 미설정으로 스펙 문서 형식 작성 (`__tests__/signal-card.test.tsx`, `daily-brief-content.test.tsx`)
- Flutter 테스트: `mobile/test/home_screen_test.dart` 9개 테스트 모두 통과

### File List

web/src/app/globals.css (UPDATE — dot-pulse 애니메이션 추가)
web/src/components/home/signal-card.tsx (NEW)
web/src/components/home/three-dot-loading.tsx (NEW)
web/src/components/home/daily-brief-content.tsx (NEW — 'use client')
web/src/components/home/__tests__/signal-card.test.tsx (NEW — 스펙 문서)
web/src/components/home/__tests__/daily-brief-content.test.tsx (NEW — 스펙 문서)
web/src/app/(app)/home/page.tsx (UPDATE — placeholder 교체, metadata 추가)
web/src/app/(app)/home/review/[signalId]/page.tsx (NEW — placeholder)
mobile/lib/features/home/providers/daily_brief_provider.dart (NEW)
mobile/lib/features/home/providers/daily_brief_provider.g.dart (NEW — 코드 생성)
mobile/lib/features/home/widgets/signal_card.dart (NEW)
mobile/lib/features/home/widgets/three_dot_loading_indicator.dart (NEW)
mobile/lib/features/home/screens/research_review_placeholder_screen.dart (NEW)
mobile/lib/features/home/screens/home_screen.dart (UPDATE — ConsumerWidget, 6가지 상태)
mobile/lib/core/router/app_router.dart (UPDATE — /home/review/:signalId 추가)
mobile/lib/core/router/app_router.g.dart (UPDATE — 코드 재생성)
mobile/test/home_screen_test.dart (NEW)

## Change Log

- 2026-07-24: Story 2.4 구현 완료 — Web(Next.js) + Flutter 홈 화면 Daily Brief 표시, SignalCard, 6가지 상태, Supabase Realtime, Accessibility(aria/Semantics), 라우팅 구현
