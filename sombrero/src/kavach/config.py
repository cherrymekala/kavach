from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # Absent in the container; Cloud Run passes real env vars instead.
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    google_api_key: str = ""
    use_vertex: bool = False
    gcp_project: str = "kavach-510312"
    gcp_region: str = "asia-south1"
    gemini_location: str = "global"  # Gemini 3.x on Vertex is served only from global
    # Live API: no Gemini 3.x Live model yet; native audio is only served from us-central1.
    live_model: str = "gemini-live-2.5-flash-native-audio"
    live_location: str = "us-central1"
    live_voice: str = "Charon"
    model_fast: str = "gemini-3.5-flash-lite"
    model_reasoning: str = "gemini-3.8-flash"
    docs_bucket: str = "kavach-510312-docs"
    rulings_engine: str = ""  # Vertex AI Search engine + data store id, e.g. kavach-rulings
    auth_disabled: bool = False
    # Comma-separated browser origins allowed to call the API.
    cors_origins: str = (
        "http://localhost:5173,http://localhost:3000,"
        "https://kavach-510312.web.app,https://kavach-510312.firebaseapp.com"
    )
    packs_dir: str = "packs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
