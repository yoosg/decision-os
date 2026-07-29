---
baseline_commit: NO_VCS
---

# Story 5.2: History / Memory Timeline

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

사용자로서,
히스토리 탭에서 내 모든 결정 이력을 <span lang="en">Signal→Review→Decision→Outcome</span> 체인으로 시간순 조회할 수 있기를 원한다,
그래서 과거 학습 결정과 결과를 되돌아보고 다음 결정에 참고할 수 있다.

**범위 참고**: Web + Flutter 양쪽 모두 대상이며, 이 스토리는 **신규 API 엔드포인트가 없다** — 전체가 읽기 전용이며 AD-3에 따라 클라이언트가 Supabase SDK로 직접 조회한다(기존 `reviews_select`/`decisions_select`/`outcomes_select` RLS 정책이 이미 존재하므로 신규 마이그레이션 불필요, 아래 DB 스키마 참조). `signals` 테이블은 `ENABLE ROW LEVEL SECURITY`가 걸려 있지 않은 플랫폼 레벨 테이블이라 별도 정책 없이 조회 가능하다.

## Acceptance Criteria

**AC-1: 히스토리 탭 진입 시 결정 이력 표시**
- **Given** 히스토리 탭을 열면
- **Then** 결정(`decisions`) 이력이 역시간순(`created_at` DESC)으로 표시되고 월 구분선(11px/`text-secondary`, "YYYY년 M월" 형식)으로 나뉜다
- **And** 이력이 하나도 없으면 "아직 기록된 학습 결정이 없습니다. Signal을 읽고 Learn Now를 선택하면 이곳에 기록이 시작됩니다." 빈 상태가 표시된다 [Source: epics.md line 795]

**AC-2: Memory Timeline 항목 도트/스파인**
- **Given** Memory Timeline을 확인하면
- **Then** 좌측 2px spine(`border-subtle`)에 12px 도트가 연결된다
- **And** 도트 스타일은 해당 결정의 상태에 따라 전환된다(아래 "설계 결정 1" 참조): `choice`가 `queue`/`ignore`이거나 `learn_now`이지만 Outcome 미기록이면 **Decision 스타일**(`text-primary` fill, 미기록 `learn_now`는 예외적으로 미완료 Outcome 스타일 — AC-5 참조), Outcome이 기록되면 **Outcome 스타일**(color+glyph 병행 — <span lang="en">Completed</span>(`status-positive`+"✓") / <span lang="en">Applied</span>(`status-positive`+"→") / <span lang="en">Dropped</span>(`text-primary`+"✕") / <span lang="en">Not Useful</span>(`text-secondary`+"−"))
- **And** glyph는 `ExcludeSemantics`로 감싸고 도트 요소에 `Semantics(label: "Applied 결과 — [Signal 제목]")` 형태의 composite label을 적용한다 — 이 dual-encoding 요구사항은 Outcome 도트에만 적용된다(Decision 스타일 도트는 옆의 type label 텍스트로 이미 정보가 전달되므로 별도 glyph 불필요) [Source: EXPERIENCE.md line 693, 709]

**AC-3: Timeline 카드 구성**
- **Given** Timeline 카드를 확인하면
- **Then** `surface-card` bg, 12px radius, 12×14px padding
- **And** type label(10px/uppercase/700/`text-secondary`) + 제목(14px/600) + 날짜(12px/`text-secondary`, "M월 D일" 형식) 순으로 표시된다
- **And** 날짜는 `text-tertiary`가 아닌 `text-secondary`를 사용한다(기능 정보이므로 대비 부족 색상 금지 — Story 5.1 Review Findings에서 지적된 것과 동일한 종류의 실수를 반복하지 말 것)
- **And** type label 텍스트는 Outcome 기록 시 `OUTCOME_OPTIONS`/`OUTCOME_LABELS`의 englishLabel(<span lang="en">COMPLETED/APPLIED/DROPPED/NOT USEFUL</span>)을, 미기록 시 결정 영문 라벨(<span lang="en">LEARN NOW/QUEUE/IGNORE</span> — 기존 `ContextStickyBar`/`_DynamicContextStickyBar` 버튼 라벨과 동일한 영문 표기 재사용)을 사용한다

**AC-4: Timeline 항목 탭 → 체인 상세 이동**
- **Given** Timeline 항목을 탭하면
- **Then** 해당 Signal의 체인 상세(<span lang="en">Signal→Review→Decision→Outcome</span> 전체)로 이동한다 — 경로는 `/history/chain/:signalId`(Web) / 히스토리 브랜치 내 `chain/:signalId` 중첩 라우트(Flutter)
- **And** Review가 아카이빙된 경우(`signals.status === 'archived'`) "보관된 Review" 배너와 함께 전체 내용이 읽기 전용으로 표시된다(배너 표시 조건은 읽기 전용 방어 로직이며, 이 스토리는 `archived` 상태를 세팅하는 쓰기 경로를 만들지 않는다 — 아래 "알려진 갭" 참조)

**AC-5: 미기록 Outcome 노드 상태**
- **Given** <span lang="en">Learn Now</span> 후 Outcome이 아직 없는 항목을 확인하면
- **Then** 체인 상세 화면의 Outcome 노드에 "미완료" 상태(`text-secondary`, "?" glyph 도트)가 표시된다
- **And** 메인 리스트에서도 동일한 항목은 미완료 Outcome 스타일 도트("?"/`text-secondary`)로 표시된다(AC-2의 예외 케이스)

## Tasks / Subtasks

### [Web] History 메인 리스트

- [x] Task 1: `web/src/lib/kst.ts` 확장 — 월 구분선/카드 날짜 포맷 헬퍼 추가 (AC: 1, 3)
  - [x] 1.1 `kstYearMonth(isoString: string): string` 추가 — `kstDateString(isoString).slice(0, 7)`(예: `"2026-07"`), 그룹핑 키로 사용
  - [x] 1.2 `formatMonthDivider(yearMonth: string): string` 추가 — `"2026-07"` → `"2026년 7월"` (연도/월 숫자 파싱 후 템플릿 리터럴, 라이브러리 불필요)
  - [x] 1.3 `formatCardDate(isoString: string): string` 추가 — KST 기준 `"M월 D일"` 포맷(`kstDateString`으로 날짜 문자열 획득 후 `-`로 split해 월/일 숫자 추출, 앞자리 0 제거)
  - [x] 1.4 기존 `kstDateString`은 수정하지 않는다 — Queue 탭(Story 5.1)의 미완료 판정 로직이 그대로 이 함수에 의존한다

- [x] Task 2: `web/src/app/(app)/history/page.tsx` 전면 교체 (현재 스텁) (AC: 1, 2, 3)
  - [x] 2.1 `home/page.tsx`와 동일한 Server Component 패턴: `createServerSupabaseClient()` → `supabase.auth.getUser()`로 `userId` 획득(직접 필터에는 사용하지 않음 — RLS가 처리)
  - [x] 2.2 단일 nested-embed 쿼리로 결정 이력 조회 (N+1 방지, `decisions_select`/`outcomes_select` RLS가 자동 필터링, AD-3/AD-9):
    ```ts
    const { data } = await supabase
      .from("decisions")
      .select(`
        id, choice, created_at,
        reviews!inner ( signal_id, signals ( id, title, status ) ),
        outcomes ( status, created_at )
      `)
      .order("created_at", { ascending: false });
    ```
  - [x] 2.3 **`outcomes`는 1:N 임베드로 배열이 반환된다** — `outcomes` 테이블에는 `decision_id`에 대한 `UNIQUE` 제약이 없다(`idx_outcomes_decision_id`는 단순 인덱스, 아래 DB 스키마 참조). 배열이 비어있지 않으면 `created_at` 내림차순으로 정렬해 첫 번째 요소만 "최신 Outcome"으로 사용한다. 단일 객체로 가정하고 `.outcomes.status`처럼 직접 접근하지 않는다
  - [x] 2.4 조회 결과를 `HistoryContent`가 소비할 `HistoryItemData[]`(타입은 `history-content.tsx`에 정의)로 매핑 후 props 전달
  - [x] 2.5 `metadata`: `{ title: "히스토리 | Decision OS" }`

