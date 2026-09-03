# 입문자 카드 만들거리 정체성(3b) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 프로젝트 카드가 뉴스 제목을 빌려 쓰는 대신 **자기 제목(`project_title`)과 토픽 연결 한 줄(`topic_link`)** 을 갖게 하고, 생성 프롬프트가 "먼저 만들거리를 정하고 나머지를 종속시킨다"는 순서를 강제하도록 한다.

**Architecture:** LLM 호출은 1회 유지(접근안 A). `api/pipeline/llm/prompts.py`의 카드 상수·시스템 프롬프트·검증 함수만 고치고, 웹은 `ProjectCardPayload`에 optional 필드 2개를 더한 뒤 공용 `ProjectCardIdentity` 컴포넌트를 카드 상세·체인 상세 두 곳에 꽂는다. DB 마이그레이션·토글 추가 없음.

**Tech Stack:** Python 3.11 · pytest (asyncio_mode=auto) · Next.js(App Router) · TypeScript

**Spec:** `docs/superpowers/specs/2026-09-02-beginner-card-project-identity-design.md`

## Global Constraints

- 백엔드 테스트 실행 위치: `api/` 디렉터리에서 `pytest tests/<file>::<test> -v`.
- 웹에는 **테스트 러너가 없다**(`web/package.json`에 `test` 스크립트 없음). `*.test.tsx`는 문서용으로만 갱신하고, 실제 검증은 `cd web && npx tsc --noEmit`로 한다.
- 검증 실패는 곧 유저의 `failed` 화면이다(`api/pipeline/reviewer.py`가 예외를 잡아 `status="failed"`로 기록). 하드 룰은 스펙이 정한 것만 걸고 **금칙어 문자열 검사는 넣지 않는다**.
- 검증 실패 시 던지는 예외는 `LLMProviderError`(기존 패턴).
- `project_title` 길이 상한은 **60자**(`CARD_TITLE_MAX_LEN`).
- 저장 봉투 `{"schema_version": 1, "review_type": ..., "payload": ...}`와 `review_type="project_card"`는 불변. DB 변경 없음.
- 웹 타입은 두 신규 필드를 **optional**로 둔다(옛 카드 하위호환). 백엔드 검증만 필수.
- 커밋 메시지는 한국어 관례를 따른다(`feat(cards): ...`, `docs(...): ...`).

---

### Task 1: 카드 스키마 · 프롬프트 · 검증 (백엔드)

`prompts.py`의 순수 상수/함수만 바꾼다. LLM·DB 무관이라 pytest로 완결된다.

**Files:**
- Modify: `api/pipeline/llm/prompts.py` (파일 끝 카드 섹션, 231행 이후)
- Test: `api/tests/test_project_card_prompt.py` (기존 파일 수정)

**Interfaces:**
- Consumes: `LLMProviderError`, `ReviewContext` (`pipeline/llm/base.py`), `format_sources` (같은 파일 상단)
- Produces:
  - `REQUIRED_CARD_BLOCKS: list[str]` — 13개 (기존 11개 + `project_title`, `topic_link`)
  - `CARD_TITLE_MAX_LEN: int` = `60`
  - `PROJECT_CARD_SYSTEM_PROMPT: str` (재작성)
  - `parse_and_validate_card(raw: str) -> None` (시그니처 불변, 규칙 추가)
  - `build_card_user_content(context: ReviewContext) -> str` (변경 없음)

- [ ] **Step 1: 테스트 픽스처에 신규 필드 추가**

`api/tests/test_project_card_prompt.py`의 `_valid_card()` 반환 dict 맨 앞에 두 줄을 넣는다:

```python
def _valid_card() -> dict:
    return {
        "project_title": "AI에게 질문하는 나만의 챗봇 만들기",
        "topic_link": "새 모델 발표의 핵심인 '질문에 답하기'를 직접 만들어봅니다.",
        "skill_label": "웹폼 만들고 데이터 저장하기",
        "difficulty": "first_step",
```

(나머지 필드는 그대로 둔다.)

- [ ] **Step 2: 실패하는 테스트 추가**

같은 파일 맨 끝에 붙인다:

