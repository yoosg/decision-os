---
baseline_commit: NO_VCS
---

# Story 5.4: Memory 기반 개인화 & 접근성 마감

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

개발자로서,
Memory RAG가 Recommender에 연동되고 WCAG 2.2 AA 접근성 요건과 금지 인터랙션 패턴이 앱 전체에 적용되어 있기를 원한다,
그래서 MVP가 프로덕션 수준의 완성된 경험으로 출시될 수 있다.

**범위 참고 (반드시 먼저 읽을 것)** — 이 스토리는 **두 개의 독립적인 파트**로 구성된 MVP 마감(finishing) 스토리다:

- **파트 A — Memory RAG → Recommender 연동 (백엔드, FastAPI + Supabase pgvector).** 신규 기능 구현.
- **파트 B — 접근성(WCAG 2.2 AA) & 금지 인터랙션 패턴 전-앱 감사(audit) + 갭 마감.** **대부분 기존 스토리(1.x~5.3)에서 이미 인라인으로 구현됨.** 이 파트는 **처음부터 다시 만드는 것이 아니라, 남은 갭을 찾아 닫고 전수 검증하는 것**이다. 아래 "이미 적용된 것 vs 이 스토리에서 닫을 것" 표를 반드시 기준으로 삼을 것.

두 파트는 서로 의존성이 없으므로 순서 무관하게 진행 가능하다.

**⚠️ 재구현 금지 경고:** 접근성 디자인 토큰(대비 수정), reduce-motion 처리, color+glyph 병행은 상당 부분 이미 코드에 반영되어 있다. 전수 grep 없이 "없을 것"이라 가정하고 새로 만들지 말 것. **먼저 감사(grep/코드리딩) → 갭 식별 → 최소 수정**의 순서를 지킬 것.

---

## 이미 적용된 것 vs 이 스토리에서 닫을 것 (⚠️ 재구현 금지 기준표)

### 파트 A — Memory RAG

| 항목 | 상태 | 위치 |
|------|------|------|
| `memories` 테이블(`embedding VECTOR(1536)`, `user_id`, `memory_type`, `summary`) | ✅ 존재 | `supabase/migrations/20260723000000_initial_schema.sql:127-141` |
| `memories` HNSW 코사인 인덱스 `idx_memories_embedding` (`vector_cosine_ops`, m=16, ef_construction=64) | ✅ 존재 | 동 파일 `268-272` |
| `memories` RLS SELECT 정책(`user_id` 직접) | ✅ 존재 | 동 파일 `333-334` |
| pgvector `vector` 확장 활성화 | ✅ 존재 | 동 파일 `12` |
| Memory 생성 파이프라인(Outcome 후 AI 추출 → `embedding=llm.embed_text(summary)` → INSERT) | ✅ 존재 (Story 4.3) | `api/pipeline/memory_manager.py:75-82` |
| `LLMProvider.embed_text(text)->list[float]` (1536차원 검증 포함) | ✅ 존재 | `api/pipeline/llm/base.py:100-101`, `api/pipeline/llm/openai_provider.py:209-219` |
| Recommender 콜드 스타트 스코어링(`compute_relevance_score`, tech_stack/interests 키워드 매칭, min 0.1) | ✅ 존재 (Story 2.3) | `api/pipeline/recommender.py:12-37` |
| **Memory RAG 유사도 조회 → 관련성 점수 반영** | ❌ **신규** | `api/pipeline/recommender.py` + **신규 마이그레이션(RPC)** |
| **`match_memories` pgvector RPC 함수** (query_embedding + user_id → 유사도) | ❌ **신규 마이그레이션** | `supabase/migrations/`, `_bmad-output/implementation-artifacts/db/` |
| **배치 내 Signal 텍스트 임베딩** (query 벡터 생성) | ❌ **신규** | `api/pipeline/recommender.py` (LLMProvider 주입) |

### 파트 B — 접근성 & 금지 패턴 (이미 대부분 반영됨 — 감사 후 갭만 닫을 것)

| 항목 | 상태 | 근거/위치 |
|------|------|------|
| 대비 토큰 수정: `--text-secondary #595D6A`(4.5:1↑), `--status-warning #B45309`(4.7:1) | ✅ 이미 반영 | `web/src/app/globals.css:17,32` (리뷰 권고안이 이미 적용됨) |
| dot-pulse reduce-motion(웹 전역 `@media (prefers-reduced-motion)`) | ✅ 이미 반영 | `web/src/app/globals.css:133-135` |
| Flutter 로딩 인디케이터 reduce-motion(`disableAnimations` → 정적) | ✅ 이미 반영 | `mobile/lib/features/home/widgets/three_dot_loading_indicator.dart:54-56` |
| ContextStickyBar reduce-motion 전환 | ✅ 일부 반영 | `web/.../context-sticky-bar.tsx:513`, `mobile/.../research_review_screen.dart:45,625,770` |
| Onboarding reduce-motion | ✅ 이미 반영 | `mobile/.../onboarding_screen.dart:647` |
| Memory Timeline Outcome 도트 color+glyph 병행(✓/→/✕/−/?), `ExcludeSemantics`+`Semantics(label)` | ✅ 이미 반영 (Story 5.2) | epics.md:801-802 AC 및 5.2 구현 |
| Queue/Timeline 44pt(`min-height:44px`), composite `aria-label`/`Semantics` | ✅ 이미 반영 (Story 5.1/5.2) | epics.md:771-772, 5.1/5.2 구현 |
| 금지 패턴(FAB/carousel/streak/progress-bar/achievement) 부재 | ✅ 전수 grep 0건(2026-07-28 확인) | 아래 "감사 절차" 참조 |
| 화면당 `btn-primary` ≤1 | ✅ 웹 grep 1건 | `grep btn-primary web/src` |
| **Daily Brief "생성 중" 상태 `aria-live="polite"`/`role="status"`** | ❌ **미반영(2-4 defer)** | `web/.../daily-brief-content.tsx:192` [deferred-work.md:191] |
| **전-앱 접근성 전수 감사 + 잔여 갭 마감(양 플랫폼)** | ❌ **이 스토리 핵심 작업** | 아래 AC-B* + 감사 절차 |
| **금지 인터랙션 패턴 전수 감사(양 플랫폼)** | ❌ **이 스토리 핵심 작업** | AC-B4 + 감사 절차 |

