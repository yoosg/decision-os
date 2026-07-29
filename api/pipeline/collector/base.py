from abc import ABC, abstractmethod

from pipeline.models import RawArticle


class BaseCollector(ABC):
    """새 Source 추가 = 이 클래스를 상속한 어댑터 파일 추가 (AD-16).

    예외 계약(AD-5): collect()는 실패(HTTP 오류·파싱오류·타임아웃 등)를 삼키지 않고
    호출자에게 던진다. 소스 격리(한 소스 실패가 배치를 중단시키지 않음)는 aggregator가
    담당한다 — 어댑터 내부에서 예외를 억제하지 말 것.
    """

    @abstractmethod
    def collect(self) -> list[RawArticle]:
        ...
