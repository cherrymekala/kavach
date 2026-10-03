from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from ..agents import filing
from ..auth import current_user
from ..models import Case, Complainant, FilingPack, Letter
from ..tools import store

router = APIRouter(prefix="/cases/{case_id}", tags=["filing"])


def _ready_case(case_id: str, uid: str) -> Case:
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    if not case.assessment:
        raise HTTPException(409, "Run the analysis first.")
    return case


@router.put("/complainant", response_model=Case)
def set_complainant(case_id: str, body: Complainant, uid: str = Depends(current_user)) -> Case:
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    case.complainant = body
    store.save_case(case)
    return case


class LetterRequest(BaseModel):
    instruction: str | None = None  # e.g. "make it firmer"


@router.post("/letter", response_model=Letter)
def redraft_letter(case_id: str, body: LetterRequest, uid: str = Depends(current_user)) -> Letter:
    case = _ready_case(case_id, uid)
    case.letter = filing.draft_letter(case, body.instruction)
    store.save_case(case)
    return case.letter


@router.get("/filing", response_model=FilingPack)
def get_filing(
    case_id: str, step: int | None = None, uid: str = Depends(current_user)
) -> FilingPack:
    return filing.filing_pack(_ready_case(case_id, uid), step)


@router.get("/filing.pdf")
def get_filing_pdf(
    case_id: str, step: int | None = None, uid: str = Depends(current_user)
) -> Response:
    case = _ready_case(case_id, uid)
    pdf = filing.render_pdf(filing.filing_pack(case, step), case)
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="kavach-filing.pdf"'},
    )


@router.get("/letter.pdf")
def get_letter_pdf(case_id: str, local: bool = False, uid: str = Depends(current_user)) -> Response:
    case = _ready_case(case_id, uid)
    if not case.letter:
        raise HTTPException(409, "No letter yet.")
    return Response(
        filing.render_letter_pdf(case.letter, local),
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="kavach-appeal-letter.pdf"'},
    )
