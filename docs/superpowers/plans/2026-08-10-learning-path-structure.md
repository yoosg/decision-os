# 학습 경로 구조 안내 (작업 B 2단계) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 학습 경로 화면을 평평한 5개 링크 목록에서, AI가 생성한 경로 목표 + 번호별 단계 + 단계별 "무엇을 배우나"가 있는 타임라인 여정으로 바꾼다.

**Architecture:** LLM 출력 계약에 top-level `goal`과 리소스별 `objective`를 추가한다(둘 다 best-effort — 없어도 경로 생성 성공). `goal`은 이미 존재하는 `learning_paths.goal` 컬럼에 저장(마이그레이션 없음), `objective`는 `resources` JSONB 항목 안에 포함. 화면은 목표 배너 + 번호 원/연결선 타임라인 스템퍼로 렌더한다.

**Tech Stack:** Python(FastAPI, pytest) 백엔드 · Next.js 16 + React 19(TypeScript, tsc 타입체크) 프론트 · Supabase(Postgres/Realtime).

## Global Constraints

- 브랜치: `feat/learning-path-structure` (베이스 `feat/learning-link-verification` = 1단계). 이미 생성·체크아웃됨.
- 리소스는 5개 고정, type 순서 불변: `official_docs, core_material, github, practice_example, applied_idea`.
- 새 필드 `goal`/`objective`는 **하드 필수 아님**: 검증 실패 사유로 삼지 않는다(모델이 빼먹어도 경로는 성공, 있으면 표시).
- DB 스키마 변경 없음(`learning_paths.goal` text nullable 컬럼 재사용).
- 시각: 무채색 정체성 유지, 새 팔레트 금지. 기존 CSS 변수(`--border-subtle`, `--text-secondary`, `--surface-card` 등)만 사용.
- 백엔드 테스트: `api/` 디렉터리에서 `python -m pytest`. 프론트 검증: `web/` 에서 `npx tsc --noEmit`(웹 테스트러너 없음).
- 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

### Task 1: LLM 계약 확장 (프롬프트 + 검증 leniency + Mock)

`goal`/`objective`를 프롬프트에 추가하고, 검증이 이들을 하드 필수로 요구하지 않음을 테스트로 고정한다. 공유 Mock에도 새 필드를 반영한다.

**Files:**
- Modify: `api/pipeline/llm/prompts.py` (`LEARNING_PATH_SYSTEM_PROMPT` 문자열; `parse_and_validate_learning_path`는 코드 변경 없음)
- Modify: `api/tests/mocks.py` (`VALID_LEARNING_PATH_RESPONSE`)
- Test: `api/tests/test_llm_prompts_shared.py`

**Interfaces:**
- Consumes: 없음(첫 태스크).
- Produces:
  - `VALID_LEARNING_PATH_RESPONSE` (mocks.py) = JSON 문자열, 이제 top-level `"goal"` 키 + 각 resource에 `"objective"` 키 포함. resource[4](applied_idea)의 goal은 여전히 `"url": ""`.
  - `LEARNING_PATH_SYSTEM_PROMPT` 는 `"goal"` 과 `"objective"` 단어를 포함.
  - `parse_and_validate_learning_path(raw: str) -> None` 동작 불변: goal/objective 유무와 무관하게, 5개·type키·url스킴 규칙만으로 통과/실패.

- [ ] **Step 1: 검증 leniency + 프롬프트 문구 테스트 작성 (실패 확인용)**

`api/tests/test_llm_prompts_shared.py` 끝에 추가:

