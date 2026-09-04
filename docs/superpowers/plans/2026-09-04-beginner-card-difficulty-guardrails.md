# 입문자 카드 난이도 가드레일 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 카드 생성 프롬프트에 완주 가능성 게이트·셋업형 금칙·준비물 규칙을 넣어, 결제/설치 장벽이 있거나 "설치·실행" 자체가 만들거리인 카드가 생성되지 않게 한다.

**Architecture:** `PROJECT_CARD_SYSTEM_PROMPT` 한 상수만 고친다. 스키마·검증·웹·DB는 건드리지 않는다. 프롬프트 품질은 유닛 테스트로 잡히지 않으므로, 가드레일이 뚫렸던 자리를 겨냥한 토픽 4개로 카드를 실제 생성해 before/after를 눈으로 비교하는 하네스를 함께 만든다. 하네스의 순수 함수(요약·렌더)만 TDD로 테스트하고, LLM 실호출 경로는 dev/ops 실행 경로로 둔다 — 기존 `api/scripts/eval_engagement.py` + `api/tests/test_eval_engagement.py`가 같은 구조의 선례다.

**Tech Stack:** Python 3.11 / FastAPI 백엔드, pytest, OpenAI Responses API (`api/pipeline/llm/openai_provider.py`)

**Spec:** `docs/superpowers/specs/2026-09-04-beginner-card-difficulty-guardrails-design.md`

## Global Constraints

- **브랜치**: `feat/beginner-card-difficulty-guardrails` (main에서 분기). main에 직접 커밋 금지.
- **작업 디렉터리**: 모든 python/pytest 명령은 `cd api` 에서 실행한다.
- **허용선 — 요구해도 되는 준비물**: 신용카드 없이 발급되는 무료 API 키 / npm·pip 패키지 / 웹 브라우저와 텍스트 편집기. AI 코딩 도구는 모든 카드의 공통 전제라 준비물에 적지 않는다.
- **허용선 — 요구하면 안 되는 준비물**: 결제·신용카드 등록·유료 구독·크레딧 구매 / 운영체제·리눅스 배포판·가상머신·도커·데이터베이스 서버 설치 / 하드웨어 구매·클라우드 서버 배포.
- **하드 검증을 추가하지 않는다**: `parse_and_validate_card`에 금칙어 검사나 새 필드 검사를 넣지 말 것. 재시도 인프라가 없어 검증 실패가 곧 유저의 `failed` 화면이다.
- **무변경 대상**: `parse_and_validate_card`, `REQUIRED_CARD_BLOCKS`(13개), `CARD_DIFFICULTIES`, `CARD_TITLE_MAX_LEN`, `build_card_user_content`, `web/` 전체, DB 스키마.
- **비목표(손대지 말 것)**: 난이도 라벨 캘리브레이션, `estimated_minutes` 정확도, P1 마일스톤, P2 체크리스트, `example_prompt` 개인화, 피드 목록 제목, Flutter.
- **LLM 실호출은 `LLM_PROVIDER=openai`로만**: 프로덕션이 openai다. 로컬 `.env`가 gemini면 다른 모델을 검수하는 셈이 된다.
- **프롬프트 문자열을 assert 하는 테스트를 추가하지 않는다**: 방금 쓴 문장을 다시 읽는 동어반복이라 회귀를 못 잡으면서 프롬프트 개작 때마다 깨진다.

---

### Task 0: 브랜치 생성

**Files:** 없음 (git 작업만)

- [ ] **Step 1: main 최신화 후 브랜치 분기**

```bash
cd /Users/sgyoo/Desktop/claude-playground/decision-os
git checkout main
git pull --ff-only
git checkout -b feat/beginner-card-difficulty-guardrails
git status
```

Expected: `On branch feat/beginner-card-difficulty-guardrails`, working tree에 기존 미추적 파일(.png 등)만 남아있음.

---

### Task 1: 눈 점검 하네스 + before 베이스라인

