from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from backend.app.export.column_map import (
    PRODUCT_DATA_ROW,
    PRODUCT_DATE_FIELDS,
    PRODUCT_HEADER_ROW,
    PRODUCT_SHEET,
)
from backend.app.export.date_format import normalize_date_slash
from backend.app.export.xlsx_utils import (
    build_header_index,
    clear_data_rows,
    keep_only_sheet,
    write_cell_values,
)

_CLOSED_PERIOD_FIELDS = frozenset(
    {"封闭期", "封闭方式", "封闭期起始日", "运作方式"}
)


def _field_raw_value(raw: Any) -> Any:
    if isinstance(raw, dict):
        return raw.get("value")
    return getattr(raw, "value", raw)


def _product_field_values(product_elements: dict[str, Any]) -> dict[str, Any]:
    skip_closed = _field_raw_value(product_elements.get("是否封闭")) == "不封闭"
    out: dict[str, Any] = {}
    for key, raw in product_elements.items():
        if skip_closed and key in _CLOSED_PERIOD_FIELDS:
            continue
        if isinstance(raw, dict):
            val = raw.get("value")
        else:
            val = getattr(raw, "value", raw)
        if val is None or str(val).strip() == "":
            continue
        if key in PRODUCT_DATE_FIELDS:
            normalized = normalize_date_slash(val)
            out[key] = normalized if normalized is not None else val
        else:
            out[key] = val
    return out


def fill_product_workbook(
    template_path: Path,
    dest_path: Path,
    product_elements: dict[str, Any],
) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    wb = load_workbook(template_path)
    ws = wb[PRODUCT_SHEET]
    header_index = build_header_index(ws, PRODUCT_HEADER_ROW)
    clear_data_rows(ws, PRODUCT_DATA_ROW)
    values = _product_field_values(product_elements)
    write_cell_values(ws, PRODUCT_DATA_ROW, header_index, values)
    keep_only_sheet(wb, PRODUCT_SHEET)
    wb.save(dest_path)
    wb.close()