- [x] Task 3: `web/src/components/history/history-content.tsx` 신규 (Client Component) (AC: 1, 2, 3, 4)
  - [x] 3.1 `"use client"` — props: `items: HistoryItemData[]`(타입: `{ decisionId: string; signalId: string; title: string; choice: "learn_now"|"queue"|"ignore"; outcomeStatus: "completed"|"applied"|"dropped"|"not_useful"|null; createdAt: string }`)
  - [x] 3.2 `items`를 `kstYearMonth(createdAt)`로 그룹핑(이미 역시간순 정렬된 상태이므로 순서 유지하며 그룹핑만 수행) 후 그룹 순서대로 `formatMonthDivider` 헤딩(`<h2 className="text-caption">`, 11px) + `MemoryTimelineItem` 리스트 렌더링
  - [x] 3.3 `items.length === 0`이면 AC-1 빈 상태 메시지 렌더링(다른 그룹 로직 스킵)
  - [x] 3.4 각 항목 탭 시 `router.push(`/history/chain/${signalId}`)` (AC-4)
  - [x] 3.5 이 컴포넌트는 **낙관적 업데이트 상태를 가지지 않는다** — Queue 탭(`queue-content.tsx`)과 달리 History는 순수 읽기 전용이므로 서버에서 받은 `items`를 그대로 렌더링만 한다(불필요한 `useState` 래핑 금지, YAGNI)

- [x] Task 4: `web/src/components/history/memory-timeline-item.tsx` 신규 (Presentational) (AC: 2, 3)
  - [x] 4.1 Props: `title, dateISO, dotStyle`(`{ kind: "decision"; choice: "learn_now"|"queue"|"ignore" } | { kind: "outcome"; status: OutcomeStatus } | { kind: "outcome-pending" }`), `onTap`
  - [x] 4.2 도트 색상/glyph 매핑은 `web/src/components/home/outcome/outcome-card.tsx`의 `OUTCOME_OPTIONS`(englishLabel)를 import해 재사용 — 새 매핑 배열을 중복 정의하지 않는다. 색상 매핑만 이 파일에 추가: `{ completed: "status-positive", applied: "status-positive", dropped: "text-primary", not_useful: "text-secondary" }`, glyph 매핑: `{ completed: "✓", applied: "→", dropped: "✕", not_useful: "−" }`, `outcome-pending`은 `text-secondary` + `"?"` 고정
  - [x] 4.3 Decision 스타일(`kind: "decision"`) 도트: `text-primary` fill, glyph 없음, type label은 `{ learn_now: "LEARN NOW", queue: "QUEUE", ignore: "IGNORE" }` 매핑(`context-sticky-bar.tsx`의 버튼 라벨과 동일 영문 표기)
  - [x] 4.4 전체를 단일 `<button>`으로 감싸도(Queue와 달리 중첩 인터랙티브 요소 없음 — "일정 변경" 같은 2차 액션이 없으므로 `signal-card.tsx`의 단일 버튼 패턴을 그대로 따를 수 있다)
  - [x] 4.5 `min-height: 44px`, `background: var(--surface-card)`, `border-radius: 12px`, `padding: 12px 14px`
  - [x] 4.6 Outcome 도트만 `ExcludeSemantics` 상당(Web에서는 glyph `<span aria-hidden="true">`) + 버튼 전체 `aria-label`에 `"${outcomeEnglishLabel} 결과 — ${title}"` 포함(AC-2). Decision 스타일 도트는 버튼의 기본 텍스트 콘텐츠(제목+타입 라벨)로 이미 접근 가능하므로 별도 aria-label 조합 불필요

- [x] Task 5: `web/src/components/history/__tests__/history-content.test.tsx` 신규 — 스펙 문서 (AC: 1, 2, 3) — 이 저장소는 Jest/Vitest 러너가 없다(`signal-card.test.tsx` 상단 주석 참조, Story 5.1과 동일 컨벤션). 파일 상단에 동일한 `// @ts-nocheck` + 안내 주석 포함
  - [x] 5.1 월 그룹핑, 빈 상태, Outcome 유무에 따른 도트 스타일 전환, outcome 배열 다중 요소 시 최신 것 선택 검증

### [Web] Chain 상세 화면

- [x] Task 6: `web/src/components/home/review/review-sections.tsx` 신규 — `research-review-content.tsx`에서 섹션 렌더링 로직 추출 (AC: 4) — **순수 리팩터링, 기존 렌더 출력은 완전히 동일하게 유지해야 한다**
  - [x] 6.1 `research-review-content.tsx`의 `SECTION_CONFIG`(line 29-50), `DIFFICULTY_LABEL`(line 52-56), `renderSectionContent`(line 58-93), `ReviewPayload` 타입(line 7-27)을 이 신규 파일로 이동(export)
  - [x] 6.2 `ReviewSections({ payload }: { payload: ReviewPayload })` 컴포넌트 추가 — `research-review-content.tsx`의 12개 섹션 렌더링 블록(line 139-161) + `honest_box`(line 163-170) 렌더링만 포함, 뒤로가기 링크/타이틀/Chat 링크/`ContextStickyBar`는 **포함하지 않는다**(이 부분들은 Home/Queue 전용 인터랙티브 UI)
  - [x] 6.3 `research-review-content.tsx`는 이 신규 컴포넌트를 import해 기존 12개 섹션 렌더링 블록을 `<ReviewSections payload={payload} />` 호출로 교체 — 뒤로가기 링크/타이틀/Chat 링크/`ContextStickyBar`는 그대로 유지(변경 없음)
  - [x] 6.4 이 리팩터링 후 기존 Home(`/home/review/:id`)과 Queue(`/queue/review/:id`, Story 5.1)의 시각적 출력이 픽셀 단위로 동일해야 한다 — 회귀 발생 시 즉시 원복

- [x] Task 7: `web/src/components/history/archived-banner.tsx` 신규 (AC: 4) — 시각 스펙 미정의(EXPERIENCE.md/DESIGN.md 어디에도 색상/레이아웃 명시 없음, 아래 "설계 결정 3" 참조)
  - [x] 7.1 `honest-box.tsx`의 박스 셸 패턴(surface bg + `border-radius: 12px` + `padding: 16px` + 11px/uppercase/700 라벨 + body 텍스트)을 구조적으로 재사용하되, `background: var(--surface-card-alt)`(honest-box 전용 톤과 구분), `borderLeft: "3px solid var(--text-secondary)"`(경고 아님 — 중립 정보)
  - [x] 7.2 라벨 텍스트: "보관된 REVIEW", 본문: "이 Signal은 보관되어 최신 정보 갱신이 중단되었습니다. 아래 내용은 결정 당시 기록입니다."

