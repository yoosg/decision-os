from unittest.mock import MagicMock

from pipeline.collector.hackernews import HackerNewsCollector
from pipeline.collector import registry


def _resp(hits):
    r = MagicMock()
    r.json.return_value = {"hits": hits}
    r.raise_for_status.return_value = None
    return r


def test_min_points_filters_low_score_hits():
    client = MagicMock()
    client.get.return_value = _resp([
        {"title": "big tool launch", "url": "https://a", "points": 120, "objectID": "1"},
        {"title": "low signal news", "url": "https://b", "points": 3, "objectID": "2"},
    ])
    c = HackerNewsCollector(["LLM"], client, min_points=50, per_query=10)
    out = c.collect()
    urls = {a.url for a in out}
    assert "https://a" in urls and "https://b" not in urls


def test_min_points_sent_as_numeric_filter():
    client = MagicMock()
    client.get.return_value = _resp([])
    HackerNewsCollector(["LLM"], client, min_points=50).collect()
    params = client.get.call_args.kwargs["params"]
    assert params.get("numericFilters") == "points>=50"


def test_tags_included_in_params():
    client = MagicMock()
    client.get.return_value = _resp([])
    HackerNewsCollector([""], client, tags=("show_hn",)).collect()
    params = client.get.call_args.kwargs["params"]
    assert "show_hn" in params["tags"]


def test_registry_has_no_verge_and_has_github_releases():
    names = [s.name for s in registry.SOURCES]
    assert "The Verge AI" not in names
    kinds_urls = [(s.kind, s.url) for s in registry.SOURCES]
    assert ("github", "vllm-project/vllm") in kinds_urls
    hn = [s for s in registry.SOURCES if s.kind == "hn"]
    assert any(s.min_points >= 50 for s in hn)
