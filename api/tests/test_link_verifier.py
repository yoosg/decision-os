from unittest.mock import MagicMock

import httpx
import pytest

from pipeline.link_verifier import verify_and_fix_links, _search_url


class _Resp:
    def __init__(self, status_code: int):
        self.status_code = status_code


def _client(status_by_url: dict):
    """url→상태코드(int) 또는 예외 인스턴스를 돌려주는 mock httpx.Client."""
    client = MagicMock()

    def _get(url, timeout=None):
        val = status_by_url[url]
        if isinstance(val, Exception):
            raise val
        return _Resp(val)

    client.get.side_effect = _get
    return client


def _resources():
    return [
        {"type": "official_docs", "title": "T1", "url": "https://a.dev/docs", "descriptor": "d1"},
        {"type": "core_material", "title": "T2", "url": "https://b.dev/guide", "descriptor": "d2"},
        {"type": "github", "title": "T3", "url": "https://github.com/x/y", "descriptor": "d3"},
        {"type": "practice_example", "title": "T4", "url": "https://c.dev/ex", "descriptor": "d4"},
        {"type": "applied_idea", "title": "T5", "url": "", "descriptor": "d5"},
    ]


def test_alive_links_are_kept_unchanged():
    urls = {r["url"]: 200 for r in _resources() if r["url"]}
    out = verify_and_fix_links(_resources(), "LangGraph", _client(urls), 5.0)
    assert [r["url"] for r in out[:4]] == [r["url"] for r in _resources()[:4]]
    assert all("is_search_fallback" not in r for r in out)


def test_404_link_is_replaced_with_search_and_flagged():
    urls = {r["url"]: 200 for r in _resources() if r["url"]}
    urls["https://a.dev/docs"] = 404
    out = verify_and_fix_links(_resources(), "LangGraph", _client(urls), 5.0)
    assert out[0]["is_search_fallback"] is True
    assert out[0]["url"].startswith("https://www.google.com/search?q=")
    assert "LangGraph" in out[0]["url"]
    # 제목/설명/타입은 원본 유지
    assert (out[0]["title"], out[0]["descriptor"], out[0]["type"]) == ("T1", "d1", "official_docs")


def test_410_link_is_replaced():
    urls = {r["url"]: 200 for r in _resources() if r["url"]}
    urls["https://b.dev/guide"] = 410
    out = verify_and_fix_links(_resources(), "LangGraph", _client(urls), 5.0)
    assert out[1]["is_search_fallback"] is True


@pytest.mark.parametrize("err", [httpx.TimeoutException("t"), httpx.ConnectError("c")])
def test_network_failures_are_replaced(err):
    urls = {r["url"]: 200 for r in _resources() if r["url"]}
    urls["https://c.dev/ex"] = err
    out = verify_and_fix_links(_resources(), "LangGraph", _client(urls), 5.0)
    assert out[3]["is_search_fallback"] is True


@pytest.mark.parametrize("code", [401, 403, 429, 500, 503])
def test_ambiguous_statuses_are_kept(code):
    urls = {r["url"]: 200 for r in _resources() if r["url"]}
    urls["https://a.dev/docs"] = code
    out = verify_and_fix_links(_resources(), "LangGraph", _client(urls), 5.0)
    assert "is_search_fallback" not in out[0]
    assert out[0]["url"] == "https://a.dev/docs"


def test_applied_idea_empty_url_is_untouched_and_not_requested():
    urls = {r["url"]: 200 for r in _resources() if r["url"]}
    client = _client(urls)
    out = verify_and_fix_links(_resources(), "LangGraph", client, 5.0)
    assert out[4]["url"] == ""
    assert "is_search_fallback" not in out[4]
    requested = {call.args[0] for call in client.get.call_args_list}
    assert "" not in requested


def test_length_order_and_types_preserved():
    urls = {r["url"]: 404 for r in _resources() if r["url"]}
    out = verify_and_fix_links(_resources(), "LangGraph", _client(urls), 5.0)
    assert len(out) == 5
    assert [r["type"] for r in out] == [r["type"] for r in _resources()]


def test_search_url_includes_tech_and_label_encoded():
    url = _search_url("Llama Index", "official_docs")
    assert url.startswith("https://www.google.com/search?q=")
    # 공백은 quote_plus로 '+' 인코딩
    assert "Llama+Index" in url
    assert "%EA%B3%B5%EC%8B%9D" in url  # '공식'의 URL 인코딩 일부


def test_extra_keys_like_objective_are_preserved_on_replace():
    """죽은 링크 교체 시에도 objective 등 추가 키가 보존된다(작업 B 2단계 상호작용)."""
    resources = [dict(r, objective=f"obj{i}") for i, r in enumerate(_resources())]
    urls = {r["url"]: 200 for r in resources if r["url"]}
    urls["https://a.dev/docs"] = 404  # 첫 리소스를 죽은 링크로
    out = verify_and_fix_links(resources, "LangGraph", _client(urls), 5.0)
    # 교체된 리소스도 objective 유지
    assert out[0]["is_search_fallback"] is True
    assert out[0]["objective"] == "obj0"
    # 나머지도 objective 유지
    assert [r["objective"] for r in out] == [f"obj{i}" for i in range(5)]
