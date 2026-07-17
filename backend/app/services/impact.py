from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BomItem, Component, LifecycleStatus, Product, RiskLevel
from app.schemas.impact import AffectedProduct, ImpactAnalysisResponse, ImpactResponse, RiskAssessment


def _load_impact(part_number: str, db: Session) -> tuple[Component, list[AffectedProduct]]:
    component = db.scalar(
        select(Component).where(Component.part_number == part_number.strip().upper())
    )
    if component is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "未找到该元器件")
    rows = db.execute(
        select(Product, BomItem)
        .join(BomItem, BomItem.product_id == Product.id)
        .where(BomItem.component_id == component.id)
        .order_by(Product.product_code)
    ).all()
    products = [
        AffectedProduct(
            product_code=product.product_code,
            product_name=product.product_name,
            quantity=item.quantity,
            reference=item.reference,
            is_critical=item.is_critical,
        )
        for product, item in rows
    ]
    return component, products


def _risk(component: Component, products: list[AffectedProduct]) -> RiskLevel:
    if not products:
        return RiskLevel.LOW
    critical = any(product.is_critical for product in products)
    if component.lifecycle_status == LifecycleStatus.EOL:
        return RiskLevel.CRITICAL if critical or len(products) >= 5 else RiskLevel.HIGH
    if component.lifecycle_status == LifecycleStatus.NRND:
        return RiskLevel.HIGH if critical else RiskLevel.MEDIUM
    return RiskLevel.MEDIUM if critical else RiskLevel.LOW


def get_impact(part_number: str, db: Session) -> ImpactResponse:
    component, products = _load_impact(part_number, db)
    return ImpactResponse(
        part_number=component.part_number,
        manufacturer=component.manufacturer,
        lifecycle_status=component.lifecycle_status,
        affected_products=products,
        total_affected=len(products),
        risk_level=_risk(component, products),
    )


def analyze_impact(part_number: str, db: Session) -> ImpactAnalysisResponse:
    impact = get_impact(part_number, db)
    reason = (
        f"{impact.part_number} 当前状态为 {impact.lifecycle_status.value}，"
        f"共影响 {impact.total_affected} 个产品。"
    )
    recommendations = ["核对元器件生命周期数据来源与更新时间"]
    if impact.lifecycle_status != LifecycleStatus.ACTIVE:
        recommendations.extend(["联系原厂确认最后采购日期（LTB）", "启动替代料兼容性评估"])
    return ImpactAnalysisResponse(
        **impact.model_dump(),
        risk_assessment=RiskAssessment(level=impact.risk_level, reason=reason),
        recommendations=recommendations,
    )

