import re
from collections.abc import Callable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import BomItem, Component, Product
from app.schemas.query import NaturalQueryResponse, QueryPlan
from app.services.llm import LlmError, LlmQueryInterpreter

MANUFACTURERS = {
    "ti": "Texas Instruments",
    "德州仪器": "Texas Instruments",
    "texas instruments": "Texas Instruments",
    "st": "STMicroelectronics",
    "意法半导体": "STMicroelectronics",
    "stmicroelectronics": "STMicroelectronics",
    "nxp": "NXP",
    "英飞凌": "Infineon",
}
STOP_WORDS = {
    "哪些产品",
    "什么产品",
    "产品",
    "bom",
    "中包含",
    "包含",
    "使用",
    "影响",
    "元器件",
    "芯片",
    "器件",
    "查询",
    "所有",
}


def _has_alias(text: str, alias: str) -> bool:
    if alias.isascii() and len(alias) <= 3:
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", text))
    return alias in text


def _rule_plan(question: str) -> QueryPlan:
    lowered = question.casefold()
    manufacturer = next(
        (value for key, value in MANUFACTURERS.items() if _has_alias(lowered, key)), None
    )
    part_match = re.search(r"\b[A-Z]{2,}[A-Z0-9._/-]*\d[A-Z0-9._/-]*\b", question.upper())
    lifecycle = next(
        (
            status
            for status in ("EOL", "NRND", "Active")
            if status.casefold() in lowered
        ),
        None,
    )
    cleaned = lowered
    for phrase in sorted(STOP_WORDS, key=len, reverse=True):
        cleaned = cleaned.replace(phrase, " ")
    for alias in MANUFACTURERS:
        if alias.isascii() and len(alias) <= 3:
            cleaned = re.sub(
                rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", " ", cleaned
            )
        else:
            cleaned = cleaned.replace(alias, " ")
    cleaned = re.sub(r"(^|\s)[的和与](?=\S)", r"\1", cleaned)
    tokens = re.findall(r"[A-Za-z0-9._/-]+|[\u4e00-\u9fff]{2,}", cleaned)
    ignored = (
        set(STOP_WORDS)
        | set(MANUFACTURERS)
        | {value.casefold() for value in MANUFACTURERS.values()}
    )
    keywords = [
        token
        for token in tokens
        if token.casefold() not in ignored
        and token.casefold() not in {"eol", "nrnd", "active"}
        and (part_match is None or token.upper() != part_match.group(0))
    ]
    return QueryPlan(
        manufacturer=manufacturer,
        part_number=part_match.group(0) if part_match else None,
        keywords=list(dict.fromkeys(keywords))[:5],
        lifecycle_status=lifecycle,
        critical_only="关键" in question,
    )


def _like(value: str) -> str:
    escaped = value.replace("%", r"\%").replace("_", r"\_")
    return f"%{escaped}%"


def natural_query(
    question: str,
    db: Session,
    interpret: Callable[[str], QueryPlan] | None = None,
) -> NaturalQueryResponse:
    warning = None
    mode = "structured-rules"
    if settings.llm_available or interpret:
        try:
            plan = (interpret or LlmQueryInterpreter().interpret)(question)
            mode = "llm-structured"
        except LlmError as exc:
            plan = _rule_plan(question)
            mode = "rules-fallback"
            warning = f"{exc}，已使用本地规则完成查询。"
    else:
        plan = _rule_plan(question)

    conditions = []
    if plan.manufacturer:
        canonical = MANUFACTURERS.get(plan.manufacturer.casefold(), plan.manufacturer)
        aliases = [key for key, value in MANUFACTURERS.items() if value == canonical]
        manufacturer_matches = [
            Component.manufacturer.ilike(_like(canonical), escape="\\")
        ]
        manufacturer_matches.extend(
            Component.manufacturer.ilike(alias)
            if alias.isascii() and len(alias) <= 3
            else Component.manufacturer.ilike(_like(alias), escape="\\")
            for alias in aliases
        )
        conditions.append(or_(*manufacturer_matches))
    if plan.part_number:
        conditions.append(
            Component.part_number.ilike(_like(plan.part_number), escape="\\")
        )
    if plan.product_code:
        conditions.append(
            Product.product_code.ilike(_like(plan.product_code), escape="\\")
        )
    if plan.lifecycle_status:
        conditions.append(Component.lifecycle_status == plan.lifecycle_status)
    if plan.critical_only:
        conditions.append(BomItem.is_critical.is_(True))
    for keyword in plan.keywords[:5]:
        pattern = _like(keyword)
        conditions.append(
            or_(
                Component.description.ilike(pattern, escape="\\"),
                Component.part_number.ilike(pattern, escape="\\"),
            )
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
            "description": component.description,
            "lifecycle_status": component.lifecycle_status.value,
            "quantity": item.quantity,
            "reference": item.reference,
            "is_critical": item.is_critical,
        }
        for product, component, item in rows
    ]
    products = len({row["product_code"] for row in results})
    answer = (
        f"共找到 {len(results)} 条 BOM 记录，涉及 {products} 个产品。"
        if results
        else "当前 BOM 数据中没有找到符合条件的记录。"
    )
    return NaturalQueryResponse(
        question=question,
        interpreted_as=plan.model_dump(mode="json"),
        results=results,
        total=len(results),
        mode=mode,
        answer=answer,
        warning=warning,
    )
