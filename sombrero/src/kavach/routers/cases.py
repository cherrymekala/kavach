import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from ..agents import assistant
from ..auth import current_user
from ..config import get_settings
from ..models import (
    AskAnswer,
    AskRequest,
    Case,
    CaseEvent,
    CaseSummary,
    CreateCase,
    NoteRequest,
    TitleRequest,
)
from ..tools import files, store

router = APIRouter(prefix="/cases", tags=["cases"])

_ABBREVIATIONS = {
    "co",
    "corp",
    "dept",
    "dr",
    "est",
    "etc",
    "fig",
    "govt",
    "inc",
    "jr",
    "ltd",
    "mr",
    "mrs",
    "ms",
    "no",
    "prof",
    "rs",
    "sr",
    "st",
    "vs",
}


def _auto_title(text: str) -> str:
    """Derive a short case name from the patient's first message.

    ``.`` is only treated as a sentence end when it is followed by whitespace
    and an uppercase letter (or the end of the text) and isn't a common
    abbreviation, so ``Rs. 1,000`` and ``Dr. Rao`` aren't chopped mid-word.
    """
    t = " ".join(text.split())
    for i, ch in enumerate(t):
        if ch in "?!।":
            return t[: i + 1].strip()
        if ch != ".":
            continue
        nxt = i + 1
        if nxt >= len(t):
            return t[: i + 1].strip()
        j = nxt
        while j < len(t) and t[j].isspace():
            j += 1
        if j >= len(t) or not t[j].isupper():
            continue
        start = i
        while start > 0 and (t[start - 1].isalnum() or t[start - 1] == "&"):
            start -= 1
        if t[start:i].lower() in _ABBREVIATIONS:
            continue
        return t[: i + 1].strip()
    return t[:120].rstrip()


@router.post("", response_model=Case)
def create_case(body: CreateCase, uid: str = Depends(current_user)) -> Case:
    case = Case(
        id=uuid.uuid4().hex,
        owner=uid,
        created_at=datetime.now(UTC),
        kind=body.kind,
        country=body.country,
        language=body.language,
    )
    store.save_case(case)
    return case


@router.get("", response_model=list[CaseSummary])
def list_cases(uid: str = Depends(current_user)) -> list[CaseSummary]:
    """The signed-in user's cases, newest first."""
    return [CaseSummary.of(c) for c in store.list_cases(uid)]


@router.get("/{case_id}", response_model=Case)
def get_case(case_id: str, uid: str = Depends(current_user)) -> Case:
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    return case


@router.delete("/{case_id}", status_code=204)
def delete_case(case_id: str, uid: str = Depends(current_user)) -> None:
    """Erase the case and every uploaded document (DPDP Act / PDPA: people can delete their data)."""
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    files.delete_case_files(case.id)
    store.delete_case(case.id)


@router.put("/{case_id}/title", response_model=Case)
def set_title(case_id: str, body: TitleRequest, uid: str = Depends(current_user)) -> Case:
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    title = body.title.strip()
    if not title:
        raise HTTPException(400, "Title can't be empty.")
    case.title = title
    case.title_auto = False
    store.save_case(case)
    return case


@router.post("/{case_id}/notes", response_model=Case)
def add_note(case_id: str, body: NoteRequest, uid: str = Depends(current_user)) -> Case:
    """Append the patient's own text to the case history."""
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "The note can't be empty.")
    case.events.append(CaseEvent(at=datetime.now(UTC), kind="message", text=text))
    if not case.title:
        case.title = _auto_title(text)
        case.title_auto = True
    store.save_case(case)
    return case


@router.post("/{case_id}/ask", response_model=AskAnswer)
def ask(case_id: str, body: AskRequest, uid: str = Depends(current_user)) -> AskAnswer:
    """Answer a free-text question about the case, grounded in its facts and assessment."""
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    if not case.assessment and not case.discharge_check:
        raise HTTPException(409, "Run the analysis before asking about the case.")
    question = body.question.strip()
    if not question:
        raise HTTPException(400, "Ask a question first.")
    limit = get_settings().questions_per_day
    if not store.take_quota(f"ask-{uid}-{datetime.now(UTC):%Y%m%d}", limit):
        raise HTTPException(429, f"You can ask up to {limit} questions a day.")
    answer = assistant.answer(case, question)
    now = datetime.now(UTC)
    case.events.append(CaseEvent(at=now, kind="message", text=question))
    case.events.append(CaseEvent(at=now, kind="ask", text=answer))
    if not case.title:
        case.title = _auto_title(question)
        case.title_auto = True
    store.save_case(case)
    return AskAnswer(answer=answer)
