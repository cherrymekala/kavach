from fastapi import APIRouter, HTTPException

from ..models import Insights
from ..tools import packs

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/{country}", response_model=Insights)
def get_insights(country: str) -> Insights:
    """Public: how disputes that reached the dispute body ended, by ground, insurer and year."""
    if not country.isalpha() or len(country) != 2:
        raise HTTPException(404, f"No report for {country}.")
    report = packs.insights(country)
    if not report:
        raise HTTPException(
            404, f"Not enough published rulings for a {country.upper()} report yet."
        )
    return Insights.model_validate(report)