```python
def test_missing_project_title_raises():
    card = _valid_card()
    del card["project_title"]
    with pytest.raises(LLMProviderError, match="필수 블록 누락"):
        parse_and_validate_card(json.dumps(card))


def test_missing_topic_link_raises():
    card = _valid_card()
    del card["topic_link"]
    with pytest.raises(LLMProviderError, match="필수 블록 누락"):
        parse_and_validate_card(json.dumps(card))


def test_project_title_at_max_len_passes():
    card = _valid_card()
    card["project_title"] = "가" * CARD_TITLE_MAX_LEN
    parse_and_validate_card(json.dumps(card))  # 예외 없이 통과


def test_project_title_over_max_len_raises():
    card = _valid_card()
    card["project_title"] = "가" * (CARD_TITLE_MAX_LEN + 1)
    with pytest.raises(LLMProviderError, match="project_title"):
        parse_and_validate_card(json.dumps(card))


def test_system_prompt_lists_every_required_block():
    # 프롬프트에 안 적힌 키를 검증만 강제하면 생성이 통째로 실패한다 — 회귀 방지용
    for key in REQUIRED_CARD_BLOCKS:
        assert key in PROJECT_CARD_SYSTEM_PROMPT
```

그리고 같은 파일의 `_STRING_BLOCKS` 리스트를 아래로 교체한다(빈 문자열·비문자열 파라미터라이즈 테스트가 신규 필드까지 덮게 된다):

```python
_STRING_BLOCKS = [
    "project_title", "topic_link",
    "skill_label", "deliverable", "success_preview",
    "prerequisites", "how_to_start", "example_prompt",
]
```

마지막으로 파일 상단 import를 아래로 교체한다:

```python
from pipeline.llm.prompts import (
    CARD_TITLE_MAX_LEN,
    PROJECT_CARD_SYSTEM_PROMPT,
    REQUIRED_CARD_BLOCKS,
    build_card_user_content,
    parse_and_validate_card,
)
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

Run: `cd api && pytest tests/test_project_card_prompt.py -v`
Expected: FAIL — `ImportError: cannot import name 'CARD_TITLE_MAX_LEN' from 'pipeline.llm.prompts'`

- [ ] **Step 4: `REQUIRED_CARD_BLOCKS`와 상한 상수 수정**

`api/pipeline/llm/prompts.py`의 `REQUIRED_CARD_BLOCKS` 정의를 아래로 교체한다:

```python
REQUIRED_CARD_BLOCKS = [
    "project_title", "topic_link",
    "skill_label", "difficulty", "estimated_minutes",
    "deliverable", "success_preview", "prerequisites",
    "how_to_start", "example_prompt",
    "milestones", "troubleshooting", "success_checklist",
]

CARD_DIFFICULTIES = ["first_step", "basic", "challenge"]

