"""Signal Pipeline Foundation 단위 테스트 (Story 2.1).

Supabase Mock으로 실행 가능 — 환경변수 불필요.
"""
from datetime import date
from unittest.mock import MagicMock, patch

from pipeline.collector.stub import StubCollector
from pipeline.logger import pipeline_log
from pipeline.models import RawArticle
from pipeline.normalizer import normalize


# ─── RawArticle 테스트 ────────────────────────────────────────────────────────

def test_raw_article_creation():
    a = RawArticle(
        technology_name="MCP",
        title="MCP 소개",
        url="https://example.com",
        source_type="official_blog",
    )
    assert a.technology_name == "MCP"
    assert a.title == "MCP 소개"
    assert a.url == "https://example.com"
    assert a.source_type == "official_blog"
    assert a.content == ""


def test_raw_article_with_content():
    a = RawArticle(
        technology_name="LangGraph",
        title="LangGraph 0.3",
        url="https://blog.langchain.dev/langgraph-0-3",
        source_type="official_blog",
        content="본문 내용",
    )
    assert a.content == "본문 내용"


# ─── StubCollector 테스트 ─────────────────────────────────────────────────────

def test_stub_collector_returns_list():
    articles = StubCollector().collect()
    assert isinstance(articles, list)


def test_stub_collector_returns_at_least_one_article():
    articles = StubCollector().collect()
    assert len(articles) >= 1


def test_stub_collector_all_items_are_raw_articles():
    articles = StubCollector().collect()
    assert all(isinstance(a, RawArticle) for a in articles)


# ─── Mock 헬퍼 ───────────────────────────────────────────────────────────────

def _make_mock_client(upsert_data=None):
    """테이블별 독립 mock을 가진 Supabase Client 흉내.

    Attributes on returned client:
      _signals_mock  -- mock for table("signals")
      _sources_mock  -- mock for table("signal_sources")
    """
    mock_client = MagicMock()

    signals_mock = MagicMock()
    signals_mock.upsert.return_value.execute.return_value.data = (
        upsert_data if upsert_data is not None else [{"id": "test-uuid"}]
    )

    sources_mock = MagicMock()
    sources_mock.insert.return_value.execute.return_value.data = [{"id": "src-uuid"}]

    def table_side_effect(table_name):
        return signals_mock if table_name == "signals" else sources_mock

    mock_client.table.side_effect = table_side_effect
    mock_client._signals_mock = signals_mock
    mock_client._sources_mock = sources_mock
    return mock_client


# ─── Normalizer 그룹핑 테스트 ─────────────────────────────────────────────────

def test_normalizer_groups_by_technology():
    """동일 technology_name의 기사 3개 → Signal 1개."""
    articles = [
        RawArticle("LangGraph", "LangGraph 0.3", "https://a.com", "official_blog"),
        RawArticle("LangGraph", "LangGraph GitHub", "https://b.com", "github"),
        RawArticle("LangGraph", "LangGraph Reddit", "https://c.com", "reddit"),
    ]
    mock_client = _make_mock_client()

    signal_ids = normalize(articles, date(2026, 7, 24), mock_client, brief_date="2026-07-24")

    assert len(signal_ids) == 1


def test_normalizer_multiple_technologies():
    """서로 다른 기술 2개 → Signal 2개."""
    articles = [
        RawArticle("LangGraph", "LangGraph 0.3", "https://a.com", "official_blog"),
        RawArticle("LangGraph", "LangGraph GitHub", "https://b.com", "github"),
        RawArticle("MCP", "MCP spec", "https://c.com", "official_blog"),
    ]
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

    def table_side_effect(table_name):
        return signals_mock if table_name == "signals" else sources_mock

    mock_client.table.side_effect = table_side_effect

    signal_ids = normalize(articles, date(2026, 7, 24), mock_client, brief_date="2026-07-24")

    assert len(signal_ids) == 2


# ─── Normalizer 중복 방지 테스트 ─────────────────────────────────────────────

def test_normalizer_deduplication_skips_existing():
    """DB ON CONFLICT DO NOTHING → upsert 빈 data 반환 시 INSERT 스킵."""
    articles = [RawArticle("LangGraph", "Title", "https://a.com", "official_blog")]
    mock_client = _make_mock_client(upsert_data=[])  # conflict → no row inserted

    signal_ids = normalize(articles, date(2026, 7, 24), mock_client, brief_date="2026-07-24")

    assert signal_ids == []
    mock_client._sources_mock.insert.assert_not_called()


# ─── signal_sources 개별 저장 테스트 ─────────────────────────────────────────

