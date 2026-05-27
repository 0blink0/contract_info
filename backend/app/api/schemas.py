from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    filename: str


class RunResponse(BaseModel):
    job_id: uuid.UUID
    status: str


class DeleteJobResponse(BaseModel):
    job_id: uuid.UUID
    deleted: bool = True


class WarningItem(BaseModel):
    field: str
    code: str
    message: str
    suggestion: str | None = None


class JobListItem(BaseModel):
    job_id: uuid.UUID
    filename: str
    status: str
    created_at: datetime


class JobListResponse(BaseModel):
    items: list[JobListItem]


class ProductPreviewItem(BaseModel):
    field: str
    value: str | None = None


class JobPreviewResponse(BaseModel):
    job_id: uuid.UUID
    source: str  # xlsx | extraction
    product_rows: list[ProductPreviewItem] = Field(default_factory=list)
    fee_columns: list[str] = Field(default_factory=list)
    fee_rows: list[dict[str, str | None]] = Field(default_factory=list)
    lock_columns: list[str] = Field(default_factory=list)
    lock_rows: list[dict[str, str | None]] = Field(default_factory=list)
    share_columns: list[str] = Field(default_factory=list)
    share_rows: list[dict[str, str | None]] = Field(default_factory=list)
    subscription_columns: list[str] = Field(default_factory=list)
    subscription_rows: list[dict[str, str | None]] = Field(default_factory=list)


class PathBResponse(BaseModel):
    job_id: uuid.UUID
    performance_fee: dict[str, Any] = Field(default_factory=dict)
    open_day: dict[str, Any] = Field(default_factory=dict)
    source_snippets: dict[str, str] = Field(default_factory=dict)


class ValidationItemResponse(BaseModel):
    field: str
    field_label: str | None = None
    status: str
    value: str | None = None
    reason: str
    suggestion: str | None = None


class ValidationResponse(BaseModel):
    job_id: uuid.UUID
    validated_at: str | None = None
    model: str | None = None
    skipped: bool = False
    items: list[ValidationItemResponse] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)


class JobDetailResponse(BaseModel):
    job_id: uuid.UUID
    filename: str
    status: str
    error_message: str | None = None
    product_xlsx_path: str | None = None
    fee_xlsx_path: str | None = None
    lock_xlsx_path: str | None = None
    share_xlsx_path: str | None = None
    subscription_xlsx_path: str | None = None
    path_b_available: bool = False
    validation_available: bool = False
    validation_fail_count: int = 0
    validation_warn_count: int = 0
    extraction_warnings: list[WarningItem] = Field(default_factory=list)
    extraction_warnings_count: int = 0
    outline_preview_count: int | None = None


def warnings_from_jsonb(raw: Any) -> list[WarningItem]:
    if not isinstance(raw, list):
        return []
    items: list[WarningItem] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        try:
            items.append(WarningItem.model_validate(entry))
        except Exception:
            continue
    return items