# project_title이 뉴스 헤드라인 복붙으로 채워지는 것을 막는 안전핀.
# 목표는 30자 내외지만, 상한은 넉넉히 잡아 정상 카드가 탈락하지 않게 한다.
CARD_TITLE_MAX_LEN = 60
```

- [ ] **Step 5: 시스템 프롬프트 재작성**

같은 파일의 `PROJECT_CARD_SYSTEM_PROMPT` 전체를 아래로 교체한다:

```python
PROJECT_CARD_SYSTEM_PROMPT = """당신은 '개발 입문자'를 위한 학습 코치입니다. 주어진 기술/토픽을 재료 삼아, 입문자가 직접 만들어보는(바이브코딩) '프로젝트 카드'를 JSON으로 작성하세요.

## 작성 순서 (반드시 이 순서로 생각하세요)

1단계 — 먼저 '만들거리' 하나를 정합니다.
- 입문자가 AI 코딩 도구로 몇십 분 안에 완주할 수 있는 작은 프로젝트여야 합니다.
- 우선 토픽의 기술을 '직접 써서' 만들 수 있는지 봅니다.
- 직접 만들기 어려운 토픽(하드웨어, 기업 소식, 대규모 인프라 등)이면, 그 토픽의 핵심 개념만 손으로 체험하는 미니 프로젝트로 돌립니다. 예) '정책 언어(Rego vs CEL) 논쟁' → '내 앱에 간단한 접근 규칙 만들어보기'
- 준비물이 결제나 복잡한 설치를 요구하면, 그 만들거리를 버리고 다시 고릅니다.

2단계 — 정한 만들거리를 기준으로 나머지 항목을 채웁니다.
- 결과물·성공 모습·준비물·진행 과정·막힘 대처가 전부 '그 프로젝트를 만드는 이야기'여야 합니다.
- 토픽 해설이나 뉴스 요약이 되어서는 안 됩니다.

## 금지 사항

- '뉴스 요약 봇', '트렌드 정리 대시보드'처럼 어떤 토픽에나 갖다 붙는 만들거리는 금지입니다.
- project_title에 회사명이나 모델 버전을 나열하지 마세요. 뉴스 헤드라인 어투도 금지입니다.
- 전문용어를 피하고 쉬운 말로 씁니다. 특정 개인 맞춤이 아니라 누구에게나 동일한 '표준' 내용으로 작성합니다.

반드시 아래 13개 키를 모두 포함한 JSON 객체만 반환하세요(마크다운 코드블록 없이):
{
  "project_title": "만들거리 제목 — 무엇을 만드는지가 드러나게 (30자 내외, 예: 'AI에게 질문하는 나만의 챗봇 만들기')",
  "topic_link": "이 토픽에서 왜 이 만들거리가 나왔는지 한 줄 (예: '정책 언어 논쟁의 핵심인 규칙으로 판단하기를 직접 만들어봅니다')",
  "skill_label": "이 카드로 배우는 스킬 — 제목이 아니라 능력 (예: 'API 연결과 대화 상태 관리')",
  "difficulty": "first_step|basic|challenge 중 하나",
  "estimated_minutes": 30,
  "deliverable": "완성하면 손에 쥐어지는 결과물 (2-3문장)",
  "success_preview": "이렇게 보이면 성공 — 완성 화면/상태 묘사 (1-2문장)",
  "prerequisites": "시작 전 준비물/세팅. 없으면 '없어요, 바로 시작!'",
  "how_to_start": "표준 진입점과 첫 단계 (2-4문장, 누구에게나 동일)",
  "example_prompt": "AI 코딩 도구에 복붙할 수 있는 표준 예시 프롬프트 (구체적으로)",
  "milestones": [{"action": "무엇을 함", "done_signal": "끝나면 이렇게 보임"}],
  "troubleshooting": [{"symptom": "자주 나는 문제/에러", "fix": "복붙하거나 시도할 복구 방법"}],
  "success_checklist": ["다 됐는지 확인할 체크 항목"]
}
규칙:
- project_title은 60자 이내.
- milestones는 큰 단계 3~5개만(잘게 쪼개지 말 것 — 지시서가 아니라 지도).
- troubleshooting 최소 1개, success_checklist 최소 1개.
- estimated_minutes는 양의 정수(분).
- 모든 문구는 한국어, 입문자가 겁먹지 않는 친근한 말투."""
```

- [ ] **Step 6: 검증 규칙 추가**

같은 파일 `parse_and_validate_card` 함수 끝의 문자열 검사 루프를 아래로 교체한다(신규 2필드를 목록에 넣고, 루프 뒤에 길이 상한 검사를 잇는다):

```python
    for field in (
        "project_title", "topic_link",
        "skill_label", "deliverable", "success_preview",
        "prerequisites", "how_to_start", "example_prompt",
    ):
        value = parsed[field]
        if not isinstance(value, str) or not value.strip():
            raise LLMProviderError(f"{field}가 비어있거나 문자열이 아님: {value!r}")
    title = parsed["project_title"]
    if len(title) > CARD_TITLE_MAX_LEN:
        raise LLMProviderError(
            f"project_title이 너무 김({len(title)}자 > {CARD_TITLE_MAX_LEN}): {title!r}"
        )
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `cd api && pytest tests/test_project_card_prompt.py -v`
Expected: PASS (전부)

- [ ] **Step 8: 카드 경로 회귀 확인**

