"""Rule-layer golden regression for 石云中证1000 (QUAL-01, QUAL-02)."""

from backend.app.extract.rules.fee_rules import extract_fee_rates
from backend.app.extract.rules.lock_rules import extract_lock_periods_rules
from backend.app.extract.rules.party_helpers import is_valid_party_name
from backend.app.extract.rules.product_rules import extract_product_rules
from backend.app.extract.section_windows import build_section_windows
from backend.tests.golden.conftest import SHIYUN_KEY, load_contract_expected
from backend.tests.golden.helpers.normalize import contains_normalized, empty_equiv, normalize_cell


def test_critical_parties(shiyun_document):
    expected = load_contract_expected()[SHIYUN_KEY]
    windows, _ = build_section_windows(shiyun_document)
    product = extract_product_rules(shiyun_document, windows)
    for field in ("管理人", "托管人", "外包机构"):
        exp = expected.get(field, "")
        fv = product.get(field)
        actual = str(fv.value).strip() if fv and fv.value else ""
        if empty_equiv(exp, actual):
            continue
        assert actual == exp, f"{field}: expected {exp!r}, got {actual!r}"
        assert is_valid_party_name(actual), f"{field} failed party validation: {actual!r}"


def test_critical_product_fields(shiyun_document):
    expected = load_contract_expected()[SHIYUN_KEY]
    windows, _ = build_section_windows(shiyun_document)
    product = extract_product_rules(shiyun_document, windows)
    assert empty_equiv(product["锁定期"].value, expected["锁定期"]) or normalize_cell(
        product["锁定期"].value
    ) == expected["锁定期"]
    assert empty_equiv(product["预警线"].value, expected["预警线"])
    assert empty_equiv(product["止损线"].value, expected["止损线"])
    assert product["风险等级"].value == expected["风险等级"]
    for part in str(expected["投资经理"]).replace("、", ",").split(","):
        part = part.strip()
        if part:
            assert part in str(product["投资经理"].value)
    assert contains_normalized(product["开放日规则"].value, expected["开放日规则"])


def test_critical_fee_rates_by_type(shiyun_document):
    expected = load_contract_expected()[SHIYUN_KEY]["fee_rates_by_type"]
    windows, _ = build_section_windows(shiyun_document)
    product = extract_product_rules(shiyun_document, windows)
    fund = str(product["基金全称"].value)
    fees = extract_fee_rates(windows["fees"], fund, shiyun_document)
    for fee_type, spec in expected.items():
        rates = [
            r.rate_annual_pct
            for r in fees
            if r.运营费类型 == fee_type and r.rate_annual_pct
        ]
        assert spec["rate_annual_pct"] in rates, (
            f"{fee_type}: expected {spec['rate_annual_pct']!r} among {rates!r}"
        )


def test_lock_periods_shiyun(shiyun_document):
    expected = load_contract_expected()[SHIYUN_KEY]
    windows, _ = build_section_windows(shiyun_document)
    product = extract_product_rules(shiyun_document, windows)
    fund = str(product["基金全称"].value)
    locks = extract_lock_periods_rules(
        fund, product.get("锁定期"), windows.get("subscription", "")
    )
    assert len(locks) >= 1
    assert any("180" in str(r.锁定时间 or "") for r in locks)
    assert expected["lock_periods"]
