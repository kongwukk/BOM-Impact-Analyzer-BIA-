from pydantic import BaseModel, ConfigDict

from app.models.component import LifecycleStatus
from app.models.impact_analysis import RiskLevel


class AffectedProduct(BaseModel):
    product_code: str
    product_name: str
    quantity: int
    reference: str | None
    is_critical: bool

    model_config = ConfigDict(from_attributes=True)


class ImpactResponse(BaseModel):
    part_number: str
    manufacturer: str | None
    lifecycle_status: LifecycleStatus
    affected_products: list[AffectedProduct]
    total_affected: int
    risk_level: RiskLevel


class ComponentCandidate(BaseModel):
    part_number: str
    description: str | None
    manufacturer: str | None

    model_config = ConfigDict(from_attributes=True)


class RiskAssessment(BaseModel):
    level: RiskLevel
    reason: str


class ImpactAnalysisResponse(ImpactResponse):
    risk_assessment: RiskAssessment
    recommendations: list[str]