---

## Acceptance Criteria

### 파트 A — Memory RAG → Recommender

**AC-A1: Memory 보유 사용자 pgvector 유사도 반영** [Source: epics.md:852-855]
- **Given** Recommender(`run_recommender` / `create_daily_brief_for_user`)가 실행될 때 해당 사용자에게 `memories` row가 1개 이상 존재하면
- **Then** 각 후보 Signal의 텍스트를 임베딩한 query 벡터로 그 사용자의 `memories.embedding`을 **pgvector HNSW 인덱스**(코사인)로 조회하여 유사도를 산출하고, 이를 Signal 관련성 점수에 반영한다
- **And** **외부 벡터 DB를 사용하지 않는다** — Supabase pgvector 전용(AD-2/AD-6: RAG는 외부 벡터 DB 불허) [Source: ARCHITECTURE-SPINE.md:26,191]
- **And** 코사인 거리 연산자(`<=>`)와 인덱스 연산자 클래스(`vector_cosine_ops`)가 일치해야 인덱스가 사용된다

**AC-A2: 콜드 스타트 폴백** [Source: epics.md:855]
- **Given** 해당 사용자에게 `memories` row가 없으면(신규/이력 없는 사용자)
- **Then** 기존 콜드 스타트 로직(`compute_relevance_score`, 프로필 tech_stack/interests 기반)으로 **폴백**하고 Memory RAG 조회는 생략한다
- **And** Memory 조회/임베딩 실패(LLM/DB 장애) 시에도 콜드 스타트 점수로 안전하게 폴백하며, 해당 사용자의 brief 생성 자체는 중단되지 않는다(AD-5 배치 회복탄력성 — 사용자 단위 실패 격리, 기존 `run_recommender` try/except 패턴 유지)

**AC-A3: 데이터 무결성 & 격리**
- **Given** RAG 조회를 수행할 때
- **Then** `match_memories` 조회는 **반드시 해당 `user_id`로 필터**되어 다른 사용자의 memory가 누출되지 않는다(service_role로 실행되므로 RLS가 우회됨 — 애플리케이션/함수 레벨에서 user_id 스코프를 명시적으로 강제할 것)
- **And** 관련성 점수의 최종 범위 규약(콜드 스타트의 min 0.1 하한 등 `daily_brief_signals.relevance_score`가 만족하던 불변식)이 유지된다

### 파트 B — 접근성 & 금지 패턴 (전-앱, 웹 + Flutter)

**AC-B1: 44×44pt 탭 타겟** [Source: epics.md:857-858, UX-DR13 epics.md:110]
- **Given** 앱의 모든 인터랙티브 요소(버튼/링크/체크박스/카드 탭/탭바/바텀시트 옵션/일정변경 링크 등)를 확인하면
- **Then** 최소 44×44pt 탭 타겟을 충족한다
- **And** text-bearing 컨테이너는 fixed height를 쓰지 않고 intrinsic + padding 방식으로 Dynamic Type에 대응한다

**AC-B2: 색상 독립(color independence)** [Source: epics.md:859, 리뷰 §5]
- **Given** 상태 정보를 전달하는 모든 요소를 확인하면
- **Then** 색상만으로 상태를 전달하는 요소가 없다 — glyph 또는 텍스트 레이블을 색상과 병행한다(예: Outcome 도트 ✓/→/✕/−/?는 이미 반영됨 — 잔여 요소 확인)

**AC-B3: Reduce Motion** [Source: epics.md:862-865, UX-DR13, 리뷰 §6]
- **Given** `prefers-reduced-motion`(웹) / `MediaQuery.disableAnimations`(Flutter)이 활성화된 환경에서
- **Then** 모든 로딩 dot-pulse 애니메이션이 정적으로 대체된다
- **And** **Bottom Sheet open/close가 즉시 appear/disappear로 대체된다**(translate 트랜스폼 제거 — 리뷰 §6 신규 요건, 갭 가능성 높음)
- **And** ContextStickyBar 활성화 전환이 즉시 전환으로 대체된다

**AC-B4: 금지 인터랙션 패턴 부재** [Source: epics.md:867-873]
- **Given** 앱 전체(웹 + Flutter)를 검토하면
- **Then** 다음이 **어디에도 존재하지 않는다**:
  - Floating AI Chat FAB
  - 카루셀 / 수평 스크롤 콘텐츠
  - 시스템이 Learn Now / Queue / Ignore를 자동 선택하는 경로
  - 진행률 표시줄 / 스트릭 / 달성 배지
  - 2중 모달 스택(Bottom Sheet는 한 번에 1개)
