from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ImpactAnalysis(Base):
    __tablename__ = "impact_analysis"

    id: Mapped[int] = mapped_column(primary_key=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("components.id", ondelete="CASCADE"))
    affected_product_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    risk_level: Mapped[RiskLevel] = mapped_column(SqlEnum(RiskLevel), default=RiskLevel.LOW)
    reason: Mapped[str | None] = mapped_column(Text)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

