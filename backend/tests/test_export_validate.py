from backend.app.export.validate_export import check_fees, check_product


def test_check_product_empty():
    warnings = check_product({"product_elements": {}, "fee_rates": []})
    assert any(w.code == "export_required_missing" for w in warnings)


def test_check_fees_missing_rate():
    warnings = check_fees(
        {
            "fee_rates": [
                {"基金名称": "X", "运营费类型": "管理费", "计费频率": "按年"}
            ]
        }
    )
    assert any("费率" in w.field for w in warnings)
