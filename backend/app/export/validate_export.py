from __future__ import annotations

from typing import Any

from backend.app.extract.schemas import ExtractionWarning

REQUIRED_PRODUCT = ["基金全称", "基金简称", "管理人"]
REQUIRED_FEE_PER_ROW = ["基金名称", "运营费类型", "计费频率", "费率（单位：%/年）"]


def _field_value(product_elements: dict[str, Any], key: str) -> str | None:
    raw = product_elements.get(key)
    if raw is None:
        return None
    if isinstance(raw, dict):
        val = raw.get("value")
    else:
        val = getattr(raw, "value", raw)
    if val is None or str(val).strip() == "":
        return None
    return str(val).strip()


def check_product(extraction: dict[str, Any]) -> list[ExtractionWarning]:
    warnings: list[ExtractionWarning] = []
    pe = extraction.get("product_elements") or {}
    for key in REQUIRED_PRODUCT:
        if not _field_value(pe, key):
            warnings.append(
                ExtractionWarning(
                    field=key,
                    code="export_required_missing",
                    message=f"产品要素必填列「{key}」为空",
                    suggestion="请在合同中核对或手工补录",
                )
            )
    return warnings


def check_fees(extraction: dict[str, Any]) -> list[ExtractionWarning]:
    warnings: list[ExtractionWarning] = []
    rows = extraction.get("fee_rates") or []
    if not rows:
        warnings.append(
            ExtractionWarning(
                field="fee_rates",
                code="export_required_missing",
                message="运营费率无数据行",
            )
        )
        return warnings

    for idx, row in enumerate(rows, start=1):
        data = row if isinstance(row, dict) else row.model_dump(by_alias=True)
        for key in REQUIRED_FEE_PER_ROW:
            val = data.get(key) or data.get("rate_annual_pct")
            if "费率" in key and val is None:
                val = data.get("rate_annual_pct")
            if val is None or str(val).strip() == "":
                warnings.append(
                    ExtractionWarning(
                        field=f"fee_rates[{idx}].{key}",
                        code="export_required_missing",
                        message=f"费率第 {idx} 行必填「{key}」为空",
                    )
                )
    return warnings


def merge_export_warnings(
    existing: list[dict[str, Any]] | None,
    new_warnings: list[ExtractionWarning],
) -> list[dict[str, Any]]:
    out = list(existing or [])
    for w in new_warnings:
        out.append(w.model_dump(exclude_none=True))
    return out
