import uuid
from pathlib import Path

from backend.app.config import data_dir
from backend.app.db.session import SessionLocal
from backend.app.models.contract_file import ContractFile
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict, outline_preview_from_document
from backend.app.services.upload_service import persist_upload


def parse_file_id(file_id: uuid.UUID) -> uuid.UUID:
    session = SessionLocal()
    try:
        record = session.get(ContractFile, file_id)
        if record is None:
            raise ValueError(f"contract_file not found: {file_id}")
        if not record.storage_path:
            raise ValueError(f"storage_path empty for {file_id}")

        dest_file = data_dir() / record.storage_path
        if not dest_file.is_file():
            raise FileNotFoundError(str(dest_file))

        record.status = "parsing"
        record.error_message = None
        session.commit()

        try:
            document = parse_docx(str(dest_file))
            record.parse_json = document_to_dict(document)
            record.outline_preview = outline_preview_from_document(document)
            record.status = "parsed"
            record.error_message = None
            session.commit()
            return file_id
        except Exception as exc:
            session.rollback()
            row = session.get(ContractFile, file_id)
            if row:
                row.status = "failed"
                row.error_message = str(exc)
                session.commit()
            raise
    finally:
        session.close()


def persist_parse(file_path: str) -> uuid.UUID:
    source = Path(file_path).resolve()
    if not source.is_file():
        raise FileNotFoundError(file_path)

    file_id = persist_upload(source.read_bytes(), source.name)
    return parse_file_id(file_id)