가드레일 토픽 4개로 카드를 실제 생성해 markdown 리포트를 뽑는 스크립트를 만들고, **프롬프트를 고치기 전에** 베이스라인을 찍어둔다. 베이스라인 없이 프롬프트를 고치면 "정말 나아졌나"를 확인할 방법이 사라진다.

**Files:**
- Create: `api/scripts/eval_card_guardrails.py`
- Create: `api/tests/test_eval_card_guardrails.py`

**Interfaces:**
- Consumes: `pipeline.llm.base.ReviewContext(technology_name: str, signal_sources: list[dict])`, `pipeline.llm.factory.get_llm_provider() -> LLMProvider`, `LLMProvider.generate_card(context) -> LLMResponse`(`.content`는 JSON 문자열), `core.config.settings.llm_provider`
- Produces: `EVAL_TOPICS: list[dict]`(각 dict는 `technology_name`, `aims_at`, `signal_sources` 키), `summarize_card(raw: str) -> dict[str, str]`, `render_markdown(rows: list[dict[str, str]]) -> str`, `run() -> list[dict[str, str]]`, `main() -> int`

- [ ] **Step 1: 실패하는 테스트 작성**

`api/tests/test_eval_card_guardrails.py` 신규 생성:

```python
"""눈 점검 하네스의 순수 함수 테스트 (LLM 호출 없음).

LLM 실호출 경로(run)는 dev/ops 실행 경로라 테스트하지 않는다 —
기존 test_eval_engagement.py가 DB 읽기(load_*)를 빼고 compute_metrics만 테스트하는 것과 같다.
"""
import json

from scripts.eval_card_guardrails import (
    EVAL_TOPICS,
    render_markdown,
    summarize_card,
)


def _card(**overrides) -> str:
    payload = {
        "project_title": "메모를 저장하는 나만의 웹페이지 만들기",
        "topic_link": "새 모델 발표의 핵심인 '기억해두기'를 직접 만들어봅니다.",
        "skill_label": "웹폼 만들고 데이터 저장하기",
        "difficulty": "first_step",
        "estimated_minutes": 30,
        "deliverable": "이름과 메모를 입력해 저장하는 간단한 웹페이지",
        "success_preview": "저장을 누르면 목록에 내가 쓴 내용이 나타난다",
        "prerequisites": "없어요, 바로 시작!",
        "how_to_start": "AI 코딩 도구를 열고 예시 프롬프트를 붙여넣으세요.",
        "example_prompt": "메모를 저장하는 웹페이지를 만들어줘.",
        "milestones": [{"action": "화면 만들기", "done_signal": "입력칸이 뜬다"}],
        "troubleshooting": [{"symptom": "저장이 안 됨", "fix": "콘솔 에러를 붙여넣고 물어보기"}],
        "success_checklist": ["저장한 내용이 다시 보인다"],
    }
    payload.update(overrides)
    return json.dumps(payload, ensure_ascii=False)


def test_eval_topics_cover_four_guardrail_targets():
    """토픽 4개는 스펙이 지정한 '노리는 실패' 4종을 하나씩 겨냥해야 한다."""
    assert len(EVAL_TOPICS) == 4
    for topic in EVAL_TOPICS:
        assert topic["technology_name"].strip()
        assert topic["aims_at"].strip()
        assert topic["signal_sources"], "출처가 비면 프롬프트 입력이 실제와 달라진다"


def test_summarize_card_extracts_eye_check_fields():
    result = summarize_card(_card())
    assert result["project_title"] == "메모를 저장하는 나만의 웹페이지 만들기"
    assert result["difficulty"] == "first_step"
    assert result["estimated_minutes"] == "30"
    assert result["prerequisites"] == "없어요, 바로 시작!"
    assert result["deliverable"] == "이름과 메모를 입력해 저장하는 간단한 웹페이지"


def test_summarize_card_marks_missing_field_instead_of_raising():
    """필드가 빠진 카드도 눈 점검 대상이다 — 누락 자체가 관찰할 사실이라 죽지 않는다."""
    payload = json.loads(_card())
    del payload["prerequisites"]
    result = summarize_card(json.dumps(payload, ensure_ascii=False))
    assert result["prerequisites"] == "<누락>"
    assert result["project_title"] == "메모를 저장하는 나만의 웹페이지 만들기"


def test_summarize_card_marks_invalid_json_instead_of_raising():
    result = summarize_card("이건 JSON이 아님")
    assert all("JSON 파싱 실패" in v for v in result.values())


def test_render_markdown_includes_topic_aim_and_fields():
    rows = [
        {
            "technology_name": "Omarchy — Arch Linux 기반 개발 환경",
            "aims_at": "셋업형 만들거리",
            **summarize_card(_card()),
        }
    ]
    report = render_markdown(rows)
    assert "Omarchy — Arch Linux 기반 개발 환경" in report
    assert "셋업형 만들거리" in report
    assert "없어요, 바로 시작!" in report
    assert "합격 기준" in report, "리포트만 보고도 무엇을 판정해야 하는지 알 수 있어야 한다"
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인**

```bash
cd api && python -m pytest tests/test_eval_card_guardrails.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.eval_card_guardrails'`