- [x] Task 8: `web/src/app/(app)/history/chain/[signalId]/page.tsx` 신규 (AC: 4, 5)
  - [x] 8.1 Server Component — `web/src/app/(app)/home/review/[signalId]/outcome/page.tsx`(line 33-65)의 순차 조회 패턴을 모델로 삼아 4단계로 확장:
    1. `signals` 조회: `.select("id, title, status").eq("id", signalId).maybeSingle()` — 없으면 `notFound()`
    2. `reviews` 조회: `.select("id, status, result, created_at").eq("signal_id", signalId).eq("status", "completed").order("created_at", { ascending: false }).limit(1).maybeSingle()`
    3. `decisions` 조회: `.select("id, choice, queue_timing, created_at").eq("review_id", review.id).order("created_at", { ascending: false }).limit(1).maybeSingle()` — Task outcome/page.tsx와 달리 `choice` 필터 없음(모든 결정 유형 표시)
    4. `outcomes` 조회: `.select("id, status, useful, actual_learning_time_min, applied_project_note, memo, created_at").eq("decision_id", decision.id).order("created_at", { ascending: false }).limit(1).maybeSingle()` — decision이 없으면 이 단계 스킵
  - [x] 8.2 각 단계 결과가 `null`이면 이후 단계는 실행하지 않고 해당 노드부터 "미완료"/미존재로 처리(예: review가 없으면 Decision/Outcome 조회 자체를 생략)
  - [x] 8.3 `metadata`: `{ title: "체인 상세 | Decision OS" }`
  - [x] 8.4 조회 결과를 `ChainDetailContent`에 props로 전달

- [x] Task 9: `web/src/components/history/chain-detail-content.tsx` 신규 (AC: 4, 5)
  - [x] 9.1 뒤로가기 링크(`href="/history"`, `research-review-content.tsx`의 뒤로가기 마크업 재사용하되 목적지만 변경)
  - [x] 9.2 `signal.status === "archived"`이면 `ArchivedBanner`(Task 7)를 헤더 바로 아래 렌더링(AC-4)
  - [x] 9.3 4개 노드를 순서대로(Signal → Review → Decision → Outcome) 세로 나열, 각 노드는 Task 4의 도트 스타일을 재사용(동일 시각 언어 유지): Signal 노드는 `text-secondary` fill 도트(글리프 없음)
  - [x] 9.4 Review 노드 아래 `<ReviewSections payload={review.result.payload} />`(Task 6) 렌더링 — Chat 링크/`ContextStickyBar` 없음(이미 결정이 내려진 과거 기록이므로 재결정 유도 UI 금지, 아래 "절대 금지사항" 참조). `review.result`가 없으면(예: review 자체가 없는 극단적 케이스) 이 섹션 자체를 생략
  - [x] 9.5 Decision 노드: `choice` 영문 라벨(Task 4.3과 동일 매핑) + `created_at` 날짜
  - [x] 9.6 Outcome 노드: outcome이 있으면 색상+glyph(Task 4.2 매핑, AC-2) + 상태 한글 라벨(`OUTCOME_OPTIONS`의 `koreanLabel`) 표시, 없으면 "미완료" 상태(`text-secondary`, "?" glyph) 표시(AC-5) — 단, `choice !== "learn_now"`이면 애초에 Outcome이 발생하지 않는 정상 흐름이므로 "미완료"가 아니라 노드 자체를 흐리게(`text-tertiary`) 표시하거나 생략(설계 결정 필요 시 "미완료"와 동일 처리로 통일 — 별도 시각 언어 신설 없이 재사용, 아래 "설계 결정 1" 참조)

### [Flutter] History 메인 리스트

- [x] Task 10: `mobile/lib/features/history/providers/history_provider.dart` 신규 (AC: 1, 2, 3) — **단순 `Future` 함수형 프로바이더** (`@riverpod Future<List<HistoryItemData>> historyItems(...)`) — `queue_provider.dart`의 `QueueItems`(클래스 기반 `Notifier`, 낙관적 업데이트)를 이 스토리에서 그대로 복제하지 않는다. History는 쓰기 동작이 전혀 없는 순수 읽기 화면이므로 클래스 기반 Notifier는 불필요한 과설계다(YAGNI) — Story 5.1의 `estimatedLearningMinutes`(단순 `Future` 프로바이더)와 동일한 패턴을 따른다
  - [x] 10.1 `HistoryItemData` 클래스: `decisionId, signalId, title, choice(String), outcomeStatus(String?), createdAt(DateTime)`
  - [x] 10.2 쿼리(Web Task 2.2와 동일 nested-embed): `Supabase.instance.client.from('decisions').select('id, choice, created_at, reviews!inner(signal_id, signals(id, title, status)), outcomes(status, created_at)').order('created_at', ascending: false)` — `.stream()` 사용 금지(nested embed 미지원, `daily_brief_provider.dart`와 동일 이유)
  - [x] 10.3 `outcomes`가 배열로 반환됨 — 비어있지 않으면 `created_at` 기준 최신 요소만 사용(Web Task 2.3과 동일 근거, `outcomes.decision_id`에 `UNIQUE` 제약 없음)
  - [x] 10.4 KST 월 그룹핑 키/포맷 헬퍼는 이 파일에 private 함수로 추가(`String _kstYearMonth(DateTime dt)`, `String _formatMonthDivider(String yearMonth)`, `String _formatCardDate(DateTime dt)`) — `queue_provider.dart`의 `_kstDateStr` 스타일 그대로 확장(Web Task 1과 동일 로직을 Dart로 이식, 신규 패키지 의존성 없음)

- [x] Task 11: `mobile/lib/features/history/widgets/memory_timeline_item.dart` 신규 (AC: 2, 3)
  - [x] 11.1 Web Task 4와 동일한 도트 스타일 분기(Decision/Outcome/Outcome-pending) + `Semantics`(Outcome만 composite label, `ExcludeSemantics`로 glyph 감싸기 — Queue의 `queue_item.dart` Semantics 패턴 참조)
  - [x] 11.2 `InkWell`(`splashFactory: NoSplash.splashFactory`, UX-DR18) 단일 탭 영역 — 중첩 액션 없음
  - [x] 11.3 `minHeight: 44`, `surface-card` 배경, 12px radius

- [x] Task 12: `mobile/lib/features/history/screens/history_screen.dart` 전면 교체 (현재 스텁) (AC: 1, 2, 3, 4)
  - [x] 12.1 `ConsumerWidget`으로 전환, `ref.watch(historyItemsProvider)` `.when(loading/error/data)` 처리
  - [x] 12.2 월별 그룹핑 후 구분선(`Theme.of(context).textTheme.bodySmall`, 기존 스텁의 부제 스타일과 유사하되 11px) + `MemoryTimelineItem` 리스트
  - [x] 12.3 빈 상태: AC-1 문구 그대로, 기존 스텁의 `bodyLarge` 스타일 재사용
  - [x] 12.4 항목 탭 시 `context.push('/history/chain/${item.signalId}')` (AC-4)

### [Flutter] Chain 상세 화면

- [x] Task 13: `mobile/lib/features/home/screens/research_review_screen.dart` 리팩터링 — 읽기 전용 섹션 위젯 추출 (AC: 4) — **이 태스크를 시작하기 전 파일 전체(1000+줄)를 반드시 정독한다.** 이전 세션 조사에서 `_DynamicContextStickyBar`(line 632-1009)가 `_ReviewBody`(line 461-471 부근)에서 무조건 렌더링됨은 확인했으나, 12개 섹션을 빌드하는 정확한 위젯/메서드 구조(Web의 `SECTION_CONFIG` 상당)는 이번 조사에서 직접 읽지 않았다 — 구현 시 반드시 확인할 것
  - [x] 13.1 Web Task 6과 동일한 원칙으로, 12개 섹션 + honest box를 렌더링하는 부분을 `mobile/lib/features/home/widgets/review_sections.dart`(신규 public 위젯, 예: `ReviewSections extends StatelessWidget`)로 추출 — `_DynamicContextStickyBar`/뒤로가기/Chat 이동 버튼은 이 위젯에 포함하지 않는다
  - [x] 13.2 `research_review_screen.dart`는 이 신규 위젯을 사용하도록 교체 — 기존 시각 출력이 완전히 동일해야 한다(순수 추출, 회귀 금지)

