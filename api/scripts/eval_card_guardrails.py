"""입문자 카드 난이도 가드레일 — 눈 점검 하네스.

무엇을:
    가드레일이 뚫렸던 자리를 겨냥한 토픽 4개로 가짜 ReviewContext를 만들고 llm.generate_card()를
    직접 호출해, 눈 점검에 쓰는 필드만 markdown으로 뽑는다. 시그널 DB도 파이프라인도 타지 않는다.
    "프롬프트 규칙이 실제로 먹히는가"는 유닛 테스트로 잡히지 않아 사람이 눈으로 본다.

    프롬프트를 고치기 전/후로 한 번씩 돌려 나란히 비교하는 것이 이 스크립트의 용도다.
    P1(마일스톤)·P2(체크리스트) 슬라이스에서는 EVAL_TOPICS만 바꿔 재사용한다.

⚠️ 반드시 LLM_PROVIDER=openai 로 실행한다. 프로덕션이 openai라, gemini로 보면 실제 배포되는 것과
    다른 모델을 검수하는 셈이 된다. --allow-non-openai 없이는 openai가 아닌 프로바이더로 아예
    호출하지 않는다(잘못된 모델로 유료 호출 4회를 태우는 사고를 막기 위함).

실행:
    cd api && python -m scripts.eval_card_guardrails                      # stdout
    cd api && python -m scripts.eval_card_guardrails --output before.md   # markdown 저장
    cd api && python -m scripts.eval_card_guardrails --allow-non-openai   # openai 아닌 프로바이더로도 강행

순수 함수(summarize_card·render_markdown)만 test_eval_card_guardrails.py에서 테스트한다.
LLM 실호출(run)은 dev/ops 실행 경로다.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from pipeline.llm.base import LLMProviderError, ReviewContext

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

# topic_link·skill_label: 스펙 리스크 절의 "도피(개념체험형 우회)" 신호를 잡으려면 토픽 연결을
# 보여주는 필드가 있어야 한다(I3) — deliverable만으로는 판정을 추론해야 했다.
_SUMMARY_FIELDS = (
    "project_title",
    "topic_link",
    "skill_label",
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

    파싱 실패나 필드 누락에도 예외를 올리지 않는다. generate_card()는 내부에서 이미
    parse_and_validate_card로 검증하므로(api/pipeline/llm/openai_provider.py) *성공한* 호출의
    raw는 항상 온전한 JSON이다 — 즉 run()의 정상 경로에서는 이 함수가 malformed 입력을 볼 일이
    없다. 이 방어는 그래서 run()을 위한 것이 아니라, summarize_card를 테스트나 향후 호출부에서
    직접 부를 때(예: 사람이 손으로 만든 응답을 눈 점검에 끼워 넣을 때)를 위한 것이다.

    "토픽 하나가 죽어도 나머지 3개 수집이 중단되지 않아야 한다"는 요구는 이 함수가 아니라
    run()의 try/except가 책임진다(generate_card가 raise하는 LLMProviderError는 여기 도달하기
    전에 이미 발생하므로, 이 함수의 방어로는 애초에 막을 수 없다).
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        return {field: f"<JSON 파싱 실패: {e}>" for field in _SUMMARY_FIELDS}
    if not isinstance(parsed, dict):
        return {field: f"<JSON 객체 아님: {type(parsed).__name__}>" for field in _SUMMARY_FIELDS}
    return {field: str(parsed.get(field, "<누락>")) for field in _SUMMARY_FIELDS}


def _fmt_minutes(value: str) -> str:
    """estimated_minutes가 누락/파싱실패 마커(<...>)면 '분'을 붙이지 않는다(M4)."""
    if value.startswith("<"):
        return value
    return f"{value}분"


def render_markdown(rows: list[dict[str, str]], meta: dict[str, str] | None = None) -> str:
    """토픽별 카드 요약을 markdown 리포트로 렌더하는 순수 함수.

    meta: {"provider", "model", "generated_at"} — 리포트만 보고도 어떤 프로바이더/모델/시각의
    결과인지 알 수 있어야 한다(I2). eval_engagement.py의 render_table이 cohort 한계 문구를
    헤더에 찍는 선례를 따른다.
    """
    out: list[str] = ["# 입문자 카드 가드레일 눈 점검", ""]
    if meta:
        out.append(
            f"⚠️ provider={meta.get('provider', 'n/a')} · model={meta.get('model', 'n/a')} · "
            f"생성 시각={meta.get('generated_at', 'n/a')}"
        )
        out.append("")
    out.append(_PASS_CRITERIA)
    out.append("")
    for row in rows:
        out.append(f"## {row['technology_name']}")
        out.append("")
        out.append(f"- **노리는 실패**: {row['aims_at']}")
        out.append(f"- **project_title**: {row['project_title']}")
        out.append(f"- **topic_link**: {row['topic_link']}")
        out.append(f"- **skill_label**: {row['skill_label']}")
        out.append(
            f"- **difficulty / estimated_minutes**: {row['difficulty']} / {_fmt_minutes(row['estimated_minutes'])}"
        )
        out.append(f"- **prerequisites**: {row['prerequisites']}")
        out.append(f"- **deliverable**: {row['deliverable']}")
        out.append("")
    return "\n".join(out)


def run(allow_non_openai: bool = False) -> tuple[list[dict[str, str]], dict[str, str]]:
    """토픽마다 카드를 1장씩 생성한다 (LLM 실호출 — dev/ops 경로).

    generate_card()가 던지는 LLMProviderError(타임아웃·429 등)를 토픽 단위로 잡아 실패 행으로
    기록하고 다음 토픽으로 넘어간다 — 이 try/except가 없으면 4번째 토픽에서 죽었을 때 이미
    유료로 받아둔 앞선 3장의 카드까지 함께 버려진다(I1).
    """
    from core.config import settings
    from pipeline.llm.factory import get_llm_provider

    if settings.llm_provider != "openai" and not allow_non_openai:
        print(
            f"⛔ LLM_PROVIDER={settings.llm_provider} — 프로덕션은 openai다. openai가 아닌 프로바이더로는 "
            "호출하지 않는다(잘못된 모델로 유료 호출 4회를 태우는 사고 방지). 의도적으로 점검하려면 "
            "--allow-non-openai를 붙여라."
        )
        raise SystemExit(2)

    llm = get_llm_provider()
    rows: list[dict[str, str]] = []
    model = ""
    for topic in EVAL_TOPICS:
        print(f"[eval_card_guardrails] 생성 중: {topic['technology_name']}")
        context = ReviewContext(
            technology_name=topic["technology_name"],
            signal_sources=topic["signal_sources"],
        )
        try:
            response = llm.generate_card(context)
        except LLMProviderError as e:
            print(f"[eval_card_guardrails] 실패: {topic['technology_name']} — {e}")
            rows.append(
                {
                    "technology_name": topic["technology_name"],
                    "aims_at": topic["aims_at"],
                    **{field: f"<생성 실패: {e}>" for field in _SUMMARY_FIELDS},
                }
            )
            continue
        model = response.model or model
        rows.append(
            {
                "technology_name": topic["technology_name"],
                "aims_at": topic["aims_at"],
                **summarize_card(response.content),
            }
        )

    meta = {
        "provider": settings.llm_provider,
        "model": model or "n/a",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    return rows, meta


def main() -> int:
    parser = argparse.ArgumentParser(description="입문자 카드 난이도 가드레일 눈 점검")
    parser.add_argument("--output", help="markdown 저장 경로 (미지정 시 stdout)")
    parser.add_argument(
        "--allow-non-openai",
        action="store_true",
        help="LLM_PROVIDER가 openai가 아니어도 강행한다(기본은 호출 없이 종료)",
    )
    args = parser.parse_args()

    rows, meta = run(allow_non_openai=args.allow_non_openai)
    report = render_markdown(rows, meta)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"[eval_card_guardrails] {len(EVAL_TOPICS)} topics → {args.output}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
