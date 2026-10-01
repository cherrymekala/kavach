"""Similar past rulings from Vertex AI Search (vector + keyword, filtered by country)."""
from ..config import get_settings
from ..models import CaseFacts


def search_similar(facts: CaseFacts, country: str, limit: int = 12) -> list[dict]:
    s = get_settings()
    if not s.rulings_data_store:
        return []
    # TODO(week 2): discoveryengine SearchServiceClient query built from
    # facts.diagnosis + facts.rejection_reason, filter country / insurer.
    return []