- [ ] **Step 3: 스크립트 구현**

`api/scripts/eval_card_guardrails.py` 신규 생성:

```python
"""입문자 카드 난이도 가드레일 — 눈 점검 하네스.

무엇을:
    가드레일이 뚫렸던 자리를 겨냥한 토픽 4개로 가짜 ReviewContext를 만들고 llm.generate_card()를
    직접 호출해, 눈 점검에 쓰는 필드만 markdown으로 뽑는다. 시그널 DB도 파이프라인도 타지 않는다.
    "프롬프트 규칙이 실제로 먹히는가"는 유닛 테스트로 잡히지 않아 사람이 눈으로 본다.

    프롬프트를 고치기 전/후로 한 번씩 돌려 나란히 비교하는 것이 이 스크립트의 용도다.
    P1(마일스톤)·P2(체크리스트) 슬라이스에서는 EVAL_TOPICS만 바꿔 재사용한다.

⚠️ 반드시 LLM_PROVIDER=openai 로 실행한다. 프로덕션이 openai라, gemini로 보면 실제 배포되는 것과
    다른 모델을 검수하는 셈이 된다.

실행:
    cd api && python -m scripts.eval_card_guardrails                      # stdout
    cd api && python -m scripts.eval_card_guardrails --output before.md   # markdown 저장

순수 함수(summarize_card·render_markdown)만 test_eval_card_guardrails.py에서 테스트한다.
LLM 실호출(run)은 dev/ops 실행 경로다.
"""
from __future__ import annotations

import argparse
import json

from pipeline.llm.base import ReviewContext

# 스펙의 '겨냥 토픽 4개'. aims_at은 리포트에 그대로 찍혀, 읽는 사람이 무엇을 확인해야 하는지 알려준다.
EVAL_TOPICS: list[dict] = [
    {
        "technology_name": "Omarchy — Arch Linux 기반 개발 환경",
        "aims_at": "셋업형 만들거리 (실제 실패 사례 재현)",
        "signal_sources": [
            {
                "source_type": "blog",
                "title": "Omarchy: 내 Arch Linux 개발 환경을 통째로 옮겨담기",
                "url": "https://example.com/omarchy",
            }
        ],
    },
    {
        "technology_name": "SK하이닉스 HBM4 양산",
        "aims_at": "하드웨어 구매 요구",
        "signal_sources": [
            {
                "source_type": "news",
                "title": "SK하이닉스, HBM4 양산 돌입 — AI 가속기 메모리 세대교체",
                "url": "https://example.com/hbm4",
            }
        ],
    },
    {
        "technology_name": "Vercel Pro 플랜 가격 개편",
        "aims_at": "결제 유도",
        "signal_sources": [
            {
                "source_type": "news",
                "title": "Vercel, Pro 플랜 가격 체계 개편 발표",
                "url": "https://example.com/vercel-pricing",
            }
        ],
    },
    {
        "technology_name": "Claude Opus 5 출시",
        "aims_at": "정상 케이스 회귀 (무료 키 발급처가 제대로 적히나)",
        "signal_sources": [
            {
                "source_type": "news",
                "title": "Anthropic, Claude Opus 5 공개",
                "url": "https://example.com/opus5",
            }
        ],
    },
]

_SUMMARY_FIELDS = (
    "project_title",
    "difficulty",
    "estimated_minutes",
    "prerequisites",
    "deliverable",
)

_PASS_CRITERIA = """## 합격 기준 (사람이 판정 — 4장 전부 만족해야 통과)

1. 만들거리가 '설치·실행·구축'형이 아니다
2. prerequisites에 결제·OS 설치·하드웨어 요구가 없다
3. prerequisites에 AI 코딩 도구 설치나 '터미널 기본 이해' 같은 겁주기 문구가 없다
4. 무료 키가 필요한 카드는 발급처가 한 줄로 적혀 있다
5. (3b 회귀) project_title이 뉴스 제목이 아니고, 만들거리에 동작하는 것이 있다"""


def summarize_card(raw: str) -> dict[str, str]:
    """generate_card 응답(JSON 문자열)에서 눈 점검용 필드만 뽑는 순수 함수.

    파싱 실패나 필드 누락에도 예외를 올리지 않는다 — 눈 점검은 망가진 카드도 봐야 하고,
    한 토픽이 죽었다고 나머지 3개 수집이 중단되면 비교가 반쪽이 되기 때문이다.
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        return {field: f"<JSON 파싱 실패: {e}>" for field in _SUMMARY_FIELDS}
    if not isinstance(parsed, dict):
        return {field: f"<JSON 객체 아님: {type(parsed).__name__}>" for field in _SUMMARY_FIELDS}
    return {field: str(parsed.get(field, "<누락>")) for field in _SUMMARY_FIELDS}


def render_markdown(rows: list[dict[str, str]]) -> str:
    """토픽별 카드 요약을 markdown 리포트로 렌더하는 순수 함수."""
    out: list[str] = ["# 입문자 카드 가드레일 눈 점검", "", _PASS_CRITERIA, ""]
    for row in rows:
        out.append(f"## {row['technology_name']}")
        out.append("")
        out.append(f"- **노리는 실패**: {row['aims_at']}")
        out.append(f"- **project_title**: {row['project_title']}")
        out.append(f"- **difficulty / estimated_minutes**: {row['difficulty']} / {row['estimated_minutes']}분")
        out.append(f"- **prerequisites**: {row['prerequisites']}")
        out.append(f"- **deliverable**: {row['deliverable']}")
        out.append("")
    return "\n".join(out)


def run() -> list[dict[str, str]]:
    """토픽마다 카드를 1장씩 생성한다 (LLM 실호출 — dev/ops 경로)."""
    from core.config import settings
    from pipeline.llm.factory import get_llm_provider

    if settings.llm_provider != "openai":
        print(
            f"⚠️ LLM_PROVIDER={settings.llm_provider} — 프로덕션은 openai다. "
            "이 결과는 실제 배포되는 모델의 것이 아니다."
        )

    llm = get_llm_provider()
    rows: list[dict[str, str]] = []
    for topic in EVAL_TOPICS:
        print(f"[eval_card_guardrails] 생성 중: {topic['technology_name']}")
        context = ReviewContext(
            technology_name=topic["technology_name"],
            signal_sources=topic["signal_sources"],
        )
        response = llm.generate_card(context)
        rows.append(
            {
                "technology_name": topic["technology_name"],
                "aims_at": topic["aims_at"],
                **summarize_card(response.content),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="입문자 카드 난이도 가드레일 눈 점검")
    parser.add_argument("--output", help="markdown 저장 경로 (미지정 시 stdout)")
    args = parser.parse_args()

    report = render_markdown(run())
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"[eval_card_guardrails] {len(EVAL_TOPICS)} topics → {args.output}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 테스트를 돌려 통과를 확인**

```bash
cd api && python -m pytest tests/test_eval_card_guardrails.py -v
```

Expected: PASS (5 passed)

- [ ] **Step 5: 커밋**

```bash
cd /Users/sgyoo/Desktop/claude-playground/decision-os
git add api/scripts/eval_card_guardrails.py api/tests/test_eval_card_guardrails.py
git commit -m "test(cards): 입문자 카드 가드레일 눈 점검 하네스

