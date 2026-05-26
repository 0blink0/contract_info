from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

ValidationStatus = Literal["pass", "warn", "fail"]


class ValidationCandidate(BaseModel):
    field: str
    value: str
    evidence_text: str
    party: bool = False


class ValidationItem(BaseModel):
    field: str
    status: ValidationStatus
    value: str | None = None
    reason: str
    suggestion: str | None = None


class ValidationBatchItem(BaseModel):
    field: str
    status: ValidationStatus
    reason: str
    suggestion: str | None = None


class ValidationBatchResponse(BaseModel):
    items: list[ValidationBatchItem] = Field(default_factory=list)


class ValidationResult(BaseModel):
    validated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    model: str | None = None
    skipped: bool = False
    items: list[ValidationItem] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)

    def compute_summary(self) -> dict[str, int]:
        counts = {"pass": 0, "warn": 0, "fail": 0}
        for item in self.items:
            counts[item.status] = counts.get(item.status, 0) + 1
        self.summary = counts
        return counts
