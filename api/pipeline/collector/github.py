"""GitHub Releases 수집 어댑터 (Story 6.1, AD-16).

`<owner>/<repo>/releases.atom`은 Atom 피드이므로 RssCollector 파싱 로직을 그대로
재사용한다. 릴리스 제목(예: "v0.3.0")만으로는 technology_name 휴리스틱이 매치되지
않으므로 repo 이름 문맥을 함께 넣어 파생한다.
"""
from __future__ import annotations

import httpx

from pipeline.collector.rss import RssCollector, derive_tech


class GitHubReleasesCollector(RssCollector):
    """단일 GitHub repo의 releases.atom을 수집한다. source_type="github"."""

    def __init__(
        self,
        repo: str,
        client: httpx.Client,
        name: str | None = None,
        max_items: int = 5,
    ) -> None:
        self._repo = repo
        url = f"https://github.com/{repo}/releases.atom"
        super().__init__(
            name=name or f"github:{repo}",
            url=url,
            source_type="github",
            client=client,
            max_items=max_items,
        )

    def _technology_name(self, title: str, feed) -> str:
        # repo 이름을 문맥으로 더해 릴리스 태그만으로는 놓치는 기술명을 잡는다.
        return derive_tech(f"{self._repo} {title}")