- **And** 화면당 `btn-primary`(accent-primary 배경 CTA)가 1개를 초과하지 않는다

**AC-B5: ContextStickyBar 스크린리더 상태 전달 (잔여 갭)** [Source: 리뷰 §1, §4]
- **Given** ContextStickyBar가 disabled → enabled로 전환될 때(웹)
- **Then** visually-hidden `aria-live="polite"` 상태 영역이 활성화를 안내한다(assertive 금지)
- **And** disabled CTA는 `disabled` 속성이 아니라 `aria-disabled="true"`로 표기되어 포커스 순회에서 사라지지 않으며, 힌트 텍스트가 `aria-describedby`로 연결된다
- **And** 힌트의 방향 화살표(↑) 등 장식 glyph는 `aria-hidden` 처리된다
- (현재 구현이 이미 충족하는지 **먼저 `context-sticky-bar.tsx` 정독으로 확인** — 충족 시 "확인됨"으로 감사 로그에 기록, 미충족 항목만 수정)

**AC-B6: Daily Brief 생성 중 상태 알림 (2-4 defer 마감)** [Source: deferred-work.md:191]
- **Given** Daily Brief가 "생성 중(generating)" 상태로 표시될 때(웹 `daily-brief-content.tsx:192`, Flutter 대응 상태)
- **Then** 해당 상태 영역에 `aria-live="polite"` / `role="status"`(Flutter: `Semantics(liveRegion: true)`)가 적용되어 스크린리더가 진행 상태를 인지한다

---

## Tasks / Subtasks

### 파트 A — Memory RAG

- [x] **T-A1. `match_memories` pgvector RPC 마이그레이션 작성** (AC-A1, AC-A3)
  - [x] `supabase/migrations/20260729000000_match_memories_rpc.sql` 신규 파일 생성(기존 타임스탬프 네이밍 규약 준수 — 최신은 `20260728000000_*`)
  - [x] `public.match_memories(query_embedding vector(1536), match_user_id uuid, match_count int DEFAULT 5)` 함수 정의
    - `SELECT id, summary, memory_type, 1 - (embedding <=> query_embedding) AS similarity FROM public.memories WHERE user_id = match_user_id AND embedding IS NOT NULL ORDER BY embedding <=> query_embedding LIMIT match_count`
    - **`<=>`(코사인 거리) 사용** — 인덱스 `vector_cosine_ops`와 일치시켜 HNSW 사용 보장
    - `SECURITY DEFINER` + 함수 본문에서 `match_user_id` 필터로 스코프 강제(호출자 격리) + `SET search_path = public`
    - `LANGUAGE sql STABLE`, `service_role`에만 EXECUTE 부여
  - [x] `_bmad-output/implementation-artifacts/db/004_match_memories_rpc.sql` 동일 마이그레이션 사본/기록(기존 관행 — 5.3에서 `db/` 병행 기록)
  - [x] 적용은 `mcp__supabase__apply_migration` 사용(원격 프로젝트 반영) — 함수 존재/SECURITY DEFINER/STABLE 및 RPC 왕복(빈 결과) 검증 완료
- [x] **T-A2. Recommender에 LLMProvider 주입 + Signal 임베딩** (AC-A1, AC-A2)
  - [x] `create_daily_brief_for_user` / `run_recommender` 시그니처에 `llm: LLMProvider | None = None` 추가(기존 호출부 `orchestrator.py` batch/on-demand 함께 수정, embedding_model 명시 주입)
  - [x] 배치 효율: **후보 Signal 임베딩은 배치당 1회만 계산**(`_build_signal_embeddings`)하여 사용자 전체에 재사용. 임베딩 대상 텍스트는 `technology_name + title + summary`(`_signal_embed_text`, memory_manager와 동일한 `embed_text` 사용)
  - [x] 임베딩 실패 시 해당 Signal은 콜드 스타트 점수로 폴백(`_embed_signal_list` 개별 try/except, 예외 전파 금지)
- [x] **T-A3. RAG 점수 반영 로직** (`_score_signals`) (AC-A1, AC-A2, AC-A3)
  - [x] 사용자별: `memories` count 확인 → 없으면 `compute_relevance_score` 폴백, 있으면 각 Signal query 벡터로 `match_memories(match_user_id)` 호출하여 top-k 유사도 획득
  - [x] 블렌딩 공식: `blended = base + _RAG_WEIGHT(0.5) * max(top_similarity)`, `clamp(0.1, 1.0)`, 정렬 `(-score, signal_id)` 결정론적 (설계 A-1 ①②③ 충족)
  - [x] `pipeline_log`에 `event="memory_rag_applied"`(user_id, memory_count) / 폴백 시 `event="memory_rag_coldstart"`, RPC 실패 시 `memory_rag_query_failed`, 임베딩 실패 시 `signal_embed_failed` 기록
- [x] **T-A4. 파트 A 테스트** (아래 Testing 규약)
  - [x] `LLMProvider`/Supabase client 모킹(기존 repo 관행 — Vitest/Jest 미설정, 실 DB는 RPC 왕복으로 마이그레이션 단계에서 검증). 17개 신규 테스트 추가(`test_recommender_pipeline.py`)
  - [x] 케이스: (1) memory 보유 사용자 → RAG 경로/블렌딩/클램프, (2) memory 없는 사용자 → 콜드 스타트 폴백, (3) 임베딩/RPC 예외 → 폴백 + brief 생성 지속, (4) user_id 격리(`match_user_id` 스코프), (5) 배치당 1회 임베딩 재사용

