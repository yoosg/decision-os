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
