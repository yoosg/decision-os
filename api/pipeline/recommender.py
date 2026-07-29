from __future__ import annotations

import math
from datetime import date, datetime, timezone, timedelta

from supabase import Client

from pipeline.engagement import log_engagement_bulk
from pipeline.llm.base import LLMProvider
from pipeline.logger import pipeline_log

_PAGE_SIZE = 1000

# Memory RAG (Story 5.4) — 콜드 스타트 점수에 가산되는 코사인 유사도 가중치.
# base(0.1~1.0) + _RAG_WEIGHT * top_similarity(0~1) → clamp(0.1, 1.0).
# memory 보유 사용자가 콜드 스타트보다 개인화되도록 양수, 불변식 유지 위해 clamp.
#
# ⚠️ Story 6.4 스케일 정합성 주석: v1에서 base는 substring 카운트(0.1/0.4/0.7/1.0 이산)였다.
# v2에서 base는 프로필·시그널 임베딩 코사인(연속 0.1~1.0, 실무상 0.1~0.6 밀집)으로 바뀌었으므로
# `base + 0.5*top_sim`의 상대 균형이 달라진다(코사인 base가 작아 RAG 항 영향이 상대적으로 커질 여지).
# 이 스토리에선 값(0.5)을 유지한다 — 최적 weight는 근거 없는 임의 튜닝이 아니라 6.5 held-out
# engagement 측정으로 확정한다(D2). 향후 정규화 블렌드 `(1-w)*cold + w*sim`으로의 리팩터는 6.5 이후.
_RAG_WEIGHT = 0.5
# match_memories RPC가 반환할 memory 수. 블렌딩은 top_similarity 최댓값만 사용하므로
# (거리 오름차순 정렬의 최근접 1행 = 최대 유사도) 1이면 충분하다. 상위 4행 조회/직렬화
# 낭비를 제거 (코드리뷰 2026-07-28). 향후 top-k 평균 블렌딩 채택 시 이 값을 늘린다.
_RAG_MATCH_COUNT = 1

# ── Story 6.4: 랭킹 피처 가중치 (초기값 — 6.5 측정으로 튜닝, 상수로 분리) ──────────────
# combined = clamp(0.1, 1.0, _W_RELEVANCE*base + _W_RECENCY*recency + _W_POPULARITY*pop + _W_AUTHORITY*auth)
# 합=1.0. base(관련도)가 지배적이되 최신성·인기·권위가 보조 신호로 결합된다.
_W_RELEVANCE = 0.70
_W_RECENCY = 0.15
_W_POPULARITY = 0.10
_W_AUTHORITY = 0.05
# 최신성 감쇠 반감기(일): published_at이 이 일수만큼 지날 때마다 recency_norm이 절반이 된다.
_RECENCY_HALFLIFE_DAYS = 7
# MMR 다양성 계수: mmr = λ*combined − (1−λ)*max_sim. λ가 클수록 관련도 우선, 작을수록 다양성 우선.
_MMR_LAMBDA = 0.7


def _clamp(x: float) -> float:
    """relevance_score 불변식: [0.1, 1.0]로 강제 (daily_brief_signals.relevance_score는 DB CHECK 없음)."""
    return max(min(x, 1.0), 0.1)


def _norm(vec: list[float]) -> float:
    """순수 파이썬 L2 노름 (numpy 금지 — AD-2/AD-6, clustering.py L61-63과 동일 시그니처, D3)."""
    return math.sqrt(sum(x * x for x in vec))


def _cosine(a: list[float], b: list[float], norm_a: float, norm_b: float) -> float:
    """순수 파이썬 코사인 유사도. norm은 미리 계산해 전달(반복 최적화). clustering.py L65-73과 동일."""
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (norm_a * norm_b)