가드레일을 겨냥한 토픽 4개로 카드를 실제 생성해 markdown으로 뽑는다.
프롬프트 품질은 유닛 테스트로 안 잡혀 before/after를 눈으로 비교하기 위한 자(尺).
순수 함수만 테스트하고 LLM 실호출은 dev/ops 경로 — eval_engagement.py와 같은 구조."
```

- [ ] **Step 6: before 베이스라인 수집 (프롬프트를 고치기 전에!)**

⚠️ 이 단계를 건너뛰고 Task 2로 넘어가면 비교 대상이 영원히 사라진다.

```bash
cd api && grep -n "^LLM_PROVIDER" .env
```

`LLM_PROVIDER=openai` 가 아니면 아래 실행 전에 `.env`를 openai로 바꾸거나 환경변수로 덮어쓴다.

```bash
cd api && LLM_PROVIDER=openai python -m scripts.eval_card_guardrails \
  --output /private/tmp/claude-501/-Users-sgyoo-Desktop-claude-playground-decision-os/a6d94507-2cc6-4f7a-8e46-79ddd7502446/scratchpad/card-guardrails-before.md
```

Expected: 토픽 4개에 대해 `[eval_card_guardrails] 생성 중: ...` 4줄이 찍히고 마지막에 저장 경로 출력.

- [ ] **Step 7: 베이스라인을 눈으로 읽고 기록**

저장된 markdown을 읽고, 합격 기준 5개 중 어느 것이 깨졌는지 토픽별로 메모해둔다(Task 3의 비교표에 쓴다). 특히 Omarchy 토픽이 다시 셋업형으로 나오는지 확인한다 — 나온다면 문제 재현에 성공한 것이다.

---

### Task 2: 프롬프트에 가드레일 3종 반영

**Files:**
- Modify: `api/pipeline/llm/prompts.py` — `PROJECT_CARD_SYSTEM_PROMPT` (현재 245~287행)

**Interfaces:**
- Consumes: 없음 (문자열 상수만 수정)
- Produces: 없음 (상수 이름·타입 불변, 호출부 무변경)

**이 태스크에는 새 유닛 테스트가 없다.** 프롬프트 문자열을 assert 하는 테스트는 동어반복이라 회귀를 못 잡는다(Global Constraints 참고). 검증은 기존 14개 테스트의 회귀 통과 + Task 3의 눈 점검이다.

- [ ] **Step 1: 변경 전 회귀 기준선 확보**

```bash
cd api && python -m pytest tests/test_project_card_prompt.py tests/test_project_card_generation.py tests/test_card_pipeline.py -v
```

Expected: 전부 PASS. (여기서 이미 실패하는 게 있으면 프롬프트 변경과 무관한 문제이므로 먼저 보고한다.)

- [ ] **Step 2: 1단계의 마지막 불릿을 삭제하고 1.5단계 게이트를 넣는다**

`api/pipeline/llm/prompts.py`에서 아래 한 줄을 **삭제**한다 (1.5단계 게이트에 흡수되므로 중복):

```
- 준비물이 결제나 복잡한 설치를 요구하면, 그 만들거리를 버리고 다시 고릅니다.
```

그리고 `1단계 — ...` 블록과 `2단계 — ...` 블록 **사이**에 빈 줄 하나를 두고 아래를 삽입한다:

```
1.5단계 — 정한 만들거리를 아래 3문항으로 점검합니다. 하나라도 '예'면 그 만들거리를 버리고 1단계로 돌아갑니다.
- 돈이 드나요? 신용카드 등록, 유료 구독, 크레딧 구매가 필요하면 '예'입니다.
- 무거운 설치가 필요한가요? 운영체제·리눅스 배포판·가상머신·도커·데이터베이스 서버 설치나 특정 하드웨어 구매가 필요하면 '예'입니다.
- 만들거리가 '설치·설정·실행' 그 자체인가요? 남이 만든 것을 내 컴퓨터에 올려 돌려보는 일이면 '예'입니다.
```

- [ ] **Step 3: `## 금지 사항`에 셋업형 금칙을 추가한다**

