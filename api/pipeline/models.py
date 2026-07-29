from dataclasses import dataclass
from datetime import datetime
from typing import Literal

SourceType = Literal['official_blog', 'github', 'reddit', 'hn', 'youtube', 'other']


@dataclass
class RawArticle:
    technology_name: str
    title: str
    url: str
    source_type: SourceType
    content: str = ""
    # Story 6.3 랭킹 메타데이터. ⚠️ 기존 필드 뒤(맨 끝)에 기본값과 함께 추가 —
    # positional 생성(RawArticle("MCP", "title", "url", "official_blog"))을 쓰는
    # 기존 테스트 무회귀를 위해 순서를 절대 앞당기지 말 것.
    published_at: datetime | None = None  # 원문 발행 시각(UTC). 없으면 None(safe degrade).
    popularity: int = 0                   # 인기 신호(예: HN points). 없으면 0.
    cluster_key: str | None = None        # 6.2 클러스터 식별키. pass-through 기사는 None.