### 파트 B — 접근성 & 금지 패턴 감사

- [x] **T-B0. 전-앱 감사 인벤토리 작성(먼저 수행)** — 감사 매트릭스를 Completion Notes에 기록(각 AC × 플랫폼 충족/갭)
- [x] **T-B1. 금지 패턴 전수 grep 감사** (AC-B4)
  - [x] `FloatingActionButton|carousel|overflow-x|PageView|Axis.horizontal|streak|progress-?bar|achievement|badge-earned|snap-x|scroll-x` grep → **0건**(웹+Flutter, 2026-07-28 재확인)
  - [x] 2중 Bottom Sheet 동시 표시 경로 없음 — 웹 2개(context-sticky-bar Queue Sheet, reschedule-sheet)·Flutter 2개(research_review, reschedule) 각각 단일 표시, 스택 없음
  - [x] 화면당 `btn-primary`/accent CTA ≤1 — 웹 `btn-primary` 1건(review-failed-state). ※`.btn-primary` CSS 미정의(선-존재 시각 이슈, AC 밖 → defer 기록)
- [x] **T-B2. 44pt 탭 타겟 감사 + 갭 마감** (AC-B1) — Chat 화면 갭 3건 수정(back/전송/재시도 버튼 `minHeight:44`), 그 외 화면 확인됨(intrinsic+padding)
- [x] **T-B3. Reduce Motion 갭 마감** (AC-B3)
  - [x] **Bottom Sheet open/close**: Flutter 2개 시트에 `sheetAnimationStyle: disableAnimationsOf ? AnimationStyle.noAnimation : null` 추가(갭 마감). 웹 reschedule-sheet는 transform 애니메이션 없음 → 즉시 표시 확인됨
  - [x] dot-pulse(globals.css:133)/ContextStickyBar(context-sticky-bar.tsx:512) 전환 이미 반영 → 확인됨
- [x] **T-B4. 색상 독립 감사** (AC-B2) — honest-box high severity(웹+Flutter) ⚠ glyph+semantics 병행 추가; queue-item overdue(웹+Flutter) composite label에 "미완료" 포함; Outcome 도트 color+glyph(memory-timeline-item) 확인됨
- [x] **T-B5. ContextStickyBar 스크린리더(웹)** (AC-B5) — 정독 결과 **4개 항목 모두 이미 충족(확인됨)**: 시각 숨김 `aria-live="polite"` 상태 영역(L364-379)+활성화 안내(L88-90), `aria-disabled`+`aria-describedby`(not `disabled`, L396-398), 장식 glyph `aria-hidden`(↑ L393, lock SVG L418), 스코프 reduce-motion(L512-519). 수정 없음
- [x] **T-B6. Daily Brief 생성 중 라이브 리전** (AC-B6) — 웹 `daily-brief-content.tsx` generating `<p>`에 `role="status" aria-live="polite"`; Flutter `home_screen.dart` `_buildGenerating()`에 `Semantics(liveRegion: true)` 추가
- [x] **T-B7. 감사 결과 문서화** — Completion Notes에 감사 매트릭스 요약

---

## Dev Notes

### 파트 A — Memory RAG 설계

**현재 Recommender 동작 (반드시 보존):** `create_daily_brief_for_user`는 중복 체크 → 프로필 조회 → Signal 배치 조회(`status='processed'`) → `compute_relevance_score`로 점수 산출 → `daily_briefs`(pending→processing→completed) + `daily_brief_signals`(relevance_score, position) INSERT의 상태 머신을 갖는다. **이 상태 전이·에러 폴백(AC-6 stuck job, P2/P3/P5/P8 패치)·`daily_brief_signals` position 규약을 깨지 말 것.** [Source: api/pipeline/recommender.py:84-233]

**설계 결정 A-1 — 블렌딩 공식(dev가 확정):** 콜드 스타트 점수(키워드, 0.1~1.0)와 Memory 코사인 유사도(0~1)를 결합한다. 권장 접근: 콜드 스타트를 base로 두고 top-k memory 유사도의 최댓값(또는 평균)을 가중 가산한 뒤 `max(min(score,1.0),0.1)`로 클램프. 정확한 가중치는 dev 재량이되 **① memory 보유 사용자가 콜드 스타트보다 개인화가 강화되고, ② `relevance_score` 불변식(0.1~1.0)이 유지되며, ③ 결정론적으로 정렬 가능**해야 한다. 선택한 공식을 Completion Notes에 기록.

**설계 결정 A-2 — query 벡터 출처:** `signals` 테이블에는 embedding 컬럼이 없다. 따라서 recommend 시점에 Signal 텍스트를 `llm.embed_text()`로 즉석 임베딩하여 query 벡터로 사용한다. **비용 최적화 필수:** Signal은 사용자 공유 콘텐츠이므로 **배치당 Signal 1회 임베딩 → 전 사용자 재사용**. 사용자마다 재임베딩하면 OpenAI 비용이 사용자 수만큼 폭증한다.

