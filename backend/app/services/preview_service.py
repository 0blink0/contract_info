from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from backend.app.config import PROJECT_ROOT
from backend.app.export.column_map import (
    FEE_DATA_START_ROW,
    FEE_HEADER_ROW,
    FEE_SHEET,
    PRODUCT_DATA_ROW,
    PRODUCT_HEADER_ROW,
    PRODUCT_SHEET,
)
from backend.app.export.column_map import template_header_for_fee_key

PREVIEW_STATUSES = frozenset({"extracted", "exporting", "exported", "export_failed"})


def _cell_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _read_xlsx_table(
    path: Path,
    sheet_name: str,
    header_row: int,
    data_start_row: int,
    *,
    max_data_rows: int = 100,
) -> tuple[list[str], list[dict[str, str | None]]]:
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        if sheet_name not in wb.sheetnames:
            return [], []
        ws = wb[sheet_name]
        headers: list[str] = []
        for col in range(1, (ws.max_column or 0) + 1):
            raw = ws.cell(row=header_row, column=col).value
            label = str(raw).strip() if raw is not None else ""
            if label:
                headers.append(label)
            else:
                headers.append(f"列{col}")

        rows: list[dict[str, str | None]] = []
        for r in range(data_start_row, data_start_row + max_data_rows):
            row_data: dict[str, str | None] = {}
            has_value = False
            for col, header in enumerate(headers, start=1):
                val = _cell_str(ws.cell(row=r, column=col).value)
                row_data[header] = val
                if val:
                    has_value = True
            if not has_value:
                break
            rows.append(row_data)
        return headers, rows
    finally:
        wb.close()


def _product_from_extraction(extraction: dict[str, Any]) -> list[dict[str, str | None]]:
    elements = extraction.get("product_elements") or {}
    rows: list[dict[str, str | None]] = []
    for field, raw in elements.items():
        if isinstance(raw, dict):
            val = raw.get("value")
        else:
            val = raw
        text = _cell_str(val)
        if text:
            rows.append({"field": field, "value": text})
    return rows


def _fee_from_extraction(extraction: dict[str, Any]) -> tuple[list[str], list[dict[str, str | None]]]:
    fee_list = extraction.get("fee_rates") or []
    if not fee_list:
        return [], []

    columns_order: list[str] = []
    seen: set[str] = set()
    for row in fee_list:
        if not isinstance(row, dict):
            continue
        for key in row:
            label = template_header_for_fee_key(key)
            if label not in seen:
                seen.add(label)
                columns_order.append(label)

    rows: list[dict[str, str | None]] = []
    for row in fee_list:
        if not isinstance(row, dict):
            continue
        mapped: dict[str, str | None] = {}
        for key, val in row.items():
            label = template_header_for_fee_key(key)
            mapped[label] = _cell_str(val)
        if any(mapped.values()):
            rows.append(mapped)
    return columns_order, rows


def build_job_preview(record) -> dict[str, Any]:
    if record.status not in PREVIEW_STATUSES:
        raise ValueError(f"Preview not available for status: {record.status}")

    source = "extraction"
    product_rows: list[dict[str, str | None]] = []
    fee_columns: list[str] = []
    fee_rows: list[dict[str, str | None]] = []

    if record.status == "exported" and record.product_xlsx_path and record.fee_xlsx_path:
        product_path = (PROJECT_ROOT / record.product_xlsx_path).resolve()
        fee_path = (PROJECT_ROOT / record.fee_xlsx_path).resolve()
        if product_path.is_file() and fee_path.is_file():
            _, product_data = _read_xlsx_table(
                product_path, PRODUCT_SHEET, PRODUCT_HEADER_ROW, PRODUCT_DATA_ROW, max_data_rows=5
            )
            if product_data:
                # 宽表转 字段/值（仅非空列）
                wide = product_data[0]
                product_rows = [
                    {"field": k, "value": v} for k, v in wide.items() if v
                ]
            fee_columns, fee_rows = _read_xlsx_table(
                fee_path, FEE_SHEET, FEE_HEADER_ROW, FEE_DATA_START_ROW
            )
            source = "xlsx"

    if not product_rows and record.extraction_result:
        product_rows = _product_from_extraction(record.extraction_result)

    if not fee_rows and record.extraction_result:
        fee_columns, fee_rows = _fee_from_extraction(record.extraction_result)

    if not product_rows and not fee_rows:
        raise ValueError("No preview data — run extract/export first")

    return {
        "job_id": record.id,
        "source": source,
        "product_rows": product_rows,
        "fee_columns": fee_columns,
        "fee_rows": fee_rows,
    }


def get_job_preview(file_id: uuid.UUID) -> dict[str, Any]:
    from backend.app.db.session import SessionLocal
    from backend.app.models.contract_file import ContractFile

    session = SessionLocal()
    try:
        record = session.get(ContractFile, file_id)
        if record is None:
            raise LookupError(f"contract_file not found: {file_id}")
        return build_job_preview(record)
    finally:
        session.close()
