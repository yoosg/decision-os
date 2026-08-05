"""chat 엔드포인트 단위 테스트 (Story 3.4)."""
import time
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

TEST_SECRET = "test-super-secret-key-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_SIGNAL_ID = "sig-abc-111"
TEST_PROJECT_ID = "proj-xyz-222"
TEST_REPLY = "이 기술은 매우 흥미롭습니다."


def _make_token(user_id: str = TEST_USER_ID) -> str:
    payload = {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")


def _chain() -> MagicMock:
    c = MagicMock()
    for attr in ("select", "insert", "eq", "limit", "order"):
        getattr(c, attr).return_value = c
    return c


def _base_mock(
    signal_data: list | None = None,
    project_data: list | None = None,
    review_data: list | None = None,
    user_data: list | None = None,
) -> MagicMock:
    mock_client = MagicMock()

    def table_side_effect(table_name: str) -> MagicMock:
        c = _chain()
        if table_name == "signals":
            c.execute.return_value.data = signal_data if signal_data is not None else [
                {"id": TEST_SIGNAL_ID, "project_id": TEST_PROJECT_ID}
            ]
        elif table_name == "projects":
            c.execute.return_value.data = project_data if project_data is not None else [
                {"id": TEST_PROJECT_ID}
            ]
        elif table_name == "reviews":
            c.execute.return_value.data = review_data if review_data is not None else [
                {"result": {"payload": {"one_line_definition": "테스트 기술", "recommendation_reason": "추천"}}}
            ]
        elif table_name == "users":
            c.execute.return_value.data = user_data if user_data is not None else [
                {"role": "developer", "tech_stack": ["Python"]}
            ]
        return c

    mock_client.table.side_effect = table_side_effect
    return mock_client


# ─── 5.1: 정상 chat 메시지 전송 → 200 + reply 반환 ─────────────────────────────

def test_send_chat_message_returns_200_with_reply(monkeypatch):
    """정상 chat 메시지 전송 → 200 + reply 반환."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_llm = MagicMock()
    from pipeline.llm.base import LLMResponse
    mock_llm.chat.return_value = LLMResponse(content=TEST_REPLY, model="gpt-4o")

    mock_client = _base_mock()

    from routers.chat import _cached_llm_provider as get_llm_provider
    from main import app

    app.dependency_overrides[get_llm_provider] = lambda: mock_llm
    try:
        with patch("routers.chat.get_supabase", return_value=mock_client):
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/chat/messages",
                    json={"signal_id": TEST_SIGNAL_ID, "message": "이 기술은 어떤가요?"},
                    headers={"Authorization": f"Bearer {_make_token()}"},
                )
    finally:
        app.dependency_overrides.pop(get_llm_provider, None)

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["reply"] == TEST_REPLY
    assert body["error"] is None


# ─── 5.2: 다른 사용자의 signal_id로 요청 → 404 ───────────────────────────────

def test_chat_with_other_users_signal_returns_404(monkeypatch):
    """다른 사용자 소유의 signal → 404."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_llm = MagicMock()
    mock_client = _base_mock(project_data=[])

    from routers.chat import _cached_llm_provider as get_llm_provider
    from main import app

    app.dependency_overrides[get_llm_provider] = lambda: mock_llm
    try:
        with patch("routers.chat.get_supabase", return_value=mock_client):
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/chat/messages",
                    json={"signal_id": TEST_SIGNAL_ID, "message": "질문입니다."},
                    headers={"Authorization": f"Bearer {_make_token()}"},
                )
    finally:
        app.dependency_overrides.pop(get_llm_provider, None)

    assert response.status_code == 404


# ─── 5.3: 빈 메시지 전송 → 422 ────────────────────────────────────────────────

def test_chat_with_empty_message_returns_422(monkeypatch):
    """빈 메시지 전송 → 422."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_llm = MagicMock()
    mock_client = _base_mock()

    from routers.chat import _cached_llm_provider as get_llm_provider
    from main import app

    app.dependency_overrides[get_llm_provider] = lambda: mock_llm
    try:
        with patch("routers.chat.get_supabase", return_value=mock_client):
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/chat/messages",
                    json={"signal_id": TEST_SIGNAL_ID, "message": ""},
                    headers={"Authorization": f"Bearer {_make_token()}"},
                )
    finally:
        app.dependency_overrides.pop(get_llm_provider, None)

    assert response.status_code == 422


# ─── 5.4: LLMProviderError 발생 시 → 503 + error 봉투 구조 ───────────────────

def test_chat_llm_error_returns_503(monkeypatch):
    """LLMProviderError 발생 시 → 503."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_llm = MagicMock()
    from pipeline.llm.base import LLMProviderError
    mock_llm.chat.side_effect = LLMProviderError("OpenAI timeout")

    mock_client = _base_mock()

    from routers.chat import _cached_llm_provider as get_llm_provider
    from main import app

    app.dependency_overrides[get_llm_provider] = lambda: mock_llm
    try:
        with patch("routers.chat.get_supabase", return_value=mock_client):
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/chat/messages",
                    json={"signal_id": TEST_SIGNAL_ID, "message": "질문입니다."},
                    headers={"Authorization": f"Bearer {_make_token()}"},
                )
    finally:
        app.dependency_overrides.pop(get_llm_provider, None)

    assert response.status_code == 503


# ─── 5.5: completed review 없는 signal → graceful 처리 (review_payload=None) ──

def test_chat_without_completed_review_uses_null_payload(monkeypatch):
    """completed review 없는 signal → review_payload=None으로 graceful 처리."""
    import middleware.auth as auth_module
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", TEST_SECRET)

    mock_llm = MagicMock()
    from pipeline.llm.base import ChatContext, LLMResponse
    captured_context: list[ChatContext] = []

    def capture_chat(context: ChatContext) -> LLMResponse:
        captured_context.append(context)
        return LLMResponse(content=TEST_REPLY, model="gpt-4o")

    mock_llm.chat.side_effect = capture_chat
    mock_client = _base_mock(review_data=[])

    from routers.chat import _cached_llm_provider as get_llm_provider
    from main import app

    app.dependency_overrides[get_llm_provider] = lambda: mock_llm
    try:
        with patch("routers.chat.get_supabase", return_value=mock_client):
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/chat/messages",
                    json={"signal_id": TEST_SIGNAL_ID, "message": "질문입니다."},
                    headers={"Authorization": f"Bearer {_make_token()}"},
                )
    finally:
        app.dependency_overrides.pop(get_llm_provider, None)

    assert response.status_code == 200
    assert len(captured_context) == 1
    assert captured_context[0].review_payload is None
