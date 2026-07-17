import re
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
    "part_number": ["part_number", "型号", "器件型号", "part number", "mpn", "mfr part #", "元件编号"],
    "quantity": ["quantity", "数量", "qty", "用量"],
    "reference": ["reference", "位号", "ref", "designator"],
    "manufacturer": ["manufacturer", "制造商", "厂商", "品牌"],
    "description": ["description", "描述", "器件描述", "名称"],
    "is_critical": ["is_critical", "关键器件", "是否关键"],
}


def _normalized_name(value: Any) -> str:
    return re.sub(r"[\s_-]+", " ", str(value).strip().lower())


def _rename_columns(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        _normalized_name(alias): standard
        for standard, names in COLUMN_MAPPING.items()
        for alias in names
    }
    return frame.rename(columns={col: aliases.get(_normalized_name(col), col) for col in frame.columns})


def _positive_int(value: Any) -> int:
    try:
        return max(1, int(float(value))) if not pd.isna(value) else 1
    except (TypeError, ValueError):
        return 1


async def import_bom(file: UploadFile, product_code: str | None, db: Session) -> BomUploadResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".xlsx", ".xlsm"}:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "仅支持 .xlsx 或 .xlsm 文件")

    content = await file.read()
    if len(content) > settings.upload_max_mb * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "文件超过大小限制")

    try:
        frame = _rename_columns(pd.read_excel(BytesIO(content), engine="openpyxl"))
    except Exception as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Excel 解析失败: {exc}") from exc
    if "part_number" not in frame.columns:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "未识别到型号列")

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
    seen: set[str] = set()
    for _, row in frame.iterrows():
        raw_number = row.get("part_number")
        if pd.isna(raw_number) or not str(raw_number).strip():
            continue
        part_number = str(raw_number).strip().upper()
        if part_number in seen:
            skipped += 1
            continue
        seen.add(part_number)
        component = db.scalar(select(Component).where(Component.part_number == part_number))
        if component is None:
            component = Component(
                part_number=part_number,
                manufacturer=_optional_text(row.get("manufacturer")),
                description=_optional_text(row.get("description")),
            )
            db.add(component)
            db.flush()
        db.add(
            BomItem(
                product=product,
                component=component,
                quantity=_positive_int(row.get("quantity")),
                reference=_optional_text(row.get("reference")),
                is_critical=_as_bool(row.get("is_critical")),
            )
        )
        imported += 1

    db.commit()
    return BomUploadResponse(
        product_id=product.id,
        components_imported=imported,
        duplicates_skipped=skipped,
        warnings=[] if imported else ["文件中没有可导入的元器件记录"],
    )


def _optional_text(value: Any) -> str | None:
    return None if value is None or pd.isna(value) or not str(value).strip() else str(value).strip()


def _as_bool(value: Any) -> bool:
    return _normalized_name(value) in {"1", "true", "yes", "y", "是", "关键"}

