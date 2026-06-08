"""TEST-01: parse → extract (golden mock LLM) → export E2E."""

import pytest

from backend.tests.golden.conftest import FULU_KEY, SHIYUN_KEY, load_contract_expected
from backend.tests.golden.helpers.pipeline_runner import run_golden_pipeline
from backend.tests.golden.helpers.xlsx_diff import (
    assert_critical_product,
    assert_export_structure,
    assert_fee_types_present,
    assert_lock_sheet,
    assert_share_sheet_extended,
    assert_subscription_rates,
)


@pytest.mark.parametrize(
    "docx_fixture,expected_key,lock_rows",
    [
        ("golden_docx_shiyun", SHIYUN_KEY, 1),
        ("golden_docx_fulu", FULU_KEY, 1),
    ],
)
def test_golden_export_e2e(
    request,
    docx_fixture,
    expected_key,
    lock_rows,
    tmp_exports,
    monkeypatch,
):
    docx_path = request.getfixturevalue(docx_fixture)
    expected = load_contract_expected()[expected_key]
    run = run_golden_pipeline(
        docx_path, exports_root=tmp_exports, monkeypatch=monkeypatch
    )
    paths = {
        "product": run.product_path,
        "fee": run.fee_path,
        "lock": run.lock_path,
        "share": run.share_path,
        "subscription": run.subscription_path,
    }
    assert_export_structure(paths)
    fund = expected["基金全称"]
    assert_critical_product(run.product_path, expected)
    assert_fee_types_present(
        run.fee_path, fund, expected.get("fee_rates_by_type", {})
    )
    assert_lock_sheet(run.lock_path, fund, expect_rows=lock_rows)
    assert_share_sheet_extended(run.share_path)
    sub_expected = expected.get("subscription_fees_by_share")
    if sub_expected:
        assert_subscription_rates(run.subscription_path, sub_expected)
