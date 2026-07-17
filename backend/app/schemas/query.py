from typing import Any

from pydantic import BaseModel, Field


class NaturalQueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class NaturalQueryResponse(BaseModel):
    question: str
    interpreted_as: dict[str, Any]
    results: list[dict[str, Any]]
    total: int
    mode: str

