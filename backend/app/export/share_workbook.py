from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from backend.app.export.column_map import (
    SHARE_DATA_START_ROW,
    SHARE_HEADER_ROW,
    SHARE_SHEET,
)
from backend.app.export.date_format import normalize_date_slash
from backend.app.export.xlsx_utils import build_header_index, write_cell_values

_SHARE_DATE_FIELDS = frozenset({"实际成立日期", "投资起始日"})


def _row_values(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, val in row.items():
        if val is None or str(val).strip() == "":
            continue
        if key in _SHARE_DATE_FIELDS:
            normalized = normalize_date_slash(val)
            out[key] = normalized if normalized is not None else val
        else:
            out[key] = val
    return out


def fill_share_workbook(
    template_path: Path,
    dest_path: Path,
    share_classes: list[dict[str, Any]],
) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    wb = load_workbook(template_path)
    ws = wb[SHARE_SHEET]
    header_index = build_header_index(ws, SHARE_HEADER_ROW)
    for offset, row in enumerate(share_classes):
        data = row if isinstance(row, dict) else row.model_dump()
        values = _row_values(data)
        if values:
            write_cell_values(ws, SHARE_DATA_START_ROW + offset, header_index, values)
    wb.save(dest_path)
    wb.close()
