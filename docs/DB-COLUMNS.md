# Decision OS — 테이블 컬럼 레퍼런스 (Database Columns)

> 각 테이블의 **핵심 컬럼과 의미**를 정리한 문서. 라이브 스키마(Supabase public) 기준.
> 테이블 역할·관계도(ERD)는 [`IMPLEMENTATION-STATUS.md`](./IMPLEMENTATION-STATUS.md),
> 동작 흐름은 [`HOW-IT-WORKS.md`](./HOW-IT-WORKS.md) 참고.
>
> 최종 갱신: 2026-07-31

- `created_at` / `updated_at`(생성·수정 시각)은 대부분 테이블 공통이라 표에서 생략한다.
- **CHECK** = DB가 강제하는 값 집합(enum). **FK** = 외래키. **PK** = 기본키.
- 상태머신 컬럼은 모두 `pending → processing → completed | failed` 패턴.

---

## 신원 · 계정 레이어

### `user_profiles` — 사용자 프로필
| 컬럼 | 의미 |
|---|---|
| `id` | PK 겸 `auth.users.id` FK (계정과 1:1) |
| `display_name` | 표시 이름 (≤256자) |
| `role` | 역할 (frontend/backend/ai_engineer/pm/designer/student/other) |
| `experience_level` | 경험 (beginner/intermediate/advanced) |
| `tech_stack` | 기술 스택 배열(text[]) |
| `project_goal` | 프로젝트 목표 |
| `interests` | 관심 영역 배열(text[]) |
| `daily_learning_time_min` | 하루 학습 시간(분) |
| `onboarding_completed` | 온보딩 완료 여부(bool) — **라우팅 게이트**(false면 온보딩으로) |

> `role`~`interests`는 **추천 개인화의 입력값**(리뷰·추천기가 읽음).

### `user_devices` — 푸시 기기
| 컬럼 | 의미 |
|---|---|
| `user_id` | 소유 사용자 FK |
| `fcm_token` | 푸시 발송용 토큰 |
| `platform` | web / ios / android (CHECK) |

---

## 공통 Decision Loop (플레이북 무관)

### `projects` — 플레이북 컨테이너
| 컬럼 | 의미 |
|---|---|
| `user_id` | 소유자 FK |
| `playbook_type` | **도메인 분기점** (현재 `ai_research`만; 보험 붙으면 `insurance`) |
| `name` | 프로젝트 이름(예: "내 AI 학습") |

### `reviews` — AI 리뷰
| 컬럼 | 의미 |
|---|---|
| `project_id` / `signal_id` | 소속 프로젝트 / 대상 시그널 FK (signal_id nullable) |
| `playbook_type` / `review_type` | 도메인·리뷰 종류 판별자(`ai_research` / `research`) |
| `status` | pending → processing → completed / failed (CHECK, 상태머신) |
| `bar_gate_override` | "지금 학습" 버튼 강제 켜기/끄기 (force_enable / force_disable, nullable) |
| `context_snapshot` | **입력 스냅샷** JSONB 봉투 `{schema_version, review_type, payload}` (당시 signal+프로필) |
| `result` | **LLM 결과** JSONB 봉투 (13개 섹션) |
| `error_message` / `processing_started_at` / `completed_at` | 실패 사유 / 처리 시작·완료 시각 |

### `decisions` — 사용자 결정
| 컬럼 | 의미 |
|---|---|
| `review_id` | 대상 리뷰 FK — **UNIQUE(리뷰당 결정 1개)** |
| `choice` | learn_now(지금 학습) / queue(나중에·보관) / ignore(관심없음) (CHECK) |
| `queue_timing` | queue일 때만: today / this_week / later (nullable) |
| `memo` | 결정 시 남긴 메모 |
| `outcome_reminder_sent_at` | 결과 기록 리마인더 발송 시각(중복 발송 방지) |

> `choice=learn_now` → `learning_paths` 생성 트리거. **`outcomes`는 이때 생기지 않고**, 사용자가 학습 후 "결과 기록"을 해야 생성된다(그전까지 히스토리에서 "미완료").
> `queue`/`ignore`는 learning_path·outcome 모두 생성하지 않는다.

