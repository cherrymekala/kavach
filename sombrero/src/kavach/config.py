from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # Absent in the container; Cloud Run passes real env vars instead.
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    google_api_key: str = ""
    use_vertex: bool = False
    gcp_project: str = "kavach-prod"
    gcp_region: str = "asia-south1"
    gemini_location: str = "global"  # Gemini 3.x on Vertex is served only from global
    model_fast: str = "gemini-2.5-flash"
    model_reasoning: str = "gemini-2.5-pro"
    docs_bucket: str = "kavach-prod-docs"
    rulings_engine: str = ""  # Vertex AI Search engine + data store id, e.g. kavach-rulings
    auth_disabled: bool = False
    packs_dir: str = "packs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
