from fastapi.testclient import TestClient

from app.api.v1 import health as health_module
from app.main import app
from app.schemas.health import HealthResponse


def test_health_returns_ok_when_dependencies_are_available(monkeypatch):
    async def healthy_dependencies():
        return HealthResponse(status="ok", postgres="ok", qdrant="ok"), 200

    monkeypatch.setattr(health_module, "get_health_status", healthy_dependencies)

    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "candidate-recruiter-matching",
        "postgres": "ok",
        "qdrant": "ok",
    }


def test_health_returns_503_when_a_dependency_is_unavailable(monkeypatch):
    async def unavailable_qdrant():
        return (
            HealthResponse(
                status="error",
                postgres="ok",
                qdrant="error",
                detail="qdrant: Connection refused",
            ),
            503,
        )

    monkeypatch.setattr(health_module, "get_health_status", unavailable_qdrant)

    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json()["qdrant"] == "error"
    assert response.json()["detail"] == "qdrant: Connection refused"
