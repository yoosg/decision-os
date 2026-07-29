import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_response_envelope():
    response = client.get("/api/v1/health")
    body = response.json()
    assert body["data"] == {"status": "ok"}
    assert body["error"] is None


def test_health_content_type_json():
    response = client.get("/api/v1/health")
    assert "application/json" in response.headers["content-type"]
