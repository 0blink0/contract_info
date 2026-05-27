from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

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
    evidence_text: str | None = None
    reason: str
    suggestion: str | None = None


class ValidationBatchItem(BaseModel):
    field: str
    status: ValidationStatus
    reason: str = ""
    suggestion: str | None = None

    @field_validator("field", mode="before")
    @classmethod
    def _field_str(cls, v: object) -> str:
        return str(v or "").strip()

    @field_validator("reason", mode="before")
    @classmethod
    def _reason_str(cls, v: object) -> str:
        if v is None:
            return "（模型未返回原因）"
        text = str(v).strip()
        return text or "（模型未返回原因）"

    @field_validator("status", mode="before")
    @classmethod
    def _status_literal(cls, v: object) -> str:
        if v is None:
            return "warn"
        s = str(v).lower().strip()
        if s in ("pass", "warn", "fail"):
            return s
        return "warn"


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
