from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BomItem(Base):
    __tablename__ = "bom_items"
    __table_args__ = (
        UniqueConstraint("product_id", "component_id", name="uq_bom_product_component"),
        Index("ix_bom_component_product", "component_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    component_id: Mapped[int] = mapped_column(ForeignKey("components.id", ondelete="CASCADE"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    reference: Mapped[str | None] = mapped_column(String(200))
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    product: Mapped["Product"] = relationship(back_populates="bom_items")  # noqa: F821
    component: Mapped["Component"] = relationship(back_populates="bom_items")  # noqa: F821

