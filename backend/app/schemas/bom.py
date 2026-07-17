from pydantic import BaseModel, Field


class BomUploadResponse(BaseModel):
    success: bool = True
    product_id: int
    components_imported: int
    duplicates_skipped: int
    warnings: list[str] = Field(default_factory=list)


class BatchUploadResponse(BaseModel):
    total: int
    success: int
    failed: int
    failed_list: list[str]

