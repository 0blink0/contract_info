import os

import pytest

from backend.app.llm.client import LlmClient


@pytest.mark.llm
def test_validation_llm_shiyun_sample(example_docx_path):
    if not LlmClient().available:
        pytest.skip("OPENAI_API_KEY not configured")

    from backend.app.parse import parse_docx
    from backend.app.parse.schemas import document_to_dict
    from backend.app.validate.llm_validator import run_llm_validation_sync

    document = document_to_dict(parse_docx(str(example_docx_path)))
    from backend.app.extract.pipeline import extract_document_sync

    result, _warnings, path_b = extract_document_sync(document)
    from backend.app.extract.schemas import extraction_result_to_dict

    extraction = extraction_result_to_dict(result)
    validation = run_llm_validation_sync(extraction, path_b, document)
    assert not validation.skipped
    assert validation.items
    assert validation.summary.get("pass", 0) >= 0
