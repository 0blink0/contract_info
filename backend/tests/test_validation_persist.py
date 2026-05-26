import uuid
from unittest.mock import patch

from backend.app.validate.schemas import ValidationItem, ValidationResult


def test_persist_validation_with_mock_llm(db_session):
    session, created_ids = db_session
    from backend.app.models.contract_file import ContractFile

    file_id = uuid.uuid4()
    record = ContractFile(
        id=file_id,
        filename="test.docx",
        status="extracting",
        parse_json={"blocks": []},
        extraction_result={
            "product_elements": {
                "管理人": {
                    "value": "测试公司",
                    "snippet": "管理人为测试公司，依法登记成立。",
                }
            }
        },
        extraction_warnings=[],
    )
    session.add(record)
    session.commit()
    created_ids.append(file_id)

    mock_result = ValidationResult(
        model="mock",
        skipped=False,
        items=[
            ValidationItem(
                field="管理人",
                status="pass",
                value="测试公司",
                reason="ok",
            )
        ],
    )
    mock_result.compute_summary()

    with patch(
        "backend.app.services.validation_service.run_llm_validation_sync",
        return_value=mock_result,
    ):
        from backend.app.services.validation_service import persist_validation

        persist_validation(file_id, session=session)
        session.commit()

    row = session.get(ContractFile, file_id)
    assert row.validation_result is not None
    assert row.validation_result["summary"]["pass"] >= 1


def test_persist_validation_skipped_warning(db_session):
    session, created_ids = db_session
    from backend.app.models.contract_file import ContractFile

    file_id = uuid.uuid4()
    record = ContractFile(
        id=file_id,
        filename="test.docx",
        status="extracting",
        parse_json={},
        extraction_result={"product_elements": {}},
        extraction_warnings=[],
    )
    session.add(record)
    session.commit()
    created_ids.append(file_id)

    skipped = ValidationResult(skipped=True, items=[])
    skipped.compute_summary()

    with patch(
        "backend.app.services.validation_service.run_llm_validation_sync",
        return_value=skipped,
    ):
        from backend.app.services.validation_service import persist_validation

        persist_validation(file_id, session=session)
        session.commit()

    row = session.get(ContractFile, file_id)
    codes = [w.get("code") for w in (row.extraction_warnings or [])]
    assert "validation_skipped" in codes
