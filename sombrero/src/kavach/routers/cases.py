import uuid

from fastapi import APIRouter, Depends, HTTPException

from ..auth import current_user
from ..models import Case, CreateCase
from ..tools import files, store

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=Case)
def create_case(body: CreateCase, uid: str = Depends(current_user)) -> Case:
    case = Case(id=uuid.uuid4().hex, owner=uid, country=body.country, language=body.language)
    store.save_case(case)
    return case


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