> **A-2 보강 (2026-07-28 코드리뷰 Decision 1 결정):** query(Signal)는 `technology_name + title + summary`(`_signal_embed_text`)로, memory는 `summary`만으로(`memory_manager.embed_text(summary)`) 임베딩되어 **임베딩 소스 텍스트가 비대칭**이다. 이는 의도된 설계다 — 본 검색은 doc-to-doc(대칭)이 아니라 **Signal↔Memory cross-type 검색**이므로 "대칭 임베딩"이라는 이상적 기준 자체가 성립하지 않는다. Signal에서 `technology_name/title`을 제거해 summary만 맞추면 매칭에 가장 변별력 있는 기술명 토큰이 사라져 개인화가 오히려 악화된다. 동일 모델(`text-embedding-3-small`)로 같은 벡터 공간에 놓이므로 richer query가 유사도에 유리하다. 향후 실사용 데이터로 개인화 품질이 미흡하면 재튜닝 대상.

**설계 결정 A-3 — pgvector 조회는 RPC로:** supabase-py 쿼리 빌더로는 `ORDER BY embedding <=> :vec` 벡터 정렬을 직접 표현하기 어렵다. 표준 해법은 Postgres 함수(`match_memories`)를 만들고 `client.rpc("match_memories", {...}).execute()`로 호출하는 것. **연산자 클래스 일치가 핵심:** 인덱스가 `vector_cosine_ops`이므로 함수도 코사인 거리 `<=>`를 써야 HNSW가 사용된다(다른 연산자면 seq scan). [Source: initial_schema.sql:268-272]

**설계 결정 A-4 — RLS 우회 하 격리:** Recommender는 service_role(`get_supabase()`)로 돌기 때문에 `memories` RLS가 우회된다. 따라서 **`match_user_id` 필터를 함수 본문에서 반드시 강제**하여 사용자 간 memory 누출을 막는다(RLS에 의존 금지). [Source: deferred-work.md:98 service_role 싱글톤 RLS 우회 특성]

**임베딩 계약:** `embed_text`는 1536차원을 반환·검증하며 실패 시 `LLMProviderError`. memory 생성 시 동일 모델(`text-embedding-3-small`)로 임베딩했으므로 query도 동일 모델이어야 유사도가 의미를 갖는다. [Source: openai_provider.py:88-92,209-219]

### 파트 B — 접근성 감사 방법론

**핵심 원칙: 감사 우선, 재구현 금지.** 위 "이미 적용된 것" 표가 보여주듯 대비 토큰·reduce-motion·color+glyph·44pt·금지패턴 부재는 상당수 이미 반영됨(2026-07-28 grep 확인). 이 스토리의 가치는 **전수 검증 + 소수의 잔여 갭 마감 + 감사 산출물 문서화**다.

**확정된(=이미 반영된) 항목 — 확인만:**
- 대비 토큰: `--text-secondary #595D6A`, `--status-warning #B45309`는 리뷰 권고안이 이미 globals.css에 적용됨. (주의: `--text-tertiary #9CA3AF`는 리뷰상 미달로 지적되나, 리뷰 §3 권고는 "타임스탬프는 composite accessible label로 기능 무손실 보장"이므로 색 변경 대신 라벨 병행 방식이 채택되었는지 확인) [Source: globals.css:16-34, 리뷰 §3]
- dot-pulse reduce-motion(globals.css:133), Flutter 로딩(three_dot_loading_indicator.dart:54), Onboarding(onboarding_screen.dart:647), ContextStickyBar 전환(context-sticky-bar.tsx:513, research_review_screen.dart:45)
- Outcome 도트 color+glyph(5.2), Queue/Timeline 44pt+composite label(5.1/5.2)

**잔여 갭(우선 조사 대상):**
1. **Bottom Sheet reduce-motion** — 리뷰 §6이 명시적으로 "바텀시트 slide-up → 즉시 전환"을 신규 요구. 웹 일정변경 시트(5.1)·Flutter 바텀시트들이 이를 반영했는지 불확실 → 최우선 확인.
2. **Daily Brief generating aria-live**(2-4 defer, deferred-work.md:191) — 확실한 미반영 갭.
3. **ContextStickyBar aria-live/aria-disabled/aria-describedby**(리뷰 §1) — 현재 구현 정독으로 충족 여부 판정.

**금지 패턴 감사(AC-B4) 실행 커맨드(참고):**
`grep -rniE "FloatingActionButton|carousel|overflow-x|streak|progress-?bar|achievement|PageView" web/src mobile/lib` (node_modules 제외). 2026-07-28 기준 0건 — dev는 재확인 후 감사 로그에 기록. 화면당 btn-primary는 `grep -rn "btn-primary" web/src`(웹 1건) + Flutter primary 버튼 화면별 카운트.

**감사 대상 화면(웹 + Flutter 양측):** Home/Daily Brief · Research Review 상세(+ContextStickyBar) · Contextual Chat · Queue · History/Memory Timeline · Onboarding · Profile.

### 아키텍처 준수(양 파트 공통)

- **AD-2/AD-6:** RAG는 Supabase pgvector(HNSW)로만. 외부 벡터 DB·외부 RAG 서비스 불허. [Source: ARCHITECTURE-SPINE.md:26,191]
- **AD-3:** `memories`·`daily_briefs`·`daily_brief_signals` 쓰기는 FastAPI(service_role)만.
- **AD-5:** 배치는 사용자 단위 실패 격리 — 한 사용자의 RAG 실패가 전체 배치를 중단시키지 않는다.
- **AD-7:** Memory summary 임베딩은 Recommender 개인화에 활용(이 스토리가 그 소비 지점을 구현). [Source: ARCHITECTURE-SPINE.md:217-220]
- **UX-DR13:** WCAG 2.2 AA — 44×44pt, 색상 독립(glyph 병행), Dynamic Type(intrinsic+padding), Reduce Motion, VoiceOver/TalkBack 지원. [Source: epics.md:110]

