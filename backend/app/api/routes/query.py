from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.schemas.query import (
    LlmStatusResponse,
    NaturalQueryRequest,
    NaturalQueryResponse,
)
from app.services.natural_query import natural_query

router = APIRouter()


@router.post("/natural", response_model=NaturalQueryResponse)
def query(request: NaturalQueryRequest, db: Session = Depends(get_db)) -> NaturalQueryResponse:
    return natural_query(request.question, db)


@router.get("/status", response_model=LlmStatusResponse)
def llm_status() -> LlmStatusResponse:
    return LlmStatusResponse(
        enabled=settings.llm_enabled,
        available=settings.llm_available,
        provider=settings.llm_base_url,
        model=settings.llm_model if settings.llm_enabled else None,
    )