`## 금지 사항` 절의 마지막 불릿(`- 전문용어를 피하고 쉬운 말로 씁니다...`) **앞**에 아래 한 줄을 추가한다:

```
- '○○ 설치하기', '○○ 실행해보기', '○○ 환경 구축하기', '○○ 세팅하기'는 만들거리가 아닙니다. 만들거리는 당신이 코드로 새로 만들어내는 것이어야 합니다. 남이 만든 도구나 운영체제를 내 컴퓨터에 올려 돌려보는 것은, 그 과정이 아무리 길어도 만들거리로 치지 않습니다.
```

- [ ] **Step 4: `## 준비물 규칙` 절을 신설한다**

`## 금지 사항` 절이 끝난 뒤, `반드시 아래 13개 키를 모두 포함한 JSON 객체만 반환하세요...` **앞**에 아래 절을 통째로 삽입한다:

```
## 준비물 규칙

요구해도 되는 것
- 신용카드 없이 발급되는 무료 API 키
- npm / pip 으로 설치하는 패키지
- 웹 브라우저와 텍스트 편집기

요구하면 안 되는 것
- 결제, 신용카드 등록, 유료 구독, 크레딧 구매
- 운영체제·리눅스 배포판·가상머신·도커·데이터베이스 서버 설치
- 하드웨어 구매, 클라우드 서버 배포

prerequisites 작성법
- 아무것도 필요 없으면 "없어요, 바로 시작!"
- 무료 키가 필요하면 '어디서 어떻게 받는지'를 한 줄로 적습니다. '(서비스명) API 키 필요'처럼 막연히 적지 마세요. 예: "Google AI Studio에서 구글 계정으로 로그인하면 무료 키를 바로 받을 수 있어요 — 신용카드는 필요 없어요." (예시일 뿐이니 카드에 맞는 곳을 적으세요)
- AI 코딩 도구(Claude Code 등)는 모든 카드의 공통 전제입니다. 준비물에 적지 마세요.
- 이미 갖고 있을 법한 것(컴퓨터, 인터넷, 터미널 기본 사용법)도 적지 마세요. 겁만 줍니다.
```

