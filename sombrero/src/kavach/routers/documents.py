import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from ..auth import current_user
from ..models import CaseStatus, Document
from ..tools import files, store

router = APIRouter(prefix="/cases/{case_id}/documents", tags=["documents"])

MAX_BYTES = 20 * 1024 * 1024
MAX_DOCUMENTS = 15
ALLOWED = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".txt"}


def safe_name(name: str | None) -> str:
    """Basename only, no path tricks, conservative characters."""
    base = Path((name or "").replace("\\", "/")).name
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", base).strip(" .")
    return base[:100] or "document"


@router.post("", response_model=Document)
async def upload(case_id: str, file: UploadFile, uid: str = Depends(current_user)) -> Document:
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    if len(case.documents) >= MAX_DOCUMENTS:
        raise HTTPException(400, f"A case can hold at most {MAX_DOCUMENTS} documents.")
    name = safe_name(file.filename)
    if Path(name).suffix.lower() not in ALLOWED:
        raise HTTPException(415, "Upload a PDF, a photo (JPG, PNG, WEBP) or a text file.")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Files must be 20 MB or smaller.")
    if not data:
        raise HTTPException(400, "The file is empty.")
    doc_id = uuid.uuid4().hex
    uri = files.put(f"{case_id}/{doc_id}-{name}", data, file.content_type)
    doc = Document(id=doc_id, filename=name, gcs_uri=uri)
    case.documents.append(doc)
    store.save_case(case)
    return doc


@router.delete("/{doc_id}", status_code=204)
def delete_document(case_id: str, doc_id: str, uid: str = Depends(current_user)) -> None:
    """Remove a wrong upload. Only before analysis, so results never cite a missing file."""
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    if case.status != CaseStatus.COLLECTING:
        raise HTTPException(409, "Documents can only be removed before the analysis starts.")
    doc = next((d for d in case.documents if d.id == doc_id), None)
    if not doc:
        raise HTTPException(404, "Document not found.")
    files.delete(doc.gcs_uri)
    case.documents = [d for d in case.documents if d.id != doc_id]
    store.save_case(case)