### `outcomes` — 학습 결과 (사용자가 직접 기록)
| 컬럼 | 의미 |
|---|---|
| `decision_id` | 대상 결정 FK |
| `status` | completed(완료) / applied(적용함) / dropped(그만둠) / not_useful(도움안됨) (CHECK) |
| `useful` | 유용했나(bool, nullable) |
| `actual_learning_time_min` | 실제 학습 시간(분) |
| `applied_project_note` | 어디에 적용했는지 메모 |
| `memo` | 자유 메모 |

### `memories` — 개인화 기억
| 컬럼 | 의미 |
|---|---|
| `user_id` | 소유자 FK |
| `memory_type` | preference / skill / project / decision_history / outcome_history (CHECK) |
| `summary` | LLM이 뽑은 **한 줄 요약** |
| `embedding` | **벡터(pgvector)** — `match_memories` RAG 검색 대상 |
| `source_decision_id` | 어느 결정에서 파생됐나(FK, nullable) |

### `activities` — 프로젝트 활동 로그 (확장용, 현재 미사용)
| 컬럼 | 의미 |
|---|---|
| `project_id` | 소속 프로젝트 FK |
| `activity_type` / `payload` | 활동 종류 / 상세 JSONB |

---

## AI Research 전용 (콘텐츠 · 파이프라인)

### `signals` — 콘텐츠 원천(기술 소식)
| 컬럼 | 의미 |
|---|---|
| `technology_name` | 기술명(=클러스터 라벨). normalize 그룹핑 키 |
| `title` / `summary` | 제목·요약 (signal_builder가 LLM으로 생성; summary nullable) |
| `signal_date` | 시그널 날짜(date) — `technology_name + signal_date` **UNIQUE** |
| `status` | raw → processed → archived (CHECK, 상태머신) |
| `published_at` | 원문 최신 발행 시각 → **랭킹 최신성** |
| `popularity` | 인기(클러스터 멤버 합) → 랭킹 |
| `source_authority` | 출처 권위 0~4(smallint) → 랭킹 |
| `cluster_key` | 클러스터 **결정론적 식별키**(재실행 안정성) |

### `signal_sources` — 시그널 출처 링크
| 컬럼 | 의미 |
|---|---|
| `signal_id` | 소속 시그널 FK |
| `source_type` | official_blog / github / reddit / hn / youtube / other (CHECK) |
| `url` / `title` | 원문 링크 / 원문 제목 |

### `daily_briefs` — 오늘의 브리핑 컨테이너
| 컬럼 | 의미 |
|---|---|
| `user_id` / `brief_date` | 소유자 / 브리핑 날짜(사용자·날짜당 1개) |
| `status` | pending → processing → completed / failed (CHECK) |
| `generated_at` / `processing_started_at` | 완료 시각 / 처리 시작(stuck 감지용) |
| `error_message` | 실패 사유 |

### `daily_brief_signals` — 브리핑↔시그널 연결 (복합 PK)
| 컬럼 | 의미 |
|---|---|
| `daily_brief_id` + `signal_id` | 복합 기본키(어느 브리핑에 어느 시그널) |
| `relevance_score` | 추천 점수(combined, 0.1~1.0) |
| `position` | 노출 순서(1부터) — 홈이 이 순서로 표시 |

### `learning_paths` — 학습 자료 (learn_now 결정 시 생성)
| 컬럼 | 의미 |
|---|---|
| `decision_id` | 대상 결정 FK (choice=learn_now인 결정에서만 생성) |
| `signal_id` | 대상 시그널 FK |
| `resources` | 학습 자료 **정확히 5개** 배열(JSONB) — LLM(`coach`)이 생성, 정해진 type 순서 검증 |
| `status` | pending → processing → completed / failed (CHECK, 상태머신) |
| `error_message` / `processing_started_at` | 실패 사유 / 처리 시작 시각 |

> "지금 학습" → `decisions(learn_now)` → 이 테이블 pending 생성 후 BackgroundTask로 자료 생성. 보험 플레이북에서는 이 역할을 "서류 Checklist"가 대체한다.

### `engagement_events` — 행동 로깅(측정)
| 컬럼 | 의미 |
|---|---|
| `user_id` / `signal_id` / `daily_brief_id` | 누가 / 무엇을 / 어느 브리핑 맥락(daily_brief_id nullable) |
| `event_type` | impression(노출) / open(열람) / read_through(끝까지 읽음) / decision(결정) (CHECK) |
| `variant` | rag / coldstart (nullable) — **추천 코호트**(A/B 측정) |
| `metadata` | position, relevance_score 등 부가정보(JSONB) |
