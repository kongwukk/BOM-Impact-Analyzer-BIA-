from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.query import NaturalQueryRequest, NaturalQueryResponse
from app.services.natural_query import natural_query

router = APIRouter()


@router.post("/natural", response_model=NaturalQueryResponse)
def query(request: NaturalQueryRequest, db: Session = Depends(get_db)) -> NaturalQueryResponse:
    return natural_query(request.question, db)