```python
def test_parse_and_validate_learning_path_accepts_goal_and_objective():
    import json
    from pipeline.llm.prompts import parse_and_validate_learning_path
    raw = json.dumps({
        "goal": "vLLM로 로컬 LLM 서빙을 직접 띄워본다",
        "resources": [
            {"type": "official_docs", "title": "T", "url": "https://a.dev", "descriptor": "d", "objective": "설치 감잡기"},
            {"type": "core_material", "title": "T", "url": "https://a.dev", "descriptor": "d", "objective": "핵심 개념"},
            {"type": "github", "title": "T", "url": "https://github.com/x/y", "descriptor": "d", "objective": "예제 읽기"},
            {"type": "practice_example", "title": "T", "url": "https://a.dev", "descriptor": "d", "objective": "따라하기"},
            {"type": "applied_idea", "title": "T", "url": "", "descriptor": "d", "objective": "내 프로젝트 적용"},
        ],
    })
    parse_and_validate_learning_path(raw)  # 예외 없이 통과해야 함


def test_parse_and_validate_learning_path_accepts_missing_goal_and_objective():
    """goal/objective가 없어도(하위호환/모델 누락) 검증은 통과해야 한다(best-effort)."""
    import json
    from pipeline.llm.prompts import parse_and_validate_learning_path
    raw = json.dumps({
        "resources": [
            {"type": "official_docs", "title": "T", "url": "https://a.dev", "descriptor": "d"},
            {"type": "core_material", "title": "T", "url": "https://a.dev", "descriptor": "d"},
            {"type": "github", "title": "T", "url": "https://github.com/x/y", "descriptor": "d"},
            {"type": "practice_example", "title": "T", "url": "https://a.dev", "descriptor": "d"},
            {"type": "applied_idea", "title": "T", "url": "", "descriptor": "d"},
        ],
    })
    parse_and_validate_learning_path(raw)  # 예외 없이 통과해야 함


def test_learning_path_prompt_mentions_goal_and_objective():
    from pipeline.llm.prompts import LEARNING_PATH_SYSTEM_PROMPT
    assert "goal" in LEARNING_PATH_SYSTEM_PROMPT
    assert "objective" in LEARNING_PATH_SYSTEM_PROMPT
```

- [ ] **Step 2: 테스트 실행 → prompt 테스트만 실패 확인**

Run: `cd api && python -m pytest tests/test_llm_prompts_shared.py -v`
Expected: `test_learning_path_prompt_mentions_goal_and_objective` FAIL(프롬프트에 아직 goal/objective 없음). 나머지 두 개는 이미 PASS(검증이 원래 관대함 — 이 둘은 회귀 방지용 고정).

- [ ] **Step 3: 프롬프트에 goal/objective 추가**

`api/pipeline/llm/prompts.py`의 `LEARNING_PATH_SYSTEM_PROMPT`를 아래로 교체:

```python
LEARNING_PATH_SYSTEM_PROMPT = """당신은 AI 기술 학습 전문가입니다. 주어진 기술 Signal에 대한 Learning Path를 JSON 형식으로 작성하세요.
반드시 다음 형식을 따르는 JSON 객체만 반환하세요:
{
  "goal": "이 학습 경로로 사용자가 무엇을 달성하는지 1~2문장. 사용자 역할/기술스택/프로젝트 목표를 반영해 구체적으로.",
  "resources": [
    {"type": "official_docs",    "title": "공식 문서 제목", "url": "https://...", "descriptor": "간단한 설명", "objective": "이 단계에서 무엇을 배우는지 한 줄(한국어)"},
    {"type": "core_material",    "title": "핵심 자료 제목", "url": "https://...", "descriptor": "간단한 설명", "objective": "이 단계에서 무엇을 배우는지 한 줄"},
    {"type": "github",           "title": "GitHub 레포/예제 제목", "url": "https://github.com/...", "descriptor": "간단한 설명", "objective": "이 단계에서 무엇을 배우는지 한 줄"},
    {"type": "practice_example", "title": "실습 예제 제목", "url": "https://...", "descriptor": "간단한 설명", "objective": "이 단계에서 무엇을 배우는지 한 줄"},
    {"type": "applied_idea",     "title": "적용 아이디어 제목", "url": "", "descriptor": "사용자 프로젝트 목표 기반 구체적 적용 아이디어", "objective": "이 단계에서 무엇을 배우는지 한 줄"}
  ]
}
순서를 변경하지 마세요. goal과 각 objective는 반드시 채우세요. 마크다운 없이 JSON만 반환하세요."""
```

- [ ] **Step 4: Mock 응답에 goal/objective 추가**

`api/tests/mocks.py`의 `VALID_LEARNING_PATH_RESPONSE`를 아래로 교체:

