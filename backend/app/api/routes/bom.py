from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.bom import BatchUploadResponse, BomUploadResponse
from app.services.bom_import import import_bom

router = APIRouter()


@router.post("/upload", response_model=BomUploadResponse)
async def upload_bom(
    file: UploadFile = File(...),
    product_code: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> BomUploadResponse:
    return await import_bom(file, product_code, db)


@router.post("/batch-upload", response_model=BatchUploadResponse)
async def batch_upload_bom(
    files: list[UploadFile] = File(...), db: Session = Depends(get_db)
) -> BatchUploadResponse:
    failed: list[str] = []
    succeeded = 0
    for file in files:
        try:
            await import_bom(file, None, db)
            succeeded += 1
        except Exception:
            db.rollback()
            failed.append(file.filename or "unnamed")
    return BatchUploadResponse(
        total=len(files), success=succeeded, failed=len(failed), failed_list=failed
    )

