"""Story 6.5 — 오프라인 평가 하네스 compute_metrics 순수함수 테스트.

합성 이벤트로 결정적 검증(실 DB·실 네트워크 금지). variant별 CTR/read-through/Learn Now율/유용도 +
분모 0 방어 + variant 조인(D5) + unknown 버킷을 검증한다.
"""
from scripts.eval_engagement import compute_metrics, main

U = "user-1"
S1 = "sig-1"
S2 = "sig-2"


def _impression(user, signal, variant):
    return {"event_type": "impression", "user_id": user, "signal_id": signal, "variant": variant}


def _event(etype, user, signal, **meta):
    row = {"event_type": etype, "user_id": user, "signal_id": signal}
    if meta:
        row["metadata"] = meta
    return row


def test_ctr_and_read_through_by_variant():
    """CTR = opens/impressions, read-through율 = read_through/opens — variant별로 분리 집계."""
    events = [
        _impression(U, S1, "rag"),
        _impression(U, S2, "coldstart"),
        _event("open", U, S1),            # rag open
        _event("read_through", U, S1),    # rag read_through
        # S2(coldstart)는 open 없음
    ]
    m = compute_metrics(events, [])
    assert m["rag"]["impressions"] == 1
    assert m["rag"]["opens"] == 1
    assert m["rag"]["ctr"] == 1.0
    assert m["rag"]["read_through_rate"] == 1.0
    assert m["coldstart"]["impressions"] == 1
    assert m["coldstart"]["opens"] == 0
    assert m["coldstart"]["ctr"] == 0.0  # 0/1


def test_learn_now_rate_counts_only_learn_now_decisions():
    """Learn Now율 = learn_now decision/impressions. queue·ignore는 분자에서 제외."""
    events = [
        _impression(U, S1, "rag"),
        _impression(U, S2, "rag"),
        _event("decision", U, S1, choice="learn_now"),
        _event("decision", U, S2, choice="ignore"),
    ]
    m = compute_metrics(events, [])
    assert m["rag"]["impressions"] == 2
    assert m["rag"]["learn_now"] == 1
    assert m["rag"]["learn_now_rate"] == 0.5


def test_variant_attached_to_decision_via_impression_join():
    """decision 이벤트는 variant가 없어도 (user_id, signal_id)로 impression variant를 attach(D5)."""
    events = [
        _impression(U, S1, "coldstart"),
        _event("decision", U, S1, choice="learn_now"),  # variant 필드 없음 → coldstart로 귀속
    ]
    m = compute_metrics(events, [])
    assert m["coldstart"]["learn_now"] == 1
    assert "rag" not in m  # rag impression 없음


def test_outcome_usefulness_ratio():
    """Outcome 유용도 = useful=true / (completed·applied outcomes). dropped/not_useful은 분모 제외."""
    events = [_impression(U, S1, "rag")]
    outcomes = [
        {"status": "completed", "useful": True, "user_id": U, "signal_id": S1},
        {"status": "applied", "useful": False, "user_id": U, "signal_id": S1},
        {"status": "dropped", "useful": None, "user_id": U, "signal_id": S1},  # 분모 제외
    ]
    m = compute_metrics(events, outcomes)
    assert m["rag"]["outcomes_considered"] == 2
    assert m["rag"]["outcomes_useful"] == 1
    assert m["rag"]["outcome_usefulness"] == 0.5


def test_zero_denominator_returns_na():
    """분모 0 → None/NaN 대신 명시적 'n/a'(변별 불가 가시화)."""
    events = [_impression(U, S1, "rag")]  # opens 0, outcomes 0
    m = compute_metrics(events, [])
    assert m["rag"]["ctr"] == 0.0          # opens/impressions = 0/1 (분모>0)
    assert m["rag"]["read_through_rate"] == "n/a"  # read_through/opens = ?/0
    assert m["rag"]["outcome_usefulness"] == "n/a"  # ?/0


def test_events_without_impression_go_to_unknown_bucket():
    """impression 없이 후속 이벤트만 있으면 'unknown' 버킷으로 분리(누락 아님, D5)."""
    events = [_event("open", U, S1)]  # 대응 impression 없음
    m = compute_metrics(events, [])
    assert "unknown" in m
    assert m["unknown"]["opens"] == 1


def test_empty_inputs_return_empty():
    """이벤트·outcome 없으면 빈 dict."""
    assert compute_metrics([], []) == {}


def test_conflicting_variant_for_same_key_goes_unknown():
    """같은 (user, signal)이 서로 다른 variant로 재노출되면(D5 다중-brief 모호성) 후속 이벤트는
    마지막 값으로 덮어쓰지 않고 'unknown'으로 분리(오귀속 방지·가시화 — 코드리뷰 2026-07-29)."""
    events = [
        _impression(U, S1, "coldstart"),  # 1일차: memory 없음
        _impression(U, S1, "rag"),        # N일차: memory 생김 → 같은 시그널 재노출
        _event("decision", U, S1, choice="learn_now"),
    ]
    m = compute_metrics(events, [])
    # impression은 각자 실제 variant로 카운트(정본 유지)
    assert m["rag"]["impressions"] == 1
    assert m["coldstart"]["impressions"] == 1
    # 후속 decision은 코호트 미상 → 'unknown'(rag/coldstart 어느 쪽에도 귀속 안 함)
    assert m["unknown"]["learn_now"] == 1
    assert m["rag"]["learn_now"] == 0
    assert m["coldstart"]["learn_now"] == 0


def test_main_rejects_unsupported_output_extension(tmp_path):
    """--output이 .json/.md가 아니면 무음으로 잘못된 포맷을 쓰지 않고 비정상 종료(exit 2)."""
    bad = tmp_path / "out.txt"
    rc = main(["--output", str(bad)])
    assert rc == 2
    assert not bad.exists()  # DB 접근 전에 반환 — 파일 미생성
