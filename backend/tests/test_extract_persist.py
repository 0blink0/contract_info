import os
import uuid

import pytest

from backend.app.models.contract_file import ContractFile
from backend.app.services.extract_service import persist_extract_from_path


@pytest.mark.integration
def test_extract_persist_roundtrip(db_session, example_docx_path):
    session, created_ids = db_session
    file_id = persist_extract_from_path(str(example_docx_path))
    created_ids.append(file_id)

    row = session.get(ContractFile, file_id)
    assert row is not None
    assert row.status == "extracted"
    assert row.extraction_result
    assert row.extraction_result.get("product_elements")
    assert len(row.extraction_result.get("fee_rates") or []) >= 2


