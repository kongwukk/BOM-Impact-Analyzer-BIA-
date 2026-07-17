from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.impact import ComponentCandidate, ImpactAnalysisResponse, ImpactResponse
from app.services.impact import analyze_impact, get_impact, search_components

router = APIRouter()


@router.get("/search", response_model=list[ComponentCandidate])
def search(q: str, db: Session = Depends(get_db)) -> list[ComponentCandidate]:
    return search_components(q, db)


@router.get("/analyze/{part_number}", response_model=ImpactAnalysisResponse)
def analyze(part_number: str, db: Session = Depends(get_db)) -> ImpactAnalysisResponse:
    return analyze_impact(part_number, db)


@router.get("/{part_number}", response_model=ImpactResponse)
def impact(part_number: str, db: Session = Depends(get_db)) -> ImpactResponse:
    return get_impact(part_number, db)
