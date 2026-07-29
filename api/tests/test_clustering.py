"""Story 6.2: 의미 클러스터링 & 관련성/세이프티 필터 테스트.

오프라인 원칙(절대): 실제 OpenAI 호출 금지. llm은 MagicMock으로 대체하고
embed_text가 결정론적 저차원 벡터를 반환하게 스텁한다(코사인 성질은 차원과 무관하게
검증 가능 — 실제 1536차원일 필요 없음). 도메인 앵커 임베딩도 같은 스텁을 탄다.

벡터 설계(3D):
- 앵커 문장("artificial intelligence ...") → [1, 0, 0] = 도메인 축
- 도메인 기사 → x성분이 큰 벡터(앵커와 코사인 높음)
- off-domain("smart rings") → 앵커에 직교 → 코사인 0 < relevance_min_similarity
"""
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from pipeline.clustering import cluster_and_filter
from pipeline.models import RawArticle
from pipeline.normalizer import normalize

_ANCHOR_SUB = "artificial intelligence"


def _fake_llm(vectors, default=(0.0, 0.0, 1.0)):
    """결정론적 임베딩 스텁.

    vectors: list[(substring, vec)] — embed_text 인자에 substring이 포함되면 그 벡터 반환
    (순서대로 첫 매치). 매치 없으면 default(앵커에 직교하는 off-domain 기본값).
    """
    llm = MagicMock()

    def embed(text):
        for sub, vec in vectors:
            if sub in text:
                return list(vec)
        return list(default)

    llm.embed_text.side_effect = embed
    return llm


def _events(mock_log):
    """patch된 pipeline_log 호출들의 kwargs 목록."""
    return [c.kwargs for c in mock_log.call_args_list]


# ─── AC1: 의미 임베딩 클러스터링 ──────────────────────────────────────────────

def test_similar_articles_form_single_cluster():
    """스파이크 케이스: Claude 공식 블로그 + 동일 주제 HN → 반드시 1 클러스터."""
    articles = [
        RawArticle("Claude", "Claude cryptography vulnerability disclosed", "u1", "official_blog"),
        RawArticle("General AI", "HN: discussion on Claude crypto flaw", "u2", "hn"),
    ]
    llm = _fake_llm([
        (_ANCHOR_SUB, [1.0, 0.0, 0.0]),
        ("cryptography", [1.0, 0.10, 0.0]),
        ("crypto flaw", [1.0, 0.12, 0.0]),
    ])
    out = cluster_and_filter(articles, llm, brief_date="d")
    # 1 클러스터 → 모든 멤버가 동일 라벨, 소스 2개 보존
    assert len({a.technology_name for a in out}) == 1
    assert len(out) == 2
    assert {a.url for a in out} == {"u1", "u2"}


def test_unrelated_articles_stay_separate():
    """무관한 두 기사는 별개 클러스터로 남는다."""
    articles = [
        RawArticle("Claude", "Claude model update", "u1", "official_blog"),
        RawArticle("MCP", "MCP spec revision released", "u2", "official_blog"),
    ]
    llm = _fake_llm([
        (_ANCHOR_SUB, [1.0, 0.0, 0.0]),
        ("Claude", [1.0, 0.1, 0.0]),
        ("MCP", [1.0, 3.0, 0.0]),  # cosine(Claude,MCP)=0.41 < 0.82
    ])
    out = cluster_and_filter(articles, llm, brief_date="d")
    assert len({a.technology_name for a in out}) == 2


def test_threshold_merges_when_low():
    """임계치 경계: cosine≈0.894, threshold 0.82 → 병합."""
    articles = [
        RawArticle("Claude", "Claude launch", "u1", "official_blog"),
        RawArticle("Gemini", "Gemini launch", "u2", "official_blog"),
    ]
    llm = _fake_llm([
        (_ANCHOR_SUB, [1.0, 0.0, 0.0]),
        ("Claude", [1.0, 0.0, 0.0]),
        ("Gemini", [1.0, 0.5, 0.0]),
    ])
    with patch("pipeline.clustering.settings.cluster_similarity_threshold", 0.82):
        out = cluster_and_filter(articles, llm, brief_date="d")
    assert len({a.technology_name for a in out}) == 1


