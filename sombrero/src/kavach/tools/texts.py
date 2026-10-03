"""Plain text of an uploaded document, for quote verification. Images return "" (no OCR here)."""

import io
from functools import lru_cache
from pathlib import Path

from pypdf import PdfReader

from ..config import get_settings


def _bytes(uri: str) -> bytes:
    if not uri.startswith("gs://"):
        return Path(uri).read_bytes()
    from google.cloud import storage

    bucket, _, name = uri[5:].partition("/")
    return (
        storage.Client(project=get_settings().gcp_project)
        .bucket(bucket)
        .blob(name)
        .download_as_bytes()
    )


@lru_cache(maxsize=64)
def read(uri: str) -> str:
    suffix = Path(uri).suffix.lower()
    if suffix in (".txt", ".md"):
        return _bytes(uri).decode("utf-8", errors="ignore")
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(_bytes(uri)))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return ""
