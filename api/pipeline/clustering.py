"""Story 6.2: 의미 클러스터링 & 관련성/세이프티 필터.

6.1 수집기가 반환한 RawArticle을 **임베딩 의미 유사도**로 클러스터링하고,
SignalBuilder(LLM) 이전에 무관/유해 기사를 걸러낸다.

설계 결정(스토리 Dev Notes):
- D1: 외부 벡터 DB 미도입(AD-2/AD-6). 임베딩은 기존 `LLMProvider.embed_text`
  (text-embedding-3-small)로 생성하고, pre-persist 기사 간 코사인 유사도는
  **인프로세스 순수 파이썬**으로 계산(배치당 수십 건 → O(n²)도 무시 가능). numpy 금지.
- D2: `normalizer.py`를 수정하지 않고 1클러스터=1시그널을 달성하기 위해, 각 클러스터에
  **배치 내 고유한 technology_name 라벨**을 부여하고 멤버 전부를 그 라벨로 재생성한다.
  normalize의 technology_name 그룹핑이 자연히 클러스터당 1그룹 → 1 signal + N sources.
- D3: 세이프티 필터는 경량 블록리스트 휴리스틱(제목 소문자 매칭). Moderation API 미채택.

safe degradation(AD-5): llm 부재/임베딩 실패는 배치를 죽이지 않고 pass-through로 폴백.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import replace

from core.config import settings
from pipeline.collector.rss import derive_tech
from pipeline.llm.base import LLMProvider
from pipeline.logger import pipeline_log
from pipeline.models import RawArticle

_STAGE = "clustering"

# 관련성 필터용 도메인 앵커 문장 — 각 배치에서 llm으로 1회 임베딩해 기사와의 코사인으로
# "이 기사가 AI/개발 기술 도메인인가"를 저비용 판정한다.
_DOMAIN_ANCHOR_SENTENCE = (
    "artificial intelligence, machine learning, large language models, "
    "software development, and developer tools"
)

# 세이프티 블록리스트(제목 소문자 매칭) — 명백한 유해 표현만. 관련성 필터가 도메인 밖
# 대부분을 이미 거르므로 최소 집합만 유지(D3). 오탐을 줄이기 위해 단어 조각이 아닌
# 충분히 구체적인 구절 위주로 구성. 강화는 6.5(측정) 이후 데이터로 판단.
_UNSAFE_KEYWORDS = [
    "child sexual", "child porn", "nsfw", "xxx rated",
    "how to make a bomb", "how to build a bomb", "build a bomb",
    "make a weapon", "bioweapon", "nerve agent", "how to make meth",
]


def _embed_text(a: RawArticle) -> str:
    """임베딩 대상 텍스트. 6.1은 content를 채우지 않으므로(6.3 스코프) title 중심."""
    return f"{a.technology_name} {a.title}".strip()


def _norm(vec: list[float]) -> float:
    return math.sqrt(sum(x * x for x in vec))


def _cosine(a: list[float], b: list[float], norm_a: float, norm_b: float) -> float:
    """순수 파이썬 코사인 유사도. norm은 미리 계산해 전달(O(n²) 반복 최적화)."""
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (norm_a * norm_b)


def _is_unsafe(title: str) -> bool:
    low = (title or "").lower()
    return any(kw in low for kw in _UNSAFE_KEYWORDS)


def _compute_anchor(llm: LLMProvider, brief_date: str) -> tuple[list[float], float] | None:
    """도메인 앵커 임베딩 + norm. 실패/영벡터면 None → 관련성 필터를 건너뛴다(safe-degrade)."""
    try:
        vec = llm.embed_text(_DOMAIN_ANCHOR_SENTENCE)
        norm = _norm(vec)
        if norm == 0:
            raise ValueError("anchor embedding has zero norm")
        return vec, norm
    except Exception as e:
        pipeline_log(stage=_STAGE, brief_date=brief_date, user_count=0, level="warning",
                     event="anchor_embed_failed", error=str(e)[:200])
        return None


# 임베딩된 기사 1건: (article, vector, norm)
_Embedded = tuple[RawArticle, list[float], float]


def _embed_articles(
    articles: list[RawArticle], llm: LLMProvider, brief_date: str
) -> tuple[list[_Embedded], list[RawArticle]]:
    """각 기사를 임베딩. (embedded, passthrough) 반환.

    embedded: 필터/클러스터 대상 [(article, vec, norm)]
    passthrough: 임베딩 실패 기사 — 원본 라벨 유지한 채 그대로 통과(전체 중단 금지, AD-5)
    """
    embedded: list[_Embedded] = []
    passthrough: list[RawArticle] = []
    for a in articles:
        try:
            vec = llm.embed_text(_embed_text(a))
            norm = _norm(vec)
            if norm == 0:
                raise ValueError("embedding has zero norm")
            embedded.append((a, vec, norm))
        except Exception as e:
            pipeline_log(stage=_STAGE, brief_date=brief_date, user_count=0, level="warning",
                         event="article_embed_failed", url=a.url, error=str(e)[:200])
            passthrough.append(a)
    return embedded, passthrough


def _apply_filters(
    embedded: list[_Embedded],
    anchor: tuple[list[float], float] | None,
    brief_date: str,
) -> tuple[list[_Embedded], int, int]:
    """세이프티(제목) → 관련성(앵커 코사인) 순으로 필터. (survivors, off_domain, unsafe)."""
    survivors: list[_Embedded] = []
    off_domain = 0
    unsafe = 0
    for a, vec, norm in embedded:
        if _is_unsafe(a.title):
            unsafe += 1
            pipeline_log(stage=_STAGE, brief_date=brief_date, user_count=0,
                         event="article_filtered", reason="unsafe", url=a.url)
            continue
        if anchor is not None:
            sim = _cosine(vec, anchor[0], norm, anchor[1])
            if sim < settings.relevance_min_similarity:
                off_domain += 1
                pipeline_log(stage=_STAGE, brief_date=brief_date, user_count=0,
                             event="article_filtered", reason="off_domain",
                             url=a.url, similarity=round(sim, 4))
                continue
        survivors.append((a, vec, norm))
    return survivors, off_domain, unsafe


def _cluster(survivors: list[_Embedded], threshold: float) -> list[list[_Embedded]]:
    """단일 패스 greedy 클러스터링. 각 기사를 대표(첫 멤버)와의 코사인 ≥ threshold인
    첫 클러스터에 배정, 없으면 새 클러스터 생성."""
    clusters: list[dict] = []  # {"vec","norm","members"}
    for item in survivors:
        _a, vec, norm = item
        placed = False
        for c in clusters:
            if _cosine(vec, c["vec"], norm, c["norm"]) >= threshold:
                c["members"].append(item)
                placed = True
                break
        if not placed:
            clusters.append({"vec": vec, "norm": norm, "members": [item]})
    return [c["members"] for c in clusters]


def _title_slug(title: str, max_words: int = 4, max_len: int = 40) -> str:
    return " ".join((title or "").split()[:max_words]).strip()[:max_len]


def _unique_label(base: str, rep: RawArticle, used: set[str]) -> str:
    """배치 내 고유 라벨 생성(D2). base가 이미 쓰였으면 제목 slug/인덱스로 판별자 부여.

    ⚠️ derive_tech는 매치 없으면 모두 'General AI' → 서로 다른 클러스터가 같은 라벨이 되면
    normalize가 다시 1시그널로 합쳐 6.1 문제가 재현되므로 반드시 distinct하게 만든다.
    """
    if base not in used:
        return base
    slug = _title_slug(rep.title)
    if slug:
        candidate = f"{base}: {slug}"
        if candidate not in used:
            return candidate
    i = 2
    while f"{base} #{i}" in used:
        i += 1
    return f"{base} #{i}"


def _cluster_key(members: list[_Embedded]) -> str:
    """클러스터의 결정론적 식별키(Story 6.3). 멤버 url 집합을 정렬·조인해 짧은 해시.

    멤버 집합이 같으면 순서에 무관하게 같은 key → 같은 클러스터의 lineage를 재실행 간
    안정적으로 식별(6.4/부분 UNIQUE 인덱스가 소비). cluster_and_filter에서 입력이 url로
    정렬되므로 동일 입력이면 동일 클러스터·동일 key가 결정된다.
    같은 url이 중복 유입돼도 key가 흔들리지 않도록 set으로 중복 제거 후 해시한다.
    """
    joined = "\n".join(sorted({m[0].url for m in members}))
    return hashlib.sha1(joined.encode()).hexdigest()[:16]


def _relabel(
    clusters: list[list[_Embedded]], reserved_labels: set[str] | None = None
) -> list[RawArticle]:
    """각 클러스터에 배치 내 고유 라벨 + 결정론적 cluster_key 부여, 멤버 전부를 재생성.

    replace()는 technology_name·cluster_key만 바꾸므로 published_at·popularity는 자동 보존.

    reserved_labels: pass-through(임베딩 실패) 기사의 원본 라벨. 이를 `used`에 미리 등록해
    relabeled 클러스터가 pass-through와 같은 라벨을 받지 않게 한다 — 그렇지 않으면 normalize가
    둘을 같은 그룹으로 묶어 별개 토픽이 1 signal로 병합된다(D2 불변식을 pass-through까지 확장).
    """
    out: list[RawArticle] = []
    used: set[str] = set(reserved_labels or ())
    for members in clusters:
        rep = members[0][0]
        label = _unique_label(derive_tech(rep.title), rep, used)
        used.add(label)
        key = _cluster_key(members)
        for a, _vec, _norm in members:
            out.append(replace(a, technology_name=label, cluster_key=key))
    return out


def cluster_and_filter(
    articles: list[RawArticle], llm: LLMProvider | None, brief_date: str = ""
) -> list[RawArticle]:
    """6.2 공개 진입점: 임베딩 → 필터 → 클러스터 → 재라벨.

    반환: 재라벨된 RawArticle 목록(클러스터당 N개 소스, 모두 동일 고유 라벨)
    + 임베딩 실패로 pass-through된 원본 기사들.
    """
    # safe-degrade 가드: 빈 입력 / 토글 off / llm 부재 → 6.1 그대로 통과
    if not articles or not settings.clustering_enabled or llm is None:
        reason = ("empty_input" if not articles
                  else "disabled" if not settings.clustering_enabled
                  else "no_llm")
        pipeline_log(stage=_STAGE, brief_date=brief_date, user_count=0,
                     event="clustering_skipped", reason=reason, input=len(articles))
        return list(articles)

    # 결정론적 정렬: greedy 클러스터링/라벨이 입력 순서에 의존하므로, 같은 입력이면 항상
    # 같은 클러스터·라벨이 나오도록 url로 정렬(같은 brief_date 재실행 시 중복 시그널 방지).
    articles = sorted(articles, key=lambda a: a.url)

    embedded, passthrough = _embed_articles(articles, llm, brief_date)
    anchor = _compute_anchor(llm, brief_date)
    survivors, off_domain, unsafe = _apply_filters(embedded, anchor, brief_date)

    # 임베딩 실패 pass-through 기사에도 세이프티(제목) 필터 적용 — 제목 매칭은 임베딩이
    # 불필요하므로, 임베딩 실패가 유해 기사의 필터 우회 경로가 되지 않게 한다.
    safe_passthrough: list[RawArticle] = []
    for a in passthrough:
        if _is_unsafe(a.title):
            unsafe += 1
            pipeline_log(stage=_STAGE, brief_date=brief_date, user_count=0,
                         event="article_filtered", reason="unsafe", url=a.url)
            continue
        safe_passthrough.append(a)

    clusters = _cluster(survivors, settings.cluster_similarity_threshold)
    # pass-through 원본 라벨을 예약해 relabeled 클러스터와의 라벨 충돌(→ signal 병합)을 막는다.
    reserved = {a.technology_name for a in safe_passthrough}
    relabeled = _relabel(clusters, reserved)

    # 임베딩 실패(세이프티 통과) 기사는 원본 라벨 유지한 채 뒤에 붙인다(전체 중단 금지).
    result = relabeled + safe_passthrough

    pipeline_log(stage=_STAGE, brief_date=brief_date, user_count=0,
                 event="clustering_done", input=len(articles),
                 filtered_off_domain=off_domain, filtered_unsafe=unsafe,
                 embed_failed=len(passthrough), cluster_count=len(clusters))
    return result
