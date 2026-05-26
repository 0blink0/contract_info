from __future__ import annotations

import uuid
from pathlib import Path

from backend.app.db.session import SessionLocal
from backend.app.extract.pipeline import extract_document_sync
from backend.app.extract.schemas import extraction_result_to_dict, warnings_to_list
from backend.app.models.contract_file import ContractFile
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict
from backend.app.services.parse_service import persist_parse


def _run_extract_on_document(document: dict) -> tuple[dict, list, dict]:
    result, warnings, path_b = extract_document_sync(document)
    return extraction_result_to_dict(result), warnings_to_list(warnings), path_b


def persist_extract_from_path(file_path: str) -> uuid.UUID:
    file_id = persist_parse(file_path)
    return persist_extract(file_id)


def persist_extract(file_id: uuid.UUID) -> uuid.UUID:
    session = SessionLocal()
    try:
        record = session.get(ContractFile, file_id)
        if record is None:
            raise ValueError(f"contract_file not found: {file_id}")
        if not record.parse_json:
            raise ValueError("parse_json empty — run parse first")

        record.status = "extracting"
        session.commit()

        try:
            result_dict, warnings, path_b = _run_extract_on_document(record.parse_json)
            record.extraction_result = result_dict
            record.path_b_json = path_b
            record.extraction_warnings = warnings
            record.status = "extracted"
            record.error_message = None
            session.commit()
            return file_id
        except Exception as exc:
            session.rollback()
            row = session.get(ContractFile, file_id)
            if row:
                row.status = "extraction_failed"
                row.error_message = str(exc)
                session.commit()
            raise
    finally:
        session.close()


def extract_from_docx_path(file_path: str) -> tuple[dict, list, dict]:
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(file_path)
    document = parse_docx(str(path))
    return _run_extract_on_document(document_to_dict(document))


def extract_from_file_id(file_id: uuid.UUID) -> tuple[dict, list, dict]:
    session = SessionLocal()
    try:
        record = session.get(ContractFile, file_id)
        if record is None or not record.parse_json:
            raise ValueError(f"No parse_json for {file_id}")
        return _run_extract_on_document(record.parse_json)
    finally:
        session.close()
