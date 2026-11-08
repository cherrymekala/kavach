from fastapi import APIRouter, HTTPException

from ..models import Insights, InsurerScorecard
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


@router.get("/{country}/insurers/{slug}", response_model=InsurerScorecard)
def get_scorecard(country: str, slug: str) -> InsurerScorecard:
    """Public: one insurer's scorecard (shareable link)."""
    report = get_insights(country)
    card = next((c for c in report.insurers if c.slug == slug), None)
    if not card:
        raise HTTPException(404, "No scorecard for that insurer: too few published awards.")
    return card
