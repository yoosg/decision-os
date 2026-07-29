"""Story 6.5 — 오프라인 engagement 평가 하네스 (held-out: RAG 재랭킹 vs 콜드스타트).

무엇을:
    engagement_events(+ outcomes)를 읽어, impression의 variant(rag | coldstart)로 코호트를 나눈 뒤
    variant별 engagement 지표를 계산해 표로 출력한다. "6.1~6.4의 랭킹 고도화가 실제로 추천 품질을
    올렸는가?"를 감이 아니라 데이터로 보기 위한 자(尺)다. 이 스크립트는 자를 대서 **읽기만** 한다 —
    랭킹 로직·가중치·λ를 **바꾸지 않는다**(6.5 스코프 경계).

지표 정의(자세한 분자/분모/출처는 api/scripts/METRICS.md):
    - CTR              = opens / impressions
    - read-through율   = read_through / opens
    - Learn Now율       = learn_now decisions / impressions
    - Outcome 유용도    = useful=true / (completed·applied outcomes)

⚠️ 한계(반드시 인지): 이것은 **무작위 A/B가 아니라 관찰적 cohort 비교**다. variant는 무작위 배정이
    아니라 "Memory 보유 → rag / 미보유 → coldstart"로 이미 갈라진 두 집단이다. Memory 보유 사용자는
    원래 더 활발할 수 있어(선택 편향) engagement가 높게 나올 수 있다. 엄밀한 인과는 향후 무작위
    실험(deferred)에서. → 리포트 헤더에도 이 문구를 출력한다.

실행:
    cd api && python -m scripts.eval_engagement                 # stdout 표
    cd api && python -m scripts.eval_engagement --output out.json   # JSON 저장
    cd api && python -m scripts.eval_engagement --output out.md     # markdown 저장

지표 계산부(compute_metrics)는 순수 함수라 합성 이벤트로 단위 테스트된다(test_eval_engagement.py).
DB 읽기(load_*)는 dev/ops 실행 경로 — service_role 읽기 전용(AD-11의 "테스트" 아님).
"""
from __future__ import annotations

import argparse
import json
from typing import Any

_COHORT_DISCLAIMER = (
    "⚠️ 관찰적 cohort 비교(무작위 A/B 아님). variant는 Memory 보유 여부로 이미 갈라진 두 집단이며 "
    "선택 편향(활발한 사용자일수록 Memory 보유·engagement↑)이 있을 수 있다. 인과 아님."
)

_OUTCOME_CONSIDERED_STATUSES = ("completed", "applied")


def _ratio(numerator: int, denominator: int) -> float | str:
    """분모 0 방어: 변별 불가 시 None/NaN 대신 명시적 'n/a'(문자열)를 반환해 표에서 가시화."""
    if denominator == 0:
        return "n/a"
    return numerator / denominator


