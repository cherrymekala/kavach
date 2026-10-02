"""Similar past rulings from Vertex AI Search (semantic + keyword, filtered by metadata)."""
from functools import lru_cache

from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import InvalidArgument
from google.cloud import discoveryengine_v1 as de

from ..config import get_settings
from ..models import CaseFacts


@lru_cache
def _client() -> de.SearchServiceClient:
    return de.SearchServiceClient(client_options=ClientOptions(quota_project_id=get_settings().gcp_project))


def _query(facts: CaseFacts) -> str:
    category = facts.rejection_category.replace("_", " ") if facts.rejection_category else None
    parts = [category, facts.rejection_reason, facts.diagnosis, facts.cited_clause]
    return " ".join(p for p in parts if p) or "health insurance claim rejection"


def search_similar(facts: CaseFacts, country: str, limit: int = 12) -> list[dict]:
    s = get_settings()
    if not s.rulings_engine:
        return []
    filters = [f'country: ANY("{country.upper()}")']
    if facts.rejection_category:
        filters.append(f'category: ANY("{facts.rejection_category}")')
    serving_config = (
        f"projects/{s.gcp_project}/locations/global/collections/default_collection"
        f"/engines/{s.rulings_engine}/servingConfigs/default_search"
    )
    request = de.SearchRequest(
        serving_config=serving_config, query=_query(facts), filter=" AND ".join(filters), page_size=limit
    )
    try:
        resp = _client().search(request=request)
        return [{"id": r.document.id, **dict(r.document.struct_data)} for r in resp.results]
    except InvalidArgument:
        # Filterable fields only work once Vertex AI Search finishes reindexing after a schema change.
        request.filter, request.page_size = "", 50
        hits = [{"id": r.document.id, **dict(r.document.struct_data)} for r in _client().search(request=request).results]
        hits = [h for h in hits if h.get("country") == country.upper()]
        if facts.rejection_category:
            hits = [h for h in hits if h.get("category") == facts.rejection_category]
        return hits[:limit]
