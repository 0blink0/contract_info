from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from backend.app.config import exports_dir, templates_dir
from backend.app.export.fee_workbook import fill_fee_workbook
from backend.app.export.lock_workbook import fill_lock_workbook
from backend.app.export.product_workbook import fill_product_workbook
from backend.app.export.share_workbook import fill_share_workbook
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
LOCK_OUTPUT = "lock_periods.xlsx"
SHARE_OUTPUT = "share_classes.xlsx"


def export_xlsx(
    extraction: dict[str, Any],
    file_id: uuid.UUID | str,
) -> tuple[str, str, str, str, list[dict[str, Any]]]:
    fid = str(file_id)
    out_dir = exports_dir() / fid
    out_dir.mkdir(parents=True, exist_ok=True)

    product_dest = out_dir / PRODUCT_OUTPUT
    fee_dest = out_dir / FEE_OUTPUT
    lock_dest = out_dir / LOCK_OUTPUT
    share_dest = out_dir / SHARE_OUTPUT

    tpl_root = templates_dir()
    product_tpl = tpl_root / PRODUCT_TEMPLATE
    fill_product_workbook(
        product_tpl,
        product_dest,
        extraction.get("product_elements") or {},
    )
    fill_fee_workbook(
        tpl_root / FEE_TEMPLATE,
        fee_dest,
        extraction.get("fee_rates") or [],
    )
    fill_lock_workbook(
        product_tpl,
        lock_dest,
        extraction.get("lock_periods") or [],
    )
    fill_share_workbook(
        product_tpl,
        share_dest,
        extraction.get("share_classes") or [],
    )

    new_warnings: list[ExtractionWarning] = []
    new_warnings.extend(check_product(extraction))
    new_warnings.extend(check_fees(extraction))

    rel_product = f"exports/{fid}/{PRODUCT_OUTPUT}"
    rel_fee = f"exports/{fid}/{FEE_OUTPUT}"
    rel_lock = f"exports/{fid}/{LOCK_OUTPUT}"
    rel_share = f"exports/{fid}/{SHARE_OUTPUT}"

    return rel_product, rel_fee, rel_lock, rel_share, warnings_to_list(new_warnings)
