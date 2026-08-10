# 작업 B 2단계 — 학습 경로 구조 안내 (Learning Path Structure)

- 날짜: 2026-08-10
- 브랜치: `feat/learning-path-structure` (베이스: `feat/learning-link-verification` = 1단계, PR #1 미머지)
- 관련: [[signal-quality-roadmap]] 작업 B 2단계, 1단계=링크 검증

## 문제

학습 경로 화면은 고정 5개 리소스(공식문서 → 핵심자료 → GitHub → 실습예제 → 적용아이디어)를
**평평한 링크 목록**으로만 보여준다. 학습자가 "이 경로로 결국 뭘 향해 가는지(목표)", "각 단계에서
무엇을 배우는지"를 알 수 없어 방향감이 없다.

## 목표

평평한 5개 링크 나열을 **목표가 있는 번호별 학습 여정**으로 보여준다.

- ① 경로 목표(path goal) — 이 경로로 달성하는 것
- ② 번호가 매겨진 단계(numbered steps) — 이미 순서가 고정된 5개를 ①~⑤로
- ③ 각 단계 "무엇을 배우나"(objective)

문구는 **AI가 사용자 역할/프로젝트 목표에 맞춰 생성**(고정 템플릿 아님).

## 설계

### 1) 데이터 계약 — LLM 출력 확장

`LEARNING_PATH_SYSTEM_PROMPT`(`api/pipeline/llm/prompts.py`)를 확장한다.

```jsonc
{
  "goal": "이 경로로 무엇을 달성하는지 1~2문장 (사용자 역할/프로젝트 목표 반영, 한국어)",
  "resources": [
    { "type": "official_docs",    "title": "...", "url": "https://...", "descriptor": "...",
      "objective": "이 단계에서 무엇을 배우나 (짧게, 한국어)" },
    { "type": "core_material",    "title": "...", "url": "https://...", "descriptor": "...", "objective": "..." },
    { "type": "github",           "title": "...", "url": "https://github.com/...", "descriptor": "...", "objective": "..." },
    { "type": "practice_example", "title": "...", "url": "https://...", "descriptor": "...", "objective": "..." },
    { "type": "applied_idea",     "title": "...", "url": "", "descriptor": "...", "objective": "..." }
  ]
}
```

리소스 5개 순서·type 고정 규칙은 그대로 유지한다.

### 2) 저장 — 마이그레이션 없음

- `goal` → **기존 `learning_paths.goal` 컬럼**(text, nullable, 이미 존재하나 현재 미사용)에 기록.
- `objective` → `resources` JSONB 배열 항목 안에 그대로 저장(추가 키).
- DB 스키마 변경 없음. 기존 13개 row는 `goal=null`, `objective` 없음 → 하위호환 유지.

`api/pipeline/coach.py::_execute_learning_path_pipeline`:
- 파싱한 payload에서 `goal = payload.get("goal")` 추출.
- `completed` 업데이트에 `goal`을 함께 기록하되, 비어있지 않은 문자열일 때만 기록(빈 값이면 컬럼 null 유지).
- `resources`는 지금처럼 저장(objective 키가 자연히 포함됨).

### 3) 검증 / 에러 처리 — best-effort 강화

핵심 제약: `parse_and_validate_learning_path` 실패 시 **재시도 없이** `LLMProviderError` →
coach가 잡아 경로를 `failed`로 전이. 서버는 gemini 무료티어 429 이슈도 있으므로,
새 필드를 하드 필수로 만들면 신뢰도가 떨어진다.

따라서:
- `parse_and_validate_learning_path`의 **기존 하드 규칙 유지**: resources 5개, type 순서
  (coach 쪽 `LEARNING_PATH_RESOURCE_TYPES` 검증), 필수 키(type/title/url/descriptor), url 스킴.
- **새 필드 `goal`/`objective`는 하드 필수로 넣지 않는다.** 빠져도 경로 생성은 성공, 있으면 화면에 표시.
  (즉 `_LEARNING_PATH_RESOURCE_KEYS`에 `objective`를 강제 추가하지 않는다 — subset 검증이 깨지지 않도록.)

### 4) ⚠️ 1단계와의 상호작용 — objective 보존

1단계 `api/pipeline/link_verifier.py::verify_and_fix_links`가 리소스 dict를 재구성하며
`objective` 같은 미지정 키를 **떨어뜨리지 않는지** 반드시 확인/보존해야 한다.
- 구현 시 `link_verifier`가 원본 dict를 복사(shallow copy) 후 url 관련 키만 갱신하도록 하여
  `objective`를 포함한 모든 키가 보존되게 한다.
- 테스트로 "objective가 있는 리소스가 링크 교체 후에도 objective를 유지"함을 고정한다.

### 5) 화면 — 타임라인 스템퍼 + 목표 배너

`web/src/app/(app)/home/review/[signalId]/learning-path/page.tsx`
`web/src/components/home/learning-path/learning-path-card.tsx`

- **목표 배너**: `goal`이 있으면 상단에 "이 경로의 목표" 라벨 + 목표 문구 카드. 없으면 렌더 안 함.
- **타임라인 스템퍼**: 5개 카드를 왼쪽 번호 원 ①~⑤ + 세로 연결선(마지막 단계 제외)으로 감싼다.
  - 번호 = 렌더 인덱스 + 1(리소스 순서 고정이므로 안정적).
- **objective**: 카드 안에 `objective`가 있으면 "이 단계에서: …" 한 줄 추가(없으면 생략).
- **쿼리**: `learning_paths` select에 `goal` 컬럼 추가
  (`resolveAndStart`의 초기 조회, `subscribe`의 재확인/`fetchAndApplyCompleted` 조회 모두).
  - `UIState`의 `ready`에 `goal?: string` 추가.
- 타입: `LearningPathResource`에 `objective?: string` 추가.
- **시각 정체성**: 무채색 유지(새 팔레트 금지). 연결선/번호 원은 `var(--border-subtle)`,
  `var(--text-secondary)` 등 기존 토큰 사용.
- **하위호환**: 기존 row(goal null, objective 없음)는 배너·objective 줄만 숨고 카드 목록은 그대로 동작.

## 테스트

- **백엔드(pytest)**:
  - `parse_and_validate_learning_path`: goal/objective **있는** 응답 통과, **없는** 응답도 통과(하드 필수 아님),
    기존 규칙(5개/type/url 스킴) 위반은 여전히 실패.
  - `coach`: payload에 goal 있으면 `goal` 컬럼 기록, 빈 값이면 null 유지(MockLLMProvider 응답 확장).
  - `link_verifier`: objective가 있는 리소스가 링크 교체(죽은 링크) 후에도 objective 보존.
  - `api/tests/mocks.py::MockLLMProvider.generate_learning_path`에 goal + objective 포함하도록 갱신.
- **프론트엔드**: 웹 테스트러너 없음(vitest 바이너리만 존재) → `tsc` 타입 통과로 검증.
  Playwright 스크린샷으로 스템퍼/배너 시각 비평(무채색 확인). 데모 시드/스크린샷은 마지막에 삭제.

## 범위 밖 (YAGNI)

- 실제 학습 진행률/단계 체크박스
- objective/goal 인라인 편집
- 목표 재생성 버튼
- 5개 고정 리소스 구조 자체의 변경(개수·type)

## 요약 (변경 파일)

- `api/pipeline/llm/prompts.py` — 프롬프트에 goal/objective 추가, 검증은 best-effort 유지
- `api/pipeline/coach.py` — goal 컬럼 기록
- `api/pipeline/link_verifier.py` — objective 등 미지정 키 보존(복사 방식 점검)
- `api/tests/mocks.py` + 신규/기존 테스트
- `web/.../learning-path/page.tsx` — goal select, UIState.ready.goal, 배너, 스템퍼 래핑
- `web/.../learning-path/learning-path-card.tsx` — objective 줄, 번호 원/연결선
