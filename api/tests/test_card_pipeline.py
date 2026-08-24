from unittest.mock import MagicMock

import pipeline.reviewer as reviewer
from tests.mocks import MockLLMProvider


class _Exec:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    """table(name).select/update/eq/...().execute().data 체인 흉내 + update 페이로드 캡처."""
    def __init__(self, name, data_map, captures):
        self._name = name
        self._data_map = data_map
        self._captures = captures

    def select(self, *a, **k):
        return self

    def update(self, payload):
        self._captures.append((self._name, payload))
        return self

    def insert(self, payload):
        self._captures.append((self._name, payload))
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return _Exec(self._data_map.get(self._name, []))


class _FakeClient:
    def __init__(self, data_map):
        self._data_map = data_map
        self.captures = []

    def table(self, name):
        return _FakeTable(name, self._data_map, self.captures)


def _data_map():
    return {
        "signals": [{
            "technology_name": "간단한 웹폼",
            "title": "간단한 웹폼 만들기",
            "summary": "요약",
            "signal_date": "2026-08-23",
        }],
        "signal_sources": [{"source_type": "github", "url": "https://x", "title": "예제"}],
        "projects": [{"user_id": "user-1"}],
        "user_profiles": [{"role": None, "tech_stack": [], "interests": [], "experience_level": None}],
    }


def _completed_payload(client):
    """완료 전이 update 페이로드 전체를 반환."""
    for name, payload in client.captures:
        if name == "reviews" and payload.get("status") == "completed":
            return payload
    return None


def _completed_result(client):
    p = _completed_payload(client)
    return p["result"] if p else None


def test_pipeline_stores_project_card_when_toggle_on(monkeypatch):
    monkeypatch.setattr(reviewer.settings, "beginner_card_mode_enabled", True)
    client = _FakeClient(_data_map())
    llm = MockLLMProvider()

    ok = reviewer._execute_review_pipeline(
        review_id="rev-1", signal_id="sig-1", project_id="proj-1",
        client=client, llm=llm,
    )

    assert ok is True
    completed = _completed_payload(client)
    assert completed is not None
    # 봉투(result JSON) review_type
    result = completed["result"]
    assert result["review_type"] == "project_card"
    assert "milestones" in result["payload"]
    assert "skill_label" in result["payload"]
    # 행 수준 컬럼 review_type (봉투와 일치해야 함)
    assert completed["review_type"] == "project_card"


def test_pipeline_stores_research_when_toggle_off(monkeypatch):
    monkeypatch.setattr(reviewer.settings, "beginner_card_mode_enabled", False)
    client = _FakeClient(_data_map())
    llm = MockLLMProvider()  # 기본 generate() = 13섹션 응답

    ok = reviewer._execute_review_pipeline(
        review_id="rev-2", signal_id="sig-2", project_id="proj-2",
        client=client, llm=llm,
    )

    assert ok is True
    completed = _completed_payload(client)
    assert completed is not None
    # 봉투(result JSON) review_type
    result = completed["result"]
    assert result["review_type"] == "research"
    assert "one_line_definition" in result["payload"]
    # 행 수준 컬럼 review_type (봉투와 일치해야 함)
    assert completed["review_type"] == "research"
