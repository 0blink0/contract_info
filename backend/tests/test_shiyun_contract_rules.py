"""Rule-layer extraction checks for 石云中证1000 示例合同.

完整 Critical 回归见 `tests/golden/test_golden_rules_shiyun.py`（Phase 6）。
本文件保留薄包装以免破坏已有 import。
"""

from pathlib import Path

import pytest

from backend.app.extract.rules.fee_rules import extract_fee_rates
from backend.app.extract.rules.product_rules import extract_product_rules
from backend.app.extract.section_windows import build_section_windows
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict

SHIYUN_DOCX = (
    Path(__file__).resolve().parents[2]
    / "example"
    / "石云中证1000资产进取一号私募证券投资基金-基金合同(1).docx"
)


@pytest.fixture(scope="module")
def shiyun_document():
    if not SHIYUN_DOCX.is_file():
        pytest.skip("石云示例合同不存在")
    doc = parse_docx(str(SHIYUN_DOCX))
    return document_to_dict(doc)


def test_shiyun_party_and_investment_fields(shiyun_document):
    windows, _ = build_section_windows(shiyun_document)
    product = extract_product_rules(shiyun_document, windows)

    assert product["管理人"].value == "北京石云科技有限公司"
    assert product["托管人"].value == "华福证券股份有限公司"
    cust = product["托管人"]
    assert cust.snippet
    assert cust.value in cust.snippet
    assert product.get("投资顾问") is None
    assert product["风险等级"].value == "R4"
    assert "王敏敏" in str(product["投资经理"].value)
    assert product["锁定期"].value == "180天"
    assert "第一个、第三个周三" in str(product["开放日规则"].value)
    assert product["预警线"].value == "无"
    assert product["止损线"].value == "无"
    assert "指数增强" in str(product["投资策略"].value)
    assert "力争获得投资回报" in str(product["投资目标"].value)
    assert "外包机构" in product
    assert "国泰海通" in str(product["外包机构"].value)


def test_shiyun_fee_rates(shiyun_document):
    windows, _ = build_section_windows(shiyun_document)
    product = extract_product_rules(shiyun_document, windows)
    fund = product.get("基金全称")
    name = str(fund.value) if fund and fund.value else None
    fees = extract_fee_rates(windows["fees"], name, shiyun_document)

    def _has_rate(fee_type: str, rate: str) -> bool:
        return any(
            r.运营费类型 == fee_type and r.rate_annual_pct == rate for r in fees
        )

    assert _has_rate("管理费", "1")
    assert _has_rate("托管费", "0.03")
    assert _has_rate("基金服务费", "0.01")
    assert _has_rate("销售服务费", "0.5")
