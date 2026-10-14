from fastapi.testclient import TestClient

from kavach.main import app


def test_india_report_is_public_and_consistent():
    r = TestClient(app).get("/insights/in")
    assert r.status_code == 200
    report = r.json()
    o = report["overall"]
    assert o["total"] == o["allowed"] + o["partly_allowed"] + o["dismissed"] > 3000
    assert {"pre_existing", "room_rent"} <= {row["key"] for row in report["by_category"]}
    assert all(row["total"] >= 20 for row in report["by_category"])


def test_countries_without_enough_rulings_get_404():
    client = TestClient(app)
    assert client.get("/insights/SG").status_code == 404
    assert client.get("/insights/..").status_code == 404
