import pytest
from fastapi.testclient import TestClient

from kavach.agents import hearing
from kavach.config import get_settings
from kavach.main import app
from kavach.models import Assessment, Case, CaseFacts, CaseStatus
from kavach.routers.documents import MAX_BYTES, safe_name
from kavach.tools import store


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.chdir(tmp_path)  # local uploads land in a temp folder
    get_settings.cache_clear()
    yield TestClient(app)
    get_settings.cache_clear()


def _new_case(client) -> str:
    return client.post("/cases", json={"country": "IN"}).json()["id"]


def test_filenames_cannot_escape_the_upload_folder():
    assert safe_name("../../etc/passwd") == "passwd"
    assert safe_name("..\\..\\boot.ini") == "boot.ini"
    assert safe_name("rejection letter (1).pdf") == "rejection letter _1_.pdf"
    assert safe_name("") == "document"


def test_upload_rejects_bad_type_empty_and_oversized_files(client):
    case_id = _new_case(client)
    url = f"/cases/{case_id}/documents"
    assert client.post(url, files={"file": ("x.exe", b"MZ")}).status_code == 415
    assert client.post(url, files={"file": ("x.pdf", b"")}).status_code == 400
    assert client.post(url, files={"file": ("x.pdf", b"0" * (MAX_BYTES + 1))}).status_code == 413
    ok = client.post(url, files={"file": ("../letter.txt", b"claim rejected")})
    assert ok.status_code == 200 and ok.json()["filename"] == "letter.txt"


def test_delete_erases_case_and_files(client):
    case_id = _new_case(client)
    client.post(f"/cases/{case_id}/documents", files={"file": ("letter.txt", b"claim rejected")})
    assert client.delete(f"/cases/{case_id}").status_code == 204
    assert client.get(f"/cases/{case_id}").status_code == 404
    assert store.load_case(case_id) is None


def test_analysis_cannot_be_started_twice(client):
    case_id = _new_case(client)
    case = store.load_case(case_id)
    case.status = CaseStatus.ANALYSING
    store.save_case(case)
    assert client.post(f"/cases/{case_id}/analyse").status_code == 409


def test_cors_allows_the_app_origin_only(client):
    headers = {"Access-Control-Request-Method": "POST"}
    ok = client.options("/cases", headers={**headers, "Origin": "https://kavach-510312.web.app"})
    bad = client.options("/cases", headers={**headers, "Origin": "https://evil.example"})
    assert ok.headers.get("access-control-allow-origin") == "https://kavach-510312.web.app"
    assert "access-control-allow-origin" not in bad.headers


def test_hearing_prompt_leaves_out_identifying_details():
    case = Case(
        id="h",
        owner="u",
        facts=CaseFacts(
            patient_name="Lakshmi Iyer",
            policy_number="P/161100/01",
            claim_number="CLI/2026/1",
            hospital="Sri Sai Hospital",
            insurer="Star Health",
        ),
        assessment=Assessment(strength="strong", score=0.8),
    )
    text = hearing.instructions(case)
    for secret in ("Lakshmi", "P/161100/01", "CLI/2026/1", "Sri Sai"):
        assert secret not in text
    assert "Star Health" in text
