from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import BomItem, Component, Product
from app.schemas.query import QueryPlan
from app.services.llm import _json_object
from app.services.natural_query import _rule_plan, natural_query


def test_llm_json_parser_accepts_fenced_object() -> None:
    assert _json_object('```json\n{"manufacturer": "Texas Instruments"}\n```') == {
        "manufacturer": "Texas Instruments"
    }


def test_rule_plan_extracts_part_number_and_manufacturer() -> None:
    plan = _rule_plan("STM32F103C8T6 影响哪些产品？")
    assert plan.part_number == "STM32F103C8T6"

    manufacturer_plan = _rule_plan("哪些产品使用了 TI 的电源管理芯片？")
    assert manufacturer_plan.manufacturer == "Texas Instruments"
    assert "电源管理" in "".join(manufacturer_plan.keywords)

    assert _rule_plan("查询 Active status").manufacturer is None


def test_structured_plan_is_executed_by_orm() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        product = Product(product_code="PSU-1", product_name="电源")
        component = Component(
            part_number="TPS5430",
            manufacturer="Texas Instruments",
            description="降压电源管理芯片",
        )
        db.add(BomItem(product=product, component=component, quantity=2))
        db.commit()

        response = natural_query(
            "哪些产品使用 TI 电源芯片？",
            db,
            interpret=lambda _: QueryPlan(
                manufacturer="Texas Instruments", keywords=["电源"]
            ),
        )

    assert response.mode == "llm-structured"
    assert response.total == 1
    assert response.results[0]["product_code"] == "PSU-1"
    assert response.answer == "共找到 1 条 BOM 记录，涉及 1 个产品。"
