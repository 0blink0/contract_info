from backend.app.validate.deterministic import deterministic_validation_items


def test_stop_lines_both_none_pass():
    extraction = {
        "product_elements": {
            "预警线": {
                "value": "无",
                "snippet": "本基金不设置预警线、止损线。",
            },
            "止损线": {
                "value": "无",
                "snippet": "本基金不设置预警线、止损线。",
            },
        }
    }
    items = deterministic_validation_items(extraction)
    assert items["预警线"].status == "pass"
    assert items["止损线"].status == "pass"


def test_face_value_pass_without_explicit_rmb_word():
    extraction = {
        "product_elements": {
            "基金面值": {
                "value": "1",
                "snippet": "基金份额的初始募集面值：1.0000 元。",
            },
            "币种": {
                "value": "人民币现钞",
                "snippet": "基金份额的初始募集面值：1.0000 元。",
            },
        }
    }
    items = deterministic_validation_items(extraction)
    assert items["基金面值"].status == "pass"
    assert items["币种"].status == "pass"


def test_face_value_pass_from_basic_snippet():
    extraction = {
        "product_elements": {
            "基金面值": {
                "value": "1",
                "snippet": "基金份额的初始募集面值：人民币 1.0000 元。",
            },
            "币种": {
                "value": "人民币现钞",
                "snippet": "基金份额的初始募集面值：人民币 1.0000 元。",
            },
        }
    }
    items = deterministic_validation_items(extraction)
    assert items["基金面值"].status == "pass"
    assert items["币种"].status == "pass"
