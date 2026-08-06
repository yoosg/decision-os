import json
from unittest.mock import MagicMock, patch

from pipeline.curator import curate_learnability
from pipeline.llm.base import LLMProviderError, LLMResponse
from pipeline.models import RawArticle


def _llm(results):
    llm = MagicMock()
    llm.classify_learnability.return_value = LLMResponse(
        content=json.dumps({"results": results})
    )
    return llm


def _art(label, title, url, ck):
    return RawArticle(label, title, url, "hn", cluster_key=ck)


def test_drops_non_learnable_and_renames_kept():
    articles = [
        _art("General AI", "OpenAI 353,000명 협력", "u0", "ck0"),
        _art("LangGraph", "LangGraph 0.3 릴리스", "u1", "ck1"),
    ]
    # 정렬(ck0<ck1) 후 id 0=OpenAI, 1=LangGraph
    llm = _llm([
        {"id": 0, "keep": False, "category": "business_news", "name": "OpenAI 협력"},
        {"id": 1, "keep": True, "category": "tool_update", "name": "LangGraph 0.3"},
    ])
    with patch("pipeline.curator.settings") as s:
        s.learnability_filter_enabled = True
        out = curate_learnability(articles, llm, brief_date="d")
    assert len(out) == 1
    assert out[0].url == "u1" and out[0].technology_name == "LangGraph 0.3"


def test_cluster_members_share_new_name():
    articles = [
        _art("General AI", "Claude MCP 커넥터", "u0", "ck"),
        _art("General AI", "HN: Claude MCP 토론", "u1", "ck"),
    ]
    llm = _llm([{"id": 0, "keep": True, "category": "new_tool", "name": "Claude MCP"}])
    with patch("pipeline.curator.settings") as s:
        s.learnability_filter_enabled = True
        out = curate_learnability(articles, llm, brief_date="d")
    assert len(out) == 2
    assert {a.technology_name for a in out} == {"Claude MCP"}


def test_safe_degrade_when_disabled():
    articles = [_art("X", "t", "u", "ck")]
    with patch("pipeline.curator.settings") as s:
        s.learnability_filter_enabled = False
        out = curate_learnability(articles, MagicMock(), brief_date="d")
    assert out == articles


def test_safe_degrade_when_llm_none():
    articles = [_art("X", "t", "u", "ck")]
    with patch("pipeline.curator.settings") as s:
        s.learnability_filter_enabled = True
        out = curate_learnability(articles, None, brief_date="d")
    assert out == articles


def test_safe_degrade_on_llm_error():
    articles = [_art("X", "t", "u", "ck")]
    llm = MagicMock()
    llm.classify_learnability.side_effect = LLMProviderError("boom")
    with patch("pipeline.curator.settings") as s:
        s.learnability_filter_enabled = True
        out = curate_learnability(articles, llm, brief_date="d")
    assert out == articles


def test_dropped_topic_is_logged():
    articles = [_art("General AI", "AI 아티스트 논쟁", "u0", "ck0")]
    llm = _llm([{"id": 0, "keep": False, "category": "social_ethics", "name": "논쟁"}])
    with patch("pipeline.curator.settings") as s, \
         patch("pipeline.curator.pipeline_log") as log:
        s.learnability_filter_enabled = True
        curate_learnability(articles, llm, brief_date="d")
    events = [c.kwargs.get("event") for c in log.call_args_list]
    assert "topic_dropped" in events


def test_safe_degrade_on_empty_input():
    # 빈 입력은 토글/llm 상태와 무관하게 전량(=빈) 통과, 예외 없음.
    assert curate_learnability([], MagicMock(), brief_date="d") == []


def test_distinct_clusters_with_same_name_converge_for_normalize():
    # 의도된 계약(문서주석 참고): 서로 다른 cluster_key 토픽이 같은 name을 받으면
    # curator는 둘 다 그 name으로 개명한다 → 이후 normalize가 technology_name 기준으로
    # 하나의 signal로 병합(중복제거). curator 단계에서는 아직 두 기사 모두 남아있다.
    articles = [
        _art("General AI", "vLLM 0.6 릴리스", "u0", "ck0"),
        _art("vLLM stuff", "vLLM 성능 개선 글", "u1", "ck1"),
    ]
    llm = _llm([
        {"id": 0, "keep": True, "category": "tool_update", "name": "vLLM"},
        {"id": 1, "keep": True, "category": "tool_update", "name": "vLLM"},
    ])
    with patch("pipeline.curator.settings") as s:
        s.learnability_filter_enabled = True
        out = curate_learnability(articles, llm, brief_date="d")
    assert len(out) == 2
    assert {a.technology_name for a in out} == {"vLLM"}
