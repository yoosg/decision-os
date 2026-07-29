from __future__ import annotations

from datetime import date, datetime, timezone, timedelta

from supabase import Client

from pipeline.llm.base import LLMProvider
from pipeline.logger import pipeline_log

_PAGE_SIZE = 1000

# Memory RAG (Story 5.4) — 콜드 스타트 점수에 가산되는 코사인 유사도 가중치.
# base(0.1~1.0) + _RAG_WEIGHT * top_similarity(0~1) → clamp(0.1, 1.0).
# memory 보유 사용자가 콜드 스타트보다 개인화되도록 양수, 불변식 유지 위해 clamp.
_RAG_WEIGHT = 0.5
# match_memories RPC가 반환할 memory 수. 블렌딩은 top_similarity 최댓값만 사용하므로
# (거리 오름차순 정렬의 최근접 1행 = 최대 유사도) 1이면 충분하다. 상위 4행 조회/직렬화
# 낭비를 제거 (코드리뷰 2026-07-28). 향후 top-k 평균 블렌딩 채택 시 이 값을 늘린다.
_RAG_MATCH_COUNT = 1


def compute_relevance_score(signal: dict, user_profile: dict) -> float:
    """MVP 콜드 스타트: 키워드 매칭 기반 관련성 점수.

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
    """Signal 임베딩 대상 텍스트 (memory_manager와 동일 모델로 임베딩되는 query 벡터 소스)."""
    return " ".join(
        part for part in (
            signal.get("technology_name"),
            signal.get("title"),
            signal.get("summary"),
        ) if part
    ).strip()


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
        .select("id,technology_name,title,summary")
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
) -> list[tuple[str, float]]:
    """콜드 스타트 점수 + (memory 보유 시) Memory RAG 유사도 블렌딩 → (signal_id, score) 정렬 리스트.

    - llm 미주입 또는 memory 미보유 → 콜드 스타트 폴백(AC-A2).
    - 임베딩/RPC 실패 → 콜드 스타트 점수로 안전 폴백, brief 생성 지속(AC-A2, AD-5).
    - user_id 스코프는 match_memories 함수 본문에서 강제(AC-A3).
    - 정렬은 (-score, signal_id)로 결정론적(설계 A-1 ③).
    """
    base_scores = {sig["id"]: compute_relevance_score(sig, user_profile) for sig in signals}

    def _sorted(scores: dict[str, float]) -> list[tuple[str, float]]:
        return sorted(scores.items(), key=lambda x: (-x[1], x[0]))

    if llm is None:
        return _sorted(base_scores)

    try:
        # 배치 경로에서 계산된 임베딩 재사용, 없으면(온디맨드 단일 사용자) 지금 계산
        embeddings = signal_embeddings
        if embeddings is None:
            embeddings = _embed_signal_list(signals, llm, brief_date)

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
                stage="recommender",
                brief_date=brief_date,
                user_count=0,
                event="memory_rag_coldstart",
                user_id=user_id,
                memory_count=0,
            )
            return _sorted(base_scores)

        final_scores: dict[str, float] = {}
        for sig in signals:
            sid = sig["id"]
            base = base_scores[sid]
            emb = embeddings.get(sid)
            if emb is None:
                final_scores[sid] = base
                continue
            try:
                rpc_result = client.rpc(
                    "match_memories",
                    {
                        "query_embedding": emb,
                        "match_user_id": user_id,
                        "match_count": _RAG_MATCH_COUNT,
                    },
                ).execute()
                sims = [
                    (row.get("similarity") or 0.0)
                    for row in (rpc_result.data or [])
                ]
                top_sim = max(sims) if sims else 0.0
            except Exception as e:
                pipeline_log(
                    stage="recommender",
                    brief_date=brief_date,
                    user_count=0,
                    level="warning",
                    event="memory_rag_query_failed",
                    user_id=user_id,
                    signal_id=sid,
                    error=str(e)[:200],
                )
                final_scores[sid] = base
                continue
            blended = base + _RAG_WEIGHT * max(top_sim, 0.0)
            final_scores[sid] = max(min(blended, 1.0), 0.1)

        pipeline_log(
            stage="recommender",
            brief_date=brief_date,
            user_count=0,
            event="memory_rag_applied",
            user_id=user_id,
            memory_count=memory_count,
        )
        return _sorted(final_scores)

    except Exception as e:
        # AD-5: RAG 전체 실패 시에도 콜드 스타트로 폴백하여 brief 생성 지속
        pipeline_log(
            stage="recommender",
            brief_date=brief_date,
            user_count=0,
            level="warning",
            event="memory_rag_coldstart",
            user_id=user_id,
            error=str(e)[:200],
        )
        return _sorted(base_scores)


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
            .select("id,technology_name,title,summary")
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

    # 점수 계산 + 정렬 (콜드 스타트 + Memory RAG 블렌딩, Story 5.4)
    scored = _score_signals(
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
