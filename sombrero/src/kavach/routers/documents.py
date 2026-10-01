import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from ..auth import current_user
from ..models import Document
from ..tools import files, store

router = APIRouter(prefix="/cases/{case_id}/documents", tags=["documents"])


@router.post("", response_model=Document)
async def upload(case_id: str, file: UploadFile, uid: str = Depends(current_user)) -> Document:
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    doc_id = uuid.uuid4().hex
    uri = files.put(f"{case_id}/{doc_id}-{file.filename}", await file.read(), file.content_type)
    doc = Document(id=doc_id, filename=file.filename or doc_id, gcs_uri=uri)
    case.documents.append(doc)
    store.save_case(case)
    return doc
