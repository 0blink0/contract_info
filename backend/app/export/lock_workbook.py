from __future__ import annotations



from pathlib import Path

from typing import Any



from openpyxl import load_workbook



from backend.app.export.column_map import LOCK_DATA_START_ROW, LOCK_HEADER_ROW, LOCK_SHEET

from backend.app.export.xlsx_utils import (
    build_header_index,
    keep_only_sheet,
    write_cell_values,
)





def _row_values(row: dict[str, Any]) -> dict[str, Any]:

    return {

        k: v

        for k, v in row.items()

        if v is not None and str(v).strip() != ""

    }





def fill_lock_workbook(

    template_path: Path,

    dest_path: Path,

    lock_periods: list[dict[str, Any]],

) -> None:

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    wb = load_workbook(template_path)

    ws = wb[LOCK_SHEET]

    header_index = build_header_index(ws, LOCK_HEADER_ROW)

    for offset, row in enumerate(lock_periods):

        data = row if isinstance(row, dict) else row.model_dump()

        values = _row_values(data)

        if values:

            write_cell_values(ws, LOCK_DATA_START_ROW + offset, header_index, values)

    keep_only_sheet(wb, LOCK_SHEET)
    wb.save(dest_path)
    wb.close()


