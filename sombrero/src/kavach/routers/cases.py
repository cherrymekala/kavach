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


def _auto_title(text: str) -> str:
    """Derive a short case name from the patient's first message."""
    t = " ".join(text.split())
    for end in (".", "?", "!", "।"):
        i = t.find(end)
        if i >= 0:
            t = t[: i + 1].strip()
            break
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
    store.save_case(case)
    return AskAnswer(answer=answer)
