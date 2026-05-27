"""Section windows must not head-truncate chapter text used by rules."""

from pathlib import Path

import pytest

from backend.app.extract.section_windows import build_section_windows
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict

ZHENGREN = (
    Path(__file__).resolve().parents[2]
    / "example"
    / "正仁1号私募证券投资基金私募基金合同.docx"
)


@pytest.mark.parametrize("docx_path", [ZHENGREN])
def test_section_windows_not_head_truncated(docx_path: Path):
    if not docx_path.is_file():
        pytest.skip(f"missing {docx_path}")
    doc = document_to_dict(parse_docx(str(docx_path)))
    windows, truncated = build_section_windows(doc)
    assert truncated == []
    sub = windows.get("subscription", "")
    assert "365天及以上" in sub or "赎回费率为" in sub, (
        "subscription window should include late-chapter redemption tiers"
    )
