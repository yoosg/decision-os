from dataclasses import dataclass
from typing import Literal

SourceType = Literal['official_blog', 'github', 'reddit', 'hn', 'youtube', 'other']


@dataclass
class RawArticle:
    technology_name: str
    title: str
    url: str
    source_type: SourceType
    content: str = ""
