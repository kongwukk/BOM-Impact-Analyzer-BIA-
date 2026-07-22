from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class NaturalQueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class QueryIntent(str, Enum):
    IMPACT = "impact"
    COMPONENT_SEARCH = "component_search"
    PRODUCT_SEARCH = "product_search"


class QueryPlan(BaseModel):
    intent: QueryIntent = QueryIntent.IMPACT
    manufacturer: Annotated[str, Field(max_length=100)] | None = None
    part_number: Annotated[str, Field(max_length=200)] | None = None
    product_code: Annotated[str, Field(max_length=100)] | None = None
    keywords: list[Annotated[str, Field(max_length=100)]] = Field(
        default_factory=list, max_length=8
    )
    lifecycle_status: Literal["Active", "NRND", "EOL"] | None = None
    critical_only: bool = False


class NaturalQueryResponse(BaseModel):
    question: str
    interpreted_as: dict[str, Any]
    results: list[dict[str, Any]]
    total: int
    mode: str
    answer: str
    warning: str | None = None


class LlmStatusResponse(BaseModel):
    enabled: bool
    available: bool
    provider: str
    model: str | None = None