```python
VALID_LEARNING_PATH_RESPONSE = json.dumps({
    "goal": "LangGraph로 상태 기반 에이전트 워크플로를 직접 구성해본다",
    "resources": [
        {"type": "official_docs", "title": "공식 문서", "url": "https://example.com/docs", "descriptor": "설명", "objective": "설치와 기본 구조 감잡기"},
        {"type": "core_material", "title": "핵심 자료", "url": "https://example.com/core", "descriptor": "설명", "objective": "핵심 개념 이해"},
        {"type": "github", "title": "GitHub", "url": "https://github.com/example", "descriptor": "설명", "objective": "실제 예제 코드 읽기"},
        {"type": "practice_example", "title": "실습 예제", "url": "https://example.com/practice", "descriptor": "설명", "objective": "직접 따라 만들기"},
        {"type": "applied_idea", "title": "적용 아이디어", "url": "", "descriptor": "개인화된 적용 아이디어", "objective": "내 프로젝트에 적용 구상"},
    ],
})
```

- [ ] **Step 5: 테스트 실행 → 전체 PASS 확인**

Run: `cd api && python -m pytest tests/test_llm_prompts_shared.py -v`
Expected: 신규 3개 포함 모두 PASS.

- [ ] **Step 6: 커밋**

```bash
git add api/pipeline/llm/prompts.py api/tests/mocks.py api/tests/test_llm_prompts_shared.py
git commit -m "feat(coach): 학습 경로 프롬프트에 goal+objective 추가 (best-effort 검증)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: coach가 goal 컬럼에 기록

파이프라인이 LLM payload의 `goal`을 `learning_paths.goal` 컬럼에 저장한다(비어있으면 저장 안 함).

**Files:**
- Modify: `api/pipeline/coach.py` (`_execute_learning_path_pipeline`의 completed 업데이트)
- Test: `api/tests/test_learning_paths.py`

**Interfaces:**
- Consumes: `MockLLMProvider` (goal 포함 `VALID_LEARNING_PATH_RESPONSE` — Task 1).
- Produces: completed 시점 `learning_paths` update dict가 `goal` 키를 포함(payload의 goal이 비어있지 않은 str일 때만). resources 저장 동작은 불변.

- [ ] **Step 1: goal 기록 테스트 작성**

`api/tests/test_learning_paths.py`의 `test_execute_learning_path_pipeline_completes` 마지막 assert 아래(같은 함수 끝)에 추가:

```python
    # goal 컬럼에 LLM payload의 goal이 기록된다 (작업 B 2단계)
    assert completed_update.get("goal") == "LangGraph로 상태 기반 에이전트 워크플로를 직접 구성해본다"
```

그리고 파일 끝에 빈 goal은 기록하지 않음을 검증하는 테스트 추가:

```python
def test_execute_learning_path_pipeline_omits_empty_goal(monkeypatch):
    """LLM payload의 goal이 빈 문자열이면 goal 컬럼을 기록하지 않는다."""
    import json
    from tests.mocks import MockLLMProvider, VALID_LEARNING_PATH_RESPONSE
    from pipeline import coach as coach_mod
    monkeypatch.setattr(coach_mod, "verify_and_fix_links", lambda resources, *a, **k: resources)

    payload = json.loads(VALID_LEARNING_PATH_RESPONSE)
    payload["goal"] = ""
    empty_goal_response = json.dumps(payload)

    mock_client = MagicMock()
    update_data: list[dict] = []

    def table_side_effect(table_name):
        c = _chain()
        if table_name == "signals":
            c.execute.return_value.data = [{"id": TEST_SIGNAL_ID, "technology_name": "LangGraph", "summary": "요약"}]
        elif table_name == "signal_sources":
            c.execute.return_value.data = []
        elif table_name == "decisions":
            c.execute.return_value.data = [{"review_id": TEST_REVIEW_ID}]
        elif table_name == "reviews":
            c.execute.return_value.data = [{"project_id": TEST_PROJECT_ID}]
        elif table_name == "projects":
            c.execute.return_value.data = [{"user_id": TEST_USER_ID}]
        elif table_name == "user_profiles":
            c.execute.return_value.data = [{"role": "backend", "tech_stack": ["Python"], "project_goal": "x", "experience_level": "intermediate"}]
        elif table_name == "learning_paths":
            c.update.side_effect = lambda data: update_data.append(data) or c
        return c

    mock_client.table.side_effect = table_side_effect

    from pipeline.coach import _execute_learning_path_pipeline
    _execute_learning_path_pipeline(
        TEST_LEARNING_PATH_ID, TEST_DECISION_ID, TEST_SIGNAL_ID, mock_client,
        MockLLMProvider(learning_path_content=empty_goal_response),
    )

    completed = next(d for d in update_data if d.get("status") == "completed")
    assert "goal" not in completed
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

