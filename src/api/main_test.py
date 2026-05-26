from fastapi.testclient import TestClient
from src.api.main import create_app


def test_healthz():
    client = TestClient(create_app())
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_app_has_search_route():
    app = create_app()
    routes = [r.path for r in app.routes]
    assert "/api/search" in routes
