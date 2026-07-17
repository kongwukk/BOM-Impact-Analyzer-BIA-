from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    product_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(String(500))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    bom_items: Mapped[list["BomItem"]] = relationship(  # noqa: F821
        back_populates="product", cascade="all, delete-orphan"
    )

