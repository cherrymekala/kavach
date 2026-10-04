from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from kavach.agents import escalation
from kavach.config import get_settings
from kavach.main import app
from kavach.models import Case, CaseFacts, CaseStatus, FiledRequest, ReplyRequest


def _case(**facts) -> Case:
    return Case(
        id="c",
        owner="u",
        country="IN",
        status=CaseStatus.READY,
        facts=CaseFacts(claim_amount=112000, **facts),
    )


def _at(y, m, d) -> datetime:
    return datetime(y, m, d, 9, tzinfo=UTC)


def test_no_reply_moves_case_up_the_ladder_then_reminds_at_the_last_step():
    case = escalation.mark_filed(_case(), FiledRequest(filed_on=date(2026, 7, 1)), _at(2026, 7, 1))
    assert case.status == CaseStatus.FILED and case.next_deadline.date() == date(2026, 7, 16)

    assert not escalation.tick(case, _at(2026, 7, 10))  # still within 15 days
    assert escalation.tick(case, _at(2026, 7, 17))
    assert case.escalation_step == 1 and case.status == CaseStatus.ESCALATED
    assert "Bima Bharosa" in case.events[-1].text

    escalation.mark_filed(case, FiledRequest(filed_on=date(2026, 7, 18), step=2), _at(2026, 7, 18))
    assert escalation.tick(case, _at(2026, 10, 20))  # 90 days with no Ombudsman decision
    assert case.escalation_step == 2 and case.events[-1].kind == "reminder"


def test_paid_reply_resolves_and_partial_reply_escalates():
    paid = escalation.record_reply(
        _case(), ReplyRequest(outcome="paid", replied_on=date(2026, 7, 9)), _at(2026, 7, 9)
    )
    assert paid.status == CaseStatus.RESOLVED and paid.amount_recovered == 112000

    partial = escalation.record_reply(
        _case(),
        ReplyRequest(outcome="partly_paid", replied_on=date(2026, 7, 9), amount_paid=20000),
        _at(2026, 7, 9),
    )
    assert partial.escalation_step == 1 and partial.amount_recovered == 20000


def test_one_year_ombudsman_limit_warns_once():
    case = _case(rejection_date=date(2026, 1, 10))
    assert not escalation.tick(case, _at(2026, 10, 1))  # 101 days left
    assert escalation.tick(case, _at(2026, 11, 20))  # 51 days left
    assert not escalation.tick(case, _at(2026, 11, 21))
    assert [e.kind for e in case.events] == ["warning"]


def test_tick_rejects_callers_without_a_scheduler_token(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    get_settings.cache_clear()
    try:
        assert TestClient(app).post("/tracker/tick").status_code == 401
    finally:
        get_settings.cache_clear()


def test_singapore_ladder_and_fidrec_time_limit():
    case = _case(rejection_date=date(2026, 8, 14))
    case.country = "SG"
    escalation.mark_filed(case, FiledRequest(filed_on=date(2026, 8, 20)), _at(2026, 8, 20))
    assert case.next_deadline.date() == date(2026, 9, 17)  # 4 weeks for the insurer
    assert escalation.tick(case, _at(2026, 9, 18))
    assert case.escalation_step == 1 and "FIDReC" in case.events[-1].text
    assert escalation.tick(case, _at(2026, 12, 20))  # 6-month FIDReC limit approaching
    assert "FIDReC" in case.events[-1].text and case.events[-1].kind == "warning"


def test_documents_are_deleted_30_days_after_resolution(monkeypatch, tmp_path):
    from kavach.models import Document
    from kavach.tools import store

    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    try:
        (tmp_path / ".uploads" / "r1").mkdir(parents=True)
        (tmp_path / ".uploads" / "r1" / "letter.txt").write_text("rejected")
        case = _case()
        case.id, case.owner = "r1", "dev-user"
        case.documents = [Document(id="d", filename="letter.txt", gcs_uri="x")]
        escalation.record_reply(
            case, ReplyRequest(outcome="paid", replied_on=date(2026, 7, 9)), _at(2026, 7, 9)
        )
        assert not escalation.documents_due_for_deletion(case, _at(2026, 8, 7))  # 29 days
        assert escalation.documents_due_for_deletion(case, _at(2026, 8, 9))  # 31 days

        store.save_case(case)
        client = TestClient(app)
        assert client.post("/tracker/tick").json()["changed"] >= 1
        saved = store.load_case("r1")
        assert saved.documents_deleted_at and saved.events[-1].kind == "documents_deleted"
        assert not (tmp_path / ".uploads" / "r1" / "letter.txt").exists()
        assert client.post("/cases/r1/analyse").status_code == 410
    finally:
        get_settings.cache_clear()
