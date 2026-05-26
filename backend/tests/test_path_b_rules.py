"""路径 B 规则抽取（无 LLM）。"""

from pathlib import Path

import pytest

from backend.app.extract.pipeline import extract_document_sync
from backend.app.extract.rules.path_b_rules import extract_path_b_rules
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict
from backend.app.extract.section_windows import build_section_windows
from backend.app.extract.rules.product_rules import extract_product_rules
from backend.tests.golden.conftest import FULU_KEY, SHIYUN_KEY, load_contract_expected

EXAMPLE = Path(__file__).resolve().parents[2] / "example"


class LlmOff:
    available = False
    model_name = ""


def _run_path_b(docx_name: str):
    path = EXAMPLE / docx_name
    if not path.is_file():
        pytest.skip(f"missing {path}")
    doc = document_to_dict(parse_docx(str(path)))
    windows, _ = build_section_windows(doc)
    product = extract_product_rules(doc, windows)
    fund_name = str(product["基金全称"].value) if product.get("基金全称") else None
    path_b, warnings = extract_path_b_rules(
        doc, windows, fund_name=fund_name, product_elements=product
    )
    return path_b, warnings, product


@pytest.mark.parametrize("docx_key", [SHIYUN_KEY, FULU_KEY])
def test_path_b_structure(docx_key):
    path_b, _, _ = _run_path_b(docx_key)
    assert path_b.get("performance_fee")
    assert path_b.get("open_day")
    assert path_b.get("source_snippets")


@pytest.mark.parametrize("docx_key", [SHIYUN_KEY, FULU_KEY])
def test_open_day_schedule_matches_expected(docx_key):
    expected = load_contract_expected()[docx_key]
    path_b, _, product = _run_path_b(docx_key)
    spec = expected.get("path_b", {})
    schedule_contains = spec.get("open_day", {}).get("fixed_schedule_contains")
    if not schedule_contains:
        pytest.skip("no path_b open_day expected")
    fixed = (path_b.get("open_day") or {}).get("fixed_schedule") or ""
    product_schedule = ""
    if product.get("开放日规则"):
        product_schedule = str(product["开放日规则"].value or "")
    assert schedule_contains in fixed or schedule_contains in product_schedule


def test_performance_fee_tiers_or_summary():
    path_b, _, _ = _run_path_b(SHIYUN_KEY)
    perf = path_b.get("performance_fee") or {}
    tiers = perf.get("tiers") or []
    summary = perf.get("summary")
    assert len(tiers) >= 1 or summary


def test_source_snippets_for_open_day():
    path_b, _, _ = _run_path_b(SHIYUN_KEY)
    snippets = path_b.get("source_snippets") or {}
    assert any(k.startswith("open_day.") for k in snippets)


def test_extract_document_sync_returns_path_b():
    path = EXAMPLE / SHIYUN_KEY
    if not path.is_file():
        pytest.skip("missing shiyun docx")
    doc = document_to_dict(parse_docx(str(path)))
    _, _, path_b = extract_document_sync(doc, llm_client=LlmOff())  # type: ignore[arg-type]
    assert path_b.get("open_day")
