from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_api_key: str = ""
    use_vertex: bool = False
    gcp_project: str = "kavach-prod"
    gcp_region: str = "asia-south1"
    model_fast: str = "gemini-2.5-flash"
    model_reasoning: str = "gemini-2.5-pro"
    docs_bucket: str = "kavach-prod-docs"
    rulings_data_store: str = ""
    auth_disabled: bool = False
    packs_dir: str = "packs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