Run: `cd api && python -m pytest tests/test_learning_paths.py::test_execute_learning_path_pipeline_completes tests/test_learning_paths.py::test_execute_learning_path_pipeline_omits_empty_goal -v`
Expected: 첫 테스트 FAIL(`completed_update.get("goal")`이 None), 둘째는 PASS(아직 goal 키를 안 쓰므로).

- [ ] **Step 3: coach에 goal 기록 로직 추가**

`api/pipeline/coach.py` — `payload = json.loads(llm_response.content)` (line ~87) 바로 아래에 goal 추출 추가:

```python
        payload = json.loads(llm_response.content)
        goal = payload.get("goal")
        resources = payload.get("resources")
```

그리고 completed 업데이트(line ~113 `client.table("learning_paths").update({...})`)를 아래로 교체:

```python
        # completed 상태 전이 (불변)
        completed_update = {
            "status": "completed",
            "resources": resources,
        }
        if isinstance(goal, str) and goal.strip():
            completed_update["goal"] = goal
        client.table("learning_paths").update(completed_update).eq("id", learning_path_id).execute()
```

- [ ] **Step 4: 테스트 실행 → PASS 확인**

Run: `cd api && python -m pytest tests/test_learning_paths.py -v`
Expected: 전체 PASS(신규 2개 포함).

- [ ] **Step 5: 커밋**

```bash
git add api/pipeline/coach.py api/tests/test_learning_paths.py
git commit -m "feat(coach): learning_paths.goal 컬럼에 경로 목표 기록

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: link_verifier가 objective 보존 (회귀 방지 테스트)

`verify_and_fix_links`는 이미 `dict(r)` 얕은 복사로 모든 키를 보존한다. 죽은 링크 교체 시에도 `objective`가 유지됨을 테스트로 고정한다(1단계와 2단계 상호작용 안전장치).

**Files:**
- Test: `api/tests/test_link_verifier.py` (코드 변경 없음 — 회귀 방지 테스트만)

**Interfaces:**
- Consumes: `verify_and_fix_links(resources, technology_name, client, timeout)` (기존).
- Produces: 없음.

- [ ] **Step 1: objective 보존 테스트 작성**

`api/tests/test_link_verifier.py` 끝에 추가:

```python
def test_extra_keys_like_objective_are_preserved_on_replace():
    """죽은 링크 교체 시에도 objective 등 추가 키가 보존된다(작업 B 2단계 상호작용)."""
    resources = [dict(r, objective=f"obj{i}") for i, r in enumerate(_resources())]
    urls = {r["url"]: 200 for r in resources if r["url"]}
    urls["https://a.dev/docs"] = 404  # 첫 리소스를 죽은 링크로
    out = verify_and_fix_links(resources, "LangGraph", _client(urls), 5.0)
    # 교체된 리소스도 objective 유지
    assert out[0]["is_search_fallback"] is True
    assert out[0]["objective"] == "obj0"
    # 나머지도 objective 유지
    assert [r["objective"] for r in out] == [f"obj{i}" for i in range(5)]
```

- [ ] **Step 2: 테스트 실행 → PASS 확인**

Run: `cd api && python -m pytest tests/test_link_verifier.py -v`
Expected: 신규 테스트 포함 전체 PASS(구현이 이미 키를 보존하므로 바로 통과 — 회귀 방지용 고정).

- [ ] **Step 3: 커밋**

```bash
git add api/tests/test_link_verifier.py
git commit -m "test(link_verifier): 링크 교체 시 objective 등 추가 키 보존 고정

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: 카드에 objective 줄 추가

`LearningPathResource` 타입에 `objective`를 추가하고, 카드에 "이 단계에서: …" 한 줄을 표시한다(objective 있을 때만).

**Files:**
- Modify: `web/src/components/home/learning-path/learning-path-card.tsx`

**Interfaces:**
- Consumes: 없음.
- Produces:
  - `LearningPathResource` 인터페이스에 `objective?: string` 추가(export 유지).
  - `LearningPathCard`는 `resource.objective`가 truthy면 descriptor 아래에 "이 단계에서: {objective}" 표시.

- [ ] **Step 1: 타입에 objective 추가**