- [x] Task 14: `mobile/lib/features/history/widgets/archived_banner.dart` 신규 (AC: 4) — Web Task 7과 동일 시각 결정(surface-card-alt bg, `text-secondary` 3px 좌측 보더, "보관된 REVIEW" 라벨)

- [x] Task 15: `mobile/lib/features/history/providers/chain_detail_provider.dart` 신규 (AC: 4, 5) — family 프로바이더, `signalId`로 파라미터화
  - [x] 15.1 `@riverpod Future<ChainDetailData?> chainDetail(ChainDetailRef ref, String signalId)` — 단순 `Future` 프로바이더(쓰기 없음, YAGNI 원칙 Task 10과 동일)
  - [x] 15.2 Web Task 8.1의 4단계 순차 조회를 그대로 Dart로 이식 — `signals` → `reviews`(`status='completed'`, 최신 1건) → `decisions`(최신 1건, `choice` 필터 없음) → `outcomes`(최신 1건). 각 단계는 `.maybeSingle()` 상당(Supabase Dart는 `.single()`이 없으면 예외 발생 여부 확인 후 안전한 null 처리 사용 — `research_review_screen.dart`의 기존 조회 코드 컨벤션 참조)

- [x] Task 16: `mobile/lib/features/history/screens/chain_detail_screen.dart` 신규 (AC: 4, 5)
  - [x] 16.1 `ConsumerWidget`, `ref.watch(chainDetailProvider(signalId))` `.when(...)` 처리
  - [x] 16.2 `signal.status == 'archived'`이면 `ArchivedBanner`(Task 14) 렌더링
  - [x] 16.3 4개 노드 순서대로 렌더링, Review 노드는 `ReviewSections`(Task 13.1) 재사용, Decision/Outcome 노드는 `MemoryTimelineItem`(Task 11)과 동일한 도트 스타일 위젯을 재사용(별도 도트 위젯 신규 작성 금지 — 공용 위젯으로 추출해 `memory_timeline_item.dart`와 `chain_detail_screen.dart` 양쪽에서 사용)

- [x] Task 17: `mobile/lib/core/router/app_router.dart` 수정 (AC: 4)
  - [x] 17.1 `/history` `StatefulShellBranch`(현재 132-135줄, flat `GoRoute` 1개)에 Home/Queue 브랜치와 동일한 구조로 `chain/:signalId` 중첩 라우트 추가: `GoRoute(path: '/history', builder: (_, __) => const HistoryScreen(), routes: [GoRoute(path: 'chain/:signalId', builder: (_, state) => ChainDetailScreen(signalId: state.pathParameters['signalId']!))])`
  - [x] 17.2 `ResearchReviewScreen`을 히스토리 브랜치에 별도로 마운트하지 않는다 — Review 콘텐츠는 `ChainDetailScreen` 내부에 인라인으로 표시되며(Task 16.3), Queue 탭처럼 별도 push 라우트가 아니다(AC-4가 "체인 상세로 이동"만 요구하며 그 안에서 Review 전체 내용이 읽기 전용으로 표시되어야 하므로 — EXPERIENCE.md line 445)

- [x] Task 18: `mobile/test/history_test.dart` 신규 (AC: 1, 2, 3, 4, 5)
  - [x] 18.1 `MemoryTimelineItem` 위젯: 도트 스타일 3종(decision/outcome/outcome-pending) 렌더링 검증
  - [x] 18.2 월 그룹핑 헬퍼 유닛 테스트
  - [x] 18.3 `ChainDetailScreen`: archived 배너 조건부 렌더링, Outcome 미기록 시 "미완료" 표시
  - [x] 18.4 `navigation_shell_test.dart`의 `_buildTestRouter()` 패턴을 확장한 라우팅 테스트: `/history`에서 항목 탭 시 `/history/chain/:signalId`로 push되고 `BottomNavigationBar`가 히스토리 탭(index 2)을 유지하는지 검증

## Dev Notes

### 핵심 아키텍처 제약

