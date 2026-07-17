import re
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import BomItem, Component, Product
from app.schemas.bom import BomUploadResponse

COLUMN_MAPPING = {
    "part_number": [
        "part_number",
        "型号",
        "器件型号",
        "规格型号",
        "part number",
        "part no",
        "p/n",
        "pn",
        "mpn",
        "mfr part #",
        "物料描述",
        "元件描述",
        "规格描述",
    ],
    "material_code": [
        "元件编号",
        "物料编号",
        "物料编码",
        "物料号",
        "料号",
        "编码",
        "编号",
    ],
    "quantity": ["quantity", "数量", "qty", "用量", "单机用量", "默认数量"],
    "reference": ["reference", "位号", "ref", "designator", "元件位号"],
    "manufacturer": [
        "manufacturer",
        "制造商",
        "厂家",
        "厂商",
        "品牌",
        "推荐供应商",
        "指定供应商",
    ],
    "description": [
        "description",
        "描述",
        "器件描述",
        "名称",
        "物料名称",
        "元件名称",
        "品名",
    ],
    "is_critical": ["is_critical", "关键器件", "是否关键"],
}


def _normalized_name(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", str(value).strip().lower())


def _match_column(value: Any) -> str | None:
    """Map a slightly non-standard Excel header to a canonical field name."""
    raw_name = str(value)
    without_qualifier = re.sub(r"[（(【\[].*?[）)】\]]", "", raw_name)
    name = _normalized_name(without_qualifier)
    if not name:
        return None

    best_field: str | None = None
    best_score = 0.0
    for field, aliases in COLUMN_MAPPING.items():
        for alias in aliases:
            candidate = _normalized_name(alias)
            if name == candidate:
                return field
            # Covers “物料描述（规格）”, while not mapping “序号” to “编号”.
            if len(candidate) >= 2 and candidate in name:
                score = 0.9
            elif len(name) >= 4 and len(candidate) >= 4:
                score = SequenceMatcher(None, name, candidate).ratio()
            else:
                score = 0.0
            if score > best_score:
                best_field, best_score = field, score
    return best_field if best_score >= 0.7 else None


def _header_row(frame: pd.DataFrame) -> int | None:
    """Find a BOM header even when title/metadata rows precede it."""
    best_row: int | None = None
    best_score = -1
    for row_index in range(min(len(frame), 40)):
        matches = {_match_column(value) for value in frame.iloc[row_index].tolist()}
        matches.discard(None)
        if "part_number" not in matches:
            continue
        score = len(matches)
        if score > best_score:
            best_row, best_score = row_index, score
    return best_row


def _standardize_sheet(raw: pd.DataFrame) -> pd.DataFrame | None:
    header_row = _header_row(raw)
    if header_row is None:
        return None

    headers = raw.iloc[header_row].tolist()
    data = raw.iloc[header_row + 1 :].reset_index(drop=True)
    result = pd.DataFrame(index=data.index)
    for position, header in enumerate(headers):
        field = _match_column(header)
        if field is None:
            continue
        values = data.iloc[:, position]
        # Coalesce duplicate aliases of the same field.
        if field in result:
            result[field] = result[field].combine_first(values)
        else:
            result[field] = values
    return result.dropna(how="all")


def _read_bom_sheets(content: bytes) -> tuple[pd.DataFrame, list[str]]:
    workbook = pd.read_excel(
        BytesIO(content),
        engine="openpyxl",
        sheet_name=None,
        header=None,
        dtype=object,
    )
    frames: list[pd.DataFrame] = []
    skipped_sheets: list[str] = []
    for sheet_name, raw in workbook.items():
        frame = _standardize_sheet(raw)
        if frame is None:
            skipped_sheets.append(str(sheet_name))
            continue
        frame["_sheet_name"] = str(sheet_name)
        frames.append(frame)
    if not frames:
        return pd.DataFrame(), skipped_sheets
    return pd.concat(frames, ignore_index=True), skipped_sheets


def _positive_int(value: Any) -> int:
    try:
        return max(1, int(float(value))) if not pd.isna(value) else 1
    except (TypeError, ValueError):
        return 1


async def import_bom(
    file: UploadFile, product_code: str | None, db: Session
) -> BomUploadResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".xlsx", ".xlsm"}:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "仅支持 .xlsx 或 .xlsm 文件"
        )

    content = await file.read()
    if len(content) > settings.upload_max_mb * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "文件超过大小限制")

    try:
        frame, skipped_sheets = _read_bom_sheets(content)
    except Exception as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Excel 解析失败: {exc}"
        ) from exc
    if frame.empty or "part_number" not in frame.columns:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "所有工作表均未识别到型号/编号/料号列",
        )

    code = (product_code or Path(file.filename or "product").stem).strip()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = upload_dir / f"{re.sub(r'[^A-Za-z0-9._-]', '_', code)}{suffix}"
    stored_path.write_bytes(content)

    product = db.scalar(select(Product).where(Product.product_code == code))
    if product is None:
        product = Product(product_code=code, product_name=code)
        db.add(product)
        db.flush()
    else:
        product.bom_items.clear()
        db.flush()
    product.file_path = str(stored_path)

    imported = 0
    skipped = 0
    imported_items: dict[str, BomItem] = {}
    items_by_component_id: dict[int, BomItem] = {}
    for _, row in frame.iterrows():
        raw_number = row.get("part_number")
        if pd.isna(raw_number) or not str(raw_number).strip():
            continue
        # Printed BOMs sometimes repeat their header on every page.
        if _match_column(raw_number) == "part_number":
            continue
        part_number = str(raw_number).strip().upper()
        material_code = _optional_text(row.get("material_code"))
        material_code = material_code.upper() if material_code else None
        identity = material_code or part_number
        if identity in imported_items:
            item = imported_items[identity]
            item.quantity += _positive_int(row.get("quantity"))
            item.reference = _merge_text(
                item.reference, _optional_text(row.get("reference"))
            )
            item.is_critical = item.is_critical or _as_bool(row.get("is_critical"))
            item.component.description = _merge_text(
                item.component.description, _optional_text(row.get("description"))
            )
            if item.component.part_number != part_number:
                item.component.description = _merge_text(
                    item.component.description, part_number
                )
            skipped += 1
            continue

        component = db.scalar(select(Component).where(Component.part_number == part_number))
        legacy_component = False
        if component is None and material_code:
            component = db.scalar(
                select(Component).where(
                    Component.attributes["material_code"].as_string() == material_code
                )
            )
        if component is None and material_code:
            # Migrate records imported by the old rule, where 编号 was part_number.
            component = db.scalar(
                select(Component).where(Component.part_number == material_code)
            )
            legacy_component = component is not None
        if component is None:
            component = Component(
                part_number=part_number,
                manufacturer=_optional_text(row.get("manufacturer")),
                description=_optional_text(row.get("description")),
                attributes={"material_code": material_code} if material_code else {},
            )
            db.add(component)
            db.flush()
        else:
            if legacy_component:
                component.part_number = part_number
                component.description = _optional_text(row.get("description"))
            if component.manufacturer is None:
                component.manufacturer = _optional_text(row.get("manufacturer"))
            if not legacy_component:
                component.description = _merge_text(
                    component.description, _optional_text(row.get("description"))
                )
                if component.part_number != part_number:
                    component.description = _merge_text(
                        component.description, part_number
                    )
            if material_code:
                attributes = dict(component.attributes or {})
                attributes["material_code"] = material_code
                component.attributes = attributes

        if component.id in items_by_component_id:
            item = items_by_component_id[component.id]
            item.quantity += _positive_int(row.get("quantity"))
            item.reference = _merge_text(
                item.reference, _optional_text(row.get("reference"))
            )
            item.is_critical = item.is_critical or _as_bool(row.get("is_critical"))
            imported_items[identity] = item
            skipped += 1
            continue

        item = BomItem(
            product=product,
            component=component,
            quantity=_positive_int(row.get("quantity")),
            reference=_optional_text(row.get("reference")),
            is_critical=_as_bool(row.get("is_critical")),
        )
        db.add(item)
        imported_items[identity] = item
        items_by_component_id[component.id] = item
        imported += 1

    db.commit()
    warnings = []
    if skipped_sheets:
        warnings.append(
            f"以下工作表未找到可识别的BOM表头，已跳过：{', '.join(skipped_sheets)}"
        )
    if not imported:
        warnings.append("文件中没有可导入的元器件记录")
    return BomUploadResponse(
        product_id=product.id,
        components_imported=imported,
        duplicates_skipped=skipped,
        warnings=warnings,
    )


def _optional_text(value: Any) -> str | None:
    return None if value is None or pd.isna(value) or not str(value).strip() else str(value).strip()


def _merge_text(current: str | None, incoming: str | None) -> str | None:
    if not current:
        return incoming
    if not incoming:
        return current
    current_folded = current.casefold()
    incoming_folded = incoming.casefold()
    if incoming_folded in current_folded:
        return current
    if current_folded in incoming_folded:
        return incoming
    return f"{current}, {incoming}"


def _as_bool(value: Any) -> bool:
    return _normalized_name(value) in {"1", "true", "yes", "y", "是", "关键"}