Run: `cd api && pytest tests/test_card_pipeline.py tests/test_project_cards.py tests/test_reviews_trigger.py -v`
Expected: PASS. 실패한다면 해당 테스트의 카드 픽스처에도 `project_title`·`topic_link`를 추가해야 한다(Step 1과 동일한 두 줄).

- [ ] **Step 9: 커밋**

```bash
git add api/pipeline/llm/prompts.py api/tests/test_project_card_prompt.py
git commit -m "feat(cards): 카드에 만들거리 제목·토픽 연결 필드 추가(생성 프롬프트 재설계)"
```

---

### Task 2: 웹 렌더 — 정체성 블록 (카드 상세 · 체인 상세)

백엔드가 채운 두 필드를 화면에 꽂는다. 옛 카드는 필드가 없으므로 전부 optional 처리.

**Files:**
- Modify: `web/src/components/home/review/project-card-blocks.tsx` (타입 + 신규 컴포넌트)
- Modify: `web/src/components/home/review/project-card-content.tsx` (h1 교체)
- Modify: `web/src/components/history/chain-detail-content.tsx` (REVIEW 노드에 삽입)
- Modify: `web/src/components/home/review/__tests__/project-card-blocks.test.tsx` (문서용 픽스처 갱신)
- Modify: `web/src/components/home/review/__tests__/project-card-content.test.tsx` (문서용 픽스처 갱신)

**Interfaces:**
- Consumes: `ProjectCardPayload` (Task 1이 만든 백엔드 필드와 이름이 1:1로 맞아야 한다 — `project_title`, `topic_link`)
- Produces:
  - `ProjectCardPayload.project_title?: string`, `ProjectCardPayload.topic_link?: string`
  - `ProjectCardIdentity({ payload, signalTitle, variant }: { payload: ProjectCardPayload; signalTitle: string; variant: "detail" | "chain" })`

- [ ] **Step 1: 페이로드 타입에 optional 필드 추가**

`web/src/components/home/review/project-card-blocks.tsx`의 `ProjectCardPayload` 인터페이스 첫 줄들을 아래로 교체한다:

```tsx
export interface ProjectCardPayload {
  /** 만들거리 제목. 이 필드 이전에 생성된 카드에는 없다 — 하위호환을 위해 optional */
  project_title?: string;
  /** "왜 이 토픽에서 이게 나왔나" 한 줄. 위와 같은 이유로 optional */
  topic_link?: string;
  skill_label: string;
```

(나머지 필드는 그대로 둔다.)

- [ ] **Step 2: `ProjectCardIdentity` 컴포넌트 추가**

같은 파일에서 `export function ProjectCardMeta(...)` **바로 위**에 추가한다:

```tsx
/**
 * 카드의 정체성 블록 — 만들거리 제목 + 토픽 연결 한 줄.
 * detail: 화면 최상단 h1. 제목이 없는 옛 카드는 뉴스 제목으로 폴백하고, 출처 토픽 라벨을 함께 보여준다.
 * chain:  체인의 REVIEW 노드 안 h2. SIGNAL 노드가 이미 뉴스 제목을 들고 있어 출처 라벨은 생략한다.
 */
export function ProjectCardIdentity({
  payload,
  signalTitle,
  variant,
}: {
  payload: ProjectCardPayload;
  signalTitle: string;
  variant: "detail" | "chain";
}) {
  const projectTitle = payload.project_title?.trim();
  const topicLink = payload.topic_link?.trim();
  const title = variant === "detail" ? projectTitle || signalTitle : projectTitle;

  return (
    <div style={{ marginBottom: "12px" }}>
      {title &&
        (variant === "detail" ? (
          <h1 className="text-screen-title" style={{ marginBottom: "6px" }}>
            {title}
          </h1>
        ) : (
          <h2 className="text-section-title" style={{ marginBottom: "6px" }}>
            {title}
          </h2>
        ))}
      {topicLink && (
        <p className="text-body" style={{ color: "var(--text-secondary)", marginBottom: "4px" }}>
          {topicLink}
        </p>
      )}
      {variant === "detail" && (
        <p className="text-caption" style={{ color: "var(--text-secondary)" }}>
          📰 출처 토픽 · {signalTitle}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 3: 카드 상세의 h1 교체**

`web/src/components/home/review/project-card-content.tsx`에서 아래 줄을

```tsx
      <h1 className="text-screen-title" style={{ marginBottom: "12px" }}>{signalTitle}</h1>
