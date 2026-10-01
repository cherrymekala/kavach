"""Thin wrapper over google-genai so agents don't repeat client setup."""
import json
from functools import lru_cache

from google import genai
from google.genai import types

from ..config import get_settings


@lru_cache
def client() -> genai.Client:
    s = get_settings()
    if s.use_vertex:
        return genai.Client(vertexai=True, project=s.gcp_project, location=s.gcp_region)
    return genai.Client(api_key=s.google_api_key)


def _parts(uris: list[str], context: dict | None) -> list:
    parts = [types.Part.from_uri(file_uri=u, mime_type=_mime(u)) for u in uris]
    if context:
        parts.append(types.Part.from_text(text=json.dumps(context, default=str)))
    return parts


def _mime(uri: str) -> str:
    return "application/pdf" if uri.lower().endswith(".pdf") else "image/jpeg"


def structured(system: str, uris: list[str], schema, context: dict | None = None):
    s = get_settings()
    resp = client().models.generate_content(
        model=s.model_reasoning,
        contents=_parts(uris, context),
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
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