- **AD-3 (데이터 접근 소유권)**: 이 스토리는 **쓰기가 전혀 없다** — 전체가 클라이언트의 직접 Supabase SDK 조회다. 신규 API 엔드포인트 없음. [Source: ARCHITECTURE-SPINE.md#AD-3]
- **AD-9 (RLS 패턴)**: `decisions`/`outcomes`/`reviews`는 간접 소유(project_id 경유 `EXISTS` 체인) RLS로 이미 보호됨. `signals`는 RLS 자체가 비활성화된 플랫폼 레벨 테이블(사용자 무관 데이터)이라 별도 정책이 없다. [Source: ARCHITECTURE-SPINE.md#AD-9, 001_initial_schema.sql line 154-164 — `ALTER TABLE public.signals ENABLE ROW LEVEL SECURITY` 자체가 없음]
- **AD-5는 이 스토리에 적용되지 않음**: 조회만 하는 화면이며 상태 머신을 다루지 않는다(Story 5.1의 `decisions` 판단과 동일 논리).
- **UX-DR9 (4탭 내비게이션 + 브랜치 스택)**: Flutter `/history` 브랜치에 `chain/:signalId` 중첩 라우트 추가(Home/Queue 브랜치와 동일 구조). Web은 `/history/chain/:signalId` 별도 URL로 뒤로가기가 `/history`로 복귀하도록 한다. [Source: EXPERIENCE.md line 95-103 패턴을 히스토리에 동일 적용]
- **UX-DR18 (금지된 상호작용 패턴)**: FAB 없음, 캐러셀 없음, 드래그 재정렬 없음, 롱프레스 없음, 카드류 잉크 스플래시 없음(`NoSplash.splashFactory`). Memory Timeline은 "레코드이지 할 일 목록이 아니다" — 항목을 수정/삭제하는 어떤 인터랙션도 추가하지 않는다. [Source: EXPERIENCE.md line 828]
- **WCAG 2.2 AA (UX-DR13)**: 최소 44×44 tap target, Outcome 도트만 색상+glyph 이중 인코딩 필수(다른 도트는 옆 텍스트 라벨로 이미 충족).

### DB 스키마 참조 (기존 마이그레이션, 수정 없음 — 신규 마이그레이션 불필요)

```sql
-- reviews (line 61-91) — result: JSONB 봉투 {schema_version, review_type, payload} (AD-4)
-- decisions (line 94-106) — choice IN ('learn_now','queue','ignore')
-- outcomes (line 109-120) — status IN ('completed','applied','dropped','not_useful')
--   ⚠ decision_id에 UNIQUE 제약 없음(idx_outcomes_decision_id는 단순 인덱스, line 238) — 1:N 가능
-- signals (line 154-164) — status IN ('raw','processed','archived'), RLS 비활성화(플랫폼 레벨)

-- RLS (SELECT only, 쓰기는 FastAPI service_role만)
CREATE POLICY "reviews_select" ON public.reviews FOR SELECT
    USING (EXISTS (SELECT 1 FROM public.projects p WHERE p.id = project_id AND p.user_id = auth.uid()));  -- line 296-300

CREATE POLICY "decisions_select" ON public.decisions FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.reviews r JOIN public.projects p ON p.id = r.project_id
        WHERE r.id = review_id AND p.user_id = auth.uid()
    ));  -- line 303-308

CREATE POLICY "outcomes_select" ON public.outcomes FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.decisions d
        JOIN public.reviews r ON r.id = d.review_id
        JOIN public.projects p ON p.id = r.project_id
        WHERE d.id = decision_id AND p.user_id = auth.uid()
    ));  -- line 311-317
```

### 설계 결정 1: 메인 리스트 = "Signal당 1개 노드 나열"이 아니라 "Decision당 1개 항목" (스펙 해석)

epics.md AC 원문은 Signal/Review/Decision/Outcome 4가지 도트 색상을 모두 나열해(line 799-801) 마치 4종 노드가 평면적으로 섞여 표시되는 것처럼 읽힐 수 있다. 그러나 EXPERIENCE.md line 444("Each item shows the **Decision node's label** (Learn Now / Queue / Ignore) **and Outcome state if recorded**")이 더 구체적이며, epics.md의 "Timeline 항목을 탭하면 → 체인 상세로 이동"(line 809-810, 별도 화면 전환)과도 정합적이다. **결정**: 메인 리스트는 **Decision 레코드당 1개 카드**를 표시하고, 그 카드의 도트/타입 라벨은 Outcome 기록 여부에 따라 Decision 스타일 ↔ Outcome 스타일로 전환된다(AC-2). epics.md가 나열한 4가지 도트 색상 전부는 **체인 상세 화면**에서 Signal→Review→Decision→Outcome 4개 노드를 동시에 보여줄 때 사용된다(AC-4, Task 9/16). `choice != 'learn_now'`인 결정(Queue/Ignore)은 애초에 Outcome이 발생하지 않으므로 메인 리스트에서 영구히 Decision 스타일로 남는다.

### 설계 결정 2: Outcome 1:N 스키마 갭 — 최신 레코드 우선

`outcomes.decision_id`는 `UNIQUE` 제약이 없다(FK + 단순 인덱스만 존재, line 238). 이론적으로 한 Decision에 여러 Outcome이 기록될 수 있다(API 쓰기 경로에 이를 막는 로직이 있는지는 이 스토리 범위에서 확인하지 않음 — 스키마 레벨 사실만 반영). Supabase 클라이언트가 `outcomes(...)` nested embed를 요청하면 **배열**이 반환되므로, 단일 객체로 가정하고 직접 필드 접근하면 런타임 오류 또는 잘못된 렌더링이 발생한다. **결정**: 배열이 비어있지 않으면 `created_at` 내림차순으로 정렬해 첫 번째(최신) 요소만 사용한다(Task 2.3/10.3/8.1-4).

### 설계 결정 3: "보관된 Review" 배너 시각 스펙 부재 → HonestBox 셸 재사용

DESIGN.md/EXPERIENCE.md 어디에도 이 배너의 색상/레이아웃이 명시되어 있지 않다(전수 검색 완료 — "보관"/"archived" 키워드로 DESIGN.md에서 0건 매치). **결정**: 기존 `honest-box.tsx`의 박스 셸 구조(surface bg + 12px radius + 16px padding + 11px/uppercase/700 라벨 + body)를 구조적으로 재사용하되, `surface-honest-box`(AI 정직성 전용 의미) 대신 `surface-card-alt`를, `status-warning` 보더 대신 `text-secondary` 보더를 사용해 "경고"가 아닌 "중립 정보"임을 시각적으로 구분한다(Task 7/14).

### 알려진 갭 — `signals.status = 'archived'`를 세팅하는 쓰기 경로가 현재 존재하지 않음 (이 스토리 범위 밖)

EXPERIENCE.md line 402/773은 <span lang="en">Ignore</span> 결정 시 "Research Review archived"(Signal이 아카이빙됨)를 명시한다. 그러나 `api/`, `web/src/`, `mobile/lib/` 전수 검색 결과 `archived`라는 문자열로 `signals.status`를 업데이트하는 코드 경로가 **어디에도 없다**(Ignore 결정은 현재 `decisions` 테이블에 `choice='ignore'` 행만 생성하고 `signals.status`는 손대지 않는다). 즉, AC-4의 "보관된 Review" 배너는 스펙대로 구현해도 현재 시스템에서는 **절대 표시되지 않는 죽은 조건 분기**가 된다. **이 스토리는 이 쓰기 경로를 추가하지 않는다** — Ignore 결정 흐름(Story 3.3 영역)을 건드리는 것은 범위 확장이며, 이 스토리의 책임은 "만약 `archived`가 세팅된다면 올바르게 표시한다"는 읽기 전용 방어 로직까지다. 향후 Ignore 흐름에 `signals.status='archived'` 업데이트가 추가되면 이 스토리의 배너 로직이 자동으로 작동한다.

### 재사용 패턴 (그대로 따를 것)

- **`web/src/app/(app)/home/review/[signalId]/outcome/page.tsx`(line 33-65)**: Signal → Review(`status='completed'` 필터) → Decision 순차 조회 패턴. Chain 상세 페이지(Task 8)가 이 구조를 4단계로 확장한다.
- **`web/src/components/home/outcome/outcome-card.tsx`의 `OUTCOME_OPTIONS`**: `{status, englishLabel, koreanLabel}` 배열 — Timeline/Chain 상세의 Outcome 라벨 매핑에 그대로 import해 재사용한다(신규 매핑 배열 중복 정의 금지).
- **`web/src/components/home/review/honest-box.tsx`**: `ArchivedBanner`(Task 7/14)의 구조적 모델(설계 결정 3).
- **`web/src/lib/kst.ts`의 `kstDateString`(Story 5.1)**: 월 그룹핑/카드 날짜 포맷의 기반 함수 — 이 스토리는 이를 확장만 하고 기존 시그니처는 변경하지 않는다.
- **`mobile/lib/features/queue/providers/queue_provider.dart`의 `_kstDateStr`**: History 프로바이더의 KST 헬퍼가 동일 스타일로 확장.
- **`daily_brief_provider.dart`의 Future+nested-embed 패턴**: `.select('a, b, rel(c,d))')`는 `Future` 기반 일회성 쿼리에서만 동작(`.stream()` 미지원) — `history_provider.dart`/`chain_detail_provider.dart` 모두 이 제약을 따른다.
- **`mobile/lib/core/router/app_router.dart`의 Home/Queue 브랜치 중첩 라우트 구조**: `/history` 브랜치에 `chain/:signalId`를 추가할 때 그대로 모델로 삼는다.
- **`research_review_screen.dart`/`research-review-content.tsx`의 12-섹션 렌더링**: Chain 상세의 Review 노드가 이를 추출한 공용 위젯/컴포넌트(Task 6, 13)로 재사용한다 — `ContextStickyBar`/`_DynamicContextStickyBar`(무조건 렌더링되는 <span lang="en">Learn Now/Queue/Ignore</span> 액션 바)는 **재사용하지 않는다**. 이미 결정이 내려진 과거 기록에 재결정 유도 UI를 보여주는 것은 의미상 오류다.

### 기존 코드베이스 현황 (수정 대상 파일)

- `web/src/app/(app)/history/page.tsx` (11줄, 전체 정독 완료) — "Story 5.2에서 구현 예정" 플레이스홀더. 전면 교체.
- `mobile/lib/features/history/screens/history_screen.dart` (31줄, 전체 정독 완료) — 동일 플레이스홀더(`StatelessWidget`). `ConsumerWidget`으로 교체.
- `web/src/components/layout/bottom-nav.tsx` (78줄, 전체 정독 완료) — `/history` 탭이 이미 4탭 내비게이션에 존재(`{ href: "/history", label: "히스토리", icon: "🕐" }`), `isActive`는 `pathname.startsWith(tab.href + "/")`로 `/history/chain/...`도 자동 활성화. **변경 불필요.**
- `mobile/lib/core/router/app_router.dart` (134줄) — `/history` 브랜치(132-135줄)는 현재 flat `GoRoute` 1개. Task 17에서 Home/Queue 브랜치와 동일 구조로 확장.
- `web/src/components/home/review/research-review-content.tsx` (195줄, 전체 정독 완료) — Task 6에서 섹션 렌더링 로직을 `review-sections.tsx`로 추출하는 리팩터링 대상. 뒤로가기/Chat/`ContextStickyBar`는 그대로 유지.
- `web/src/components/home/review/review-page-content.tsx` (187줄, 전체 정독 완료) — 이 스토리에서 **재사용하지 않는다**(트리거/재시도 로직이 Chain 상세에는 불필요 — Review는 이미 `completed` 상태로 존재함이 전제). 신규 Chain 상세 페이지는 이 컴포넌트를 import하지 않는다.
- `mobile/lib/features/home/screens/research_review_screen.dart` (1000+줄, 이번 조사에서 CTA 바 부분만 확인 — Task 13 시작 전 전체 정독 필수) — 12-섹션 빌드 로직을 `review_sections.dart`로 추출하는 리팩터링 대상.
- `_bmad-output/implementation-artifacts/db/001_initial_schema.sql` — 스키마 변경 없음, 참조만.

### 범위 경계

| 항목 | 이 스토리 (5.2) | 이후 |
|------|----------------|------|
| 메인 리스트(Decision당 1항목, 월 그룹핑, 빈 상태) | ✅ | — |
| 도트 스타일 전환(Decision ↔ Outcome) | ✅ | — |
| Chain 상세(Signal→Review→Decision→Outcome 4노드) | ✅ | — |
| "보관된 Review" 배너 표시(읽기 전용 방어 로직) | ✅ | — |
| `signals.status='archived'`를 세팅하는 쓰기 경로(Ignore 흐름 연동) | ❌ | 별도 스토리(Story 3.3 영역, 알려진 갭 참조) |
| Chain 상세에서 Chat/재결정 등 인터랙티브 액션 | ❌ | 범위 밖 — 과거 기록은 읽기 전용 |
| Memory Timeline 항목 수정/삭제 | ❌ | 영구 금지(EXPERIENCE.md line 828 — "레코드이지 할 일 목록이 아니다") |
| 페이지네이션/무한 스크롤 | ❌ | V2 — 현재 규모에서는 불필요(Story 5.1과 동일 판단) |
| `decisions`/`outcomes`/`signals` 신규 마이그레이션 | ❌ | 불필요 — 이미 존재 |

### 절대 금지사항

| 금지 | 이유 |
|------|------|
| `decisions`/`outcomes`/`signals` 관련 신규 DB 마이그레이션 추가 | 스키마·RLS 모두 이미 존재 |
| History/Chain 상세 조회용 신규 API 엔드포인트 추가 | AD-3 — 순수 읽기는 클라이언트가 Supabase SDK로 직접 수행 |
| Flutter `historyItems`/`chainDetail` 프로바이더에 `.stream()` 사용 | nested embed 미지원 — `Future` 프로바이더만 사용 |
| Flutter `historyItems`/`chainDetail`을 `QueueItems`처럼 클래스 기반 Notifier로 구현 | 쓰기 동작이 없는 순수 읽기 화면 — 불필요한 과설계(YAGNI) |
| Chain 상세의 Review 노드에 `ContextStickyBar`/`_DynamicContextStickyBar` 재사용 | 이미 결정된 과거 기록에 재결정 유도 UI는 의미상 오류 |
| Chain 상세 페이지가 `ReviewPageContent`를 그대로 재사용(Story 5.1의 Queue 재사용 패턴을 그대로 답습) | `ReviewPageContent`는 트리거/재시도 로직을 포함 — Chain 상세는 이미 `completed`인 Review만 다룬다는 전제가 다름 |
| `outcomes` nested embed 결과를 단일 객체로 가정해 `.status` 직접 접근 | `decision_id`에 `UNIQUE` 제약 없음 — 배열로 반환됨(설계 결정 2) |
| 이 스토리에서 Ignore 결정 흐름에 `signals.status='archived'` 업데이트 코드 추가 | 알려진 갭으로 명시적으로 범위 밖 처리 — 별도 스토리로 |
| Memory Timeline 항목에 스와이프 삭제/드래그 재정렬/롱프레스 추가 | UX-DR18 + EXPERIENCE.md line 828(불변 레코드) |
| KST 변환에 타임존 라이브러리 도입 | Asia/Seoul 고정 UTC+9, DST 없음 — Story 5.1과 동일 판단 |

### 신규 / 수정 파일 목록

```
# Web 신규 파일
web/src/components/history/history-content.tsx              (NEW)
web/src/components/history/memory-timeline-item.tsx          (NEW)
web/src/components/history/archived-banner.tsx                (NEW)
web/src/components/history/chain-detail-content.tsx           (NEW)
web/src/components/home/review/review-sections.tsx             (NEW — research-review-content.tsx에서 추출)
web/src/app/(app)/history/chain/[signalId]/page.tsx            (NEW)
web/src/components/history/__tests__/history-content.test.tsx (NEW — 스펙 문서)

# Web 수정 파일
web/src/app/(app)/history/page.tsx                              (UPDATE — 스텁 → 실제 구현)
web/src/lib/kst.ts                                              (UPDATE — 월/카드 날짜 포맷 헬퍼 추가)
web/src/components/home/review/research-review-content.tsx     (UPDATE — 섹션 렌더링을 review-sections.tsx로 위임)

# Flutter 신규 파일
mobile/lib/features/history/providers/history_provider.dart      (NEW)
mobile/lib/features/history/providers/chain_detail_provider.dart (NEW)
mobile/lib/features/history/widgets/memory_timeline_item.dart    (NEW)
mobile/lib/features/history/widgets/archived_banner.dart          (NEW)
mobile/lib/features/history/screens/chain_detail_screen.dart      (NEW)
mobile/lib/features/home/widgets/review_sections.dart              (NEW — research_review_screen.dart에서 추출)
mobile/test/history_test.dart                                      (NEW)

# Flutter 수정 파일
mobile/lib/features/history/screens/history_screen.dart           (UPDATE — 스텁 → 실제 구현)
mobile/lib/features/home/screens/research_review_screen.dart       (UPDATE — 섹션 빌드를 review_sections.dart로 위임)
mobile/lib/core/router/app_router.dart                              (UPDATE — /history 브랜치에 chain/:signalId 중첩 라우트 추가)

# 변경 없음 (확인만)
web/src/components/layout/bottom-nav.tsx                            (이미 /history 탭 존재, startsWith 매칭으로 하위 경로 자동 활성화)
```

### References

- 에픽: `_bmad-output/planning-artifacts/epics.md` — Story 5.2 AC 원문(line 785-815), Epic 5 개요(line 752-754)
- 아키텍처: `ARCHITECTURE-SPINE.md` — AD-3(데이터 접근 소유권), AD-9(RLS 패턴), AD-4(JSONB 봉투)
- UX: `ux-decision-os-2026-07-21/EXPERIENCE.md` line 357-375(Memory Timeline Item 행동 스펙), line 402·773(Ignore→archived 스펙, 알려진 갭의 근거), line 444-445(History States — Decision당 1항목 해석의 근거), line 601-709(접근성 — 44px tap target, dual-encoding 요구사항), line 828(불변 레코드 원칙)
- DB 스키마: `_bmad-output/implementation-artifacts/db/001_initial_schema.sql` — `reviews`(line 61-91), `decisions`(line 94-106), `outcomes`(line 109-120, `UNIQUE` 없음 확인), `signals`(line 154-164, RLS 비활성화 확인), RLS 정책(line 296-317)
- 재사용 패턴: `web/src/app/(app)/home/review/[signalId]/outcome/page.tsx`(순차 조회 모델), `web/src/components/home/outcome/outcome-card.tsx`(`OUTCOME_OPTIONS` 라벨 매핑), `web/src/components/home/review/honest-box.tsx`(배너 셸 모델), `web/src/lib/kst.ts` + `mobile/lib/features/queue/providers/queue_provider.dart`(KST 헬퍼, Story 5.1), `mobile/lib/features/home/providers/daily_brief_provider.dart`(Future vs Stream), `mobile/lib/core/router/app_router.dart`(중첩 라우트 구조)
- 이전 스토리: `_bmad-output/implementation-artifacts/5-1-queue-탭.md` — 이 스토리 파일의 형식/컨벤션 모델, KST 유틸(`kst.ts`/`_kstDateStr`) 최초 도입처, "알려진 갭" 문서화 방식, 낙관적 업데이트 패턴(이 스토리에서는 불필요함을 대조 확인하는 데 사용)

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (BMad dev-story 워크플로우)

### Debug Log References

- **Web 타입체크**: `npx tsc --noEmit` → 신규/변경 파일 0 오류. (기존 이슈 `home/review/[signalId]/chat/page.tsx`의 `PromiseLike.catch` 오류는 이 스토리 범위 밖 사전 존재 이슈로 유지)
- **Supabase 타입 `never` 이슈**: 생성된 DB 타입이 없어 `signals`/`decisions`/`outcomes` select 결과가 `never`로 추론됨 → `home/page.tsx` 컨벤션대로 `as unknown as {...}` 명시 캐스팅으로 해결(chain `page.tsx`).
- **Flutter 코드 생성**: `dart run build_runner build --delete-conflicting-outputs` → `history_provider.g.dart`, `chain_detail_provider.g.dart` 등 8개 output 생성. (기존 `test/profile_test.dart` 구문 오류는 사전 존재 이슈로 무관)
- **Flutter analyze**: 신규/변경 파일(`lib/features/history/**`, `review_sections.dart`, `app_router.dart`) 0 오류. (전체 `lib`의 유일 error 는 사전 존재 `profile_screen.dart`의 `AppSettings.openNotificationSettings` — Story 5.1에서 문서화된 범위 밖 이슈)
- **Flutter 테스트**: `flutter test test/history_test.dart` → 11/11 통과. 회귀 확인 `queue_test`/`home_screen_test`/`theme_test`/`widget_test` → 34/34 통과(review_sections 추출·라우터 변경 무회귀). `navigation_shell_test`는 사전 존재 profile 컴파일 오류로 실패(이 스토리 무관).
- **데이터 레이어 검증 (Supabase MCP, live DB)**: (1) `outcomes.decision_id` UNIQUE 제약 0건 확인 → 1:N 최신 1건 처리(설계 결정 2) 타당. (2) PostgREST nested-embed 의존 FK 전부 존재: `decisions.review_id→reviews`, `reviews.signal_id→signals`(`fk_reviews_signal`), `outcomes.decision_id→decisions`. (3) 쿼리가 참조하는 컬럼명 전부 실제 스키마와 일치(decisions/reviews/outcomes/signals). (4) **문서 불일치 발견**: Dev Notes는 "signals RLS 비활성"이라 기술했으나 live DB는 `signals` RLS **enabled** + `signals_select` 정책 `auth.uid() IS NOT NULL` 존재 → 실질 효과(로그인 사용자 전체 signals 조회 가능)는 동일하므로 **코드 정상 동작, 문서만 정정 필요**.
- **라이브 브라우저 테스트 (puppeteer + 실제 Chrome, 로그인→히스토리→Chain 상세, 시드 데이터 주입 후)**:
  - ✅ 히스토리 리스트: 5개 항목, 월 구분선(2026년 7월/6월), 도트 4종+미완료(→/?/✓/QUEUE·IGNORE 검정), 라벨/날짜 전부 정상 렌더.
  - ❌→✅ **회귀급 버그 발견·수정 (RSC 경계)**: Chain 상세가 `TypeError: OUTCOME_OPTIONS.find is not a function`으로 500 크래시. 원인 — `outcome-card.tsx`가 `"use client"`라 거기서 export한 `OUTCOME_OPTIONS`를 **Server Component**(`chain-detail-content.tsx`)에서 import하면 client reference 프록시가 되어 배열 메서드 호출 실패(리스트는 `history-content.tsx`가 client라 정상이었음). **수정**: `OUTCOME_OPTIONS`/`OutcomeStatus`를 client 경계 밖 plain 모듈 `outcome-options.ts`로 분리, `outcome-card.tsx`는 재-export(하위호환), 서버측 소비자(memory-timeline-item/chain-detail-content 등)는 plain 모듈에서 import. 수정 후 재실행 → Chain 상세(Applied/보관됨) 정상 렌더, "보관된 REVIEW" 배너·12섹션·Decision·Outcome 노드 확인, 콘솔/HTTP 4xx·5xx 0건.
  - ⚠️ **별개 사전 존재 버그(이 스토리 무관, Story 1.5 영역)**: 웹은 `/onboarding` 라우트가 없어(`GET /onboarding = 404`), signin/signup이 `onboarding_completed=false` 사용자를 `router.push("/onboarding")` 하면 로그인 직후 404. `yousk6347@gmail.com` 계정이 이 케이스였음(테스트용으로 `onboarding_completed=true` 처리해 언블록). 웹 온보딩 화면 구현 필요 — 별도 스토리 권장.

### Completion Notes List

- **전 범위 읽기 전용**: 신규 API/마이그레이션 없음. Web은 Server Component 직접 조회, Flutter는 `Future`+nested-embed 프로바이더(`.stream()` 미사용, 클래스 Notifier 미사용 — YAGNI 준수).
- **설계 결정 1 (Decision당 1항목 + 도트 전환)**: `resolveDotStyle` — outcome 기록 시 Outcome 스타일, `learn_now`+미기록 시 outcome-pending("?"), `queue`/`ignore`는 영구 Decision 스타일. Web(`history-content.tsx`)/Flutter(`memory_timeline_item.dart`) 동일 규칙.
- **설계 결정 2 (Outcome 1:N)**: nested-embed 배열을 `created_at` 내림차순 정렬 후 최신 1건만 사용(Web `page.tsx` / Flutter `history_provider.dart` / chain 4단계 순차 조회 모두).
- **설계 결정 3 (보관 배너)**: `honest-box` 셸 재사용, `surface-card-alt` bg + `text-secondary` 3px 좌측 보더(중립 정보 톤). Web `archived-banner.tsx` / Flutter `archived_banner.dart`.
- **순수 추출 리팩터링(Task 6/13)**: 12섹션+HonestBox를 Web `review-sections.tsx` / Flutter `review_sections.dart` 공용 컴포넌트로 이동. 뒤로가기/타이틀/Chat/StickyBar 제외. Flutter는 gating용 `sectionKeys`/`focusNodes`를 옵셔널 파라미터로 받아 Home 동작 보존(회귀 테스트 통과). Web은 `ReviewPayload`를 `research-review-content.tsx`에서 재-export해 기존 import 경로 유지.
- **공용 도트 위젯(Task 16.3)**: Flutter `TimelineDot`(+`TimelineDot.forStyle`)을 `memory_timeline_item.dart`에 두고 `chain_detail_screen.dart`에서 재사용. Signal/Review 노드는 중립 `text-secondary` 도트.
- **알려진 갭 준수**: `signals.status='archived'` 쓰기 경로는 추가하지 않음(읽기 전용 방어 로직만 구현). Chain 상세에 재결정 UI(ContextStickyBar) 미포함.
- **경미한 편차**: Flutter의 outcome 라벨 매핑(`kOutcomeEnglishLabel`/`kOutcomeKoreanLabel`)은 `outcome_screen.dart`의 `_kOutcomeOptions`가 private이라 재사용 불가 → `memory_timeline_item.dart`에 동일 문자열로 정의(Web은 `OUTCOME_OPTIONS`를 직접 import해 재사용).

### File List

**Web 신규**
- `web/src/components/history/history-content.tsx`
- `web/src/components/history/memory-timeline-item.tsx`
- `web/src/components/history/archived-banner.tsx`
- `web/src/components/history/chain-detail-content.tsx`
- `web/src/components/home/review/review-sections.tsx`
- `web/src/components/home/outcome/outcome-options.ts` (RSC 경계 버그 수정 — `OUTCOME_OPTIONS`/`OutcomeStatus` client 경계 밖 분리)
- `web/src/app/(app)/history/chain/[signalId]/page.tsx`
- `web/src/components/history/__tests__/history-content.test.tsx`

**Web 수정**
- `web/src/app/(app)/history/page.tsx`
- `web/src/lib/kst.ts`
- `web/src/components/home/review/research-review-content.tsx`
- `web/src/components/home/outcome/outcome-card.tsx` (상수 분리 후 재-export, 하위호환 유지)

**Flutter 신규**
- `mobile/lib/features/history/providers/history_provider.dart` (+ `.g.dart` 생성)
- `mobile/lib/features/history/providers/chain_detail_provider.dart` (+ `.g.dart` 생성)
- `mobile/lib/features/history/widgets/memory_timeline_item.dart`
- `mobile/lib/features/history/widgets/archived_banner.dart`
- `mobile/lib/features/history/screens/chain_detail_screen.dart`
- `mobile/lib/features/home/widgets/review_sections.dart`
- `mobile/test/history_test.dart`

**Flutter 수정**
- `mobile/lib/features/history/screens/history_screen.dart`
- `mobile/lib/features/home/screens/research_review_screen.dart`
- `mobile/lib/core/router/app_router.dart`

### Review Findings

_코드 리뷰(bmad-code-review, 2026-07-28) — Blind Hunter + Edge Case Hunter + Acceptance Auditor 3-레이어. 전 항목 소스 코드로 재현 가능성 검증 완료._

- [x] [Review][Patch] `outcome-card.tsx`의 `OUTCOME_OPTIONS` 재-export 트랩 제거 (2026-07-28 적용) — `outcome-card.tsx`에서 `export { OUTCOME_OPTIONS }`/`export type { OutcomeStatus }` 재-export 삭제(값은 plain `outcome-options.ts`에서만 직접 import하도록 주석 강화), 유일 소비자 `home/review/[signalId]/outcome/page.tsx`의 import를 `outcome-options.ts`로 이전. `npx tsc --noEmit` 무오류(기존 chat/page.tsx 이슈 제외).
- [x] [Review][Defer] Chain 상세가 `signalId`만으로 "최신 completed review → 최신 decision"을 재해석 — 한 signal에 완료된 review/decision이 복수면 리스트에서 탭한 항목과 다른 체인이 표시됨 [history-content.tsx:75 / chain/[signalId]/page.tsx:29-53] — deferred, 스펙 설계 귀결(AC-4가 `/history/chain/:signalId` 라우트, Task 8.1이 "최신 해석" 명시) + 도달 조건 좁음(동일 signal on-demand 재-리뷰 후 재결정 필요) + 올바른 수정(decisionId 딥링크)은 웹 라우트·Flutter 중첩 라우트·양쪽 provider를 바꾸는 스펙 계약 확장이라 별도 스토리 적합. (source: blind+edge, severity: medium)
- [x] [Review][Defer] review payload 내부 필드 무방어 접근 — 부분/불완전 payload 시 SSR 500 [web/src/components/home/review/review-sections.tsx:59,70,123] — deferred, pre-existing (`research-review-content.tsx`에서 순수 추출된 로직, Home Review 경로가 동일 코드로 이미 렌더 중. payload는 reviewer 에이전트가 고정 스키마로 생성 + `chk_result_envelope` 제약. Chain 상세가 신규 소비자로 추가된 점만 새로움)
- [x] [Review][Defer] `estimated_hours` 표기 크로스플랫폼 불일치 — Web은 raw(`2.5시간`), Flutter는 `toStringAsFixed(0)` 반올림(`3시간`) [web review-sections.tsx:62 vs mobile review_sections.dart] — deferred, pre-existing (양측 모두 추출 전 기존 동작 보존)
- [x] [Review][Defer] Flutter `reference_sources` 링크 `onTap: () {}` no-op 죽은 어포던스 (Web은 새 탭 오픈) [mobile/lib/features/home/widgets/review_sections.dart] — deferred, pre-existing (추출 전 동작 보존)
- [x] [Review][Defer] `outcome.useful` 필드를 web/Flutter 모델 끝까지 운반하나 렌더링하지 않음(죽은 필드) [web chain-detail-content.tsx:14, mobile chain_detail_provider.dart] — deferred, minor cleanup

_Dismissed as noise (15): 메인 리스트 미기록 Outcome type label `"IN PROGRESS"`(리스트 배지가 전부 영문 대문자라 패턴상 자연스럽고 의미 명확 — 리뷰 시 사용자 확정), enum unknown-value 크래시들(outcomes.status / decisions.choice — DB CHECK 제약으로 도달 불가), malformed timestamp parse(created_at NOT NULL), Flutter null 하드캐스트(NOT NULL 컬럼), `actual_learning_time_min as int?`(INTEGER 컬럼), reviews 배열 캐스트(to-one embed), outcome sort tie 비결정성(created_at NOT NULL·코스메틱), `String(value)` [object Object](현 스키마 미도달), RLS user_id 미필터(AD-3/AD-9 by-design·정책 검증됨), web 테스트 실행 불가(러너 부재 컨벤션·문서용), Flutter 라우팅 테스트 약함, `formatMonthDivider` NaN(내부 전용), Flutter outcome 라벨 재정의(문서화된 정당한 편차), sticky-bar 대소문자 nit(text-badge가 CSS로 uppercase)._

## Change Log

| 날짜 | 변경 내용 |
|------|----------|
| 2026-07-27 | Story 5.2 생성 (create-story 워크플로우) — Epic 5 두 번째 스토리. |
| 2026-07-27 | Story 5.2 구현 완료 (dev-story) — Web/Flutter History 메인 리스트 + Chain 상세 + review 섹션 공용 추출. Web tsc 무오류, Flutter analyze 무오류(신규 파일), history 테스트 11/11 + 회귀 34/34 통과. Status → review. |
| 2026-07-27 | 라이브 브라우저 테스트에서 Chain 상세 500 크래시(RSC 경계: `OUTCOME_OPTIONS`가 client 모듈 export라 Server Component 에서 프록시화) 발견·수정 — `outcome-options.ts` plain 모듈 분리. 수정 후 로그인→리스트→Chain 상세(Applied/보관됨) 전 흐름 정상 확인. (별개로 웹 `/onboarding` 404 사전 존재 버그 문서화 — 이 스토리 무관.) |
| 2026-07-28 | 코드 리뷰(bmad-code-review, 3-레이어) 완료 — 2 decision-needed(①Chain divergence→defer, ②"IN PROGRESS" 라벨→dismiss), 1 patch(outcome-card 재-export 트랩 제거·tsc 무오류) 적용, 4→5 defer, 15 dismiss. Status review → done. |
