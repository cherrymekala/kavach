from fastapi.testclient import TestClient

from kavach.main import app


def test_healthz():
    assert TestClient(app).get("/healthz").json() == {"ok": True}


def test_create_and_get_case(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    client = TestClient(app)
    case = client.post("/cases", json={"country": "IN"}).json()
    assert client.get(f"/cases/{case['id']}").json()["country"] == "IN"
