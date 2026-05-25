from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

Confidence = Literal["high", "medium", "low"]
FieldSource = Literal["rule", "llm", "manual"]


class FieldValue(BaseModel):
    value: str | float | None = None
    confidence: Confidence = "medium"
    source: FieldSource = "rule"
    block_id: str | None = None
    section_id: str | None = None
    snippet: str | None = None


class FeeRateRow(BaseModel):
    model_config = {"populate_by_name": True, "extra": "allow"}

    基金名称: str | None = None
    运营费类型: str | None = None
    计费频率: str | None = None
    计费基准: str | None = None
    rate_annual_pct: str | None = Field(None, alias="费率（%/年）")


class ExtractionMeta(BaseModel):
    model: str | None = None
    chapters_called: list[str] = Field(default_factory=list)
    truncated_windows: list[str] = Field(default_factory=list)
    extracted_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ExtractionResult(BaseModel):
    product_elements: dict[str, FieldValue] = Field(default_factory=dict)
    fee_rates: list[FeeRateRow] = Field(default_factory=list)
    meta: ExtractionMeta = Field(default_factory=ExtractionMeta, alias="_meta")

    model_config = {"populate_by_name": True}


class ExtractionWarning(BaseModel):
    field: str
    code: str
    message: str
    suggestion: str | None = None


def extraction_result_to_dict(result: ExtractionResult) -> dict[str, Any]:
    data = result.model_dump(by_alias=True, exclude_none=False)
    elements: dict[str, Any] = {}
    for key, fv in data.get("product_elements", {}).items():
        if isinstance(fv, dict):
            elements[key] = fv
        else:
            elements[key] = fv
    data["product_elements"] = elements
    data["fee_rates"] = [
        row if isinstance(row, dict) else row for row in data.get("fee_rates", [])
    ]
    return data


def warnings_to_list(warnings: list[ExtractionWarning]) -> list[dict[str, Any]]:
    return [w.model_dump(exclude_none=True) for w in warnings]