```

이렇게 바꾼다:

```tsx
      <ProjectCardIdentity payload={payload} signalTitle={signalTitle} variant="detail" />
```

같은 파일 상단 import도 교체한다:

```tsx
import { ProjectCardBlocks, ProjectCardIdentity, ProjectCardMeta, type ProjectCardPayload } from "./project-card-blocks";
```

- [ ] **Step 4: 체인 상세의 REVIEW 노드에 삽입**

`web/src/components/history/chain-detail-content.tsx`의 REVIEW 노드에서 아래 블록을

```tsx
            <>
              <VibeCodingGuide />
              <ProjectCardMeta payload={review.payload} />
              <ProjectCardBlocks payload={review.payload} />
            </>
```

이렇게 바꾼다(SIGNAL 노드의 `<h1>{signal.title}</h1>`은 **건드리지 않는다**):

```tsx
            <>
              <VibeCodingGuide />
              <ProjectCardIdentity payload={review.payload} signalTitle={signal.title} variant="chain" />
              <ProjectCardMeta payload={review.payload} />
              <ProjectCardBlocks payload={review.payload} />
            </>
```

같은 파일 상단 import도 교체한다:

```tsx
import { ProjectCardBlocks, ProjectCardIdentity, ProjectCardMeta, type ProjectCardPayload } from "@/components/home/review/project-card-blocks";
```

- [ ] **Step 5: 문서용 테스트 픽스처 갱신**

`web/src/components/home/review/__tests__/project-card-blocks.test.tsx`와 `project-card-content.test.tsx` 두 파일에서, 카드 픽스처의 `skill_label: "웹폼 만들고 데이터 저장하기",` 줄 **바로 위**에 아래 두 줄을 넣는다:

```tsx
  project_title: "AI에게 질문하는 나만의 챗봇 만들기",
  topic_link: "새 모델 발표의 핵심인 '질문에 답하기'를 직접 만들어봅니다.",
```

(러너가 없어 실행되지는 않지만, 픽스처가 실제 페이로드 모양과 어긋나면 다음 사람이 잘못된 예시를 복사한다.)

- [ ] **Step 6: 타입 체크**

Run: `cd web && npx tsc --noEmit`
Expected: 에러 없음. `project_title`을 필수로 잘못 선언했다면 옛 카드 픽스처에서 에러가 난다.

- [ ] **Step 7: 커밋**

```bash
git add web/src/components/home/review/project-card-blocks.tsx web/src/components/home/review/project-card-content.tsx web/src/components/history/chain-detail-content.tsx web/src/components/home/review/__tests__/project-card-blocks.test.tsx web/src/components/home/review/__tests__/project-card-content.test.tsx
git commit -m "feat(cards): 카드 상세·체인 상세에 만들거리 제목/토픽 연결 노출"
```

---

### Task 3: 생성 품질 눈 점검 (정성, n=1)

프롬프트 변경의 성패는 유닛 테스트가 아니라 **실제 생성물**로만 판정된다. DB·인증 없이 LLM만 때려서 3개 토픽을 뽑아 본다.

**Files:**
- Create: `/private/tmp/claude-501/-Users-sgyoo-Desktop-claude-playground-decision-os/a744d453-bac5-4b04-8665-3c60e590a2b8/scratchpad/check_card_identity.py` (**커밋하지 않는 일회용 스크립트**)

**Interfaces:**
- Consumes: `get_llm_provider()` (`api/pipeline/llm/factory.py`), `ReviewContext` (`api/pipeline/llm/base.py`), `parse_and_validate_card` (Task 1)

- [ ] **Step 1: 점검 스크립트 작성**

위 경로에 아래 내용으로 만든다:

```python
"""3b 눈 점검 — 성격이 다른 토픽 3개로 카드를 실제 생성해 정체성을 확인한다. 일회용."""
import json
import sys

sys.path.insert(0, "/Users/sgyoo/Desktop/claude-playground/decision-os/api")

from pipeline.llm.base import ReviewContext
from pipeline.llm.factory import get_llm_provider
from pipeline.llm.prompts import parse_and_validate_card