`learning-path-card.tsx`의 `LearningPathResource` 인터페이스에 필드 추가:

```tsx
export interface LearningPathResource {
  type: "official_docs" | "core_material" | "github" | "practice_example" | "applied_idea" | string;
  title: string;
  url: string;
  descriptor: string;
  objective?: string;
  is_search_fallback?: boolean;
}
```

- [ ] **Step 2: objective 렌더 추가**

`learning-path-card.tsx`에서 descriptor를 렌더하는 블록(아래) 직후에 objective 블록 추가:

```tsx
          {resource.descriptor && (
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: 0 }}>
              {resource.descriptor}
            </p>
          )}
          {resource.objective && (
            <p style={{ fontSize: "13px", color: "var(--text-tertiary)", margin: "6px 0 0" }}>
              이 단계에서: {resource.objective}
            </p>
          )}
```

- [ ] **Step 3: 타입체크**

Run: `cd web && npx tsc --noEmit`
Expected: 에러 없음(exit 0).

- [ ] **Step 4: 커밋**

```bash
git add web/src/components/home/learning-path/learning-path-card.tsx
git commit -m "feat(web): 학습 경로 카드에 objective(이 단계에서) 줄 추가

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: 페이지에 goal 배너 + 타임라인 스템퍼

`goal` 컬럼을 조회해 상단 목표 배너를 렌더하고, 5개 카드를 번호 원 ①~⑤ + 세로 연결선 타임라인으로 감싼다.

**Files:**
- Modify: `web/src/app/(app)/home/review/[signalId]/learning-path/page.tsx`

**Interfaces:**
- Consumes: `LearningPathCard`, `LearningPathResource` (Task 4).
- Produces: 없음(화면 종단).

- [ ] **Step 1: UIState.ready에 goal 추가 + 쿼리에 goal 컬럼 포함**

`page.tsx`의 `UIState` 타입 변경:

```tsx
type UIState =
  | { type: "generating" }
  | { type: "ready"; resources: LearningPathResource[]; goal?: string }
  | { type: "failed" };
```

`applyCompleted` 시그니처와 호출부, 그리고 세 곳의 `learning_paths` select에 `goal`을 추가한다.

`subscribe` 내부 `applyCompleted`를 goal도 받도록 교체:

```tsx
    const applyCompleted = (resources: LearningPathResource[], goal?: string) => {
      if (resources.length === 5) {
        setUIState({ type: "ready", resources, goal });
      } else {
        setUIState({ type: "failed" });
      }
    };
```

`subscribe` 내부 `fetchAndApplyCompleted`의 select와 호출:

```tsx
    const fetchAndApplyCompleted = async () => {
      const { data, error } = await supabase
        .from("learning_paths")
        .select("resources, goal")
        .eq("id", learningPathId)
        .maybeSingle();
      if (error) {
        console.error("learning_paths resources 조회 실패:", error);
        setUIState({ type: "failed" });
        return;
      }
      applyCompleted(
        (data?.resources as LearningPathResource[] | undefined) ?? [],
        (data?.goal as string | undefined) ?? undefined,
      );
    };
```

`subscribe` 하단의 재확인 블록 select와 호출:

```tsx
      const { data, error } = await supabase
        .from("learning_paths")
        .select("status, resources, goal")
        .eq("id", learningPathId)
        .maybeSingle();
      if (error) {
        console.error("learning_paths 상태 재확인 실패:", error);
        return;
      }
      if (data?.status === "completed") {
        applyCompleted(
          (data.resources as LearningPathResource[] | undefined) ?? [],
          (data.goal as string | undefined) ?? undefined,
        );
      } else if (data?.status === "failed") {
        setUIState({ type: "failed" });
      }
