from backend.app.validate.evidence import collect_validation_candidates


def _sample_extraction():
    return {
        "product_elements": {
            "管理人": {
                "value": "海南正仁量化私募基金管理有限公司",
                "snippet": "基金管理人：海南正仁量化私募基金管理有限公司，登记为管理人。",
                "block_id": "b1",
            },
            "基金简称": {
                "value": "正仁1号",
                "snippet": "短",
            },
        },
        "fee_rates": [],
        "subscription_fees": [],
    }


def test_collect_includes_manager_with_evidence():
    parse_json = {
        "blocks": [
            {
                "id": "b1",
                "type": "paragraph",
                "text": "基金管理人：海南正仁量化私募基金管理有限公司。",
            }
        ]
    }
    candidates = collect_validation_candidates(
        _sample_extraction(), None, parse_json
    )
    fields = {c.field for c in candidates}
    assert "管理人" in fields
    mgr = next(c for c in candidates if c.field == "管理人")
    assert mgr.evidence_text
    assert mgr.party is True


def test_skips_field_without_snippet_or_block_id():
    extraction = {
        "product_elements": {
            "无证据": {"value": "x"},
        }
    }
    candidates = collect_validation_candidates(extraction, None, {})
    assert not any(c.field == "无证据" for c in candidates)


def test_path_b_source_snippets():
    path_b = {
        "open_day": {"fixed_schedule": "每月开放"},
        "source_snippets": {
            "open_day.fixed_schedule": "本基金每月开放申购赎回。",
        },
    }
    candidates = collect_validation_candidates({}, path_b, {})
    assert any(c.field == "path_b.open_day.fixed_schedule" for c in candidates)