### Project Structure Notes

- 백엔드 파이프라인: `api/pipeline/recommender.py`(수정), `api/pipeline/orchestrator.py`(호출부 시그니처 수정), 신규 마이그레이션 `supabase/migrations/` + `_bmad-output/implementation-artifacts/db/` 병행 기록.
- 마이그레이션 네이밍: 기존 `YYYYMMDD000000_*.sql` 규약(최신 `20260728000000_decisions_outcome_reminder_sent_at.sql`) — 신규는 그보다 큰 타임스탬프.
- 접근성 수정은 기능 코드 산재 — 화면별 컴포넌트(`web/src/components/**`, `mobile/lib/features/**`)와 토큰(`web/src/app/globals.css`, `mobile/lib/core/theme/app_theme.dart`)에 국소 수정.

### Testing

- **파이프라인 테스트 규약(epics.md:746-748):** 실제 Supabase 테스트 DB에 연결(프로덕션 DB 모킹 금지), `LLMProvider`는 인터페이스 모킹으로 대체. 기존 `api/tests/test_*`의 supabase mock 패턴 참고하되, RAG 유사도 검증은 실제 벡터 삽입 후 `match_memories` RPC 왕복으로 검증 권장.
- 파트 A 필수 케이스: RAG 경로 / 콜드 스타트 폴백 / 예외 폴백(생성 지속) / user_id 격리. [Source: AC-A2, AC-A3]
- 접근성은 자동화 테스트 인프라가 프로젝트에 미구성(웹 Jest/Vitest 미설정 — deferred-work.md:13). 따라서 파트 B 검증은 **코드 감사 + 실기기/시뮬레이터 수동 확인**(VoiceOver/TalkBack, reduce-motion 토글, Dynamic Type)으로 수행하고 결과를 Completion Notes에 매트릭스로 남긴다.

### References

