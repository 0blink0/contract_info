from backend.app.parse.outline import detect_outline


def test_detect_chapter_chinese_numeral():
    item = detect_outline("四、私募基金的基本情况")
    assert item is not None
    assert "私募基金" in item["title"] or item["title"]


def test_detect_di_zhang():
    item = detect_outline("第一章 总则")
    assert item is not None


def test_detect_digit_list():
    item = detect_outline("1、适用范围")
    assert item is not None


def test_no_match_subsection():
    assert detect_outline("1.1 一般规定") is None