def test_normalizer_signal_sources_count():
    """그룹 내 기사 3개 → signal_sources 3개 INSERT."""
    articles = [
        RawArticle("LangGraph", "Title A", "https://a.com", "official_blog"),
        RawArticle("LangGraph", "Title B", "https://b.com", "github"),
        RawArticle("LangGraph", "Title C", "https://c.com", "reddit"),
    ]
    mock_client = _make_mock_client(upsert_data=[{"id": "signal-uuid"}])

    normalize(articles, date(2026, 7, 24), mock_client, brief_date="2026-07-24")

    mock_client._sources_mock.insert.assert_called_once()
    sources_data = mock_client._sources_mock.insert.call_args[0][0]
    assert len(sources_data) == 3


def test_normalizer_signal_sources_fields():
    """signal_sources INSERT 데이터에 signal_id, source_type, url, title 포함."""
    articles = [RawArticle("MCP", "MCP 소개", "https://example.com", "official_blog")]
    mock_client = _make_mock_client(upsert_data=[{"id": "sig-id"}])

    normalize(articles, date(2026, 7, 24), mock_client, brief_date="2026-07-24")

    sources_data = mock_client._sources_mock.insert.call_args[0][0]
    assert sources_data[0]["signal_id"] == "sig-id"
    assert sources_data[0]["source_type"] == "official_blog"
    assert sources_data[0]["url"] == "https://example.com"
    assert sources_data[0]["title"] == "MCP 소개"


def test_normalizer_signal_sources_insert_failure():
    """signal_sources INSERT 실패 시 signal_id 반환 목록 제외."""
    articles = [RawArticle("LangGraph", "Title", "https://a.com", "official_blog")]
    mock_client = _make_mock_client(upsert_data=[{"id": "signal-uuid"}])
    mock_client._sources_mock.insert.return_value.execute.return_value.data = []

    signal_ids = normalize(articles, date(2026, 7, 24), mock_client, brief_date="2026-07-24")

    assert signal_ids == []


# ─── technology_name 검증 테스트 ─────────────────────────────────────────────

def test_normalizer_empty_technology_name_skipped():
    """빈 technology_name 기사는 스킵, 유효한 기술만 Signal 생성."""
    articles = [
        RawArticle("", "Title", "https://a.com", "official_blog"),
        RawArticle("   ", "Title2", "https://b.com", "official_blog"),
        RawArticle("LangGraph", "Valid", "https://c.com", "official_blog"),
    ]
    mock_client = _make_mock_client()

    signal_ids = normalize(articles, date(2026, 7, 24), mock_client, brief_date="2026-07-24")

    assert len(signal_ids) == 1


# ─── Supabase 예외 처리 테스트 ───────────────────────────────────────────────

def test_normalizer_supabase_error_skips_tech_and_continues():
    """Supabase 예외 발생 시 해당 기술 스킵 후 다음 기술 계속 처리."""
    articles = [
        RawArticle("BrokenTech", "Title", "https://a.com", "official_blog"),
        RawArticle("GoodTech", "Title2", "https://b.com", "official_blog"),
    ]
    mock_client = MagicMock()
    signals_mock = MagicMock()
    sources_mock = MagicMock()
    sources_mock.insert.return_value.execute.return_value.data = [{"id": "src"}]

    def upsert_side_effect(data, **kwargs):
        if data["technology_name"] == "BrokenTech":
            raise RuntimeError("DB error")
        m = MagicMock()
        m.execute.return_value.data = [{"id": "good-uuid"}]
        return m

    signals_mock.upsert.side_effect = upsert_side_effect

    def table_side_effect(table_name):
        return signals_mock if table_name == "signals" else sources_mock

    mock_client.table.side_effect = table_side_effect

    signal_ids = normalize(articles, date(2026, 7, 24), mock_client, brief_date="2026-07-24")

    assert signal_ids == ["good-uuid"]


# ─── pipeline_log 구조화 필드 테스트 ─────────────────────────────────────────

def test_pipeline_log_structured_fields():
    """pipeline_log()가 brief_date, pipeline_stage, user_count 필드를 포함."""
    with patch("pipeline.logger._pipeline_logger") as mock_logger:
        pipeline_log(stage="collector", brief_date="2026-07-24", user_count=5)

        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        extra = call_args[1]["extra"]

        assert extra["pipeline_stage"] == "collector"
        assert extra["brief_date"] == "2026-07-24"
        assert extra["user_count"] == 5


def test_pipeline_log_default_user_count():
    """pipeline_log() user_count 기본값 = 0."""
    with patch("pipeline.logger._pipeline_logger") as mock_logger:
        pipeline_log(stage="normalizer", brief_date="2026-07-24")

        extra = mock_logger.log.call_args[1]["extra"]
        assert extra["user_count"] == 0


def test_pipeline_log_extra_fields():
    """pipeline_log()에 추가 필드 전달 시 extra에 포함."""
    with patch("pipeline.logger._pipeline_logger") as mock_logger:
        pipeline_log(stage="normalizer", brief_date="2026-07-24", article_count=10)

        extra = mock_logger.log.call_args[1]["extra"]
        assert extra["article_count"] == 10
