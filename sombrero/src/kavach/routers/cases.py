import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from ..agents import assistant
from ..auth import current_user
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


@router.post("", response_model=Case)
def create_case(body: CreateCase, uid: str = Depends(current_user)) -> Case:
    case = Case(
        id=uuid.uuid4().hex,
        owner=uid,
        created_at=datetime.now(UTC),
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
    case.title = body.title.strip()
    store.save_case(case)
    return case


@router.post("/{case_id}/notes", response_model=Case)
def add_note(case_id: str, body: NoteRequest, uid: str = Depends(current_user)) -> Case:
    """Append the patient's own text to the case history."""
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    case.events.append(CaseEvent(at=datetime.now(UTC), kind="message", text=body.text.strip()))
    store.save_case(case)
    return case


@router.post("/{case_id}/ask", response_model=AskAnswer)
def ask(case_id: str, body: AskRequest, uid: str = Depends(current_user)) -> AskAnswer:
    """Answer a free-text question about the case, grounded in its facts and assessment."""
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    if not case.assessment:
        raise HTTPException(409, "Run the analysis before asking about the case.")
    answer = assistant.answer(case, body.question.strip())
    now = datetime.now(UTC)
    case.events.append(CaseEvent(at=now, kind="message", text=body.question.strip()))
    case.events.append(CaseEvent(at=now, kind="ask", text=answer))
    store.save_case(case)
    return AskAnswer(answer=answer)
