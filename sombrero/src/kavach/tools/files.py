"""Document storage in Cloud Storage. Local dev writes to ./.uploads."""

from pathlib import Path

from ..config import get_settings


def put(path: str, data: bytes, content_type: str | None) -> str:
    s = get_settings()
    if s.auth_disabled:
        dest = Path(".uploads") / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return str(dest.resolve())
    from google.cloud import storage

    blob = storage.Client(project=s.gcp_project).bucket(s.docs_bucket).blob(path)
    blob.upload_from_string(data, content_type=content_type)
    return f"gs://{s.docs_bucket}/{path}"


def delete_case_files(case_id: str) -> int:
    """Remove every uploaded document for a case. Returns how many were deleted."""
    s = get_settings()
    if s.auth_disabled:
        folder = Path(".uploads") / case_id
        removed = [f.unlink() for f in folder.glob("*") if f.is_file()] if folder.exists() else []
        return len(removed)
    from google.cloud import storage

    blobs = list(
        storage.Client(project=s.gcp_project).bucket(s.docs_bucket).list_blobs(prefix=f"{case_id}/")
    )
    for blob in blobs:
        blob.delete()
    return len(blobs)
