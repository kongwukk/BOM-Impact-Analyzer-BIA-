from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import BomItem, Component, Product
from app.services.overview import get_overview


def test_empty_overview() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        overview = get_overview(db)

    assert overview.product_count == 0
    assert overview.component_count == 0
    assert overview.bom_item_count == 0
    assert overview.recent_products == []


def test_overview_counts_current_bom_data() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        product = Product(product_code="PRODUCT-1", product_name="测试产品")
        component = Component(part_number="灯体罩 1071*96.3*40.6MM")
        db.add(BomItem(product=product, component=component, quantity=2))
        db.commit()

        overview = get_overview(db)

    assert overview.product_count == 1
    assert overview.component_count == 1
    assert overview.bom_item_count == 1
    assert overview.recent_products[0].product_code == "PRODUCT-1"
    assert overview.recent_products[0].component_count == 1
