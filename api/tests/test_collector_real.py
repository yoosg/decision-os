"""실 수집기 어댑터 & aggregator 단위 테스트 (Story 6.1).

오프라인 원칙: 실제 네트워크 호출 금지 — httpx.Client를 MagicMock/monkeypatch로
대체하고 고정 RSS/Atom·HN JSON 픽스처를 주입한다.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import certifi

from pipeline.collector import aggregator
from pipeline.collector.aggregator import _dedup, run_collectors
from pipeline.collector.github import GitHubReleasesCollector
from pipeline.collector.hackernews import HackerNewsCollector
from pipeline.collector.registry import Source, build_collectors
from pipeline.collector.rss import RssCollector, derive_tech
from pipeline.models import RawArticle

# ─── 픽스처 ───────────────────────────────────────────────────────────────────

RSS_XML = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
<title>Test Feed</title>
<item><title>OpenAI releases GPT-5</title><link>https://ex.com/a</link></item>
<item><title>Anthropic Claude gets an update</title><link>https://ex.com/b</link></item>
<item><title>A totally unrelated post</title><link>https://ex.com/c</link></item>
</channel></rss>"""

# link 누락 item은 스킵되어야 함
RSS_XML_MISSING_LINK = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>Has link</title><link>https://ex.com/a</link></item>
<item><title>No link here</title></item>
</channel></rss>"""

GITHUB_ATOM = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>Release notes from langgraph</title>
<entry><title>v0.3.0</title>
<link href="https://github.com/langchain-ai/langgraph/releases/tag/0.3.0"/></entry>
</feed>"""

HN_JSON = {
    "hits": [
        {"title": "New RAG technique", "url": "https://hn-ex.com/1", "objectID": "111"},
        {"title": "Show HN: my LLM tool", "url": None, "objectID": "222"},
        {"title": "", "url": "https://hn-ex.com/3", "objectID": "333"},  # 빈 제목 → 스킵
    ]
}

