from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LifecycleStatus(str, Enum):
    ACTIVE = "Active"
    NRND = "NRND"
    EOL = "EOL"


class Component(Base):
    __tablename__ = "components"

    id: Mapped[int] = mapped_column(primary_key=True)
    part_number: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    manufacturer: Mapped[str | None] = mapped_column(String(100), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    lifecycle_status: Mapped[LifecycleStatus] = mapped_column(
        SqlEnum(LifecycleStatus), default=LifecycleStatus.ACTIVE
    )
    datasheet_url: Mapped[str | None] = mapped_column(String(500))
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    bom_items: Mapped[list["BomItem"]] = relationship(  # noqa: F821
        back_populates="component", cascade="all, delete-orphan"
    )