- [ ] **Step 5: 회귀 테스트 통과 확인**

```bash
cd api && python -m pytest tests/test_project_card_prompt.py tests/test_project_card_generation.py tests/test_card_pipeline.py -v
```

Expected: Step 1과 동일하게 전부 PASS. (검증 로직을 안 건드렸으므로 결과가 달라지면 실수로 프롬프트 밖을 고친 것이다.)

- [ ] **Step 6: 전체 테스트 스위트 회귀 확인**

```bash
cd api && python -m pytest -q
```

Expected: 변경 전과 동일한 pass/fail 구성. 새로 깨지는 테스트가 있으면 멈추고 보고한다.

- [ ] **Step 7: 커밋**

```bash
cd /Users/sgyoo/Desktop/claude-playground/decision-os
git add api/pipeline/llm/prompts.py
git commit -m "feat(cards): 카드 생성에 완주 가능성 게이트·셋업형 금칙·준비물 규칙

프로덕션 카드 3장 중 2장이 'Omarchy 실행하기'(= 설치 작업)로 나왔다.
기존 방어선은 '준비물'을 필터링해 만들거리 자체의 성격을 못 걸렀다.

- 1.5단계 완주 가능성 게이트 신설 (돈/무거운 설치/설치가 만들거리인가)
- 금지 사항에 '남의 것 돌리기 금지' 추가
- 준비물 화이트리스트 + prerequisites 작성법 명시

스키마·검증·웹·DB 무변경. 하드 검증은 실패 화면 리스크 때문에 추가하지 않음."
```