def compute_metrics(
    events: list[dict[str, Any]], outcomes: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """variant별 engagement 지표를 계산하는 순수 함수(오프라인 결정적).

    입력:
      events: engagement_events 행. 각 dict는 최소 event_type·user_id·signal_id 보유.
              impression 행은 variant('rag'|'coldstart') 보유(정본). open/read_through/decision은
              variant 없음 → (user_id, signal_id)로 impression variant를 조회해 attach(D5).
              decision 행은 metadata.choice('learn_now'|'queue'|'ignore') 보유.
      outcomes: 각 dict는 status·useful + (user_id, signal_id)(변별용 — eval 스크립트가 조인해 채움).

    반환: {variant: {카운트들 + ctr·read_through_rate·learn_now_rate·outcome_usefulness}}.
      impression variant가 없는 이벤트/outcome은 'unknown' 버킷으로 분리(누락 대신 가시화, D5).
    """
    # 1) impression에서 (user_id, signal_id) → variant 정본 맵 구성.
    #    같은 (user, signal)이 여러 brief에 서로 다른 variant로 재노출되면(D5 다중-brief 모호성)
    #    마지막 값으로 덮어쓰지 않고 'unknown'으로 분리해 다운스트림 이벤트의 오귀속을 방지·가시화한다.
    variant_by_key: dict[tuple, str] = {}
    for e in events:
        if e.get("event_type") == "impression":
            key = (e.get("user_id"), e.get("signal_id"))
            v = e.get("variant") or "unknown"
            if key in variant_by_key and variant_by_key[key] != v:
                variant_by_key[key] = "unknown"  # variant 충돌 → 코호트 미상으로 분리
            else:
                variant_by_key[key] = v

    def variant_of(row: dict[str, Any]) -> str:
        return variant_by_key.get((row.get("user_id"), row.get("signal_id")), "unknown")

    buckets: dict[str, dict[str, int]] = {}

    def bucket(v: str) -> dict[str, int]:
        return buckets.setdefault(
            v,
            {
                "impressions": 0,
                "opens": 0,
                "read_throughs": 0,
                "learn_now": 0,
                "outcomes_considered": 0,
                "outcomes_useful": 0,
            },
        )

    # 2) 이벤트 집계
    for e in events:
        et = e.get("event_type")
        if et == "impression":
            bucket(e.get("variant") or "unknown")["impressions"] += 1
        elif et == "open":
            bucket(variant_of(e))["opens"] += 1
        elif et == "read_through":
            bucket(variant_of(e))["read_throughs"] += 1
        elif et == "decision":
            if (e.get("metadata") or {}).get("choice") == "learn_now":
                bucket(variant_of(e))["learn_now"] += 1

    # 3) outcome 유용도 집계(완료·적용된 것 중 useful=true 비율)
    for o in outcomes:
        if o.get("status") in _OUTCOME_CONSIDERED_STATUSES:
            b = bucket(variant_by_key.get((o.get("user_id"), o.get("signal_id")), "unknown"))
            b["outcomes_considered"] += 1
            if o.get("useful") is True:
                b["outcomes_useful"] += 1

    # 4) 비율 파생(분모 0 방어)
    result: dict[str, dict[str, Any]] = {}
    for v, c in buckets.items():
        result[v] = {
            **c,
            "ctr": _ratio(c["opens"], c["impressions"]),
            "read_through_rate": _ratio(c["read_throughs"], c["opens"]),
            "learn_now_rate": _ratio(c["learn_now"], c["impressions"]),
            "outcome_usefulness": _ratio(c["outcomes_useful"], c["outcomes_considered"]),
        }
    return result


def _fmt(value: Any) -> str:
    return f"{value:.3f}" if isinstance(value, float) else str(value)


def render_table(metrics: dict[str, dict[str, Any]]) -> str:
    """variant별 지표를 사람이 읽는 표(문자열)로 렌더 — cohort 한계 문구 포함."""
    lines = ["# Engagement 평가 리포트 (RAG vs 콜드스타트)", "", _COHORT_DISCLAIMER, ""]
    cols = [
        ("variant", "variant"),
        ("impressions", "impressions"),
        ("opens", "opens"),
        ("read_throughs", "read_throughs"),
        ("learn_now", "learn_now"),
        ("ctr", "CTR"),
        ("read_through_rate", "read-through율"),
        ("learn_now_rate", "Learn Now율"),
        ("outcome_usefulness", "Outcome 유용도"),
    ]
    header = " | ".join(label for _key, label in cols)
    lines.append(header)
    lines.append(" | ".join("---" for _ in cols))
    for variant in sorted(metrics.keys()):
        row = metrics[variant]
        cells = []
        for key, _label in cols:
            cells.append(variant if key == "variant" else _fmt(row.get(key, "n/a")))
        lines.append(" | ".join(cells))
    return "\n".join(lines)


# ── DB 로더(dev/ops 실행 경로 — service_role 읽기 전용) ─────────────────────────

_PAGE_SIZE = 1000


def _load_all(client, table: str, columns: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        batch = (
            client.table(table)
            .select(columns)
            .range(offset, offset + _PAGE_SIZE - 1)
            .execute()
            .data
            or []
        )
        rows.extend(batch)
        if len(batch) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE
    return rows


def load_engagement_events(client) -> list[dict[str, Any]]:
    return _load_all(
        client, "engagement_events", "event_type,user_id,signal_id,variant,metadata,created_at"
    )


def load_outcomes_enriched(client) -> list[dict[str, Any]]:
    """outcomes를 (user_id, signal_id)로 보강 — outcome→decision→review→project 조인.

    outcomes.decision_id → decisions.review_id → reviews.(signal_id, project_id) → projects.user_id.
    """
    outcomes = _load_all(client, "outcomes", "status,useful,decision_id")
    decisions = {d["id"]: d for d in _load_all(client, "decisions", "id,review_id")}
    reviews = {r["id"]: r for r in _load_all(client, "reviews", "id,signal_id,project_id")}
    projects = {p["id"]: p for p in _load_all(client, "projects", "id,user_id")}

    enriched: list[dict[str, Any]] = []
    for o in outcomes:
        dec = decisions.get(o.get("decision_id"))
        rev = reviews.get(dec.get("review_id")) if dec else None
        proj = projects.get(rev.get("project_id")) if rev else None
        enriched.append(
            {
                "status": o.get("status"),
                "useful": o.get("useful"),
                "signal_id": rev.get("signal_id") if rev else None,
                "user_id": proj.get("user_id") if proj else None,
            }
        )
    return enriched


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="engagement held-out 평가 리포트 (rag vs coldstart)")
    parser.add_argument(
        "--output", metavar="PATH", default=None, help="결과 저장 경로(.json 또는 .md). 미지정 시 stdout 표"
    )
    args = parser.parse_args(argv)

    if args.output and not (args.output.endswith(".json") or args.output.endswith(".md")):
        print(
            f"[eval_engagement] 미지원 출력 확장자: {args.output} — .json 또는 .md만 지원합니다."
        )
        return 2

    from core.supabase import get_supabase

    client = get_supabase()
    events = load_engagement_events(client)
    outcomes = load_outcomes_enriched(client)
    metrics = compute_metrics(events, outcomes)

    if args.output and args.output.endswith(".json"):
        payload = {"disclaimer": _COHORT_DISCLAIMER, "metrics": metrics}
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[eval_engagement] {len(events)} events, {len(outcomes)} outcomes → {args.output}")
    else:
        table = render_table(metrics)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(table + "\n")
            print(f"[eval_engagement] {len(events)} events, {len(outcomes)} outcomes → {args.output}")
        else:
            print(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