def _as_float(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    # NaN/inf 방어: 랭킹 피처(popularity/authority)로 흘러들면 combined가 NaN으로 오염되어
    # 정렬·MMR 비교 교란 + relevance_score에 NaN 기록(프런트 0~1 가정 위반). (코드리뷰 2026-07-29)
    if math.isnan(f) or math.isinf(f):
        return 0.0
    return f


def _parse_dt(value) -> datetime:
    """ISO 문자열/날짜를 aware datetime(UTC)로 방어적 파싱 (D5). naive는 UTC로 간주, 'Z' 접미 지원."""
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _recency_norm(published_at, brief_date: str) -> float:
    """최신성 감쇠 [0,1]. published_at None/파싱실패 → 0.5(중립, AD-5). 미래 timestamp → 1.0 캡."""
    if not published_at:
        return 0.5
    try:
        pub = _parse_dt(published_at)
        ref = _parse_dt(brief_date)
    except Exception:
        return 0.5
    age_days = (ref - pub).total_seconds() / 86400.0
    if age_days < 0:
        return 1.0
    # 0 나눗셈 방어: 반감기 상수는 6.5 튜닝으로 값 편집이 예고됨 → 0이면 1로 폴백. (코드리뷰 2026-07-29)
    halflife = _RECENCY_HALFLIFE_DAYS or 1
    return 0.5 ** (age_days / halflife)


def _popularity_norm(popularity, batch_max_logpop: float) -> float:
    """인기 로그 정규화 [0,1]. 배치 내 최대 log1p 대비 상대값. batch_max=0이면 0."""
    p = _as_float(popularity)
    if p <= 0 or batch_max_logpop <= 0:
        return 0.0
    return min(math.log1p(p) / batch_max_logpop, 1.0)


def _authority_norm(source_authority) -> float:
    """출처 권위 정규화 [0,1]. 0~4 등급 → /4.0. None → 0."""
    return max(min(_as_float(source_authority) / 4.0, 1.0), 0.0)


def _embed_profile(user_profile: dict, llm: LLMProvider, brief_date: str) -> list[float] | None:
    """프로필(tech_stack + interests)을 1회 임베딩 → 콜드 스타트 코사인 base용 벡터.

    빈 프로필/임베딩 실패 → None(로깅, safe-degrade → substring 폴백). 사용자당 1회만 호출(설계 A-2).
    """
    parts = list(user_profile.get("tech_stack") or []) + list(user_profile.get("interests") or [])
    text = " ".join(str(p) for p in parts if p).strip()
    if not text:
        return None
    try:
        return llm.embed_text(text)
    except Exception as e:
        pipeline_log(
            stage="recommender",
            brief_date=brief_date,
            user_count=0,
            level="warning",
            event="profile_embed_failed",
            error=str(e)[:200],
        )
        return None


def compute_relevance_score_v2(
    signal_emb: list[float], signal_norm: float, profile_emb: list[float], profile_norm: float
) -> float:
    """콜드 스타트 v2 관련도: 프로필·시그널 임베딩 코사인 → clamp[0.1,1.0]. substring 매칭 완전 제거(AC1)."""
    return _clamp(_cosine(signal_emb, profile_emb, signal_norm, profile_norm))


def _mmr_rerank(
    items: list[tuple[str, float, list[float] | None, float]], lambda_: float = _MMR_LAMBDA
) -> list[tuple[str, float]]:
    """MMR greedy 재랭킹 (AC3). items=[(signal_id, combined, emb|None, norm)].

    매 라운드 mmr = λ*combined − (1−λ)*max_{선택됨} cosine. 최고 mmr 선택, 동점은 signal_id 오름차순.
    임베딩 없는(norm 0) 시그널은 중복 페널티 0 → 탈락 없이 순서만 뒤로(AD-5). 반환은 (signal_id, combined).
    """
    remaining = list(items)
    selected_embs: list[tuple[list[float], float]] = []
    result: list[tuple[str, float]] = []
    while remaining:
        best = None
        best_key: tuple[float, str] | None = None
        for entry in remaining:
            sid, combined, emb, norm = entry
            if emb is not None and norm > 0 and selected_embs:
                max_sim = max(_cosine(emb, semb, norm, snorm) for semb, snorm in selected_embs)
            else:
                max_sim = 0.0
            mmr = lambda_ * combined - (1 - lambda_) * max_sim
            key = (-mmr, sid)  # mmr 최대화, 동점 signal_id 오름차순 tie-break(결정론)
            if best_key is None or key < best_key:
                best_key = key
                best = entry
        remaining.remove(best)
        sid, combined, emb, norm = best
        result.append((sid, combined))
        if emb is not None and norm > 0:
            selected_embs.append((emb, norm))
    return result


def compute_relevance_score(signal: dict, user_profile: dict) -> float:
    """[v1 FALLBACK ONLY — Story 6.4] substring 키워드 매칭 콜드 스타트 점수.

    ⚠️ 정상(llm 주입) 경로에서는 절대 사용하지 않는다. AC1이 요구한 "substring 매칭 제거"는
    정상 경로에서 substring이 관여하지 않게 하라는 뜻이며(D1), 정상 경로 base는
    compute_relevance_score_v2(프로필·시그널 임베딩 코사인)로 계산된다.
    이 함수는 AD-5 안전 저하용으로만 남는다: `llm is None`(단위 테스트·오프라인) 또는
    프로필 임베딩 불가 시, flat 0.1로 뭉개지지 않도록 순위를 보존하는 폴백.
    (오매칭 예: tech="go"가 "google"에 substring 매칭 — 이 함수의 한계이자 v2 전환 이유.)

    tech_stack 매칭: +0.4/개, interests 매칭: +0.3/개
    최솟값 0.1 (콜드 스타트 — 매칭 없어도 브리프에 포함)
    최댓값 1.0 (캡)
    """
    tech_name = (signal.get("technology_name") or "").lower()
    summary = (signal.get("summary") or "").lower()
    signal_text = f"{tech_name} {summary}"

    tech_stack = [t.lower() for t in (user_profile.get("tech_stack") or [])]
    interests = [i.lower() for i in (user_profile.get("interests") or [])]

    score = 0.0
    for tech in tech_stack:
        if tech and tech in signal_text:
            score += 0.4
    for interest in interests:
        if interest and interest in signal_text:
            score += 0.3

    return max(min(score, 1.0), 0.1)


def mark_stuck_jobs(client: Client, timeout_minutes: int = 15) -> int:
    """processing_started_at이 timeout_minutes 이상 경과한 processing 상태 brief를 failed로 전이. (AC-6)"""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)).isoformat()
    result = (
        client.table("daily_briefs")
        .update({"status": "failed"})
        .eq("status", "processing")
        .lt("processing_started_at", cutoff)
        .execute()
    )
    stuck_count = len(result.data or [])
    if stuck_count:
        pipeline_log(
            stage="recommender",
            brief_date="",
            user_count=0,
            level="warning",
            event="stuck_jobs_marked_failed",
            count=stuck_count,
        )
    return stuck_count


