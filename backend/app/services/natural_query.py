import re

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import BomItem, Component, Product
from app.schemas.query import NaturalQueryResponse

MANUFACTURERS = {
    "ti": "Texas Instruments",
    "德州仪器": "Texas Instruments",
    "st": "STMicroelectronics",
    "意法半导体": "STMicroelectronics",
    "nxp": "NXP",
    "英飞凌": "Infineon",
}


def natural_query(question: str, db: Session) -> NaturalQueryResponse:
    lowered = question.lower()
    manufacturer_match = next(
        ((key, value) for key, value in MANUFACTURERS.items() if key in lowered), None
    )
    manufacturer = manufacturer_match[1] if manufacturer_match else None
    part_match = re.search(r"\b[A-Z]{2,}[A-Z0-9._/-]*\d[A-Z0-9._/-]*\b", question.upper())
    part_number = part_match.group(0) if part_match else None

    conditions = []
    if manufacturer:
        alias = manufacturer_match[0] if manufacturer_match else manufacturer
        conditions.append(
            or_(
                Component.manufacturer.ilike(f"%{manufacturer}%"),
                Component.manufacturer.ilike(f"%{alias}%"),
            )
        )
    if part_number:
        conditions.append(Component.part_number.ilike(f"%{part_number}%"))
    if not conditions:
        keywords = [word for word in re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", question) if len(word) > 1]
        if keywords:
            conditions.append(
                or_(*[Component.description.ilike(f"%{word}%") for word in keywords[:5]])
            )

    rows = []
    if conditions:
        rows = db.execute(
            select(Product, Component, BomItem)
            .join(BomItem, BomItem.product_id == Product.id)
            .join(Component, Component.id == BomItem.component_id)
            .where(*conditions)
            .order_by(Product.product_code, Component.part_number)
            .limit(200)
        ).all()
    results = [
        {
            "product_code": product.product_code,
            "product_name": product.product_name,
            "part_number": component.part_number,
            "manufacturer": component.manufacturer,
            "quantity": item.quantity,
        }
        for product, component, item in rows
    ]
    return NaturalQueryResponse(
        question=question,
        interpreted_as={"manufacturer": manufacturer, "part_number": part_number},
        results=results,
        total=len(results),
        mode="structured-rules",
    )
