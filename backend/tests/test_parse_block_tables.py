from backend.app.services.parse_block_tables import (
    find_best_table_for_needles,
    resolve_excerpt_table,
    table_rows_from_block_id,
)


def test_table_rows_from_block_id():
    parse_json = {
        "blocks": [
            {
                "id": "t1",
                "type": "table",
                "rows": [
                    ["", "A类", "B类"],
                    ["管理费", "1.5%", "1.2%"],
                ],
            }
        ]
    }
    rows = table_rows_from_block_id(parse_json, "t1")
    assert rows == [["", "A类", "B类"], ["管理费", "1.5%", "1.2%"]]


def test_find_best_table_for_fee_needles():
    parse_json = {
        "blocks": [
            {
                "id": "t1",
                "type": "table",
                "rows": [
                    ["项目", "A类", "B类"],
                    ["年管理费率", "1.5%", "1.2%"],
                ],
            },
            {"id": "p1", "type": "paragraph", "text": "普通段落"},
        ]
    }
    found = find_best_table_for_needles(parse_json, ["1.5%"], hints=("年管理费率",))
    assert found is not None
    assert found[1][1] == "1.5%"


def test_resolve_excerpt_table_from_row_block_id():
    parse_json = {
        "blocks": [
            {
                "id": "fee-t",
                "type": "table",
                "rows": [["运营费", "费率"], ["管理费", "1.5%"]],
            }
        ]
    }
    raw = {"block_id": "fee-t", "运营费类型": "管理费", "费率（%/年）": "1.5"}
    out = resolve_excerpt_table(raw, parse_json, section="fee-rates", value="1.5")
    assert out is not None
    assert len(out["rows"]) == 2
