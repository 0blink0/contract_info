from types import SimpleNamespace

from backend.app.services.verification_service import (
    build_verification_rows,
    page_no_available,
)


def test_product_rows_have_labels_and_excerpt():
    record = SimpleNamespace(
        extraction_result={
            "product_elements": {
                "基金全称": {
                    "value": "测试基金",
                    "snippet": "本基金名称为测试基金，成立于2020年。",
                    "block_id": "b1",
                }
            },
        },
        parse_json={"blocks": [{"id": "b1", "text": "本基金名称为测试基金，成立于2020年。"}]},
        validation_result=None,
    )
    rows = build_verification_rows(record, "product-elements")
    assert len(rows) >= 1
    assert rows[0]["field_label"] == "基金全称"
    assert rows[0]["value"] == "测试基金"
    assert rows[0]["excerpt"]


def test_page_no_unavailable():
    record = SimpleNamespace(
        extraction_result={
            "product_elements": {"基金全称": {"value": "X"}},
        },
        parse_json={"blocks": []},
        validation_result=None,
    )
    rows = build_verification_rows(record, "product-elements")
    assert all(r["page_no"] is None for r in rows)
    assert page_no_available(rows) is False
    assert rows[0]["page_no_note"] == "页码暂未解析"


def test_rule_capture_does_not_duplicate_value_when_already_in_snippet():
    record = SimpleNamespace(
        extraction_result={
            "product_elements": {
                "首次申购起点": {
                    "value": "100万",
                    "snippet": "首次净申购金额应不低于100万元",
                    "source": "rule",
                }
            },
        },
        parse_json={},
        validation_result=None,
    )
    rows = build_verification_rows(record, "product-elements")
    row = next(r for r in rows if r["field"] == "首次申购起点")
    assert row["excerpt"] == "首次净申购金额应不低于100万元"
    assert not (row["excerpt"] or "").rstrip().endswith("100万 100万")


def test_rule_capture_prefers_full_section_body_in_excerpt():
    body = "1、权益类：股票。2、固定收益类：债券。" * 3
    record = SimpleNamespace(
        extraction_result={
            "product_elements": {
                "投资范围": {
                    "value": body,
                    "snippet": "（三）投资范围",
                    "source": "rule",
                }
            },
        },
        parse_json={},
        validation_result=None,
    )
    rows = build_verification_rows(record, "product-elements")
    scope = next(r for r in rows if r["field"] == "投资范围")
    assert scope["capture_source"] == "rule"
    assert body in (scope["excerpt"] or "")


def test_verification_falls_back_to_exported_preview_when_extraction_empty():
    record = SimpleNamespace(
        status="exported",
        extraction_result=None,
        parse_json={},
        validation_result=None,
        product_xlsx_path=None,
        fee_xlsx_path=None,
        lock_xlsx_path=None,
        share_xlsx_path=None,
        subscription_xlsx_path=None,
    )

    preview = {
        "job_id": "test",
        "source": "xlsx",
        "product_rows": [{"field": "基金全称", "value": "石云测试基金"}],
        "fee_columns": [],
        "fee_rows": [],
        "lock_columns": [],
        "lock_rows": [],
        "share_columns": [],
        "share_rows": [],
        "subscription_columns": [],
        "subscription_rows": [],
    }

    from unittest.mock import patch

    with patch(
        "backend.app.services.verification_service.build_job_preview",
        return_value=preview,
    ):
        rows = build_verification_rows(record, "product-elements")

    assert len(rows) == 1
    assert rows[0]["field_label"] == "基金全称"
    assert rows[0]["value"] == "石云测试基金"
    assert rows[0]["page_no_note"] == "页码暂未解析"


def test_fee_verification_includes_excerpt_table():
    record = SimpleNamespace(
        extraction_result={
            "fee_rates": [
                {
                    "block_id": "fee-t",
                    "运营费类型": "管理费",
                    "费率（%/年）": "1.5",
                }
            ],
        },
        parse_json={
            "blocks": [
                {
                    "id": "fee-t",
                    "type": "table",
                    "rows": [
                        ["", "A类", "B类"],
                        ["年管理费率", "1.5%", "1.2%"],
                    ],
                }
            ]
        },
        validation_result=None,
    )
    record.parse_json["blocks"].append(
        {
            "id": "p-fees",
            "type": "paragraph",
            "text": (
                "1、基金管理费\n本基金的管理费按前一日资产净值年费率1%计提。\n"
                "2、基金的托管费\n年费率0.05%。"
            ),
        }
    )

    rows = build_verification_rows(record, "fee-rates")
    assert rows
    type_row = next(r for r in rows if r.get("value") == "管理费")
    tables = type_row.get("excerpt_tables") or []
    assert tables
    assert type_row.get("excerpt")
    assert "基金管理费" in (type_row.get("excerpt") or "")


def test_validation_overlay():
    record = SimpleNamespace(
        extraction_result={
            "product_elements": {"管理人": {"value": "A公司"}},
        },
        parse_json={},
        validation_result={
            "items": [
                {
                    "field": "管理人",
                    "status": "warn",
                    "reason": "摘录较短",
                }
            ]
        },
    )
    rows = build_verification_rows(record, "product-elements")
    mgr = next(r for r in rows if r["field"] == "管理人")
    assert mgr["validation_status"] == "warn"
    assert mgr["validation_reason"] == "摘录较短"