def test_threshold_splits_when_high():
    """임계치 경계: cosine≈0.894, threshold 0.95 → 분리."""
    articles = [
        RawArticle("Claude", "Claude launch", "u1", "official_blog"),
        RawArticle("Gemini", "Gemini launch", "u2", "official_blog"),
    ]
    llm = _fake_llm([
        (_ANCHOR_SUB, [1.0, 0.0, 0.0]),
        ("Claude", [1.0, 0.0, 0.0]),
        ("Gemini", [1.0, 0.5, 0.0]),
    ])
    with patch("pipeline.clustering.settings.cluster_similarity_threshold", 0.95):
        out = cluster_and_filter(articles, llm, brief_date="d")
    assert len({a.technology_name for a in out}) == 2


# ─── AC2: 관련성/세이프티 필터 ────────────────────────────────────────────────

def test_off_domain_article_filtered():
    """도메인 밖 기사(smart rings)는 앵커 유사도 미달 → 제외 + off_domain 로깅."""
    articles = [
        RawArticle("Claude", "Claude update", "u1", "official_blog"),
        RawArticle("General AI", "Smart rings track your sleep quality", "u2", "other"),
    ]
    llm = _fake_llm([
        (_ANCHOR_SUB, [1.0, 0.0, 0.0]),
        ("Claude", [1.0, 0.05, 0.0]),
        ("Smart rings", [0.0, 1.0, 0.0]),  # 앵커에 직교 → cosine 0 < 0.20
    ])
    with patch("pipeline.clustering.pipeline_log") as mock_log:
        out = cluster_and_filter(articles, llm, brief_date="d")
    urls = {a.url for a in out}
    assert "u2" not in urls and "u1" in urls
    off = [e for e in _events(mock_log)
           if e.get("event") == "article_filtered" and e.get("reason") == "off_domain"]
    assert len(off) == 1
    assert off[0]["url"] == "u2"
    assert "similarity" in off[0]


def test_unsafe_article_filtered():
    """유해 기사(블록리스트 매칭)는 도메인 내여도 제외 + unsafe 로깅."""
    articles = [
        RawArticle("Claude", "Claude update", "u1", "official_blog"),
        RawArticle("General AI", "Tutorial: how to make a bomb at home", "u2", "other"),
    ]
    llm = _fake_llm([
        (_ANCHOR_SUB, [1.0, 0.0, 0.0]),
        ("Claude", [1.0, 0.05, 0.0]),
        ("bomb", [1.0, 0.05, 0.0]),  # 도메인 내 벡터 → 제외는 세이프티 때문임을 보장
    ])
    with patch("pipeline.clustering.pipeline_log") as mock_log:
        out = cluster_and_filter(articles, llm, brief_date="d")
    assert "u2" not in {a.url for a in out}
    unsafe = [e for e in _events(mock_log)
              if e.get("event") == "article_filtered" and e.get("reason") == "unsafe"]
    assert len(unsafe) == 1 and unsafe[0]["url"] == "u2"


# ─── D2: 라벨 고유성 (normalize에서 재병합 방지) ──────────────────────────────

def test_label_uniqueness_prevents_merge():
    """derive_tech가 둘 다 'General AI'를 내도, 다른 클러스터면 라벨이 distinct해야 한다."""
    articles = [
        RawArticle("General AI", "Novel photonic compute breakthrough", "u1", "other"),
        RawArticle("General AI", "Quantum annealing hardware milestone", "u2", "other"),
    ]
    llm = _fake_llm([
        (_ANCHOR_SUB, [1.0, 0.0, 0.0]),
        ("photonic", [1.0, 0.1, 0.0]),
        ("Quantum", [1.0, 2.0, 0.0]),  # cosine≈0.53 < 0.82 → 별개 클러스터
    ])
    out = cluster_and_filter(articles, llm, brief_date="d")
    labels = [a.technology_name for a in out]
    assert len(set(labels)) == 2  # distinct == cluster_count