---

### Task 3: after 수집 + before/after 비교 기록

**Files:**
- Modify: `docs/superpowers/specs/2026-09-04-beginner-card-difficulty-guardrails-design.md` (문서 끝에 결과 절 추가)

**Interfaces:**
- Consumes: Task 1의 `scripts/eval_card_guardrails.py`, Task 1 Step 6이 남긴 `card-guardrails-before.md`
- Produces: 없음 (문서만)

- [ ] **Step 1: after 리포트 수집**

```bash
cd api && LLM_PROVIDER=openai python -m scripts.eval_card_guardrails \
  --output /private/tmp/claude-501/-Users-sgyoo-Desktop-claude-playground-decision-os/a6d94507-2cc6-4f7a-8e46-79ddd7502446/scratchpad/card-guardrails-after.md
```

Expected: 토픽 4개 생성 완료 후 저장 경로 출력.

- [ ] **Step 2: 두 리포트를 나란히 읽고 합격 기준 5개로 판정**

```bash
cd /private/tmp/claude-501/-Users-sgyoo-Desktop-claude-playground-decision-os/a6d94507-2cc6-4f7a-8e46-79ddd7502446/scratchpad
diff -y --width=200 card-guardrails-before.md card-guardrails-after.md | head -80
```

토픽 4개 × 합격 기준 5개를 표로 정리한다. **기준 5(3b 회귀)를 특히 본다** — 금칙이 늘어 LLM이 개념체험형으로 도피해 카드가 토픽과 멀어졌다면 그것도 실패다(스펙의 '리스크' 절).

- [ ] **Step 3: 스펙 문서 끝에 결과 절을 추가**

`docs/superpowers/specs/2026-09-04-beginner-card-difficulty-guardrails-design.md` 맨 아래에 아래 형태로 추가한다. `<...>` 자리는 Step 2에서 실제로 읽은 값으로 채운다 — 요약하지 말고 `project_title`과 `prerequisites`는 원문 그대로 옮긴다.

```markdown
## 눈 점검 결과 (2026-09-04, LLM_PROVIDER=openai)

| 토픽 | before — project_title / prerequisites | after — project_title / prerequisites | 판정 |
|---|---|---|---|
| Omarchy | <원문> | <원문> | <합격 기준 중 통과·실패> |
| SK하이닉스 HBM4 | <원문> | <원문> | <...> |
| Vercel Pro 가격 | <원문> | <원문> | <...> |
| Claude Opus 5 | <원문> | <원문> | <...> |

**종합**: <4장 전부 합격 / 몇 번 기준이 어느 토픽에서 깨졌는지>

**남은 문제**: <없으면 "없음". 있으면 다음 슬라이스 후보로 한 줄씩>
```

- [ ] **Step 4: 커밋**

```bash
cd /Users/sgyoo/Desktop/claude-playground/decision-os
git add docs/superpowers/specs/2026-09-04-beginner-card-difficulty-guardrails-design.md
git commit -m "docs(spec): 가드레일 눈 점검 before/after 결과 기록"
```

- [ ] **Step 5: 오너에게 인계**

아래를 보고한다:
1. 합격 기준 5개 × 토픽 4개 판정 결과 (통과 여부를 단정적으로)
2. 깨진 기준이 있으면 그 카드의 `project_title` / `prerequisites` 원문
3. **오너가 직접 화면 확인을 원한다는 점**을 감안해, 로컬에서 카드를 화면으로 보려면 `.env`에 `BEGINNER_CARD_MODE_ENABLED=true`가 필요하다는 사실 (프로덕션은 OFF라 배포해도 실사용자 화면에는 안 나타난다)

PR 생성은 오너의 화면 확인 뒤로 미룬다 — 추가 개선을 같은 브랜치에 얹을 예정이기 때문이다.