```

`resolveAndStart`의 learning_paths select와 completed 처리:

```tsx
    const { data: lpRow, error: lpError } = await supabase
      .from("learning_paths")
      .select("id, status, resources, goal")
      .eq("decision_id", decisionRow.id)
      .limit(1)
      .maybeSingle();
    if (isCancelled()) return;
    if (lpError) console.error("learning_paths 조회 실패:", lpError);

    if (lpRow) {
      if (lpRow.status === "completed") {
        const resources = (lpRow.resources as LearningPathResource[] | undefined) ?? [];
        setUIState({ type: "ready", resources, goal: (lpRow.goal as string | undefined) ?? undefined });
        return;
      }
```

- [ ] **Step 2: goal 배너 + 타임라인 스템퍼 렌더**

`page.tsx`의 `uiState.type === "ready"` 블록을 아래로 교체:

```tsx
        {uiState.type === "ready" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {uiState.goal && (
              <div
                style={{
                  backgroundColor: "var(--surface-card)",
                  borderRadius: "var(--radius-card)",
                  padding: "var(--card-padding)",
                  borderLeft: "3px solid var(--border-strong, var(--text-tertiary))",
                }}
              >
                <span
                  className="text-badge"
                  style={{ color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}
                >
                  이 경로의 목표
                </span>
                <p style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
                  {uiState.goal}
                </p>
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column" }}>
              {uiState.resources.map((resource, idx) => {
                const isLast = idx === uiState.resources.length - 1;
                return (
                  <div key={`${resource.type}-${idx}`} style={{ display: "flex", gap: "12px" }}>
                    {/* 번호 원 + 세로 연결선 */}
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
                      <div
                        aria-hidden="true"
                        style={{
                          width: "24px",
                          height: "24px",
                          borderRadius: "9999px",
                          border: "1px solid var(--border-subtle)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: "12px",
                          fontWeight: 600,
                          color: "var(--text-secondary)",
                          backgroundColor: "var(--surface-base)",
                        }}
                      >
                        {idx + 1}
                      </div>
                      {!isLast && (
                        <div style={{ flex: 1, width: "1px", backgroundColor: "var(--border-subtle)", minHeight: "12px" }} />
                      )}
                    </div>
                    {/* 카드 */}
                    <div style={{ flex: 1, minWidth: 0, paddingBottom: isLast ? 0 : "12px" }}>
                      <LearningPathCard resource={resource} onVisit={() => setHasVisitedExternal(true)} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
```

- [ ] **Step 3: 타입체크**

Run: `cd web && npx tsc --noEmit`
Expected: 에러 없음(exit 0). (참고: `--border-strong` 미정의 시 CSS fallback `var(--text-tertiary)`가 적용되므로 타입/런타임 문제 없음.)

- [ ] **Step 4: 커밋**

```bash
git add "web/src/app/(app)/home/review/[signalId]/learning-path/page.tsx"
git commit -m "feat(web): 학습 경로 목표 배너 + 번호 타임라인 스템퍼

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: 시각 검증 (Playwright 스크린샷 비평)

로컬에서 학습 경로 화면을 띄워 목표 배너 + 번호 타임라인 + objective가 무채색 정체성으로 잘 보이는지 스크린샷으로 확인한다.

**Files:** 없음(검증 전용). 데모용 시드/스크린샷은 마지막에 삭제.

- [ ] **Step 1: 백엔드/프론트 로컬 실행 및 학습 경로 완료 상태의 signal로 이동**

[[local-run-setup]] 참고. `completed` 상태 learning_path가 있는 signal의 `/home/review/{signalId}/learning-path`로 접속(없으면 기존 seed/트리거로 하나 생성). goal 컬럼이 채워진 신규 경로가 필요하면 새로 트리거.

- [ ] **Step 2: Playwright로 스크린샷 촬영 후 비평**

`mcp__plugin_playwright_playwright__browser_navigate` → `browser_take_screenshot`. 확인 포인트:
- 목표 배너가 상단에 보이고, 목표 문구가 읽힘.
- 카드 왼쪽에 ①~⑤ 번호 원과 카드 사이 세로 연결선이 자연스럽게 이어짐.
- 각 카드에 "이 단계에서: …" objective 줄이 보임.
- 새 색이 없고 무채색 유지(연결선/번호 원이 기존 톤과 어울림).
- 기존 데이터(goal 없는 예전 경로)에서도 배너만 빠지고 레이아웃이 깨지지 않음.

- [ ] **Step 3: 필요 시 미세 조정 후 재촬영, 데모 아티팩트 정리**

간격/정렬 등 조정이 필요하면 Task 4/5 파일을 수정하고 재커밋. 마지막에 데모용 스크린샷/시드는 삭제.

---

## 완료 후

모든 태스크 완료 시 `superpowers:finishing-a-development-branch`로 통합 옵션(1단계 PR 위에 쌓인 상태 반영)을 정한다. 1단계(PR #1) 머지 순서와의 관계를 오너에게 확인.