def _fetch_all_users(client: Client) -> list[dict]:
    """onboarding_completed=true 사용자 전체 페이지네이션 조회."""
    all_users: list[dict] = []
    offset = 0
    while True:
        result = (
            client.table("user_profiles")
            .select("id")
            .eq("onboarding_completed", True)
            .range(offset, offset + _PAGE_SIZE - 1)
            .execute()
        )
        batch = result.data or []
        all_users.extend(batch)
        if len(batch) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE
    return all_users


def _signal_embed_text(signal: dict) -> str:
    """Signal 임베딩 대상 텍스트 (콜드 스타트 코사인 + Memory RAG query 둘 다에 쓰이는 단일 임베딩).

    Story 6.4(AC4): memory는 memory_manager에서 `summary`만 임베딩하므로(동일 표현 공간), RAG query
    비대칭("go→google" 인접 리뷰 파인딩)을 없애기 위해 **summary 중심**으로 맞춘다.
    summary 없으면 title 폴백, 둘 다 없으면 "" (→ 임베딩 스킵, 기존 동작). 시그널당 임베딩 1회 불변(A-2).
    """
    return (signal.get("summary") or signal.get("title") or "").strip()


def _embed_signal_list(
    signals: list[dict], llm: LLMProvider, brief_date: str
) -> dict[str, list[float]]:
    """후보 Signal을 배치당 1회 임베딩 → query 벡터 dict 반환 (설계 A-2: 사용자 재임베딩 금지).

    개별 Signal 임베딩 실패는 격리(AD-5) — 예외 전파 없이 해당 Signal만 dict에서 누락되어
    콜드 스타트 점수로 폴백된다.
    """
    embeddings: dict[str, list[float]] = {}
    for sig in signals:
        text = _signal_embed_text(sig)
        if not text:
            continue
        try:
            embeddings[sig["id"]] = llm.embed_text(text)
        except Exception as e:
            pipeline_log(
                stage="recommender",
                brief_date=brief_date,
                user_count=0,
                level="warning",
                event="signal_embed_failed",
                signal_id=sig["id"],
                error=str(e)[:200],
            )
    return embeddings


