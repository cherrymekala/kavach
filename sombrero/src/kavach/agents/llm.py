"""Thin wrapper over google-genai so agents don't repeat client setup."""
import json
import mimetypes
from functools import lru_cache
from pathlib import Path

from google import genai
from google.genai import types

from ..config import get_settings


@lru_cache
def client() -> genai.Client:
    s = get_settings()
    if s.use_vertex:
        return genai.Client(vertexai=True, project=s.gcp_project, location=s.gcp_region)
    return genai.Client(api_key=s.google_api_key)


def _mime(uri: str) -> str:
    return mimetypes.guess_type(uri)[0] or "application/octet-stream"


def _file_part(uri: str) -> types.Part:
    # gs:// only resolves on Vertex; local paths (dev, evals) are sent inline.
    if uri.startswith("gs://"):
        return types.Part.from_uri(file_uri=uri, mime_type=_mime(uri))
    return types.Part.from_bytes(data=Path(uri).read_bytes(), mime_type=_mime(uri))


def _parts(uris: list[str], context: dict | None) -> list:
    parts = []
    for i, u in enumerate(uris):
        parts.append(types.Part.from_text(text=f"[File {i}: {Path(u).name}]"))
        parts.append(_file_part(u))
    if context:
        parts.append(types.Part.from_text(text=json.dumps(context, default=str)))
    return parts


def structured(system: str, uris: list[str], schema, context: dict | None = None, model: str | None = None):
    s = get_settings()
    resp = client().models.generate_content(
        model=model or s.model_reasoning,
        contents=_parts(uris, context),
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0,
        ),
    )
    return schema.model_validate_json(resp.text)


def text(system: str, context: dict) -> str:
    s = get_settings()
    resp = client().models.generate_content(
        model=s.model_fast,
        contents=[json.dumps(context, default=str)],
        config=types.GenerateContentConfig(system_instruction=system),
    )
    return resp.text
