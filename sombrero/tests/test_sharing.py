from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from kavach.auth import current_user
from kavach.main import app
from kavach.routers import sharing
from kavach.tools import store


@pytest.fixture
def as_user(monkeypatch, tmp_path):
    """Switch the signed-in user: as_user("owner") then requests run as that uid."""
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)

    def switch(uid: str) -> TestClient:
        app.dependency_overrides[current_user] = lambda: uid
        return client

    yield switch
    app.dependency_overrides.pop(current_user, None)


def _shared_case(as_user) -> tuple[str, str]:
    case_id = as_user("owner").post("/cases", json={"country": "IN"}).json()["id"]
    code = as_user("owner").post(f"/cases/{case_id}/share").json()["code"]
    return case_id, code


def test_a_helper_joins_with_a_code_and_can_work_on_the_case(as_user):
    case_id, code = _shared_case(as_user)
    assert len(code) == 9 and code[4] == "-"
    joined = as_user("helper").post(
        "/share/redeem", json={"code": code.lower(), "name": "Asha (Lotus Hospital billing)"}
    )
    assert joined.status_code == 200
    assert joined.json()["helpers"][0]["name"] == "Asha (Lotus Hospital billing)"
    assert joined.json()["events"][-1]["kind"] == "helper_added"

    helper = as_user("helper")
    assert [(c["id"], c["role"]) for c in helper.get("/cases").json()] == [(case_id, "helper")]
    assert helper.get(f"/cases/{case_id}").status_code == 200
    up = helper.post(
        f"/cases/{case_id}/documents", files={"file": ("letter.txt", b"Claim rejected.")}
    )
    assert up.status_code == 200
    # Deleting the case and managing sharing stay with the patient.
    assert helper.delete(f"/cases/{case_id}").status_code == 404
    assert helper.post(f"/cases/{case_id}/share").status_code == 404
    assert as_user("owner").get("/cases").json()[0]["role"] == "owner"


def test_codes_are_single_use_and_a_new_code_replaces_the_old(as_user):
    case_id, code = _shared_case(as_user)
    assert (
        as_user("helper").post("/share/redeem", json={"code": code, "name": "Asha"}).status_code
        == 200
    )
    assert (
        as_user("someone").post("/share/redeem", json={"code": code, "name": "X"}).status_code
        == 404
    )

    old = as_user("owner").post(f"/cases/{case_id}/share").json()["code"]
    new = as_user("owner").post(f"/cases/{case_id}/share").json()["code"]
    assert (
        as_user("other").post("/share/redeem", json={"code": old, "name": "Y"}).status_code == 404
    )
    assert (
        as_user("other").post("/share/redeem", json={"code": new, "name": "Y"}).status_code == 200
    )


def test_expired_codes_and_the_owners_own_code_are_refused(as_user):
    case_id, code = _shared_case(as_user)
    assert (
        as_user("owner").post("/share/redeem", json={"code": code, "name": "Me"}).status_code == 409
    )
    entry_hash = sharing._hash(code)
    store.save_share_code(
        entry_hash,
        {"case_id": case_id, "expires_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat()},
    )
    assert (
        as_user("helper").post("/share/redeem", json={"code": code, "name": "Asha"}).status_code
        == 404
    )


def test_removing_a_helper_ends_their_access_and_strangers_see_nothing(as_user):
    case_id, code = _shared_case(as_user)
    as_user("helper").post("/share/redeem", json={"code": code, "name": "Asha"})
    assert as_user("stranger").get(f"/cases/{case_id}").status_code == 404
    left = as_user("owner").delete(f"/cases/{case_id}/helpers/helper")
    assert left.status_code == 200 and left.json()["helper_ids"] == []
    assert as_user("helper").get(f"/cases/{case_id}").status_code == 404
    assert case_id not in [c["id"] for c in as_user("helper").get("/cases").json()]
