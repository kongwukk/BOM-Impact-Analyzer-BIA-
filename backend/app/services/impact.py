import re
from difflib import SequenceMatcher

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import BomItem, Component, LifecycleStatus, Product, RiskLevel
from app.schemas.impact import (
    AffectedProduct,
    ComponentCandidate,
    ImpactAnalysisResponse,
    ImpactResponse,
    RiskAssessment,
)


def _normalized_search_text(value: str | None) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", (value or "").casefold())


def _search_terms(query: str) -> list[str]:
    terms = re.findall(r"[0-9A-Za-z\u4e00-\u9fff][0-9A-Za-z\u4e00-\u9fff._/-]*", query)
    return list(dict.fromkeys(term for term in terms if len(_normalized_search_text(term)) >= 2))


def _candidate_score(component: Component, query: str, terms: list[str]) -> float:
    query_text = _normalized_search_text(query)
    number = _normalized_search_text(component.part_number)
    description = _normalized_search_text(component.description)
    manufacturer = _normalized_search_text(component.manufacturer)
    searchable = (number, description, manufacturer)

    if query_text == number:
        return 1000
    score = 0.0
    if query_text and query_text in number:
        score = 850
    elif query_text and query_text in description:
        score = 750

    normalized_terms = [_normalized_search_text(term) for term in terms]
    matched = sum(any(term in field for field in searchable) for term in normalized_terms)
    if normalized_terms:
        score = max(score, 500 * matched / len(normalized_terms))
    score += 100 * SequenceMatcher(None, query_text, number).ratio()
    return score


def search_components(query: str, db: Session, limit: int = 20) -> list[ComponentCandidate]:
    cleaned = query.strip()
    if not cleaned:
        return []

    terms = _search_terms(cleaned)
    patterns = [cleaned, *terms]
    conditions = []
    for pattern in dict.fromkeys(patterns):
        escaped = pattern.replace("%", r"\%").replace("_", r"\_")
        like = f"%{escaped}%"
        conditions.extend(
            [
                Component.part_number.ilike(like, escape="\\"),
                Component.description.ilike(like, escape="\\"),
                Component.manufacturer.ilike(like, escape="\\"),
            ]
        )
    components = db.scalars(select(Component).where(or_(*conditions)).limit(100)).all()
    ranked = sorted(
        components,
        key=lambda component: _candidate_score(component, cleaned, terms),
        reverse=True,
    )
    return [ComponentCandidate.model_validate(component) for component in ranked[:limit]]


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