TOPICS = [
    # 1) 직접형 — 토픽 기술을 그대로 써서 만들 수 있다
    ("Claude Opus 5", [{"source_type": "blog", "url": "https://example.com/opus5", "title": "Claude Opus 5 발표"}]),
    # 2) 개념형 — 추상 논쟁, 개념 체험으로 우회해야 한다
    ("Rego vs CEL vs Cedar 정책 언어", [{"source_type": "blog", "url": "https://example.com/policy", "title": "정책 언어 비교"}]),
    # 3) 변환 난이도 최상 — 하드웨어/기업 소식
    ("CXMT 메모리 채택 (HP·Asus·Acer)", [{"source_type": "news", "url": "https://example.com/cxmt", "title": "PC 제조사들의 CXMT 메모리 채택"}]),
]

llm = get_llm_provider()
for name, sources in TOPICS:
    print("=" * 70)
    print(f"토픽: {name}")
    try:
        raw = llm.generate_card(ReviewContext(technology_name=name, signal_sources=sources)).content
        parse_and_validate_card(raw)
        card = json.loads(raw)
        print(f"  project_title : {card['project_title']}")
        print(f"  topic_link    : {card['topic_link']}")
        print(f"  skill_label   : {card['skill_label']}")
        print(f"  deliverable   : {card['deliverable']}")
        print(f"  prerequisites : {card['prerequisites']}")
        print("  milestones    :")
        for m in card["milestones"]:
            print(f"    - {m['action']} → {m['done_signal']}")
    except Exception as e:
        print(f"  실패: {type(e).__name__}: {e}")
```

- [ ] **Step 2: 실행**

Run:
```bash
cd /Users/sgyoo/Desktop/claude-playground/decision-os/api && .venv/bin/python /private/tmp/claude-501/-Users-sgyoo-Desktop-claude-playground-decision-os/a744d453-bac5-4b04-8665-3c60e590a2b8/scratchpad/check_card_identity.py
```
(`.env`의 LLM 키를 factory가 읽는다. 키가 없으면 여기서 멈추고 오너에게 알린다 — 임의로 키를 찾아다니지 말 것.)

- [ ] **Step 3: 판정**

세 토픽의 출력을 아래 기준으로 읽는다. **오너에게 그대로 보여주고 판정을 받는다.**

- 통과: `project_title`이 셋 다 "무엇을 만드는지"를 말한다. 3번(하드웨어)이 개념 체험형으로 착지했다.
- 실패: 3번에서 "뉴스 요약 봇 / 트렌드 대시보드" 류가 나왔다. 또는 `project_title`이 뉴스 헤드라인 어투다. 또는 `prerequisites`가 결제·복잡한 설치를 요구한다.
- 실패면 Task 1 Step 5의 프롬프트 문구(특히 "금지 사항" 절)를 고치고 Step 2를 다시 돌린다. 프롬프트를 고쳤으면 `cd api && pytest tests/test_project_card_prompt.py -v`를 다시 통과시킨다.

- [ ] **Step 4: 화면 확인**

로컬 웹(:3000)에서 카드 상세를 열어 헤더가 만들거리 제목으로 바뀌고 그 아래 토픽 연결 한 줄 + `📰 출처 토픽` 라벨이 보이는지 확인한다. 히스토리 → 체인 상세에서는 SIGNAL 노드가 뉴스 제목을, REVIEW 노드가 만들거리 제목을 들고 있어야 한다.

- [ ] **Step 5: 스크래치패드 스크립트는 커밋하지 않는다**

Run: `git status --short`
Expected: 스크래치패드 경로가 목록에 없다(프로젝트 밖이라 애초에 잡히지 않는다). 프로젝트 안에 임시 파일을 만들었다면 지운다.

---

## 완료 조건

1. `cd api && pytest tests/test_project_card_prompt.py tests/test_card_pipeline.py tests/test_project_cards.py tests/test_reviews_trigger.py -v` 전부 통과
2. `cd web && npx tsc --noEmit` 에러 없음
3. Task 3의 3토픽 생성 결과를 오너가 보고 "통과" 판정
