from fastapi.testclient import TestClient
from src.ui.app import app

def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")
    data = response.json()
    assert data.get("status") == "ok"
    assert data.get("service") == "aegis-investigation-console"
