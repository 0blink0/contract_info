"""QUAL-03: optional LLM e2e — skipped without API key."""

import os

import pytest

from backend.app.extract.pipeline import extract_document_sync
from backend.app.llm.client import LlmClient
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict
from backend.tests.golden.conftest import FULU_KEY, SHIYUN_KEY, load_contract_expected
from backend.tests.golden.helpers.pipeline_runner import LlmOff

CRITICAL_LLM_TEXT_FIELDS = (
    "投资目标",
    "投资范围",
    "投资限制",
    "投资策略",
    "风险等级",
)


def _fill_rate(extraction, fields: tuple[str, ...]) -> float:
    pe = extraction.product_elements
    filled = 0
    for key in fields:
        fv = pe.get(key)
        val = fv.value if fv and getattr(fv, "value", None) else None
        if val is not None and str(val).strip():
            filled += 1
    return filled / len(fields) if fields else 0.0


@pytest.mark.llm
@pytest.mark.parametrize(
    "docx_fixture,expected_key",
    [
        ("golden_docx_shiyun", SHIYUN_KEY),
        ("golden_docx_fulu", FULU_KEY),
    ],
)
def test_golden_llm_fill_rate(request, docx_fixture, expected_key):
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    client = LlmClient()
    if not client.available:
        pytest.skip("LLM client not available")

    docx_path = request.getfixturevalue(docx_fixture)
    _ = load_contract_expected()[expected_key]
    doc = parse_docx(str(docx_path))
    document = document_to_dict(doc)

    ext_rule, _ = extract_document_sync(document, llm_client=LlmOff())  # type: ignore[arg-type]
    ext_llm, _ = extract_document_sync(document, llm_client=client)

    rate_rule = _fill_rate(ext_rule, CRITICAL_LLM_TEXT_FIELDS)
    rate_llm = _fill_rate(ext_llm, CRITICAL_LLM_TEXT_FIELDS)

    assert rate_llm > rate_rule or rate_rule == 0
    assert rate_llm >= 0.8