# ─── AC3: 파이프라인 순서 / signal 수 == cluster 수 ───────────────────────────

def test_signal_count_equals_cluster_count():
    """재라벨 산출물을 실제 normalize에 흘려 생성 signal 수 == cluster 수 검증.

    원문 3건 > 클러스터 2개 → LLM(build_signals) 호출이 원문이 아닌 토픽 수에 비례.
    """
    articles = [
        RawArticle("Claude", "Claude crypto vuln", "u1", "official_blog"),
        RawArticle("General AI", "HN Claude crypto discussion", "u2", "hn"),
        RawArticle("MCP", "MCP spec update", "u3", "official_blog"),
    ]
    llm = _fake_llm([
        (_ANCHOR_SUB, [1.0, 0.0, 0.0]),
        ("Claude crypto vuln", [1.0, 0.10, 0.0]),
        ("crypto discussion", [1.0, 0.12, 0.0]),
        ("MCP", [1.0, 3.0, 0.0]),
    ])
    clustered = cluster_and_filter(articles, llm, brief_date="d")
    assert len({a.technology_name for a in clustered}) == 2

    # 실제 normalize (Supabase는 MagicMock — test_pipeline_foundation 패턴)
    mock_client = MagicMock()
    signals_mock = MagicMock()
    sources_mock = MagicMock()
    sources_mock.insert.return_value.execute.return_value.data = [{"id": "src"}]
    call_count = 0

    def upsert_side_effect(data, **kwargs):
        nonlocal call_count
        call_count += 1
        m = MagicMock()
        m.execute.return_value.data = [{"id": f"uuid-{call_count}"}]
        return m

    signals_mock.upsert.side_effect = upsert_side_effect
    mock_client.table.side_effect = lambda t: signals_mock if t == "signals" else sources_mock

    signal_ids = normalize(clustered, date(2026, 7, 29), mock_client, brief_date="d")
    assert len(signal_ids) == 2  # == cluster count (원문 3 > 2)


# ─── Story 6.3: cluster_key 부여 & 메타데이터 보존 ────────────────────────────

def test_cluster_key_assigned_and_shared_within_cluster():
    """재라벨 결과에 cluster_key가 부여되고(non-null), 같은 클러스터 멤버는 동일 key."""
    articles = [
        RawArticle("Claude", "Claude crypto vuln", "u1", "official_blog"),
        RawArticle("General AI", "HN Claude crypto discussion", "u2", "hn"),
    ]
    llm = _fake_llm([
        (_ANCHOR_SUB, [1.0, 0.0, 0.0]),
        ("crypto vuln", [1.0, 0.10, 0.0]),
        ("crypto discussion", [1.0, 0.12, 0.0]),
    ])
    out = cluster_and_filter(articles, llm, brief_date="d")
    keys = {a.cluster_key for a in out}
    assert len(keys) == 1  # 1 클러스터 → 1 key
    assert all(a.cluster_key for a in out)  # non-null


def test_cluster_key_deterministic_and_distinct_per_cluster():
    """같은 입력이면 같은 key(결정론), 다른 클러스터는 다른 key."""
    articles = [
        RawArticle("Claude", "Claude model update", "u1", "official_blog"),
        RawArticle("MCP", "MCP spec revision released", "u2", "official_blog"),
    ]
    llm = _fake_llm([
        (_ANCHOR_SUB, [1.0, 0.0, 0.0]),
        ("Claude", [1.0, 0.1, 0.0]),
        ("MCP", [1.0, 3.0, 0.0]),  # 별개 클러스터
    ])
    out1 = cluster_and_filter(articles, llm, brief_date="d")
    out2 = cluster_and_filter(articles, llm, brief_date="d")
    keys1 = {a.url: a.cluster_key for a in out1}
    keys2 = {a.url: a.cluster_key for a in out2}
    assert keys1 == keys2  # 결정론
    assert keys1["u1"] != keys1["u2"]  # 다른 클러스터 → 다른 key


