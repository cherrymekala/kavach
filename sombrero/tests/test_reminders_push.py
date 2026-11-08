from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from kavach.agents import escalation
from kavach.main import app
from kavach.models import Case, CaseFacts, CaseStatus, FiledRequest
from kavach.routers import tracker
from kavach.tools import push, store


def _at(y, m, d) -> datetime:
    return datetime(y, m, d, 9, tzinfo=UTC)


def _filed(owner: str = "u", helpers: list[str] | None = None) -> Case:
    case = Case(
        id=f"rem-{owner}",
        owner=owner,
        country="IN",
        status=CaseStatus.READY,
        facts=CaseFacts(claim_amount=1000),
        helper_ids=helpers or [],
    )
    return escalation.mark_filed(case, FiledRequest(filed_on=date(2026, 7, 1)), _at(2026, 7, 1))


def test_days_left_reminders_fire_once_each_at_seven_and_two_days():
    case = _filed()  # reply due 16 Jul
    assert not escalation.tick(case, _at(2026, 7, 8))  # 8 days left
    assert escalation.tick(case, _at(2026, 7, 9))  # 7 days left
    assert "(7 days left)" in case.events[-1].text and case.events[-1].kind == "reminder"
    assert not escalation.tick(case, _at(2026, 7, 10))
    assert escalation.tick(case, _at(2026, 7, 15))  # 1 day left: the 2-day nudge
    assert "(1 day left)" in case.events[-1].text
    assert not escalation.tick(case, _at(2026, 7, 16))
    assert [e.kind for e in case.events] == ["filed", "reminder", "reminder"]


def test_a_late_first_tick_never_sends_the_seven_day_nudge_after_the_two_day_one():
    case = _filed()
    assert escalation.tick(case, _at(2026, 7, 15))
    assert not escalation.tick(case, _at(2026, 7, 16))
    assert sum(e.kind == "reminder" for e in case.events) == 1


@pytest.fixture
def client():
    return TestClient(app)


def test_devices_register_and_only_their_owner_can_remove_them(client, monkeypatch):
    token = "fcm-token-" + "x" * 30
    assert client.post("/push/tokens", json={"token": token}).status_code == 204
    assert store.push_tokens_for("dev-user") == [token]
    store.delete_push_token(token, uid="someone-else")
    assert store.push_tokens_for("dev-user") == [token]
    assert client.post("/push/tokens/remove", json={"token": token}).status_code == 204
    assert store.push_tokens_for("dev-user") == []


def test_push_goes_to_owner_and_helpers_and_prunes_dead_tokens(monkeypatch):
    store.save_push_token("owner-p", "owner-token-" + "a" * 30)
    store.save_push_token("helper-p", "helper-token-" + "b" * 30)
    sent = []

    def fake_send(tokens, title, body, link):
        sent.append((sorted(tokens), body, link))
        return [True if t.startswith("owner") else "gone" for t in tokens]

    monkeypatch.setattr(push, "_send", fake_send)
    case = _filed("owner-p", ["helper-p"])
    assert push.notify_case(case, "Reply due soon") == 1
    assert sent[0][1] == "Reply due soon" and sent[0][2].endswith(f"/case/{case.id}")
    assert len(sent[0][0]) == 2
    assert store.push_tokens_for("helper-p") == []  # pruned
    assert store.push_tokens_for("owner-p") != []


def test_daily_tick_pushes_the_reminder(client, monkeypatch):
    case = _filed("tick-owner")
    store.save_case(case)
    pushed = []
    monkeypatch.setattr(push, "notify_case", lambda c, text: pushed.append(text) or 1)
    monkeypatch.setattr(tracker.whatsapp, "notify_case", lambda c, text: 0)
    monkeypatch.setattr(store, "open_cases", lambda: [case])

    class Now(datetime):
        @classmethod
        def now(cls, tz=None):
            return _at(2026, 7, 9)

    monkeypatch.setattr(tracker, "datetime", Now)
    assert client.post("/tracker/tick").json()["notified"] == 1
    assert "7 days left" in pushed[0]
