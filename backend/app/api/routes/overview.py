from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.overview import OverviewResponse
from app.services.overview import get_overview

router = APIRouter()


@router.get("", response_model=OverviewResponse)
def overview(db: Session = Depends(get_db)) -> OverviewResponse:
    return get_overview(db)
