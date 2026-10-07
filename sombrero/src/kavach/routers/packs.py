from fastapi import APIRouter, HTTPException

from ..models import LadderStep, PackInfo
from ..tools import packs

router = APIRouter(prefix="/packs", tags=["packs"])
COUNTRIES = ("IN", "SG")


@router.get("/{country}", response_model=PackInfo)
def get_pack(country: str) -> PackInfo:
    """Public: languages, dispute ladder and time limit for a country. No case data."""
    code = country.upper()
    if code not in COUNTRIES:
        raise HTTPException(404, f"No country pack for {country}.")
    pack = packs.load(code)
    return PackInfo(
        country=code,
        currency=pack["currency"],
        languages=pack["languages"],
        regulator=pack["regulator"],
        ladder=[
            LadderStep(
                step=s["step"],
                dispute_body=s.get("dispute_body", s["step"]),
                deadline_days=s["deadline_days"],
                form=s["form"],
            )
            for s in pack["dispute_process"]
        ],
        limitation=pack.get("limitation"),
    )
