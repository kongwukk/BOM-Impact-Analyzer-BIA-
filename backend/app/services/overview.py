from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.models import BomItem, Product
from app.schemas.overview import OverviewResponse, RecentProduct


def get_overview(db: Session) -> OverviewResponse:
    product_count = db.scalar(select(func.count(distinct(BomItem.product_id)))) or 0
    component_count = (
        db.scalar(select(func.count(distinct(BomItem.component_id)))) or 0
    )
    bom_item_count = db.scalar(select(func.count(BomItem.id))) or 0

    recent_rows = db.execute(
        select(Product, func.count(BomItem.id).label("component_count"))
        .join(BomItem, BomItem.product_id == Product.id)
        .group_by(Product.id)
        .order_by(Product.updated_at.desc())
        .limit(5)
    ).all()
    recent_products = [
        RecentProduct(
            product_code=product.product_code,
            product_name=product.product_name,
            component_count=component_count,
            updated_at=product.updated_at,
        )
        for product, component_count in recent_rows
    ]
    return OverviewResponse(
        product_count=product_count,
        component_count=component_count,
        bom_item_count=bom_item_count,
        recent_products=recent_products,
    )