# Story 6.3: pubDate 있는 RSS → published_at 파싱 검증용
RSS_XML_WITH_DATE = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>Claude ships something</title><link>https://ex.com/d</link>
<pubDate>Sat, 25 Jul 2026 08:30:00 +0000</pubDate></item>
<item><title>No date here about GPT-5</title><link>https://ex.com/e</link></item>
</channel></rss>"""

# Story 6.3: points/created_at_i 있는 HN hit → popularity/published_at 파싱 검증용
HN_JSON_WITH_META = {
    "hits": [
        {"title": "RAG breakthrough", "url": "https://hn-ex.com/m1", "objectID": "901",
         "points": 240, "created_at_i": 1_770_000_000},
        {"title": "LLM tool via ISO date", "url": "https://hn-ex.com/m2", "objectID": "902",
         "created_at": "2026-07-25T08:30:00.000Z"},
    ]
}


class _FakeResponse:
    def __init__(self, content=b"", json_data=None):
        self.content = content
        self._json = json_data

    def raise_for_status(self):
        return None

    def json(self):
        return self._json


def _client_returning(response):
    client = MagicMock()
    client.get.return_value = response
    return client


# ─── RSS 어댑터 ───────────────────────────────────────────────────────────────

def test_rss_collector_maps_entries():
    client = _client_returning(_FakeResponse(content=RSS_XML))
    articles = RssCollector("Test", "https://feed", "official_blog", client).collect()

    assert len(articles) == 3
    assert all(isinstance(a, RawArticle) for a in articles)
    assert articles[0].title == "OpenAI releases GPT-5"
    assert articles[0].url == "https://ex.com/a"
    assert articles[0].source_type == "official_blog"
    # 휴리스틱: "GPT-5"가 키워드 리스트에서 먼저 매치
    assert articles[0].technology_name == "GPT-5"
    assert articles[1].technology_name == "Claude"


def test_rss_collector_technology_name_never_empty():
    client = _client_returning(_FakeResponse(content=RSS_XML))
    articles = RssCollector("Test", "https://feed", "official_blog", client).collect()
    # 매치 없는 기사 → "General AI" (빈 문자열 금지 — normalize 스킵 방지)
    assert articles[2].technology_name == "General AI"
    assert all(a.technology_name.strip() for a in articles)


def test_rss_collector_skips_entries_without_link():
    client = _client_returning(_FakeResponse(content=RSS_XML_MISSING_LINK))
    articles = RssCollector("Test", "https://feed", "official_blog", client).collect()
    assert len(articles) == 1
    assert articles[0].url == "https://ex.com/a"


def test_rss_collector_respects_max_items():
    client = _client_returning(_FakeResponse(content=RSS_XML))
    articles = RssCollector("Test", "https://feed", "official_blog", client, max_items=1).collect()
    assert len(articles) == 1


def test_rss_collector_parses_published_at():
    """Story 6.3: pubDate 있으면 published_at UTC datetime, 없으면 None(safe degrade)."""
    client = _client_returning(_FakeResponse(content=RSS_XML_WITH_DATE))
    articles = RssCollector("Test", "https://feed", "official_blog", client).collect()

    assert articles[0].published_at == datetime(2026, 7, 25, 8, 30, 0, tzinfo=timezone.utc)
    assert articles[1].published_at is None  # pubDate 없음
    # RSS는 popularity 없음 → 기본 0
    assert articles[0].popularity == 0


# ─── HackerNews 어댑터 ────────────────────────────────────────────────────────

def test_hn_collector_maps_hits():
    client = _client_returning(_FakeResponse(json_data=HN_JSON))
    articles = HackerNewsCollector(["RAG"], client).collect()

    # 빈 제목 hit은 스킵 → 2건
    assert len(articles) == 2
    assert all(a.source_type == "hn" for a in articles)
    assert articles[0].url == "https://hn-ex.com/1"
    # url 없으면 HN 스레드 URL로 폴백
    assert articles[1].url == "https://news.ycombinator.com/item?id=222"


def test_hn_collector_respects_max_total():
    client = _client_returning(_FakeResponse(json_data=HN_JSON))
    articles = HackerNewsCollector(["RAG", "LLM"], client, max_total=1).collect()
    assert len(articles) == 1


def test_hn_collector_parses_popularity_and_published_at():
    """Story 6.3: points→popularity, created_at_i(unix)→published_at, created_at(ISO) 폴백."""
    client = _client_returning(_FakeResponse(json_data=HN_JSON_WITH_META))
    articles = HackerNewsCollector(["RAG"], client).collect()

    assert articles[0].popularity == 240
    assert articles[0].published_at == datetime.fromtimestamp(1_770_000_000, tz=timezone.utc)
    # created_at(ISO) 폴백 경로
    assert articles[1].published_at == datetime(2026, 7, 25, 8, 30, 0, tzinfo=timezone.utc)
    # points 없으면 0(safe degrade)
    assert articles[1].popularity == 0


def test_hn_collector_missing_meta_safe_degrades():
    """points/created_at 모두 없으면 popularity=0, published_at=None(예외 없음)."""
    client = _client_returning(_FakeResponse(json_data=HN_JSON))
    articles = HackerNewsCollector(["RAG"], client).collect()
    assert all(a.popularity == 0 and a.published_at is None for a in articles)


# ─── GitHub Releases 어댑터 ───────────────────────────────────────────────────

def test_github_collector_url_source_type_and_tech():
    client = _client_returning(_FakeResponse(content=GITHUB_ATOM))
    articles = GitHubReleasesCollector("langchain-ai/langgraph", client).collect()

    client.get.assert_called_with("https://github.com/langchain-ai/langgraph/releases.atom")
    assert len(articles) == 1
    assert articles[0].source_type == "github"
    # repo 문맥으로 파생 → "v0.3.0"만으론 못 잡는 기술명을 잡음
    assert articles[0].technology_name == "LangGraph"


# ─── 레지스트리 팩토리 ────────────────────────────────────────────────────────

def test_build_collectors_maps_kinds():
    sources = [
        Source("rss-src", "rss", "official_blog", url="https://feed"),
        Source("hn-src", "hn", "hn", queries=("LLM",)),
        Source("gh-src", "github", "github", url="owner/repo"),
    ]
    collectors = build_collectors(MagicMock(), sources=sources)
    assert isinstance(collectors[0], RssCollector)
    assert isinstance(collectors[1], HackerNewsCollector)
    assert isinstance(collectors[2], GitHubReleasesCollector)


def test_build_collectors_filters_disabled():
    sources = [
        Source("on", "rss", "official_blog", url="https://a"),
        Source("off", "rss", "official_blog", url="https://b", enabled=False),
    ]
    collectors = build_collectors(MagicMock(), sources=sources)
    assert len(collectors) == 1
    assert collectors[0].name == "on"


# ─── Aggregator: 격리 ─────────────────────────────────────────────────────────

class _DummyCM:
    def __enter__(self):
        return MagicMock()

    def __exit__(self, *a):
        return False


def test_aggregator_isolates_failing_source(monkeypatch):
    good = MagicMock()
    good.name = "good"
    good.collect.return_value = [RawArticle("MCP", "title", "https://x", "hn")]
    bad = MagicMock()
    bad.name = "bad"
    bad.collect.side_effect = RuntimeError("boom")

    monkeypatch.setattr(aggregator.httpx, "Client", lambda **kw: _DummyCM())
    monkeypatch.setattr(aggregator, "build_collectors", lambda client: [bad, good])

    logs = []
    monkeypatch.setattr(aggregator, "pipeline_log", lambda **kw: logs.append(kw))

    result = run_collectors(brief_date="2026-07-29")

    # 한 소스 실패해도 나머지 결과 반환
    assert len(result) == 1
    assert result[0].technology_name == "MCP"

    events = [l["event"] for l in logs]
    assert "source_failed" in events
    assert "source_collected" in events
    assert "dedup_done" in events
    failed = next(l for l in logs if l["event"] == "source_failed")
    assert failed["source"] == "bad"
    assert failed["level"] == "error"


# ─── Aggregator: exact dedup ──────────────────────────────────────────────────

def test_dedup_removes_same_url():
    articles = [
        RawArticle("A", "Title one", "https://x", "hn"),
        RawArticle("B", "Title two", "https://x", "official_blog"),
    ]
    out, removed = _dedup(articles)
    assert len(out) == 1
    assert removed == 1


def test_dedup_removes_same_normalized_title():
    articles = [
        RawArticle("A", "Agent Intrusion", "https://x", "hn"),
        RawArticle("B", "  agent intrusion ", "https://y", "official_blog"),
    ]
    out, removed = _dedup(articles)
    assert len(out) == 1
    assert removed == 1


def test_dedup_keeps_distinct():
    articles = [
        RawArticle("A", "Title one", "https://x", "hn"),
        RawArticle("B", "Title two", "https://y", "official_blog"),
    ]
    out, removed = _dedup(articles)
    assert len(out) == 2
    assert removed == 0


# ─── Aggregator: certifi / timeout 전달 ───────────────────────────────────────

def test_aggregator_uses_certifi_and_timeout(monkeypatch):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return _DummyCM()

    monkeypatch.setattr(aggregator.httpx, "Client", fake_client)
    monkeypatch.setattr(aggregator, "build_collectors", lambda client: [])

    run_collectors(brief_date="d", timeout=7.5)

    assert captured["verify"] == certifi.where()
    assert captured["timeout"] == 7.5
    assert captured["follow_redirects"] is True
    assert "User-Agent" in captured["headers"]


# ─── Orchestrator collector_mode 분기 ─────────────────────────────────────────

def _stub_orchestrator_downstream(monkeypatch, orch):
    monkeypatch.setattr(orch, "get_supabase", lambda: MagicMock())
    monkeypatch.setattr(orch, "get_llm_provider", lambda: MagicMock())
    monkeypatch.setattr(orch, "normalize", lambda *a, **k: [])
    monkeypatch.setattr(orch, "build_signals", lambda *a, **k: [])
    monkeypatch.setattr(orch, "run_recommender", lambda *a, **k: 0)


def test_orchestrator_real_mode_calls_run_collectors(monkeypatch):
    from pipeline import orchestrator as orch

    calls = {"real": 0, "stub": 0}
    monkeypatch.setattr(orch.settings, "collector_mode", "real")
    monkeypatch.setattr(orch, "run_collectors", lambda **kw: calls.__setitem__("real", calls["real"] + 1) or [])

    class _FakeStub:
        def collect(self):
            calls["stub"] += 1
            return []

    monkeypatch.setattr(orch, "StubCollector", _FakeStub)
    _stub_orchestrator_downstream(monkeypatch, orch)

    result = orch.run_daily_pipeline("2026-07-29")

    assert calls["real"] == 1
    assert calls["stub"] == 0
    assert result["error"] is None


def test_orchestrator_stub_mode_uses_stub_collector(monkeypatch):
    from pipeline import orchestrator as orch

    calls = {"real": 0, "stub": 0}
    monkeypatch.setattr(orch.settings, "collector_mode", "stub")
    monkeypatch.setattr(orch, "run_collectors", lambda **kw: calls.__setitem__("real", calls["real"] + 1) or [])

    class _FakeStub:
        def collect(self):
            calls["stub"] += 1
            return []

    monkeypatch.setattr(orch, "StubCollector", _FakeStub)
    _stub_orchestrator_downstream(monkeypatch, orch)

    result = orch.run_daily_pipeline("2026-07-29")

    assert calls["stub"] == 1
    assert calls["real"] == 0
    assert result["error"] is None
