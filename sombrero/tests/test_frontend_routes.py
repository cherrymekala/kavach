import pytest
from fastapi.testclient import TestClient

from kavach.config import get_settings
from kavach.main import app
from kavach.models import Case, CaseStatus
from kavach.routers.cases import _auto_title
from kavach.tools import store


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    store._memory.clear()
    yield TestClient(app)
    get_settings.cache_clear()


def test_list_cases_returns_only_mine_newest_first(client):
    first = client.post("/cases", json={"country": "IN"}).json()["id"]
    second = client.post("/cases", json={"country": "SG", "language": "zh"}).json()["id"]
    store.save_case(Case(id="other", owner="someone-else"))
    rows = client.get("/cases").json()
    assert [r["id"] for r in rows] == [second, first]
    assert rows[0]["country"] == "SG" and rows[0]["status"] == "collecting"


def test_delete_document_only_before_analysis(client):
    case_id = client.post("/cases", json={"country": "IN"}).json()["id"]
    doc = client.post(
        f"/cases/{case_id}/documents", files={"file": ("wrong.txt", b"not my letter")}
    ).json()
    assert client.delete(f"/cases/{case_id}/documents/nope").status_code == 404
    assert client.delete(f"/cases/{case_id}/documents/{doc['id']}").status_code == 204
    assert client.get(f"/cases/{case_id}").json()["documents"] == []

    doc = client.post(
        f"/cases/{case_id}/documents", files={"file": ("letter.txt", b"rejected")}
    ).json()
    case = store.load_case(case_id)
    case.status = CaseStatus.READY
    store.save_case(case)
    assert client.delete(f"/cases/{case_id}/documents/{doc['id']}").status_code == 409


def test_pack_info_exposes_the_ladder_without_auth(client):
    sg = client.get("/packs/sg").json()
    assert sg["currency"] == "SGD" and [s["step"] for s in sg["ladder"]][-1] == "FIDReC"
    india = client.get("/packs/IN").json()
    assert len(india["ladder"]) == 3 and india["limitation"]["days"] == 365
    assert client.get("/packs/xx").status_code == 404


def test_note_auto_titles_the_case(client):
    case_id = client.post("/cases", json={"country": "IN"}).json()["id"]
    case = client.post(
        f"/cases/{case_id}/notes",
        json={"text": "My claim was rejected by Star Health."},
    ).json()
    assert case["title"] == "My claim was rejected by Star Health."
    assert case["title_auto"] is True


def test_typed_title_is_not_auto(client):
    case_id = client.post("/cases", json={"country": "IN"}).json()["id"]
    client.post(f"/cases/{case_id}/notes", json={"text": "hi"})
    case = client.put(f"/cases/{case_id}/title", json={"title": "My typed title"}).json()
    assert case["title"] == "My typed title"
    assert case["title_auto"] is False


def test_auto_title_handles_abbreviations():
    assert (
        _auto_title("Star Health rejected my claim of Rs. 1,84,000 for gallstones")
        == "Star Health rejected my claim of Rs. 1,84,000 for gallstones"
    )
    assert (
        _auto_title("Dr. Rao says my father was admitted to hospital.")
        == "Dr. Rao says my father was admitted to hospital."
    )
    assert _auto_title("My claim was rejected. The insurer said no.") == "My claim was rejected."
    assert _auto_title("Rejected! No warning given") == "Rejected!"


def test_document_records_upload_time(client):
    case_id = client.post("/cases", json={"country": "IN"}).json()["id"]
    doc = client.post(
        f"/cases/{case_id}/documents", files={"file": ("letter.txt", b"rejected")}
    ).json()
    assert doc["uploaded_at"] is not None


def test_summary_carries_last_message(client):
    case_id = client.post("/cases", json={"country": "IN"}).json()["id"]
    client.post(f"/cases/{case_id}/notes", json={"text": "hello there"})
    rows = client.get("/cases").json()
    assert rows[0]["title"] == "hello there"
    assert rows[0]["last_message"] == "hello there"
    assert rows[0]["last_message_at"] is not None
