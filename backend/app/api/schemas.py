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


class JobDetailResponse(BaseModel):
    job_id: uuid.UUID
    filename: str
    status: str
    error_message: str | None = None
    product_xlsx_path: str | None = None
    fee_xlsx_path: str | None = None
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