def _build_signal_embeddings(
    signal_ids: list[str], client: Client, llm: LLMProvider, brief_date: str
) -> dict[str, list[float]]:
    """signal_ids로 processed Signal을 조회한 뒤 배치 임베딩(run_recommender 배치 경로용)."""
    if not signal_ids:
        return {}
    sig_result = (
        client.table("signals")
        .select("id,technology_name,title,summary,published_at,popularity,source_authority")
        .in_("id", signal_ids)
        .eq("status", "processed")
        .execute()
    )
    return _embed_signal_list(sig_result.data or [], llm, brief_date)


def _score_signals(
    signals: list[dict],
    user_profile: dict,
    user_id: str,
    client: Client,
    brief_date: str,
    llm: LLMProvider | None,
    signal_embeddings: dict[str, list[float]] | None,
) -> tuple[list[tuple[str, float]], str]:
    """Story 6.4 v2 스코어링 → (MMR 순서의 (signal_id, combined) 리스트, variant).

    조립: (1) 프로필 임베딩 1회, (2) base = 코사인(프로필, 시그널) 또는 substring 폴백(D1),
    (3) memory 보유 시 RAG 블렌드(base + _RAG_WEIGHT*top_sim), (4) 랭킹 피처 결합(최신성·인기·권위)
    → combined[0.1,1.0], (5) MMR 재랭킹 → 순서 확정.

    safe degradation(AD-5): llm 미주입 → substring 콜드 스타트, 프로필/시그널 임베딩 실패 → 해당 폴백,
    RAG RPC 실패 → base 폴백. 어느 것도 brief 생성을 막지 않는다.
    user_id 스코프는 match_memories 본문에서 강제(AC-A3). 정렬·MMR tie-break은 signal_id 오름차순(결정론).

    Story 6.5: 두 번째 반환값 variant는 held-out 평가용 코호트 라벨 — memory RAG가 실제로 적용된
    경로(memory_rag_applied)면 "rag", 그 외(llm None·memory 미보유·RAG 폴백)면 "coldstart".
    pipeline_log의 memory_rag_applied/coldstart 판정과 동일 분기에서 파생(중복 판정 로직 신설 금지).
    """
    # 배치 내 인기 정규화 기준(같은 브리프 후보들의 최대 log1p popularity)
    batch_max_logpop = 0.0
    for sig in signals:
        lp = math.log1p(max(_as_float(sig.get("popularity")), 0.0))
        if lp > batch_max_logpop:
            batch_max_logpop = lp

    # ── (1) 임베딩: 시그널(배치 재사용 or 지금) + 프로필(사용자당 1회) ──
    embeddings: dict[str, list[float]] = {}
    norms: dict[str, float] = {}
    profile_emb: list[float] | None = None
    profile_norm = 0.0
    if llm is not None:
        embeddings = signal_embeddings if signal_embeddings is not None else _embed_signal_list(
            signals, llm, brief_date
        )
        for sid, emb in embeddings.items():
            norms[sid] = _norm(emb)
        profile_emb = _embed_profile(user_profile, llm, brief_date)
        if profile_emb is not None:
            profile_norm = _norm(profile_emb)

    # ── (2) base 관련도: 정상 경로 = 코사인, 폴백 = substring(D1) ──
    base_scores: dict[str, float] = {}
    for sig in signals:
        sid = sig["id"]
        emb = embeddings.get(sid)
        sig_norm = norms.get(sid, 0.0)
        if profile_emb is not None and profile_norm > 0 and emb is not None and sig_norm > 0:
            base_scores[sid] = compute_relevance_score_v2(emb, sig_norm, profile_emb, profile_norm)
        else:
            # AD-5 폴백: llm None, 빈 프로필, 임베딩 실패 → substring(정상 경로엔 관여 안 함)
            base_scores[sid] = compute_relevance_score(sig, user_profile)

    # ── (3) Memory RAG 블렌드(보유 시에만). 실패는 base로 안전 폴백 ──
    # variant(6.5): 기본 coldstart, memory_rag_applied 경로에서만 rag로 승격.
    variant = "coldstart"
    blended_scores = dict(base_scores)
    if llm is not None:
        try:
            mem_check = (
                client.table("memories")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            memory_count = mem_check.count if mem_check.count is not None else len(mem_check.data or [])

            if not memory_count:
                pipeline_log(
                    stage="recommender", brief_date=brief_date, user_count=0,
                    event="memory_rag_coldstart", user_id=user_id, memory_count=0, scorer="v2",
                )
            else:
                for sig in signals:
                    sid = sig["id"]
                    emb = embeddings.get(sid)
                    if emb is None:
                        continue  # 임베딩 없는 시그널 → base 유지
                    try:
                        rpc_result = client.rpc(
                            "match_memories",
                            {
                                "query_embedding": emb,
                                "match_user_id": user_id,
                                "match_count": _RAG_MATCH_COUNT,
                            },
                        ).execute()
                        sims = [(row.get("similarity") or 0.0) for row in (rpc_result.data or [])]
                        top_sim = max(sims) if sims else 0.0
                    except Exception as e:
                        pipeline_log(
                            stage="recommender", brief_date=brief_date, user_count=0, level="warning",
                            event="memory_rag_query_failed", user_id=user_id, signal_id=sid,
                            error=str(e)[:200],
                        )
                        continue  # 해당 시그널만 base 폴백
                    blended_scores[sid] = _clamp(base_scores[sid] + _RAG_WEIGHT * max(top_sim, 0.0))
                variant = "rag"  # 6.5: memory RAG 실제 적용 → rag 코호트
                pipeline_log(
                    stage="recommender", brief_date=brief_date, user_count=0,
                    event="memory_rag_applied", user_id=user_id, memory_count=memory_count, scorer="v2",
                )
        except Exception as e:
            # AD-5: RAG 전체 실패 → base 유지, brief 생성 지속
            blended_scores = dict(base_scores)
            pipeline_log(
                stage="recommender", brief_date=brief_date, user_count=0, level="warning",
                event="memory_rag_coldstart", user_id=user_id, error=str(e)[:200], scorer="v2",
            )

    # ── (4) 랭킹 피처 결합 → combined[0.1,1.0] ──
    combined_scores: dict[str, float] = {}
    for sig in signals:
        sid = sig["id"]
        recency = _recency_norm(sig.get("published_at"), brief_date)
        pop = _popularity_norm(sig.get("popularity"), batch_max_logpop)
        auth = _authority_norm(sig.get("source_authority"))
        combined_scores[sid] = _clamp(
            _W_RELEVANCE * blended_scores[sid]
            + _W_RECENCY * recency
            + _W_POPULARITY * pop
            + _W_AUTHORITY * auth
        )

    # ── (5) MMR 재랭킹(임베딩 있을 때) or 결정론적 정렬(폴백) ──
    valid_embs = {sid: e for sid, e in embeddings.items() if norms.get(sid, 0.0) > 0}
    if valid_embs:
        scored_items = [
            (sig["id"], combined_scores[sig["id"]], valid_embs.get(sig["id"]), norms.get(sig["id"], 0.0))
            for sig in signals
        ]
        return _mmr_rerank(scored_items, _MMR_LAMBDA), variant
    return sorted(combined_scores.items(), key=lambda x: (-x[1], x[0])), variant


def create_daily_brief_for_user(
    user_id: str,
    signal_ids: list[str],
    client: Client,
    brief_date: str,
    llm: LLMProvider | None = None,
    signal_embeddings: dict[str, list[float]] | None = None,
) -> str | None:
    """단일 사용자 Daily Brief 생성. brief_id 반환 또는 None(스킵/실패)."""
    today = date.fromisoformat(brief_date)

    # 중복 체크 — 이미 존재하면 스킵
    existing = (
        client.table("daily_briefs")
        .select("id")
        .eq("user_id", user_id)
        .eq("brief_date", today.isoformat())
        .execute()
    )
    if existing.data:
        pipeline_log(
            stage="recommender",
            brief_date=brief_date,
            user_count=0,
            event="brief_already_exists",
            user_id=user_id,
        )
        return existing.data[0]["id"]

    # 사용자 프로필 조회
    profile_result = (
        client.table("user_profiles")
        .select("role,tech_stack,interests,experience_level,project_goal")
        .eq("id", user_id)
        .execute()
    )
    user_profile = profile_result.data[0] if profile_result.data else {}

    # Signal 데이터 배치 조회 및 관련성 점수 계산 (P7: N+1 → batch)
    signals: list[dict] = []
    if signal_ids:
        sig_result = (
            client.table("signals")
            .select("id,technology_name,title,summary,published_at,popularity,source_authority")
            .in_("id", signal_ids)
            .eq("status", "processed")
            .execute()
        )
        signals = sig_result.data or []

    if not signals:
        pipeline_log(
            stage="recommender",
            brief_date=brief_date,
            user_count=0,
            level="warning",
            event="no_processed_signals",
            user_id=user_id,
        )
        return None

    # 점수 계산 + MMR 순서 (v2: 코사인 콜드 스타트 + Memory RAG + 랭킹 피처 + MMR, Story 6.4)
    # scored = [(signal_id, combined)] — position=MMR 순서, relevance_score=combined(D4)
    # variant(6.5): 이 brief가 실제로 탄 랭킹 경로(rag|coldstart) — impression 정본 라벨.
    scored, variant = _score_signals(
        signals, user_profile, user_id, client, brief_date, llm, signal_embeddings
    )

    # daily_briefs INSERT (pending) — P5: UNIQUE 충돌 시 기존 id 반환
    try:
        brief_result = client.table("daily_briefs").insert({
            "user_id": user_id,
            "brief_date": today.isoformat(),
            "status": "pending",
        }).execute()
    except Exception as e:
        if "23505" in str(e) or "duplicate" in str(e).lower() or "unique" in str(e).lower():
            # 경쟁 조건으로 이미 삽입된 경우 기존 레코드 반환
            fallback = (
                client.table("daily_briefs")
                .select("id")
                .eq("user_id", user_id)
                .eq("brief_date", today.isoformat())
                .execute()
            )
            return fallback.data[0]["id"] if fallback.data else None
        raise

    if not brief_result.data:
        pipeline_log(
            stage="recommender",
            brief_date=brief_date,
            user_count=0,
            level="error",
            event="brief_insert_failed",
            user_id=user_id,
        )
        return None

    brief_id = brief_result.data[0]["id"]

    # processing 상태로 전이 + processing_started_at 기록 (AC-6)
    client.table("daily_briefs").update({
        "status": "processing",
        "processing_started_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", brief_id).execute()

    # daily_brief_signals INSERT — P2: 실패 시 failed 전이 후 None 반환
    brief_signals = [
        {
            "daily_brief_id": brief_id,
            "signal_id": sig_id,
            "relevance_score": score,
            "position": pos + 1,
        }
        for pos, (sig_id, score) in enumerate(scored)
    ]
    signals_result = client.table("daily_brief_signals").insert(brief_signals).execute()
    if not signals_result.data:
        pipeline_log(
            stage="recommender",
            brief_date=brief_date,
            user_count=0,
            level="error",
            event="brief_signals_insert_failed",
            user_id=user_id,
            brief_id=brief_id,
        )
        client.table("daily_briefs").update({"status": "failed"}).eq("id", brief_id).execute()
        return None

    # Story 6.5: 서버 사이드 impression 정본 로깅 (best-effort, AD-5).
    # daily_brief_signals insert 성공 직후에만 — brief에 노출된 각 시그널에 대해 그 사용자·brief의
    # variant/position/relevance_score를 함께 기록. 추가 쿼리 없이 이미 계산된 값(scored·variant) 재사용.
    # log_engagement_bulk 자체가 best-effort지만, 여기서도 try/except로 한 번 더 감싸 로깅이 어떤
    # 이유로든 예외를 던져도 brief가 completed로 진행되도록 이중 보증한다(로깅은 순수 부수효과).
    try:
        log_engagement_bulk(
            client,
            [
                {
                    "user_id": user_id,
                    "signal_id": sig_id,
                    "event_type": "impression",
                    "daily_brief_id": brief_id,
                    "variant": variant,
                    "metadata": {"position": pos + 1, "relevance_score": score},
                }
                for pos, (sig_id, score) in enumerate(scored)
            ],
        )
    except Exception:  # noqa: BLE001 — impression 로깅은 brief 완료를 절대 막지 않는다(AD-5)
        pass

    # completed 전이
    client.table("daily_briefs").update({
        "status": "completed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", brief_id).execute()

    pipeline_log(
        stage="recommender",
        brief_date=brief_date,
        user_count=0,
        event="brief_created",
        user_id=user_id,
        brief_id=brief_id,
        signal_count=len(scored),
    )
    return brief_id


def run_recommender(
    signal_ids: list[str],
    client: Client,
    brief_date: str,
    llm: LLMProvider | None = None,
) -> int:
    """onboarding_completed=true 사용자 전체 Daily Brief 생성. 성공 수 반환.

    llm 주입 시 후보 Signal을 배치당 1회 임베딩하여 전 사용자 Memory RAG 스코어링에 재사용한다
    (설계 A-2: 사용자 재임베딩 금지). 임베딩 자체 실패는 콜드 스타트로 폴백.
    """
    # AC-6: 이전 실행에서 stuck된 brief 정리
    mark_stuck_jobs(client)

    users = _fetch_all_users(client)  # P8: 페이지네이션

    pipeline_log(
        stage="recommender",
        brief_date=brief_date,
        user_count=len(users),
        event="recommender_started",
        signal_count=len(signal_ids),
    )

    # 배치당 1회 Signal 임베딩 (전 사용자 공유)
    signal_embeddings: dict[str, list[float]] | None = None
    if llm is not None:
        try:
            signal_embeddings = _build_signal_embeddings(signal_ids, client, llm, brief_date)
        except Exception as e:
            # 배치 임베딩 자체 실패 → 전 사용자 콜드 스타트 폴백 (AD-5)
            pipeline_log(
                stage="recommender",
                brief_date=brief_date,
                user_count=len(users),
                level="warning",
                event="signal_embed_batch_failed",
                error=str(e)[:200],
            )
            signal_embeddings = {}

    success_count = 0
    for user in users:
        user_id = user["id"]
        try:
            brief_id = create_daily_brief_for_user(
                user_id, signal_ids, client, brief_date, llm, signal_embeddings
            )
            if brief_id:
                success_count += 1
        except Exception as e:
            pipeline_log(
                stage="recommender",
                brief_date=brief_date,
                user_count=len(users),
                level="error",
                event="brief_creation_failed",
                user_id=user_id,
                error=str(e)[:200],
            )
            # P3: AC-3 — 실패한 사용자의 pending/processing brief를 failed로 전이
            try:
                client.table("daily_briefs").update({"status": "failed"}).eq(
                    "user_id", user_id
                ).eq("brief_date", brief_date).in_("status", ["pending", "processing"]).execute()
            except Exception:
                pass

    pipeline_log(
        stage="recommender",
        brief_date=brief_date,
        user_count=len(users),
        event="recommender_completed",
        success_count=success_count,
    )
    return success_count
