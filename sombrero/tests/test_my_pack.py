from fastapi.testclient import TestClient

from kavach.agents import filing, hearing
from kavach.main import app
from kavach.models import Case


def test_malaysia_pack_ladder_ends_at_fmos():
    r = TestClient(app).get("/packs/MY")
    assert r.status_code == 200
    info = r.json()
    assert info["currency"] == "MYR" and info["regulator"] == "BNM"
    assert [s["step"] for s in info["ladder"]] == ["Insurer's complaints unit", "FMOS"]
    assert info["limitation"]["body"] == "FMOS"


def test_malaysian_money_and_speech_codes():
    assert filing._money(9860, "MYR") == "RM 9,860"
    case = Case(id="c", owner="u", country="MY", language="ms")
    assert hearing.speech_languages(case) == ["en-MY", "ms-MY"]
