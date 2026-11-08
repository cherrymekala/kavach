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


def test_each_insurer_has_a_shareable_scorecard():
    from fastapi.testclient import TestClient

    from kavach.main import app

    c = TestClient(app)
    report = c.get("/insights/IN").json()
    slugs = [s["slug"] for s in report["insurers"]]
    assert "star-health" in slugs and "new-india-assurance" in slugs
    card = c.get("/insights/IN/insurers/star-health").json()
    assert card["key"] == "Star Health" and card["total"] >= 30
    assert all(g["total"] >= 10 and g["everyone_won_pct"] is not None for g in card["grounds"])
    assert (
        c.get("/insights/IN/insurers/reliance-general").json()["now_known_as"]
        == "IndusInd General Insurance"
    )
    assert c.get("/insights/IN/insurers/no-such-insurer").status_code == 404
