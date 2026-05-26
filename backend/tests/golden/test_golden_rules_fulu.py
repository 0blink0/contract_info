"""Rule-layer golden regression for 石云福禄 (QUAL-01, QUAL-02)."""

from backend.app.extract.rules.fee_rules import extract_fee_rates
from backend.app.extract.rules.lock_rules import extract_lock_periods_rules
from backend.app.extract.rules.party_helpers import is_valid_party_name
from backend.app.extract.rules.product_rules import extract_product_rules
from backend.app.extract.section_windows import build_section_windows
from backend.tests.golden.conftest import FULU_KEY, load_contract_expected
from backend.tests.golden.helpers.normalize import contains_normalized, empty_equiv


def test_critical_parties(fulu_document):
    expected = load_contract_expected()[FULU_KEY]
    windows, _ = build_section_windows(fulu_document)
    product = extract_product_rules(fulu_document, windows)
    for field in ("管理人", "托管人"):
        exp = expected[field]
        actual = str(product[field].value).strip()
        assert actual == exp, f"{field}: expected {exp!r}, got {actual!r}"
        assert is_valid_party_name(actual)


def test_critical_product_fields(fulu_document):
    expected = load_contract_expected()[FULU_KEY]
    windows, _ = build_section_windows(fulu_document)
    product = extract_product_rules(fulu_document, windows)
    assert product.get("锁定期") is None or empty_equiv(
        getattr(product.get("锁定期"), "value", None), expected["锁定期"]
    )
    assert empty_equiv(product["预警线"].value, expected["预警线"])
    assert empty_equiv(product["止损线"].value, expected["止损线"])
    assert product["风险等级"].value == expected["风险等级"]
    assert expected["投资经理"] in str(product["投资经理"].value)
    assert contains_normalized(product["开放日规则"].value, expected["开放日规则"])


def test_critical_fee_rates_by_type(fulu_document):
    expected = load_contract_expected()[FULU_KEY]["fee_rates_by_type"]
    windows, _ = build_section_windows(fulu_document)
    product = extract_product_rules(fulu_document, windows)
    fund = str(product["基金全称"].value)
    fees = extract_fee_rates(windows["fees"], fund, fulu_document)
    for fee_type, spec in expected.items():
        rates = [
            r.rate_annual_pct
            for r in fees
            if r.运营费类型 == fee_type and r.rate_annual_pct
        ]
        assert spec["rate_annual_pct"] in rates, (
            f"{fee_type}: expected {spec['rate_annual_pct']!r} among {rates!r}"
        )


def test_lock_periods_fulu_empty(fulu_document):
    windows, _ = build_section_windows(fulu_document)
    product = extract_product_rules(fulu_document, windows)
    fund = str(product["基金全称"].value)
    locks = extract_lock_periods_rules(
        fund, product.get("锁定期"), windows.get("subscription", "")
    )
    assert locks == []