def test_metadata_preserved_through_relabel():
    """재라벨(replace) 후 published_at·popularity가 보존됨(technology_name·cluster_key만 변경)."""
    dt = datetime(2026, 7, 25, tzinfo=timezone.utc)
    articles = [
        RawArticle("Claude", "Claude update", "u1", "official_blog",
                   published_at=dt, popularity=99),
    ]
    llm = _fake_llm([
        (_ANCHOR_SUB, [1.0, 0.0, 0.0]),
        ("Claude", [1.0, 0.05, 0.0]),
    ])
    out = cluster_and_filter(articles, llm, brief_date="d")
    assert len(out) == 1
    assert out[0].published_at == dt
    assert out[0].popularity == 99
    assert out[0].cluster_key is not None  # 부여됨
    assert out[0].technology_name == "Claude"  # 재라벨됨(derive_tech)


# ─── AC4: 안전 저하 & 무회귀 ──────────────────────────────────────────────────

def test_passthrough_when_llm_none():
    """llm 부재 → 입력 그대로(길이·라벨 불변)."""
    articles = [
        RawArticle("Claude", "t", "u1", "official_blog"),
        RawArticle("MCP", "t2", "u2", "github"),
    ]
    out = cluster_and_filter(articles, None, brief_date="d")
    assert out == articles
    assert [a.technology_name for a in out] == ["Claude", "MCP"]


def test_passthrough_when_disabled():
    """clustering_enabled=False → pass-through, 임베딩 호출 없음."""
    articles = [RawArticle("Claude", "t", "u1", "official_blog")]
    llm = _fake_llm([(_ANCHOR_SUB, [1.0, 0.0, 0.0])])
    with patch("pipeline.clustering.settings.clustering_enabled", False):
        out = cluster_and_filter(articles, llm, brief_date="d")
    assert [a.technology_name for a in out] == ["Claude"]
    llm.embed_text.assert_not_called()


def test_empty_input_returns_empty():
    """빈 입력 → 빈 출력(가드)."""
    assert cluster_and_filter([], MagicMock(), brief_date="d") == []


def test_embed_failure_isolated():
    """개별 기사 임베딩 실패는 격리 — 그 기사만 원본 라벨로 pass-through, 나머지 정상."""
    articles = [
        RawArticle("Claude", "Claude good", "u1", "official_blog"),
        RawArticle("MCP", "MCP bad embed", "u2", "official_blog"),
    ]
    llm = MagicMock()

    def embed(text):
        if _ANCHOR_SUB in text:
            return [1.0, 0.0, 0.0]
        if "bad embed" in text:
            raise RuntimeError("embed fail")
        return [1.0, 0.05, 0.0]

    llm.embed_text.side_effect = embed
    with patch("pipeline.clustering.pipeline_log") as mock_log:
        out = cluster_and_filter(articles, llm, brief_date="d")
    assert {a.url for a in out} == {"u1", "u2"}  # 실패 기사도 살아남음
    labels = {a.url: a.technology_name for a in out}
    assert labels["u2"] == "MCP"  # 원본 라벨 유지
    fails = [e for e in _events(mock_log) if e.get("event") == "article_embed_failed"]
    assert len(fails) == 1 and fails[0]["url"] == "u2"


def test_clustering_done_logged():
    """clustering_done 요약 로그에 집계 필드 포함."""
    articles = [
        RawArticle("Claude", "Claude update", "u1", "official_blog"),
        RawArticle("General AI", "Smart rings sleep tracker", "u2", "other"),
    ]
    llm = _fake_llm([
        (_ANCHOR_SUB, [1.0, 0.0, 0.0]),
        ("Claude", [1.0, 0.05, 0.0]),
        ("Smart rings", [0.0, 1.0, 0.0]),
    ])
    with patch("pipeline.clustering.pipeline_log") as mock_log:
        cluster_and_filter(articles, llm, brief_date="d")
    done = [e for e in _events(mock_log) if e.get("event") == "clustering_done"]
    assert len(done) == 1
    e = done[0]
    assert e["input"] == 2
    assert e["filtered_off_domain"] == 1
    assert e["cluster_count"] == 1
