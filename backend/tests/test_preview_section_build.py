import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.services.preview_service import (
    build_job_preview,
    build_section_preview,
)


def _exported_record(**kwargs):
    base = dict(
        id=uuid.uuid4(),
        status="exported",
        product_xlsx_path="exports/p/product.xlsx",
        fee_xlsx_path="exports/p/fee.xlsx",
        lock_xlsx_path="exports/p/lock.xlsx",
        share_xlsx_path="exports/p/share.xlsx",
        subscription_xlsx_path="exports/p/sub.xlsx",
        extraction_result={
            "product_elements": {"基金全称": {"value": "来自JSON"}},
            "fee_rates": [{"运营费类型": "管理费", "rate_annual_pct": "1"}],
            "lock_periods": [],
            "share_classes": [],
            "subscription_fees": [],
        },
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_build_section_product_only_reads_product_xlsx():
    record = _exported_record()
    with patch(
        "backend.app.services.preview_service._exported_xlsx_path",
        side_effect=lambda _r, attr: Path("/fake/product.xlsx")
        if attr == "product_xlsx_path"
        else None,
    ), patch("backend.app.services.preview_service._read_xlsx_table") as read:
        read.return_value = ([], [{"基金全称": "来自Excel"}])
        data = build_section_preview(record, "product-elements")
    assert read.call_count == 1
    assert data["section"] == "product-elements"
    assert data["product_rows"][0]["value"] == "来自Excel"
    assert "fee_rows" not in data


def test_build_section_fee_only_reads_fee_xlsx():
    record = _exported_record()
    with patch(
        "backend.app.services.preview_service._exported_xlsx_path",
        side_effect=lambda _r, attr: Path("/fake/fee.xlsx")
        if attr == "fee_xlsx_path"
        else None,
    ), patch("backend.app.services.preview_service._read_xlsx_table") as read:
        read.return_value = (["运营费类型"], [{"运营费类型": "管理费"}])
        data = build_section_preview(record, "fee-rates")
    assert read.call_count == 1
    assert data["section"] == "fee-rates"
    assert data["fee_rows"][0]["运营费类型"] == "管理费"
    assert "product_rows" not in data


def test_build_job_preview_still_loads_all_sections():
    record = _exported_record()
    paths = {
        "product_xlsx_path": Path("/fake/product.xlsx"),
        "fee_xlsx_path": Path("/fake/fee.xlsx"),
        "lock_xlsx_path": Path("/fake/lock.xlsx"),
        "share_xlsx_path": Path("/fake/share.xlsx"),
        "subscription_xlsx_path": Path("/fake/sub.xlsx"),
    }
    with patch(
        "backend.app.services.preview_service._exported_xlsx_path",
        side_effect=lambda _r, attr: paths.get(attr),
    ), patch("backend.app.services.preview_service._read_xlsx_table") as read:
        read.side_effect = [
            ([], [{"基金全称": "A"}]),
            (["运营费类型"], [{"运营费类型": "管理费"}]),
            ([], []),
            ([], []),
            ([], []),
        ]
        data = build_job_preview(record)
    assert read.call_count == 5
    assert data["product_rows"]
    assert data["fee_rows"]
