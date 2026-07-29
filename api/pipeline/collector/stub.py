from pipeline.collector.base import BaseCollector
from pipeline.models import RawArticle


class StubCollector(BaseCollector):
    """파이프라인 검증용 스텁 — 하드코딩된 AI 기술 기사 5개 반환."""

    def collect(self) -> list[RawArticle]:
        return [
            RawArticle(
                technology_name="LangGraph",
                title="LangGraph 0.3 릴리스 — 새로운 Persistence 모델",
                url="https://blog.langchain.dev/langgraph-0-3",
                source_type="official_blog",
            ),
            RawArticle(
                technology_name="LangGraph",
                title="LangGraph multi-agent patterns - GitHub",
                url="https://github.com/langchain-ai/langgraph/discussions/1234",
                source_type="github",
            ),
            RawArticle(
                technology_name="MCP",
                title="Model Context Protocol 공식 스펙 업데이트",
                url="https://modelcontextprotocol.io/blog/mcp-spec-update",
                source_type="official_blog",
            ),
            RawArticle(
                technology_name="MCP",
                title="MCP가 정말 필요한가? — 토론",
                url="https://news.ycombinator.com/item?id=99999",
                source_type="hn",
            ),
            RawArticle(
                technology_name="OpenAI Responses API",
                title="OpenAI Responses API — Chat Completions 대체 이유",
                url="https://platform.openai.com/docs/guides/responses-vs-chat",
                source_type="official_blog",
            ),
        ]
