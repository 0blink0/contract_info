from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from backend.app.config import exports_dir, templates_dir
from backend.app.export.fee_workbook import fill_fee_workbook
from backend.app.export.product_workbook import fill_product_workbook
from backend.app.export.validate_export import (
    check_fees,
    check_product,
    merge_export_warnings,
)
from backend.app.extract.schemas import ExtractionWarning, warnings_to_list

PRODUCT_TEMPLATE = "产品要素-2.xlsx"
FEE_TEMPLATE = "产品运营费率导入模板-1.xlsx"
PRODUCT_OUTPUT = "product_elements.xlsx"
FEE_OUTPUT = "fee_rates.xlsx"


def export_xlsx(
    extraction: dict[str, Any],
    file_id: uuid.UUID | str,
) -> tuple[str, str, list[dict[str, Any]]]:
    fid = str(file_id)
    out_dir = exports_dir() / fid
    out_dir.mkdir(parents=True, exist_ok=True)

    product_dest = out_dir / PRODUCT_OUTPUT
    fee_dest = out_dir / FEE_OUTPUT

    tpl_root = templates_dir()
    fill_product_workbook(
        tpl_root / PRODUCT_TEMPLATE,
        product_dest,
        extraction.get("product_elements") or {},
    )
    fill_fee_workbook(
        tpl_root / FEE_TEMPLATE,
        fee_dest,
        extraction.get("fee_rates") or [],
    )

    new_warnings: list[ExtractionWarning] = []
    new_warnings.extend(check_product(extraction))
    new_warnings.extend(check_fees(extraction))

    rel_product = f"exports/{fid}/{PRODUCT_OUTPUT}"
    rel_fee = f"exports/{fid}/{FEE_OUTPUT}"

    return rel_product, rel_fee, warnings_to_list(new_warnings)
