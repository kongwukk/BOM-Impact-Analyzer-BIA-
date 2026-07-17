from datetime import datetime

from pydantic import BaseModel


class RecentProduct(BaseModel):
    product_code: str
    product_name: str
    component_count: int
    updated_at: datetime


class OverviewResponse(BaseModel):
    product_count: int
    component_count: int
    bom_item_count: int
    recent_products: list[RecentProduct]