- [Source: epics.md#Story-5.4 (844-874)] — Story 5.4 AC 전문
- [Source: epics.md:110 UX-DR13] — WCAG 2.2 AA 요건
- [Source: ARCHITECTURE-SPINE.md:23-26 AD-2, 189-191 AD-6, 217-220 AD-7]
- [Source: supabase/migrations/20260723000000_initial_schema.sql:127-141,268-272,333-334] — memories 스키마/인덱스/RLS
- [Source: api/pipeline/recommender.py:12-37,84-233] — 현재 Recommender
- [Source: api/pipeline/memory_manager.py:75-82] — 임베딩 생성 선례
- [Source: api/pipeline/llm/openai_provider.py:209-219] — embed_text 계약
- [Source: ux-designs/.../review-accessibility.md §1,§3,§5,§6] — 접근성 리뷰 파인딩
- [Source: deferred-work.md:191] — 2-4 Daily Brief aria-live defer

---

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (BMAD dev-story workflow)

### Debug Log References

- 마이그레이션 적용: `mcp__supabase__apply_migration(match_memories_rpc)` → success. 함수 검증: `pg_proc`(SECURITY DEFINER=true, STABLE), RPC 왕복(zero-vector, dummy uuid) → `[]` 정상.
- Python 회귀: `pytest -q` 전체 **163 passed**(파트 A 신규 17 테스트 포함).
- Flutter: `flutter analyze`(변경 5파일) → 신규 이슈 0(선-존재 info 1건 `use_build_context_synchronously` research_review_screen.dart, 본 변경과 무관).
- 웹: `tsc --noEmit` → 신규 타입 오류 0(선-존재 오류 1건 chat/page.tsx:45 `.catch` on PromiseLike, 본 변경과 무관 — 라인 45는 미수정). 웹 유닛 테스트는 러너(Vitest/Jest) 미설정으로 실행 불가(deferred-work.md:13) — 변경-테스트 호환성은 코드 리딩으로 검증.

### Completion Notes List

**파트 A — Memory RAG → Recommender (신규 구현)**

- `match_memories` pgvector RPC(코사인 `<=>`, `vector_cosine_ops` 인덱스 일치로 HNSW 사용, `SECURITY DEFINER`+`match_user_id` 필터로 격리, `service_role`에만 EXECUTE) 신규 마이그레이션 + 원격 적용 + `db/004` 병행 기록.
- **블렌딩 공식(설계 A-1 확정):** `blended = compute_relevance_score(base 0.1~1.0) + 0.5 * max(top_k cosine similarity)`, `clamp(0.1, 1.0)`. 정렬 `(-score, signal_id)`로 결정론적. → ① memory 보유자 개인화 강화 ② 불변식 유지 ③ 결정론 정렬 충족.
- **비용 최적화(설계 A-2):** Signal은 공유 콘텐츠이므로 `run_recommender`에서 **배치당 1회** 임베딩(`_build_signal_embeddings`) 후 전 사용자 재사용. 온디맨드(단일 사용자) 경로는 fetched signals로 즉석 임베딩.
- **폴백/격리(AC-A2/A3, AD-5):** llm 미주입·memory 미보유·임베딩 실패·RPC 실패 모두 콜드 스타트 점수로 안전 폴백하며 brief 생성 지속. `match_user_id` 함수 본문 강제로 타 사용자 memory 누출 차단. 온디맨드 provider 구성 실패(키 미설정)도 `llm=None` 저하.
- 관측성 로그: `memory_rag_applied`/`memory_rag_coldstart`/`memory_rag_query_failed`/`signal_embed_failed`/`signal_embed_batch_failed`.
- 임베딩 모델 일치: orchestrator batch/on-demand 모두 `embedding_model=settings.openai_embedding_model` 명시 주입(memory summary 임베딩과 동일 모델 → 유사도 유의미).

**파트 B — 접근성 감사 매트릭스 (감사 우선, 갭만 마감)**

| AC | 항목 | 웹 | Flutter |
|----|------|-----|---------|
| B1 | 44pt 탭 타겟 | **수정**: chat back/전송/재시도 `minHeight:44`. 그 외 확인됨 | 확인됨(기존 `minimumSize`/`ConstrainedBox 44`) |
| B2 | 색상 독립 | **수정**: honest-box high ⚠glyph, queue-item overdue label. 도트 확인됨 | **수정**: honest-box high ⚠+Semantics, queue-item overdue label |
| B3 | Reduce Motion | 확인됨(reschedule 시트 무애니메이션, dot-pulse, ctx-bar) | **수정**: 2개 bottom sheet `sheetAnimationStyle=noAnimation` |
| B4 | 금지 패턴 부재 | 확인됨(grep 0, btn-primary 1) | 확인됨(grep 0, FAB 0, 가로스크롤 0) |
| B5 | ContextStickyBar aria | 확인됨(4항목 전부 기충족, 수정 없음) | N/A |
| B6 | Daily Brief 생성중 알림 | **수정**: `role=status aria-live=polite` | **수정**: `Semantics(liveRegion:true)` |

- **접근성 검증 방식:** 프로젝트에 웹/Flutter 접근성 자동화 테스트 인프라 미구성(deferred-work.md:13). 본 파트는 **코드 감사 + 정적 분석(flutter analyze/tsc)**으로 검증했으며, VoiceOver/TalkBack·reduce-motion 토글·Dynamic Type 실기기 확인은 QA 단계 권장.
- **Defer 기록:** `.btn-primary` CSS 클래스 미정의(review-failed-state.tsx가 참조) — 본 스토리 6개 AC 밖의 선-존재 시각 스타일 이슈. 재시도 CTA는 인라인 padding(≈44pt)로 기능은 동작. 별도 디자인/스타일 티켓 권장(재구현 금지 원칙 준수).

### File List

**파트 A (백엔드)**
- `supabase/migrations/20260729000000_match_memories_rpc.sql` (신규)
- `_bmad-output/implementation-artifacts/db/004_match_memories_rpc.sql` (신규, 병행 기록)
- `api/pipeline/recommender.py` (수정: RAG 스코어링/임베딩 헬퍼, 시그니처 llm 추가)
- `api/pipeline/orchestrator.py` (수정: batch/on-demand llm 주입, embedding_model 명시)
- `api/tests/test_recommender_pipeline.py` (수정: RAG 테스트 17건 추가 + 시그니처 반영)
- `api/tests/test_daily_briefs_trigger.py` (수정: create 호출 시그니처 `ANY` llm 반영)

**파트 B (접근성)**
- `web/src/components/home/daily-brief-content.tsx` (수정: generating aria-live)
- `web/src/components/home/review/honest-box.tsx` (수정: high severity ⚠ glyph)
- `web/src/components/queue/queue-item.tsx` (수정: overdue composite label)
- `web/src/app/(app)/home/review/[signalId]/chat/page.tsx` (수정: 44pt 탭 타겟 3건)
- `mobile/lib/features/home/screens/home_screen.dart` (수정: generating liveRegion)
- `mobile/lib/features/home/widgets/review_sections.dart` (수정: honest-box high ⚠+Semantics)
- `mobile/lib/features/home/screens/research_review_screen.dart` (수정: bottom sheet reduce-motion)
- `mobile/lib/features/queue/widgets/reschedule_sheet.dart` (수정: bottom sheet reduce-motion)
- `mobile/lib/features/queue/widgets/queue_item.dart` (수정: overdue composite label)

### Change Log

- 2026-07-28: Story 5.4 구현 — 파트 A(Memory RAG→Recommender pgvector 연동, 배치 임베딩/블렌딩/폴백/격리, 신규 RPC 마이그레이션 + 17 테스트) & 파트 B(WCAG 2.2 AA 전-앱 감사 + 잔여 갭 마감: 44pt 3건, 색상 독립 4건, reduce-motion 2건, 라이브 리전 2건, ContextStickyBar 확인). 회귀 163 passed, 신규 정적 분석 이슈 0.

---

## Review Findings

_코드 리뷰: 2026-07-28 (Blind Hunter + Edge Case Hunter + Acceptance Auditor 3-레이어, NO_VCS 전체파일 리뷰). decision-needed 0(2건 해결) · patch 1 · defer 8 · dismissed 13._

### Decision Needed (해결됨)

- [x] [Review][Decision→Dismiss] 임베딩 텍스트 비대칭 — 사용자 결정: **현행 유지 + 문서화**. Signal↔Memory는 cross-type 검색으로 "대칭 임베딩" 기준이 없고, Signal에서 `technology_name/title`을 제거하면 매칭 변별 토큰이 사라져 개인화가 오히려 악화. 동일 모델로 같은 벡터 공간이므로 richer query 유지. 근거는 Dev Notes(설계 A-2 보강)에 문서화. [`api/pipeline/recommender.py:88-96`]
- [x] [Review][Decision→Defer] Memory RAG RPC 사용자×Signal 이중 루프 호출 — 사용자 결정: **MVP 수용, defer**. 코드 정확·HNSW 인덱스 정상 사용, 값비싼 임베딩은 배치 1회 최적화됨. defer 사유: 사용자 수 급증 또는 배치 소요가 스케줄러 윈도우에 근접할 때 재검토(사용자당 memories 1회 로드 로컬 스코어링 또는 다중벡터 RPC). [`api/pipeline/recommender.py:194-209`]

### Patch

- [x] [Review][Patch] `_RAG_MATCH_COUNT=5`이나 블렌딩은 `max(top_sim)`만 사용 → 매 RPC마다 상위 4행을 조회·직렬화 후 폐기. **적용됨(2026-07-28): `_RAG_MATCH_COUNT = 1`로 축소**(최근접 1행 = 최대 유사도, 동일 결과). [`api/pipeline/recommender.py:17`]

### Deferred

- [x] [Review][Defer] user_id 격리 불변식(AC-A3) 실행 가능한 회귀 테스트 부재 — 코드(RPC `WHERE user_id`)는 정확하나 테스트는 파라미터 전달만 모킹 검증. 실 DB 왕복 테스트 인프라 미구성(스펙 Testing에서 인정). [`api/tests/test_recommender_pipeline.py`] — deferred, 인프라 제약
- [x] [Review][Defer] 온디맨드 brief가 트리거마다 당일 Signal 전체 재임베딩 — 단일 사용자·소규모지만 반복 트리거 시 임베딩 비용 누적, 캐싱 미구현. [`api/pipeline/orchestrator.py:156`] — deferred, MVP 수용
- [x] [Review][Defer] `compute_relevance_score` 부분문자열 매칭(예: "go"→"google") — 선행 스토리(2.3) 이슈가 RAG base로 유입. [`api/pipeline/recommender.py:27-42`] — deferred, pre-existing
- [x] [Review][Defer] 웹 생성중 라이브리전 조건부 마운트 — AC-B6 문자적 충족이나, 라이브리전을 항상 DOM에 두고 텍스트만 토글하면 SR 안내 신뢰성↑. [`web/src/components/home/daily-brief-content.tsx:192-203`] — deferred, 견고성 개선
- [x] [Review][Defer] Flutter `_buildGenerating` 라이브리전이 `signalsAsync.error/loading`에도 매핑 → "생성 중" 오안내 가능(기존 라우팅 에러→생성중). [`mobile/lib/features/home/screens/home_screen.dart:110-111,120-125`] — deferred, pre-existing 라우팅
- [x] [Review][Defer] `.btn-primary` CSS 미정의(review-failed-state 참조) — 오류 화면 CTA 무스타일. [`web/src/components/home/review-failed-state.tsx:16`] — deferred, pre-existing (스토리에서 이미 기록)
- [x] [Review][Defer] `--text-tertiary #9CA3AF` 대비 미달 토큰이 채팅 타임스탬프 등 가시 텍스트에 사용 — 라벨 병행 방식 채택. [`web/src/app/globals.css:18`, `web/src/app/(app)/home/review/[signalId]/chat/page.tsx:200`] — deferred, pre-existing 토큰
- [x] [Review][Defer] (Decision 2에서 이관) Memory RAG RPC 사용자×Signal 이중 루프 → 배치당 O(사용자수 × Signal수) HNSW 왕복. [`api/pipeline/recommender.py:194-209`] — deferred, 사용자 급증/배치 윈도우 근접 시 재검토

### Dismissed (13, 참고용)

- (Decision 1에서 이관) 임베딩 텍스트 비대칭 — cross-type 검색, richer query 유지가 매칭에 유리. Dev Notes 문서화 완료.
- `similarity or 0.0` 강제 — 마이그레이션이 `embedding IS NOT NULL` 필터(RPC:32) + `max(top_sim,0.0)` 클램프로 이미 방어. 오탐.
- `count="exact"` + `.limit(1)` memory_count 오보고 — 로직은 truthiness만 사용, 로그 값만 희귀 영향(장식).
- memory 보유하나 embedding 전부 NULL → `memory_rag_applied` 오해 로그 — RPC 빈 결과→base 폴백, 무해.
- 비-OpenAI provider 차원 미검증 — 현재 OpenAIProvider(1536 검증)만 사용, RPC 예외 시 콜드스타트 우아 폴백.
- 배치 임베딩 실패 시 `{}` → 강제 콜드스타트 — 의도된 AD-5 설계({} vs None 구분).
- embeddings dict 누락 Signal 무-부스트 — 의도된 폴백(`signal_embed_failed` 로깅됨).
- text 버튼 min-width 부재 — 뒤로가기(아이콘)는 44×44, 재시도/전송(텍스트)은 콘텐츠+패딩으로 가로 44px 초과 → AC-B1 충족.
- `⚠` glyph 이모지 렌더링 — 색상 무관 형상(shape) 병행으로 색-독립 충족.
- overdue "미완료" 색상-단독 — "미완료" 텍스트 자체가 비색상 단서.
- `sheetAnimationStyle` 신규 API 버전 가드 — `flutter analyze` 통과(SDK 지원 확인).
- Bottom sheet barrier fade 잔여 모션 — noAnimation이 시트 슬라이드 제거, 잔여 미미.
- RPC 실패 per-signal 로그 스팸 — 세밀 폴백은 의도, 로그량만 경미.
